from __future__ import annotations

import random
import re
import copy
from typing import Any

from css_data_synthesis_test.schemas import DialogueTurn, SERVICE_SPEAKER, normalize_speaker


ROUTING_RESULT_HOME = "家用 + 可直接确认机型"
ROUTING_RESULT_BUILDING = "楼宇 + 可直接确认机型"
ROUTING_RESULT_HUMAN = "转人工"
ROUTING_RESULT_DIRECT = "可直接确认归属与机型"

PROMPT_BRAND_OR_SERIES = "请问您的空气能具体是什么品牌或系列的呢？"
PROMPT_USAGE_PURPOSE = "请问是生活用水加采暖使用，还是单独生活用水，或者单独采暖的呢？"
PROMPT_USAGE_SCENE = "请问空气能是在哪里使用的呢？家庭、别墅、公寓、理发店还是其他地方呢？"
PROMPT_PURCHASE_OR_PROPERTY = "请问是您自己购买的，还是楼盘配套赠送的呢？"
PROMPT_PROPERTY_YEAR = "请问是21年之前的楼盘，还是之后的呢？"
PROMPT_CAPACITY = "请问机器是多少升的，或者多少匹数的呢？"
PROMPT_HISTORY_DEVICE_CONFIRMATION = "请问是您名下查询到的空气能设备吗？"
PRODUCT_ROUTING_WEIGHT_CONTEXT_KEYS = {
    "entry": "product_routing_entry_weights",
    "brand_series": "product_routing_brand_series_weights",
    "usage_scene": "product_routing_usage_scene_weights",
    "purchase_or_property": "product_routing_purchase_or_property_weights",
    "property_year": "product_routing_property_year_weights",
    "history_confirmation": "product_routing_history_confirmation_weights",
}
PRODUCT_ROUTING_ALLOWED_ANSWER_KEYS = {
    "brand_or_series": {
        "brand_series.colmo",
        "brand_series.cooling_or_little_swan",
        "brand_series.home_series",
        "brand_series.lieyan",
        "entry.model",
        "entry.unknown",
    },
    "usage_purpose": {
        "purpose.heating",
        "purpose.unknown",
        "purpose.water",
        "purpose.both",
    },
    "usage_scene": {
        "scene.family",
        "scene.villa_apartment_barber",
        "scene.other_unknown",
        "scene.yes",
        "scene.no",
        "scene.unknown",
    },
    "history_device_confirmation": {
        "history_device.yes",
        "history_device.no_unknown",
    },
    "capacity_or_hp": {
        "capacity.above_threshold",
        "capacity.below_threshold",
        "capacity.unknown",
    },
    "purchase_or_property": {
        "purchase.self_buy",
        "purchase.unknown",
        "purchase.property_bundle",
    },
    "property_year": {
        "property_year.before_2021",
        "property_year.after_2021",
        "property_year.unknown",
    },
}

ENTRY_WEIGHTS = {
    "brand_series": 0.35,
    "model": 0.05,
    "unknown": 0.6,
}
BRAND_SERIES_WEIGHTS = {
    "colmo": 0.23,
    "cooling_or_little_swan": 0.15,
    "home_series": 0.40,
    "lieyan": 0.22,
}
COLMO_HOMOPHONE_TOKENS = ("COLMO", "科目", "科慕", "可么", "可木", "可慕", "扣摸", "扣慕")
LIEYAN_HOMOPHONE_TOKENS = (
    "烈焰",
    "烈炎",
    "列焰",
    "列炎",
    "莲焰",
    "莲炎",
    "莲叶",
    "连焰",
    "连炎",
    "连叶",
    "连夜",
    "莲夜",
)
COOLING_OR_LITTLE_SWAN_HOMOPHONE_TOKENS = (
    "酷风",
    "库风",
    "酷丰",
    "苦风",
    "小天鹅",
    "小天娥",
    "小天额",
)
HOME_SERIES_HOMOPHONE_TOKENS = (
    "真暖",
    "真蓝",
    "真省",
    "真神",
    "雪焰",
    "雪燕",
    "暖家",
    "暖佳",
    "煤改电",
    "煤改点",
    "真享",
    "真想",
)
MODEL_LOOKUP_WEIGHTS = {
    "home": 0.43,
    "unknown": 0.15,
    "building": 0.42,
}
UNKNOWN_PURPOSE_WEIGHTS = {
    "heating": 0.2,
    "unknown": 0.1,
    "water": 0.5,
    "both": 0.2,
}
USAGE_SCENE_WEIGHTS = {
    "family": 0.56,
    "villa_apartment_barber": 0.2,
    "other_unknown": 0.24,
}
PURCHASE_OR_PROPERTY_WEIGHTS = {
    "self_buy": 0.65,
    "unknown": 0.1,
    "property_bundle": 0.25,
}
PROPERTY_YEAR_WEIGHTS = {
    "before_2021": 0.6,
    "after_2021": 0.4,
}
WATER_CAPACITY_WEIGHTS = {
    "above_threshold": 0.3,
    "below_threshold": 0.5,
    "unknown": 0.2,
}
HISTORY_CONFIRMATION_WEIGHTS = {
    "yes": 0.68,
    "no_unknown": 0.32,
}
COOLING_OR_LITTLE_SWAN_NAMES = ("酷风", "小天鹅")
HOME_SERIES_NAMES = ("真暖", "真省", "雪焰", "暖家", "煤改电", "真享")
MODEL_FALLBACKS = (
    "KF66/200L-MI(E4)",
    "RSJ-20/300RDN3-C",
    "KF75/300L-MI(E5)",
    "KF110/500L-D",
)
KNOWN_BUILDING_MODEL_HINT_PATTERNS = (
    re.compile(r"KF110/500L-D", re.IGNORECASE),
    re.compile(r"/(?:7[5-9]\d|[89]\d{2}|\d{4,})L", re.IGNORECASE),
)
CHINESE_DIGITS = {
    "零": 0,
    "一": 1,
    "二": 2,
    "两": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "七": 7,
    "八": 8,
    "九": 9,
}
UNKNOWN_TEXT_PATTERNS = (
    "不知道",
    "不清楚",
    "不太清楚",
    "忘了",
    "忘记了",
    "记不得",
    "记不清",
    "说不上来",
    "不确定",
    "我也不知道",
)
GENERIC_MIDEA_PRODUCT_TOKENS = (
    "空气能热水器",
    "空气能热水机",
    "空气能",
    "热水器",
    "热水机",
    "机器",
    "机子",
    "品牌",
    "牌子",
    "系列",
    "款",
)
GENERIC_MIDEA_UNKNOWN_PATTERNS = (
    r"^(?:我)?(?:只|就)?知道(?:是)?美的(?:的)?(?:啊|呀|吧|呢|哈|嘛)?$",
    r"^(?:只|就)知道美的(?:的)?(?:啊|呀|吧|呢|哈|嘛)?$",
)
HEATING_USAGE_TOKENS = ("采暖", "供暖", "地暖", "暖气", "取暖", "制热")
HEATING_NEGATION_PREFIXES = (
    "不",
    "没",
    "没有",
    "无",
    "非",
    "不是",
    "并非",
    "不带",
    "没带",
    "没有带",
    "不用",
    "不做",
    "不搞",
)
ROUTING_SEGMENT_SPLIT_PATTERN = re.compile(r"[，,。！？!?；;、]")
ROUTING_PREFIX_PATTERNS = (
    r"^(这个|那个|这边|那边|我这边|我家这个|我们这个)",
    r"^(我看|我瞅|我猜|我估摸着|我觉得|我感觉)(?:着)?(?:是|像是|应该是|大概是|好像是)?",
    r"^(应该|可能|估计|大概|好像|像是|似乎|感觉)(?:是|算是|就是)?",
    r"^(就是|应该就是|可能就是|估计就是|大概就是)",
)
ROUTING_SUFFIX_PATTERNS = (
    r"(应该|可能|估计|大概|好像|像是|似乎|感觉)(?:是)?$",
    r"(应该就是|可能就是|估计就是|大概就是|好像就是)$",
    r"(来着)$",
    r"(这种|那种|那款|这一款|这一种)$",
    r"(吧|呢|啊|呀|哈|嘛)$",
    r"(的)$",
)
PROPERTY_CONTEXT_TOKENS = (
    "楼盘",
    "买房",
    "购房",
    "房子",
    "交房",
    "开发商",
    "物业",
    "小区",
)
PROPERTY_BUNDLE_TOKENS = (
    "配套",
    "赠送",
    "赠送的",
    "赠的",
    "送的",
    "送",
    "附送",
    "白送",
    "白送的",
    "白给",
    "白给的",
    "免费给",
    "免费给的",
    "免费送",
    "免费送的",
    "自带",
    "自带的",
    "就有",
    "原来就有",
    "本来就有",
    "一开始就有",
    "交付就有",
    "交房就有",
    "带的",
    "带",
    "配的",
    "配套的",
    "配好的",
    "配送",
)
SELF_BUY_TOKENS = (
    "自己买",
    "自己购买",
    "我买的",
    "买的",
    "单买的",
    "单独买的",
    "后来买的",
    "后装的",
    "另买的",
    "网上买",
    "京东买",
    "淘宝买",
    "拼多多买",
    "店里买",
)
UNCERTAIN_PREFIX_PATTERNS = (
    r"^(应该|可能|估计|大概|好像|像是|似乎|感觉)(?:是)?",
    r"^(我看|我瞅|我猜|我估摸着)(?:着)?(?:是)?",
)
EXTERNAL_GIFT_SOURCE_TOKENS = (
    "朋友",
    "亲戚",
    "别人",
    "家里人",
    "父母",
    "单位",
    "公司",
    "老板",
    "邻居",
    "同事",
)
ROUTING_SCENE_YES_TOKENS = (
    "是",
    "是的",
    "是啊",
    "是呀",
    "对",
    "对的",
    "对啊",
    "对滴",
    "嗯",
    "嗯嗯",
    "嗯呐",
    "没错",
    "算是",
    "属于",
)
ROUTING_SCENE_NO_TOKENS = (
    "不是",
    "不是的",
    "不是啊",
    "不对",
    "不算",
    "不属于",
    "都不是",
    "不在这几种",
    "不属于这个",
    "不属于这种",
)
FAMILY_SCENE_TOKENS = (
    "家庭",
    "家里",
    "家用",
    "自家",
    "自己家",
    "家里的",
    "住宅",
    "住家",
)
BUILDING_SCENE_TOKENS = (
    "别墅",
    "公寓",
    "理发店",
)
OTHER_SCENE_TOKENS = (
    "其他",
    "别的",
    "别处",
    "商用",
    "工程",
    "学校",
    "工厂",
    "酒店",
    "宿舍",
    "医院",
    "办公",
    "办公室",
    "门店",
    "店里",
)


def _normalize_text(text: str) -> str:
    normalized = str(text or "").strip()
    normalized = re.sub(r"^好的[，,\s]*", "", normalized)
    return normalized.rstrip("。！？!?")


def _weighted_choice(rng: random.Random, weights: dict[str, float]) -> str:
    options = [key for key, value in weights.items() if max(0.0, float(value)) > 0.0]
    if not options:
        return ""
    selected = rng.choices(
        population=options,
        weights=[max(0.0, float(weights[key])) for key in options],
        k=1,
    )[0]
    return str(selected)


def _pick_model_value(rng: random.Random, model_hint: str) -> str:
    normalized_hint = str(model_hint or "").strip()
    return normalized_hint if normalized_hint and normalized_hint != "未知" else rng.choice(MODEL_FALLBACKS)


def infer_model_lookup_answer_key(model_hint: str) -> str:
    normalized_hint = re.sub(r"\s+", "", str(model_hint or "").strip().upper())
    if not normalized_hint or normalized_hint == "未知":
        return "model_lookup.unknown"
    for pattern in KNOWN_BUILDING_MODEL_HINT_PATTERNS:
        if pattern.search(normalized_hint):
            return "model_lookup.building"
    return "model_lookup.unknown"


def _answer_value(rng: random.Random, answer_key: str, *, model_hint: str = "") -> str:
    if answer_key == "brand_series.colmo":
        return "COLMO"
    if answer_key == "brand_series.cooling_or_little_swan":
        return rng.choice(COOLING_OR_LITTLE_SWAN_NAMES)
    if answer_key == "brand_series.home_series":
        return rng.choice(HOME_SERIES_NAMES)
    if answer_key == "brand_series.lieyan":
        return "烈焰"
    if answer_key == "entry.model":
        return _pick_model_value(rng, model_hint)
    if answer_key == "entry.unknown":
        return "不知道品牌或系列"
    if answer_key == "purpose.heating":
        return "单独采暖"
    if answer_key == "purpose.unknown":
        return "不清楚用途"
    if answer_key == "purpose.water":
        return "单独生活用水"
    if answer_key == "purpose.both":
        return "生活用水和采暖都有"
    if answer_key == "scene.family":
        return "家庭使用"
    if answer_key == "scene.villa_apartment_barber":
        return rng.choice(("别墅使用", "公寓使用", "理发店使用"))
    if answer_key == "scene.other_unknown":
        return "不清楚具体使用场所"
    if answer_key == "scene.yes":
        return "是家庭/别墅/公寓/理发店使用"
    if answer_key == "scene.no":
        return "不是家庭/别墅/公寓/理发店使用"
    if answer_key == "scene.unknown":
        return "不确定是不是家庭/别墅/公寓/理发店使用"
    if answer_key == "history_device.yes":
        return "是查询到的那台设备"
    if answer_key == "history_device.no_unknown":
        return "不是或不清楚查询到的设备"
    if answer_key == "purchase.self_buy":
        return "自己购买"
    if answer_key == "purchase.unknown":
        return "不知道是不是自己购买"
    if answer_key == "purchase.property_bundle":
        return "楼盘配套赠送"
    if answer_key == "property_year.before_2021":
        return "21年之前的楼盘"
    if answer_key == "property_year.after_2021":
        return "21年之后的楼盘"
    if answer_key == "property_year.unknown":
        return "不清楚楼盘年份"
    if answer_key == "capacity.above_threshold":
        return rng.choice(("750升以上", "3匹及以上"))
    if answer_key == "capacity.below_threshold":
        return rng.choice(("750升以下", "3匹以下"))
    if answer_key == "capacity.unknown":
        return "不清楚容量或匹数"
    return ""


def _answer_instruction(answer_key: str, *, answer_value: str) -> str:
    instructions = {
        "brand_series.colmo": "自然表达品牌或系列是 COLMO。",
        "brand_series.cooling_or_little_swan": "自然表达品牌或系列是酷风或小天鹅中的一个。",
        "brand_series.home_series": "自然表达副品牌/系列是真暖、真省、雪焰、暖家、煤改电、真享中的一个。",
        "brand_series.lieyan": "自然表达系列是烈焰。",
        "entry.model": "自然提供一个具体型号，不要说自己不知道。",
        "entry.unknown": "优先用一小句直接表达自己不知道品牌或系列、暂时提供不了，或者只知道是美的；不要先猜一遍再否定，也不要绕着解释。",
        "purpose.heating": "自然表达机器是单独采暖用途。",
        "purpose.unknown": "优先用一小句直接表达自己不清楚机器用途；不要先猜生活用水还是采暖再反复改口。",
        "purpose.water": "自然表达机器是单独生活用水/洗澡热水用途。",
        "purpose.both": "自然表达机器同时用于生活用水和采暖。",
        "scene.family": "自然表达空气能是在家庭场所使用，只说这一个明确场所。",
        "scene.villa_apartment_barber": "自然表达空气能是在别墅、公寓或理发店中的一个场所使用，只能围绕关键信息里的单个场所回答。",
        "scene.other_unknown": "自然表达空气能是在其他地方使用，或者自己不清楚具体场所。",
        "scene.yes": "自然表达这是用户本人居住或单体经营空间内的使用场景。“公寓”仅指用户自己居住的公寓住房。",
        "scene.no": "自然表达这不是用户本人居住或单体经营空间内的使用场景，不算这里的“公寓”。不要为了回答问题刻意复述提示语里的分类解释。",
        "scene.unknown": "优先用一小句直接表达自己不确定使用场景；不要一边猜是家庭一边又反复否定。",
        "history_device.yes": "自然确认客服查询到的历史空气能设备就是本次要处理的设备。",
        "history_device.no_unknown": "自然表达不是查询到的那台设备，或者自己不清楚是否一致。",
        "purchase.self_buy": "自然表达机器是自己购买的。",
        "purchase.unknown": "优先用一小句直接表达自己不清楚是不是自己购买的；不要铺垫太多背景。",
        "purchase.property_bundle": "自然表达机器是楼盘配套赠送的。",
        "property_year.before_2021": "自然表达楼盘属于 2021 年之前。",
        "property_year.after_2021": "自然表达楼盘属于 2021 年之后。",
        "property_year.unknown": "优先用一小句直接表达自己不清楚楼盘年份；不要先猜年份再反复改口。",
        "capacity.above_threshold": "自然表达机器容量较大。更像真实用户时，通常只说自己更确定的一个维度，优先只说升数或匹数其中一个。",
        "capacity.below_threshold": "自然表达机器容量较小。更像真实用户时，通常只说自己更确定的一个维度，优先只说升数或匹数其中一个。",
        "capacity.unknown": "优先用一小句直接表达自己不清楚容量或匹数；不要先猜升数或匹数再否定。",
    }
    instruction = instructions.get(answer_key, "围绕当前节点自然回答。")
    if answer_value:
        return f"{instruction} 关键信息可围绕“{answer_value}”展开，但不要机械照抄。"
    return instruction


def _make_step(prompt_key: str, prompt: str, answer_key: str, answer_value: str) -> dict[str, str]:
    return {
        "prompt_key": prompt_key,
        "prompt": prompt,
        "answer_key": answer_key,
        "answer_value": answer_value,
        "answer_instruction": _answer_instruction(answer_key, answer_value=answer_value),
    }


def _stable_routing_rng(seed_text: str) -> random.Random:
    return random.Random(sum((index + 1) * ord(char) for index, char in enumerate(str(seed_text or ""))))


def _contains_unknown_intent(text: str) -> bool:
    normalized = _normalize_text(text)
    return any(pattern in normalized for pattern in UNKNOWN_TEXT_PATTERNS)


def _is_generic_midea_brand_expression(text: str) -> bool:
    normalized = re.sub(
        r"\s+",
        "",
        _strip_routing_prefixes(_normalize_text(text)),
    )
    if not normalized or "美的" not in normalized:
        return False
    if re.search(r"(不是|非)美的", normalized):
        return False
    if any(re.fullmatch(pattern, normalized) for pattern in GENERIC_MIDEA_UNKNOWN_PATTERNS):
        return True
    for token in GENERIC_MIDEA_PRODUCT_TOKENS:
        normalized = normalized.replace(token, "")
    normalized = re.sub(r"(吧|呢|啊|呀|哈|嘛|啦)+$", "", normalized)
    return normalized == "美的"


def _has_air_energy_history_device(hidden_context: dict[str, Any] | None) -> bool:
    if not isinstance(hidden_context, dict):
        return False
    for key in (
        "product_routing_has_history_device",
        "has_air_energy_history_device",
        "air_energy_history_device_exists",
    ):
        if isinstance(hidden_context.get(key), bool):
            return bool(hidden_context.get(key))
    for key in (
        "air_energy_history_device",
        "air_energy_history_device_info",
        "air_energy_history_equipment",
        "known_air_energy_device",
    ):
        value = hidden_context.get(key)
        if isinstance(value, str) and value.strip():
            return True
        if isinstance(value, dict) and value:
            return True
        if isinstance(value, list) and value:
            return True
    return False


def _history_device_confirmation_prompt(hidden_context: dict[str, Any] | None) -> str:
    if not isinstance(hidden_context, dict):
        return PROMPT_HISTORY_DEVICE_CONFIRMATION
    value = hidden_context.get("air_energy_history_device")
    if not isinstance(value, dict):
        value = hidden_context.get("air_energy_history_device_info")
    if not isinstance(value, dict):
        return PROMPT_HISTORY_DEVICE_CONFIRMATION
    brand = str(value.get("brand") or value.get("series") or "").strip()
    category = str(value.get("category") or value.get("product_category") or "").strip()
    year = str(value.get("purchase_year") or "").strip()
    month = str(value.get("purchase_month") or "").strip()
    purchase_date = str(value.get("purchase_date") or "").strip()
    if (not year or not month) and purchase_date:
        match = re.match(r"^(\d{4})-(\d{1,2})-\d{1,2}$", purchase_date)
        if match:
            year = match.group(1)
            month = str(int(match.group(2)))
    if brand and category and year and month:
        return f"这边看到您{year}年{month}月有购买一台{brand}{category}，请问是这台吗？"
    return PROMPT_HISTORY_DEVICE_CONFIRMATION


def _routing_weights(
    hidden_context: dict[str, Any] | None,
    group: str,
    default: dict[str, float],
) -> dict[str, float]:
    if not isinstance(hidden_context, dict):
        return dict(default)
    override = hidden_context.get(PRODUCT_ROUTING_WEIGHT_CONTEXT_KEYS.get(group, ""))
    if not isinstance(override, dict):
        return dict(default)
    weights = dict(default)
    for key, value in override.items():
        normalized_key = str(key).strip()
        if normalized_key in weights:
            weights[normalized_key] = max(0.0, float(value))
    if sum(weights.values()) <= 0:
        return dict(default)
    return weights


def allowed_product_routing_answer_keys(prompt_key: str) -> set[str]:
    return set(PRODUCT_ROUTING_ALLOWED_ANSWER_KEYS.get(str(prompt_key or "").strip(), set()))


def default_unknown_product_routing_answer_key(prompt_key: str) -> str:
    unknown_mapping = {
        "brand_or_series": "entry.unknown",
        "usage_purpose": "purpose.unknown",
        "usage_scene": "scene.other_unknown",
        "history_device_confirmation": "history_device.no_unknown",
        "capacity_or_hp": "capacity.unknown",
        "purchase_or_property": "purchase.unknown",
        "property_year": "property_year.unknown",
    }
    return str(unknown_mapping.get(str(prompt_key or "").strip(), "")).strip()


def _strip_uncertain_prefixes(text: str) -> str:
    normalized = str(text or "")
    for pattern in UNCERTAIN_PREFIX_PATTERNS:
        updated = re.sub(pattern, "", normalized)
        if updated != normalized:
            normalized = updated
    return normalized


def _matched_tokens(text: str, tokens: tuple[str, ...]) -> tuple[str, ...]:
    normalized = str(text or "")
    return tuple(token for token in tokens if token and token in normalized)


def _strip_routing_prefixes(text: str) -> str:
    normalized = str(text or "")
    changed = True
    while changed and normalized:
        changed = False
        for pattern in (*UNCERTAIN_PREFIX_PATTERNS, *ROUTING_PREFIX_PATTERNS):
            updated = re.sub(pattern, "", normalized)
            if updated != normalized:
                normalized = updated
                changed = True
    return normalized


def _strip_routing_suffixes(text: str) -> str:
    normalized = str(text or "")
    changed = True
    while changed and normalized:
        changed = False
        for pattern in ROUTING_SUFFIX_PATTERNS:
            updated = re.sub(pattern, "", normalized)
            if updated != normalized:
                normalized = updated
                changed = True
    return normalized


def _product_routing_text_variants(text: str) -> list[str]:
    normalized = _normalize_text(text)
    if not normalized:
        return []
    segments = [normalized]
    segments.extend(
        segment.strip()
        for segment in ROUTING_SEGMENT_SPLIT_PATTERN.split(normalized)
        if segment.strip()
    )
    variants: list[str] = []
    seen: set[str] = set()
    for segment in segments:
        compact = re.sub(r"\s+", "", segment)
        if compact and compact not in seen:
            seen.add(compact)
            variants.append(compact)
        stripped_prefix = re.sub(r"\s+", "", _strip_routing_prefixes(segment))
        if stripped_prefix and stripped_prefix not in seen:
            seen.add(stripped_prefix)
            variants.append(stripped_prefix)
        stripped_suffix = re.sub(r"\s+", "", _strip_routing_suffixes(segment))
        if stripped_suffix and stripped_suffix not in seen:
            seen.add(stripped_suffix)
            variants.append(stripped_suffix)
        stripped_both = re.sub(r"\s+", "", _strip_routing_suffixes(_strip_routing_prefixes(segment)))
        if stripped_both and stripped_both not in seen:
            seen.add(stripped_both)
            variants.append(stripped_both)
    return variants


def _is_property_bundle_expression(text: str) -> bool:
    normalized = re.sub(r"\s+", "", _strip_uncertain_prefixes(_normalize_text(text)))
    explicit_tokens = (
        "楼盘配套",
        "配套赠送",
        "楼盘送的",
        "楼盘赠的",
        "楼盘赠送的",
        "楼盘白给的",
        "楼盘免费给的",
        "开发商送",
        "开发商配的",
        "开发商装的",
        "开发商赠的",
        "开发商赠送的",
        "开发商白给的",
        "开发商免费给的",
        "交房带的",
        "交房带",
        "交房就有",
        "交房自带",
        "交付带的",
        "交付自带",
        "买房送的",
        "买房送",
        "买房自带",
        "买房就有",
        "购房送的",
        "购房送",
        "购房自带",
        "购房就有",
        "房子自己就有",
        "房子就有",
        "房子原来就有",
        "房子本来就有",
        "房子带的",
        "房子自带",
        "物业配的",
    )
    if any(token in normalized for token in explicit_tokens):
        return True
    if any(token in normalized for token in EXTERNAL_GIFT_SOURCE_TOKENS):
        return False
    bundle_hits = _matched_tokens(normalized, PROPERTY_BUNDLE_TOKENS)
    self_buy_hits = _matched_tokens(normalized, SELF_BUY_TOKENS)
    if bundle_hits and not self_buy_hits:
        has_property_context = any(token in normalized for token in PROPERTY_CONTEXT_TOKENS)
        has_strong_bundle_signal = any(len(token) >= 2 and token not in {"送", "带"} for token in bundle_hits)
        if has_property_context or has_strong_bundle_signal:
            return True
        simplified = re.sub(r"[的是吧呢啊呀哈嘛]", "", normalized)
        if simplified and len(simplified) <= 4:
            return True
    if normalized in {
        "送的",
        "赠的",
        "赠送的",
        "白给",
        "白给的",
        "白送",
        "白送的",
        "免费给",
        "免费给的",
        "免费送",
        "免费送的",
        "配的",
        "配套的",
        "自带的",
        "带的",
        "就有",
        "原来就有",
        "本来就有",
    }:
        return True
    has_property_context = any(token in normalized for token in PROPERTY_CONTEXT_TOKENS)
    has_bundle_signal = bool(bundle_hits)
    return has_property_context and has_bundle_signal


def _is_self_buy_expression(text: str) -> bool:
    normalized = re.sub(r"\s+", "", _strip_uncertain_prefixes(_normalize_text(text)))
    self_buy_hits = _matched_tokens(normalized, SELF_BUY_TOKENS)
    bundle_hits = _matched_tokens(normalized, PROPERTY_BUNDLE_TOKENS)
    return bool(self_buy_hits and not bundle_hits)


def _contains_water_usage_intent(text: str) -> bool:
    normalized = re.sub(r"\s+", "", _normalize_text(text))
    direct_tokens = (
        "热水",
        "生活用水",
        "生活热水",
        "洗澡",
        "洗浴",
        "用水",
        "洗澡用",
        "家用热水",
        "生活的",
        "生活用的",
        "单独生活的",
        "单独生活用的",
    )
    if any(token in normalized for token in direct_tokens):
        return True
    return bool(
        ("生活" in normalized and any(token in normalized for token in ("单独", "就", "只是", "平时")))
        or ("洗" in normalized and "澡" in normalized)
    )


def _contains_positive_heating_usage_intent(text: str) -> bool:
    normalized = re.sub(r"\s+", "", _normalize_text(text))
    if not normalized:
        return False

    for token in HEATING_USAGE_TOKENS:
        for match in re.finditer(re.escape(token), normalized):
            prefix = normalized[max(0, match.start() - 4) : match.start()]
            if any(prefix.endswith(neg) for neg in HEATING_NEGATION_PREFIXES):
                continue
            return True
    return False


def _simple_chinese_number_to_int(text: str) -> int | None:
    normalized = str(text or "").strip()
    if not normalized:
        return None
    if normalized.isdigit():
        return int(normalized)
    if normalized in CHINESE_DIGITS:
        return CHINESE_DIGITS[normalized]
    if normalized == "十":
        return 10
    if "百" in normalized:
        left, _, right = normalized.partition("百")
        hundreds = CHINESE_DIGITS.get(left, -1)
        if hundreds < 0:
            return None
        if not right:
            return hundreds * 100
        if right == "十":
            return hundreds * 100 + 10
        if right.endswith("十"):
            tens = CHINESE_DIGITS.get(right[:-1], -1)
            if tens >= 0:
                return hundreds * 100 + tens * 10
        if "十" in right:
            tens_part, _, units_part = right.partition("十")
            tens = CHINESE_DIGITS.get(tens_part, 1 if tens_part == "" else -1)
            units = CHINESE_DIGITS.get(units_part, 0 if units_part == "" else -1)
            if tens >= 0 and units >= 0:
                return hundreds * 100 + tens * 10 + units
        units = CHINESE_DIGITS.get(right, -1)
        if units >= 0:
            return hundreds * 100 + units
        return None
    if "十" in normalized:
        left, _, right = normalized.partition("十")
        tens = CHINESE_DIGITS.get(left, 1 if left == "" else -1)
        units = CHINESE_DIGITS.get(right, 0 if right == "" else -1)
        if tens >= 0 and units >= 0:
            return tens * 10 + units
        return None
    total = 0
    for char in normalized:
        if char not in CHINESE_DIGITS:
            return None
        total = total * 10 + CHINESE_DIGITS[char]
    return total


def _extract_measure_candidates(text: str, unit: str) -> list[int]:
    normalized = re.sub(r"\s+", "", _normalize_text(text))
    candidates: list[int] = []
    seen: set[int] = set()

    def add(value: int | None) -> None:
        if value is None or value in seen:
            return
        seen.add(value)
        candidates.append(value)

    pair_hundreds_match = re.search(
        rf"([一二两三四五六七八九])([一二两三四五六七八九])百(?:多|来)?{unit}",
        normalized,
    )
    if pair_hundreds_match:
        add(CHINESE_DIGITS.get(pair_hundreds_match.group(1), 0) * 100)
        add(CHINESE_DIGITS.get(pair_hundreds_match.group(2), 0) * 100)

    pair_direct_match = re.search(
        rf"([一二两三四五六七八九])([一二两三四五六七八九])(?:多|来)?{unit}",
        normalized,
    )
    if pair_direct_match:
        add(CHINESE_DIGITS.get(pair_direct_match.group(1)))
        add(CHINESE_DIGITS.get(pair_direct_match.group(2)))

    for match in re.finditer(rf"(\d+)(?:多|来)?{unit}", normalized):
        add(int(match.group(1)))

    for match in re.finditer(rf"([零一二两三四五六七八九十百\d]+)(?:多|来)?{unit}", normalized):
        token = match.group(1)
        if (
            unit == "匹"
            and len(token) == 2
            and all(char in CHINESE_DIGITS for char in token)
            and "十" not in token
            and "百" not in token
        ):
            add(CHINESE_DIGITS.get(token[0]))
            add(CHINESE_DIGITS.get(token[1]))
            continue
        add(_simple_chinese_number_to_int(token))

    return candidates


def _classify_capacity_threshold(text: str, *, unit: str, threshold: int) -> str:
    normalized = re.sub(r"\s+", "", _normalize_text(text))
    candidates = _extract_measure_candidates(normalized, unit)
    if not candidates:
        return ""
    if "以上" in normalized or "及以上" in normalized:
        return "capacity.above_threshold"
    if "以下" in normalized:
        return "capacity.below_threshold"
    if len(set(candidates)) > 1 and min(candidates) <= threshold <= max(candidates):
        return "capacity.unknown"
    if max(candidates) < threshold:
        return "capacity.below_threshold"
    if min(candidates) >= threshold:
        return "capacity.above_threshold"
    return "capacity.unknown"


def _extract_property_year_value(text: str) -> int | None:
    normalized = re.sub(r"\s+", "", _normalize_text(text))
    if not normalized:
        return None

    for match in re.finditer(r"(20\d{2})年?", normalized):
        year = int(match.group(1))
        if 2000 <= year <= 2099:
            return year

    for match in re.finditer(r"(?<!\d)(\d{2})年?", normalized):
        year = int(match.group(1))
        if 0 <= year <= 99:
            return 2000 + year

    for match in re.finditer(r"([零一二两三四五六七八九十百]{1,4})年", normalized):
        year = _simple_chinese_number_to_int(match.group(1))
        if year is None:
            continue
        if 0 <= year <= 99:
            return 2000 + year
        if 2000 <= year <= 2099:
            return year

    return None


def infer_product_routing_answer_key(prompt_key: str, user_text: str) -> str:
    for compact in _product_routing_text_variants(user_text):
        if prompt_key == "brand_or_series":
            if _contains_unknown_intent(compact):
                return "entry.unknown"
            if "COLMO" in compact.upper() or any(token in compact for token in COLMO_HOMOPHONE_TOKENS[1:]):
                return "brand_series.colmo"
            if any(token in compact for token in COOLING_OR_LITTLE_SWAN_HOMOPHONE_TOKENS):
                return "brand_series.cooling_or_little_swan"
            if any(token in compact for token in HOME_SERIES_NAMES) or any(
                token in compact for token in HOME_SERIES_HOMOPHONE_TOKENS
            ):
                return "brand_series.home_series"
            if any(token in compact for token in LIEYAN_HOMOPHONE_TOKENS):
                return "brand_series.lieyan"
            if re.search(r"[A-Za-z]{1,4}\d{1,4}|(?:KF|RSJ)[A-Za-z0-9/\-()]+", compact, flags=re.IGNORECASE):
                return "entry.model"
            if _is_generic_midea_brand_expression(compact):
                return "entry.unknown"
            continue

        if prompt_key == "usage_purpose":
            if _contains_unknown_intent(compact):
                return "purpose.unknown"
            has_heating = _contains_positive_heating_usage_intent(compact)
            has_water = _contains_water_usage_intent(compact)
            if has_heating and has_water:
                return "purpose.both"
            if has_heating:
                return "purpose.heating"
            if has_water:
                return "purpose.water"
            continue

        if prompt_key == "usage_scene":
            if _contains_unknown_intent(compact):
                return "scene.other_unknown"
            if any(token in compact for token in BUILDING_SCENE_TOKENS):
                return "scene.villa_apartment_barber"
            if any(token in compact for token in FAMILY_SCENE_TOKENS):
                return "scene.family"
            if compact in ROUTING_SCENE_NO_TOKENS or compact in ROUTING_SCENE_YES_TOKENS:
                return "scene.other_unknown"
            if any(token in compact for token in OTHER_SCENE_TOKENS):
                return "scene.other_unknown"
            continue

        if prompt_key == "history_device_confirmation":
            if _contains_unknown_intent(compact):
                return "history_device.no_unknown"
            if compact in ROUTING_SCENE_NO_TOKENS:
                return "history_device.no_unknown"
            if any(token in compact for token in ("不是这台", "不是查询到的", "不是名下的", "不对")):
                return "history_device.no_unknown"
            if compact in ROUTING_SCENE_YES_TOKENS:
                return "history_device.yes"
            if any(token in compact for token in ("是这台", "就是这台", "是查询到的", "是名下的")):
                return "history_device.yes"
            continue

        if prompt_key == "capacity_or_hp":
            if _contains_unknown_intent(compact):
                return "capacity.unknown"
            liter_result = _classify_capacity_threshold(compact, unit="升", threshold=750)
            if liter_result:
                return liter_result
            hp_result = _classify_capacity_threshold(compact, unit="匹", threshold=3)
            if hp_result:
                return hp_result
            continue

        if prompt_key == "purchase_or_property":
            if _contains_unknown_intent(compact):
                return "purchase.unknown"
            if _is_property_bundle_expression(compact):
                return "purchase.property_bundle"
            if _is_self_buy_expression(compact):
                return "purchase.self_buy"
            continue

        if prompt_key == "property_year":
            if _contains_unknown_intent(compact):
                return "property_year.unknown"
            if "之前" in compact or "以前" in compact:
                return "property_year.before_2021"
            if "之后" in compact or "以后" in compact:
                return "property_year.after_2021"
            if "2021" in compact or "21年" in compact:
                return "property_year.after_2021" if any(token in compact for token in ("之后", "以后")) else "property_year.before_2021"
            explicit_year = _extract_property_year_value(compact)
            if explicit_year is not None:
                return "property_year.before_2021" if explicit_year < 2021 else "property_year.after_2021"
            continue
    return ""


def _planned_next_answer_key(
    hidden_context: dict[str, Any] | None,
    observed_trace: list[str],
    *,
    prompt_key: str,
) -> str:
    steps = get_initial_product_routing_steps(hidden_context) or get_product_routing_steps(hidden_context)
    if not steps or not observed_trace:
        return ""

    matched_count = 0
    for step in steps:
        answer_key = str(step.get("answer_key", "")).strip()
        if matched_count < len(observed_trace):
            if answer_key == str(observed_trace[matched_count]).strip():
                matched_count += 1
            continue
        if str(step.get("prompt_key", "")).strip() == prompt_key:
            return answer_key
    return ""


def planned_product_routing_step(
    hidden_context: dict[str, Any] | None,
    observed_trace: list[str],
    *,
    prompt_key: str,
) -> dict[str, Any] | None:
    steps = get_initial_product_routing_steps(hidden_context) or get_product_routing_steps(hidden_context)
    if not steps:
        return None

    matched_count = 0
    for step in steps:
        answer_key = str(step.get("answer_key", "")).strip()
        if matched_count < len(observed_trace):
            if answer_key == str(observed_trace[matched_count]).strip():
                matched_count += 1
            continue
        if str(step.get("prompt_key", "")).strip() == prompt_key:
            return copy.deepcopy(step)
    return None


def _planned_next_step(
    hidden_context: dict[str, Any] | None,
    observed_trace: list[str],
    *,
    prompt_key: str,
    allowed_answer_keys: set[str],
    fallback_answer_key: str,
    rng: random.Random,
    model_hint: str = "",
) -> dict[str, str]:
    planned_step = planned_product_routing_step(
        hidden_context,
        observed_trace,
        prompt_key=prompt_key,
    )
    planned_answer_key = str((planned_step or {}).get("answer_key", "")).strip()
    if planned_answer_key not in allowed_answer_keys:
        planned_answer_key = fallback_answer_key
    prompt_by_key = {
        "usage_scene": PROMPT_USAGE_SCENE,
        "history_device_confirmation": _history_device_confirmation_prompt(hidden_context),
        "purchase_or_property": PROMPT_PURCHASE_OR_PROPERTY,
        "property_year": PROMPT_PROPERTY_YEAR,
    }
    return _make_step(
        prompt_key,
        prompt_by_key[prompt_key],
        planned_answer_key,
        _answer_value(rng, planned_answer_key, model_hint=model_hint),
    )


def next_product_routing_steps_from_observed_trace(
    observed_trace: list[str],
    *,
    model_hint: str = "",
    hidden_context: dict[str, Any] | None = None,
) -> tuple[list[dict[str, str]], str]:
    if not observed_trace:
        return [], ""

    current_answer_key = observed_trace[-1]
    rng = _stable_routing_rng("|".join(observed_trace) + f"|{model_hint}")

    if current_answer_key in {"entry.unknown", "entry.model"}:
        return [
            _planned_next_step(
                hidden_context,
                observed_trace,
                prompt_key="usage_scene",
                allowed_answer_keys={"scene.family", "scene.villa_apartment_barber", "scene.other_unknown"},
                fallback_answer_key="scene.other_unknown",
                rng=rng,
                model_hint=model_hint,
            )
        ], ""

    if current_answer_key in {"brand_series.colmo", "brand_series.home_series"}:
        return [], ROUTING_RESULT_HOME
    if current_answer_key == "brand_series.cooling_or_little_swan":
        return [], ROUTING_RESULT_HUMAN
    if current_answer_key == "brand_series.lieyan":
        return [], ROUTING_RESULT_BUILDING

    if current_answer_key == "scene.family":
        if _has_air_energy_history_device(hidden_context):
            return [
                _planned_next_step(
                    hidden_context,
                    observed_trace,
                    prompt_key="history_device_confirmation",
                    allowed_answer_keys={"history_device.yes", "history_device.no_unknown"},
                    fallback_answer_key="history_device.yes",
                    rng=rng,
                    model_hint=model_hint,
                )
            ], ""
        return [
            _planned_next_step(
                hidden_context,
                observed_trace,
                prompt_key="purchase_or_property",
                allowed_answer_keys={"purchase.self_buy", "purchase.unknown", "purchase.property_bundle"},
                fallback_answer_key="purchase.self_buy",
                rng=rng,
                model_hint=model_hint,
            )
        ], ""

    if current_answer_key in {"history_device.no_unknown"}:
        return [
            _planned_next_step(
                hidden_context,
                observed_trace,
                prompt_key="purchase_or_property",
                allowed_answer_keys={"purchase.self_buy", "purchase.unknown", "purchase.property_bundle"},
                fallback_answer_key="purchase.self_buy",
                rng=rng,
                model_hint=model_hint,
            )
        ], ""
    if current_answer_key == "history_device.yes":
        return [], ROUTING_RESULT_DIRECT

    if current_answer_key in {"scene.villa_apartment_barber", "scene.other_unknown", "scene.no", "scene.unknown"}:
        return [], ROUTING_RESULT_BUILDING

    if current_answer_key in {"purchase.self_buy", "purchase.unknown"}:
        return [], ROUTING_RESULT_HOME
    if current_answer_key == "purchase.property_bundle":
        return [
            _planned_next_step(
                hidden_context,
                observed_trace,
                prompt_key="property_year",
                allowed_answer_keys={
                    "property_year.before_2021",
                    "property_year.after_2021",
                    "property_year.unknown",
                },
                fallback_answer_key="property_year.before_2021",
                rng=rng,
                model_hint=model_hint,
            )
        ], ""

    if current_answer_key == "property_year.before_2021":
        return [], ROUTING_RESULT_HOME
    if current_answer_key in {"property_year.after_2021", "property_year.unknown"}:
        return [], ROUTING_RESULT_BUILDING

    return [], ""


def _append_purchase_chain(
    *,
    rng: random.Random,
    steps: list[dict[str, str]],
    trace: list[str],
    model_hint: str,
    hidden_context: dict[str, Any] | None = None,
) -> str:
    purchase = _weighted_choice(
        rng,
        _routing_weights(hidden_context, "purchase_or_property", PURCHASE_OR_PROPERTY_WEIGHTS),
    )
    purchase_answer_key = f"purchase.{purchase}"
    steps.append(
        _make_step(
            "purchase_or_property",
            PROMPT_PURCHASE_OR_PROPERTY,
            purchase_answer_key,
            _answer_value(rng, purchase_answer_key, model_hint=model_hint),
        )
    )
    trace.append(purchase_answer_key)

    if purchase in {"self_buy", "unknown"}:
        return ROUTING_RESULT_HOME

    property_year = _weighted_choice(
        rng,
        _routing_weights(hidden_context, "property_year", PROPERTY_YEAR_WEIGHTS),
    )
    property_year_answer_key = f"property_year.{property_year}"
    steps.append(
        _make_step(
            "property_year",
            PROMPT_PROPERTY_YEAR,
            property_year_answer_key,
            _answer_value(rng, property_year_answer_key, model_hint=model_hint),
        )
    )
    trace.append(property_year_answer_key)
    if property_year == "before_2021":
        return ROUTING_RESULT_HOME
    return ROUTING_RESULT_BUILDING


def build_product_routing_plan(
    *,
    rng: random.Random | None = None,
    model_hint: str = "",
    hidden_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    resolved_rng = rng or random.Random()
    steps: list[dict[str, str]] = []
    trace: list[str] = []

    entry = _weighted_choice(resolved_rng, _routing_weights(hidden_context, "entry", ENTRY_WEIGHTS))
    if entry == "brand_series":
        brand_choice = _weighted_choice(
            resolved_rng,
            _routing_weights(hidden_context, "brand_series", BRAND_SERIES_WEIGHTS),
        )
        brand_answer_key = f"brand_series.{brand_choice}"
        steps.append(
            _make_step(
                "brand_or_series",
                PROMPT_BRAND_OR_SERIES,
                brand_answer_key,
                _answer_value(resolved_rng, brand_answer_key, model_hint=model_hint),
            )
        )
        trace.append(brand_answer_key)
        result = {
            "colmo": ROUTING_RESULT_HOME,
            "cooling_or_little_swan": ROUTING_RESULT_HUMAN,
            "home_series": ROUTING_RESULT_HOME,
            "lieyan": ROUTING_RESULT_BUILDING,
        }[brand_choice]
    elif entry == "model":
        steps.append(
            _make_step(
                "brand_or_series",
                PROMPT_BRAND_OR_SERIES,
                "entry.model",
                _answer_value(resolved_rng, "entry.model", model_hint=model_hint),
            )
        )
        trace.append("entry.model")
        scene = _weighted_choice(
            resolved_rng,
            _routing_weights(hidden_context, "usage_scene", USAGE_SCENE_WEIGHTS),
        )
        scene_answer_key = f"scene.{scene}"
        steps.append(
            _make_step(
                "usage_scene",
                PROMPT_USAGE_SCENE,
                scene_answer_key,
                _answer_value(resolved_rng, scene_answer_key, model_hint=model_hint),
            )
        )
        trace.append(scene_answer_key)
        if scene == "family":
            if _has_air_energy_history_device(hidden_context):
                history_answer_key = "history_device.yes"
                steps.append(
                    _make_step(
                        "history_device_confirmation",
                        _history_device_confirmation_prompt(hidden_context),
                        history_answer_key,
                        _answer_value(resolved_rng, history_answer_key, model_hint=model_hint),
                    )
                )
                trace.append(history_answer_key)
                result = ROUTING_RESULT_DIRECT
            else:
                result = _append_purchase_chain(
                    rng=resolved_rng,
                    steps=steps,
                    trace=trace,
                    model_hint=model_hint,
                    hidden_context=hidden_context,
                )
        else:
            result = ROUTING_RESULT_BUILDING
    else:
        steps.append(
            _make_step(
                "brand_or_series",
                PROMPT_BRAND_OR_SERIES,
                "entry.unknown",
                _answer_value(resolved_rng, "entry.unknown", model_hint=model_hint),
            )
        )
        trace.append("entry.unknown")
        scene = _weighted_choice(
            resolved_rng,
            _routing_weights(hidden_context, "usage_scene", USAGE_SCENE_WEIGHTS),
        )
        scene_answer_key = f"scene.{scene}"
        steps.append(
            _make_step(
                "usage_scene",
                PROMPT_USAGE_SCENE,
                scene_answer_key,
                _answer_value(resolved_rng, scene_answer_key, model_hint=model_hint),
            )
        )
        trace.append(scene_answer_key)

        if scene == "family":
            if _has_air_energy_history_device(hidden_context):
                history_choice = _weighted_choice(
                    resolved_rng,
                    _routing_weights(
                        hidden_context,
                        "history_confirmation",
                        HISTORY_CONFIRMATION_WEIGHTS,
                    ),
                )
                history_answer_key = f"history_device.{history_choice}"
                steps.append(
                    _make_step(
                        "history_device_confirmation",
                        _history_device_confirmation_prompt(hidden_context),
                        history_answer_key,
                        _answer_value(resolved_rng, history_answer_key, model_hint=model_hint),
                    )
                )
                trace.append(history_answer_key)
                if history_answer_key == "history_device.yes":
                    result = ROUTING_RESULT_DIRECT
                else:
                    result = _append_purchase_chain(
                        rng=resolved_rng,
                        steps=steps,
                        trace=trace,
                        model_hint=model_hint,
                        hidden_context=hidden_context,
                    )
            else:
                result = _append_purchase_chain(
                    rng=resolved_rng,
                    steps=steps,
                    trace=trace,
                    model_hint=model_hint,
                    hidden_context=hidden_context,
                )
        else:
            result = ROUTING_RESULT_BUILDING

    return {
        "enabled": True,
        "result": result,
        "trace": trace,
        "steps": steps,
        "summary": " -> ".join(trace + [result]),
    }


def ensure_product_routing_plan(
    hidden_context: dict[str, Any] | None,
    *,
    enabled: bool,
    apply_probability: float,
    model_hint: str = "",
    rng: random.Random | None = None,
) -> dict[str, Any] | None:
    if not isinstance(hidden_context, dict) or not enabled:
        return None

    existing_plan = get_product_routing_plan(hidden_context)
    if existing_plan:
        hidden_context.setdefault("product_routing_initial_plan", copy.deepcopy(existing_plan))
        return existing_plan

    resolved_rng = rng or random.Random()
    decision = hidden_context.get("product_routing_should_apply")
    if isinstance(decision, bool):
        should_apply = decision
    else:
        probability = max(0.0, min(1.0, float(apply_probability)))
        should_apply = resolved_rng.random() < probability
        hidden_context["product_routing_should_apply"] = should_apply

    if not should_apply:
        return None

    plan = build_product_routing_plan(
        rng=resolved_rng,
        model_hint=model_hint,
        hidden_context=hidden_context,
    )
    hidden_context["product_routing_plan"] = plan
    hidden_context["product_routing_initial_plan"] = copy.deepcopy(plan)
    hidden_context["product_routing_result"] = str(plan.get("result", "")).strip()
    hidden_context["product_routing_trace"] = list(plan.get("trace", []))
    hidden_context["product_routing_summary"] = str(plan.get("summary", "")).strip()
    return plan


def get_product_routing_plan(hidden_context: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(hidden_context, dict):
        return None
    plan = hidden_context.get("product_routing_plan")
    if not isinstance(plan, dict):
        return None
    if not bool(plan.get("enabled", False)):
        return None
    steps = plan.get("steps")
    if not isinstance(steps, list) or not steps:
        return None
    return plan


def get_initial_product_routing_plan(hidden_context: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(hidden_context, dict):
        return None
    plan = hidden_context.get("product_routing_initial_plan")
    if not isinstance(plan, dict):
        return None
    if not bool(plan.get("enabled", False)):
        return None
    steps = plan.get("steps")
    if not isinstance(steps, list) or not steps:
        return None
    return plan


def _product_routing_steps_from_plan(plan: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not plan:
        return []
    steps = plan.get("steps", [])
    normalized_steps: list[dict[str, Any]] = []
    for step in steps:
        if not isinstance(step, dict):
            continue
        prompt = str(step.get("prompt", "")).strip()
        prompt_key = str(step.get("prompt_key", "")).strip()
        answer_key = str(step.get("answer_key", "")).strip()
        answer_value = str(step.get("answer_value", "")).strip()
        answer_instruction = str(step.get("answer_instruction", "")).strip()
        if not prompt or not prompt_key or not answer_key or not answer_instruction:
            continue
        normalized_step: dict[str, Any] = {
            "prompt_key": prompt_key,
            "prompt": prompt,
            "answer_key": answer_key,
            "answer_value": answer_value,
            "answer_instruction": answer_instruction,
        }
        raw_post_answer_trace = step.get("post_answer_trace", [])
        if isinstance(raw_post_answer_trace, list):
            normalized_step["post_answer_trace"] = [
                str(item).strip() for item in raw_post_answer_trace if str(item).strip()
            ]
        normalized_steps.append(normalized_step)
    return normalized_steps


def get_product_routing_steps(hidden_context: dict[str, Any] | None) -> list[dict[str, Any]]:
    return _product_routing_steps_from_plan(get_product_routing_plan(hidden_context))


def get_initial_product_routing_steps(hidden_context: dict[str, Any] | None) -> list[dict[str, Any]]:
    return _product_routing_steps_from_plan(get_initial_product_routing_plan(hidden_context))


def current_product_routing_step(
    transcript: list[DialogueTurn],
    hidden_context: dict[str, Any] | None,
) -> dict[str, str] | None:
    steps = get_product_routing_steps(hidden_context)
    if not steps or not transcript:
        return None
    last_turn = transcript[-1]
    if normalize_speaker(last_turn.speaker) != SERVICE_SPEAKER:
        return None

    matched_index = 0
    for index, turn in enumerate(transcript):
        if normalize_speaker(turn.speaker) != SERVICE_SPEAKER:
            continue
        if matched_index >= len(steps):
            break
        normalized_turn_text = _normalize_text(turn.text)
        normalized_step_prompt = _normalize_text(steps[matched_index]["prompt"])
        if (
            normalized_turn_text != normalized_step_prompt
            and not normalized_turn_text.endswith(normalized_step_prompt)
        ):
            continue
        if index == len(transcript) - 1:
            return steps[matched_index]
        matched_index += 1
    return None


def product_routing_instruction_for_prompt(
    transcript: list[DialogueTurn],
    hidden_context: dict[str, Any] | None,
) -> dict[str, str] | None:
    step = current_product_routing_step(transcript, hidden_context)
    return step
