from __future__ import annotations

import re
from typing import Any

from css_data_synthesis_test.dialogue_plans import resolve_second_round_reply_strategy
from css_data_synthesis_test.llm import OpenAIChatClient
from css_data_synthesis_test.product_routing import (
    ensure_product_routing_plan,
    product_routing_instruction_for_prompt,
)
from css_data_synthesis_test.prompts import build_user_agent_messages, next_address_input_value
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
            if answer_key.startswith("capacity.") and answer_value:
                suffix_options = ("吧", "呢", "")
                suffix = cls._stable_pick(f"{seed}:capacity", suffix_options)
                return f"{answer_value}{suffix}".strip()
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
            address_inference_callback=self._infer_address_candidate_with_model,
            address_collection_acceptance_inference_callback=self._infer_address_collection_acceptance_with_model,
            surname_inference_callback=self._infer_surname_with_model,
            contact_intent_inference_callback=self._infer_contactable_intent_with_model,
            confirmation_intent_inference_callback=self._infer_confirmation_intent_with_model,
            opening_intent_inference_callback=self._infer_opening_intent_with_model,
            issue_description_extraction_callback=self._extract_issue_description_with_model,
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
3. 不要脑补用户没说出的省、市、区、镇、村、小区、门牌号。
4. 可以结合“当前已积累的地址片段”输出一个不含脑补的“合并后最新地址候选”。
5. 如果这一轮没有明确说出可用地址，就返回空字符串。
6. 如果用户说“就这个地方就行”“按前面那个地址”等模糊收尾话术，可以结合“最近对话历史”和“当前已积累的地址片段”总结出用户真正想登记的地址，但不要补出对话里从未出现过的细节。
7. 像“302”“1103”这类裸数字，如果明显是在补充楼栋后的房号，可以按房间号理解。
8. 如果用户已经说到“小区/道路门牌号/楼栋/房号”中的任一足够定位的信息，不要因为缺少单元、楼层就强行补全这些细节。
9. 如果用户说“我说了啊”“前面不是说了吗”“怎么还是这问题”这类明确表示自己已经提供过地址的句子，优先结合“最近对话历史”和“当前已积累的地址片段”总结当前最合理的地址候选；不要返回空字符串。
10. 如果用户这一轮只说到“省/市/区/县/镇/乡/街道”等行政区层级，不要在 merged_address_candidate 里擅自补出小区、楼栋、房号。
11. 像“外卖柜/快递柜/取餐柜/驿站/前台/门岗/保安亭/收发室”这类明确可到达的点位，视为有效地址细节；如果结合已积累地址片段后已经足够定位，不要再强行补楼栋单元。

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
        user_round_index: int = 0,
    ) -> dict[str, Any]:
        system_prompt = """你是家电客服对话里的确认意图识别助手。

任务：
1. 判断用户这句话对当前确认问题的意图是 yes、no 还是 unknown。
2. 仅基于当前用户原话判断，不要脑补未说出的事实。
3. yes 表示确认/肯定/已满足；no 表示否认/未满足；unknown 表示仍无法判断。

当前可能的 prompt_kind：
- phone_number_confirmation：确认刚才识别出的手机号是否正确
- address_confirmation：确认客服正在核对的地址是否正确
- product_arrival_confirmation：确认产品是否已经到货

输出 JSON：
{
  "prompt_kind": "当前问题类型",
  "intent": "yes|no|unknown"
}
"""
        payload = self.client.complete_json(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": f"当前 prompt_kind：{prompt_kind}\n[{user_round_index}]用户: {user_text}\n只返回 JSON。",
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

    def _infer_product_routing_intent_with_model(
        self,
        *,
        prompt_key: str,
        user_text: str,
        user_round_index: int = 0,
    ) -> dict[str, Any]:
        system_prompt = """你是家电客服对话里的产品归属分支识别助手。

任务：
1. 根据当前客服问题类型和用户原话，判断用户命中了哪个产品归属分支。
2. 只在下列 answer_key 中选择最贴近的一项；实在无法判断就输出空字符串。
3. 不要脑补用户没说出的信息。
4. answer_key 必须属于当前 prompt_key 对应的候选集合；如果拿不准或跨到了别的节点，返回空字符串。
5. 要忽略常见口头语、犹豫前缀、附带闲聊后再判断真实意图，例如“这个我不清楚，家里人帮我找”“我瞅瞅，单独生活用水的”“应该是送的”“好像是自己买的吧”，都应按核心事实判断，而不是因为前缀口语返回空。
6. 对 purchase_or_property 节点要特别注意：
   - “自己购买 / 我买的 / 后来单独买的” 才是 purchase.self_buy
   - “买房送的 / 交房就有 / 房子原来就有 / 开发商配的 / 楼盘自带” 都是 purchase.property_bundle
   - “应该是送的 / 好像送的 / 可能是送的 / 估计是送的” 也按 purchase.property_bundle
   - “应该是自己买的 / 好像自己买的 / 估计自己买的” 按 purchase.self_buy
   - 句子里出现“自己”这个词，不等于就是 self_buy；例如“房子自己就有”应判为 purchase.property_bundle
7. 对 capacity_or_hp 节点要特别注意：
   - 明确在 750 升以下或 3 匹以下，判为 capacity.below_threshold，例如“五六百升”“四五百升”“两匹多”
   - 明确在 750 升以上或 3 匹及以上，判为 capacity.above_threshold，例如“八百升”“三匹”“3匹以上”
   - 如果口语范围跨过阈值，统一判为 capacity.unknown，例如“七八百升”“两三匹”“三四匹”
8. 对 property_year 节点要特别注意：
   - “21年前 / 2020年 / 19年的楼盘 / 2018年交付” 判为 property_year.before_2021
   - “21年后 / 2022年 / 22年的楼盘” 判为 property_year.after_2021
   - “忘了 / 记不清 / 太久了不记得 / 说不好 / 不清楚”，且用户没提供可辅助判断的大概年份时，判为 property_year.unknown

可选 prompt_key / answer_key：
- brand_or_series: brand_series.colmo | brand_series.cooling_or_little_swan | brand_series.home_series | brand_series.lieyan | entry.model | entry.unknown
- usage_purpose: purpose.heating | purpose.unknown | purpose.water | purpose.both
- usage_scene: scene.yes | scene.no | scene.unknown
- capacity_or_hp: capacity.above_threshold | capacity.below_threshold | capacity.unknown
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
        }

    def build_initial_user_utterance(self, scenario: Scenario) -> str:
        return self.policy.build_initial_user_utterance(scenario)
