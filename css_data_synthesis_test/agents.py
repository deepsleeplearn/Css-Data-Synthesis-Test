from __future__ import annotations

import re
from typing import Any

from css_data_synthesis_test.dialogue_plans import resolve_second_round_reply_strategy
from css_data_synthesis_test.function_call import build_telephone_model_observation
from css_data_synthesis_test.llm import OpenAIChatClient
from css_data_synthesis_test.product_routing import (
    ensure_product_routing_plan,
    product_routing_instruction_for_prompt,
)
from css_data_synthesis_test.prompts import (
    build_user_agent_messages,
    is_replying_to_service_opening,
    next_address_input_value,
)
from css_data_synthesis_test.schemas import DialogueTurn, Scenario, SERVICE_SPEAKER
from css_data_synthesis_test.service_policy import (
    ServiceDialoguePolicy,
    ServiceRuntimeState,
)


class UserAgent:
    ISSUE_MARKERS = re.compile(
        r"(故障|报码|故障码|报错|报警|显示|不加热|没热水|热水不稳定|忽冷忽热|温度上不去|升温慢|"
        r"漏水|渗水|滴水|异响|噪音|不启动|启动不了|无法启动|跳闸|停机|维修)"
    )
    ADDRESS_CORE_MARKERS = re.compile(
        r"(省|市|区|县|旗|镇|乡|街道|路|街|大道|巷|弄|胡同|小区|社区|花园|公寓|苑|府|里|村|组|队|社|栋|幢|座|单元|室|号)"
    )
    ADDRESS_STRONG_MARKERS = re.compile(
        r"(省|市|区|县|旗|镇|乡|街道|路|街|大道|巷|弄|胡同|小区|社区|花园|公寓|苑|府|里|\d+号|\d+室|\d+单元|\d+(?:栋|幢|座|楼)|[零一二三四五六七八九十两\d]+(?:组|队|社))"
    )
    ADDRESS_CHATTER_MARKERS = re.compile(
        r"(旁边|附近|对面|斜对面|路口|红绿灯|往南|往北|往东|往西|到了|小卖部|超市|门口|怎么走|你知道|你懂的)"
    )
    CAPACITY_LITER_PATTERN = re.compile(r"[零一二三四五六七八九十两\d]+\s*升(?:以上|以下)?")
    CAPACITY_HP_PATTERN = re.compile(r"[零一二三四五六七八九十两\d]+\s*匹(?:及以上|以上|以下)?")
    WATER_HEATER_TYPE_SELECTION_PATTERN = re.compile(
        r"空气能热水器.*燃气热水器.*电热水器|空气能.*燃气.*电热"
    )

    def __init__(
        self,
        client: OpenAIChatClient,
        model: str,
        temperature: float,
        second_round_include_issue_probability: float,
    ):
        self.client = client
        self.model = model
        self.temperature = temperature
        self.second_round_include_issue_probability = second_round_include_issue_probability

    @staticmethod
    def _last_service_text(transcript: list[DialogueTurn]) -> str:
        for turn in reversed(transcript):
            if turn.speaker == SERVICE_SPEAKER:
                return turn.text
        return ""

    @staticmethod
    def _forced_satisfaction_rating(scenario: Scenario, round_index: int) -> str:
        basis = f"{scenario.scenario_id}:{round_index}"
        return "1" if sum(ord(char) for char in basis) % 2 == 0 else "2"

    @classmethod
    def _normalize_asr_style(cls, reply: str) -> str:
        text = str(reply or "").strip()
        if not text:
            return ""
        text = re.sub(r"\.{3,}|…{1,}", "，", text)
        text = re.sub(r"，{2,}", "，", text)
        text = re.sub(r"^\s*，", "", text)
        text = re.sub(r"[，,]\s*$", "", text)
        text = re.sub(r"([。！？!?])\1+", r"\1", text)
        return text.strip()

    @staticmethod
    def _stable_pick(seed_text: str, options: tuple[str, ...]) -> str:
        if not options:
            return ""
        index = sum(ord(char) for char in str(seed_text or "")) % len(options)
        return options[index]

    @classmethod
    def _split_clauses(cls, text: str) -> list[str]:
        return [
            clause.strip()
            for clause in re.split(r"[，,。！？!?；;]", cls._normalize_asr_style(text))
            if clause.strip()
        ]

    @classmethod
    def _join_clauses(cls, clauses: list[str], original_text: str) -> str:
        if not clauses:
            return ""
        joined = "，".join(clauses)
        if str(original_text or "").strip().endswith(("。", "！", "？")):
            return f"{joined}。"
        return joined

    @classmethod
    def _dedupe_clauses(cls, text: str) -> str:
        clauses = cls._split_clauses(text)
        if not clauses:
            return cls._normalize_asr_style(text)
        kept: list[str] = []
        seen: set[str] = set()
        for clause in clauses:
            normalized = re.sub(r"\s+", "", clause)
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            kept.append(clause)
        return cls._join_clauses(kept, text)

    @classmethod
    def _contains_issue_detail(cls, text: str) -> bool:
        return bool(cls.ISSUE_MARKERS.search(text or ""))

    @classmethod
    def _strip_issue_clauses(cls, text: str) -> str:
        clauses = cls._split_clauses(text)
        kept = [clause for clause in clauses if not cls._contains_issue_detail(clause)]
        return cls._join_clauses(kept, text)

    @classmethod
    def _sanitize_capacity_reply(cls, text: str, answer_value: str) -> str:
        sanitized = cls._normalize_asr_style(text)
        has_liter = bool(cls.CAPACITY_LITER_PATTERN.search(sanitized))
        has_hp = bool(cls.CAPACITY_HP_PATTERN.search(sanitized))
        if not (has_liter and has_hp):
            return sanitized

        preferred_pattern = cls.CAPACITY_LITER_PATTERN if "升" in answer_value else cls.CAPACITY_HP_PATTERN
        match = preferred_pattern.search(sanitized)
        if match:
            token = match.group(0)
            if sanitized.endswith(("吧", "呢")):
                return f"{token}{sanitized[-1]}"
            return token

        first_match = min(
            (
                match
                for match in (
                    cls.CAPACITY_LITER_PATTERN.search(sanitized),
                    cls.CAPACITY_HP_PATTERN.search(sanitized),
                )
                if match is not None
            ),
            key=lambda current: current.start(),
        )
        return first_match.group(0)

    @classmethod
    def _sanitize_address_collection_reply(cls, reply: str) -> str:
        text = cls._normalize_asr_style(reply)
        if not text:
            return ""

        clauses = [
            clause.strip()
            for clause in re.split(r"[，,。！？!?；;]", text)
            if clause.strip()
        ]
        kept: list[str] = []
        for clause in clauses:
            has_core_marker = bool(cls.ADDRESS_CORE_MARKERS.search(clause))
            has_chatter_marker = bool(cls.ADDRESS_CHATTER_MARKERS.search(clause))
            has_strong_marker = bool(cls.ADDRESS_STRONG_MARKERS.search(clause))
            if has_core_marker and not (has_chatter_marker and not has_strong_marker):
                kept.append(clause)

        if kept:
            sanitized = "，".join(kept)
            if text.endswith(("。", "！", "？")):
                sanitized = f"{sanitized}。"
            return sanitized
        return text

    @staticmethod
    def _is_unknown_routing_answer(answer_key: str) -> bool:
        normalized = str(answer_key or "").strip()
        return (
            normalized.endswith(".unknown")
            or normalized in {"entry.unknown", "scene.other_unknown", "history_device.no_unknown"}
        )

    @classmethod
    def _routing_reply_conflicts_with_plan(
        cls,
        reply: str,
        answer_key: str,
        prompt_key: str = "",
    ) -> bool:
        normalized_reply = re.sub(r"\s+", "", str(reply or "").strip())
        normalized_answer_key = str(answer_key or "").strip()
        if not normalized_reply or not normalized_answer_key:
            return False
        if cls._is_unknown_routing_answer(normalized_answer_key):
            return False
        if re.search(r"(不太清楚|不清楚|不知道|不确定|记不清|说不上来|应该不是|可能不是|好像不是)", normalized_reply):
            return True
        if str(prompt_key or "").strip() == "usage_scene":
            if re.search(r"(可能|或者|还是|其他地方|具体是在哪里|具体在哪里)", normalized_reply):
                return True
            scene_hits = sum(
                1
                for pattern in (r"家里|家庭|家用|自家", r"别墅", r"公寓", r"理发店")
                if re.search(pattern, normalized_reply)
            )
            if scene_hits > 1:
                return True
        if normalized_answer_key == "scene.family" and re.search(r"(不是家里|不是家庭|不在家里|不在家庭|不是自家|不算家用)", normalized_reply):
            return True
        if normalized_answer_key == "purchase.self_buy" and re.search(r"(不是自己买|不是我买|楼盘|开发商|送的|配套)", normalized_reply):
            return True
        if normalized_answer_key == "purchase.property_bundle" and re.search(r"(自己买|我买|单独买|后来买)", normalized_reply):
            return True
        return False

    @classmethod
    def _fallback_reply_for_turn(
        cls,
        scenario: Scenario,
        transcript: list[DialogueTurn],
        last_service_text: str,
    ) -> str:
        seed = f"{scenario.scenario_id}:{last_service_text}"
        routing_step = product_routing_instruction_for_prompt(transcript, scenario.hidden_context)
        if routing_step:
            answer_value = str(routing_step.get("answer_value", "")).strip()
            answer_key = str(routing_step.get("answer_key", "")).strip()
            prompt_key = str(routing_step.get("prompt_key", "")).strip()
            if answer_key.startswith("capacity.") and answer_value:
                suffix_options = ("吧", "呢", "")
                suffix = cls._stable_pick(f"{seed}:capacity", suffix_options)
                return f"{answer_value}{suffix}".strip()
            if prompt_key == "usage_scene" and answer_value:
                return cls._stable_pick(
                    f"{seed}:usage-scene",
                    (
                        answer_value,
                        f"在{answer_value.replace('使用', '')}用。",
                    ),
                )
            if answer_value:
                return cls._stable_pick(
                    f"{seed}:routing",
                    (
                        answer_value,
                        f"应该是{answer_value}",
                        f"大概是{answer_value}",
                    ),
                )

        if ServiceDialoguePolicy.is_surname_prompt(last_service_text):
            surname = str(scenario.customer.surname or "").strip() or "王"
            return cls._stable_pick(
                f"{seed}:surname",
                (
                    f"我姓{surname}",
                    f"免贵姓{surname}",
                    f"姓{surname}",
                ),
            )
        if ServiceDialoguePolicy.is_contactable_prompt(last_service_text):
            if bool(scenario.hidden_context.get("current_call_contactable", True)):
                return cls._stable_pick(
                    f"{seed}:contactable:yes",
                    (
                        "能联系，就是这个号码。",
                        "可以联系，我这个号码能打通。",
                        "能联系，我这个号码就行。",
                    ),
                )
            owner = str(
                scenario.hidden_context.get("contact_phone_owner_spoken_label")
                or scenario.hidden_context.get("contact_phone_owner")
                or "家里人的"
            ).strip()
            return cls._stable_pick(
                f"{seed}:contactable:no",
                (
                    f"不能联系，留{owner}的号码吧。",
                    f"这个号不太方便联系，登记{owner}的号码。",
                    f"这个号码联系不上，留{owner}的号码。",
                ),
            )
        if ServiceDialoguePolicy.is_phone_confirmation_prompt(last_service_text):
            expected_phone = str(
                scenario.hidden_context.get("contact_phone")
                or scenario.customer.phone
            ).strip()
            service_phone_match = re.search(r"1[3-9]\d{9}", last_service_text or "")
            if service_phone_match and service_phone_match.group(0) == expected_phone:
                return cls._stable_pick(f"{seed}:phone-confirm:yes", ("对。", "对，是的。", "嗯，没错。"))
            return cls._stable_pick(f"{seed}:phone-confirm:no", ("不对。", "不是这个。", "不对，号码不对。"))
        if ServiceDialoguePolicy.is_address_confirmation_prompt(last_service_text):
            normalized_actual = re.sub(r"\s+", "", str(scenario.customer.address or ""))
            normalized_service = re.sub(r"\s+", "", str(last_service_text or ""))
            if normalized_actual and normalized_actual in normalized_service:
                return cls._stable_pick(f"{seed}:address-confirm:yes", ("对。", "对，是的。", "嗯，没错。"))
            correction = str(scenario.hidden_context.get("address_confirmation_no_reply", "")).strip()
            return correction or cls._stable_pick(
                f"{seed}:address-confirm:no",
                ("不对。", "不是这个地址。", "地址不对。"),
            )
        if ServiceDialoguePolicy.is_address_collection_prompt(last_service_text):
            return next_address_input_value(scenario, transcript)
        if ServiceDialoguePolicy.is_product_arrival_prompt(last_service_text):
            arrived = str(scenario.hidden_context.get("product_arrived", "yes")).strip().lower() == "yes"
            return cls._stable_pick(
                f"{seed}:arrival",
                ("到了。", "到货了。", "已经到了。") if arrived else ("还没到。", "没到货。", "暂时还没到。"),
            )
        if ServiceDialoguePolicy.is_product_model_prompt(last_service_text):
            model = str(scenario.product.model or "").strip()
            if model and model != "未知":
                return cls._stable_pick(
                    f"{seed}:model",
                    (
                        model,
                        f"型号是{model}",
                        f"我看下，型号是{model}",
                    ),
                )
            return cls._stable_pick(f"{seed}:model-unknown", ("型号我记不清了。", "型号一下说不上来。"))
        if ServiceDialoguePolicy.is_closing_notice_prompt(last_service_text):
            return cls._stable_pick(f"{seed}:closing", ("好的。", "知道了。", "行，知道了。"))
        return ""

    @staticmethod
    def _planned_water_heater_opening_reply(
        scenario: Scenario,
        transcript: list[DialogueTurn],
        round_index: int,
    ) -> str:
        hidden_context = scenario.hidden_context if isinstance(scenario.hidden_context, dict) else {}
        if str(hidden_context.get("ivr_product_kind", "")).strip() != "water_heater":
            return ""
        if not is_replying_to_service_opening(scenario, transcript, round_index):
            return ""
        return str(hidden_context.get("auto_mode_water_heater_opening_reply", "")).strip()

    @classmethod
    def _planned_water_heater_type_reply(
        cls,
        scenario: Scenario,
        transcript: list[DialogueTurn],
    ) -> str:
        hidden_context = scenario.hidden_context if isinstance(scenario.hidden_context, dict) else {}
        if str(hidden_context.get("ivr_product_kind", "")).strip() != "water_heater":
            return ""
        last_service_text = cls._last_service_text(transcript)
        if not cls.WATER_HEATER_TYPE_SELECTION_PATTERN.search(last_service_text or ""):
            return ""
        return "空气能的。"

    @classmethod
    def _sanitize_reply_for_turn(
        cls,
        scenario: Scenario,
        transcript: list[DialogueTurn],
        reply: str,
    ) -> str:
        text = cls._dedupe_clauses(reply)
        if not transcript:
            return text
        last_service_text = cls._last_service_text(transcript)
        routing_step = product_routing_instruction_for_prompt(transcript, scenario.hidden_context)
        if ServiceDialoguePolicy.is_address_collection_prompt(last_service_text):
            return cls._sanitize_address_collection_reply(text)
        if routing_step:
            text = cls._sanitize_capacity_reply(text, str(routing_step.get("answer_value", "")).strip())
            if cls._routing_reply_conflicts_with_plan(
                text,
                str(routing_step.get("answer_key", "")).strip(),
                str(routing_step.get("prompt_key", "")).strip(),
            ):
                fallback = cls._fallback_reply_for_turn(scenario, transcript, last_service_text)
                if fallback:
                    text = fallback

        narrow_prompt = bool(routing_step) or any(
            predicate(last_service_text)
            for predicate in (
                ServiceDialoguePolicy.is_surname_prompt,
                ServiceDialoguePolicy.is_contactable_prompt,
                ServiceDialoguePolicy.is_phone_confirmation_prompt,
                ServiceDialoguePolicy.is_address_confirmation_prompt,
                ServiceDialoguePolicy.is_product_arrival_prompt,
                ServiceDialoguePolicy.is_product_model_prompt,
                ServiceDialoguePolicy.is_closing_notice_prompt,
            )
        )
        if narrow_prompt and cls._contains_issue_detail(text):
            stripped = cls._strip_issue_clauses(text)
            if stripped:
                text = stripped
        if not text or (narrow_prompt and cls._contains_issue_detail(text)):
            fallback = cls._fallback_reply_for_turn(scenario, transcript, last_service_text)
            if fallback:
                text = fallback
        return text

    def respond(
        self,
        *,
        scenario: Scenario,
        transcript: list[DialogueTurn],
        round_index: int,
    ) -> dict[str, Any]:
        if ServiceDialoguePolicy.is_satisfaction_prompt(self._last_service_text(transcript)):
            return {
                "reply": self._forced_satisfaction_rating(scenario, round_index),
                "call_complete": True,
            }
        planned_type_reply = self._planned_water_heater_type_reply(scenario, transcript)
        if planned_type_reply:
            return {
                "reply": planned_type_reply,
                "call_complete": False,
            }
        planned_reply = self._planned_water_heater_opening_reply(scenario, transcript, round_index)
        if planned_reply:
            return {
                "reply": planned_reply,
                "call_complete": False,
            }
        second_round_reply_strategy = resolve_second_round_reply_strategy(
            scenario_id=scenario.scenario_id,
            hidden_context=scenario.hidden_context,
            include_issue_probability=self.second_round_include_issue_probability,
        )
        payload = self.client.complete_json(
            model=self.model,
            messages=build_user_agent_messages(
                scenario,
                transcript,
                round_index,
                second_round_reply_strategy=second_round_reply_strategy,
            ),
            temperature=self.temperature,
        )
        reply = self._sanitize_reply_for_turn(scenario, transcript, str(payload.get("reply", "")).strip())
        return {
            "reply": reply,
            "call_complete": bool(payload.get("call_complete", False)),
        }

    async def respond_async(
        self,
        *,
        scenario: Scenario,
        transcript: list[DialogueTurn],
        round_index: int,
    ) -> dict[str, Any]:
        if ServiceDialoguePolicy.is_satisfaction_prompt(self._last_service_text(transcript)):
            return {
                "reply": self._forced_satisfaction_rating(scenario, round_index),
                "call_complete": True,
            }
        planned_type_reply = self._planned_water_heater_type_reply(scenario, transcript)
        if planned_type_reply:
            return {
                "reply": planned_type_reply,
                "call_complete": False,
            }
        planned_reply = self._planned_water_heater_opening_reply(scenario, transcript, round_index)
        if planned_reply:
            return {
                "reply": planned_reply,
                "call_complete": False,
            }
        second_round_reply_strategy = resolve_second_round_reply_strategy(
            scenario_id=scenario.scenario_id,
            hidden_context=scenario.hidden_context,
            include_issue_probability=self.second_round_include_issue_probability,
        )
        payload = await self.client.complete_json_async(
            model=self.model,
            messages=build_user_agent_messages(
                scenario,
                transcript,
                round_index,
                second_round_reply_strategy=second_round_reply_strategy,
            ),
            temperature=self.temperature,
        )
        reply = self._sanitize_reply_for_turn(scenario, transcript, str(payload.get("reply", "")).strip())
        return {
            "reply": reply,
            "call_complete": bool(payload.get("call_complete", False)),
        }


class ServiceAgent:
    SURNAME_SPLIT_VARIANTS = (
        ("耳东", "东耳"),
        ("弓长", "长弓"),
        ("木子", "子木"),
        ("关耳", "耳关"),
        ("言午", "午言"),
        ("立早", "早立"),
        ("古月", "月古"),
        ("双木", "木双"),
    )

    def __init__(
        self,
        client: OpenAIChatClient,
        model: str,
        temperature: float,
        ok_prefix_probability: float = 1.0,
        query_prefix_weights: dict[str, float] | None = None,
        product_routing_enabled: bool = True,
        product_routing_apply_probability: float = 1.0,
    ):
        self.client = client
        self.model = model
        self.temperature = temperature
        self.product_routing_enabled = product_routing_enabled
        self.product_routing_apply_probability = max(0.0, min(1.0, float(product_routing_apply_probability)))
        self.policy = ServiceDialoguePolicy(
            ok_prefix_probability=ok_prefix_probability,
            query_prefix_weights=query_prefix_weights,
            address_inference_callback=self._infer_address_candidate_with_model,
            address_collection_acceptance_inference_callback=self._infer_address_collection_acceptance_with_model,
            surname_inference_callback=self._infer_surname_with_model,
            contact_intent_inference_callback=self._infer_contactable_intent_with_model,
            confirmation_intent_inference_callback=self._infer_confirmation_intent_with_model,
            opening_intent_inference_callback=self._infer_opening_intent_with_model,
            water_heater_opening_resolution_callback=self._infer_water_heater_opening_resolution_with_model,
            issue_description_extraction_callback=self._extract_issue_description_with_model,
            phone_inference_callback=self._infer_phone_with_model,
            product_routing_intent_inference_callback=self._infer_product_routing_intent_with_model,
            product_routing_enabled=product_routing_enabled,
        )

    @classmethod
    def _normalize_surname_model_input(cls, user_text: str) -> str:
        normalized = str(user_text or "").strip()
        if not normalized:
            return ""
        for canonical, variant in cls.SURNAME_SPLIT_VARIANTS:
            normalized = normalized.replace(variant, canonical)
        return normalized

    def _infer_address_candidate_with_model(
        self,
        *,
        user_text: str,
        confirmation_address: str,
        partial_address_candidate: str,
        last_address_followup_prompt: str,
        dialogue_history: str = "",
    ) -> dict[str, Any]:
        system_prompt = """你是家电客服对话里的地址识别助手。

任务：
1. 只提取用户这一轮明确说出的地址内容。
2. 去掉抱怨、路线说明、上门提醒、停车说明等非地址信息。
3. 如果用户只提供了区、县、旗、镇、乡、街道、村、小区、社区、学校、医院、酒店、门牌号等粒度，不能脑补缺失的省、市、区，必须保留已说出的部分并等待后续追问。
4. 如果用户明确说出了真实存在的中国地级市或直辖市名称，且该城市对应的上级省级行政区唯一明确，那么 merged_address_candidate 必须补全对应省份；address_candidate 仍然只保留用户原话里真正说出的地址内容。
5. 除了上一条“用户明确说出地级市/直辖市”的情况外，不要脑补用户没说出的省、市、区、镇、村、小区、门牌号。
6. 可以结合“当前已积累的地址片段”输出一个不含脑补的“合并后最新地址候选”。
7. 如果这一轮没有明确说出可用地址，就返回空字符串。
8. 如果用户说“就这个地方就行”“按前面那个地址”等模糊收尾话术，可以结合“最近对话历史”和“当前已积累的地址片段”总结出用户真正想登记的地址，但不要补出对话里从未出现过的细节。
9. 像“302”“1103”这类裸数字，如果明显是在补充楼栋后的房号，可以按房间号理解。
10. 如果用户已经说到“小区/道路门牌号/楼栋/房号”中的任一足够定位的信息，不要因为缺少单元、楼层就强行补全这些细节。
11. 如果用户说“我说了啊”“前面不是说了吗”“怎么还是这问题”这类明确表示自己已经提供过地址的句子，优先结合“最近对话历史”和“当前已积累的地址片段”总结当前最合理的地址候选；不要返回空字符串。
12. 如果用户这一轮只说到“省/市/区/县/镇/乡/街道”等行政区层级，不要在 merged_address_candidate 里擅自补出小区、楼栋、房号。
13. 像“外卖柜/快递柜/取餐柜/驿站/前台/门岗/保安亭/收发室”这类明确可到达的点位，视为有效地址细节；如果结合已积累地址片段后已经足够定位，不要再强行补楼栋单元。
14. 像“换一个”“留个新地址”“重新登记地址”“改个地址”这类只是要求重新登记、但没有提供真实地址内容的话，必须返回空字符串，granularity=non_address。
15. 如果用户先否认再给出真实地址，例如“不是，江苏省扬州市宝应县御景豪庭”，要把否认部分去掉，只提取后面的真实地址。
16. 如果用户说“换个地址，三门县江南壹号”“留个新地址，徐泾镇西郊一区”“改成南京农业大学卫岗校区”，前半句只是换址意图，真正的地址内容是后半句；不要把“换个地址”“留个新地址”混进地址槽位。
17. 只有在用户明确说出了真实存在的中国行政区时，才能在 address_candidate / merged_address_candidate 里写入省、市、区、县、旗、镇、乡、街道等行政层级；不要把细粒度地名误写成行政区。
18. 详细地名里常见的“市场、超市、门市、夜市、校区、园区、景区、厂区、小区、社区、片区”等词，其中的“市/区”通常只是地名组成，不是行政区后缀，绝不能据此脑补或改写城市、区县。
19. 如果“当前已积累的地址片段”里已经有省、市、区，而用户这一轮只是在补充小区、市场、门牌号、楼栋、房号，就必须保留原有省、市、区，不要改写、更不要吞并成新的“市/区”。
20. 如果用户是在否定旧地址并给出新区域，例如“不是天津，在江苏”“不在老地方，现在在苏州”“不是这个区，是武侯区”，必须只提取用户真正想登记的新地址部分；像“不是天津”“不在老地址”这类被否定的旧地址内容不能进入 address_candidate / merged_address_candidate。
21. 如果用户当前只提供了新的省、市、区其中一部分，也要把这部分当作新的地址纠正信息保留下来，供后续继续追问；不要把否定词一起混进地址槽位。
22. 只提取用户原话中与地址相关的文本，忽略与地址无关的口头禅、语气词、主语、寒暄、抱怨和连接成分；例如“啥，我在南京邮电大学仙林校区”只应提取“南京邮电大学仙林校区”。
23. 示例：
- 用户说“武汉市江夏区”，address_candidate 必须是“武汉市江夏区”，merged_address_candidate 必须补充完整省：“湖北省武汉市江夏区”。
- 用户只说“江夏区”或“幸福家园10号楼402室”，则不能补成“湖北省武汉市江夏区...”，必须继续追问缺失行政区。
- 如果客服刚核对的是“四川省绵阳市...”，用户说“不是，我在扬州市宝应县”，那么 address_candidate 必须是“扬州市宝应县”，merged_address_candidate 必须是“江苏省扬州市宝应县”；绝不能保留旧的“四川省”。
24. 如果用户给出了新的城市，且它与“客服正在核对或上下文中的地址”里的旧城市不同，那么旧城市、旧省份都必须视为作废，不能继承到 merged_address_candidate 里。绝不能输出“四川省扬州市宝应县”“广东省武汉市江夏区”这类真实中国行政归属错误的组合。

输出 JSON：
{
  "address_candidate": "提取后的地址片段，没有就返回空字符串",
  "merged_address_candidate": "结合已积累地址片段后，本轮结束时最合理的最新地址候选；如果仍无法给出就返回空字符串",
  "granularity": "none|admin_region|locality|detail|locality_with_detail|complete"
}
"""
        user_prompt = f"""请基于下面信息识别本轮用户明确说出的地址。

上一轮客服话术：
{last_address_followup_prompt or '无'}

客服正在核对或上下文中的地址：
{confirmation_address or '无'}

当前已积累的地址片段：
{partial_address_candidate or '无'}

最近对话历史：
{dialogue_history or '无'}

用户本轮原话：
{user_text}

只返回 JSON。"""
        payload = self.client.complete_json(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.0,
        )
        return {
            "address_candidate": str(payload.get("address_candidate", "")).strip(),
            "merged_address_candidate": str(payload.get("merged_address_candidate", "")).strip(),
            "granularity": str(payload.get("granularity", "")).strip(),
        }

    def _infer_address_collection_acceptance_with_model(
        self,
        *,
        user_text: str,
        partial_address_candidate: str,
        last_address_followup_prompt: str,
        dialogue_history: str = "",
    ) -> dict[str, Any]:
        system_prompt = """你是家电客服对话里的地址收集意图识别助手。

任务：
1. 判断用户这句话是不是在表达“就按当前已经提供的地址先登记/确认，不再继续补充更详细地址”。
2. 只输出 yes、no 或 unknown。
3. 像“就到这儿吧”“就这些了”“按前面那个就行”“后面电话联系吧”“先这样登记”“只能提供到这了”“我说完了”，如果语义是在停止继续补充地址，判为 yes。
4. 如果用户仍在继续补充地址内容，或者是在纠正地址细节，而不是表示停止补充，判为 no。
5. 如果无法判断，输出 unknown。

输出 JSON：
{
  "intent": "yes|no|unknown"
}
"""
        user_prompt = f"""请基于下面信息判断用户是否在表示“按当前已提供地址处理，不再继续补充”。

上一轮客服话术：
{last_address_followup_prompt or '无'}

当前已积累的地址片段：
{partial_address_candidate or '无'}

最近对话历史：
{dialogue_history or '无'}

用户本轮原话：
{user_text}

只返回 JSON。"""
        payload = self.client.complete_json(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.0,
        )
        return {"intent": str(payload.get("intent", "")).strip()}

    def _infer_contactable_intent_with_model(
        self,
        *,
        user_text: str,
        user_round_index: int = 0,
    ) -> dict[str, Any]:
        system_prompt = """你是家电客服对话里的联系方式意图识别助手。

任务：
1. 判断用户当前这句话是在表达“当前来电可以联系到本人”，还是“当前来电不方便联系，需要换别的号码”。
2. 只输出 yes、no 或 unknown。
3. 如果用户语义更接近“联系另一个号码”“换个号码”“换一个吧”“我说换一个”“打别的号码”“改联系备用号码”，判为 no。
4. 如果用户提到“联系我老伴/爱人/老婆/老公/儿子/女儿/家里人/家属”或“记我老伴的吧”“留一个我老伴的”，即使前面说了“可以是可以”，整体仍判为 no。
5. 如果句子前半段先说“可以/能联系”，后半段又转折到“但是/不过/还是换一个/联系备用号码/联系家里人”，整体仍判为 no。
6. 只有明确表示“当前这个来电号码就能联系到本人”时，才判 yes。
7. 如果用户已经直接口述了一个新的 11 位手机号，并表达“联系这个号码/留这个号码/记这个号码/打这个号码”，整体判为 no；因为这表示要换成新的联系方式，而不是确认当前来电号码可联系。
8. 如果用户只口述了一个新的 11 位手机号，没有明确说“当前来电号码可以联系到本人”，通常也更接近 no。

输出 JSON：
{
  "intent": "yes|no|unknown"
}
"""
        payload = self.client.complete_json(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": f"[{user_round_index}]用户: {user_text}\n只返回 JSON。",
                },
            ],
            temperature=0.0,
        )
        return {"intent": str(payload.get("intent", "")).strip()}

    def _infer_surname_with_model(
        self,
        *,
        user_text: str,
        user_round_index: int = 0,
    ) -> dict[str, Any]:
        normalized_user_text = self._normalize_surname_model_input(user_text)
        system_prompt = """你是家电客服对话里的姓氏识别助手。

任务：
1. 从用户当前这句回答里识别用户真正表达的姓氏。
2. 支持常见口语、全名、自报姓氏，以及拆字式表达，例如“耳东陈”“东耳陈”“弓长张”“长弓张”“关耳郑”。
3. 如果用户说的是全名，只返回姓，不返回名字。
4. 如果用户没有明确回答姓氏，返回空字符串。
5. surname 只返回 1 到 2 个汉字。
6. 拆字式表达即使前后顺序颠倒，本质上还是同一个姓，例如“东耳郑”仍应识别为“郑”。

输出 JSON：
{
  "surname": "识别出的姓氏，没有就返回空字符串"
}
"""
        payload = self.client.complete_json(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": (
                        f"[{user_round_index}]用户原话: {user_text}\n"
                        f"归一化参考: {normalized_user_text or user_text}\n"
                        "只返回 JSON。"
                    ),
                },
            ],
            temperature=0.0,
        )
        return {"surname": str(payload.get("surname", "")).strip()}

    def _infer_confirmation_intent_with_model(
        self,
        *,
        prompt_kind: str,
        user_text: str,
        confirmation_address: str = "",
        user_round_index: int = 0,
    ) -> dict[str, Any]:
        system_prompt = """你是家电客服对话里的确认意图识别助手。

任务：
1. 根据 prompt_kind 判断用户这句话对当前确认问题的意图。
2. 仅基于当前用户原话判断，不要脑补未说出的事实。
3. 对 phone_number_confirmation、address_confirmation、product_arrival_confirmation：
   - yes 表示确认/肯定/已满足
   - no 表示否认/未满足
   - unknown 表示仍无法判断
4. 对 address_confirmation 来说，只要用户是在否认当前客服核对的地址，不管后面有没有顺手补充新地址，intent 都应判为 no。
5. 对 address_confirmation 来说，像“不是”“不对”“换一个”“留个新地址”“改个地址”“重新登记地址”“这不是现在的地址”都判为 no。
6. 对 address_confirmation 来说，像“不是，江苏省扬州市宝应县御景豪庭”“不对，改成南京农业大学卫岗校区”“这是以前的住址，我现在在...”这类句子，虽然包含新地址或纠正信息，但本轮确认意图仍然是 no。
7. 对 address_confirmation 来说，只有明确认可当前核对项正确时才判 yes，例如“对”“是的”“没错”“这个可以”“就这个”。
8. 对 address_confirmation_observation_followup：
   - confirm_only：只是确认当前核对地址正确，没有新增、删除、修改任何地址粒度
   - add：在确认的同时新增了地址粒度，例如补楼栋、单元、楼层、门牌号、小区、街道等
   - modify：修改了当前核对地址中的某一粒度
   - delete：明确删掉了当前核对地址中的某一粒度或说明某粒度不该有
   - unknown：无法判断
9. 对 address_confirmation_observation_followup，如果用户只是“对”“是的”“没错”“对对对”“嗯”这类纯确认，应判为 confirm_only。
10. 对 address_confirmation_observation_followup，如果用户像“对的，10号楼”“是的，2单元504”“对，不过区县要改成...”这类在确认同时补充或修改地址，应判为 add 或 modify，而不是 confirm_only。

当前可能的 prompt_kind：
- phone_number_confirmation：确认刚才识别出的手机号是否正确
- address_confirmation：确认客服正在核对的地址是否正确
- address_confirmation_observation_followup：在 observation 触发的地址确认之后，判断用户这轮是纯确认，还是在新增/修改/删除地址粒度
- product_arrival_confirmation：确认产品是否已经到货

输出 JSON：
{
  "prompt_kind": "当前问题类型",
  "intent": "yes|no|unknown|confirm_only|add|modify|delete"
}
"""
        user_prompt = f"当前 prompt_kind：{prompt_kind}\n"
        if confirmation_address:
            user_prompt += f"当前客服正在核对的地址：{confirmation_address}\n"
        user_prompt += f"[{user_round_index}]用户: {user_text}\n只返回 JSON。"
        payload = self.client.complete_json(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": user_prompt,
                },
            ],
            temperature=0.0,
        )
        return {
            "prompt_kind": str(payload.get("prompt_kind", "")).strip(),
            "intent": str(payload.get("intent", "")).strip(),
        }

    def _infer_opening_intent_with_model(
        self,
        *,
        user_text: str,
        user_round_index: int = 0,
    ) -> dict[str, Any]:
        system_prompt = """你是家电客服对话里的开场确认意图识别助手。

任务：
1. 判断用户这句话是在单纯确认“是报修/是安装”，还是已经补充了故障/安装诉求细节。
2. 只输出 yes、no、issue_detail 或 unknown。
3. 像“是滴、是呀、是啊、嗯呐、对滴”这类口语肯定，通常是 yes，不算 issue_detail。
4. 只有用户明确说出故障现象、报错、安装诉求细节时，才判为 issue_detail。
5. “维修”“报修”“需要修”“坏了”“有问题”这类泛泛表达，本身不算 issue_detail。
5. 仅有品牌、系列、型号、容量、匹数、楼宇/家用等产品信息，不算 issue_detail。
6. “东西坏了”“热水器坏了”“有问题”这类泛泛表述，不算 issue_detail；必须有具体故障现象才算。
7. 如果用户明确说了产品部位或零件哪里坏了，例如“面板坏了”“显示屏坏了”“压缩机坏了”“主板坏了”，算 issue_detail。

输出 JSON：
{
  "intent": "yes|no|issue_detail|unknown"
}
"""
        payload = self.client.complete_json(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": f"[{user_round_index}]用户: {user_text}\n只返回 JSON。",
                },
            ],
            temperature=0.0,
        )
        return {"intent": str(payload.get("intent", "")).strip()}

    def _infer_water_heater_opening_resolution_with_model(
        self,
        *,
        user_text: str,
        current_brand: str,
        current_request_type: str,
        previous_service_text: str = "",
        user_round_index: int = 0,
    ) -> dict[str, Any]:
        action = "安装" if str(current_request_type or "").strip() == "installation" else "维修"
        def _normalize_opening_resolution_payload(payload: dict[str, Any] | None) -> dict[str, str]:
            normalized_payload = payload if isinstance(payload, dict) else {}
            return {
                "intent": str(normalized_payload.get("intent", "")).strip(),
                "brand": str(normalized_payload.get("brand", "")).strip(),
                "request_type": str(normalized_payload.get("request_type", "")).strip(),
                "heater_type": str(normalized_payload.get("heater_type", "")).strip(),
            }

        prompt_brand = str(current_brand or "").strip() or "美的"
        system_prompt = """你是家电客服对话里的热水器首轮确认识别助手。

场景：
客服刚问过用户一个确认问题。
你会同时看到：
1. 客服上一句原话
2. 当前用户回复

默认场景里，客服可能问：
“您好，很高兴为您服务，请问是__PROMPT_BRAND__热水器需要__ACTION__吗？”
这句话同时在确认三点：
1. 品牌是不是这个品牌
2. 品类是不是热水器
3. 诉求是不是安装/维修

你的任务：
只根据用户当前这一句回复，判断：
1. 用户整体是在肯定、否定/修改、还是没答清
2. 如果用户修改了品牌，提取修改后的品牌
3. 如果用户修改了诉求，提取 installation 或 fault
4. 如果用户已经明确把热水器细分成 空气能 / 燃气 / 电热，提取 heater_type

输出要求：
1. intent 只允许 yes / no / unknown
2. request_type 只允许 installation / fault / 空字符串
3. heater_type 只允许 air_energy / gas / electric / water_heater / 空字符串
4. brand 没有明确修改时输出空字符串
5. 不要脑补没有说出的品牌或诉求
6. 只要用户对品牌、诉求、热水器类型中的任意一点做了修改或补充，intent 就必须输出 no，不能输出 yes 或 unknown。
7. 用户即使先说“是的”“对”“嗯”，但后面又说“是安装”“不是美的”“海尔的”“空气能热水器”，也属于修改，intent 必须是 no。
8. “是的，是安装”“对，但是安装”“不是维修，是安装”“海尔的，要安装”“是空气能热水器” 这些都不是纯确认。
9. 忽略寒暄和语气词，例如“你好啊”“您好啊”“嗯”“哦”“啊”“呀”“哈”“呢”“吧”“嘛”，只看真正表达的品牌/诉求/类型信息。
10. “你好啊，是安装啊。”“嗯，是安装的。”“您好，不是维修，是安装。” 都属于修改诉求，intent 必须是 no。
11. “科目”“科慕”“可么”“扣摸”是 COLMO 的常见同音/近音说法，提取品牌时统一输出 COLMO。
12. “打不开了”“不加热”“没反应”等是故障现象，不是品牌，也不是修改诉求；如果当前确认诉求已经是维修，不要因为故障描述输出 request_type=fault。

示例：
- “对，是美的的，维修” -> {"intent":"yes","brand":"","request_type":"","heater_type":""}
- “是的，是安装。” -> {"intent":"no","brand":"","request_type":"installation","heater_type":""}
- “你好啊，是安装啊。” -> {"intent":"no","brand":"","request_type":"installation","heater_type":""}
- “您好啊，不是维修，是安装。” -> {"intent":"no","brand":"","request_type":"installation","heater_type":""}
- “嗯，是海尔的，安装。” -> {"intent":"no","brand":"海尔","request_type":"installation","heater_type":""}
- “对，但是安装。” -> {"intent":"no","brand":"","request_type":"installation","heater_type":""}
- “对，海尔的。” -> {"intent":"no","brand":"海尔","request_type":"","heater_type":""}
- “不是美的，海尔的” -> {"intent":"no","brand":"海尔","request_type":"","heater_type":""}
- “不是维修，是安装” -> {"intent":"no","brand":"","request_type":"installation","heater_type":""}
- “是空气能热水器” -> {"intent":"no","brand":"","request_type":"","heater_type":"air_energy"}
- “对，是空气能热水器。” -> {"intent":"no","brand":"","request_type":"","heater_type":"air_energy"}
- “海尔的，安装空气能” -> {"intent":"no","brand":"海尔","request_type":"installation","heater_type":"air_energy"}
- “是的，科目的设备打不开了。” -> {"intent":"no","brand":"COLMO","request_type":"","heater_type":""}

只返回 JSON：
{
  "intent": "yes|no|unknown",
  "brand": "修改后的品牌或空字符串",
  "request_type": "installation|fault|",
  "heater_type": "air_energy|gas|electric|water_heater|"
}"""
        system_prompt = (
            system_prompt
            .replace("__PROMPT_BRAND__", prompt_brand)
            .replace("__ACTION__", action)
        )
        payload = self.client.complete_json(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": (
                        f"客服上一句: {previous_service_text}\n"
                        f"当前确认品牌: {current_brand}\n"
                        f"当前确认诉求: {current_request_type}\n"
                        f"[{user_round_index}]用户: {user_text}\n"
                        "只返回 JSON。"
                    ),
                },
            ],
            temperature=0.0,
        )
        resolved = _normalize_opening_resolution_payload(payload)
        if (
            resolved["intent"].strip().lower() == "unknown"
            and not resolved["brand"].strip()
            and not resolved["request_type"].strip()
            and not resolved["heater_type"].strip()
        ):
            repair_prompt = """你是家电客服对话里的热水器确认补判助手。

客服上一句在确认：
1. 品牌是不是指定品牌
2. 品类是不是热水器
3. 诉求是不是安装/维修

你会同时看到客服上一句原话和用户当前回复，要结合这组问答来判断。

你的任务：
只根据用户这一句，补判用户有没有：
1. 仅仅确认，不改任何点
2. 改品牌
3. 改诉求（installation/fault）
4. 指明空气能/燃气/电热

注意：
1. 用户即使开头说“是的”“对”“嗯”，只要后面改了品牌、诉求或类型，都必须视为修改，intent=no。
2. “是的，是安装”“对，安装”“嗯，是海尔的”“对，是空气能热水器” 都属于修改，不是纯确认。
3. 只有纯粹确认、没有新增或修改任何品牌/诉求/类型信息时，intent 才能是 yes。
4. 如果用户直接说“是安装”“安装”“要安装”“是维修”“维修”“要维修”，这就是在明确诉求，不能输出 unknown。
5. 如果当前确认诉求是维修，而用户说“是安装”“安装”，就输出 {"intent":"no","request_type":"installation"}。
6. 如果当前确认诉求是安装，而用户说“是维修”“维修”，就输出 {"intent":"no","request_type":"fault"}。
7. 忽略寒暄和语气词，例如“你好啊”“您好啊”“嗯”“啊”“呀”“哈”“呢”，只看真正表达的品牌/诉求/类型信息。
8. “科目”“科慕”“可么”“扣摸”是 COLMO 的常见同音/近音说法，提取品牌时统一输出 COLMO。
9. “打不开了”“不加热”“没反应”等是故障现象，不是品牌，也不是修改诉求；如果当前确认诉求已经是维修，不要因为故障描述输出 request_type=fault。

只返回 JSON：
{
  "intent": "yes|no|unknown",
  "brand": "修改后的品牌或空字符串",
  "request_type": "installation|fault|",
  "heater_type": "air_energy|gas|electric|water_heater|"
}

示例：
- “是安装。” -> {"intent":"no","brand":"","request_type":"installation","heater_type":""}
- “安装。” -> {"intent":"no","brand":"","request_type":"installation","heater_type":""}
- “要安装。” -> {"intent":"no","brand":"","request_type":"installation","heater_type":""}
- “你好啊，是安装啊。” -> {"intent":"no","brand":"","request_type":"installation","heater_type":""}
- “您好啊，安装。” -> {"intent":"no","brand":"","request_type":"installation","heater_type":""}
- “是维修。” -> {"intent":"no","brand":"","request_type":"fault","heater_type":""}
- “维修。” -> {"intent":"no","brand":"","request_type":"fault","heater_type":""}
- “对，是安装。” -> {"intent":"no","brand":"","request_type":"installation","heater_type":""}
- “对，是维修。” -> {"intent":"no","brand":"","request_type":"fault","heater_type":""}
- “是的，科目的设备打不开了。” -> {"intent":"no","brand":"COLMO","request_type":"","heater_type":""}"""
            repaired_payload = self.client.complete_json(
                model=self.model,
                messages=[
                    {"role": "system", "content": repair_prompt},
                    {
                        "role": "user",
                        "content": (
                            f"客服上一句: {previous_service_text}\n"
                            f"当前确认品牌: {current_brand}\n"
                            f"当前确认诉求: {current_request_type}\n"
                            f"[{user_round_index}]用户: {user_text}\n"
                            "只返回 JSON。"
                        ),
                    },
                ],
                temperature=0.0,
            )
            resolved = _normalize_opening_resolution_payload(repaired_payload)
        if (
            resolved["intent"].strip().lower() == "unknown"
            and not resolved["brand"].strip()
            and not resolved["request_type"].strip()
            and not resolved["heater_type"].strip()
        ):
            extraction_prompt = """你是家电客服对话里的热水器字段提取助手。

任务：
1. 只根据用户这一句，提取是否明确说了品牌、安装/维修诉求、空气能/燃气/电热类型。
1.1 需要结合客服上一句的问题一起看，判断用户是在改什么。
2. 不需要判断整体语气，只需要尽量提取用户明确说出来的字段。
3. 如果用户说“是安装”“安装”“要安装”，request_type 必须输出 installation。
4. 如果用户说“是维修”“维修”“要维修”，request_type 必须输出 fault。
5. 如果用户说“空气能热水器”“燃气热水器”“电热水器”，heater_type 必须输出对应值。
6. 没明确说就留空。
7. 忽略寒暄和语气词，例如“你好啊”“您好”“嗯”“啊”“呀”，不要因为这些词漏掉后面的安装/维修信息。
8. “科目”“科慕”“可么”“扣摸”是 COLMO 的常见同音/近音说法，提取品牌时统一输出 COLMO。
9. “打不开了”“不加热”“没反应”等是故障现象，不是品牌，也不是修改诉求；如果当前确认诉求已经是维修，不要因为故障描述输出 request_type=fault。

只返回 JSON：
{
  "brand": "修改后的品牌或空字符串",
  "request_type": "installation|fault|",
  "heater_type": "air_energy|gas|electric|water_heater|"
}"""
            extracted_payload = self.client.complete_json(
                model=self.model,
                messages=[
                    {"role": "system", "content": extraction_prompt},
                    {
                        "role": "user",
                        "content": (
                            f"客服上一句: {previous_service_text}\n"
                            f"当前确认品牌: {current_brand}\n"
                            f"当前确认诉求: {current_request_type}\n"
                            f"[{user_round_index}]用户: {user_text}\n"
                            "只返回 JSON。"
                        ),
                    },
                ],
                temperature=0.0,
            )
            extracted_brand = str((extracted_payload or {}).get("brand", "")).strip()
            extracted_request_type = str((extracted_payload or {}).get("request_type", "")).strip()
            extracted_heater_type = str((extracted_payload or {}).get("heater_type", "")).strip()
            if extracted_brand or extracted_request_type or extracted_heater_type:
                resolved = {
                    "intent": "no",
                    "brand": extracted_brand,
                    "request_type": extracted_request_type,
                    "heater_type": extracted_heater_type,
                }
        return resolved

    def _extract_issue_description_with_model(
        self,
        *,
        user_text: str,
        user_round_index: int = 0,
    ) -> dict[str, Any]:
        system_prompt = """你是家电客服对话里的故障/诉求描述总结助手。

任务：
1. 从用户原话里总结真正的故障现象、报错信息、使用异常，或安装诉求细节。
2. 去掉“是的、是滴、对的、嗯嗯、侬好、麻烦了”这类确认、寒暄、语气词和无关评价。
3. 保留和客服登记相关的核心问题描述，尽量短而完整。
4. 如果用户原话里没有可提取的有效故障/诉求描述，就返回空字符串。
5. 像“东西坏了”“热水器坏了”“有问题”这类泛泛故障表述不算有效故障描述，返回空字符串。
6. 只有品牌、系列、型号、容量、匹数等产品信息时，也返回空字符串。
7. 如果用户明确说了具体现象，比如“不加热”“出水不热”“开到 80 度烧两小时才 40 度”“忽冷忽热”“漏水”“噪音大”，要提炼出核心故障描述，不要返回空字符串。
8. 如果用户明确说了产品部位或零件哪里坏了，例如“面板坏了”“显示屏坏了”“压缩机坏了”“主板坏了”，这也算有效故障描述，直接提炼核心部位故障。

输出 JSON：
{
  "issue_description": "总结后的核心故障/诉求描述，没有就返回空字符串"
}
"""
        payload = self.client.complete_json(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": f"[{user_round_index}]用户: {user_text}\n只返回 JSON。",
                },
            ],
            temperature=0.0,
        )
        return {"issue_description": str(payload.get("issue_description", "")).strip()}

    def _infer_phone_with_model(
        self,
        *,
        dialogue: list[DialogueTurn],
        user_text: str,
    ) -> dict[str, Any]:
        _ = user_text
        return build_telephone_model_observation(
            dialogue,
            client=self.client,
            model=self.model,
        )

    def _infer_product_routing_intent_with_model(
        self,
        *,
        prompt_key: str,
        user_text: str,
        user_round_index: int = 0,
    ) -> dict[str, Any]:
        system_prompt = """你是家电客服对话里的空气能产品归属分支识别助手。

任务：
1. 根据当前客服问题类型和用户原话，判断用户命中了哪个产品归属分支。
2. 只在下列 answer_key 中选择最贴近的一项；实在无法判断就输出空字符串。
3. 不要脑补用户没说出的信息。
4. answer_key 必须属于当前 prompt_key 对应的候选集合；如果拿不准或跨到了别的节点，返回空字符串。
5. 要忽略常见口头语、犹豫前缀、附带闲聊后再判断真实意图，例如“这个我不清楚，家里人帮我找”“我瞅瞅，单独生活用水的”“应该是送的”“好像是自己买的吧”，都应按核心事实判断，而不是因为前缀口语返回空。
6. 对 brand_or_series 节点要特别注意：
   - 用户在电话里说品牌/系列时，常会出现同音、近音、方言、口误、错别字、音译写法。你需要按“听起来像哪个候选品牌/系列”判断，但前提是该说法不是另一个明确市面品牌。
   - 这个节点不要因为用户带“好像/大概/应该/可能/的”就返回空；这些只是语气词。只要核心音近候选品牌/系列，就输出对应 answer_key。
   - 判断近音时重点看普通话读音、声母/韵母接近程度、电话听感、语音转写常见错字，不要只看字面含义；即使用户写出来的词看起来像普通名词，只要在“空气能品牌/系列”上下文里明显更像候选系列，就按候选系列处理。
   - 示例只用于说明泛化方法，不是穷举词表；遇到未列出的近音、同音、错别字、转写错误，也要按同一原则泛化判断。
   - 用户表示 COLMO，判为 brand_series.colmo
   - 如果用户表达的是疑似 COLMO 的中文音译、谐音、近音、口误说法，且该说法不是另一个明确市面品牌，也判为 brand_series.colmo；例如“科目/科慕”这类听起来接近 COLMO 的说法。
   - 但如果用户说的是另一个明确市面品牌或系列，例如海尔、格力、奥克斯、小天鹅、酷风、真暖、真省、雪焰、暖家、煤改电、真享、烈焰等，不能因为发音相近而归为 COLMO，必须按对应分支判断。
   - 用户表示酷风或小天鹅，判为 brand_series.cooling_or_little_swan
   - 酷风、小天鹅也要识别听起来像的说法、错别字、转写误差。
   - 用户表示真暖、真省、雪焰、暖家、煤改电、真享，判为 brand_series.home_series
   - 真暖、真省、雪焰、暖家、煤改电、真享也要识别听起来像的说法、错别字、转写误差。
   - 用户表示烈焰，判为 brand_series.lieyan
   - 如果用户表达的是疑似“烈焰”的中文音译、谐音、近音、口误说法，且该说法不是另一个明确市面品牌，也判为 brand_series.lieyan；重点泛化识别 lián/liè + yàn/yè 这类电话听感接近“烈焰”的两字表达，不要只匹配已列示例。
   - 用户直接或主动提供具体型号，判为 entry.model
   - 用户说不清楚、提供不了、只知道是美的，判为 entry.unknown
7. 对 usage_scene 节点要特别注意：
   - 家庭、家里、家用、自家、自己家、住宅，判为 scene.family
   - 别墅、公寓、理发店，判为 scene.villa_apartment_barber
   - 其他场所、不知道、不清楚，判为 scene.other_unknown
   - 用户只说“是/不是/对/不对”但没有给出场所，也判为 scene.other_unknown
8. 对 history_device_confirmation 节点要特别注意：
   - 用户确认查询到的历史空气能设备就是本次设备，判为 history_device.yes
   - 用户否定、不确定、不清楚是否一致，判为 history_device.no_unknown
   - 用户先说“对/是/没错/就是这台”等肯定词，后面补充“买了五六年了/时间差不多/确实买过/是那台老机器”等购买时间或背景信息，也必须判为 history_device.yes。
   - 像“不是这台”“不对，不是这个”“不是查询到的那台”“不是名下这台”必须判为 history_device.no_unknown；不要因为句子里包含“是这台”三个字就误判为 yes。
9. 对 purchase_or_property 节点要特别注意：
   - “自己购买 / 我买的 / 后来单独买的” 才是 purchase.self_buy
   - “买房送的 / 交房就有 / 房子原来就有 / 开发商配的 / 楼盘自带” 都是 purchase.property_bundle
   - “应该是送的 / 好像送的 / 可能是送的 / 估计是送的” 也按 purchase.property_bundle
   - “应该是自己买的 / 好像自己买的 / 估计自己买的” 按 purchase.self_buy
   - 句子里出现“自己”这个词，不等于就是 self_buy；例如“房子自己就有”应判为 purchase.property_bundle
10. 对 property_year 节点要特别注意：
   - “21年前 / 2020年 / 19年的楼盘 / 2018年交付” 判为 property_year.before_2021
   - “21年后 / 2022年 / 22年的楼盘” 判为 property_year.after_2021
   - “忘了 / 记不清 / 太久了不记得 / 说不好 / 不清楚”，且用户没提供可辅助判断的大概年份时，判为 property_year.unknown

可选 prompt_key / answer_key：
- brand_or_series: brand_series.colmo | brand_series.cooling_or_little_swan | brand_series.home_series | brand_series.lieyan | entry.model | entry.unknown
- usage_scene: scene.family | scene.villa_apartment_barber | scene.other_unknown
- history_device_confirmation: history_device.yes | history_device.no_unknown
- purchase_or_property: purchase.self_buy | purchase.unknown | purchase.property_bundle
- property_year: property_year.before_2021 | property_year.after_2021 | property_year.unknown

输出 JSON：
{
  "prompt_key": "当前问题类型",
  "answer_key": "命中的 answer_key，没有就返回空字符串"
}
"""
        payload = self.client.complete_json(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": f"当前 prompt_key：{prompt_key}\n[{user_round_index}]用户: {user_text}\n只返回 JSON。",
                },
            ],
            temperature=0.0,
        )
        return {
            "prompt_key": str(payload.get("prompt_key", "")).strip(),
            "answer_key": str(payload.get("answer_key", "")).strip(),
        }

    def respond(
        self,
        *,
        scenario: Scenario,
        transcript: list[DialogueTurn],
        collected_slots: dict[str, str],
        runtime_state: ServiceRuntimeState,
    ) -> dict[str, Any]:
        ensure_product_routing_plan(
            scenario.hidden_context,
            enabled=self.product_routing_enabled,
            apply_probability=self.product_routing_apply_probability,
            model_hint=scenario.product.model,
        )
        result = self.policy.respond(
            scenario=scenario,
            transcript=transcript,
            collected_slots=collected_slots,
            runtime_state=runtime_state,
        )
        return {
            "reply": result.reply,
            "slot_updates": result.slot_updates,
            "is_ready_to_close": result.is_ready_to_close,
            "close_status": result.close_status,
            "close_reason": result.close_reason,
            "used_model_intent_inference": self.policy.last_used_model_intent_inference,
            "model_intent_inference_attempted": self.policy.last_model_intent_inference_attempted,
            "model_intent_inference_unapplied": (
                self.policy.last_model_intent_inference_attempted
                and not self.policy.last_used_model_intent_inference
            ),
        }

    def build_initial_user_utterance(self, scenario: Scenario) -> str:
        return self.policy.build_initial_user_utterance(scenario)
