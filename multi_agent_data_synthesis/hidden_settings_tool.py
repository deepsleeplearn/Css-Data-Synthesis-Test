from __future__ import annotations

import asyncio
import json
import random
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

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
1. 只生成美的(家用){product_name}的中文客服场景。
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
                    "contact_phone": primary_phone,
                    "phone_input_attempts_required": 0,
                    "phone_input_round_1": f"{primary_phone}#",
                    "phone_input_round_2": f"{primary_phone}#",
                    "phone_input_round_3": f"{primary_phone}#",
                }
            )
            return

        backup_owner = rng.choices(
            population=["本人备用号码", "爱人", "父亲", "母亲", "儿子", "女儿"],
            weights=[50, 10, 10, 10, 10, 10],
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

        candidate["hidden_context"].update(
            {
                "current_call_contactable": False,
                "contact_phone_owner": backup_owner,
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

        if service_knows_address:
            service_known_address_matches_actual = (
                rng.random() < self.config.service_known_address_matches_probability
            )
            service_known_address_value = (
                actual_address
                if service_known_address_matches_actual
                else self._generate_stale_address(actual_address, rng)
            )
            if not service_known_address_matches_actual:
                if rng.random() < self.config.address_confirmation_direct_correction_probability:
                    correction_address = self._generate_address_correction(
                        actual_address=actual_address,
                        stale_address=service_known_address_value,
                        rng=rng,
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
        if should_force_full_address_after_known_mismatch:
            address_round_1 = actual_address
            address_round_2 = actual_address
        elif rng.random() < self.config.address_collection_followup_probability:
            if rng.random() < 0.5:
                address_round_1 = self._generate_partial_address(actual_address)
            else:
                address_round_1 = self._generate_detail_address(actual_address)

        candidate["hidden_context"].update(
            {
                "service_known_address": service_knows_address,
                "service_known_address_value": service_known_address_value,
                "service_known_address_matches_actual": service_known_address_matches_actual,
                "address_confirmation_no_reply": address_confirmation_no_reply,
                "address_input_round_1": address_round_1,
                "address_input_round_2": address_round_2,
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
        ]
        weights = [
            max(0.0, self.config.phone_collection_invalid_short_probability),
            max(0.0, self.config.phone_collection_invalid_long_probability),
            max(0.0, self.config.phone_collection_invalid_pattern_probability),
        ]
        if sum(weights) <= 0:
            weights = [1.0, 1.0, 1.0]

        candidate = rng.choices(variants, weights=weights, k=1)[0]()
        if re.fullmatch(r"1[3-9]\d{9}#", candidate):
            raise AssertionError(f"Generated phone input should be invalid: {candidate}")
        return candidate

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

    @staticmethod
    def _generate_region_stale_address(address: str, rng: random.Random) -> str:
        stale = address
        changed = False

        province_match = re.search(r"^[^省]+省", stale)
        if province_match and rng.random() >= 0.5:
            pool = ["广东省", "浙江省", "江苏省", "山东省", "河南省", "湖北省", "湖南省", "四川省", "福建省", "安徽省"]
            original = province_match.group(0)
            alternatives = [value for value in pool if value != original]
            if alternatives:
                stale = stale[: province_match.start()] + rng.choice(alternatives) + stale[province_match.end() :]
                changed = True

        city_pattern = r"(?<=省)[^市]+市" if re.search(r"^[^省]+省", stale) else r"^[^市]+市"
        city_match = re.search(city_pattern, stale)
        if city_match and rng.random() >= 0.5:
            pool = ["广州市", "深圳市", "杭州市", "宁波市", "南京市", "苏州市", "青岛市", "郑州市", "武汉市", "长沙市", "成都市", "佛山市", "济南市"]
            original = city_match.group(0)
            alternatives = [value for value in pool if value != original]
            if alternatives:
                stale = stale[: city_match.start()] + rng.choice(alternatives) + stale[city_match.end() :]
                changed = True

        district_match = re.search(r"(?<=市)[^区县]+(?:区|县)", stale)
        if district_match and rng.random() >= 0.5:
            pool = ["天河区", "南山区", "西湖区", "浦东新区", "鼓楼区", "历下区", "金水区", "顺德区", "鄞州区", "盘龙区", "市南区", "余杭区"]
            original = district_match.group(0)
            alternatives = [value for value in pool if value != original]
            if alternatives:
                stale = stale[: district_match.start()] + rng.choice(alternatives) + stale[district_match.end() :]
                changed = True

        return stale if changed else address

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
