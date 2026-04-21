from __future__ import annotations

import random
import re
from dataclasses import dataclass


PROVINCE_PREFIXES = (
    "河北",
    "山西",
    "辽宁",
    "吉林",
    "黑龙江",
    "江苏",
    "浙江",
    "安徽",
    "福建",
    "江西",
    "山东",
    "河南",
    "湖北",
    "湖南",
    "广东",
    "海南",
    "四川",
    "贵州",
    "云南",
    "陕西",
    "甘肃",
    "青海",
    "内蒙古",
    "广西",
    "西藏",
    "宁夏",
    "新疆",
    "台湾",
    "香港",
    "澳门",
)
PROVINCE_DISPLAY_NAMES = {
    "河北": "河北省",
    "山西": "山西省",
    "辽宁": "辽宁省",
    "吉林": "吉林省",
    "黑龙江": "黑龙江省",
    "江苏": "江苏省",
    "浙江": "浙江省",
    "安徽": "安徽省",
    "福建": "福建省",
    "江西": "江西省",
    "山东": "山东省",
    "河南": "河南省",
    "湖北": "湖北省",
    "湖南": "湖南省",
    "广东": "广东省",
    "海南": "海南省",
    "四川": "四川省",
    "贵州": "贵州省",
    "云南": "云南省",
    "陕西": "陕西省",
    "甘肃": "甘肃省",
    "青海": "青海省",
    "台湾": "台湾省",
}
MUNICIPALITY_PREFIXES = ("北京", "上海", "天津", "重庆")
COMMUNITY_SUFFIXES = (
    "小区",
    "社区",
    "花园",
    "公寓",
    "庭",
    "苑",
    "府",
    "里",
    "村",
    "大厦",
    "中心",
    "广场",
    "城",
    "家园",
    "新村",
    "碧桂园",
)
COMMUNITY_LIKE_SUFFIXES = COMMUNITY_SUFFIXES + ("校区", "园区", "景区", "厂区")
LANDMARK_LOCALITY_SUFFIXES = (
    "学校",
    "小学",
    "中学",
    "大学",
    "幼儿园",
    "学生宿舍",
    "宿舍",
    "医院",
    "诊所",
    "卫生院",
    "酒店",
    "宾馆",
    "饭店",
    "餐馆",
    "商场",
    "超市",
    "园区",
    "厂区",
    "校区",
    "景区",
    "写字楼",
    "大厦",
    "市场",
    "门店",
    "店铺",
    "餐厅",
    "咖啡馆",
    "奶茶店",
    "药店",
    "公司",
    "有限公司",
    "有限责任公司",
    "集团",
    "工厂",
    "厂",
    "办公楼",
    "产业园",
    "科技园",
    "政府",
    "街道办",
    "办事处",
    "派出所",
    "公安局",
    "法院",
    "检察院",
    "税务局",
    "管委会",
    "居委会",
    "村委会",
    "政务服务中心",
    "行政服务中心",
)
ROAD_LOCALITY_SUFFIXES = ("路", "街", "大道", "巷", "弄", "胡同")
BUILDING_SUFFIXES = ("号楼", "栋", "幢", "座", "楼")
COMMUNITY_SECTION_PATTERN = re.compile(
    r"([A-Za-z0-9\u4e00-\u9fa5]{2,20}?(?:[一二三四五六七八九十\d]+区))"
)
LANDMARK_LOCALITY_PATTERN = re.compile(
    rf"([A-Za-z0-9\u4e00-\u9fa5]{{2,40}}(?:{'|'.join(re.escape(suffix) for suffix in sorted(LANDMARK_LOCALITY_SUFFIXES, key=len, reverse=True))}))"
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
PROVINCE_SUFFIX_PATTERN = re.compile(
    r"^(省|壮族自治区|回族自治区|维吾尔自治区|自治区|特别行政区)"
)
DEFAULT_ADDRESS_SEGMENT_ROUNDS_WEIGHTS: dict[str, float] = {
    "2": 0.45,
    "3": 0.35,
    "4": 0.20,
    "5": 0.05,
}
DEFAULT_ADDRESS_SEGMENT_2_STRATEGY_WEIGHTS: dict[str, float] = {
    "province_city_district_locality__detail": 0.6,
    "province_city_district__locality_detail": 0.4,
}
DEFAULT_ADDRESS_SEGMENT_3_STRATEGY_WEIGHTS: dict[str, float] = {
    "province_city_district__locality__detail": 0.5454545454545454,
    "province_city__district_locality__detail": 0.2727272727272727,
    "province_city__district__locality_detail": 0.18181818181818182,
}
DEFAULT_ADDRESS_SEGMENT_4_STRATEGY_WEIGHTS: dict[str, float] = {
    "province_city__district__locality__detail": 1.0,
}
DEFAULT_ADDRESS_SEGMENT_5_STRATEGY_WEIGHTS: dict[str, float] = {
    "province__city__district__locality__detail": 1.0,
}
ADDRESS_SEGMENT_STRATEGIES: dict[str, tuple[tuple[int, ...], ...]] = {
    "province__city__district__locality__detail": ((0,), (1,), (2,), (3,), (4,)),
    "province_city__district__locality__detail": ((0, 1), (2,), (3,), (4,)),
    "province_city_district__locality__detail": ((0, 1, 2), (3,), (4,)),
    "province_city__district_locality__detail": ((0, 1), (2, 3), (4,)),
    "province_city__district__locality_detail": ((0, 1), (2,), (3, 4)),
    "province_city_district_locality__detail": ((0, 1, 2, 3), (4,)),
    "province_city_district__locality_detail": ((0, 1, 2), (3, 4)),
}


@dataclass(frozen=True)
class AddressComponents:
    province: str = ""
    city: str = ""
    district: str = ""
    town: str = ""
    road: str = ""
    community: str = ""
    building: str = ""
    unit: str = ""
    floor: str = ""
    room: str = ""

    @property
    def has_admin_region(self) -> bool:
        return bool(self.city or self.district)

    @property
    def has_locality(self) -> bool:
        return bool(self.town or self.road or self.community)

    @property
    def has_precise_detail(self) -> bool:
        return bool(self.building or self.unit or self.floor or self.room)


def normalize_address_text(text: str) -> str:
    normalized = (
        (text or "")
        .replace("，", "")
        .replace(",", "")
        .replace("。", "")
        .strip()
    )
    return re.sub(r"\s+", "", normalized)


def _strip_province_suffix(text: str) -> str:
    stripped = str(text or "")
    match = PROVINCE_SUFFIX_PATTERN.match(stripped)
    if match:
        return stripped[match.end() :]
    return stripped


def canonicalize_province_name(name: str) -> str:
    normalized = normalize_address_text(name)
    if not normalized:
        return ""
    compact = re.sub(
        r"(省|壮族自治区|回族自治区|维吾尔自治区|自治区|特别行政区)$",
        "",
        normalized,
    )
    return PROVINCE_DISPLAY_NAMES.get(compact, normalized)


def _compact_municipality_prefix(text: str) -> str:
    for municipality in MUNICIPALITY_PREFIXES:
        if text.startswith(f"{municipality}市"):
            return f"{municipality}{text[len(municipality) + 1:]}"
        if text.startswith(municipality):
            return text
    return text


def compact_address_text(text: str) -> str:
    normalized = normalize_address_text(text)
    if not normalized:
        return normalized

    compact = _compact_municipality_prefix(normalized)
    if compact != normalized:
        return compact

    province_prefix = next(
        (
            province
            for province in PROVINCE_PREFIXES
            if normalized.startswith(f"{province}省") or normalized.startswith(province)
        ),
        "",
    )
    if province_prefix:
        remainder = normalized[len(province_prefix) :]
        remainder = _strip_province_suffix(remainder)
        remainder = re.sub(r"^([^市区县]{2,9})市", r"\1", remainder, count=1)
        return f"{province_prefix}{remainder}"

    return re.sub(r"^([^市区县]{2,9})市", r"\1", normalized, count=1)


def canonicalize_address_text(text: str) -> str:
    normalized = normalize_address_text(text)
    if not normalized:
        return ""

    components = extract_address_components(normalized)
    ordered = "".join(
        part
        for part in (
            components.province,
            components.city,
            components.district,
            components.town,
            components.road,
            components.community,
            components.building,
            components.unit,
            components.floor,
            components.room,
        )
        if part
    )
    if ordered:
        return ordered

    province_prefix = next(
        (candidate for candidate in PROVINCE_PREFIXES if normalized.startswith(candidate)),
        "",
    )
    if province_prefix:
        remainder = normalized[len(province_prefix) :]
        remainder = _strip_province_suffix(remainder)
        return f"{canonicalize_province_name(province_prefix)}{remainder}"
    return normalized


def extract_address_components(text: str) -> AddressComponents:
    normalized = normalize_address_text(text)
    if not normalized:
        return AddressComponents()

    remainder = normalized
    province = ""
    city = ""

    for municipality in MUNICIPALITY_PREFIXES:
        if remainder.startswith(f"{municipality}市"):
            city = f"{municipality}市"
            remainder = remainder[len(city) :]
            break
        if remainder.startswith(municipality):
            city = f"{municipality}市"
            remainder = remainder[len(municipality) :]
            break

    province_prefix = ""
    if not city:
        province_prefix = next(
            (
                candidate
                for candidate in PROVINCE_PREFIXES
                if remainder.startswith(f"{candidate}省") or remainder.startswith(candidate)
            ),
            "",
        )
        if province_prefix:
            province = canonicalize_province_name(province_prefix)
            remainder = remainder[len(province_prefix) :]
            remainder = _strip_province_suffix(remainder)

        city_match = re.match(r"^[\u4e00-\u9fa5]{2,9}市(?!场|集)", remainder)
        if city_match:
            city = city_match.group(0)
            remainder = remainder[city_match.end() :]
        elif province_prefix:
            district_only_match = re.fullmatch(r"[\u4e00-\u9fa5]{1,24}(?:(?<!小)区|县|旗)", remainder)
            district_leading_match = re.match(
                r"^([\u4e00-\u9fa5]{1,24}(?:(?<!小)区|县|旗))(.+)$",
                remainder,
            )
            if district_only_match or district_leading_match:
                city = ""
            else:
                # Support colloquial province+city forms like "甘肃兰州七里河区".
                suffixless_city_match = re.match(
                    r"^([\u4e00-\u9fa5]{2,9}?)(?=[\u4e00-\u9fa5]{1,12}(?:(?<!小)区|县|旗))",
                    remainder,
                )
                if suffixless_city_match:
                    city = f"{suffixless_city_match.group(1)}市"
                    remainder = remainder[suffixless_city_match.end() :]
                elif re.fullmatch(r"[\u4e00-\u9fa5]{2,9}", remainder):
                    city = f"{remainder}市"
                    remainder = ""

    if not city and not province_prefix:
        district_only_match = re.fullmatch(r"[\u4e00-\u9fa5]{1,24}(?:(?<!小)区|县|旗)", remainder)
        district_leading_match = re.match(
            r"^([\u4e00-\u9fa5]{1,24}(?:(?<!小)区|县|旗))(.+)$",
            remainder,
        )
        if (
            not district_only_match
            and not district_leading_match
            and "自治县" not in remainder
            and "自治旗" not in remainder
        ):
            suffixless_city_match = re.match(
                r"^([\u4e00-\u9fa5]{2,4}?)(?=[\u4e00-\u9fa5]{1,12}(?:(?<!小)区|县|旗))",
                remainder,
            )
            if suffixless_city_match:
                city = f"{suffixless_city_match.group(1)}市"
                remainder = remainder[suffixless_city_match.end() :]

    district = ""
    district_match = re.match(r"^[\u4e00-\u9fa5]{1,24}?(?:(?<!小)(?<!社)区|县|旗)", remainder)
    if district_match:
        candidate_district = district_match.group(0)
        trailing_remainder = remainder[district_match.end() :]
        is_numbered_section = bool(re.fullmatch(r"[\u4e00-\u9fa5]{1,20}[一二三四五六七八九十\d]+区", candidate_district))
        is_community_like = any(candidate_district.endswith(suffix) for suffix in COMMUNITY_LIKE_SUFFIXES)
        contains_town_then_locality = bool(
            re.search(r"(?:街道|镇|乡).+(?:(?<!小)(?<!社)区)$", candidate_district)
        )
        if (
            not is_numbered_section
            and
            not is_community_like
            and not contains_town_then_locality
            and not (is_numbered_section and trailing_remainder)
        ):
            district = candidate_district
            remainder = trailing_remainder

    town = ""
    town_match = re.match(r"^[^镇乡街道]{1,12}(?:街道|镇|乡)", remainder)
    if town_match:
        town = town_match.group(0)
        remainder = remainder[town_match.end() :]

    road = ""
    road_end = -1
    road_suffix_pattern = "|".join(re.escape(suffix) for suffix in ROAD_LOCALITY_SUFFIXES if suffix != "弄")
    named_road_match = re.search(
        rf"([A-Za-z0-9\u4e00-\u9fa5]{{1,24}}(?:{road_suffix_pattern}))",
        remainder,
    )
    if named_road_match:
        road = named_road_match.group(1)
        road_end = named_road_match.end()
    else:
        lane_match = re.match(r"([零一二三四五六七八九十两\d]+弄)", remainder)
        if not lane_match:
            lane_match = re.search(r"([零一二三四五六七八九十两\d]+弄)", remainder)
        if lane_match:
            road = lane_match.group(1)
            road_end = lane_match.end()

    community = ""
    community_patterns = [
        rf"([A-Za-z0-9\u4e00-\u9fa5]*?(?:{suffix})(?:[零一二三四五六七八九十两\d]+期)?)"
        for suffix in COMMUNITY_SUFFIXES
    ]
    community_match_spans: list[tuple[int, int, str]] = []
    for pattern in community_patterns:
        for match in re.finditer(pattern, remainder):
            trailing_text = remainder[match.end() :]
            if trailing_text.startswith(ROAD_LOCALITY_SUFFIXES):
                continue
            start = match.start()
            end = match.end()
            value = match.group(1)
            if road_end > 0 and start < road_end < end:
                trimmed_value = remainder[road_end : match.end()]
                if trimmed_value and any(trimmed_value.endswith(suffix) for suffix in COMMUNITY_SUFFIXES):
                    community_match_spans.append((road_end, end, trimmed_value))
                continue
            if road_end > 0 and start < road_end:
                continue
            community_match_spans.append((start, end, value))
    section_match = COMMUNITY_SECTION_PATTERN.search(remainder)
    if section_match and not (road_end > 0 and section_match.start() < road_end):
        community_match_spans.append((section_match.start(), section_match.end(), section_match.group(1)))
    landmark_match = LANDMARK_LOCALITY_PATTERN.search(remainder)
    if landmark_match and not (road_end > 0 and landmark_match.start() < road_end):
        community_match_spans.append((landmark_match.start(), landmark_match.end(), landmark_match.group(1)))
    community_start = -1
    community_end = -1
    if community_match_spans:
        community_start, community_end, community = sorted(
            community_match_spans,
            key=lambda item: (item[0], -len(item[2])),
        )[0]

    building_suffix_pattern = "|".join(re.escape(suffix) for suffix in BUILDING_SUFFIXES)
    building_match = re.search(
        rf"([A-Za-z零一二三四五六七八九十两\d]+(?:{building_suffix_pattern}))",
        remainder,
    )
    unit_match = re.search(r"(\d+单元)", remainder)
    floor_match = re.search(r"([零一二三四五六七八九十两\d]+层)", remainder)
    if not floor_match:
        floor_match = re.search(r"([零一二三四五六七八九十两\d]+楼)(?=\d{2,4}(?:室)?$)", remainder)
    room_match = re.search(r"(\d{2,4}室)", remainder)
    if not floor_match and room_match:
        floor_match = re.search(r"([零一二三四五六七八九十两\d]+楼)$", remainder)

    room = room_match.group(1) if room_match else ""
    if not room:
        trailing_room = re.search(r"(?:(?:栋|幢|座|楼|单元|层)[^\d]*)?(\d{2,4})$", remainder)
        if trailing_room:
            room = f"{trailing_room.group(1)}室"

    building = building_match.group(1) if building_match else ""
    if (
        building
        and building.endswith("楼")
        and floor_match
        and floor_match.group(1) == building
        and room_match
        and building_match
        and building_match.start() >= room_match.start()
    ):
        building = ""

    if not community and building_match:
        locality_start = max(road_end, 0)
        fallback_community = remainder[locality_start : building_match.start()].strip("，, ")
        if (
            re.fullmatch(r"[A-Za-z0-9\u4e00-\u9fa5]{2,20}", fallback_community)
            and not re.fullmatch(r"[零一二三四五六七八九十两\d]+(?:号|弄)?", fallback_community)
            and not re.search(r"(?:路|街|大道|巷|弄|胡同|单元|层|室)$", fallback_community)
        ):
            community = fallback_community

    detail_starts = [
        match.start()
        for match in (building_match, unit_match, floor_match, room_match)
        if match is not None
    ]
    if not road and detail_starts:
        fallback_community = remainder[: min(detail_starts)].strip("，, ")
        if (
            re.fullmatch(r"[A-Za-z0-9\u4e00-\u9fa5]{2,20}", fallback_community)
            and not re.fullmatch(r"[零一二三四五六七八九十两\d]+(?:号|弄)?", fallback_community)
            and not re.search(r"(?:路|街|大道|巷|弄|胡同)", fallback_community)
            and len(fallback_community) > len(community)
        ):
            community = fallback_community

    if not community and not road and not detail_starts:
        fallback_community = remainder.strip("，, ")
        if (
            re.fullmatch(r"[A-Za-z0-9\u4e00-\u9fa5]{2,20}", fallback_community)
            and not re.fullmatch(r"[零一二三四五六七八九十两\d]+(?:号|弄)?", fallback_community)
            and not re.search(r"(?:路|街|大道|巷|弄|胡同|单元|层|室)$", fallback_community)
        ):
            community = fallback_community

    return AddressComponents(
        province=province,
        city=city,
        district=district,
        town=town,
        road=road,
        community=community,
        building=building,
        unit=unit_match.group(1) if unit_match else "",
        floor=floor_match.group(1) if floor_match else "",
        room=room,
    )


def _chinese_number_to_int(text: str) -> int | None:
    normalized = str(text or "").strip()
    if not normalized:
        return None
    if normalized.isdigit():
        return int(normalized)

    if normalized == "十":
        return 10

    if "十" in normalized:
        left, _, right = normalized.partition("十")
        tens = CHINESE_DIGITS.get(left, 1 if left == "" else -1)
        units = CHINESE_DIGITS.get(right, 0 if right == "" else -1)
        if tens >= 0 and units >= 0:
            return tens * 10 + units

    total = 0
    for char in normalized:
        if char not in CHINESE_DIGITS:
            return None
        total = total * 10 + CHINESE_DIGITS[char]
    return total


def _numeric_token(value: str) -> str:
    token = normalize_address_text(value)
    if not token:
        return ""
    match = re.search(r"[零一二三四五六七八九十两\d]+", token)
    if not match:
        return token
    number = _chinese_number_to_int(match.group(0))
    return str(number) if number is not None else match.group(0)


def comparable_component(kind: str, value: str) -> str:
    compact = normalize_address_text(value)
    if not compact:
        return ""
    if kind == "province":
        return re.sub(r"(省|市|壮族自治区|回族自治区|维吾尔自治区|自治区|特别行政区)$", "", compact)
    if kind == "city":
        return re.sub(r"市$", "", compact)
    if kind in {"building", "unit", "floor", "room"}:
        return _numeric_token(compact)
    return compact


def components_match(candidate: AddressComponents, actual: AddressComponents) -> bool:
    comparisons = (
        ("province", candidate.province, actual.province),
        ("city", candidate.city, actual.city),
        ("district", candidate.district, actual.district),
        ("town", candidate.town, actual.town),
        ("road", candidate.road, actual.road),
        ("community", candidate.community, actual.community),
        ("building", candidate.building, actual.building),
        ("unit", candidate.unit, actual.unit),
        ("floor", candidate.floor, actual.floor),
        ("room", candidate.room, actual.room),
    )
    for kind, candidate_value, actual_value in comparisons:
        candidate_comp = comparable_component(kind, candidate_value)
        actual_comp = comparable_component(kind, actual_value)
        if not candidate_comp:
            continue
        if not actual_comp:
            return False
        if kind in {"community", "road"}:
            if candidate_comp not in actual_comp and actual_comp not in candidate_comp:
                return False
            continue
        if candidate_comp != actual_comp:
            return False
    return True


def build_address_progressive_segments(
    address: str,
    rng: random.Random,
    *,
    round_weights: dict[str, float] | None = None,
    segment_2_strategy_weights: dict[str, float] | None = None,
    segment_3_strategy_weights: dict[str, float] | None = None,
    segment_4_strategy_weights: dict[str, float] | None = None,
    segment_5_strategy_weights: dict[str, float] | None = None,
) -> list[str]:
    components = extract_address_components(address)
    groups = [
        components.province,
        components.city,
        components.district,
        "".join(part for part in (components.town, components.road, components.community) if part),
        "".join(part for part in (components.building, components.unit, components.floor, components.room) if part),
    ]
    if not any(groups):
        return [address]

    round_weights = round_weights or DEFAULT_ADDRESS_SEGMENT_ROUNDS_WEIGHTS
    segment_strategy_weights = {
        2: segment_2_strategy_weights or DEFAULT_ADDRESS_SEGMENT_2_STRATEGY_WEIGHTS,
        3: segment_3_strategy_weights or DEFAULT_ADDRESS_SEGMENT_3_STRATEGY_WEIGHTS,
        4: segment_4_strategy_weights or DEFAULT_ADDRESS_SEGMENT_4_STRATEGY_WEIGHTS,
        5: segment_5_strategy_weights or DEFAULT_ADDRESS_SEGMENT_5_STRATEGY_WEIGHTS,
    }
    valid_strategies: dict[int, list[tuple[str, list[str]]]] = {}
    for name, strategy in ADDRESS_SEGMENT_STRATEGIES.items():
        segments = _build_segments_for_strategy(groups, strategy)
        if len(segments) >= 2:
            valid_strategies.setdefault(len(segments), []).append((name, segments))

    if not valid_strategies:
        return [address]

    available_round_counts = sorted(valid_strategies)
    round_choices = [str(round_count) for round_count in available_round_counts]
    round_choice_weights = [max(0.0, float(round_weights.get(choice, 0.0))) for choice in round_choices]
    if sum(round_choice_weights) <= 0:
        round_choice_weights = [1.0] * len(round_choices)
    target_round_count = int(rng.choices(round_choices, weights=round_choice_weights, k=1)[0])

    strategy_candidates = valid_strategies[target_round_count]
    strategy_choice_names = [name for name, _ in strategy_candidates]
    selected_strategy_weights = segment_strategy_weights.get(target_round_count, {})
    strategy_choice_weights = [
        max(0.0, float(selected_strategy_weights.get(name, 0.0)))
        for name in strategy_choice_names
    ]
    if sum(strategy_choice_weights) <= 0:
        strategy_choice_weights = [1.0] * len(strategy_choice_names)
    selected_strategy_name = rng.choices(
        strategy_choice_names,
        weights=strategy_choice_weights,
        k=1,
    )[0]
    for name, segments in strategy_candidates:
        if name == selected_strategy_name:
            return segments
    return strategy_candidates[0][1]


def _build_segments_for_strategy(
    groups: list[str],
    strategy: tuple[tuple[int, ...], ...],
) -> list[str]:
    segments: list[str] = []
    for group_indexes in strategy:
        segment = "".join(groups[index] for index in group_indexes if groups[index])
        if segment:
            segments.append(segment)
    return segments
