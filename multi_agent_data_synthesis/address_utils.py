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
MUNICIPALITY_PREFIXES = ("北京", "上海", "天津", "重庆")
COMMUNITY_SUFFIXES = (
    "小区",
    "花园",
    "公寓",
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
DEFAULT_ADDRESS_SEGMENT_ROUNDS_WEIGHTS: dict[str, float] = {
    "2": 0.45,
    "3": 0.35,
    "4": 0.20,
}
DEFAULT_ADDRESS_SEGMENT_STRATEGY_WEIGHTS: dict[str, float] = {
    "province_city__district__locality__detail": 0.20,
    "province_city_district__locality__detail": 0.30,
    "province_city__district_locality__detail": 0.15,
    "province_city__district__locality_detail": 0.10,
    "province_city_district_locality__detail": 0.15,
    "province_city_district__locality_detail": 0.10,
}
ADDRESS_SEGMENT_STRATEGIES: dict[str, tuple[tuple[int, ...], ...]] = {
    "province_city__district__locality__detail": ((0,), (1,), (2,), (3,)),
    "province_city_district__locality__detail": ((0, 1), (2,), (3,)),
    "province_city__district_locality__detail": ((0,), (1, 2), (3,)),
    "province_city__district__locality_detail": ((0,), (1,), (2, 3)),
    "province_city_district_locality__detail": ((0, 1, 2), (3,)),
    "province_city_district__locality_detail": ((0, 1), (2, 3)),
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
    return (
        (text or "")
        .replace("，", "")
        .replace(",", "")
        .replace("。", "")
        .replace(" ", "")
        .strip()
    )


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
        if remainder.startswith("省"):
            remainder = remainder[1:]
        remainder = re.sub(r"^([^市区县]{2,9})市", r"\1", remainder, count=1)
        return f"{province_prefix}{remainder}"

    return re.sub(r"^([^市区县]{2,9})市", r"\1", normalized, count=1)


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
            province = f"{province_prefix}省" if remainder.startswith(f"{province_prefix}省") else province_prefix
            remainder = remainder[len(province_prefix) :]
            if remainder.startswith("省"):
                remainder = remainder[1:]

        city_match = re.match(r"^[\u4e00-\u9fa5]{2,9}市", remainder)
        if city_match:
            city = city_match.group(0)
            remainder = remainder[city_match.end() :]

    district = ""
    district_match = re.match(r"^[\u4e00-\u9fa5]{1,12}(?:(?<!小)区|县|旗)", remainder)
    if district_match:
        district = district_match.group(0)
        remainder = remainder[district_match.end() :]

    town = ""
    town_match = re.match(r"^[^镇乡街道]{1,12}(?:街道|镇|乡)", remainder)
    if town_match:
        town = town_match.group(0)
        remainder = remainder[town_match.end() :]

    road = ""
    road_match = re.search(r"([^\d]{1,20}(?:路|街|大道|巷|弄|胡同)\d+号?)", remainder)
    if road_match:
        road = road_match.group(1)
    community_search_text = remainder[road_match.end() :] if road_match else remainder

    community = ""
    community_patterns = [
        rf"([A-Za-z0-9\u4e00-\u9fa5]*?(?:{suffix})(?:[零一二三四五六七八九十两\d]+期)?)"
        for suffix in COMMUNITY_SUFFIXES
    ]
    community_matches: list[str] = []
    for pattern in community_patterns:
        community_matches.extend(match.group(1) for match in re.finditer(pattern, community_search_text))
    if community_matches:
        community = sorted(community_matches, key=len)[-1]

    building_match = re.search(r"([零一二三四五六七八九十两\d]+(?:号楼|栋|幢|座|楼))", remainder)
    unit_match = re.search(r"(\d+单元)", remainder)
    floor_match = re.search(r"([零一二三四五六七八九十两\d]+层)", remainder)
    room_match = re.search(r"(\d{2,4}室)", remainder)

    room = room_match.group(1) if room_match else ""
    if not room:
        trailing_room = re.search(r"(?:(?:栋|幢|座|楼|单元|层)[^\d]*)?(\d{2,4})$", remainder)
        if trailing_room:
            room = f"{trailing_room.group(1)}室"

    return AddressComponents(
        province=province,
        city=city,
        district=district,
        town=town,
        road=road,
        community=community,
        building=building_match.group(1) if building_match else "",
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
    strategy_weights: dict[str, float] | None = None,
) -> list[str]:
    components = extract_address_components(address)
    groups = [
        "".join(part for part in (components.province, components.city) if part),
        components.district,
        "".join(part for part in (components.town, components.road, components.community) if part),
        "".join(part for part in (components.building, components.unit, components.floor, components.room) if part),
    ]
    if not any(groups):
        return [address]

    round_weights = round_weights or DEFAULT_ADDRESS_SEGMENT_ROUNDS_WEIGHTS
    strategy_weights = strategy_weights or DEFAULT_ADDRESS_SEGMENT_STRATEGY_WEIGHTS
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
    strategy_choice_weights = [
        max(0.0, float(strategy_weights.get(name, 0.0)))
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
