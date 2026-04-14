from __future__ import annotations

import asyncio
import json
import random
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from multi_agent_data_synthesis.address_utils import (
    COMMUNITY_SUFFIXES,
    MUNICIPALITY_PREFIXES,
    build_address_progressive_segments,
    extract_address_components,
)
from multi_agent_data_synthesis.config import AppConfig
from multi_agent_data_synthesis.dialogue_plans import decide_second_round_reply_strategy
from multi_agent_data_synthesis.llm import OpenAIChatClient
from multi_agent_data_synthesis.product_routing import ensure_product_routing_plan
from multi_agent_data_synthesis.schemas import CustomerProfile, Scenario, ServiceRequest


VARIABLE_FIELDS = (
    "full_name",
    "surname",
    "phone",
    "address",
    "persona",
    "speech_style",
    "issue",
    "desired_resolution",
    "availability",
    "emotion",
    "urgency",
    "prior_attempts",
    "special_constraints",
)


def _build_region_options(region_map: dict[str, dict[str, tuple[str, ...]]]) -> tuple[dict[str, Any], ...]:
    return tuple(
        {"province": province, "city": city, "districts": districts}
        for province, cities in region_map.items()
        for city, districts in cities.items()
    )


COHERENT_REGION_CITY_DISTRICT_MAP: dict[str, dict[str, tuple[str, ...]]] = {
    "河北省": {
        "石家庄市": ("长安区", "桥西区", "裕华区"),
        "唐山市": ("路北区", "路南区", "丰南区"),
    },
    "山西省": {
        "太原市": ("小店区", "迎泽区", "万柏林区"),
        "大同市": ("平城区", "云冈区", "新荣区"),
    },
    "辽宁省": {
        "沈阳市": ("和平区", "皇姑区", "浑南区"),
        "大连市": ("中山区", "甘井子区", "沙河口区"),
    },
    "吉林省": {
        "长春市": ("朝阳区", "南关区", "绿园区"),
        "吉林市": ("昌邑区", "船营区", "丰满区"),
    },
    "黑龙江省": {
        "哈尔滨市": ("南岗区", "道里区", "香坊区"),
        "齐齐哈尔市": ("龙沙区", "建华区", "铁锋区"),
    },
    "江苏省": {
        "南京市": ("鼓楼区", "秦淮区", "建邺区"),
        "苏州市": ("吴中区", "工业园区", "虎丘区"),
    },
    "浙江省": {
        "杭州市": ("西湖区", "余杭区", "拱墅区"),
        "宁波市": ("鄞州区", "海曙区", "江北区"),
    },
    "安徽省": {
        "合肥市": ("蜀山区", "包河区", "庐阳区"),
        "芜湖市": ("镜湖区", "弋江区", "鸠江区"),
    },
    "福建省": {
        "福州市": ("仓山区", "鼓楼区", "台江区"),
        "厦门市": ("思明区", "湖里区", "集美区"),
    },
    "江西省": {
        "南昌市": ("东湖区", "西湖区", "红谷滩区"),
        "赣州市": ("章贡区", "南康区", "赣县区"),
    },
    "山东省": {
        "济南市": ("历下区", "历城区", "槐荫区"),
        "青岛市": ("崂山区", "黄岛区", "李沧区"),
    },
    "河南省": {
        "郑州市": ("金水区", "中原区", "二七区"),
        "洛阳市": ("西工区", "洛龙区", "涧西区"),
    },
    "湖北省": {
        "武汉市": ("洪山区", "江汉区", "武昌区"),
        "宜昌市": ("西陵区", "伍家岗区", "夷陵区"),
    },
    "湖南省": {
        "长沙市": ("岳麓区", "芙蓉区", "雨花区"),
        "株洲市": ("天元区", "荷塘区", "石峰区"),
    },
    "广东省": {
        "广州市": ("天河区", "海珠区", "越秀区"),
        "深圳市": ("南山区", "福田区", "宝安区"),
    },
    "海南省": {
        "海口市": ("龙华区", "美兰区", "秀英区"),
        "三亚市": ("吉阳区", "天涯区", "海棠区"),
    },
    "四川省": {
        "成都市": ("武侯区", "高新区", "锦江区"),
        "绵阳市": ("涪城区", "游仙区", "安州区"),
    },
    "贵州省": {
        "贵阳市": ("南明区", "云岩区", "观山湖区"),
        "遵义市": ("汇川区", "红花岗区", "播州区"),
    },
    "云南省": {
        "昆明市": ("五华区", "官渡区", "西山区"),
        "曲靖市": ("麒麟区", "沾益区", "马龙区"),
    },
    "陕西省": {
        "西安市": ("雁塔区", "未央区", "长安区"),
        "宝鸡市": ("金台区", "渭滨区", "陈仓区"),
    },
    "甘肃省": {
        "兰州市": ("城关区", "七里河区", "安宁区"),
        "天水市": ("秦州区", "麦积区", "清水县"),
    },
    "青海省": {
        "西宁市": ("城西区", "城东区", "城中区"),
        "海东市": ("乐都区", "平安区", "民和回族土族自治县"),
    },
    "内蒙古": {
        "呼和浩特市": ("新城区", "赛罕区", "回民区"),
        "包头市": ("昆都仑区", "青山区", "东河区"),
    },
    "广西": {
        "南宁市": ("青秀区", "兴宁区", "西乡塘区"),
        "柳州市": ("城中区", "鱼峰区", "柳南区"),
    },
    "西藏": {
        "拉萨市": ("城关区", "堆龙德庆区", "达孜区"),
        "日喀则市": ("桑珠孜区", "南木林县", "江孜县"),
    },
    "宁夏": {
        "银川市": ("金凤区", "兴庆区", "西夏区"),
        "吴忠市": ("利通区", "红寺堡区", "盐池县"),
    },
    "新疆": {
        "乌鲁木齐市": ("天山区", "沙依巴克区", "水磨沟区"),
        "克拉玛依市": ("克拉玛依区", "独山子区", "白碱滩区"),
    },
}
COHERENT_MUNICIPALITY_CITY_DISTRICT_MAP: dict[str, tuple[str, ...]] = {
    "北京市": ("朝阳区", "海淀区", "丰台区"),
    "上海市": ("浦东新区", "闵行区", "徐汇区"),
    "天津市": ("南开区", "河西区", "滨海新区"),
    "重庆市": ("渝北区", "渝中区", "沙坪坝区"),
}
COHERENT_REGION_OPTIONS: tuple[dict[str, Any], ...] = _build_region_options(
    COHERENT_REGION_CITY_DISTRICT_MAP
)
COHERENT_MUNICIPALITY_OPTIONS: tuple[dict[str, Any], ...] = tuple(
    {"province": "", "city": city, "districts": districts}
    for city, districts in COHERENT_MUNICIPALITY_CITY_DISTRICT_MAP.items()
)
SURNAME_OPTIONS: tuple[str, ...] = (
    "赵",
    "钱",
    "孙",
    "李",
    "周",
    "吴",
    "郑",
    "王",
    "冯",
    "陈",
    "褚",
    "卫",
    "蒋",
    "沈",
    "韩",
    "杨",
    "朱",
    "秦",
    "尤",
    "许",
    "何",
    "吕",
    "施",
    "张",
    "孔",
    "曹",
    "严",
    "华",
    "金",
    "魏",
    "陶",
    "姜",
    "戚",
    "谢",
    "邹",
    "喻",
    "柏",
    "水",
    "窦",
    "章",
    "云",
    "苏",
    "潘",
    "葛",
    "奚",
    "范",
    "彭",
    "郎",
    "鲁",
    "韦",
    "昌",
    "马",
    "苗",
    "凤",
    "花",
    "方",
    "俞",
    "任",
    "袁",
    "柳",
    "酆",
    "鲍",
    "史",
    "唐",
    "费",
    "廉",
    "岑",
    "薛",
    "雷",
    "贺",
    "倪",
    "汤",
    "滕",
    "殷",
    "罗",
    "毕",
    "郝",
    "邬",
    "安",
    "常",
    "乐",
    "于",
    "时",
    "傅",
    "皮",
    "卞",
    "齐",
    "康",
    "伍",
    "余",
    "元",
    "卜",
    "顾",
    "孟",
    "平",
    "黄",
    "和",
    "穆",
    "萧",
    "尹",
    "姚",
    "邵",
    "湛",
    "汪",
    "祁",
    "毛",
    "禹",
    "狄",
    "米",
    "贝",
    "明",
    "臧",
    "计",
    "伏",
    "成",
    "戴",
    "谈",
    "宋",
    "茅",
    "庞",
    "熊",
    "纪",
    "舒",
    "屈",
    "项",
    "祝",
    "董",
    "梁",
    "杜",
    "阮",
    "蓝",
    "闵",
    "席",
    "季",
    "麻",
    "强",
    "贾",
    "路",
    "娄",
    "危",
    "江",
    "童",
    "颜",
    "郭",
    "梅",
    "盛",
    "林",
    "刁",
    "钟",
    "徐",
    "邱",
    "骆",
    "高",
    "夏",
    "蔡",
    "田",
    "樊",
    "胡",
    "凌",
    "霍",
    "虞",
    "万",
    "支",
    "柯",
    "昝",
    "管",
    "卢",
    "莫",
    "经",
    "房",
    "裘",
    "缪",
    "干",
    "解",
    "应",
    "宗",
    "丁",
    "宣",
    "贲",
    "邓",
    "郁",
    "单",
    "杭",
    "洪",
    "包",
    "诸",
    "左",
    "石",
    "崔",
    "吉",
    "钮",
    "龚",
    "程",
    "嵇",
    "邢",
    "滑",
    "裴",
    "陆",
    "荣",
    "翁",
    "荀",
    "羊",
    "於",
    "惠",
    "甄",
    "曲",
    "家",
    "封",
    "芮",
    "羿",
    "储",
    "靳",
    "汲",
    "邴",
    "糜",
    "松",
    "井",
    "段",
    "富",
    "巫",
    "乌",
    "焦",
    "巴",
    "弓",
    "牧",
    "隗",
    "山",
    "谷",
    "车",
    "侯",
    "宓",
    "蓬",
    "全",
    "郗",
    "班",
    "仰",
    "秋",
    "仲",
    "伊",
    "宫",
    "宁",
    "仇",
    "栾",
    "暴",
    "甘",
    "厉",
    "戎",
    "祖",
    "武",
    "符",
    "刘",
    "景",
    "詹",
    "束",
    "龙",
    "叶",
    "幸",
    "司",
    "韶",
    "郜",
    "黎",
    "蓟",
    "薄",
    "印",
    "宿",
    "白",
    "怀",
    "蒲",
    "台",
    "从",
    "鄂",
    "索",
    "咸",
    "籍",
    "赖",
    "卓",
    "蔺",
    "屠",
    "蒙",
    "池",
    "乔",
    "阴",
    "郁",
    "胥",
    "能",
    "苍",
    "双",
    "闻",
    "莘",
    "党",
    "翟",
    "谭",
    "贡",
    "劳",
    "逄",
    "姬",
    "申",
    "扶",
    "堵",
    "冉",
    "宰",
    "郦",
    "雍",
    "郤",
    "璩",
    "桑",
    "桂",
    "濮",
    "牛",
    "寿",
    "通",
    "边",
    "扈",
    "燕",
    "冀",
    "郏",
    "浦",
    "尚",
    "农",
    "温",
    "别",
    "庄",
    "晏",
    "柴",
    "瞿",
    "阎",
    "充",
    "慕",
    "连",
    "茹",
    "习",
    "宦",
    "艾",
    "鱼",
    "容",
    "向",
    "古",
    "易",
    "慎",
    "戈",
    "廖",
    "庾",
    "终",
    "暨",
    "居",
    "衡",
    "步",
    "都",
    "耿",
    "满",
    "弘",
    "匡",
    "国",
    "文",
    "寇",
    "广",
    "禄",
    "阙",
    "东郭",
    "南门",
    "呼延",
    "归海",
    "羊舌",
    "赫连",
    "澹台",
    "皇甫",
    "尉迟",
    "公羊",
    "公冶",
    "宗政",
    "濮阳",
    "淳于",
    "单于",
    "太叔",
    "申屠",
    "公孙",
    "仲孙",
    "轩辕",
    "令狐",
    "钟离",
    "宇文",
    "长孙",
    "慕容",
    "鲜于",
    "闾丘",
    "司徒",
    "司空",
    "丌官",
    "司寇",
    "子车",
    "颛孙",
    "端木",
    "巫马",
    "公西",
    "漆雕",
    "乐正",
    "壤驷",
    "公良",
    "拓跋",
    "夹谷",
    "宰父",
    "谷梁",
    "汝嫣",
    "东门",
    "西门",
    "南宫",
    "第五",
)
FEMALE_NAME_HINT_CHARS = frozenset("丽娜静敏艳娟婷颖雪倩芳琳洁欣怡蓉莹燕璐璇岚妍媛")
MALE_NAME_HINT_CHARS = frozenset("强伟磊军勇涛超鹏杰峰斌刚浩东博飞健志明龙宁凯晨亮")
ADDRESS_LEVEL_ORDER = (
    "province",
    "city",
    "district",
    "locality",
    "building",
    "unit",
    "floor",
    "room",
)
ADDRESS_REQUIRED_LOCALITY_KEYWORDS = tuple(
    dict.fromkeys((*COMMUNITY_SUFFIXES, "社区", "家园", "新村", "村", "屯", "组", "队"))
)


@dataclass
class HiddenSettingsRecord:
    scenario_id: str
    product: dict[str, Any]
    request_type: str
    generated_customer: dict[str, Any]
    generated_request: dict[str, Any]
    hidden_context: dict[str, Any]
    duplicate_rate: float
    max_similarity_score: float
    created_at: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class UserGenerationPlan:
    address_style: str
    address_instruction: str
    reply_noise_enabled: bool
    reply_noise_target: str
    reply_noise_rounds: int
    reply_noise_instruction: str


class HiddenSettingsRepository:
    def __init__(self, path: Path | None):
        self.path = path
        self._records: list[HiddenSettingsRecord] = []

    def load(self) -> list[HiddenSettingsRecord]:
        if self.path is None:
            return list(self._records)
        if not self.path.exists():
            return []

        records: list[HiddenSettingsRecord] = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            payload = json.loads(line)
            records.append(HiddenSettingsRecord(**payload))
        return records

    def append(self, record: HiddenSettingsRecord) -> None:
        if self.path is None:
            self._records.append(record)
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record.to_dict(), ensure_ascii=False) + "\n")


class HiddenSettingsSimilarity:
    @staticmethod
    def normalize_text(text: str) -> str:
        return re.sub(r"\s+", "", re.sub(r"[^\w\u4e00-\u9fff]", " ", text or "")).lower()

    @classmethod
    def ngrams(cls, text: str, n: int = 2) -> set[str]:
        normalized = cls.normalize_text(text)
        if not normalized:
            return set()
        if len(normalized) <= n:
            return {normalized}
        return {normalized[index : index + n] for index in range(len(normalized) - n + 1)}

    @classmethod
    def jaccard_similarity(cls, left: str, right: str) -> float:
        left_ngrams = cls.ngrams(left)
        right_ngrams = cls.ngrams(right)
        if not left_ngrams or not right_ngrams:
            return 0.0
        union = left_ngrams | right_ngrams
        if not union:
            return 0.0
        return len(left_ngrams & right_ngrams) / len(union)

    @staticmethod
    def duplicate_rate(candidate: dict[str, str], existing: dict[str, str]) -> float:
        matches = 0
        for field in VARIABLE_FIELDS:
            candidate_value = (candidate.get(field) or "").strip()
            existing_value = (existing.get(field) or "").strip()
            if candidate_value and existing_value and candidate_value == existing_value:
                matches += 1
        return matches / len(VARIABLE_FIELDS)

    @classmethod
    def overall_similarity(cls, candidate: dict[str, str], existing: dict[str, str]) -> float:
        comparisons = []
        for field in VARIABLE_FIELDS:
            candidate_value = (candidate.get(field) or "").strip()
            existing_value = (existing.get(field) or "").strip()
            if candidate_value and existing_value:
                comparisons.append(cls.jaccard_similarity(candidate_value, existing_value))
        if not comparisons:
            return 0.0
        return sum(comparisons) / len(comparisons)


class HiddenSettingsTool:
    def __init__(self, client: OpenAIChatClient, config: AppConfig):
        self.client = client
        self.config = config
        self.repository = HiddenSettingsRepository(config.hidden_settings_store)
        self._history_lock = asyncio.Lock()

    def generate_for_scenario(self, scenario: Scenario) -> Scenario:
        history = self.repository.load()
        rejection_feedback = ""

        for attempt in range(1, self.config.hidden_settings_max_attempts + 1):
            generation_plan = self._sample_user_generation_plan()
            payload = self.client.complete_json(
                model=self.config.user_agent_model,
                messages=self._build_messages(scenario, rejection_feedback, generation_plan),
                temperature=0.95,
            )
            try:
                candidate = self._normalize_generated_payload(
                    payload,
                    scenario.request.request_type,
                    scenario_id=scenario.scenario_id,
                )
            except ValueError as error:
                rejection_feedback = self._build_validation_feedback(attempt, str(error))
                continue
            self._attach_user_generation_plan(candidate, generation_plan)
            self._attach_second_round_reply_plan(scenario.scenario_id, candidate)
            self._attach_product_routing_plan(scenario, candidate)
            self._attach_contact_plan(scenario.scenario_id, candidate)
            self._attach_address_plan(scenario.scenario_id, candidate)
            self._attach_installation_plan(candidate)
            duplicate_rate, max_similarity_score, most_similar_record = self._score_candidate(
                scenario,
                candidate,
                history,
            )
            if (
                duplicate_rate <= self.config.hidden_settings_duplicate_threshold
                and max_similarity_score <= self.config.hidden_settings_similarity_threshold
            ):
                generated_scenario = scenario.with_generated_hidden_settings(
                    customer=CustomerProfile(**candidate["customer"]),
                    request=ServiceRequest(**candidate["request"]),
                    hidden_context=candidate["hidden_context"],
                )
                self.repository.append(
                    HiddenSettingsRecord(
                        scenario_id=generated_scenario.scenario_id,
                        product=generated_scenario.product.__dict__,
                        request_type=generated_scenario.request.request_type,
                        generated_customer=candidate["customer"],
                        generated_request=candidate["request"],
                        hidden_context=candidate["hidden_context"],
                        duplicate_rate=duplicate_rate,
                        max_similarity_score=max_similarity_score,
                        created_at=datetime.now(timezone.utc).isoformat(),
                    )
                )
                return generated_scenario

            rejection_feedback = self._build_rejection_feedback(
                attempt,
                duplicate_rate,
                max_similarity_score,
                most_similar_record,
            )

        raise ValueError(
            "Failed to generate sufficiently distinct hidden settings after "
            f"{self.config.hidden_settings_max_attempts} attempts."
        )

    async def generate_for_scenario_async(self, scenario: Scenario) -> Scenario:
        rejection_feedback = ""

        for attempt in range(1, self.config.hidden_settings_max_attempts + 1):
            async with self._history_lock:
                history = self.repository.load()

            generation_plan = self._sample_user_generation_plan()
            payload = await self._complete_json_async(
                model=self.config.user_agent_model,
                messages=self._build_messages(scenario, rejection_feedback, generation_plan),
                temperature=0.95,
            )
            try:
                candidate = self._normalize_generated_payload(
                    payload,
                    scenario.request.request_type,
                    scenario_id=scenario.scenario_id,
                )
            except ValueError as error:
                rejection_feedback = self._build_validation_feedback(attempt, str(error))
                continue
            self._attach_user_generation_plan(candidate, generation_plan)
            self._attach_second_round_reply_plan(scenario.scenario_id, candidate)
            self._attach_contact_plan(scenario.scenario_id, candidate)
            self._attach_address_plan(scenario.scenario_id, candidate)
            self._attach_installation_plan(candidate)

            async with self._history_lock:
                latest_history = self.repository.load()
                duplicate_rate, max_similarity_score, most_similar_record = self._score_candidate(
                    scenario,
                    candidate,
                    latest_history,
                )
                if (
                    duplicate_rate <= self.config.hidden_settings_duplicate_threshold
                    and max_similarity_score <= self.config.hidden_settings_similarity_threshold
                ):
                    generated_scenario = scenario.with_generated_hidden_settings(
                        customer=CustomerProfile(**candidate["customer"]),
                        request=ServiceRequest(**candidate["request"]),
                        hidden_context=candidate["hidden_context"],
                    )
                    self.repository.append(
                        HiddenSettingsRecord(
                            scenario_id=generated_scenario.scenario_id,
                            product=generated_scenario.product.__dict__,
                            request_type=generated_scenario.request.request_type,
                            generated_customer=candidate["customer"],
                            generated_request=candidate["request"],
                            hidden_context=candidate["hidden_context"],
                            duplicate_rate=duplicate_rate,
                            max_similarity_score=max_similarity_score,
                            created_at=datetime.now(timezone.utc).isoformat(),
                        )
                    )
                    return generated_scenario

            rejection_feedback = self._build_rejection_feedback(
                attempt,
                duplicate_rate,
                max_similarity_score,
                most_similar_record,
            )

        raise ValueError(
            "Failed to generate sufficiently distinct hidden settings after "
            f"{self.config.hidden_settings_max_attempts} attempts."
        )

    async def _complete_json_async(self, **kwargs: Any) -> dict[str, Any]:
        complete_json_async = getattr(self.client, "complete_json_async", None)
        if callable(complete_json_async):
            return await complete_json_async(**kwargs)
        return await asyncio.to_thread(self.client.complete_json, **kwargs)

    @staticmethod
    def _stable_prompt_seed(seed_text: str) -> int:
        normalized = str(seed_text or "").strip()
        if not normalized:
            return 0
        return sum((index + 1) * ord(char) for index, char in enumerate(normalized))

    @classmethod
    def _stable_sample_text_options(
        cls,
        options: tuple[str, ...],
        seed_text: str,
        count: int,
    ) -> tuple[str, ...]:
        unique_options = tuple(dict.fromkeys(str(option).strip() for option in options if str(option).strip()))
        if count <= 0 or not unique_options:
            return ()
        if count >= len(unique_options):
            return unique_options
        rng = random.Random(cls._stable_prompt_seed(seed_text))
        return tuple(rng.sample(list(unique_options), count))

    @classmethod
    def _sample_prompt_surname_examples(cls, scenario_id: str, count: int = 28) -> str:
        return "、".join(cls._stable_sample_text_options(SURNAME_OPTIONS, f"{scenario_id}:surname", count))

    @classmethod
    def _sample_prompt_region_examples(cls, scenario_id: str, count: int = 18) -> str:
        region_labels = tuple(
            f"{option['province']}{option['city']}{rng.choice(tuple(option.get('districts', ()) or ('',)))}"
            for rng, option in (
                (random.Random(cls._stable_prompt_seed(f"{scenario_id}:region:{index}")), option)
                for index, option in enumerate(COHERENT_REGION_OPTIONS + COHERENT_MUNICIPALITY_OPTIONS)
            )
        )
        return "；".join(cls._stable_sample_text_options(region_labels, f"{scenario_id}:region-sample", count))

    def _build_messages(
        self,
        scenario: Scenario,
        rejection_feedback: str,
        generation_plan: UserGenerationPlan,
    ) -> list[dict[str, str]]:
        product_name = str(scenario.product.category).strip() or "空气能热水器"
        surname_examples = self._sample_prompt_surname_examples(scenario.scenario_id)
        region_examples = self._sample_prompt_region_examples(scenario.scenario_id)
        system_prompt = f"""你是一个家电客服数据生成工具，负责给 user_agent 生成隐藏设定。

任务约束：
1. 只生成美的{product_name}的中文客服场景。
2. 生成的内容必须是用户视角隐藏信息，供 user_agent 使用。
3. 输出必须具体、自然、生活化，避免模板化和高相似复用。
4. 电话、地址、用户画像、问题细节、预约时间、历史尝试等都要有变化。
5. 用户画像与说话方式要拆开写，二者都要具体，方便塑造人物。
6. 大多数用户设定为普通家庭用户，文化程度和表达能力都比较一般，不要频繁生成过于精英、逻辑特别强或表达特别书面的角色。
7. 说话方式可以自然体现轻微停顿、重复、表达不够顺或想到哪说到哪，但不要夸张到影响理解，也不要刻板化描写。
8. 用户姓名和姓氏必须匹配；单姓用户的 full_name 必须以该姓开头，复姓用户也必须用真实复姓开头。
9. 姓氏和地址都要尽量打散，不要反复集中在“张、王、李、赵”和“广深杭苏”等少数高频选项。
10. 只返回一个 JSON 对象，不要解释。

输出 JSON 结构：
{{
  "customer": {{
    "full_name": "张三",
    "surname": "张",
    "phone": "13800000000",
    "address": "完整中文地址",
    "persona": "用户背景、性格、关注点等人物画像",
    "speech_style": "用户说话方式，如简短/啰嗦/条理清晰/略带停顿等"
  }},
  "request": {{
    "request_type": "fault 或 installation",
    "issue": "具体诉求描述",
    "desired_resolution": "希望客服帮助达成什么",
    "availability": "可预约时间"
  }},
  "hidden_context": {{
    "gender": "男 或 女",
    "emotion": "情绪状态",
    "urgency": "紧急程度",
    "prior_attempts": "此前是否做过处理或排查",
    "special_constraints": "上门限制、家庭情况或其他备注"
  }}
}}
"""
        user_prompt = f"""请基于以下产品骨架生成新的隐藏设定：

- 场景ID: {scenario.scenario_id}
- 品牌: {scenario.product.brand}
- 品类: {scenario.product.category}
- 型号: {scenario.product.model}
- 购买渠道: {scenario.product.purchase_channel or '未提供'}
- 诉求类型: {scenario.request.request_type}
- 标签: {", ".join(scenario.tags) or "无"}

生成要求：
- 生成的内容必须适合中文客服通话
- 用户信息必须完整，可直接用于后续对话
- 地址必须是合理的中国地址
- 地址地区必须在全国范围内随机取样，尽量覆盖不同省份、自治区、直辖市，不要反复只写东部沿海热门城市
- 地址必须至少落到小区/社区/村一级，不能只写“某医院隔壁”“某路口西南角”“后巷门面”这类纯地标或纯路口描述
- 当前地址形态要求: {generation_plan.address_instruction}
- 电话必须是 11 位中国大陆手机号
- `hidden_context.gender` 必须填写为“男”或“女”
- 故障场景下，大多数 issue 只写 1 个具体故障点，只保留一个核心现象
- 只有极少数场景可以写 2 个相关故障点，但不要扩展到第 3 个问题，也不要堆砌过多结果后果或温度对比数据
- 安装场景与故障场景要区分明显
- 用户画像与说话方式都要具体，且不要写成同一句的重复改写
- 大多数用户应更像普通来电用户，不要总写成创业者、高管、专家或表达特别流畅的人
- 姓氏请在大池中随机分散采样，允许常见姓、次常见姓、少见姓、复姓混用；除非有特别理由，不要连续生成相似姓氏
- 姓氏候选池示例（仅示例，不限于此）: {surname_examples}
- 全国地址地区池示例（仅示例，要求覆盖全国随机采样）: {region_examples}
- 本场景用户回复随机性要求: {generation_plan.reply_noise_instruction}
- 如果收到“与历史样本相似度过高”的反馈，说明这次生成和历史记录太像，需要整体换一版内容

{rejection_feedback}

请仅返回 JSON。"""
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

    def _normalize_generated_payload(
        self,
        payload: dict[str, Any],
        expected_request_type: str,
        scenario_id: str = "",
    ) -> dict[str, Any]:
        customer = payload.get("customer") or {}
        request = payload.get("request") or {}
        hidden_context = payload.get("hidden_context") or {}
        normalized_gender = self._normalize_gender(
            hidden_context.get("gender", ""),
            str(customer.get("full_name", "")).strip(),
        )
        normalized_hidden_context = {
            str(key): str(value).strip()
            for key, value in hidden_context.items()
            if str(key).strip() != "gender" and str(value).strip()
        }
        normalized_hidden_context["gender"] = normalized_gender

        normalized = {
            "customer": {
                "full_name": str(customer.get("full_name", "")).strip(),
                "surname": str(customer.get("surname", "")).strip(),
                "phone": self._normalize_mobile_phone(customer.get("phone", "")),
                "address": str(customer.get("address", "")).strip(),
                "persona": str(customer.get("persona", "")).strip(),
                "speech_style": str(customer.get("speech_style", "")).strip(),
            },
            "request": {
                "request_type": expected_request_type,
                "issue": str(request.get("issue", "")).strip(),
                "desired_resolution": str(request.get("desired_resolution", "")).strip(),
                "availability": str(request.get("availability", "")).strip(),
            },
            "hidden_context": normalized_hidden_context,
        }

        self._validate_name_consistency(
            normalized["customer"]["full_name"],
            normalized["customer"]["surname"],
        )
        self._validate_issue_description(
            normalized["request"]["issue"],
            normalized["request"]["request_type"],
            scenario_id=scenario_id,
        )
        self._validate_address_completeness(normalized["customer"]["address"])
        for group_name, group in normalized.items():
            if any(not value for value in group.values()) and group_name != "hidden_context":
                raise ValueError(f"Generated hidden settings missing required fields in {group_name}.")
        return normalized

    @staticmethod
    def _normalize_mobile_phone(raw_phone: Any) -> str:
        phone = str(raw_phone or "").strip()
        digits = re.sub(r"\D", "", phone)

        if digits.startswith("0086") and len(digits) > 11:
            digits = digits[4:]
        elif digits.startswith("86") and len(digits) > 11:
            digits = digits[2:]

        if not re.fullmatch(r"1[3-9]\d{9}", digits):
            raise ValueError("Generated hidden settings contain invalid phone number.")
        return digits

    @staticmethod
    def _validate_name_consistency(full_name: str, surname: str) -> None:
        normalized_full_name = str(full_name or "").strip()
        normalized_surname = str(surname or "").strip()
        if not normalized_full_name or not normalized_surname:
            raise ValueError("Generated hidden settings missing customer full_name or surname.")
        if not normalized_full_name.startswith(normalized_surname):
            raise ValueError("Generated hidden settings full_name must start with surname.")

    def _validate_issue_description(
        self,
        issue_text: str,
        request_type: str,
        scenario_id: str = "",
    ) -> None:
        issue = str(issue_text or "").strip()
        if not issue:
            raise ValueError("Generated hidden settings missing request issue.")
        if request_type != "fault":
            return
        symptom_count = self._count_fault_symptom_clauses(issue)
        if symptom_count <= 1:
            return
        if symptom_count > 2:
            raise ValueError("Generated hidden settings issue contains too many fault symptoms.")
        if not self._issue_allows_multi_fault(scenario_id, issue):
            raise ValueError("Generated hidden settings issue should usually describe only one fault symptom.")

    @classmethod
    def _validate_address_completeness(cls, address_text: str) -> None:
        address = str(address_text or "").strip()
        if not address:
            raise ValueError("Generated hidden settings missing address.")

        components = extract_address_components(address)
        normalized = re.sub(r"\s+", "", address)
        municipality_cities = {f"{value}市" for value in MUNICIPALITY_PREFIXES}
        if not components.city:
            raise ValueError("Generated hidden settings address must include city-level region.")
        if components.city not in municipality_cities and not components.province:
            raise ValueError("Generated hidden settings address must include province for non-municipality cities.")
        if not components.district:
            raise ValueError("Generated hidden settings address must include district/county-level region.")

        has_locality = bool(components.town or components.road or components.community)
        has_precise_detail = bool(components.building or components.unit or components.floor or components.room)
        has_house_number = bool(re.search(r"\d+\s*号(?!楼)", normalized))
        has_rural_detail = bool(re.search(r"(村|屯|组|队).*(\d+\s*号|[零一二三四五六七八九十两\d]+组)", normalized))
        has_required_locality_anchor = bool(
            components.community
            or any(keyword in normalized for keyword in ADDRESS_REQUIRED_LOCALITY_KEYWORDS)
        )
        has_poi_locality = bool(re.search(r"(医院|学校|酒店|饭店|园区|门店|商场|广场)", normalized))

        if not (has_locality or has_poi_locality):
            raise ValueError("Generated hidden settings address must include locality detail.")
        if not has_required_locality_anchor:
            raise ValueError(
                "Generated hidden settings address must reach a community- or village-level locality."
            )
        if not (has_precise_detail or has_house_number or has_rural_detail):
            raise ValueError("Generated hidden settings address must include precise locating detail.")

    @classmethod
    def _count_fault_symptom_clauses(cls, issue_text: str) -> int:
        normalized = re.sub(r"\s+", "", issue_text or "")
        if not normalized:
            return 0

        clauses = re.split(r"[，,；;。！？、]|(?:还有|而且|并且|同时|另外|又|还会|还总是|还老是)", normalized)
        symptom_pattern = re.compile(
            r"(故障码|报码|报错|报警|显示|不加热|不制热|没热水|热水不稳定|忽冷忽热|温度上不去|升温慢|制热慢|"
            r"热水.{0,6}(不稳定|不稳|不足|异常)|出水温度|水温.{0,6}(异常|不稳|过低|过高)|"
            r"热水.{0,6}(中断|出不来|没有|没了)|出水.{0,6}(常温|不热|偏冷)|达不到设定水温|"
            r"漏水|渗水|滴水|异响|噪音|嗡嗡|轰鸣|不启动|启动不了|无法启动|跳闸|断电|停机|不出热水)"
        )
        filler_pattern = re.compile(
            r"^(嗯|嗯嗯|是|是的|对|对的|哎对|好的|需要维修|来报修|报修|想报修|这个热水器|家里这个热水器)+$"
        )

        count = 0
        for clause in clauses:
            part = clause.strip()
            if not part or filler_pattern.fullmatch(part):
                continue
            if symptom_pattern.search(part):
                count += 1
        return count

    def _issue_allows_multi_fault(self, scenario_id: str, issue_text: str) -> bool:
        if not scenario_id or not issue_text:
            return False
        score = random.random()
        return score < self.config.hidden_settings_multi_fault_probability

    @staticmethod
    def _build_validation_feedback(attempt: int, error_message: str) -> str:
        return (
            "上一次输出不合规，不能直接使用。\n"
            f"- 第 {attempt} 次失败原因: {error_message}\n"
            "- 请重新生成完整 JSON。\n"
            "- 手机号必须是 11 位中国大陆手机号，只保留号码本体，不要附带备注、空格或分隔符。\n"
            "- 地址必须足够完整，至少带省/市/区县和可定位到上门位置的细节；不要只写小区名、路名或片段地址。\n"
            "- 地址必须至少落到小区/社区/村一级，不能只写医院隔壁、路口拐角、后巷门面这类纯地标描述。\n"
            "- 故障场景下，绝大多数 issue 只保留 1 个核心故障现象；只有极少数场景可写 2 个相关故障点。\n"
            "- 即使允许双故障点，也不要扩展到第 3 个问题，不要堆砌温度数据或过多后果描述。\n"
        )

    def _sample_user_generation_plan(self) -> UserGenerationPlan:
        rng = random.Random()
        address_style = self._sample_address_style(rng)
        reply_noise_target = ""
        reply_noise_rounds = 0
        reply_noise_instruction = "整体正常配合客服，绝大多数轮次直接按问答题回答，不需要刻意答非所问。"
        reply_noise_target = self._sample_probability_choice(
            rng,
            self._reply_noise_target_probabilities(),
        )
        reply_noise_enabled = bool(reply_noise_target)
        if reply_noise_enabled:
            reply_noise_rounds = self._sample_weighted_round_count(
                rng,
                self.config.user_reply_off_topic_rounds_weights,
            )
            reply_noise_rounds = self._cap_reply_noise_rounds_for_target(
                reply_noise_target,
                reply_noise_rounds,
            )
            if reply_noise_target:
                reply_noise_instruction = self._reply_noise_instruction_for_target(
                    reply_noise_target,
                    reply_noise_rounds,
                )
            else:
                reply_noise_enabled = False

        return UserGenerationPlan(
            address_style=address_style,
            address_instruction=self._address_instruction_for_style(address_style),
            reply_noise_enabled=reply_noise_enabled,
            reply_noise_target=reply_noise_target,
            reply_noise_rounds=reply_noise_rounds,
            reply_noise_instruction=reply_noise_instruction,
        )

    @staticmethod
    def _cap_reply_noise_rounds_for_target(target: str, rounds: int) -> int:
        normalized_target = str(target or "").strip()
        bounded_rounds = max(1, int(rounds))
        if normalized_target.startswith("phone_") or normalized_target.startswith("address_"):
            return bounded_rounds
        return min(bounded_rounds, 2)

    def _sample_address_style(self, rng: random.Random) -> str:
        if rng.random() >= self.config.user_address_nonstandard_probability:
            return "standard_residential"
        styles = list(self.config.user_address_nonstandard_style_weights.keys())
        weights = [max(0.0, float(self.config.user_address_nonstandard_style_weights[style])) for style in styles]
        if not styles:
            return "standard_residential"
        if sum(weights) <= 0:
            weights = [1.0] * len(styles)
        return rng.choices(styles, weights=weights, k=1)[0]

    @staticmethod
    def _address_instruction_for_style(address_style: str) -> str:
        instructions = {
            "standard_residential": "生成标准小区/公寓住宅地址，通常包含小区、楼栋、单元、楼层或室号。",
            "house_number_only": "生成可定位但不一定有栋单元室的地址，但主体仍要落到小区/社区/家园/花园/村等一级名称，再补明确门牌号，例如“幸福家园134号”“康乐社区东门旁62号”。",
            "rural_group_number": "生成乡镇/村/组/号这类乡村地址，必须明确到村一级或组一级，不要只写镇上某路口。",
            "landmark_poi": "可以围绕医院、饭店、酒店、学校、产业园、门店等地标来描述，但主体仍必须落到小区/社区/村一级地址，地标只能作辅助定位，不要只写路口或某地标隔壁门面。",
        }
        return instructions.get(address_style, instructions["standard_residential"])

    @staticmethod
    def _sample_weighted_choice(
        rng: random.Random,
        weights_map: dict[str, float],
    ) -> str:
        choices = [str(key).strip() for key in weights_map if str(key).strip()]
        if not choices:
            return ""
        weights = [max(0.0, float(weights_map.get(choice, 0.0))) for choice in choices]
        if sum(weights) <= 0:
            weights = [1.0] * len(choices)
        return rng.choices(choices, weights=weights, k=1)[0]

    @staticmethod
    def _sample_probability_choice(
        rng: random.Random,
        probability_map: dict[str, float],
    ) -> str:
        threshold = rng.random()
        cumulative = 0.0
        for choice, probability in probability_map.items():
            cumulative += max(0.0, float(probability))
            if threshold < cumulative:
                return choice
        return ""

    def _reply_noise_target_probabilities(self) -> dict[str, float]:
        base_probability = max(0.0, min(1.0, float(self.config.user_reply_off_topic_probability)))
        probabilities: dict[str, float] = {}
        for target, coefficient in self.config.user_reply_off_topic_target_weights.items():
            normalized_target = str(target).strip()
            coefficient_value = max(0.0, float(coefficient))
            if not normalized_target or coefficient_value <= 0.0:
                continue
            probabilities[normalized_target] = coefficient_value * base_probability
        return probabilities

    @staticmethod
    def _sample_weighted_round_count(
        rng: random.Random,
        weights_map: dict[str, float],
    ) -> int:
        selected = HiddenSettingsTool._sample_weighted_choice(rng, weights_map)
        try:
            return max(1, int(selected))
        except ValueError:
            return 1

    @staticmethod
    def _reply_noise_instruction_for_target(target: str, rounds: int) -> str:
        rounds = max(1, int(rounds))
        round_scope = "第 1 次" if rounds == 1 else f"前 {rounds} 次"
        instructions = {
            "opening_confirmation": f"允许在{round_scope}回应开场确认时轻微答偏，例如先确认再顺带补一句背景，但不要连续复读同一诉求；超过配置轮数后恢复正常简短确认。",
            "issue_description": f"允许在{round_scope}被问故障或安装诉求时先说得不完全到位，例如先说影响感受或场景，再补核心问题；超过配置轮数后要直接回答核心诉求。",
            "surname_collection": f"允许在{round_scope}被问姓氏时先用更生活化的答法，比如报全名或“我姓王，叫王家俊”，但不要扯到无关内容；超过配置轮数后直接给姓氏。",
            "phone_contact_confirmation": f"允许在{round_scope}被问当前号码是否能联系时先给一句生活化解释，但当轮必须明确回答能或不能；不要提前说“待会输入号码”“等会再报号码”这类后续流程话。超过配置轮数后直接回答能或不能。",
            "phone_keypad_input": f"允许在{round_scope}被要求拨号盘输入号码时出现轻微不规范输入，但不能离题；超过配置轮数后严格只输出正确按键内容。",
            "phone_confirmation": f"允许在{round_scope}核对号码时先口语化确认或否认，但不要重复扯回别的话题；超过配置轮数后只简短回答对或不对。",
            "address_collection": f"允许在{round_scope}被问地址时先轻微答偏，例如只说到区域、先反问一句，或只补一部分地址；超过配置轮数后按地址计划正常补齐，不要反复复读同一句。",
            "address_confirmation": f"允许在{round_scope}核对地址时先口语化否认或补一小段更正，但不要一直重复同一片段；超过配置轮数后直接明确确认或更正。",
            "product_arrival_confirmation": f"允许在{round_scope}被问到货情况时先给轻微不完全对题的自然回答，例如只说物流进度或模糊时间；超过配置轮数后明确回答是否到货。",
            "product_model_collection": f"允许在{round_scope}被问型号时先说购买渠道、外观或模糊记忆，但不能一直绕开；超过配置轮数后尽量直接给型号。",
            "closing_acknowledgement": f"允许在{round_scope}收尾确认时先补一句感谢或催促，但不要重新展开旧信息；超过配置轮数后只简短确认。",
        }
        return instructions.get(
            target,
            "整体正常配合客服，绝大多数轮次直接按问答题回答，不需要刻意答非所问。",
        )

    @staticmethod
    def _attach_user_generation_plan(candidate: dict[str, Any], generation_plan: UserGenerationPlan) -> None:
        candidate["hidden_context"].update(
            {
                "user_address_style": generation_plan.address_style,
                "user_address_style_instruction": generation_plan.address_instruction,
                "user_reply_noise_enabled": generation_plan.reply_noise_enabled,
                "user_reply_noise_target": generation_plan.reply_noise_target,
                "user_reply_noise_rounds": generation_plan.reply_noise_rounds,
                "user_reply_noise_instruction": generation_plan.reply_noise_instruction,
            }
        )

    def _attach_second_round_reply_plan(self, scenario_id: str, candidate: dict[str, Any]) -> None:
        candidate["hidden_context"]["second_round_reply_strategy"] = decide_second_round_reply_strategy(
            scenario_id,
            self.config.second_round_include_issue_probability,
        )

    def _attach_product_routing_plan(self, scenario: Scenario, candidate: dict[str, Any]) -> None:
        hidden_context = candidate["hidden_context"]
        ensure_product_routing_plan(
            hidden_context,
            enabled=self.config.product_routing_enabled,
            apply_probability=self.config.product_routing_apply_probability,
            model_hint=scenario.product.model,
            rng=random.Random(),
        )

    def _attach_contact_plan(self, scenario_id: str, candidate: dict[str, Any]) -> None:
        rng = random.Random()
        current_call_contactable = (
            rng.random() < self.config.current_call_contactable_probability
        )
        primary_phone = candidate["customer"]["phone"]

        if current_call_contactable:
            candidate["hidden_context"].update(
                {
                    "current_call_contactable": True,
                    "contact_phone_owner": "本人当前来电",
                    "contact_phone_owner_spoken_label": "我这个号码",
                    "contact_phone": primary_phone,
                    "phone_input_attempts_required": 0,
                    "phone_input_round_1": f"{primary_phone}#",
                    "phone_input_round_2": f"{primary_phone}#",
                    "phone_input_round_3": f"{primary_phone}#",
                }
            )
            return

        backup_owner = rng.choices(
            population=["本人备用号码", "爱人", "爸", "妈", "儿子", "女儿", "室友"],
            weights=[20, 15, 15, 15, 12.5, 12.5, 10],
            k=1,
        )[0]
        backup_phone = self._generate_mobile_phone(rng, excluded={primary_phone})
        if self.config.phone_collection_third_attempt_probability >= 1.0:
            attempts_required = 3
        elif self.config.phone_collection_second_attempt_probability >= 1.0:
            attempts_required = 2
        elif rng.random() < self.config.phone_collection_third_attempt_probability:
            attempts_required = 3
        elif rng.random() < self.config.phone_collection_second_attempt_probability:
            attempts_required = 2
        else:
            attempts_required = 1
        first_input = (
            self._generate_invalid_phone_input(rng, backup_phone)
            if attempts_required >= 2
            else f"{backup_phone}#"
        )
        second_input = (
            self._generate_invalid_phone_input(rng, backup_phone)
            if attempts_required >= 3
            else f"{backup_phone}#"
        )
        spoken_label = self._pick_contact_phone_owner_spoken_label(
            backup_owner,
            candidate["customer"].get("full_name", ""),
            candidate["hidden_context"].get("gender", ""),
        )

        candidate["hidden_context"].update(
            {
                "current_call_contactable": False,
                "contact_phone_owner": backup_owner,
                "contact_phone_owner_spoken_label": spoken_label,
                "contact_phone": backup_phone,
                "phone_input_attempts_required": attempts_required,
                "phone_input_round_1": first_input,
                "phone_input_round_2": second_input,
                "phone_input_round_3": f"{backup_phone}#",
            }
        )

    def _attach_address_plan(self, scenario_id: str, candidate: dict[str, Any]) -> None:
        rng = random.Random()
        actual_address = candidate["customer"]["address"]
        service_knows_address = rng.random() < self.config.service_known_address_probability
        address_round_1 = actual_address
        address_round_2 = actual_address
        service_known_address_value = ""
        service_known_address_matches_actual = False
        address_confirmation_no_reply = "不对。"
        service_known_address_mismatch_start_level = ""
        service_known_address_rewrite_levels: list[str] = []
        service_known_address_rewrite_end_level = ""
        mismatch_correction_value = actual_address

        if service_knows_address:
            service_known_address_matches_actual = (
                rng.random() < self.config.service_known_address_matches_probability
            )
            if service_known_address_matches_actual:
                service_known_address_value = actual_address
            else:
                (
                    service_known_address_value,
                    service_known_address_mismatch_start_level,
                    mismatch_correction_value,
                    service_known_address_rewrite_levels,
                    service_known_address_rewrite_end_level,
                ) = self._build_known_address_mismatch_plan(actual_address, rng)
            if not service_known_address_matches_actual:
                if rng.random() < self.config.address_confirmation_direct_correction_probability:
                    correction_address = mismatch_correction_value
                    correction_address = self._maybe_compact_address_input(
                        correction_address,
                        rng,
                    )
                    address_confirmation_no_reply = rng.choice(
                        [
                            f"不对，应该是{correction_address}。",
                            f"不是，应该是{correction_address}。",
                            f"不对，是{correction_address}。",
                            f"不是这个，是{correction_address}。",
                            f"不对，改成{correction_address}。",
                            f"不是，得是{correction_address}。",
                        ]
                    )
                else:
                    address_confirmation_no_reply = rng.choice(
                        [
                            "不对，不是这个地址。",
                            "不对，地址不对。",
                            "不是这个地址。",
                        ]
                    )

        should_force_full_address_after_known_mismatch = (
            service_knows_address and not service_known_address_matches_actual
        )
        address_rounds = [actual_address]
        if should_force_full_address_after_known_mismatch:
            address_rounds = [mismatch_correction_value]
        elif rng.random() < self.config.address_collection_followup_probability:
            address_rounds = build_address_progressive_segments(
                actual_address,
                rng,
                round_weights=self.config.address_segment_rounds_weights,
                segment_2_strategy_weights=self.config.address_segment_2_strategy_weights,
                segment_3_strategy_weights=self.config.address_segment_3_strategy_weights,
                segment_4_strategy_weights=self.config.address_segment_4_strategy_weights,
            )

        compacted_address_rounds = [
            self._maybe_compact_address_input(round_text, rng)
            for round_text in address_rounds
        ]
        if compacted_address_rounds:
            address_round_1 = compacted_address_rounds[0]
            address_round_2 = compacted_address_rounds[min(1, len(compacted_address_rounds) - 1)]
            address_round_3 = compacted_address_rounds[min(2, len(compacted_address_rounds) - 1)]
            address_round_4 = compacted_address_rounds[min(3, len(compacted_address_rounds) - 1)]
        else:
            compacted_address_rounds = [actual_address]
            address_round_1 = actual_address
            address_round_2 = actual_address
            address_round_3 = actual_address
            address_round_4 = actual_address

        candidate["hidden_context"].update(
            {
                "service_known_address": service_knows_address,
                "service_known_address_value": service_known_address_value,
                "service_known_address_matches_actual": service_known_address_matches_actual,
                "service_known_address_mismatch_start_level": service_known_address_mismatch_start_level,
                "service_known_address_rewrite_levels": service_known_address_rewrite_levels,
                "service_known_address_rewrite_end_level": service_known_address_rewrite_end_level,
                "service_known_address_correction_value": mismatch_correction_value,
                "address_confirmation_no_reply": address_confirmation_no_reply,
                "address_input_round_1": address_round_1,
                "address_input_round_2": address_round_2,
                "address_input_round_3": address_round_3,
                "address_input_round_4": address_round_4,
                "address_input_rounds": compacted_address_rounds,
            }
        )

    def _attach_installation_plan(self, candidate: dict[str, Any]) -> None:
        if candidate["request"]["request_type"] != "installation":
            return
        candidate["hidden_context"]["product_arrived"] = (
            "yes" if self._infer_product_arrived(candidate["request"]["issue"]) else "no"
        )

    def _flatten_candidate(self, candidate: dict[str, Any]) -> dict[str, str]:
        return {
            "full_name": candidate["customer"]["full_name"],
            "surname": candidate["customer"]["surname"],
            "phone": candidate["customer"]["phone"],
            "address": candidate["customer"]["address"],
            "persona": candidate["customer"]["persona"],
            "speech_style": candidate["customer"]["speech_style"],
            "issue": candidate["request"]["issue"],
            "desired_resolution": candidate["request"]["desired_resolution"],
            "availability": candidate["request"]["availability"],
            "emotion": candidate["hidden_context"].get("emotion", ""),
            "urgency": candidate["hidden_context"].get("urgency", ""),
            "prior_attempts": candidate["hidden_context"].get("prior_attempts", ""),
            "special_constraints": candidate["hidden_context"].get("special_constraints", ""),
        }

    def _flatten_record(self, record: HiddenSettingsRecord) -> dict[str, str]:
        return {
            "full_name": record.generated_customer.get("full_name", ""),
            "surname": record.generated_customer.get("surname", ""),
            "phone": record.generated_customer.get("phone", ""),
            "address": record.generated_customer.get("address", ""),
            "persona": record.generated_customer.get("persona", ""),
            "speech_style": record.generated_customer.get("speech_style", ""),
            "issue": record.generated_request.get("issue", ""),
            "desired_resolution": record.generated_request.get("desired_resolution", ""),
            "availability": record.generated_request.get("availability", ""),
            "emotion": record.hidden_context.get("emotion", ""),
            "urgency": record.hidden_context.get("urgency", ""),
            "prior_attempts": record.hidden_context.get("prior_attempts", ""),
            "special_constraints": record.hidden_context.get("special_constraints", ""),
        }

    def _score_candidate(
        self,
        scenario: Scenario,
        candidate: dict[str, Any],
        history: list[HiddenSettingsRecord],
    ) -> tuple[float, float, HiddenSettingsRecord | None]:
        filtered_history = [
            record
            for record in history
            if record.product.get("brand") == scenario.product.brand
            and record.product.get("category") == scenario.product.category
            and record.request_type == candidate["request"]["request_type"]
        ]
        if not filtered_history:
            return 0.0, 0.0, None

        flattened_candidate = self._flatten_candidate(candidate)
        max_duplicate_rate = 0.0
        max_similarity_score = 0.0
        most_similar_record: HiddenSettingsRecord | None = None

        for record in filtered_history:
            flattened_record = self._flatten_record(record)
            duplicate_rate = HiddenSettingsSimilarity.duplicate_rate(
                flattened_candidate,
                flattened_record,
            )
            similarity_score = HiddenSettingsSimilarity.overall_similarity(
                flattened_candidate,
                flattened_record,
            )
            if similarity_score > max_similarity_score:
                max_similarity_score = similarity_score
                most_similar_record = record
            if duplicate_rate > max_duplicate_rate:
                max_duplicate_rate = duplicate_rate

        return max_duplicate_rate, max_similarity_score, most_similar_record

    def _build_rejection_feedback(
        self,
        attempt: int,
        duplicate_rate: float,
        similarity_score: float,
        most_similar_record: HiddenSettingsRecord | None,
    ) -> str:
        if not most_similar_record:
            return ""
        return (
            f"上一次生成在第 {attempt} 次尝试中被拒绝。\n"
            f"原因：与历史样本相似度过高，duplicate_rate={duplicate_rate:.3f}, similarity_score={similarity_score:.3f}。\n"
            "请重新生成一版差异明显的新设定。\n"
            "请显著拉开以下字段差异：姓名、地址、用户画像、说话方式、问题细节、预约时间、既往处理、上门限制。\n"
            "不要复述历史样本内容，不要解释原因，只返回新的 JSON。"
        )

    @staticmethod
    def _generate_mobile_phone(
        rng: random.Random,
        excluded: set[str] | None = None,
    ) -> str:
        excluded = excluded or set()
        prefixes = [
            "133",
            "135",
            "136",
            "137",
            "138",
            "139",
            "150",
            "151",
            "152",
            "157",
            "158",
            "159",
            "186",
            "187",
            "188",
            "189",
        ]
        while True:
            phone = f"{rng.choice(prefixes)}{rng.randint(0, 99999999):08d}"
            if phone not in excluded:
                return phone

    def _generate_invalid_phone_input(self, rng: random.Random, valid_phone: str) -> str:
        variants = [
            lambda: f"{valid_phone[:-1]}#",
            lambda: f"{valid_phone}{rng.randint(0, 9)}#",
            lambda: f"2{valid_phone[1:]}#",
            lambda: self._generate_digit_mismatch_phone_input(rng, valid_phone),
        ]
        weights = [
            max(0.0, self.config.phone_collection_invalid_short_probability),
            max(0.0, self.config.phone_collection_invalid_long_probability),
            max(0.0, self.config.phone_collection_invalid_pattern_probability),
            max(0.0, self.config.phone_collection_invalid_digit_mismatch_probability),
        ]
        if sum(weights) <= 0:
            weights = [1.0, 1.0, 1.0, 1.0]

        candidate = rng.choices(variants, weights=weights, k=1)[0]()
        digits = re.sub(r"\D", "", candidate)
        digit_difference_count = sum(
            expected != actual for expected, actual in zip(valid_phone, digits)
        )
        is_digit_mismatch_variant = (
            len(digits) == len(valid_phone)
            and digits != valid_phone
            and digit_difference_count in (1, 2)
        )
        if candidate == f"{valid_phone}#" or (
            re.fullmatch(r"1[3-9]\d{9}#", candidate) and not is_digit_mismatch_variant
        ):
            raise AssertionError(f"Generated phone input should be invalid: {candidate}")
        return candidate

    @staticmethod
    def _generate_digit_mismatch_phone_input(rng: random.Random, valid_phone: str) -> str:
        digits = list(valid_phone)
        mismatch_count = rng.choice((1, 2))
        mismatch_indexes = rng.sample(range(3, len(digits)), k=mismatch_count)
        for index in mismatch_indexes:
            replacement_choices = [digit for digit in "0123456789" if digit != digits[index]]
            digits[index] = rng.choice(replacement_choices)
        return f"{''.join(digits)}#"

    @staticmethod
    def _generate_partial_address(address: str) -> str:
        patterns = [
            r"\d+室.*$",
            r"\d+单元.*$",
            r"\d+栋.*$",
            r"\d+幢.*$",
            r"\d+号\d*室.*$",
            r"\d+号楼.*$",
        ]
        for pattern in patterns:
            partial = re.sub(pattern, "", address)
            if partial != address and partial.strip():
                return partial.strip(" ，,。")
        return address[: max(6, len(address) // 2)].strip(" ，,。")

    @staticmethod
    def _generate_detail_address(address: str) -> str:
        split_patterns = [
            r".*?(?<=街道)",
            r".*?(?<=镇)",
            r".*?(?<=乡)",
            r".*?(?<=区)",
            r".*?(?<=县)",
        ]
        for pattern in split_patterns:
            match = re.match(pattern, address)
            if match:
                detail = address[match.end() :].strip(" ，,。")
                if detail:
                    return detail
        return address[max(0, len(address) // 2) :].strip(" ，,。")

    def _maybe_compact_address_input(self, address: str, rng: random.Random) -> str:
        if not address:
            return address
        if rng.random() >= self.config.address_input_omit_province_city_suffix_probability:
            return address
        compact = self._omit_province_city_suffixes(address)
        return compact or address

    @staticmethod
    def _omit_province_city_suffixes(address: str) -> str:
        compact = str(address or "").strip()
        if not compact:
            return compact

        provinces = (
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
            "台湾",
        )
        municipalities = ("北京", "上海", "天津", "重庆")

        for municipality in municipalities:
            if compact.startswith(f"{municipality}市"):
                return f"{municipality}{compact[len(municipality) + 1:]}"

        province_prefix = next(
            (
                province
                for province in provinces
                if compact.startswith(f"{province}省") or compact.startswith(province)
            ),
            "",
        )
        if province_prefix:
            remainder = compact[len(province_prefix) :]
            if remainder.startswith("省"):
                remainder = remainder[1:]
            remainder = re.sub(r"^([^市区县]{2,9})市", r"\1", remainder, count=1)
            return f"{province_prefix}{remainder}"

        return re.sub(r"^([^市区县]{2,9})市", r"\1", compact, count=1)

    @staticmethod
    def _generate_stale_address(address: str, rng: random.Random) -> str:
        if rng.random() < 0.3:
            region_stale = HiddenSettingsTool._generate_region_stale_address(address, rng)
            if region_stale != address:
                return region_stale
        substitutions = [
            (r"(\d{1,4})室", lambda m: f"{max(1, int(m.group(1)) + rng.choice([1, 2, 3]))}室"),
            (r"(\d{1,3})单元", lambda m: f"{max(1, int(m.group(1)) + 1)}单元"),
            (r"(\d{1,3})栋", lambda m: f"{max(1, int(m.group(1)) + 1)}栋"),
            (r"(\d{1,3})幢", lambda m: f"{max(1, int(m.group(1)) + 1)}幢"),
            (r"(\d{1,4})号", lambda m: f"{max(1, int(m.group(1)) + 2)}号"),
        ]
        for pattern, replacer in substitutions:
            if re.search(pattern, address):
                return re.sub(pattern, replacer, address, count=1)
        numeric_matches = list(re.finditer(r"\d+", address))
        if numeric_matches:
            last_match = numeric_matches[-1]
            original = int(last_match.group(0))
            replacement = str(max(1, original + rng.choice([1, 2, 3])))
            return (
                address[: last_match.start()]
                + replacement
                + address[last_match.end() :]
            )
        return f"{address}1号"

    def _build_known_address_mismatch_plan(
        self,
        actual_address: str,
        rng: random.Random,
    ) -> tuple[str, str, str, list[str], str]:
        start_level = self._choose_address_mismatch_start_level(actual_address, rng)
        rewrite_levels = self._choose_address_mismatch_rewrite_levels(
            actual_address,
            start_level,
            rng,
        )
        stale_address = self._generate_stale_address_for_levels(
            actual_address,
            rewrite_levels or [start_level],
            rng,
        )
        correction_value = self._address_text_from_levels(actual_address, rewrite_levels)
        if stale_address == actual_address or not correction_value:
            fallback_stale = self._generate_stale_address(actual_address, rng)
            fallback_start_level = self._infer_mismatch_start_level(actual_address, fallback_stale)
            fallback_rewrite_levels = self._infer_mismatch_rewrite_levels(
                actual_address,
                fallback_stale,
            )
            fallback_correction = self._address_text_from_levels(
                actual_address,
                fallback_rewrite_levels,
            )
            if not fallback_correction:
                fallback_correction = self._generate_address_correction(
                    actual_address=actual_address,
                    stale_address=fallback_stale,
                    rng=rng,
                )
            return (
                fallback_stale,
                fallback_start_level,
                fallback_correction,
                fallback_rewrite_levels,
                fallback_rewrite_levels[-1] if fallback_rewrite_levels else fallback_start_level,
            )
        return (
            stale_address,
            start_level,
            correction_value,
            rewrite_levels,
            rewrite_levels[-1] if rewrite_levels else start_level,
        )

    def _generate_stale_address_for_levels(
        self,
        actual_address: str,
        levels: list[str],
        rng: random.Random,
    ) -> str:
        stale_address = actual_address
        for level in levels:
            next_stale = self._generate_stale_address_from_level(stale_address, level, rng)
            if next_stale != stale_address:
                stale_address = next_stale
        return stale_address

    def _choose_address_mismatch_start_level(
        self,
        actual_address: str,
        rng: random.Random,
    ) -> str:
        components = extract_address_components(actual_address)
        available_levels = [
            level
            for level in ("province", "city", "district", "locality", "building", "unit", "floor", "room")
            if self._address_level_is_available(level, components)
        ]
        if not available_levels:
            return "room"
        weights = self.config.address_known_mismatch_start_level_weights
        level_weights = [max(0.0, float(weights.get(level, 0.0))) for level in available_levels]
        if sum(level_weights) <= 0:
            level_weights = [1.0] * len(available_levels)
        return rng.choices(available_levels, weights=level_weights, k=1)[0]

    def _choose_address_mismatch_rewrite_levels(
        self,
        actual_address: str,
        start_level: str,
        rng: random.Random,
    ) -> list[str]:
        components = extract_address_components(actual_address)
        try:
            start_index = ADDRESS_LEVEL_ORDER.index(start_level)
        except ValueError:
            return [start_level]

        available_levels = [
            level
            for level in ADDRESS_LEVEL_ORDER[start_index:]
            if self._address_level_is_available(level, components)
        ]
        if not available_levels:
            return [start_level]
        if start_level in {"province", "city", "district", "locality"}:
            return available_levels

        weights = self.config.address_known_mismatch_rewrite_end_level_weights
        end_level_weights = [max(0.0, float(weights.get(level, 0.0))) for level in available_levels]
        if sum(end_level_weights) <= 0:
            end_level_weights = [1.0] * len(available_levels)
        end_level = rng.choices(available_levels, weights=end_level_weights, k=1)[0]
        end_index = ADDRESS_LEVEL_ORDER.index(end_level)
        return [
            level
            for level in ADDRESS_LEVEL_ORDER[start_index : end_index + 1]
            if self._address_level_is_available(level, components)
        ] or [start_level]

    @staticmethod
    def _address_level_is_available(level: str, components: Any) -> bool:
        if level == "province":
            return bool(components.province)
        if level == "city":
            return bool(components.city)
        if level == "district":
            return bool(components.district)
        if level == "locality":
            return bool(components.town or components.road or components.community)
        if level == "building":
            return bool(components.building)
        if level == "unit":
            return bool(components.unit)
        if level == "floor":
            return bool(components.floor)
        if level == "room":
            return bool(components.room)
        return False

    @classmethod
    def _address_level_values(cls, address: str) -> dict[str, str]:
        components = extract_address_components(address)
        return {
            "province": components.province,
            "city": components.city,
            "district": components.district,
            "locality": "".join(part for part in (components.town, components.road, components.community) if part),
            "building": components.building,
            "unit": components.unit,
            "floor": components.floor,
            "room": components.room,
        }

    @classmethod
    def _address_text_from_levels(cls, address: str, levels: list[str]) -> str:
        if not levels:
            return address
        level_values = cls._address_level_values(address)
        selected_levels = set(levels)
        text = "".join(
            level_values[level]
            for level in ADDRESS_LEVEL_ORDER
            if level in selected_levels and level_values[level]
        )
        return text or address

    def _generate_stale_address_from_level(
        self,
        actual_address: str,
        level: str,
        rng: random.Random,
    ) -> str:
        if level in {"province", "city", "district"}:
            stale = self._generate_region_stale_address_from_level(actual_address, level, rng)
            if stale != actual_address:
                return stale
        if level == "locality":
            stale = self._generate_locality_stale_address(actual_address, rng)
            if stale != actual_address:
                return stale
        detail_stale = self._generate_detail_stale_address(actual_address, level, rng)
        return detail_stale if detail_stale != actual_address else self._generate_stale_address(actual_address, rng)

    @staticmethod
    def _region_options_for_address(address: str) -> tuple[dict[str, Any], ...]:
        components = extract_address_components(address)
        if components.province:
            return COHERENT_REGION_OPTIONS
        return COHERENT_MUNICIPALITY_OPTIONS

    @classmethod
    def _generate_region_stale_address_from_level(
        cls,
        actual_address: str,
        level: str,
        rng: random.Random,
    ) -> str:
        components = extract_address_components(actual_address)
        options = cls._region_options_for_address(actual_address)
        if level == "province":
            candidates = [
                option
                for option in options
                if str(option.get("province", "")) and option.get("province") != components.province
            ]
            if not candidates:
                return actual_address
            replacement = rng.choice(candidates)
            stale = actual_address.replace(components.province, str(replacement["province"]), 1)
            stale = stale.replace(components.city, str(replacement["city"]), 1)
            if components.district:
                stale = stale.replace(components.district, str(rng.choice(tuple(replacement["districts"]))), 1)
            return stale

        if level == "city":
            if components.province:
                candidates = [
                    option
                    for option in options
                    if option.get("province") == components.province and option.get("city") != components.city
                ]
            else:
                candidates = [option for option in options if option.get("city") != components.city]
            if not candidates:
                return actual_address
            replacement = rng.choice(candidates)
            stale = actual_address.replace(components.city, str(replacement["city"]), 1)
            if components.district:
                stale = stale.replace(components.district, str(rng.choice(tuple(replacement["districts"]))), 1)
            return stale

        if level == "district":
            candidates = [
                district
                for option in options
                if option.get("province", "") == components.province and option.get("city") == components.city
                for district in tuple(option.get("districts", ()))
                if district != components.district
            ]
            if not candidates:
                return actual_address
            return actual_address.replace(components.district, str(rng.choice(candidates)), 1)

        return actual_address

    @staticmethod
    def _replace_first(address: str, pattern: str, replacement: str) -> str:
        return re.sub(pattern, replacement, address, count=1)

    @classmethod
    def _generate_locality_stale_address(cls, actual_address: str, rng: random.Random) -> str:
        stale = actual_address
        components = extract_address_components(actual_address)
        if components.community:
            pool = ["幸福花园", "阳光花园", "金色家园", "滨江花园", "锦绣苑", "星辰花园"]
            alternatives = [value for value in pool if value != components.community]
            if alternatives:
                return stale.replace(components.community, rng.choice(alternatives), 1)

        road_number_match = re.search(r"([^\d]{1,20}(?:路|街|大道|巷|弄|胡同))(\d+)号", components.road)
        if road_number_match and components.road:
            prefix = road_number_match.group(1)
            number = int(road_number_match.group(2))
            replacement = f"{prefix}{number + rng.choice([2, 4, 6])}号"
            return stale.replace(components.road, replacement, 1)

        if components.town:
            pool = ["东城街道", "五常街道", "安宜镇", "大良街道", "观音桥街道"]
            alternatives = [value for value in pool if value != components.town]
            if alternatives:
                return stale.replace(components.town, rng.choice(alternatives), 1)
        return actual_address

    @classmethod
    def _generate_detail_stale_address(
        cls,
        actual_address: str,
        level: str,
        rng: random.Random,
    ) -> str:
        patterns = {
            "building": r"(\d+)\s*(号楼|栋|幢|座|楼)",
            "unit": r"(\d+)\s*(单元)",
            "floor": r"(\d+)\s*(层)",
            "room": r"(\d{2,4})\s*(室)",
        }
        pattern = patterns.get(level)
        if not pattern:
            return actual_address
        match = re.search(pattern, actual_address)
        if not match:
            return actual_address
        replacement = f"{max(1, int(match.group(1)) + rng.choice([1, 2, 3]))}{match.group(2)}"
        return (
            actual_address[: match.start()]
            + replacement
            + actual_address[match.end() :]
        )

    @classmethod
    def _infer_mismatch_start_level(cls, actual_address: str, stale_address: str) -> str:
        actual_levels = cls._address_level_values(actual_address)
        stale_levels = cls._address_level_values(stale_address)
        for level in ADDRESS_LEVEL_ORDER:
            actual_value = actual_levels.get(level, "")
            stale_value = stale_levels.get(level, "")
            if actual_value and stale_value and actual_value != stale_value:
                return level
        return "province"

    @classmethod
    def _infer_mismatch_rewrite_levels(cls, actual_address: str, stale_address: str) -> list[str]:
        actual_levels = cls._address_level_values(actual_address)
        stale_levels = cls._address_level_values(stale_address)
        changed_levels = [
            level
            for level in ADDRESS_LEVEL_ORDER
            if actual_levels.get(level, "")
            and stale_levels.get(level, "")
            and actual_levels[level] != stale_levels[level]
        ]
        if not changed_levels:
            return []
        start_index = ADDRESS_LEVEL_ORDER.index(changed_levels[0])
        end_index = ADDRESS_LEVEL_ORDER.index(changed_levels[-1])
        return [
            level
            for level in ADDRESS_LEVEL_ORDER[start_index : end_index + 1]
            if actual_levels.get(level, "")
        ]

    @staticmethod
    def _generate_region_stale_address(address: str, rng: random.Random) -> str:
        components = extract_address_components(address)
        if not components.city:
            return address

        if components.province:
            options = [
                option
                for option in COHERENT_REGION_OPTIONS
                if option["province"] != components.province or option["city"] != components.city
            ]
            if components.province.endswith("省"):
                options = [
                    option
                    for option in options
                    if str(option.get("province", "")).endswith("省")
                ] or options
        else:
            options = [
                option
                for option in COHERENT_MUNICIPALITY_OPTIONS
                if option["city"] != components.city
            ]
        if not options:
            return address

        replacement = rng.choice(options)
        stale = address
        if components.province:
            stale = stale.replace(components.province, str(replacement["province"]), 1)
        stale = stale.replace(components.city, str(replacement["city"]), 1)

        replacement_districts = tuple(str(value) for value in replacement.get("districts", ()))
        if components.district and replacement_districts:
            district_options = [value for value in replacement_districts if value != components.district]
            replacement_district = rng.choice(district_options or list(replacement_districts))
            stale = stale.replace(components.district, replacement_district, 1)

        return stale if stale != address else address

    @staticmethod
    def _infer_name_gender(full_name: str) -> str:
        normalized = str(full_name or "").strip()
        if not normalized:
            return "unknown"
        given_name = normalized[1:] if len(normalized) > 1 else normalized
        female_hits = sum(char in FEMALE_NAME_HINT_CHARS for char in given_name)
        male_hits = sum(char in MALE_NAME_HINT_CHARS for char in given_name)
        if female_hits > male_hits:
            return "female"
        if male_hits > female_hits:
            return "male"
        return "unknown"

    @classmethod
    def _normalize_gender(cls, raw_gender: Any, full_name: str = "") -> str:
        normalized = str(raw_gender or "").strip().lower()
        if normalized in {"女", "女性", "female", "woman", "f"}:
            return "女"
        if normalized in {"男", "男性", "male", "man", "m"}:
            return "男"

        inferred = cls._infer_name_gender(full_name)
        if inferred == "female":
            return "女"
        if inferred == "male":
            return "男"
        return "未知"

    @classmethod
    def _pick_contact_phone_owner_spoken_label(
        cls,
        owner: str,
        full_name: str,
        gender: str = "",
    ) -> str:
        normalized_owner = str(owner or "").strip()
        normalized_gender = cls._normalize_gender(gender, full_name)

        options_map = {
            "本人备用号码": ("我另一个号码", "我备用号"),
            "爸": ("我爸", "我父亲"),
            "妈": ("我妈", "我母亲"),
            "儿子": ("我儿子", "我家孩子"),
            "女儿": ("我女儿", "我闺女"),
            "室友": ("我室友", "合租室友"),
        }
        if normalized_owner == "爱人":
            if normalized_gender == "女":
                options = ("我老公", "我丈夫", "我爱人")
                return options[cls._stable_choice_index(normalized_owner, full_name, len(options))]
            if normalized_gender == "男":
                options = ("我媳妇", "我老婆", "我爱人")
                return options[cls._stable_choice_index(normalized_owner, full_name, len(options))]
            options = ("我爱人", "家里人")
            return options[cls._stable_choice_index(normalized_owner, full_name, len(options))]

        options = options_map.get(normalized_owner)
        if options:
            return options[cls._stable_choice_index(normalized_owner, full_name, len(options))]
        return normalized_owner or "这个号码"

    @staticmethod
    def _stable_choice_index(owner: str, full_name: str, size: int) -> int:
        if size <= 0:
            return 0
        seed_text = f"{owner}:{full_name}"
        return sum(ord(char) for char in seed_text) % size

    @staticmethod
    def _extract_address_detail_token(address: str, pattern: str) -> str:
        match = re.search(pattern, address)
        return match.group(0) if match else ""

    @classmethod
    def _generate_address_correction(
        cls,
        *,
        actual_address: str,
        stale_address: str,
        rng: random.Random,
    ) -> str:
        if not stale_address:
            return actual_address

        actual_room = cls._extract_address_detail_token(actual_address, r"\d+\s*室")
        stale_room = cls._extract_address_detail_token(stale_address, r"\d+\s*室")
        actual_unit = cls._extract_address_detail_token(actual_address, r"\d+\s*单元")
        stale_unit = cls._extract_address_detail_token(stale_address, r"\d+\s*单元")
        actual_building = cls._extract_address_detail_token(actual_address, r"\d+\s*(?:号楼|栋|幢|座|楼)")
        stale_building = cls._extract_address_detail_token(stale_address, r"\d+\s*(?:号楼|栋|幢|座|楼)")

        actual_region = cls._generate_partial_address(actual_address)
        stale_region = cls._generate_partial_address(stale_address)

        if actual_region != stale_region:
            return actual_address if rng.random() < 0.75 else cls._generate_partial_address(actual_address)

        candidates: list[str] = []
        if actual_building and actual_building != stale_building:
            building_tail = actual_building
            if actual_unit:
                building_tail += actual_unit
            if actual_room:
                building_tail += actual_room
            candidates.append(building_tail)
        if actual_unit and actual_unit != stale_unit:
            unit_tail = actual_unit
            if actual_room:
                unit_tail += actual_room
            candidates.append(unit_tail)
        if actual_room and actual_room != stale_room:
            candidates.append(actual_room)

        if candidates:
            if rng.random() < 0.7:
                return rng.choice(candidates)
            return actual_address

        return actual_address if rng.random() < 0.5 else cls._generate_partial_address(actual_address)

    @staticmethod
    def _infer_product_arrived(issue_text: str) -> bool:
        normalized = re.sub(r"\s+", "", issue_text or "")
        negative_keywords = ("没到", "还没到", "未到", "没送到", "还没送到")
        positive_keywords = ("送到", "到家", "到货", "到了", "送来了", "送到了")
        if any(keyword in normalized for keyword in negative_keywords):
            return False
        if any(keyword in normalized for keyword in positive_keywords):
            return True
        return True
