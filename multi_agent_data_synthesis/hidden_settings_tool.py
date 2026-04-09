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
    build_address_progressive_segments,
    extract_address_components,
)
from multi_agent_data_synthesis.config import AppConfig
from multi_agent_data_synthesis.dialogue_plans import decide_second_round_reply_strategy
from multi_agent_data_synthesis.llm import OpenAIChatClient
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

COHERENT_REGION_OPTIONS: tuple[dict[str, Any], ...] = (
    {"province": "广东省", "city": "广州市", "districts": ("天河区", "海珠区", "越秀区")},
    {"province": "广东省", "city": "深圳市", "districts": ("南山区", "福田区", "宝安区")},
    {"province": "浙江省", "city": "杭州市", "districts": ("西湖区", "余杭区", "拱墅区")},
    {"province": "浙江省", "city": "宁波市", "districts": ("鄞州区", "海曙区")},
    {"province": "江苏省", "city": "南京市", "districts": ("鼓楼区", "秦淮区")},
    {"province": "江苏省", "city": "苏州市", "districts": ("吴中区", "工业园区")},
    {"province": "山东省", "city": "济南市", "districts": ("历下区", "历城区")},
    {"province": "山东省", "city": "青岛市", "districts": ("市南区", "崂山区")},
    {"province": "河南省", "city": "郑州市", "districts": ("金水区", "中原区")},
    {"province": "湖北省", "city": "武汉市", "districts": ("洪山区", "江汉区", "武昌区")},
    {"province": "湖南省", "city": "长沙市", "districts": ("岳麓区", "芙蓉区")},
    {"province": "四川省", "city": "成都市", "districts": ("武侯区", "高新区", "锦江区")},
    {"province": "福建省", "city": "福州市", "districts": ("仓山区", "鼓楼区", "台江区")},
    {"province": "安徽省", "city": "合肥市", "districts": ("蜀山区", "包河区")},
)
COHERENT_MUNICIPALITY_OPTIONS: tuple[dict[str, Any], ...] = (
    {"province": "", "city": "北京市", "districts": ("朝阳区", "海淀区")},
    {"province": "", "city": "上海市", "districts": ("浦东新区", "闵行区")},
    {"province": "", "city": "天津市", "districts": ("南开区", "河西区")},
    {"province": "", "city": "重庆市", "districts": ("渝北区", "渝中区")},
)
FEMALE_NAME_HINT_CHARS = frozenset("丽娜静敏艳娟婷颖雪倩芳琳洁欣怡蓉莹燕璐璇岚妍媛")
MALE_NAME_HINT_CHARS = frozenset("强伟磊军勇涛超鹏杰峰斌刚浩东博飞健志明龙宁凯晨亮")


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


class HiddenSettingsRepository:
    def __init__(self, path: Path):
        self.path = path

    def load(self) -> list[HiddenSettingsRecord]:
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
            payload = self.client.complete_json(
                model=self.config.user_agent_model,
                messages=self._build_messages(scenario, rejection_feedback),
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
            self._attach_second_round_reply_plan(scenario.scenario_id, candidate)
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

            payload = await self._complete_json_async(
                model=self.config.user_agent_model,
                messages=self._build_messages(scenario, rejection_feedback),
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

    def _build_messages(
        self,
        scenario: Scenario,
        rejection_feedback: str,
    ) -> list[dict[str, str]]:
        product_name = str(scenario.product.category).strip() or "空气能热水器"
        system_prompt = f"""你是一个家电客服数据生成工具，负责给 user_agent 生成隐藏设定。

任务约束：
1. 只生成美的{product_name}的中文客服场景。
2. 生成的内容必须是用户视角隐藏信息，供 user_agent 使用。
3. 输出必须具体、自然、生活化，避免模板化和高相似复用。
4. 电话、地址、用户画像、问题细节、预约时间、历史尝试等都要有变化。
5. 用户画像与说话方式要拆开写，二者都要具体，方便塑造人物。
6. 只返回一个 JSON 对象，不要解释。

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
- 电话必须是 11 位中国大陆手机号
- 故障场景下，大多数 issue 只写 1 个具体故障点，只保留一个核心现象
- 只有极少数场景可以写 2 个相关故障点，但不要扩展到第 3 个问题，也不要堆砌过多结果后果或温度对比数据
- 安装场景与故障场景要区分明显
- 用户画像与说话方式都要具体，且不要写成同一句的重复改写
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
            "hidden_context": {
                str(key): str(value).strip()
                for key, value in hidden_context.items()
                if str(value).strip()
            },
        }

        self._validate_issue_description(
            normalized["request"]["issue"],
            normalized["request"]["request_type"],
            scenario_id=scenario_id,
        )
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
            "- 故障场景下，绝大多数 issue 只保留 1 个核心故障现象；只有极少数场景可写 2 个相关故障点。\n"
            "- 即使允许双故障点，也不要扩展到第 3 个问题，不要堆砌温度数据或过多后果描述。\n"
        )

    def _attach_second_round_reply_plan(self, scenario_id: str, candidate: dict[str, Any]) -> None:
        candidate["hidden_context"]["second_round_reply_strategy"] = decide_second_round_reply_strategy(
            scenario_id,
            self.config.second_round_include_issue_probability,
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
        if rng.random() < self.config.phone_collection_third_attempt_probability:
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
                ) = self._build_known_address_mismatch_plan(actual_address, rng)
            if not service_known_address_matches_actual:
                if rng.random() < self.config.address_confirmation_direct_correction_probability:
                    correction_address = mismatch_correction_value
                    correction_address = self._maybe_compact_address_input(
                        correction_address,
                        rng,
                    )
                    prefix = rng.choice(["不对，", "不是，", "不对，正确的是", "不是，正确的是"])
                    address_confirmation_no_reply = f"{prefix}{correction_address}。"
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
            address_rounds = build_address_progressive_segments(actual_address, rng)

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
    ) -> tuple[str, str, str]:
        level = self._choose_address_mismatch_start_level(actual_address, rng)
        stale_address = self._generate_stale_address_from_level(actual_address, level, rng)
        correction_value = self._address_suffix_from_level(actual_address, level)
        if stale_address == actual_address or not correction_value:
            fallback_stale = self._generate_stale_address(actual_address, rng)
            fallback_correction = self._generate_address_correction(
                actual_address=actual_address,
                stale_address=fallback_stale,
                rng=rng,
            )
            return fallback_stale, self._infer_mismatch_start_level(actual_address, fallback_stale), fallback_correction
        return stale_address, level, correction_value

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
    def _address_suffix_from_level(cls, address: str, level: str) -> str:
        components = extract_address_components(address)
        level_values = {
            "province": components.province,
            "city": components.city,
            "district": components.district,
            "locality": "".join(part for part in (components.town, components.road, components.community) if part),
            "building": components.building,
            "unit": components.unit,
            "floor": components.floor,
            "room": components.room,
        }
        ordered_levels = ("province", "city", "district", "locality", "building", "unit", "floor", "room")
        try:
            start_index = ordered_levels.index(level)
        except ValueError:
            return address
        suffix = "".join(level_values[name] for name in ordered_levels[start_index:] if level_values[name])
        return suffix or address

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
        community_match = re.search(
            r"([A-Za-z0-9\u4e00-\u9fa5]+?(?:小区|花园|公寓|苑|府|里|村|大厦|中心|广场|城|家园|新村|碧桂园))",
            stale,
        )
        if community_match:
            pool = ["幸福花园", "阳光花园", "金色家园", "滨江花园", "锦绣苑", "星辰花园"]
            alternatives = [value for value in pool if value != community_match.group(1)]
            if alternatives:
                return stale.replace(community_match.group(1), rng.choice(alternatives), 1)

        road_number_match = re.search(r"([^\d]{1,20}(?:路|街|大道|巷|弄|胡同))(\d+)号", stale)
        if road_number_match:
            prefix = road_number_match.group(1)
            number = int(road_number_match.group(2))
            replacement = f"{prefix}{number + rng.choice([2, 4, 6])}号"
            return stale.replace(road_number_match.group(0), replacement, 1)

        town_match = re.search(r"([^\d]{1,12}(?:街道|镇|乡))", stale)
        if town_match:
            pool = ["东城街道", "五常街道", "安宜镇", "大良街道", "观音桥街道"]
            alternatives = [value for value in pool if value != town_match.group(1)]
            if alternatives:
                return stale.replace(town_match.group(1), rng.choice(alternatives), 1)
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
        actual = extract_address_components(actual_address)
        stale = extract_address_components(stale_address)
        checks = (
            ("province", actual.province, stale.province),
            ("city", actual.city, stale.city),
            ("district", actual.district, stale.district),
            (
                "locality",
                "".join(part for part in (actual.town, actual.road, actual.community) if part),
                "".join(part for part in (stale.town, stale.road, stale.community) if part),
            ),
            ("building", actual.building, stale.building),
            ("unit", actual.unit, stale.unit),
            ("floor", actual.floor, stale.floor),
            ("room", actual.room, stale.room),
        )
        for level, actual_value, stale_value in checks:
            if actual_value and stale_value and actual_value != stale_value:
                return level
        return "province"

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
    def _pick_contact_phone_owner_spoken_label(
        cls,
        owner: str,
        full_name: str,
    ) -> str:
        normalized_owner = str(owner or "").strip()
        gender = cls._infer_name_gender(full_name)

        options_map = {
            "本人备用号码": ("我另一个号码", "我备用号"),
            "爸": ("我爸", "我父亲"),
            "妈": ("我妈", "我母亲"),
            "儿子": ("我儿子", "我家孩子"),
            "女儿": ("我女儿", "我闺女"),
            "室友": ("我室友", "合租室友"),
        }
        if normalized_owner == "爱人":
            if gender == "female":
                options = ("我老公", "我丈夫", "我爱人")
                return options[cls._stable_choice_index(normalized_owner, full_name, len(options))]
            if gender == "male":
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
