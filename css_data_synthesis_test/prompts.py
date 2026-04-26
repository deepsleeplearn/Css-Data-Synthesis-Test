from __future__ import annotations

from css_data_synthesis_test.address_utils import (
    compact_address_text,
    extract_address_components,
    normalize_address_text,
)
from css_data_synthesis_test.dialogue_plans import (
    SECOND_ROUND_REPLY_CONFIRM_ONLY,
    SECOND_ROUND_REPLY_CONFIRM_WITH_ISSUE,
    normalize_second_round_reply_strategy,
)
from css_data_synthesis_test.product_routing import product_routing_instruction_for_prompt
from css_data_synthesis_test.service_policy import ServiceDialoguePolicy
from css_data_synthesis_test.schemas import (
    SLOT_DESCRIPTIONS,
    DialogueTurn,
    Scenario,
    SERVICE_SPEAKER,
    USER_SPEAKER,
    display_speaker,
    normalize_speaker,
    effective_required_slots,
)


def format_transcript(transcript: list[DialogueTurn]) -> str:
    if not transcript:
        return "暂无历史对话。"
    return "\n".join(f"{display_speaker(turn.speaker)}: {turn.text}" for turn in transcript)


def format_slot_state(required_slots: list[str], collected_slots: dict[str, str]) -> str:
    lines = []
    for slot in required_slots:
        value = collected_slots.get(slot, "").strip() or "未收集"
        description = SLOT_DESCRIPTIONS.get(slot, "未定义槽位")
        lines.append(f"- {slot}: {value} ({description})")
    return "\n".join(lines)


def format_hidden_context(hidden_context: dict[str, str]) -> str:
    if not hidden_context:
        return "无额外隐藏设定。"
    return "\n".join(f"- {key}: {value}" for key, value in hidden_context.items())


def count_phone_keypad_prompts(transcript: list[DialogueTurn]) -> int:
    return sum(
        1
        for turn in transcript
        if normalize_speaker(turn.speaker) == SERVICE_SPEAKER and ServiceDialoguePolicy.is_phone_keypad_prompt(turn.text)
    )


def next_phone_input_value(scenario: Scenario, transcript: list[DialogueTurn]) -> str:
    keypad_prompt_count = count_phone_keypad_prompts(transcript)
    if keypad_prompt_count <= 0:
        return "无"

    hidden_context = scenario.hidden_context
    if keypad_prompt_count == 1:
        return str(hidden_context.get("phone_input_round_1", "")).strip() or "无"
    if keypad_prompt_count == 2:
        return str(hidden_context.get("phone_input_round_2", "")).strip() or "无"
    return str(hidden_context.get("phone_input_round_3", "")).strip() or "无"


def _address_plan_round_values(scenario: Scenario) -> list[str]:
    hidden_context = scenario.hidden_context
    round_values = hidden_context.get("address_input_rounds", [])
    if isinstance(round_values, list):
        normalized_round_values = [str(value).strip() for value in round_values if str(value).strip()]
        if normalized_round_values:
            return normalized_round_values

    fallback_keys = (
        "address_input_round_1",
        "address_input_round_2",
        "address_input_round_3",
        "address_input_round_4",
    )
    fallback_values = [str(hidden_context.get(key, "")).strip() for key in fallback_keys]
    return [value for value in fallback_values if value]


def _address_collection_user_replies(transcript: list[DialogueTurn]) -> list[str]:
    replies: list[str] = []
    for index in range(1, len(transcript)):
        previous_turn = transcript[index - 1]
        current_turn = transcript[index]
        if (
            normalize_speaker(previous_turn.speaker) == SERVICE_SPEAKER
            and ServiceDialoguePolicy.is_address_collection_prompt(previous_turn.text)
            and normalize_speaker(current_turn.speaker) == USER_SPEAKER
        ):
            replies.append(current_turn.text)
    return replies


def _reply_matches_address_value(reply: str, expected: str) -> bool:
    normalized_reply = normalize_address_text(reply)
    normalized_expected = normalize_address_text(expected)
    if not normalized_reply or not normalized_expected:
        return False
    if (
        normalized_reply == normalized_expected
        or normalized_reply in normalized_expected
        or normalized_expected in normalized_reply
    ):
        return True
    return compact_address_text(reply) == compact_address_text(expected)


def _consumed_address_plan_steps(scenario: Scenario, transcript: list[DialogueTurn]) -> int:
    planned_values = _address_plan_round_values(scenario)
    if not planned_values:
        return 0

    actual_address = str(scenario.customer.address or "").strip()
    consumed_steps = 0
    for reply in _address_collection_user_replies(transcript):
        if actual_address and _reply_matches_address_value(reply, actual_address):
            return len(planned_values)
        matched_step = None
        for index in range(consumed_steps, len(planned_values)):
            if _reply_matches_address_value(reply, planned_values[index]):
                matched_step = index
                break
        if matched_step is not None:
            consumed_steps = matched_step + 1
    return consumed_steps


def _last_address_collection_prompt_text(transcript: list[DialogueTurn]) -> str:
    if not transcript:
        return ""
    last_turn = transcript[-1]
    if (
        normalize_speaker(last_turn.speaker) == SERVICE_SPEAKER
        and ServiceDialoguePolicy.is_address_collection_prompt(last_turn.text)
    ):
        return last_turn.text
    return ""


def _address_region_street_value(
    address: str,
    *,
    include_province: bool = True,
    include_city: bool = True,
    include_district: bool = True,
) -> str:
    components = extract_address_components(address)
    parts: list[str] = []
    if include_province and components.province:
        parts.append(components.province)
    if include_city and components.city:
        parts.append(components.city)
    if include_district and components.district:
        parts.append(components.district)
    locality = components.town or components.road
    if locality:
        parts.append(locality)
    return "".join(parts) or str(address or "").strip()


def _address_precise_detail_value(address: str) -> str:
    components = extract_address_components(address)
    detail = "".join(
        part
        for part in (components.building, components.unit, components.floor, components.room)
        if part
    )
    if detail:
        return detail
    group_token = ServiceDialoguePolicy._extract_village_group_token(address)
    house_token = ServiceDialoguePolicy._extract_house_number_token(address)
    return f"{group_token}{house_token}" if group_token or house_token else str(address or "").strip()


def _address_locality_detail_value(address: str) -> str:
    components = extract_address_components(address)
    parts: list[str] = []
    if ServiceDialoguePolicy._is_rural_address_candidate(address):
        parts.extend(part for part in (components.town, components.road, components.community) if part)
        group_token = ServiceDialoguePolicy._extract_village_group_token(address)
        house_token = ServiceDialoguePolicy._extract_house_number_token(address)
        if group_token:
            parts.append(group_token)
        if house_token:
            parts.append(house_token)
        return "".join(parts) or str(address or "").strip()

    if components.community:
        parts.append(components.community)
    elif components.road:
        parts.append(components.road)
    elif components.town:
        parts.append(components.town)

    detail = _address_precise_detail_value(address)
    if detail and detail not in "".join(parts):
        parts.append(detail)
    return "".join(parts) or str(address or "").strip()


def _plan_value_is_too_fine_for_full_prompt(value: str) -> bool:
    components = extract_address_components(value)
    return (
        not components.has_admin_region
        and (
            components.has_locality
            or components.has_precise_detail
            or ServiceDialoguePolicy._has_nonstandard_address_detail(value)
        )
    )


def _prompt_shaped_address_value(
    scenario: Scenario,
    transcript: list[DialogueTurn],
    planned_values: list[str],
    consumed_steps: int,
) -> str:
    actual_address = str(scenario.customer.address or "").strip()
    planned_value = planned_values[consumed_steps] if consumed_steps < len(planned_values) else actual_address
    last_service_text = _last_address_collection_prompt_text(transcript)
    if not last_service_text:
        return planned_value or actual_address

    normalized_prompt = ServiceDialoguePolicy._normalize_prompt_text(last_service_text)
    if ServiceDialoguePolicy._signature_matches_prompt(
        last_service_text,
        ServiceDialoguePolicy.ADDRESS_REGION_STREET_FOLLOWUP_PROMPT,
    ):
        return _address_region_street_value(actual_address)
    if (
        ServiceDialoguePolicy._signature_matches_prompt(
            last_service_text,
            ServiceDialoguePolicy.ADDRESS_DISTRICT_STREET_FOLLOWUP_PROMPT,
        )
        or normalized_prompt.startswith("您是在")
    ):
        return _address_region_street_value(
            actual_address,
            include_province=False,
            include_city=False,
        )
    if ServiceDialoguePolicy._signature_matches_prompt(
        last_service_text,
        ServiceDialoguePolicy.ADDRESS_LOCALITY_FOLLOWUP_PROMPT,
    ):
        return _address_locality_detail_value(actual_address)
    if ServiceDialoguePolicy._signature_matches_prompt(
        last_service_text,
        ServiceDialoguePolicy.ADDRESS_BUILDING_FOLLOWUP_PROMPT,
    ):
        return _address_precise_detail_value(actual_address)
    if ServiceDialoguePolicy._signature_matches_prompt(
        last_service_text,
        ServiceDialoguePolicy.ADDRESS_HOUSE_NUMBER_FOLLOWUP_PROMPT,
    ) or ServiceDialoguePolicy._signature_matches_prompt(
        last_service_text,
        ServiceDialoguePolicy.ADDRESS_RURAL_DETAIL_FOLLOWUP_PROMPT,
    ):
        return _address_locality_detail_value(actual_address)
    if (
        ServiceDialoguePolicy._signature_matches_prompt(
            last_service_text,
            ServiceDialoguePolicy.ADDRESS_PROMPT,
        )
        and _plan_value_is_too_fine_for_full_prompt(planned_value)
    ):
        return _address_region_street_value(actual_address)
    return planned_value or actual_address


def next_address_input_value(scenario: Scenario, transcript: list[DialogueTurn]) -> str:
    if count_address_collection_prompts(transcript) <= 0:
        return "无"

    planned_values = _address_plan_round_values(scenario)
    if not planned_values:
        return str(scenario.customer.address or "").strip() or "无"

    consumed_steps = _consumed_address_plan_steps(scenario, transcript)
    if consumed_steps < len(planned_values):
        return _prompt_shaped_address_value(scenario, transcript, planned_values, consumed_steps)
    return str(scenario.customer.address or "").strip() or planned_values[-1]


def count_phone_keypad_prompts(transcript: list[DialogueTurn]) -> int:
    return sum(
        1
        for turn in transcript
        if normalize_speaker(turn.speaker) == SERVICE_SPEAKER
        and ServiceDialoguePolicy.is_phone_keypad_prompt(turn.text)
    )


def count_address_collection_prompts(transcript: list[DialogueTurn]) -> int:
    return sum(
        1
        for turn in transcript
        if normalize_speaker(turn.speaker) == SERVICE_SPEAKER
        and ServiceDialoguePolicy.is_address_collection_prompt(turn.text)
    )


def _count_service_prompts(transcript: list[DialogueTurn], predicate) -> int:
    return sum(
        1
        for turn in transcript
        if normalize_speaker(turn.speaker) == SERVICE_SPEAKER and predicate(turn.text)
    )


def count_surname_prompts(transcript: list[DialogueTurn]) -> int:
    return _count_service_prompts(transcript, ServiceDialoguePolicy.is_surname_prompt)


def count_contactable_prompts(transcript: list[DialogueTurn]) -> int:
    return _count_service_prompts(transcript, ServiceDialoguePolicy.is_contactable_prompt)


def count_product_arrival_prompts(transcript: list[DialogueTurn]) -> int:
    return _count_service_prompts(transcript, ServiceDialoguePolicy.is_product_arrival_prompt)


def count_product_model_prompts(transcript: list[DialogueTurn]) -> int:
    return _count_service_prompts(transcript, ServiceDialoguePolicy.is_product_model_prompt)


def is_replying_to_service_opening(
    scenario: Scenario,
    transcript: list[DialogueTurn],
    round_index: int,
) -> bool:
    if round_index != 2 or not transcript:
        return False
    last_turn = transcript[-1]
    if normalize_speaker(last_turn.speaker) != SERVICE_SPEAKER:
        return False
    opening_prompt = ServiceDialoguePolicy()._build_opening_prompt(scenario)
    return (
        ServiceDialoguePolicy._normalize_prompt_text(last_turn.text)
        == ServiceDialoguePolicy._normalize_prompt_text(opening_prompt)
    )


def build_topic_guardrail_note(transcript: list[DialogueTurn]) -> str:
    if not transcript:
        return "当前没有额外的话题限制。"

    last_turn = transcript[-1]
    if normalize_speaker(last_turn.speaker) != SERVICE_SPEAKER:
        return "当前没有额外的话题限制。"

    last_service_text = last_turn.text
    if ServiceDialoguePolicy.is_contactable_prompt(last_service_text):
        return (
            "当前客服在确认这个来电号码能否联系到你。你只需要先明确回答能联系或不能联系；"
            "如果不能联系，可以顺带说留谁的号码，但不要提前纠正地址、不要报完整号码、"
            "也不要跳去讲故障、型号或其他旧信息。"
        )
    if ServiceDialoguePolicy.is_phone_confirmation_prompt(last_service_text):
        return (
            "当前客服在核对号码。你只需要回答对或不对，不要重复号码本身，"
            "也不要再扯回故障、地址、型号等已经讨论过的内容。"
        )
    if "到货了没" in last_service_text:
        return (
            "当前客服在确认产品是否到货。你只需要围绕“是否到货”回答；"
            "如果想补充，也只补 1 句新的安装相关信息，比如摆放情况、上门时间偏好、家里是否有人。"
            "不要重复前面已经确认过的安装诉求。"
        )
    if ServiceDialoguePolicy.is_address_confirmation_prompt(last_service_text):
        return (
            "当前客服在核对地址。地址正确就只简短确认；地址不对就否定并按需要更正地址。"
            "不要在这一轮再重复故障、电话、型号或其他旧信息。"
        )
    if ServiceDialoguePolicy.is_address_collection_prompt(last_service_text):
        if ServiceDialoguePolicy._signature_matches_prompt(
            last_service_text,
            ServiceDialoguePolicy.ADDRESS_PROMPT,
        ):
            return (
                "当前客服是在要求你完整说明地址。你不要只回答室号、楼层、单元或楼栋尾巴；"
                "优先从省、市、区开始说，至少先说到区县，比较自然的答法通常会继续到镇/街道这一层。"
            )
        if ServiceDialoguePolicy._signature_matches_prompt(
            last_service_text,
            ServiceDialoguePolicy.ADDRESS_REGION_STREET_FOLLOWUP_PROMPT,
        ):
            return (
                "当前客服只在追问省、市、区和街道。你这一轮优先只补行政区和镇/街道，"
                "不要顺手把小区、楼栋、单元、室号一口气全说完。"
            )
        if ServiceDialoguePolicy._signature_matches_prompt(
            last_service_text,
            ServiceDialoguePolicy.ADDRESS_DISTRICT_STREET_FOLLOWUP_PROMPT,
        ) or ServiceDialoguePolicy._normalize_prompt_text(last_service_text).startswith("您是在"):
            return (
                "当前客服只在追问区和街道。你这一轮优先补区县和镇/街道，"
                "不要继续往下说到小区、楼栋、单元、室号。"
            )
        if ServiceDialoguePolicy._signature_matches_prompt(
            last_service_text,
            ServiceDialoguePolicy.ADDRESS_LOCALITY_FOLLOWUP_PROMPT,
        ):
            return (
                "当前客服在追问具体小区、村或更细门牌。你这一轮优先补小区/村和门牌细节，"
                "不要再从省、市、区重新说起。"
            )
        return (
            "当前客服在收集地址。你只说当前需要补充的地址信息本体；"
            "不要补充路线指引、附近地标、怎么走、门口标识、停车说明、‘你懂的’这类口头补充。"
            "除非这些内容本身就是正式地址的一部分，否则不要说。"
        )
    if ServiceDialoguePolicy.is_closing_notice_prompt(last_service_text):
        return (
            "当前客服是在通知工单已受理并准备收尾。你通常只简短确认即可，比如“好的”“知道了”。"
            "不要再重复地址、故障、电话、型号等前面已经说过的内容。"
        )
    if ServiceDialoguePolicy.is_satisfaction_prompt(last_service_text):
        return (
            "当前客服是在邀请你对本次通话打分。你必须只回复单个数字“1”或“2”，"
            "不要回复“挺好的”“满意”“好的”之类的自然语言，也不要补充其他内容。"
        )
    return "当前没有额外的话题限制。"


def build_repeat_prompt_guardrail_note(scenario: Scenario, transcript: list[DialogueTurn]) -> str:
    if not transcript:
        return "当前没有额外的重复追问约束。"

    last_turn = transcript[-1]
    if normalize_speaker(last_turn.speaker) != SERVICE_SPEAKER:
        return "当前没有额外的重复追问约束。"

    last_service_text = last_turn.text
    if ServiceDialoguePolicy.is_surname_prompt(last_service_text):
        prompt_count = count_surname_prompts(transcript)
        if prompt_count >= 2:
            return (
                f"客服已第 {prompt_count} 次询问姓氏。你这一轮必须直接回答姓氏相关信息，"
                "可以简短说“我姓王”或直接说姓氏，不能继续答非所问，也不要重复上一轮自己说过的安装、维修或确认话术。"
            )
        return "当前客服在问姓氏。优先自然回答姓氏相关信息，比如“我姓王”“免贵姓王”，不要重复之前已经说过的诉求。"

    if ServiceDialoguePolicy.is_product_arrival_prompt(last_service_text):
        prompt_count = count_product_arrival_prompts(transcript)
        if prompt_count >= 2:
            return (
                f"客服已第 {prompt_count} 次确认产品是否到货。你这一轮必须直接回答是否到货，"
                "不要继续复述之前的安装诉求或上一轮原话。"
            )
        return "当前客服在确认产品是否到货。你只围绕是否到货回答，不要重复安装诉求。"

    if ServiceDialoguePolicy.is_contactable_prompt(last_service_text):
        prompt_count = count_contactable_prompts(transcript)
        if prompt_count >= 2:
            return (
                f"客服已第 {prompt_count} 次确认这个来电号码能否联系到你。你这一轮必须直接回答能联系或不能联系，"
                "不要再跳去说地址纠错、故障细节、完整号码或上一轮原话。"
            )
        return "当前客服在确认这个来电号码能否联系到你。你只围绕能否联系回答，不要扯到地址纠错或其他旧话题。"

    if ServiceDialoguePolicy.is_product_model_prompt(last_service_text):
        prompt_count = count_product_model_prompts(transcript)
        if prompt_count >= 2:
            return (
                f"客服已第 {prompt_count} 次询问型号。你这一轮必须直接回答型号相关信息，"
                "不要继续答非所问，也不要复读上一轮旧内容。"
            )
        return "当前客服在问型号。你只回答型号相关信息，不要展开旧话题。"

    if ServiceDialoguePolicy.is_address_collection_prompt(last_service_text):
        prompt_count = count_address_collection_prompts(transcript)
        if prompt_count >= 2:
            return (
                f"客服已第 {prompt_count} 次追问地址。你这一轮必须直接补当前缺失的地址信息，"
                f"优先按“{next_address_input_value(scenario, transcript)}”来答；"
                "不要再说“刚刚那个地址应该挺清楚了”之类的重复话术。"
            )
        return "当前客服在追问地址。你只补当前还没说到的那部分地址，不要重复上一轮原话。"

    return "当前没有额外的重复追问约束。"


def build_product_routing_note(transcript: list[DialogueTurn], scenario: Scenario) -> str:
    step = product_routing_instruction_for_prompt(transcript, scenario.hidden_context)
    if not step:
        return "当前没有产品归属中间路由限制。"

    answer_value = str(step.get("answer_value", "")).strip() or "无"
    answer_instruction = str(step.get("answer_instruction", "")).strip() or "围绕当前路由节点自然回答。"
    answer_key = str(step.get("answer_key", "")).strip() or "unknown"
    prompt_key = str(step.get("prompt_key", "")).strip()
    capacity_note = ""
    unknown_note = ""
    if answer_key.startswith("capacity."):
        capacity_note = (
            " 如果是在回答容量或匹数，通常只说自己更确定的一个维度，"
            "优先只说升数或匹数其中一个，不要把两个都报出来。"
        )
    if answer_key.endswith(".unknown"):
        unknown_note = (
            " 如果当前节点本身就是“不清楚/不确定”，优先一两句直接表达不知道、"
            "不确定、记不清就够了；不要先猜一个答案再否定，不要同时枚举多个可能，"
            "不要为了显得自然而故意说得很长。"
        )
    else:
        unknown_note = (
            " 当前节点已经有明确目标答案，禁止回答“不清楚、不知道、不确定、应该不是、可能不是”"
            "这类模糊或否定目标答案的话；必须明确表达参考事实本身。"
        )
    if answer_key == "scene.family":
        unknown_note += " 本轮必须明确说是在家里/家庭使用，禁止说“不是家里用”“不清楚是不是家里用”。"
    if prompt_key == "usage_scene" and not answer_key.endswith(".unknown"):
        unknown_note += (
            " 本轮是在回答使用场所，必须只表达一个明确场所；"
            "如果事实是家庭就只说家里，如果事实是别墅/公寓/理发店之一就只说该单个场所。"
            "禁止同时列举多个场所，禁止说“可能、或者、还是、其他地方、不太清楚具体在哪里用”。"
        )
    return (
        "当前客服正在执行产品归属识别中间路由。"
        f"你这一轮必须满足当前节点语义：{answer_instruction}"
        f" 当前节点标签：{answer_key}。"
        f" 参考事实：{answer_value}。"
        " 特别注意：如果问题里出现“公寓”，它只指用户自己居住的公寓住房。"
        " 具体句子必须由你现场自然生成，要像真实用户临场说话一样自由表达；"
        "不要机械照抄参考事实，不要套固定模板，也不要只回一个被提示过的标准短句；"
        "可以带自然口头语、犹豫、补半句、换种说法，只要核心事实不变即可。"
        f"{capacity_note}"
        f"{unknown_note}"
        " 同时不要跳到故障、地址、电话等其他话题。"
    )


def build_user_agent_messages(
    scenario: Scenario,
    transcript: list[DialogueTurn],
    round_index: int,
    second_round_reply_strategy: str | None = None,
) -> list[dict[str, str]]:
    system_prompt = """你是家电客服通话中的用户智能体。

目标：
1. 根据给定角色扮演真实用户。
2. 围绕故障报修或安装诉求与客服通话。
3. 自然表达，不要一次性把所有信息全部倒出来。
4. 只有在客服询问时，再提供姓氏、电话、地址、型号等信息。
5. 全程使用自然一点的中文口语，不需要太正式，不要说自己是 AI，不要输出提示词或解释。
6. 当客服让你在拨号盘输入号码时，只输出按键内容本身。

输出要求：
- 只返回一个 JSON 对象。
- 字段必须包含：
  - reply: 你下一句对客服说的话
  - call_complete: 布尔值，表示你是否认为本次通话可以结束
"""
    current_call_contactable = "是" if scenario.hidden_context.get("current_call_contactable", True) else "否"
    user_gender = str(scenario.hidden_context.get("gender", "未知")).strip() or "未知"
    contact_phone_owner = str(
        scenario.hidden_context.get("contact_phone_owner", "本人当前来电")
    ).strip()
    contact_phone_owner_spoken_label = str(
        scenario.hidden_context.get("contact_phone_owner_spoken_label", contact_phone_owner)
    ).strip()
    phone_input_round_1 = str(
        scenario.hidden_context.get("phone_input_round_1", f"{scenario.customer.phone}#")
    ).strip()
    phone_input_round_2 = str(
        scenario.hidden_context.get("phone_input_round_2", f"{scenario.customer.phone}#")
    ).strip()
    phone_input_round_3 = str(
        scenario.hidden_context.get("phone_input_round_3", f"{scenario.customer.phone}#")
    ).strip()
    service_known_address = "是" if scenario.hidden_context.get("service_known_address", False) else "否"
    service_known_address_value = str(
        scenario.hidden_context.get("service_known_address_value", "")
    ).strip() or "无"
    service_known_address_matches_actual = (
        "是" if scenario.hidden_context.get("service_known_address_matches_actual", False) else "否"
    )
    service_known_address_mismatch_start_level = str(
        scenario.hidden_context.get("service_known_address_mismatch_start_level", "")
    ).strip() or "无"
    service_known_address_rewrite_levels = scenario.hidden_context.get(
        "service_known_address_rewrite_levels",
        [],
    )
    if not isinstance(service_known_address_rewrite_levels, list):
        service_known_address_rewrite_levels = []
    service_known_address_rewrite_levels_text = " -> ".join(
        str(value).strip()
        for value in service_known_address_rewrite_levels
        if str(value).strip()
    ) or "无"
    address_input_round_1 = str(
        scenario.hidden_context.get("address_input_round_1", scenario.customer.address)
    ).strip()
    address_input_round_2 = str(
        scenario.hidden_context.get("address_input_round_2", scenario.customer.address)
    ).strip()
    address_input_rounds = scenario.hidden_context.get("address_input_rounds", [])
    if not isinstance(address_input_rounds, list):
        address_input_rounds = []
    address_input_rounds_text = " / ".join(
        str(value).strip() for value in address_input_rounds if str(value).strip()
    ) or f"{address_input_round_1} / {address_input_round_2}"
    address_confirmation_no_reply = str(
        scenario.hidden_context.get("address_confirmation_no_reply", "不对。")
    ).strip()
    user_address_style = str(
        scenario.hidden_context.get("user_address_style", "standard_residential")
    ).strip() or "standard_residential"
    user_address_style_instruction = str(
        scenario.hidden_context.get("user_address_style_instruction", "")
    ).strip() or "默认标准住宅地址"
    user_reply_noise_enabled = (
        "是" if bool(scenario.hidden_context.get("user_reply_noise_enabled", False)) else "否"
    )
    user_reply_noise_target = str(
        scenario.hidden_context.get("user_reply_noise_target", "")
    ).strip() or "无"
    try:
        user_reply_noise_rounds = int(scenario.hidden_context.get("user_reply_noise_rounds", 0) or 0)
    except (TypeError, ValueError):
        user_reply_noise_rounds = 0
    user_reply_noise_instruction = str(
        scenario.hidden_context.get("user_reply_noise_instruction", "")
    ).strip() or "整体正常配合客服，不需要刻意答非所问。"
    product_arrived = "是" if str(scenario.hidden_context.get("product_arrived", "yes")).strip().lower() == "yes" else "否"
    resolved_second_round_reply_strategy = normalize_second_round_reply_strategy(
        second_round_reply_strategy or scenario.hidden_context.get("second_round_reply_strategy", "")
    )
    replying_to_opening = is_replying_to_service_opening(scenario, transcript, round_index)
    second_round_strategy_text = (
        "确认后顺带用一句话说出当前故障现象或安装需求"
        if resolved_second_round_reply_strategy == SECOND_ROUND_REPLY_CONFIRM_WITH_ISSUE
        else "只做简短确认，不继续补充故障或安装细节"
    )
    topic_guardrail_note = build_topic_guardrail_note(transcript)
    repeat_prompt_guardrail_note = build_repeat_prompt_guardrail_note(scenario, transcript)
    product_routing_note = build_product_routing_note(transcript, scenario)
    expression_mode_note = f"""
第二轮回复策略补充要求：
1. 当你是在直接回应客服开场确认时，必须严格执行本场景的固定策略，不要临场自行切换。
2. 当前这轮是否正在回应客服开场确认: {"是" if replying_to_opening else "否"}
3. 本场景第二轮回复策略: {second_round_strategy_text}
4. 如果策略是“只做简短确认，不继续补充故障或安装细节”，就只回答“对，是的”“嗯，需要”这类简短确认，不要继续展开。
5. 如果策略是“确认后顺带用一句话说出当前故障现象或安装需求”，就要在确认后自然补一句 1 个核心故障现象或安装需求，控制在一句话内。
6. 如果这一轮还没被客服明确追问故障现象、安装需求、问题描述，就不要为了补全信息而强行多说。
7. 故障场景下，默认只围绕“问题或安装描述”里的 1 个核心故障点表达；只有当隐藏设定本身明确包含 2 个相关故障点时，才允许自然提到这 2 个，不要扩展到第 3 个。
8. 说法要自然，不能像在背规则。

当前话题限制：
{topic_guardrail_note}

重复追问约束：
{repeat_prompt_guardrail_note}

产品归属中间路由约束：
{product_routing_note}
""".strip()
    user_prompt = f"""当前是第 {round_index} 轮。

隐藏设定：
- 用户姓名: {scenario.customer.full_name}
- 用户姓氏: {scenario.customer.surname}
- 用户性别: {user_gender}
- 用户电话: {scenario.customer.phone}
- 用户地址: {scenario.customer.address}
- 用户画像: {scenario.customer.persona}
- 用户说话方式: {scenario.customer.speech_style or '未特别设定'}
- 产品品牌: {scenario.product.brand}
- 产品品类: {scenario.product.category}
- 产品型号: {scenario.product.model}
- 购买渠道: {scenario.product.purchase_channel or '未提供'}
- 诉求类型: {scenario.request.request_type}
- 通话开始时间: {scenario.call_start_time or '未提供'}
- 问题或安装描述: {scenario.request.issue}
- 希望结果: {scenario.request.desired_resolution}
- 可预约时间: {scenario.request.availability or '未提供'}
- 安装场景下产品是否已到货: {product_arrived}
- 当前来电是否可以联系到用户: {current_call_contactable}
- 如果当前来电不能联系，登记号码归属: {contact_phone_owner}
- 如果当前来电不能联系，如需自然提到联系人，可参考这个含义相近的口语称呼: {contact_phone_owner_spoken_label}
- 若客服要求拨号盘输入号码，第 1 次应输入: {phone_input_round_1}
- 若客服要求拨号盘输入号码，第 2 次应输入: {phone_input_round_2}
- 若客服要求拨号盘输入号码，第 3 次应输入: {phone_input_round_3}
- 当前已被要求拨号盘输入号码的次数: {count_phone_keypad_prompts(transcript)}
- 如果这轮正被要求拨号盘输入，本轮应输入: {next_phone_input_value(scenario, transcript)}
- 当前已被问姓氏的次数: {count_surname_prompts(transcript)}
- 当前已被问到货情况的次数: {count_product_arrival_prompts(transcript)}
- 当前已被问型号的次数: {count_product_model_prompts(transcript)}
- 当前已被问当前号码能否联系的次数: {count_contactable_prompts(transcript)}
- 客服侧是否已知地址: {service_known_address}
- 若客服已知地址，客服掌握的地址内容: {service_known_address_value}
- 若客服已知地址，该地址是否与真实地址一致: {service_known_address_matches_actual}
- 若客服已知地址但地址不对，错误起始粒度: {service_known_address_mismatch_start_level}
- 若客服已知地址但地址不对，需要重塑的地址粒度链路: {service_known_address_rewrite_levels_text}
- 若客服核对了错误地址，这一轮可参考答法: {address_confirmation_no_reply}
- 若客服第一次询问地址信息，第 1 次应答: {address_input_round_1}
- 若客服继续追问剩余地址细节，第 2 次应答: {address_input_round_2}
- 地址分段回复计划: {address_input_rounds_text}
- 当前已被要求提供地址信息的次数: {count_address_collection_prompts(transcript)}
- 如果这轮正被要求补充地址信息，本轮应答: {next_address_input_value(scenario, transcript)}
- 用户地址形态类型: {user_address_style}
- 用户地址形态说明: {user_address_style_instruction}
- 是否允许轻微答非所问: {user_reply_noise_enabled}
- 若允许，目标环节: {user_reply_noise_target}
- 若允许，该环节最多可轻微答偏的轮数: {user_reply_noise_rounds}
- 若允许，本场景的轻微答偏说明: {user_reply_noise_instruction}
- 额外隐藏设定:
{format_hidden_context(scenario.hidden_context)}

历史对话：
{format_transcript(transcript)}

{expression_mode_note}

回复规则：
1. 如果这一轮是在直接回应客服开场确认，严格按照“本场景第二轮回复策略”执行；不是这个场景时，再按客服实际追问自然回答。
2. 故障场景下，默认只围绕隐藏设定中的 1 个故障点来描述；只有当隐藏设定本身已经明确给了 2 个相关故障点时，才可以一起提到，但不要再继续追加第 3 个问题或过多温度对比数据。
3. 如果客服问“请问您贵姓”，无论前面是否带“好的”或其他安抚前缀，都只回答姓氏相关信息；首次优先用自然口语，如“我姓王”“免贵姓王”“姓王”，不要机械只蹦一个字；如果已经被重复追问两次及以上，就更直接简短。
4. 如果客服问当前来电号码能否联系到你，严格按照隐藏设定回答；这一轮必须先明确回答“能联系”或“不能联系”。如果不能联系，可以顺带说明留谁的号码，但不要直接口述完整号码，也不要说“待会输入号码”“等会再报号码”这类后续流程话；表达上可以自然地用含义相近的口语称呼，不必拘泥于登记标签原词。
5. 如果客服要求你在拨号盘上输入联系方式并以#号键结束，只输出本轮应输入的内容，不要附带任何解释。
6. 如果客服用“号码是某个号码，对吗”这类话术核对号码，无论前面是否带“好的”，都根据事实回答对或不对。
7. 如果客服用“跟您确认一下，地址是某个地址，对吗？”或“您的地址是某个地址，对吗？”这类话术核对地址，无论前面是否带“好的”，都要根据隐藏设定回答；如果地址正确，通常只简短表示肯定，不要重复完整地址；如果地址不对，就参考“若客服核对了错误地址，这一轮可参考答法”里的事实去否认或更正，但不必逐字复述那句话，可以自然地说成“应该是2单元”“不是，是4单元602室”“不对，改成5栋2单元”这类口语化表达。
8. 如果客服问地址，你可以按隐藏设定分几轮逐步补充；客服继续追问缺失部分时，就只补当前还没说到的那部分，也可以在合适时直接给出完整地址。完整地址确认完后，如果客服再按固定话术核对地址，就只做简短确认。特别注意：如果客服让你“完整说下省、市、区、乡镇，精确到门牌号”，不要只回“803室”“2单元”“3栋”这类尾巴；如果客服只追问“省、市、区和街道”或“区和街道”，就优先只答到行政区和镇/街道，不要继续一口气说到小区楼栋室号。
9. 如果客服问产品或者产品到货了没，就按隐藏设定回答，说话不需要太正式，口语化些；已经确认过“要安装/要维修”后，不要把同一句诉求又重复一遍，除非客服重新追问。
10. 如果客服通知“工单已受理成功”并说明后续联系时间，这一轮通常只做简短确认回复。
11. 如果客服要求你对本次通话按 1 到 5 打分，必须只回复单个数字“1”或“2”；不要回复“挺好的”“满意”“好的”等自然语言，也不要输出其他解释。
12. 除了客服明确问到的内容，不要主动再说已经沟通过的诉求、地址、电话号码等；如果要补充，也优先补充新的细节，不要原句复述上一轮已经说过的话。
13. 回复风格要明显符合“用户画像”和“用户说话方式”；如果设定为简短就少说，如果设定为啰嗦就自然多解释一点，如果设定为略有停顿或结巴，只能轻微体现，不能夸张到影响理解。
14. 已经确认过的旧信息，不要在后续不相关话题里重复；尤其在号码核对、地址核对、工单受理收尾这几类场景里，只围绕当前话题简短回答。
15. 如果本场景允许“轻微答非所问”，只能按隐藏设定说明在对应环节发生，而且最多持续给定的轮数；必须是轻微偏题或先说一部分，不能离题太远，也不能超过配置轮数；客服再次追问后要恢复正常配合。
16. 地址表达要符合“用户地址形态类型”：标准住宅地址可以自然说栋/单元/室；门牌号型地址可以只说到多少号；乡村组号型地址可以说到村、组、号；地标型地址可以自然提到医院、饭店、酒店、园区、学校、门店等，但仍要给出足够定位的信息。
17. 对非电话、非地址槽位，如果客服已经第 2 次或更多次重复追问同一项，这一轮必须直接回答该槽位，不能继续答非所问。
18. 如果上一轮你已经对同一个问题答偏了，这一轮不要复述上一轮自己说过的话，要直接回答当前问题。
19. 如果当前处于产品归属中间路由节点，你必须严格满足该节点语义，但具体表述要尽可能像真实用户自由发挥，允许自然口头语和个人表达习惯；不要把系统给你的参考事实原样硬拷贝成固定模板句，也不要把前面已经说过的故障现象再重复一遍。
20. 如果客服在问品牌、系列、型号、用途、场所、楼盘配套、楼盘时间、容量或匹数，你都应当优先“表达自己的话”，而不是追求最短标准答案；前提是不要偏离当前问题要求的事实边界。尤其回答容量或匹数时，通常只说自己更确定的一个维度，优先说升数或匹数其中一个。若产品归属节点给了明确目标答案，不能说成“不清楚”“应该不是”“可能不是”这类模糊或相反含义。
21. 输出文本要符合 ASR 转写风格，不要使用“...”或“……”来表示停顿；如果要体现停顿，只能用自然口语词或逗号，不能出现省略号字符。
22. 如果客服当前是在收集地址，你只说地址信息本体，不要加入“在小卖部旁边”“红绿灯往南走”“你知道的”这类路线、地标、解释性补充，除非这些词本身就是正式地址的一部分。

请直接给出 JSON。"""
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]


def build_service_agent_messages(
    scenario: Scenario,
    transcript: list[DialogueTurn],
    round_index: int,
    collected_slots: dict[str, str],
) -> list[dict[str, str]]:
    system_prompt = """你是家电客服智能体，负责处理报修或安装电话。

目标：
1. 自然地与用户通话。
2. 优先收集必需槽位，不要漏项。
3. 不要编造任何槽位值，只能根据用户明确表达更新。
4. 每轮尽量只推进 1 到 2 个关键信息点，保持客服口语化。
5. 当必需槽位都收齐后，做简短复述并礼貌结束通话。

输出要求：
- 只返回一个 JSON 对象。
- 字段必须包含：
  - reply: 你对用户说的话
  - slot_updates: 一个对象，仅填写本轮刚确认到的槽位和值；没有新信息时返回空对象
  - is_ready_to_close: 布尔值，表示你是否认为信息已收集完成并准备收尾
"""
    user_prompt = f"""当前是第 {round_index} 轮。

场景范围：
- 这是一次家电客服电话，可能是故障报修，也可能是安装预约
- 你不能使用任何未在历史对话中出现的用户真值信息
- 只有在用户明确表达后，才能更新对应槽位

本场景要求收集的槽位：
{format_slot_state(effective_required_slots(scenario), collected_slots)}

历史对话：
{format_transcript(transcript)}

请基于当前缺失信息决定下一句客服话术，并仅返回 JSON。"""
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
