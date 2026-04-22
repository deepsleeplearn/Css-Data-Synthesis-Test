from __future__ import annotations

import inspect
import random
import re
from dataclasses import dataclass, field
from typing import Any, Callable

from css_data_synthesis_test.address_utils import (
    BUILDING_SUFFIXES,
    LANDMARK_LOCALITY_SUFFIXES,
    MUNICIPALITY_PREFIXES,
    PROVINCE_PREFIXES,
    AddressComponents,
    canonicalize_address_text,
    comparable_component,
    compact_address_text,
    components_match,
    extract_address_components,
    normalize_address_text,
)
from css_data_synthesis_test.product_routing import (
    ROUTING_RESULT_HUMAN,
    allowed_product_routing_answer_keys,
    default_unknown_product_routing_answer_key,
    get_product_routing_steps,
    infer_model_lookup_answer_key,
    infer_product_routing_answer_key,
    next_product_routing_steps_from_observed_trace,
)
from css_data_synthesis_test.schemas import (
    DialogueTurn,
    Scenario,
    SERVICE_SPEAKER,
    USER_SPEAKER,
    display_speaker,
    effective_required_slots,
    normalize_speaker,
)
from css_data_synthesis_test.static_utterances import (
    appointment_utterance,
    ask_satisfaction_utterance,
    end_utterance,
    fee_collect_utterance,
)


MOBILE_PHONE_PATTERN = re.compile(r"^1[3-9]\d{9}$")
ADDRESS_COMMUNITY_LABEL_SUFFIXES = ("小区", "社区", "花园", "公寓", "苑", "府", "里", "村")
PromptVariant = str | tuple[str, float]
PromptConfig = list[PromptVariant]


@dataclass
class ServiceRuntimeState:
    expected_contactable_confirmation: bool = False
    awaiting_phone_keypad_input: bool = False
    expected_phone_number_confirmation: bool = False
    phone_input_attempts: int = 0
    pending_phone_number_confirmation: str = ""
    expected_address_confirmation: bool = False
    address_confirmation_triggered_by_observation: bool = False
    expected_product_arrival_confirmation: bool = False
    product_arrival_checked: bool = False
    pending_address_confirmation: str = ""
    address_confirmation_started_from_known_address: bool = False
    awaiting_full_address: bool = False
    address_input_attempts: int = 0
    partial_address_candidate: str = ""
    address_vague_retry_count: int = 0
    last_address_followup_prompt: str = ""
    expected_product_routing_response: bool = False
    product_routing_step_index: int = 0
    product_routing_completed: bool = False
    product_routing_observed_trace: list[str] = field(default_factory=list)
    awaiting_closing_ack: bool = False
    awaiting_satisfaction_rating: bool = False


@dataclass
class ServicePolicyResult:
    reply: str
    slot_updates: dict[str, str]
    is_ready_to_close: bool
    close_status: str = ""
    close_reason: str = ""


class ServiceDialoguePolicy:
    FAULT_ACKNOWLEDGEMENT_PREFIX = "非常抱歉，给您添麻烦了，我这就安排师傅上门维修"
    HUMAN_HANDOFF_REPLY = "请稍等，正在为您转接人工服务。"
    ADDRESS_IE_FUNCTION_CALL_DISPLAY = 'function_call: [{"name": "ie", "arguments": {"entity_type": "addressInfo"}}]'

    SURNAME_PROMPT = "请问您贵姓？"
    CONTACTABLE_PROMPT = "请问您当前这个来电号码能联系到您吗？"
    PHONE_KEYPAD_PROMPT = "请您在拨号盘上输入您的联系方式，并以#号键结束。"
    PHONE_KEYPAD_RETRY_PROMPT = "您输入的号码有误，请重新在拨号盘上输入您的联系方式，并以#号键结束。"
    PHONE_CONFIRMATION_TEMPLATE = "号码是{phone}，对吗？"
    FAULT_ISSUE_PROMPT = "请问{product}现在是出现了什么问题？"
    ADDRESS_PROMPT = "需要登记下您的地址，麻烦您完整的说下省、市、区、乡镇，精确到门牌号。"
    ADDRESS_PROVINCE_CITY_DISTRICT_STREET_FOLLOWUP_TEMPLATE = "好的，请问是{province}哪个城市的哪个区和街道呢？"
    ADDRESS_CITY_DISTRICT_FOLLOWUP_TEMPLATE = "好的，您是在{city}的哪个区县呢？具体小区门牌号也提供一下呢？"
    ADDRESS_PROVINCE_CITY_FOLLOWUP_PROMPT = "好的，请问您是在哪个省哪个市呢？"
    ADDRESS_FULL_REGION_FOLLOWUP_PROMPT = "好的，还请您说一下完整的省、市、区。"
    ADDRESS_CITY_DISTRICT_ONLY_FOLLOWUP_PROMPT = "好的，麻烦您再补充一下是在哪个市和哪个区县呢？"
    ADDRESS_CITY_DISTRICT_INFO_FOLLOWUP_PROMPT = "好的，麻烦您再补充一下城市和区县信息。"
    ADDRESS_CITY_DISTRICT_TOWN_TEMPLATE = "好的，您是在{city}的哪个区和哪个街道呢？"
    ADDRESS_FULL_REGION_COMPACT_FOLLOWUP_PROMPT = "请您说一下完整的省市区信息。"
    ADDRESS_REGION_STREET_FOLLOWUP_PROMPT = "好的，请您说一下省、市、区和街道。"
    ADDRESS_DISTRICT_STREET_FOLLOWUP_PROMPT = "好的，请您继续说一下区和街道。"
    ADDRESS_LOCALITY_FOLLOWUP_PROMPT = "请问具体是在哪个小区或村呢？尽量详细到门牌号。"
    ADDRESS_LOCALITY_WHICH_FOLLOWUP_PROMPT = "请问是在哪个小区或哪个村呢？尽量详细到门牌号。"
    ADDRESS_RURAL_DETAIL_FOLLOWUP_PROMPT = "好的，请您提供一下详细的地址，具体到门牌号。"
    ADDRESS_RECOLLECTION_PROMPT = "了解了，麻烦您重新提供一下地址，包括省、市、区、乡镇。"
    ADDRESS_CONFIRMATION_TEMPLATE = "跟您确认一下，地址是{address}，对吗？"
    KNOWN_ADDRESS_CONFIRMATION_TEMPLATE = "您的地址是{address}，对吗？"
    PRODUCT_ARRIVAL_PROMPT = "请问{product}已经送到了吗？"
    PRODUCT_MODEL_PROMPT = "请问产品型号方便提供一下吗？"
    # 每条话术支持配置为 [(文案, 权重), ...]，每次发送时使用 random.choices 按权重随机选择。
    SURNAME_PROMPT: PromptConfig = [("请问您贵姓？", 1.0)]
    CONTACTABLE_PROMPT: PromptConfig = [("请问您当前这个来电号码能联系到您吗？", 1.0)]
    PHONE_KEYPAD_PROMPT: PromptConfig = [("请您在拨号盘上输入您的联系方式，并以#号键结束。", 1.0)]
    PHONE_KEYPAD_RETRY_PROMPT: PromptConfig = [
        ("您输入的号码有误，请重新在拨号盘上输入您的联系方式，并以#号键结束。", 1.0)
    ]
    PHONE_CONFIRMATION_TEMPLATE: PromptConfig = [("号码是{phone}，对吗？", 1.0)]
    FAULT_ISSUE_PROMPT: PromptConfig = [("请问{product}现在是出现了什么问题？", 1.0)]
    ADDRESS_PROMPT: PromptConfig = [("需要登记下您的地址，麻烦您完整的说下省、市、区、乡镇，精确到门牌号。", 1.0)]
    ADDRESS_PROVINCE_CITY_DISTRICT_STREET_FOLLOWUP_TEMPLATE: PromptConfig = [
        ("好的，请问是{province}哪个城市的哪个区和街道呢？", 1.0)
    ]
    ADDRESS_CITY_DISTRICT_FOLLOWUP_TEMPLATE: PromptConfig = [
        ("好的，您是在{city}的哪个区县呢？具体小区门牌号也提供一下呢？", 1.0)
    ]
    ADDRESS_PROVINCE_CITY_FOLLOWUP_PROMPT: PromptConfig = [("好的，请问您是在哪个省哪个市呢？", 1.0)]
    ADDRESS_FULL_REGION_FOLLOWUP_PROMPT: PromptConfig = [("好的，还请您说一下完整的省、市、区。", 1.0)]
    ADDRESS_CITY_DISTRICT_ONLY_FOLLOWUP_PROMPT: PromptConfig = [("好的，麻烦您再补充一下是在哪个市和哪个区县呢？", 1.0)]
    ADDRESS_CITY_DISTRICT_INFO_FOLLOWUP_PROMPT: PromptConfig = [("好的，麻烦您再补充一下城市和区县信息。", 1.0)]
    ADDRESS_CITY_DISTRICT_TOWN_TEMPLATE: PromptConfig = [("好的，您是在{city}的哪个区和哪个街道呢？", 1.0)]
    ADDRESS_FULL_REGION_COMPACT_FOLLOWUP_PROMPT: PromptConfig = [("请您说一下完整的省市区信息。", 1.0)]
    ADDRESS_REGION_STREET_FOLLOWUP_PROMPT: PromptConfig = [("好的，请您说一下省、市、区和街道。", 1.0)]
    ADDRESS_DISTRICT_STREET_FOLLOWUP_PROMPT: PromptConfig = [("好的，请您继续说一下区和街道。", 1.0)]
    ADDRESS_LOCALITY_FOLLOWUP_PROMPT: PromptConfig = [("请问具体是在哪个小区或村呢？尽量详细到门牌号。", 1.0)]
    ADDRESS_LOCALITY_WHICH_FOLLOWUP_PROMPT: PromptConfig = [("请问是在哪个小区或哪个村呢？尽量详细到门牌号。", 1.0)]
    ADDRESS_RURAL_DETAIL_FOLLOWUP_PROMPT: PromptConfig = [("好的，请您提供一下详细的地址，具体到门牌号。", 1.0)]
    ADDRESS_RECOLLECTION_PROMPT: PromptConfig = [("了解了，麻烦您重新提供一下地址，包括省、市、区、乡镇。", 1.0)]
    ADDRESS_CONFIRMATION_TEMPLATE: PromptConfig = [("跟您确认一下，地址是{address}，对吗？", 1.0)]
    KNOWN_ADDRESS_CONFIRMATION_TEMPLATE: PromptConfig = [("您的地址是{address}，对吗？", 1.0)]
    PRODUCT_ARRIVAL_PROMPT: PromptConfig = [("请问{product}已经送到了吗？", 1.0)]
    PRODUCT_MODEL_PROMPT: PromptConfig = [("请问产品型号方便提供一下吗？", 1.0)]
    def __init__(
        self,
        ok_prefix_probability: float = 1.0,
        rng: random.Random | None = None,
        address_inference_callback: Callable[..., dict[str, Any] | None] | None = None,
        address_collection_acceptance_inference_callback: Callable[..., dict[str, Any] | None] | None = None,
        surname_inference_callback: Callable[..., dict[str, Any] | None] | None = None,
        contact_intent_inference_callback: Callable[..., dict[str, Any] | None] | None = None,
        confirmation_intent_inference_callback: Callable[..., dict[str, Any] | None] | None = None,
        opening_intent_inference_callback: Callable[..., dict[str, Any] | None] | None = None,
        issue_description_extraction_callback: Callable[..., dict[str, Any] | None] | None = None,
        product_routing_intent_inference_callback: Callable[..., dict[str, Any] | None] | None = None,
        product_routing_enabled: bool = True,
    ):
        self.ok_prefix_probability = max(0.0, min(1.0, ok_prefix_probability))
        self.rng = rng or random.Random()
        self.address_inference_callback = address_inference_callback
        self.address_collection_acceptance_inference_callback = address_collection_acceptance_inference_callback
        self.surname_inference_callback = surname_inference_callback
        self.contact_intent_inference_callback = contact_intent_inference_callback
        self.confirmation_intent_inference_callback = confirmation_intent_inference_callback
        self.opening_intent_inference_callback = opening_intent_inference_callback
        self.issue_description_extraction_callback = issue_description_extraction_callback
        self.product_routing_intent_inference_callback = product_routing_intent_inference_callback
        self.product_routing_enabled = product_routing_enabled
        self.last_used_model_intent_inference = False

    def respond(
        self,
        *,
        scenario: Scenario,
        transcript: list[DialogueTurn],
        collected_slots: dict[str, str],
        runtime_state: ServiceRuntimeState,
    ) -> ServicePolicyResult:
        self.last_used_model_intent_inference = False
        has_service_turn = any(normalize_speaker(turn.speaker) == SERVICE_SPEAKER for turn in transcript)
        if not has_service_turn and not transcript:
            return ServicePolicyResult(
                reply=self._build_opening_prompt(scenario),
                slot_updates={},
                is_ready_to_close=False,
            )

        if not has_service_turn:
            initial_user_turn = self._last_turn_by_speaker(transcript, USER_SPEAKER)
            if initial_user_turn is None:
                return ServicePolicyResult(reply="", slot_updates={}, is_ready_to_close=False)
            return self._handle_initial_user_utterance(
                scenario=scenario,
                user_text=initial_user_turn.text,
                collected_slots=collected_slots,
                runtime_state=runtime_state,
            )

        last_user_turn = self._last_turn_by_speaker(transcript, USER_SPEAKER)
        if last_user_turn is None:
            return ServicePolicyResult(reply="", slot_updates={}, is_ready_to_close=False)

        previous_service_text = self._previous_service_text(transcript)
        previous_service_signature = self._normalize_prompt_text(previous_service_text)
        slot_updates = self._extract_standard_slots(
            scenario=scenario,
            previous_service_signature=previous_service_signature,
            user_text=last_user_turn.text,
            user_round_index=last_user_turn.round_index,
            collected_slots=collected_slots,
        )
        required_slots = effective_required_slots(scenario)
        merged_slots = dict(collected_slots)
        merged_slots.update(slot_updates)
        if self._should_transfer_to_human(last_user_turn.text):
            return self._handoff_to_human(
                scenario=scenario,
                runtime_state=runtime_state,
                slot_updates=slot_updates,
                reason="user_requested_human",
            )

        if runtime_state.expected_contactable_confirmation:
            return self._handle_contactable_confirmation(
                scenario=scenario,
                user_text=last_user_turn.text,
                user_round_index=last_user_turn.round_index,
                collected_slots=merged_slots,
                runtime_state=runtime_state,
            )

        if runtime_state.awaiting_phone_keypad_input:
            return self._handle_phone_keypad_input(
                scenario=scenario,
                user_text=last_user_turn.text,
                collected_slots=merged_slots,
                runtime_state=runtime_state,
            )

        if runtime_state.expected_phone_number_confirmation:
            return self._handle_phone_number_confirmation(
                scenario=scenario,
                user_text=last_user_turn.text,
                user_round_index=last_user_turn.round_index,
                collected_slots=merged_slots,
                runtime_state=runtime_state,
            )

        if runtime_state.expected_address_confirmation:
            return self._handle_address_confirmation(
                scenario=scenario,
                user_text=last_user_turn.text,
                user_round_index=last_user_turn.round_index,
                transcript=transcript,
                collected_slots=merged_slots,
                runtime_state=runtime_state,
                slot_updates=slot_updates,
            )

        if runtime_state.expected_product_routing_response:
            return self._handle_product_routing_response(
                scenario=scenario,
                user_text=last_user_turn.text,
                user_round_index=last_user_turn.round_index,
                collected_slots=merged_slots,
                slot_updates=slot_updates,
                runtime_state=runtime_state,
            )

        if runtime_state.expected_product_arrival_confirmation:
            return self._handle_product_arrival_confirmation(
                scenario=scenario,
                user_text=last_user_turn.text,
                user_round_index=last_user_turn.round_index,
                collected_slots=merged_slots,
                slot_updates=slot_updates,
                runtime_state=runtime_state,
            )

        if runtime_state.awaiting_full_address:
            return self._handle_full_address_input(
                scenario=scenario,
                user_text=last_user_turn.text,
                transcript=transcript,
                collected_slots=merged_slots,
                runtime_state=runtime_state,
                slot_updates=slot_updates,
            )

        if runtime_state.awaiting_closing_ack:
            return self._handle_closing_acknowledgement(
                scenario=scenario,
                slot_updates=slot_updates,
                runtime_state=runtime_state,
            )

        if runtime_state.awaiting_satisfaction_rating:
            return self._handle_satisfaction_rating(
                scenario=scenario,
                user_text=last_user_turn.text,
                slot_updates=slot_updates,
                runtime_state=runtime_state,
            )

        implicit_routing_result = self._try_advance_product_routing_from_context(
            scenario=scenario,
            user_text=last_user_turn.text,
            user_round_index=last_user_turn.round_index,
            previous_service_signature=previous_service_signature,
            collected_slots=merged_slots,
            slot_updates=slot_updates,
            runtime_state=runtime_state,
        )
        if implicit_routing_result is not None:
            return implicit_routing_result

        next_slot = self._next_slot_to_request(merged_slots, required_slots)
        return self._transition_to_next_slot(
            scenario=scenario,
            collected_slots=collected_slots,
            slot_updates=slot_updates,
            runtime_state=runtime_state,
            next_slot=next_slot,
        )

    def build_initial_user_utterance(self, scenario: Scenario) -> str:
        action = "维修" if scenario.request.request_type == "fault" else "安装"
        return f"{scenario.product.brand}{self._product_name(scenario)}需要{action}"

    def _handle_initial_user_utterance(
        self,
        *,
        scenario: Scenario,
        user_text: str,
        collected_slots: dict[str, str],
        runtime_state: ServiceRuntimeState,
    ) -> ServicePolicyResult:
        slot_updates: dict[str, str] = {}
        if "request_type" in collected_slots and not collected_slots["request_type"].strip():
            slot_updates["request_type"] = scenario.request.request_type
        if self._should_transfer_to_human(user_text):
            return self._handoff_to_human(
                scenario=scenario,
                runtime_state=runtime_state,
                slot_updates=slot_updates,
                reason="user_requested_human",
            )

        return ServicePolicyResult(
            reply=self._build_opening_prompt(scenario),
            slot_updates=slot_updates,
            is_ready_to_close=False,
        )

    def _handle_contactable_confirmation(
        self,
        *,
        scenario: Scenario,
        user_text: str,
        user_round_index: int,
        collected_slots: dict[str, str],
        runtime_state: ServiceRuntimeState,
    ) -> ServicePolicyResult:
        intent = self._classify_contactable_intent(user_text, user_round_index=user_round_index)
        runtime_state.expected_contactable_confirmation = False
        has_known_phone = self._has_known_value(scenario.customer.phone)
        current_call_phone = self._current_call_phone(scenario)
        direct_phone = self._extract_mobile_phone(user_text)
        contact_owner = self._extract_contact_phone_owner_from_text(user_text) or self._contact_phone_owner(scenario)

        if (
            self._interactive_test_freeform_enabled(scenario)
            and not has_known_phone
            and direct_phone
        ):
            runtime_state.expected_phone_number_confirmation = True
            runtime_state.pending_phone_number_confirmation = direct_phone
            runtime_state.phone_input_attempts = 0
            slot_updates = {
                "phone_collection_attempts": "0",
            }
            if intent == "no":
                slot_updates["phone_contactable"] = "no"
                if contact_owner:
                    slot_updates["phone_contact_owner"] = contact_owner
            else:
                slot_updates["phone_contactable"] = "yes"
                slot_updates["phone_contact_owner"] = "本人当前来电"
            return ServicePolicyResult(
                reply=self._phone_confirmation_prompt(direct_phone),
                slot_updates=slot_updates,
                is_ready_to_close=False,
            )

        if intent == "yes":
            if not has_known_phone and current_call_phone:
                slot_updates = {
                    "phone": current_call_phone,
                    "phone_contactable": "yes",
                    "phone_contact_owner": "本人当前来电",
                    "phone_collection_attempts": "0",
                }
                merged_slots = dict(collected_slots)
                merged_slots.update(slot_updates)
                next_slot = self._next_slot_to_request(merged_slots, effective_required_slots(scenario))
                return self._transition_to_next_slot(
                    scenario=scenario,
                    collected_slots=collected_slots,
                    slot_updates=slot_updates,
                    runtime_state=runtime_state,
                    next_slot=next_slot,
                )
            if not has_known_phone and self._interactive_test_freeform_enabled(scenario):
                runtime_state.awaiting_phone_keypad_input = True
                runtime_state.phone_input_attempts = 0
                return ServicePolicyResult(
                    reply=self._phone_keypad_prompt(),
                    slot_updates={
                        "phone_contactable": "yes",
                        "phone_contact_owner": "本人当前来电",
                        "phone_collection_attempts": "0",
                    },
                    is_ready_to_close=False,
                )

            slot_updates = {
                "phone": scenario.customer.phone,
                "phone_contactable": "yes",
                "phone_contact_owner": "本人当前来电",
                "phone_collection_attempts": "0",
            }
            merged_slots = dict(collected_slots)
            merged_slots.update(slot_updates)
            next_slot = self._next_slot_to_request(merged_slots, effective_required_slots(scenario))
            return self._transition_to_next_slot(
                scenario=scenario,
                collected_slots=collected_slots,
                slot_updates=slot_updates,
                runtime_state=runtime_state,
                next_slot=next_slot,
            )

        if intent == "no":
            runtime_state.awaiting_phone_keypad_input = True
            runtime_state.phone_input_attempts = 0
            slot_updates = {"phone_contactable": "no"}
            if contact_owner:
                slot_updates["phone_contact_owner"] = contact_owner
            return ServicePolicyResult(
                reply=self._phone_keypad_prompt(),
                slot_updates=slot_updates,
                is_ready_to_close=False,
            )

        runtime_state.expected_contactable_confirmation = True
        return ServicePolicyResult(
            reply=self._contactable_prompt(),
            slot_updates={},
            is_ready_to_close=False,
        )

    def _handle_phone_number_confirmation(
        self,
        *,
        scenario: Scenario,
        user_text: str,
        user_round_index: int,
        collected_slots: dict[str, str],
        runtime_state: ServiceRuntimeState,
    ) -> ServicePolicyResult:
        intent = self._classify_confirmation_intent(
            user_text,
            prompt_kind="phone_number_confirmation",
            user_round_index=user_round_index,
        )
        pending_phone = runtime_state.pending_phone_number_confirmation

        if intent == "yes" and pending_phone:
            runtime_state.expected_phone_number_confirmation = False
            runtime_state.pending_phone_number_confirmation = ""
            slot_updates = {
                "phone": pending_phone,
                "phone_collection_attempts": str(runtime_state.phone_input_attempts),
            }
            owner = self._contact_phone_owner(scenario)
            if owner:
                slot_updates.setdefault("phone_contact_owner", owner)
            merged_slots = dict(collected_slots)
            merged_slots.update(slot_updates)
            next_slot = self._next_slot_to_request(merged_slots, effective_required_slots(scenario))
            return self._transition_to_next_slot(
                scenario=scenario,
                collected_slots=collected_slots,
                slot_updates=slot_updates,
                runtime_state=runtime_state,
                next_slot=next_slot,
            )

        if intent == "no":
            runtime_state.expected_phone_number_confirmation = False
            runtime_state.pending_phone_number_confirmation = ""
            runtime_state.awaiting_phone_keypad_input = True
            return ServicePolicyResult(
                reply=self._phone_keypad_prompt(),
                slot_updates={
                    "phone_collection_attempts": str(runtime_state.phone_input_attempts),
                },
                is_ready_to_close=False,
            )

        runtime_state.expected_phone_number_confirmation = True
        return ServicePolicyResult(
            reply=self._phone_confirmation_prompt(pending_phone),
            slot_updates={},
            is_ready_to_close=False,
        )

    def _handle_address_confirmation(
        self,
        *,
        scenario: Scenario,
        user_text: str,
        user_round_index: int,
        transcript: list[DialogueTurn],
        collected_slots: dict[str, str],
        runtime_state: ServiceRuntimeState,
        slot_updates: dict[str, str],
    ) -> ServicePolicyResult:
        intent = self._classify_confirmation_intent(
            user_text,
            prompt_kind="address_confirmation",
            user_round_index=user_round_index,
        )
        confirmation_address = (
            runtime_state.pending_address_confirmation
            or self._service_known_address_value(scenario)
            or scenario.customer.address
        )
        started_from_known_address = runtime_state.address_confirmation_started_from_known_address
        triggered_by_observation = runtime_state.address_confirmation_triggered_by_observation
        previous_service_text = self._previous_service_text(transcript)
        if (
            not started_from_known_address
            and not triggered_by_observation
            and self.is_address_confirmation_prompt(previous_service_text)
            and self._normalize_prompt_text(previous_service_text).startswith("您的地址是")
        ):
            started_from_known_address = True
        runtime_state.expected_address_confirmation = False
        runtime_state.address_confirmation_triggered_by_observation = False
        runtime_state.address_confirmation_started_from_known_address = False

        if intent == "yes":
            slot_updates = dict(slot_updates)
            slot_updates["address"] = confirmation_address or scenario.customer.address
            runtime_state.pending_address_confirmation = ""
            merged_slots = dict(collected_slots)
            merged_slots.update(slot_updates)
            next_slot = self._next_slot_to_request(merged_slots, effective_required_slots(scenario))
            return self._transition_to_next_slot(
                scenario=scenario,
                collected_slots=collected_slots,
                slot_updates=slot_updates,
                runtime_state=runtime_state,
                next_slot=next_slot,
            )

        if intent == "no":
            denial_address, use_confirmation_as_merge_source = self._resolve_confirmation_denial_address_candidate(
                transcript=transcript,
                user_text=user_text,
                confirmation_address=confirmation_address,
            )
            if denial_address:
                runtime_state.awaiting_full_address = True
                runtime_state.address_input_attempts = 1
                runtime_state.pending_address_confirmation = ""
                merge_source = (
                    confirmation_address
                    if use_confirmation_as_merge_source
                    else runtime_state.partial_address_candidate
                )
                merged_candidate = self._merge_address_candidate(merge_source, denial_address)
                if not merged_candidate:
                    merged_candidate = denial_address
                runtime_state.partial_address_candidate = merged_candidate
                runtime_state.address_vague_retry_count = 0
                normalized_candidate = self._normalize_address_text(merged_candidate)
                if self._can_start_address_confirmation(
                    scenario=scenario,
                    candidate=merged_candidate,
                ):
                    return self._start_address_confirmation(
                        scenario=scenario,
                        runtime_state=runtime_state,
                        address=merged_candidate,
                        slot_updates=slot_updates,
                        use_known_address_prompt=False,
                    )
                return ServicePolicyResult(
                    reply=self._remember_address_followup_prompt(
                        runtime_state,
                        self._address_followup_prompt_for_scenario(
                            scenario=scenario,
                            candidate=normalized_candidate,
                        ),
                    ),
                    slot_updates=slot_updates,
                    is_ready_to_close=False,
                )
            runtime_state.awaiting_full_address = True
            runtime_state.address_input_attempts = 0
            runtime_state.pending_address_confirmation = ""
            runtime_state.partial_address_candidate = ""
            runtime_state.address_vague_retry_count = 0
            return ServicePolicyResult(
                reply=self._remember_address_followup_prompt(
                    runtime_state,
                    self._address_recollection_prompt()
                    if started_from_known_address or triggered_by_observation
                    else self._address_prompt(),
                ),
                slot_updates=slot_updates,
                is_ready_to_close=False,
            )

        return self._start_address_confirmation(
            scenario=scenario,
            runtime_state=runtime_state,
            address=confirmation_address,
            slot_updates=slot_updates,
            use_known_address_prompt=False,
        )

    def _handle_phone_keypad_input(
        self,
        *,
        scenario: Scenario,
        user_text: str,
        collected_slots: dict[str, str],
        runtime_state: ServiceRuntimeState,
    ) -> ServicePolicyResult:
        runtime_state.phone_input_attempts += 1
        digits = re.sub(r"\D", "", user_text or "")
        slot_updates = {
            "phone_collection_attempts": str(runtime_state.phone_input_attempts),
        }

        if MOBILE_PHONE_PATTERN.match(digits):
            runtime_state.awaiting_phone_keypad_input = False
            runtime_state.expected_phone_number_confirmation = True
            runtime_state.pending_phone_number_confirmation = digits
            return ServicePolicyResult(
                reply=self._phone_confirmation_prompt(digits),
                slot_updates=slot_updates,
                is_ready_to_close=False,
            )

        if runtime_state.phone_input_attempts < 3:
            return ServicePolicyResult(
                reply=self._phone_keypad_retry_prompt(),
                slot_updates=slot_updates,
                is_ready_to_close=False,
            )
        return ServicePolicyResult(
            reply=self._phone_keypad_retry_prompt(),
            slot_updates=slot_updates,
            is_ready_to_close=False,
        )

    def _handle_full_address_input(
        self,
        *,
        scenario: Scenario,
        user_text: str,
        transcript: list[DialogueTurn],
        collected_slots: dict[str, str],
        runtime_state: ServiceRuntimeState,
        slot_updates: dict[str, str],
    ) -> ServicePolicyResult:
        dialogue_history = self._dialogue_history_text(transcript)
        rule_prepared_address = self._prepare_address_for_confirmation(user_text)
        model_prepared_address = ""
        previous_candidate = runtime_state.partial_address_candidate
        if self.address_inference_callback is not None:
            model_prepared_address = self._infer_address_candidate_with_callback(
                user_text=user_text,
                confirmation_address=runtime_state.pending_address_confirmation,
                partial_address_candidate=runtime_state.partial_address_candidate,
                last_address_followup_prompt=runtime_state.last_address_followup_prompt,
                dialogue_history=dialogue_history,
            )
            if model_prepared_address:
                prepared_address = model_prepared_address
            elif self._can_use_rule_address_candidate_for_collection(
                candidate=rule_prepared_address,
                actual_address=scenario.customer.address,
            ):
                prepared_address = rule_prepared_address
            else:
                prepared_address = rule_prepared_address
        else:
            prepared_address = rule_prepared_address
        inferred_candidate = ""
        if self._address_user_accepts_current_candidate_or_signals_stop(
            user_text=user_text,
            partial_address_candidate=runtime_state.partial_address_candidate,
            last_address_followup_prompt=runtime_state.last_address_followup_prompt,
            dialogue_history=dialogue_history,
        ):
            inferred_candidate = model_prepared_address
            accepted_candidate = previous_candidate
            if inferred_candidate:
                accepted_candidate = self._merge_address_candidate(
                    accepted_candidate,
                    inferred_candidate,
                )
            if accepted_candidate:
                normalized_candidate = self._normalize_address_text(accepted_candidate)
                runtime_state.partial_address_candidate = accepted_candidate
                return ServicePolicyResult(
                    reply=self._remember_address_followup_prompt(
                        runtime_state,
                        self._address_followup_prompt_for_scenario(
                            scenario=scenario,
                            candidate=normalized_candidate,
                        ),
                    ),
                    slot_updates=slot_updates,
                    is_ready_to_close=False,
                )
        elif self._address_user_signals_reask_frustration(user_text):
            frustration_candidate = previous_candidate
            inferred_candidate = model_prepared_address
            if inferred_candidate:
                frustration_candidate = self._merge_address_candidate(
                    frustration_candidate,
                    inferred_candidate,
                )
            if frustration_candidate:
                missing_precision = self._missing_required_address_precision(
                    frustration_candidate,
                    scenario.customer.address,
                )
            else:
                missing_precision = []
            if frustration_candidate and missing_precision:
                runtime_state.partial_address_candidate = frustration_candidate
                return ServicePolicyResult(
                    reply=self._remember_address_followup_prompt(
                        runtime_state,
                        self._address_followup_prompt_for_scenario(
                            scenario=scenario,
                            candidate=self._normalize_address_text(frustration_candidate),
                        ),
                    ),
                    slot_updates=slot_updates,
                    is_ready_to_close=False,
                )
        if self._contains_rural_no_building_statement(user_text) and self._is_rural_address_candidate(
            f"{previous_candidate}{user_text}"
        ):
            runtime_state.address_input_attempts += 1
            runtime_state.address_vague_retry_count = 0
            return ServicePolicyResult(
                reply=self._remember_address_followup_prompt(
                    runtime_state,
                    self._address_rural_detail_followup_prompt(),
                ),
                slot_updates=slot_updates,
                is_ready_to_close=False,
            )
        combined_address = self._merge_address_candidate(
            previous_candidate,
            prepared_address,
        )
        progress_made = self._address_input_makes_progress(
            existing=previous_candidate,
            incoming=prepared_address,
            merged=combined_address,
        )
        if self.address_inference_callback is None:
            current_is_complete = self._is_complete_address(
                self._normalize_address_text(combined_address),
                scenario.customer.address,
            )
            needs_model_backfill = self._should_backfill_address_with_model(
                current=combined_address,
                actual_address=scenario.customer.address,
            )
            if not progress_made or not current_is_complete or needs_model_backfill:
                inferred_address = model_prepared_address or self._infer_address_candidate_with_callback(
                    user_text=user_text,
                    confirmation_address=runtime_state.pending_address_confirmation,
                    partial_address_candidate=previous_candidate,
                    last_address_followup_prompt=runtime_state.last_address_followup_prompt,
                    dialogue_history=dialogue_history,
                )
                if inferred_address:
                    inferred_combined = self._merge_address_candidate(
                        previous_candidate,
                        inferred_address,
                    )
                    if (
                        self._is_complete_address(
                            self._normalize_address_text(inferred_combined),
                            scenario.customer.address,
                        )
                        or self._should_prefer_address_candidate(
                            current=combined_address,
                            candidate=inferred_combined,
                        )
                    ):
                        prepared_address = inferred_address
                        combined_address = inferred_combined
                        progress_made = self._address_input_makes_progress(
                            existing=previous_candidate,
                            incoming=prepared_address,
                            merged=combined_address,
                        )
        runtime_state.address_input_attempts += 1
        if not progress_made:
            return ServicePolicyResult(
                reply=self._repeat_address_followup_prompt(runtime_state),
                slot_updates=slot_updates,
                is_ready_to_close=False,
            )

        runtime_state.address_vague_retry_count = 0
        combined_address = self._merge_address_candidate(
            previous_candidate,
            prepared_address,
        )
        address_candidate = self._normalize_address_text(combined_address)
        runtime_state.partial_address_candidate = combined_address

        return ServicePolicyResult(
            reply=self._remember_address_followup_prompt(
                runtime_state,
                self._address_followup_prompt_for_scenario(
                    scenario=scenario,
                    candidate=address_candidate,
                ),
            ),
            slot_updates=slot_updates,
            is_ready_to_close=False,
        )

    def _handle_product_arrival_confirmation(
        self,
        *,
        scenario: Scenario,
        user_text: str,
        user_round_index: int,
        collected_slots: dict[str, str],
        slot_updates: dict[str, str],
        runtime_state: ServiceRuntimeState,
    ) -> ServicePolicyResult:
        intent = self._classify_confirmation_intent(
            user_text,
            prompt_kind="product_arrival_confirmation",
            user_round_index=user_round_index,
        )

        if intent not in {"yes", "no"}:
            runtime_state.expected_product_arrival_confirmation = True
            return ServicePolicyResult(
                reply=self._product_arrival_prompt(scenario),
                slot_updates=slot_updates,
                is_ready_to_close=False,
            )

        runtime_state.expected_product_arrival_confirmation = False
        runtime_state.product_arrival_checked = True
        slot_updates = dict(slot_updates)
        slot_updates["product_arrived"] = "yes" if intent == "yes" else "no"
        merged_slots = dict(collected_slots)
        merged_slots.update(slot_updates)
        next_slot = self._next_slot_to_request(merged_slots, effective_required_slots(scenario))
        return self._transition_to_next_slot(
            scenario=scenario,
            collected_slots=collected_slots,
            slot_updates=slot_updates,
            runtime_state=runtime_state,
            next_slot=next_slot,
        )

    def _handle_product_routing_response(
        self,
        *,
        scenario: Scenario,
        user_text: str,
        user_round_index: int,
        collected_slots: dict[str, str],
        slot_updates: dict[str, str],
        runtime_state: ServiceRuntimeState,
    ) -> ServicePolicyResult:
        runtime_state.expected_product_routing_response = False
        current_steps = self._product_routing_steps(scenario)
        current_step: dict[str, str] | None = None
        if runtime_state.product_routing_step_index < len(current_steps):
            current_step = current_steps[runtime_state.product_routing_step_index]

        observed_answer_key = ""
        if current_step:
            prompt_key = str(current_step.get("prompt_key", "")).strip()
            observed_answer_key = self._classify_product_routing_answer_key(
                prompt_key=prompt_key,
                user_text=user_text,
                user_round_index=user_round_index,
            )
            if not observed_answer_key:
                observed_answer_key = default_unknown_product_routing_answer_key(prompt_key)
            if not observed_answer_key:
                runtime_state.expected_product_routing_response = True
                return ServicePolicyResult(
                    reply=str(current_step.get("prompt", "")).strip(),
                    slot_updates=slot_updates,
                    is_ready_to_close=False,
                )

        if observed_answer_key:
            post_answer_trace: list[str] = []
            if current_step:
                expected_answer_key = str(current_step.get("answer_key", "")).strip()
                if not expected_answer_key or expected_answer_key == observed_answer_key:
                    raw_post_answer_trace = current_step.get("post_answer_trace", [])
                    if isinstance(raw_post_answer_trace, list):
                        post_answer_trace = [
                            str(item).strip() for item in raw_post_answer_trace if str(item).strip()
                        ]
            return self._advance_product_routing_with_answer(
                scenario=scenario,
                collected_slots=collected_slots,
                slot_updates=slot_updates,
                runtime_state=runtime_state,
                observed_answer_key=observed_answer_key,
                post_answer_trace=post_answer_trace,
            )

        runtime_state.product_routing_step_index += 1
        if self._has_pending_product_routing_step(scenario, runtime_state):
            return self._start_product_routing_step(
                scenario=scenario,
                runtime_state=runtime_state,
                slot_updates=slot_updates,
            )

        runtime_state.product_routing_completed = True
        slot_updates = self._with_product_routing_result_slot(
            scenario=scenario,
            slot_updates=slot_updates,
        )
        merged_slots = dict(collected_slots)
        merged_slots.update(slot_updates)
        next_slot = self._next_slot_to_request(merged_slots, effective_required_slots(scenario))
        return self._transition_to_next_slot(
            scenario=scenario,
            collected_slots=collected_slots,
            slot_updates=slot_updates,
            runtime_state=runtime_state,
            next_slot=next_slot,
        )

    def _handle_closing_acknowledgement(
        self,
        *,
        scenario: Scenario,
        slot_updates: dict[str, str],
        runtime_state: ServiceRuntimeState,
    ) -> ServicePolicyResult:
        runtime_state.awaiting_closing_ack = False
        runtime_state.awaiting_satisfaction_rating = True
        return ServicePolicyResult(
            reply=self._fee_and_satisfaction_prompt(scenario),
            slot_updates=slot_updates,
            is_ready_to_close=False,
        )

    def _with_product_routing_result_slot(
        self,
        *,
        scenario: Scenario,
        slot_updates: dict[str, str],
        result: str = "",
    ) -> dict[str, str]:
        updated_slot_updates = dict(slot_updates)
        resolved_result = str(result or scenario.hidden_context.get("product_routing_result", "")).strip()
        if resolved_result:
            updated_slot_updates["product_routing_result"] = resolved_result
        return updated_slot_updates

    def _handle_satisfaction_rating(
        self,
        *,
        scenario: Scenario,
        user_text: str,
        slot_updates: dict[str, str],
        runtime_state: ServiceRuntimeState,
    ) -> ServicePolicyResult:
        score = self._extract_satisfaction_score(user_text)
        if not score:
            runtime_state.awaiting_satisfaction_rating = True
            return ServicePolicyResult(
                reply=self._satisfaction_prompt(),
                slot_updates=slot_updates,
                is_ready_to_close=False,
            )

        runtime_state.awaiting_satisfaction_rating = False
        return ServicePolicyResult(
            reply=self._end_prompt_for_scenario(scenario),
            slot_updates=slot_updates,
            is_ready_to_close=True,
        )

    def _extract_standard_slots(
        self,
        *,
        scenario: Scenario,
        previous_service_signature: str,
        user_text: str,
        user_round_index: int,
        collected_slots: dict[str, str],
    ) -> dict[str, str]:
        slot_updates: dict[str, str] = {}

        if (
            "issue_description" in collected_slots
            and not collected_slots["issue_description"].strip()
            and user_text.strip()
        ):
            if previous_service_signature == self._normalize_prompt_text(self._build_opening_prompt(scenario)):
                force_model = (
                    scenario.request.request_type == "fault"
                    and self.opening_intent_inference_callback is not None
                )
                opening_intent = self._classify_opening_intent(
                    user_text,
                    user_round_index=user_round_index,
                    force_model=force_model,
                    request_type=scenario.request.request_type,
                )
                if opening_intent == "issue_detail":
                    issue_description = self._resolve_issue_description(
                        user_text,
                        user_round_index=user_round_index,
                        request_type=scenario.request.request_type,
                        use_model=(scenario.request.request_type == "fault"),
                        strict_model=(
                            force_model
                            and self.issue_description_extraction_callback is not None
                        ),
                    )
                    if issue_description:
                        slot_updates["issue_description"] = issue_description
                elif (
                    scenario.request.request_type == "installation"
                    and opening_intent == "yes"
                ):
                    slot_updates["issue_description"] = user_text.strip()
            elif self._signature_matches_prompt(
                previous_service_signature,
                self._format_prompt_config(self.FAULT_ISSUE_PROMPT, product=self._product_name(scenario)),
            ):
                issue_description = self._resolve_issue_description(
                    user_text,
                    user_round_index=user_round_index,
                    request_type=scenario.request.request_type,
                    use_model=(scenario.request.request_type == "fault"),
                    strict_model=(scenario.request.request_type == "fault"),
                )
                if issue_description:
                    slot_updates["issue_description"] = issue_description

        if (
            "request_type" in collected_slots
            and not collected_slots["request_type"].strip()
            and previous_service_signature == self._normalize_prompt_text(self._build_opening_prompt(scenario))
        ):
            slot_updates["request_type"] = scenario.request.request_type

        if (
            "surname" in collected_slots
            and not collected_slots["surname"].strip()
            and self._signature_matches_prompt(previous_service_signature, self.SURNAME_PROMPT)
        ):
            if self.surname_inference_callback is not None:
                freeform_surname = self._extract_surname_with_model(
                    user_text,
                    user_round_index=user_round_index,
                )
            elif self._has_known_value(scenario.customer.surname) and scenario.customer.surname in user_text:
                freeform_surname = scenario.customer.surname
            else:
                freeform_surname = self._extract_freeform_surname(user_text)
            if freeform_surname:
                slot_updates["surname"] = freeform_surname

        if (
            "product_model" in collected_slots
            and not collected_slots["product_model"].strip()
            and self._signature_matches_prompt(previous_service_signature, self.PRODUCT_MODEL_PROMPT)
            and scenario.product.model in user_text
        ):
            slot_updates["product_model"] = scenario.product.model

        return slot_updates

    def _next_slot_to_request(
        self,
        collected_slots: dict[str, str],
        required_slots: list[str],
        skip_slots: set[str] | None = None,
    ) -> str | None:
        skip_slots = skip_slots or set()
        priority = [
            "issue_description",
            "surname",
            "phone",
            "address",
            "product_model",
            "request_type",
        ]
        for slot in priority:
            if (
                slot in required_slots
                and slot not in skip_slots
                and not collected_slots.get(slot, "").strip()
            ):
                return slot
        for slot in required_slots:
            if slot not in skip_slots and not collected_slots.get(slot, "").strip():
                return slot
        return None

    def _prompt_for_slot(self, slot: str, scenario: Scenario) -> str:
        prompts = {
            "issue_description": self._fault_issue_prompt(scenario)
            if scenario.request.request_type == "fault"
            else self._surname_prompt(),
            "surname": self._surname_prompt(),
            "phone": self._contactable_prompt(),
            "address": self._address_prompt(),
            "product_model": self._product_model_prompt(),
            "request_type": self._surname_prompt(),
        }
        return prompts.get(slot, self._surname_prompt())

    def _reply_for_next_slot(
        self,
        *,
        scenario: Scenario,
        collected_slots: dict[str, str],
        slot_updates: dict[str, str],
        next_slot: str,
    ) -> str:
        reply = self._prompt_for_slot(next_slot, scenario)
        if self._should_prepend_fault_acknowledgement(
            scenario=scenario,
            collected_slots=collected_slots,
            slot_updates=slot_updates,
        ):
            return self._prepend_fault_acknowledgement(reply)
        return reply

    def _should_prepend_fault_acknowledgement(
        self,
        *,
        scenario: Scenario,
        collected_slots: dict[str, str],
        slot_updates: dict[str, str],
    ) -> bool:
        return (
            scenario.request.request_type == "fault"
            and not collected_slots.get("issue_description", "").strip()
            and bool(slot_updates.get("issue_description", "").strip())
        )

    def _prepend_fault_acknowledgement(self, reply: str) -> str:
        normalized_reply = re.sub(r"^好的[，,\s]*", "", (reply or "").strip())
        if not normalized_reply:
            return self.FAULT_ACKNOWLEDGEMENT_PREFIX
        return f"{self.FAULT_ACKNOWLEDGEMENT_PREFIX}，{normalized_reply}"

    def _start_closing_sequence(self, scenario: Scenario, runtime_state: ServiceRuntimeState) -> str:
        runtime_state.awaiting_closing_ack = True
        runtime_state.awaiting_satisfaction_rating = False
        return self._appointment_prompt_for_scenario(scenario)

    def _effective_brand_for_service_utterance(self, scenario: Scenario) -> str:
        base_brand = str(scenario.product.brand or "").strip()
        hidden_context = scenario.hidden_context if isinstance(scenario.hidden_context, dict) else {}
        trace = hidden_context.get("product_routing_trace")
        if not isinstance(trace, list):
            trace = hidden_context.get("product_routing_plan", {}).get("trace", [])
        normalized_trace = {str(item or "").strip() for item in trace if str(item or "").strip()}
        if "brand_series.colmo" in normalized_trace:
            return "COLMO"
        return base_brand

    def _appointment_prompt_for_scenario(self, scenario: Scenario) -> str:
        return appointment_utterance(
            brand=self._effective_brand_for_service_utterance(scenario),
            category=self._product_name(scenario),
            request_type=scenario.request.request_type,
            call_start_time=scenario.call_start_time,
        )

    def _fee_and_satisfaction_prompt(self, scenario: Scenario) -> str:
        return f"{self._fee_collect_prompt_for_scenario(scenario)} {self._satisfaction_prompt()}"

    def _fee_collect_prompt_for_scenario(self, scenario: Scenario) -> str:
        return fee_collect_utterance(request_type=scenario.request.request_type)

    def _satisfaction_prompt(self) -> str:
        return ask_satisfaction_utterance()

    def _end_prompt_for_scenario(self, scenario: Scenario) -> str:
        return end_utterance(brand=self._effective_brand_for_service_utterance(scenario))

    @staticmethod
    def _extract_satisfaction_score(text: str) -> str:
        match = re.search(r"[1-5]", text or "")
        return match.group(0) if match else ""

    def _build_opening_prompt(self, scenario: Scenario) -> str:
        action = "维修" if scenario.request.request_type == "fault" else "安装"
        return f"您好，很高兴为您服务，请问是{scenario.product.brand}{self._product_name(scenario)}需要{action}吗？"

    @staticmethod
    def _last_turn_by_speaker(
        transcript: list[DialogueTurn],
        speaker: str,
    ) -> DialogueTurn | None:
        for turn in reversed(transcript):
            if normalize_speaker(turn.speaker) == speaker:
                return turn
        return None

    @staticmethod
    def _previous_service_text(transcript: list[DialogueTurn]) -> str:
        if len(transcript) < 2:
            return ""
        previous_turn = transcript[-2]
        return previous_turn.text if normalize_speaker(previous_turn.speaker) == SERVICE_SPEAKER else ""

    @staticmethod
    def _classify_yes_no(text: str) -> str | None:
        normalized = (text or "").replace("，", "").replace("。", "").replace(" ", "")
        relaxed = re.sub(r"^(?:啊|嗯|额|呃|诶|欸|哎|这)+", "", normalized)
        negative_keywords = (
            "不能",
            "不行",
            "联系不到",
            "联系不上",
            "打不到",
            "打不通",
            "不是",
            "不对",
            "不太对",
            "不准确",
            "不完全对",
            "有误",
            "错了",
            "没到",
            "还没到",
            "未到",
            "否",
        )
        positive_keywords = (
            "能联系",
            "能打通",
            "就是这个",
            "没错",
            "正确",
            "到了",
            "到货了",
            "已经到了",
            "已经到货",
            "可以联系",
            "可以的",
        )
        positive_prefixes = (
            "能",
            "能啊",
            "能的",
            "可以",
            "可以啊",
            "可以呀",
            "可以的",
            "是的",
            "是滴",
            "是呀",
            "是啊",
            "对的",
            "对滴",
            "对",
            "是",
            "行",
            "嗯",
            "嗯嗯",
            "嗯呐",
            "好",
            "好的",
        )

        if any(keyword in normalized for keyword in negative_keywords):
            return "no"
        if any(keyword in normalized for keyword in positive_keywords) or any(
            keyword in relaxed for keyword in positive_keywords
        ):
            return "yes"
        if any(normalized.startswith(prefix) for prefix in positive_prefixes) or any(
            relaxed.startswith(prefix) for prefix in positive_prefixes
        ):
            return "yes"
        return None

    @staticmethod
    def _extract_contact_phone_owner_from_text(text: str) -> str:
        normalized = re.sub(r"\s+", "", text or "")
        owner_tokens = (
            "老伴",
            "爱人",
            "老婆",
            "老公",
            "媳妇",
            "丈夫",
            "先生",
            "太太",
            "对象",
            "父亲",
            "母亲",
            "爸爸",
            "妈妈",
            "儿子",
            "女儿",
            "家里人",
            "家属",
        )
        for token in owner_tokens:
            if token in normalized:
                return token
        if any(token in normalized for token in ("另一个号码", "另外一个号码", "别的号码", "其他号码", "另一个", "另外一个", "别的", "其他")):
            return "另一个号码"
        return ""

    @classmethod
    def _is_alternate_contact_request(cls, text: str) -> bool:
        normalized = re.sub(r"\s+", "", text or "")
        if not normalized:
            return False
        owner = cls._extract_contact_phone_owner_from_text(normalized)
        if owner and owner != "另一个号码":
            family_patterns = (
                rf"(留|记|登记|写)(?:一个)?(?:我)?{re.escape(owner)}(?:的)?(?:号码)?",
                rf"(留|记|登记|写)个(?:我)?{re.escape(owner)}(?:的)?(?:号码)?",
                rf"(联系|找|打给|打)(?:我)?{re.escape(owner)}",
                rf"{re.escape(owner)}(?:的)?(?:号码)?(?:吧|就行|就可以)",
            )
            if any(re.search(pattern, normalized) for pattern in family_patterns):
                return True
        alternate_patterns = (
            r"联系另一个",
            r"联系另外一个",
            r"联系别的",
            r"联系其他",
            r"打另一个",
            r"打另外一个",
            r"打别的",
            r"换另一个",
            r"换一个号码",
            r"换一个(?:吧|啊|呗)?",
            r"换个号码",
            r"换个别的",
            r"换另外一个",
            r"换别的",
            r"换其他",
            r"留一个",
            r"留个",
            r"记一个",
            r"记个",
            r"登记一个",
            r"登记个",
            r"别打这个",
            r"不要打这个",
            r"另一个号码",
            r"另外一个号码",
            r"别的号码",
            r"其他号码",
        )
        if any(re.search(pattern, normalized) for pattern in alternate_patterns):
            return True
        if any(token in normalized for token in ("不在家", "不方便接", "可能有事", "到时候有事")) and owner:
            return True
        return False

    @classmethod
    def _should_verify_contactable_intent_with_model(
        cls,
        text: str,
        *,
        heuristic: str | None,
    ) -> bool:
        normalized = re.sub(r"\s+", "", text or "")
        if not normalized or heuristic == "no":
            return False
        if heuristic not in {"yes", "no"}:
            return True

        contrast_markers = ("但是", "不过", "可是", "只是", "但")
        switch_patterns = (
            r"换一个",
            r"换个",
            r"另外",
            r"另一个",
            r"别的",
            r"其他",
            r"备用号码",
            r"备用电话",
            r"留个",
            r"留一个",
            r"记个",
            r"记一个",
            r"登记个",
            r"登记一个",
            r"写个",
            r"写一个",
        )
        if cls._extract_contact_phone_owner_from_text(normalized):
            return True
        if any(marker in normalized for marker in contrast_markers):
            return True
        return any(re.search(pattern, normalized) for pattern in switch_patterns)

    def _classify_contactable_intent_with_model(
        self,
        text: str,
        *,
        user_round_index: int = 0,
    ) -> str | None:
        if self.contact_intent_inference_callback is None:
            return None
        try:
            payload = self._invoke_inference_callback(
                self.contact_intent_inference_callback,
                user_text=text,
                user_round_index=user_round_index,
            )
        except Exception:
            return None
        if not isinstance(payload, dict):
            return None
        intent = str(payload.get("intent", "")).strip().lower()
        if intent in {"yes", "no"}:
            self.last_used_model_intent_inference = True
            return intent
        return None

    def _classify_contactable_intent(self, text: str, *, user_round_index: int = 0) -> str | None:
        normalized = re.sub(r"\s+", "", text or "")
        if self.contact_intent_inference_callback is not None:
            model_intent = self._classify_contactable_intent_with_model(
                text,
                user_round_index=user_round_index,
            )
            if model_intent in {"yes", "no"}:
                return model_intent
        if self._is_alternate_contact_request(normalized):
            return "no"
        heuristic = self._classify_yes_no(normalized)
        if heuristic in {"yes", "no"}:
            return heuristic
        return None

    def _classify_confirmation_intent(
        self,
        text: str,
        *,
        prompt_kind: str,
        user_round_index: int = 0,
    ) -> str | None:
        if self.confirmation_intent_inference_callback is None:
            heuristic = self._classify_yes_no(text)
            return heuristic if heuristic in {"yes", "no"} else None
        try:
            payload = self._invoke_inference_callback(
                self.confirmation_intent_inference_callback,
                prompt_kind=prompt_kind,
                user_text=text,
                user_round_index=user_round_index,
            )
        except Exception:
            heuristic = self._classify_yes_no(text)
            return heuristic if heuristic in {"yes", "no"} else None
        if not isinstance(payload, dict):
            heuristic = self._classify_yes_no(text)
            return heuristic if heuristic in {"yes", "no"} else None
        intent = str(payload.get("intent", "")).strip().lower()
        if intent in {"yes", "no"}:
            self.last_used_model_intent_inference = True
            return intent
        heuristic = self._classify_yes_no(text)
        return heuristic if heuristic in {"yes", "no"} else None

    def _classify_observation_address_confirmation_followup_intent(
        self,
        text: str,
        *,
        confirmation_address: str,
        user_round_index: int = 0,
    ) -> str:
        def _rule_evidence_intent() -> str:
            confirmation_intent = self._classify_confirmation_intent(
                text,
                prompt_kind="address_confirmation",
                user_round_index=user_round_index,
            )
            if confirmation_intent == "yes":
                residual_text = self._strip_address_confirmation_affirmation_prefix(text)
                prepared_user_address = self._prepare_address_for_confirmation(residual_text)
                if prepared_user_address:
                    merged_candidate = self._merge_address_candidate(
                        confirmation_address,
                        prepared_user_address,
                    )
                    if merged_candidate and self._address_input_makes_progress(
                        existing=confirmation_address,
                        incoming=prepared_user_address,
                        merged=merged_candidate,
                    ):
                        return "add"
                return "confirm_only"
            denial_address, _ = self._resolve_confirmation_denial_address_candidate(
                transcript=[],
                user_text=text,
                confirmation_address=confirmation_address,
            )
            if denial_address:
                return "modify"
            if confirmation_intent == "no":
                return "unknown"
            prepared_user_address = self._prepare_address_for_confirmation(text)
            if prepared_user_address:
                merged_candidate = self._merge_address_candidate(
                    confirmation_address,
                    prepared_user_address,
                )
                if merged_candidate and self._address_input_makes_progress(
                    existing=confirmation_address,
                    incoming=prepared_user_address,
                    merged=merged_candidate,
                ):
                    return "add"
            return "unknown"

        if self.confirmation_intent_inference_callback is not None:
            try:
                payload = self._invoke_inference_callback(
                    self.confirmation_intent_inference_callback,
                    prompt_kind="address_confirmation_observation_followup",
                    user_text=text,
                    user_round_index=user_round_index,
                    confirmation_address=confirmation_address,
                )
            except Exception:
                payload = None
            if isinstance(payload, dict):
                intent = str(payload.get("intent", "")).strip().lower()
                if intent in {"confirm_only", "modify", "add", "delete", "unknown"}:
                    rule_intent = _rule_evidence_intent()
                    if intent == "confirm_only":
                        self.last_used_model_intent_inference = True
                        return "confirm_only" if rule_intent != "add" else "add"
                    if intent in {"add", "modify", "delete"}:
                        self.last_used_model_intent_inference = True
                        if rule_intent in {"add", "modify", "delete"}:
                            return rule_intent
                        return "confirm_only" if rule_intent == "confirm_only" else "unknown"
                    self.last_used_model_intent_inference = True
                    return rule_intent

        return _rule_evidence_intent()

    @classmethod
    def _strip_address_confirmation_affirmation_prefix(cls, text: str) -> str:
        cleaned = str(text or "").strip()
        patterns = (
            r"^(?:啊|嗯|额|呃|诶|欸|哎|哦|喔|哈)[，,\s]*",
            r"^(?:对(?:的|滴)?|是(?:的|滴)?|嗯(?:嗯|呐)?|没错|正确|就是这个|就这个)[，,\s]*",
            r"^(?:就是|按你刚核对那个|按刚才那个|按这个地址)[，,\s]*",
        )
        updated = True
        while cleaned and updated:
            updated = False
            for pattern in patterns:
                next_cleaned = re.sub(pattern, "", cleaned)
                if next_cleaned != cleaned:
                    cleaned = next_cleaned.strip()
                    updated = True
        return cleaned

    def _classify_product_routing_answer_key(
        self,
        *,
        prompt_key: str,
        user_text: str,
        user_round_index: int = 0,
    ) -> str:
        if self.product_routing_intent_inference_callback is not None:
            try:
                payload = self._invoke_inference_callback(
                    self.product_routing_intent_inference_callback,
                    prompt_key=prompt_key,
                    user_text=user_text,
                    user_round_index=user_round_index,
                )
            except Exception:
                payload = None
            if isinstance(payload, dict):
                answer_key = str(payload.get("answer_key", "")).strip()
                inferred_prompt_key = str(payload.get("prompt_key", "")).strip()
                if (
                    answer_key
                    and answer_key in allowed_product_routing_answer_keys(prompt_key)
                    and (not inferred_prompt_key or inferred_prompt_key == prompt_key)
                ):
                    self.last_used_model_intent_inference = True
                    return answer_key

        heuristic = infer_product_routing_answer_key(prompt_key, user_text)
        if heuristic:
            return heuristic
        return ""

    def _classify_opening_intent(
        self,
        text: str,
        *,
        user_round_index: int = 0,
        force_model: bool = False,
        request_type: str = "fault",
    ) -> str:
        if force_model and self.opening_intent_inference_callback is not None:
            return self._classify_opening_intent_with_model(
                text,
                user_round_index=user_round_index,
            )
        if self.opening_intent_inference_callback is not None:
            model_intent = self._classify_opening_intent_with_model(
                text,
                user_round_index=user_round_index,
            )
            if model_intent in {"yes", "no", "issue_detail"}:
                return model_intent

        compact = re.sub(r"[，。！？、,.!\s]", "", str(text or ""))
        yes_no = self._classify_yes_no(text)
        if yes_no == "no":
            return "no"
        if yes_no == "yes" and not self._strip_opening_affirmation_noise(compact):
            return yes_no
        if len(compact) > 6 and self._opening_response_contains_issue_detail(text, request_type=request_type):
            return "issue_detail"
        if yes_no == "yes":
            return "yes"

        inferred_intent = self._classify_opening_intent_with_model(
            text,
            user_round_index=user_round_index,
        )
        return inferred_intent

    def _classify_opening_intent_with_model(
        self,
        text: str,
        *,
        user_round_index: int = 0,
    ) -> str:
        if self.opening_intent_inference_callback is None:
            return ""
        try:
            payload = self._invoke_inference_callback(
                self.opening_intent_inference_callback,
                user_text=text,
                user_round_index=user_round_index,
            )
        except Exception:
            return ""
        if not isinstance(payload, dict):
            return ""
        intent = str(payload.get("intent", "")).strip().lower()
        if intent in {"yes", "no", "issue_detail"}:
            self.last_used_model_intent_inference = True
            return intent
        return ""

    def _extract_issue_description_with_model(
        self,
        text: str,
        *,
        user_round_index: int = 0,
    ) -> str:
        if self.issue_description_extraction_callback is None:
            return ""
        try:
            payload = self._invoke_inference_callback(
                self.issue_description_extraction_callback,
                user_text=text,
                user_round_index=user_round_index,
            )
        except Exception:
            return ""
        if not isinstance(payload, dict):
            return ""
        issue_description = str(payload.get("issue_description", "")).strip()
        if issue_description:
            self.last_used_model_intent_inference = True
        return issue_description

    def _extract_surname_with_model(
        self,
        text: str,
        *,
        user_round_index: int = 0,
    ) -> str:
        if self.surname_inference_callback is None:
            return ""
        try:
            payload = self._invoke_inference_callback(
                self.surname_inference_callback,
                user_text=text,
                user_round_index=user_round_index,
            )
        except Exception:
            return ""
        if not isinstance(payload, dict):
            return ""
        surname = str(payload.get("surname", "")).strip()
        if not surname or not re.fullmatch(r"[一-龥]{1,2}", surname):
            return ""
        self.last_used_model_intent_inference = True
        return surname

    def _resolve_issue_description(
        self,
        text: str,
        *,
        user_round_index: int = 0,
        request_type: str = "fault",
        use_model: bool = False,
        strict_model: bool = False,
    ) -> str:
        issue_description = str(text or "").strip()
        if not issue_description:
            return ""
        if use_model and self.issue_description_extraction_callback is not None:
            extracted_issue_description = self._extract_issue_description_with_model(
                issue_description,
                user_round_index=user_round_index,
            )
            if extracted_issue_description:
                return extracted_issue_description
            if strict_model:
                return ""
        if request_type == "fault" and not self._contains_specific_fault_detail(issue_description):
            return ""
        return issue_description

    @staticmethod
    def _invoke_inference_callback(
        callback: Callable[..., dict[str, Any] | None],
        **kwargs: Any,
    ) -> dict[str, Any] | None:
        signature = inspect.signature(callback)
        accepted_kwargs = {
            name: value
            for name, value in kwargs.items()
            if name in signature.parameters
        }
        return callback(**accepted_kwargs)

    @classmethod
    def _strip_opening_affirmation_noise(cls, text: str) -> str:
        residual = str(text or "")
        filler_tokens = ("啊", "嗯", "额", "呃", "诶", "欸", "哎", "这")
        affirmative_tokens = (
            "是的",
            "是滴",
            "是呀",
            "是啊",
            "对的",
            "对滴",
            "好的",
            "可以",
            "嗯嗯",
            "嗯呐",
            "对",
            "是",
            "行",
            "嗯",
            "好",
        )
        while residual:
            updated = residual
            for token in filler_tokens:
                while updated.startswith(token):
                    updated = updated[len(token) :]
            if updated != residual:
                residual = updated
                continue
            matched = False
            for token in affirmative_tokens:
                if residual.startswith(token):
                    residual = residual[len(token) :]
                    matched = True
                    break
            if not matched:
                break
        return residual

    @classmethod
    def _opening_response_contains_issue_detail(
        cls,
        text: str,
        *,
        request_type: str = "fault",
    ) -> bool:
        normalized = (text or "").strip()
        if not normalized:
            return False
        compact = re.sub(r"[，。！？、,.!\s]", "", normalized)
        greeting_only_patterns = (
            r"^(你好|您好|哈喽|hello|hi|喂|在吗|有人吗)+$",
        )
        positive_only_patterns = (
            r"^(对|对的|对滴|是|是的|是滴|是呀|是啊|嗯|嗯嗯|嗯呐|哎对|对啊|好|好的|没错|对没错)+$",
        )
        if any(re.fullmatch(pattern, compact, flags=re.IGNORECASE) for pattern in greeting_only_patterns):
            return False
        if any(re.fullmatch(pattern, compact) for pattern in positive_only_patterns):
            return False
        if cls._classify_yes_no(normalized) == "yes" and not cls._strip_opening_affirmation_noise(compact):
            return False
        if cls._classify_yes_no(normalized) == "yes" and len(compact) <= 6:
            return False
        if request_type == "fault":
            return cls._contains_specific_fault_detail(normalized)
        return True

    @classmethod
    def _contains_specific_fault_detail(cls, text: str) -> bool:
        compact = cls._strip_opening_affirmation_noise(
            re.sub(r"[，。！？、,.!\s]", "", str(text or ""))
        )
        if not compact:
            return False
        if cls._is_product_info_only_statement(compact):
            return False

        specific_patterns = (
            r"不加热",
            r"不制热",
            r"没热水",
            r"没有热水",
            r"加热(?:特别|很|太|比较)?慢",
            r"升温(?:特别|很|太|比较)?慢",
            r"烧水(?:特别|很|太|比较)?慢",
            r"忽冷忽热",
            r"时冷时热",
            r"冷热不均",
            r"温度(?:不稳|不稳定|上不去|太低|偏低)",
            r"水温(?:不稳|不稳定|上不去|太低|偏低)",
            r"出水(?:太少|很小|变小|不大)",
            r"花洒出水(?:会)?变小",
            r"水压.*(?:太小|很小|变小|不稳|不稳定)",
            r"水量.*(?:太小|很小|变小)",
            r"漏水",
            r"渗水",
            r"滴水",
            r"漏电",
            r"异响",
            r"噪音(?:很大|特别大|大)",
            r"很吵",
            r"特别吵",
            r"不启动",
            r"启动不了",
            r"启动不起来",
            r"无法启动",
            r"开不了机",
            r"开机不了",
            r"不通电",
            r"没反应",
            r"不工作",
            r"不能用",
            r"用不了",
            r"跳闸",
            r"停机",
            r"报码",
            r"报错",
            r"报警",
            r"故障码",
            r"显示.*(?:e\d+|f\d+|p\d+)",
            r"(压缩机|主板|风机|水泵|传感器|阀门|面板|显示屏|控制器).*坏",
            r"洗澡.*(?:忽冷忽热|水小|没热水|不热|不爽)",
        )
        if any(re.search(pattern, compact, flags=re.IGNORECASE) for pattern in specific_patterns):
            return True

        generic_fault_tokens = (
            "坏了",
            "坏掉",
            "坏掉了",
            "有问题",
            "出问题",
            "有故障",
            "故障了",
            "不行了",
        )
        if any(token in compact for token in generic_fault_tokens):
            return False

        return False

    @classmethod
    def _is_product_info_only_statement(cls, text: str) -> bool:
        residual = str(text or "")
        if not residual:
            return False
        cleanup_patterns = (
            r"[零一二三四五六七八九十百千万两\d]+\s*(?:升|匹|p|P|l|L)",
            r"(空气能热水机|空气能热水器|空气能|热水器|热水机|机器|机子|产品|设备)",
            r"(品牌|系列|型号|机型)",
            r"(家用机|商用机|楼宇机|分体机|一体机)",
            r"(美的|小天鹅|华凌|COLMO|colmo)",
            r"(一个|一台|一套|这个|这个是|这是|这种|那种|款|个|台|套|的)",
        )
        for pattern in cleanup_patterns:
            residual = re.sub(pattern, "", residual, flags=re.IGNORECASE)
        residual = re.sub(r"[啊呀呢吧哦额呃嗯]", "", residual)
        return not residual

    @staticmethod
    def _contact_phone_owner(scenario: Scenario) -> str:
        value = scenario.hidden_context.get("contact_phone_owner", "")
        return str(value).strip()

    @staticmethod
    def _current_call_phone(scenario: Scenario) -> str:
        value = scenario.hidden_context.get("contact_phone", "")
        return str(value).strip()

    @staticmethod
    def _service_known_address_value(scenario: Scenario) -> str:
        if not bool(scenario.hidden_context.get("service_known_address", False)):
            return ""
        value = scenario.hidden_context.get("service_known_address_value", "")
        return str(value).strip()

    def _start_product_arrival_confirmation(
        self,
        *,
        scenario: Scenario,
        runtime_state: ServiceRuntimeState,
        slot_updates: dict[str, str] | None = None,
    ) -> ServicePolicyResult:
        runtime_state.expected_product_arrival_confirmation = True
        return ServicePolicyResult(
            reply=self._product_arrival_prompt(scenario),
            slot_updates=slot_updates or {},
            is_ready_to_close=False,
        )

    def _start_address_confirmation(
        self,
        *,
        scenario: Scenario,
        runtime_state: ServiceRuntimeState,
        address: str,
        slot_updates: dict[str, str],
        use_known_address_prompt: bool = False,
    ) -> ServicePolicyResult:
        confirmation_address = self._canonical_confirmation_address(
            address,
            scenario.customer.address,
        )
        runtime_state.expected_address_confirmation = True
        runtime_state.address_confirmation_triggered_by_observation = False
        runtime_state.address_confirmation_started_from_known_address = use_known_address_prompt
        runtime_state.awaiting_full_address = False
        runtime_state.pending_address_confirmation = confirmation_address
        runtime_state.partial_address_candidate = ""
        runtime_state.address_vague_retry_count = 0
        runtime_state.last_address_followup_prompt = ""
        return ServicePolicyResult(
            reply=self._address_confirmation_prompt(
                confirmation_address,
                use_known_address_prompt=use_known_address_prompt,
            ),
            slot_updates=slot_updates,
            is_ready_to_close=False,
        )

    @classmethod
    def _canonical_confirmation_address(cls, address: str, actual_address: str) -> str:
        normalized_candidate = cls._normalize_address_text(address)
        normalized_actual = cls._normalize_address_text(actual_address)
        if not normalized_candidate or normalized_candidate == normalized_actual:
            return cls._normalize_confirmation_address_order(address)
        if (
            normalized_candidate in normalized_actual
            and cls._address_has_detail_info(address)
            and cls._has_required_address_precision(address, actual_address)
        ):
            return cls._normalize_confirmation_address_order(actual_address)
        if cls._compact_address_text(address) == cls._compact_address_text(actual_address):
            return cls._normalize_confirmation_address_order(actual_address)
        candidate_components = extract_address_components(address)
        actual_components = extract_address_components(actual_address)
        if (
            candidate_components.has_precise_detail
            and components_match(candidate_components, actual_components)
            and cls._has_required_address_precision(address, actual_address)
        ):
            return cls._normalize_confirmation_address_order(actual_address)
        return cls._normalize_confirmation_address_order(address)

    @classmethod
    def _normalize_confirmation_address_order(cls, address: str) -> str:
        normalized = cls._normalize_address_text(address)
        if not normalized:
            return address
        components = extract_address_components(address)
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
        normalized_room = cls._normalize_address_text(components.room)
        room_digits = re.sub(r"室$", "", normalized_room)
        if (
            normalized_room
            and normalized_room not in normalized
            and room_digits
            and normalized.endswith(room_digits)
            and (components.building or components.unit or components.floor)
        ):
            return ordered or address
        detail_tokens = [token for token in (components.building, components.unit, components.floor, components.room) if token]
        if len(detail_tokens) < 2:
            return address

        token_positions = [normalized.find(cls._normalize_address_text(token)) for token in detail_tokens]
        if any(position < 0 for position in token_positions) or token_positions == sorted(token_positions):
            return address

        return ordered or address

    @classmethod
    def _prepare_address_for_confirmation(cls, text: str) -> str:
        cleaned = (text or "").strip().strip("，,。！？!?")
        discourse_prefix_patterns = (
            r"^(?:(?:啥|啊|额|呃|嗯|嗯嗯|那个|就是|诶|欸|哎|唉|哦|喔|哈)[，,\s]*)+",
        )
        for pattern in discourse_prefix_patterns:
            cleaned = re.sub(pattern, "", cleaned)
        prefix_patterns = (
            r"^(好的[，,\s]*)?地址是",
            r"^(好的[，,\s]*)?我家地址是",
            r"^(好的[，,\s]*)?详细地址是",
            r"^(好的[，,\s]*)?我的地址是",
            r"^(好的[，,\s]*)?我现在地址是",
            r"^(好的[，,\s]*)?我家是",
            r"^(好的[，,\s]*)?家里是",
            r"^(?:应该是|应为|改成|就是)[，,\s]*",
        )
        for pattern in prefix_patterns:
            cleaned = re.sub(pattern, "", cleaned)
        negated_location_switch_patterns = (
            r"^(?:不是|不对)[，,\s]*(?:我(?:现在|目前|这边|人)?在)\s*",
            r"^(?:不在|不是在|不住在)\s*[^，,。！？!?]{1,40}?(?:[，,]\s*)?(?:现在)?在\s*",
            r"^(?:不是|不对)\s*[^，,。！？!?]{1,40}?(?:[，,]\s*)?(?:现在)?(?:在|是|而是)\s*",
        )
        for pattern in negated_location_switch_patterns:
            cleaned = re.sub(pattern, "", cleaned)
        cleaned = re.sub(
            r"^(?:我(?:现在|目前|这边|人)?在)\s*(?=(?:[\u4e00-\u9fa5]{2,}(?:省|市|区|县|旗|镇|乡|街道|路|街|大道|巷|弄|胡同)|[A-Za-z0-9\u4e00-\u9fa5]{2,30}(?:小区|社区|花园|公寓|苑|府|里|村|大厦|中心|广场|城|大学|学校|校区|医院|酒店|宾馆|饭店|市场|园区|厂区|景区)|江苏|浙江|安徽|福建|江西|山东|河南|湖北|湖南|广东|海南|四川|贵州|云南|陕西|甘肃|青海|河北|山西|辽宁|吉林|黑龙江|内蒙古|广西|西藏|宁夏|新疆|台湾|香港|澳门|北京|上海|天津|重庆))",
            "",
            cleaned,
        )
        cleaned = re.sub(
            r"^(?:就在|就在那个|就是在|我在|在)\s*(?=[\u4e00-\u9fa5]{2,}(?:省|市|区|县|旗|镇|乡|街道))",
            "",
            cleaned,
        )
        cleaned = re.split(r"[。！？!?]", cleaned, maxsplit=1)[0]
        cleaned = re.split(r"[，,]\s*(?:麻烦|另外|还有|辛苦|谢谢|尽快|催一下|师傅)", cleaned, maxsplit=1)[0]
        structured = cls._extract_structured_address_from_text(cleaned)
        if structured:
            return canonicalize_address_text(structured)
        return canonicalize_address_text(cleaned.strip().strip("，,。！？!?"))

    @classmethod
    def _extract_structured_address_from_text(cls, text: str) -> str:
        clauses = [
            re.sub(r"^(?:哦|嗯|额|呃|那个|就是|然后|还有)\s*", "", clause.strip())
            for clause in re.split(r"[，,；;]", text or "")
            if clause.strip()
        ]
        if not clauses:
            return ""

        ordered_parts: dict[str, str] = {}
        matched_label = False
        patterns = (
            ("province", r"^(?:省份|省)\s*(?:是|在)?\s*(.+)$"),
            ("city", r"^(?:城市|市)\s*(?:是|在)?\s*(.+)$"),
            ("district", r"^(?:区县|区|县)\s*(?:是|在)?\s*(.+)$"),
            ("town", r"^(?:街道|乡镇|镇|乡)\s*(?:是|在)?\s*(.+)$"),
            ("road", r"^(?:路|街道地址|街|大道|巷|弄|胡同)\s*(?:是|在)?\s*(.+)$"),
            ("community", r"^(?:小区|社区|楼盘)\s*(?:是|在)?\s*(.+)$"),
            ("building", r"^(?:楼栋|栋|幢|座|楼号|楼)\s*(?:是|在)?\s*(.+)$"),
            ("unit", r"^(?:单元)\s*(?:是|在)?\s*(.+)$"),
            ("floor", r"^(?:楼层|层)\s*(?:是|在)?\s*(.+)$"),
            ("room", r"^(?:房间|房号|门牌号|门牌|室)\s*(?:是|在)?\s*(.+)$"),
        )
        for clause in clauses:
            for kind, pattern in patterns:
                match = re.match(pattern, clause)
                if not match:
                    continue
                matched_label = True
                value = match.group(1).strip("：:，,。；; ")
                if not value:
                    break
                if kind == "community":
                    if not value.endswith(ADDRESS_COMMUNITY_LABEL_SUFFIXES):
                        value = f"{value}小区"
                elif kind == "room" and re.fullmatch(r"\d{2,4}", value):
                    value = f"{value}室"
                ordered_parts[kind] = value
                break

        if not matched_label:
            return ""

        return "".join(
            ordered_parts.get(kind, "")
            for kind in ("province", "city", "district", "town", "road", "community", "building", "unit", "floor", "room")
        )

    @classmethod
    def _extract_address_candidate_from_denial(
        cls,
        *,
        user_text: str,
        confirmation_address: str,
    ) -> str:
        raw_candidates = [
            segment.strip("，,。！？!? ")
            for segment in re.split(r"[。！？!?]", user_text or "")
            if segment.strip("，,。！？!? ")
        ]
        raw_candidates.append(str(user_text or "").strip())

        cleanup_patterns = (
            r"^(不对|不是这个地址|地址不对|不太对)[，,\s]*",
            r"^不是[，,\s]*(?=(?:[\u4e00-\u9fa5]{2,}(?:省|市|区|县|镇|乡|街道|路|街|大道|巷|弄|胡同)|[A-Za-z0-9\u4e00-\u9fa5]{2,20}(?:小区|花园|公寓|苑|府|里|村|大厦|中心|广场|城|栋|幢|座|楼|单元|室|号)))",
            r"^(?:换一个|换个)(?:地址|地方)?[，,\s]*",
            r"^(?:留个|记个|登记个)(?:新)?地址[，,\s]*",
            r"^(?:不是|不对)[，,\s]*(?:换一个|换个)(?:地址|地方)?[，,\s]*",
            r"^(?:不是|不对)[，,\s]*(?:留个|记个|登记个)(?:新)?地址[，,\s]*",
            r"^(?:不是|不对)[，,\s]*(?:我)?(?:换|改)(?:个|成)?(?:新)?地址[，,\s]*",
        )
        pure_denial_patterns = (
            r"^(?:不|不是|不对|不太对|不对的|不是的|不是哦|不是啊|不是哈|不是呢|不对哦|不对啊)$",
            r"^(?:不是这个|不是这个地址|不是这个地方|这不是|这个不对|地址不对)$",
            r"^(?:换一个|换个|重新来|重新说|重说一下|重来一下)$",
            r"^(?:不是|不对)[，,\s]*(?:换一个|换个|重新来|重新说|重说一下|重来一下)$",
            r"^(?:留个|记个|登记个)(?:新)?地址$",
            r"^(?:不是|不对)[，,\s]*(?:留个|记个|登记个)(?:新)?地址$",
            r"^(?:我)?换地方了$",
            r"^(?:不是|不对)[，,\s]*(?:我)?换地方了$",
            r"^(?:我)?搬家了$",
            r"^(?:不是|不对)[，,\s]*(?:我)?搬家了$",
        )
        correction_patterns = (
            r"(?:就是|改成|换成|应该是|应为)\s*([^，,。！？!?]+)$",
            r"(?:正确的是|正确地址是)\s*([^，,。！？!?]+)$",
            r"(?:就是|改成|换成|应该是|应为)\s*([^，,。！？!?]+)",
        )

        normalized_confirmation = cls._normalize_address_text(confirmation_address)
        confirmation_components = extract_address_components(confirmation_address)
        strong_detail_markers = r"(路|街|大道|巷|弄|胡同|小区|花园|公寓|苑|府|里|村|大厦|中心|广场|城|栋|幢|座|楼|单元|室|号)"
        generic_non_address_patterns = (
            r"前面.*(?:小区|地址|地方).*(?:错|不对)",
            r"后面.*(?:小区|地址|地方).*(?:错|不对)",
            r"老家那个地址",
            r"那个地址",
            r"换一个(?:地址|地方)?$",
            r"换个(?:地址|地方)?$",
            r"(?:留个|记个|登记个)(?:新)?地址$",
            r"(?:我)?换地方了$",
            r"(?:我)?搬家了$",
        )

        for raw_candidate in reversed(raw_candidates):
            prepared = cls._prepare_address_for_confirmation(raw_candidate)
            if not prepared:
                continue

            cleaned = prepared
            for pattern in cleanup_patterns:
                cleaned = re.sub(pattern, "", cleaned)
            cleaned = re.sub(
                r"^.*?(?=(?:我家地址是|我家是|家里是|我现在地址是|我现在是|我的地址是|正确地址是|地址是))",
                "",
                cleaned,
            )
            cleaned = re.sub(
                r"^(我家地址是|我家是|家里是|我现在地址是|我现在是|我的地址是|正确地址是|地址是|是)[，,\s]*",
                "",
                cleaned,
            )
            for pattern in correction_patterns:
                match = re.search(pattern, cleaned)
                if match:
                    cleaned = match.group(1)
                    break
            cleaned = re.split(r"[，,]\s*(?:不是|不对)", cleaned, maxsplit=1)[0]

            cleaned = cleaned.strip("，,。！？!? ")
            normalized = cls._normalize_address_text(cleaned)
            if not normalized or normalized == normalized_confirmation:
                continue
            if any(re.fullmatch(pattern, normalized) for pattern in pure_denial_patterns):
                continue
            if any(re.search(pattern, normalized) for pattern in generic_non_address_patterns):
                continue

            components = extract_address_components(cleaned)
            if components.has_precise_detail and components_match(components, confirmation_components):
                continue
            if components.has_precise_detail:
                return cleaned
            if cls._address_has_admin_region(cleaned):
                return cleaned
            if components.has_locality:
                return cleaned
            if re.search(strong_detail_markers, normalized) and cls._address_has_detail_info(cleaned):
                return cleaned
        return ""

    @classmethod
    def _extract_strong_address_candidate_from_denial(
        cls,
        *,
        user_text: str,
        confirmation_address: str,
    ) -> str:
        candidate = cls._extract_address_candidate_from_denial(
            user_text=user_text,
            confirmation_address=confirmation_address,
        )
        if not candidate:
            return ""

        components = extract_address_components(candidate)
        region_levels = sum(
            1 for value in (components.province, components.city, components.district) if value
        )
        has_strong_locality = bool(components.has_locality and (components.has_admin_region or components.town))
        has_strong_region = region_levels >= 2
        has_strong_detail = bool(
            components.has_precise_detail or cls._has_nonstandard_address_detail(candidate)
        )

        if has_strong_detail:
            return candidate
        if has_strong_locality:
            return candidate
        if has_strong_region:
            return candidate
        return ""

    def _resolve_confirmation_denial_address_candidate(
        self,
        *,
        transcript: list[DialogueTurn],
        user_text: str,
        confirmation_address: str,
    ) -> tuple[str, bool]:
        denial_address = self._extract_address_candidate_from_denial(
            user_text=user_text,
            confirmation_address=confirmation_address,
        )
        strong_denial_address = self._extract_strong_address_candidate_from_denial(
            user_text=user_text,
            confirmation_address=confirmation_address,
        )
        if strong_denial_address:
            denial_address = strong_denial_address
        use_confirmation_as_merge_source = bool(strong_denial_address)
        if (
            self.address_inference_callback is not None
            and not self._is_non_address_switch_request_after_denial(user_text)
        ):
            inferred_denial_address = self._infer_address_candidate_with_callback(
                user_text=user_text,
                confirmation_address=confirmation_address,
                partial_address_candidate="",
                last_address_followup_prompt="",
                dialogue_history=self._dialogue_history_text(transcript),
            )
            if inferred_denial_address and (
                not denial_address
                or self._should_prefer_model_admin_backfill_candidate(
                    rule_candidate=denial_address,
                    model_candidate=inferred_denial_address,
                )
                or self._should_prefer_model_denial_candidate(
                    rule_candidate=denial_address,
                    model_candidate=inferred_denial_address,
                )
                or self._should_request_model_province_backfill_for_cross_city_correction(
                    confirmation_address=confirmation_address,
                    candidate=denial_address,
                )
            ):
                denial_address = inferred_denial_address
                use_confirmation_as_merge_source = False
        return denial_address, use_confirmation_as_merge_source

    @classmethod
    def _is_non_address_switch_request_after_denial(cls, text: str) -> bool:
        normalized = cls._normalize_address_text(text)
        if not normalized:
            return False
        patterns = (
            r"^(?:换一个|换个|重新来|重新说|重说一下|重来一下)$",
            r"^(?:留个|记个|登记个)(?:新)?地址$",
            r"^(?:不是|不对)[，,\s]*(?:换一个|换个|重新来|重新说|重说一下|重来一下)$",
            r"^(?:不是|不对)[，,\s]*(?:留个|记个|登记个)(?:新)?地址$",
            r"^(?:不是|不对)[，,\s]*(?:我)?(?:换|改)(?:个|成)?(?:新)?地址$",
            r"^(?:我)?换地方了$",
            r"^(?:不是|不对)[，,\s]*(?:我)?换地方了$",
            r"^(?:我)?搬家了$",
            r"^(?:不是|不对)[，,\s]*(?:我)?搬家了$",
        )
        return any(re.fullmatch(pattern, normalized) for pattern in patterns)

    @staticmethod
    def _normalize_address_text(text: str) -> str:
        return normalize_address_text(text)

    @classmethod
    def _compact_address_text(cls, text: str) -> str:
        return compact_address_text(text)

    @classmethod
    def _is_complete_address(cls, candidate: str, actual_address: str) -> bool:
        if not candidate:
            return False
        if cls._requires_city_level_followup(candidate):
            return False
        normalized_actual = cls._normalize_address_text(actual_address)
        compact_candidate = cls._compact_address_text(candidate)
        compact_actual = cls._compact_address_text(actual_address)
        if candidate == normalized_actual or compact_candidate == compact_actual:
            return True
        candidate_components = extract_address_components(candidate)
        if not cls._address_matches_actual(candidate, actual_address):
            return False
        return (
            (candidate_components.has_admin_region or candidate_components.has_locality)
            and cls._address_has_detail_info(candidate)
            and cls._has_required_address_precision(candidate, actual_address)
        )

    @classmethod
    def _address_has_region_info(cls, candidate: str) -> bool:
        components = extract_address_components(candidate)
        return components.has_admin_region and components.has_locality

    @classmethod
    def _address_has_admin_region(cls, candidate: str) -> bool:
        return extract_address_components(candidate).has_admin_region

    @classmethod
    def _address_has_detail_info(cls, candidate: str) -> bool:
        components = extract_address_components(candidate)
        return components.has_locality and (
            components.has_precise_detail or cls._has_nonstandard_address_detail(candidate)
        )

    def _can_start_address_confirmation(
        self,
        *,
        scenario: Scenario,
        candidate: str,
        require_strong_confirmable: bool = False,
    ) -> bool:
        normalized_candidate = self._normalize_address_text(candidate)
        actual_address = scenario.customer.address
        use_precision_reference = self._manual_test_uses_address_precision_reference(scenario)
        if self._is_complete_address(normalized_candidate, actual_address):
            return True
        if self._requires_city_level_followup(candidate):
            return False

        confirmable = (
            self._is_strong_confirmable_address_candidate(candidate)
            if require_strong_confirmable
            else self._is_confirmable_address_candidate(candidate)
        )
        if not confirmable:
            return False

        if self._interactive_test_freeform_enabled(scenario) and not use_precision_reference:
            return self._has_unknown_actual_confirmation_precision(candidate)

        if not self._has_required_address_precision(candidate, actual_address):
            return False

        if self._interactive_test_freeform_enabled(scenario) and not self._has_known_value(actual_address):
            return self._has_unknown_actual_confirmation_precision(candidate)
        return True

    @classmethod
    def _has_unknown_actual_confirmation_precision(cls, candidate: str) -> bool:
        components = extract_address_components(candidate)
        has_region_context = bool(components.has_admin_region or components.town)
        has_confirmation_anchor = cls._address_has_confirmation_anchor(candidate, components)
        if cls._is_rural_address_candidate(candidate):
            if cls._is_rural_landmark_candidate(candidate):
                return bool(
                    (components.has_admin_region or components.town)
                    and (
                        components.community
                        or components.road
                        or components.has_precise_detail
                        or cls._has_nonstandard_address_detail(candidate)
                    )
                )
            return has_region_context and has_confirmation_anchor

        return has_region_context and has_confirmation_anchor

    @classmethod
    def _has_required_address_precision(cls, candidate: str, actual_address: str) -> bool:
        return not cls._missing_required_address_precision(candidate, actual_address)

    @classmethod
    def _missing_required_address_precision(cls, candidate: str, actual_address: str) -> list[str]:
        candidate_components = extract_address_components(candidate)
        actual_components = extract_address_components(actual_address)
        if (
            (candidate_components.has_admin_region or candidate_components.town)
            and cls._address_has_confirmation_anchor(candidate, candidate_components)
        ):
            return []
        has_landmark_anchor = bool(
            candidate_components.city
            and candidate_components.district
            and cls._has_landmark_delivery_detail(candidate)
        )
        if has_landmark_anchor:
            return []
        missing: list[str] = []
        if actual_components.room and not candidate_components.room:
            missing.append("room")
        if actual_components.unit and not candidate_components.unit:
            missing.append("unit")
        if actual_components.building and not candidate_components.building:
            missing.append("building")
        actual_group = cls._extract_village_group_token(actual_address)
        candidate_group = cls._extract_village_group_token(candidate)
        if actual_group and not candidate_group:
            missing.append("village_group")
        if actual_group and candidate_group and not cls._numeric_address_tokens_match(candidate_group, actual_group):
            missing.append("village_group")
        actual_house_number = cls._extract_house_number_token(actual_address)
        candidate_house_number = cls._extract_house_number_token(candidate)
        if actual_house_number and not candidate_house_number:
            missing.append("house_number")
        if (
            actual_house_number
            and candidate_house_number
            and not cls._numeric_address_tokens_match(candidate_house_number, actual_house_number)
        ):
            missing.append("house_number")
        return list(dict.fromkeys(missing))

    @classmethod
    def _canonicalize_merged_address(cls, address: str) -> str:
        canonicalized = canonicalize_address_text(address)
        return canonicalized or address

    @classmethod
    def _address_component_presence_count(cls, components: AddressComponents) -> int:
        return sum(
            1
            for value in (
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
            if value
        )

    @classmethod
    def _merge_address_components_by_level(
        cls,
        *,
        existing: str,
        new: str,
        existing_components: AddressComponents,
        new_components: AddressComponents,
    ) -> str:
        if not existing or not new:
            return ""

        ordered_values: list[str] = []
        merged_count = 0
        existing_count = cls._address_component_presence_count(existing_components)
        new_count = cls._address_component_presence_count(new_components)

        for level in ("province", "city", "district", "town", "road", "community", "building", "unit", "floor", "room"):
            existing_value = getattr(existing_components, level)
            new_value = getattr(new_components, level)
            normalized_existing = cls._normalize_address_text(existing_value)
            normalized_new = cls._normalize_address_text(new_value)
            if normalized_existing and normalized_new and normalized_existing != normalized_new:
                return ""
            merged_value = new_value or existing_value
            if merged_value:
                ordered_values.append(merged_value)
                merged_count += 1

        if merged_count <= max(existing_count, new_count):
            return ""
        return cls._canonicalize_merged_address("".join(ordered_values))

    @classmethod
    def _merge_address_candidate(cls, existing: str, new: str) -> str:
        prepared_existing = cls._prepare_address_for_confirmation(existing)
        prepared_new = cls._prepare_address_for_confirmation(new)
        if not prepared_existing:
            return cls._canonicalize_merged_address(prepared_new)
        if not prepared_new:
            return cls._canonicalize_merged_address(prepared_existing)

        normalized_existing = cls._normalize_address_text(prepared_existing)
        normalized_new = cls._normalize_address_text(prepared_new)
        if normalized_existing in normalized_new:
            return prepared_new
        if normalized_new in normalized_existing:
            return prepared_existing

        existing_components = extract_address_components(prepared_existing)
        new_components = extract_address_components(prepared_new)
        rewritten_prefix = cls._merge_address_with_prefix_rewrite(
            existing=prepared_existing,
            new=prepared_new,
            existing_components=existing_components,
            new_components=new_components,
        )
        if rewritten_prefix:
            return cls._canonicalize_merged_address(rewritten_prefix)
        component_merged = cls._merge_address_components_by_level(
            existing=prepared_existing,
            new=prepared_new,
            existing_components=existing_components,
            new_components=new_components,
        )
        if component_merged:
            return component_merged
        if new_components.has_precise_detail and components_match(new_components, existing_components):
            return cls._canonicalize_merged_address(prepared_existing)

        existing_has_region = cls._address_has_region_info(prepared_existing)
        existing_has_detail = cls._address_has_detail_info(prepared_existing)
        new_has_region = cls._address_has_region_info(prepared_new)
        new_has_detail = cls._address_has_detail_info(prepared_new)
        existing_has_admin_region = cls._address_has_admin_region(prepared_existing)
        new_has_admin_region = cls._address_has_admin_region(prepared_new)
        new_has_nonstandard_detail = cls._has_nonstandard_address_detail(prepared_new)
        existing_admin_prefix = cls._address_admin_region_prefix(prepared_existing)
        existing_has_nonstandard_detail = cls._has_nonstandard_address_detail(prepared_existing)
        existing_region_town_prefix = "".join(
            value
            for value in (
                existing_components.province,
                existing_components.city,
                existing_components.district,
                existing_components.town,
            )
            if value
        )

        if (
            existing_has_admin_region
            and cls._has_landmark_delivery_detail(prepared_new)
            and not new_components.province
            and not new_components.city
            and not new_components.town
            and not new_components.road
            and not new_components.community
        ):
            merged_with_region = f"{existing_region_town_prefix or existing_admin_prefix}{prepared_new}"
            if cls._normalize_address_text(merged_with_region):
                return cls._canonicalize_merged_address(merged_with_region)

        if (
            existing_components.has_locality
            and new_has_nonstandard_detail
            and not new_has_admin_region
            and not new_components.has_locality
        ):
            if existing_has_nonstandard_detail:
                updated = cls._merge_address_detail_replacements(prepared_existing, prepared_new)
                if updated != prepared_existing:
                    return cls._canonicalize_merged_address(updated)
            return cls._canonicalize_merged_address(f"{prepared_existing}{prepared_new}")

        if existing_has_admin_region and not new_has_admin_region and (
            new_components.has_locality or new_has_nonstandard_detail
        ):
            if cls._is_numeric_lane_token(new_components.road):
                locality_prefix = "".join(
                    value
                    for value in (
                        existing_components.province,
                        existing_components.city,
                        existing_components.district,
                        existing_components.town,
                        existing_components.road,
                        existing_components.community,
                    )
                    if value
                )
                if locality_prefix:
                    merged_with_lane = re.sub(r"\s+", "", f"{locality_prefix}{prepared_new}")
                    if cls._normalize_address_text(merged_with_lane):
                        return cls._canonicalize_merged_address(merged_with_lane)
            merged_prefix = cls._address_prefix_before_first_locality(
                existing_components,
                new_components,
            ) or existing_admin_prefix
            merged_with_region = f"{merged_prefix}{prepared_new}"
            if new_components.has_precise_detail and not new_has_nonstandard_detail:
                merged_with_region = re.sub(r"\s+", "", merged_with_region)
            if cls._normalize_address_text(merged_with_region):
                return cls._canonicalize_merged_address(merged_with_region)

        if (
            existing_has_admin_region
            and existing_components.city
            and not existing_components.district
            and new_components.district
            and not new_components.province
            and not new_components.city
            and not new_components.town
            and not new_components.road
            and not new_components.community
            and (
                existing_components.town
                or existing_components.road
                or existing_components.community
                or existing_components.building
                or existing_components.unit
                or existing_components.floor
                or existing_components.room
                or existing_has_nonstandard_detail
            )
        ):
            existing_suffix = prepared_existing
            for token in (
                existing_components.province,
                existing_components.city,
                existing_components.district,
            ):
                if token and existing_suffix.startswith(token):
                    existing_suffix = existing_suffix[len(token) :]
            merged_with_inserted_district = f"{existing_admin_prefix}{prepared_new}{existing_suffix}"
            if cls._normalize_address_text(merged_with_inserted_district):
                return cls._canonicalize_merged_address(merged_with_inserted_district)

        if (
            existing_has_admin_region
            and existing_admin_prefix
            and new_components.district
            and not new_components.province
            and not new_components.city
        ):
            merged_with_region = f"{existing_admin_prefix}{prepared_new}"
            if cls._normalize_address_text(merged_with_region):
                return cls._canonicalize_merged_address(merged_with_region)

        if (
            existing_components.district
            and existing_components.city
            and new_components.city
            and cls._normalize_address_text(new_components.city)
            == cls._normalize_address_text(existing_components.city)
            and not new_components.district
            and not new_components.town
            and not new_components.road
            and not new_components.community
            and new_has_nonstandard_detail
        ):
            trimmed_new = prepared_new
            if trimmed_new.startswith(new_components.city):
                trimmed_new = trimmed_new[len(new_components.city) :]
            merged_with_existing_region = f"{existing_region_town_prefix or existing_admin_prefix}{trimmed_new}"
            if cls._normalize_address_text(merged_with_existing_region):
                return cls._canonicalize_merged_address(merged_with_existing_region)

        if new_has_region and new_has_detail:
            return cls._canonicalize_merged_address(prepared_new)

        if (
            new_has_admin_region
            and not new_has_detail
            and existing_components.district
            and new_components.district
            and cls._normalize_address_text(existing_components.district)
            == cls._normalize_address_text(new_components.district)
            and not existing_components.province
            and not existing_components.city
            and (existing_components.community or existing_components.road or cls._has_nonstandard_address_detail(prepared_existing))
        ):
            existing_suffix = prepared_existing
            if existing_components.district and existing_suffix.startswith(existing_components.district):
                existing_suffix = existing_suffix[len(existing_components.district) :]
            merged_with_completed_region = f"{prepared_new}{existing_suffix}"
            if cls._normalize_address_text(merged_with_completed_region):
                return cls._canonicalize_merged_address(merged_with_completed_region)

        if not new_has_admin_region:
            precise_merged = cls._merge_precise_detail_components(prepared_existing, prepared_new)
            if precise_merged != prepared_existing:
                return cls._canonicalize_merged_address(precise_merged)
            detail_merged = cls._merge_address_detail_replacements(prepared_existing, prepared_new)
            if detail_merged != prepared_existing:
                return cls._canonicalize_merged_address(detail_merged)
            if existing_has_admin_region and existing_components.has_precise_detail and new_components.has_precise_detail:
                return cls._canonicalize_merged_address(prepared_existing)

        if new_has_admin_region and not existing_has_admin_region and existing_has_detail and not new_has_detail:
            return cls._canonicalize_merged_address(f"{prepared_new}{prepared_existing}")
        if (
            new_components.province
            and new_components.city
            and not new_components.district
            and not new_has_detail
            and existing_components.district
            and (
                existing_components.town
                or existing_components.community
                or existing_components.road
                or cls._has_nonstandard_address_detail(prepared_existing)
            )
            and not existing_components.province
            and not existing_components.city
        ):
            return cls._canonicalize_merged_address(f"{prepared_new}{prepared_existing}")
        if existing_has_admin_region and not new_has_admin_region and new_has_detail and not existing_has_detail:
            return cls._canonicalize_merged_address(f"{prepared_existing}{prepared_new}")

        return cls._canonicalize_merged_address(f"{prepared_existing}{prepared_new}")

    @classmethod
    def _merge_address_with_prefix_rewrite(
        cls,
        *,
        existing: str,
        new: str,
        existing_components: AddressComponents,
        new_components: AddressComponents,
    ) -> str:
        if (
            cls._has_landmark_delivery_detail(new)
            and not new_components.province
            and not new_components.city
            and not new_components.town
            and not new_components.road
            and not new_components.community
        ):
            return ""
        conflict_level = cls._address_prefix_conflict_level(existing_components, new_components)
        if not conflict_level:
            return ""

        ordered_levels = ("province", "city", "district", "town", "road", "community")
        conflict_index = ordered_levels.index(conflict_level)
        prefix_levels = ordered_levels[:conflict_index]
        if conflict_level == "city" and new_components.city and not new_components.province:
            prefix_levels = ()
        prefix = "".join(
            (getattr(new_components, level) or getattr(existing_components, level))
            for level in prefix_levels
            if getattr(new_components, level) or getattr(existing_components, level)
        )
        suffix = new
        for level in prefix_levels:
            new_value = getattr(new_components, level)
            if new_value and suffix.startswith(new_value):
                suffix = suffix[len(new_value) :]
        suffix = suffix or new
        return f"{prefix}{suffix}"

    @classmethod
    def _address_prefix_conflict_level(
        cls,
        existing_components: AddressComponents,
        new_components: AddressComponents,
    ) -> str:
        for level in ("province", "city", "district", "town", "road", "community"):
            new_value = getattr(new_components, level)
            existing_value = getattr(existing_components, level)
            new_comp = cls._normalize_address_text(new_value)
            existing_comp = cls._normalize_address_text(existing_value)
            if not new_comp or not existing_comp:
                continue
            if level in {"road", "community"}:
                if new_comp in existing_comp or existing_comp in new_comp:
                    continue
            elif new_comp == existing_comp:
                continue
            return level
        return ""

    @classmethod
    def _should_request_model_province_backfill_for_cross_city_correction(
        cls,
        *,
        confirmation_address: str,
        candidate: str,
    ) -> bool:
        candidate_components = extract_address_components(candidate)
        if candidate_components.province or not candidate_components.city:
            return False
        confirmation_components = extract_address_components(confirmation_address)
        if not confirmation_components.city:
            return False
        return comparable_component("city", candidate_components.city) != comparable_component(
            "city",
            confirmation_components.city,
        )

    @classmethod
    def _should_prefer_model_admin_backfill_candidate(
        cls,
        *,
        rule_candidate: str,
        model_candidate: str,
    ) -> bool:
        rule_components = extract_address_components(rule_candidate)
        model_components = extract_address_components(model_candidate)
        if not (rule_components.city and model_components.province and model_components.city):
            return False
        if comparable_component("city", rule_components.city) != comparable_component(
            "city",
            model_components.city,
        ):
            return False
        if rule_components.district and comparable_component(
            "district",
            rule_components.district,
        ) != comparable_component("district", model_components.district):
            return False
        if rule_components.town and cls._normalize_address_text(rule_components.town) != cls._normalize_address_text(
            model_components.town
        ):
            return False
        return True

    @classmethod
    def _should_prefer_model_denial_candidate(
        cls,
        *,
        rule_candidate: str,
        model_candidate: str,
    ) -> bool:
        rule_components = extract_address_components(rule_candidate)
        model_components = extract_address_components(model_candidate)
        rule_has_admin_region = bool(
            rule_components.province or rule_components.city or rule_components.district or rule_components.town
        )
        model_has_admin_region = bool(
            model_components.province or model_components.city or model_components.district or model_components.town
        )
        if model_has_admin_region and not rule_has_admin_region:
            return True
        if model_components.province and model_components.city and not (rule_components.province and rule_components.city):
            return True
        return False

    @classmethod
    def _address_matches_actual(cls, candidate: str, actual_address: str) -> bool:
        candidate_components = extract_address_components(candidate)
        actual_components = extract_address_components(actual_address)
        if not components_match(candidate_components, actual_components):
            return False

        candidate_group = cls._extract_village_group_token(candidate)
        actual_group = cls._extract_village_group_token(actual_address)
        if candidate_group:
            if not actual_group:
                return False
            if not cls._numeric_address_tokens_match(candidate_group, actual_group):
                return False

        candidate_house_number = cls._extract_house_number_token(candidate)
        actual_house_number = cls._extract_house_number_token(actual_address)
        if candidate_house_number:
            if not actual_house_number:
                return False
            if not cls._numeric_address_tokens_match(candidate_house_number, actual_house_number):
                return False

        return True

    @classmethod
    def _can_use_rule_address_candidate_for_collection(
        cls,
        *,
        candidate: str,
        actual_address: str,
    ) -> bool:
        prepared_candidate = cls._prepare_address_for_confirmation(candidate)
        if not prepared_candidate or not cls._has_known_value(actual_address):
            return False

        components = extract_address_components(prepared_candidate)
        if not (
            components.has_admin_region
            or components.has_locality
            or components.has_precise_detail
            or cls._has_nonstandard_address_detail(prepared_candidate)
        ):
            return False
        if cls._rule_address_candidate_has_unparsed_tail(prepared_candidate):
            return False

        actual_components = extract_address_components(actual_address)
        if not components_match(components, actual_components):
            return False

        candidate_group = cls._extract_village_group_token(prepared_candidate)
        actual_group = cls._extract_village_group_token(actual_address)
        if candidate_group and (
            not actual_group or not cls._numeric_address_tokens_match(candidate_group, actual_group)
        ):
            return False

        candidate_house_number = cls._extract_house_number_token(prepared_candidate)
        actual_house_number = cls._extract_house_number_token(actual_address)
        if candidate_house_number and (
            not actual_house_number
            or not cls._numeric_address_tokens_match(candidate_house_number, actual_house_number)
        ):
            return False

        return True

    @classmethod
    def _rule_address_candidate_has_unparsed_tail(cls, candidate: str) -> bool:
        normalized = cls._normalize_address_text(candidate)
        if not normalized:
            return False

        components = extract_address_components(candidate)
        recognized_tokens = [
            token
            for token in (
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
                cls._extract_village_group_token(candidate),
                cls._extract_house_number_token(candidate),
            )
            if token
        ]
        remainder = normalized
        for token in sorted(recognized_tokens, key=len, reverse=True):
            normalized_token = cls._normalize_address_text(token)
            if normalized_token:
                remainder = remainder.replace(normalized_token, "", 1)
        remainder = remainder.strip()
        if not remainder:
            return False
        return bool(re.search(r"[\u4e00-\u9fa5A-Za-z0-9]", remainder))

    def _infer_address_candidate_with_callback(
        self,
        *,
        user_text: str,
        confirmation_address: str,
        partial_address_candidate: str,
        last_address_followup_prompt: str,
        dialogue_history: str = "",
    ) -> str:
        if self.address_inference_callback is None:
            return ""
        try:
            payload = self.address_inference_callback(
                user_text=user_text,
                confirmation_address=confirmation_address,
                partial_address_candidate=partial_address_candidate,
                last_address_followup_prompt=last_address_followup_prompt,
                dialogue_history=dialogue_history,
            )
        except Exception:
            return ""
        if not isinstance(payload, dict):
            return ""

        merged_candidate = self._prepare_address_for_confirmation(
            str(payload.get("merged_address_candidate", "")).strip()
        )
        candidate = merged_candidate or self._prepare_address_for_confirmation(
            str(payload.get("address_candidate", "")).strip()
        )
        if not candidate:
            return ""
        if self._is_model_address_overreach(
            user_text=user_text,
            partial_address_candidate=partial_address_candidate,
            candidate=candidate,
        ):
            return ""

        components = extract_address_components(candidate)
        granularity = str(payload.get("granularity", "")).strip().lower()
        if granularity in {"none", "non_address"}:
            return ""
        has_partial_admin_region = bool(
            components.province or components.city or components.district or components.town
        )
        if not (
            components.has_admin_region
            or has_partial_admin_region
            or components.has_locality
            or components.has_precise_detail
            or self._has_nonstandard_address_detail(candidate)
        ):
            return ""
        if (
            confirmation_address
            and self._normalize_address_text(candidate)
            == self._normalize_address_text(confirmation_address)
        ):
            return ""
        self.last_used_model_intent_inference = True
        return candidate

    @classmethod
    def _address_user_accepts_current_candidate(cls, text: str) -> bool:
        patterns = (
            r"^(直接)?这(?:个|里|地方)(就)?行了?$",
            r"^(直接)?那(?:个|里|地方)(就)?行了?$",
            r"^(就|按)(这(?:个|里|地方)|刚才那个)(地址|地方)?(就)?行了?$",
            r"^(就|按)那(?:个|里|地方)(地址|地方)?(就)?行了?$",
            r"^(就写)?前面(?:说的|那个)(地址|地方)?(就)?行了?$",
            r"^(直接)?按前面(?:那个|说的)(地址|地方)?(就)?行了?$",
            r"^(就这个地址|就这里|就这个地方)$",
            r"^我说完了(?:啊|呀|哈)?$",
            r"^(我)?说了(?:啊|呀|哈)?$",
            r"^(我)?都说了(?:啊|呀|哈)?$",
            r"^(我)?已经说了(?:啊|呀|哈)?$",
            r"^(我)?都提供了(?:啊|呀|哈)?$",
            r"^(我)?已经提供了(?:啊|呀|哈)?$",
            r"^(?:啥|怎么)?(?:我)?已经(?:提供|说)了(?:啊|呀|哈)?$",
            r"^(前面|刚才)不是说了(?:吗|嘛)?$",
            r"^(就)?到这(?:里)?(?:就)?行了?$",
            r"^(就)?到那(?:里)?(?:就)?行了?$",
            r"^(我)?只能(?:提供|说)到这(?:里)?了?$",
            r"^(我)?只能(?:提供|说)到那(?:里)?了?$",
            r"^(就)?只能到这(?:里)?了?$",
            r"^(就)?只能到那(?:里)?了?$",
        )
        clauses = [
            cls._normalize_address_text(clause)
            for clause in re.split(r"[，,。！？!?；;、]", str(text or ""))
            if cls._normalize_address_text(clause)
        ]
        return any(
            re.fullmatch(pattern, clause)
            for clause in clauses
            for pattern in patterns
        )

    def _classify_address_collection_acceptance_with_model(
        self,
        *,
        user_text: str,
        partial_address_candidate: str,
        last_address_followup_prompt: str,
        dialogue_history: str = "",
    ) -> str | None:
        if self.address_collection_acceptance_inference_callback is None:
            return None
        try:
            payload = self._invoke_inference_callback(
                self.address_collection_acceptance_inference_callback,
                user_text=user_text,
                partial_address_candidate=partial_address_candidate,
                last_address_followup_prompt=last_address_followup_prompt,
                dialogue_history=dialogue_history,
            )
        except Exception:
            return None
        if not isinstance(payload, dict):
            return None
        intent = str(payload.get("intent", "")).strip().lower()
        if intent in {"yes", "no"}:
            self.last_used_model_intent_inference = True
            return intent
        return None

    def _address_user_accepts_current_candidate_or_signals_stop(
        self,
        *,
        user_text: str,
        partial_address_candidate: str,
        last_address_followup_prompt: str,
        dialogue_history: str = "",
    ) -> bool:
        model_intent = self._classify_address_collection_acceptance_with_model(
            user_text=user_text,
            partial_address_candidate=partial_address_candidate,
            last_address_followup_prompt=last_address_followup_prompt,
            dialogue_history=dialogue_history,
        )
        if model_intent == "yes":
            return True
        if model_intent == "no":
            return False
        return self._address_user_accepts_current_candidate(user_text)

    @classmethod
    def _address_user_signals_reask_frustration(cls, text: str) -> bool:
        patterns = (
            r"^(怎么还是这(?:个)?问题|怎么还在问这个)$",
            r"^(不是说了(?:吗|嘛)?|前面不是说了(?:吗|嘛)?)$",
            r"^(还要我说几遍|还问什么)$",
            r"^(我)?都(?:提供|说)了(?:啊|呀|哈)?$",
            r"^(我)?已经(?:提供|说)了(?:啊|呀|哈)?$",
            r"^(?:啥|怎么)?(?:我)?已经(?:提供|说)了(?:啊|呀|哈)?$",
        )
        clauses = [
            cls._normalize_address_text(clause)
            for clause in re.split(r"[，,。！？!?；;、]", str(text or ""))
            if cls._normalize_address_text(clause)
        ]
        return any(
            re.fullmatch(pattern, clause)
            for clause in clauses
            for pattern in patterns
        )

    @staticmethod
    def _dialogue_history_text(transcript: list[DialogueTurn], *, max_turns: int = 8) -> str:
        recent_turns = transcript[-max_turns:]
        lines = [
            f"[{turn.round_index}] {display_speaker(turn.speaker)}: {turn.text}"
            for turn in recent_turns
        ]
        return "\n".join(lines)

    @classmethod
    def _address_admin_region_prefix(cls, address: str) -> str:
        components = extract_address_components(address)
        return "".join(
            value
            for value in (components.province, components.city, components.district, components.town)
            if value
        )

    @classmethod
    def _address_prefix_before_first_locality(
        cls,
        existing_components: AddressComponents,
        new_components: AddressComponents,
    ) -> str:
        ordered_levels = ("province", "city", "district", "town", "road", "community")
        first_new_level_index = next(
            (
                index
                for index, level in enumerate(ordered_levels)
                if getattr(new_components, level)
            ),
            len(ordered_levels),
        )
        return "".join(
            getattr(existing_components, level)
            for level in ordered_levels[:first_new_level_index]
            if getattr(existing_components, level)
        )

    @classmethod
    def _extract_village_group_token(cls, address: str) -> str:
        normalized = cls._normalize_address_text(address)
        match = re.search(r"([零一二三四五六七八九十两\d]+(?:组|社|队))", normalized)
        return match.group(1) if match else ""

    @classmethod
    def _is_numeric_lane_token(cls, token: str) -> bool:
        return bool(re.fullmatch(r"[零一二三四五六七八九十两\d]+弄", cls._normalize_address_text(token)))

    @classmethod
    def _extract_house_number_token(cls, address: str) -> str:
        normalized = cls._normalize_address_text(address)
        if not normalized:
            return ""

        road_token = cls._normalize_address_text(extract_address_components(address).road)
        matches = list(re.finditer(r"([零一二三四五六七八九十两\d]+号)(?!楼|栋|幢|座|单元|层|室)", normalized))
        for match in reversed(matches):
            token = match.group(1)
            if road_token and token in road_token:
                continue
            return token
        return ""

    @classmethod
    def _has_landmark_delivery_detail(cls, address: str) -> bool:
        normalized = cls._normalize_address_text(address)
        if not normalized:
            return False
        landmark_suffix_pattern = "|".join(
            re.escape(suffix)
            for suffix in sorted(LANDMARK_LOCALITY_SUFFIXES, key=len, reverse=True)
        )
        patterns = (
            r"[A-Za-z]?\d+(?:号|栋|座|区)?(?:外卖柜|快递柜|取餐柜)",
            r"(?:外卖柜|快递柜|取餐柜|驿站|代收点|前台|服务台|门岗|保安亭|岗亭|收发室)",
            rf"(?:{landmark_suffix_pattern})",
        )
        return any(re.search(pattern, normalized, flags=re.IGNORECASE) for pattern in patterns)

    @classmethod
    def _has_nonstandard_address_detail(cls, address: str) -> bool:
        return bool(
            cls._extract_village_group_token(address)
            or cls._extract_house_number_token(address)
            or cls._has_landmark_delivery_detail(address)
        )

    @classmethod
    def _is_rural_landmark_candidate(cls, candidate: str) -> bool:
        components = extract_address_components(candidate)
        return bool(
            cls._is_rural_address_candidate(candidate)
            and cls._has_landmark_delivery_detail(candidate)
            and (components.community or components.road)
        )

    @classmethod
    def _is_confirmable_address_candidate(cls, candidate: str) -> bool:
        components = extract_address_components(candidate)
        has_region_context = bool(components.has_admin_region or components.town)
        has_confirmation_anchor = cls._address_has_confirmation_anchor(candidate, components)
        if cls._is_rural_address_candidate(candidate):
            if cls._is_rural_landmark_candidate(candidate):
                return bool(
                    (components.has_admin_region or components.town)
                    and (
                        components.community
                        or components.road
                        or components.has_precise_detail
                        or cls._has_nonstandard_address_detail(candidate)
                    )
                )
            return has_region_context and has_confirmation_anchor
        has_anchor_detail = bool(
            components.road
            or components.community
            or components.has_precise_detail
            or cls._has_nonstandard_address_detail(candidate)
        )
        return has_region_context and has_anchor_detail

    @classmethod
    def _is_strong_confirmable_address_candidate(cls, candidate: str) -> bool:
        components = extract_address_components(candidate)
        has_region_context = bool(components.has_admin_region or components.town)
        has_confirmation_anchor = cls._address_has_confirmation_anchor(candidate, components)
        if cls._is_rural_address_candidate(candidate):
            if cls._is_rural_landmark_candidate(candidate):
                return bool(
                    (components.has_admin_region or components.town)
                    and (
                        components.community
                        or components.road
                        or components.has_precise_detail
                        or cls._has_nonstandard_address_detail(candidate)
                    )
                )
            return has_region_context and has_confirmation_anchor
        has_house_number = bool(cls._extract_house_number_token(candidate))
        has_room = bool(components.room)
        has_building_anchor = bool(components.building and (components.community or components.road))
        has_nonstandard_detail = bool(cls._has_nonstandard_address_detail(candidate))
        return has_region_context and (
            has_house_number or has_room or has_building_anchor or has_nonstandard_detail
        )

    @classmethod
    def _is_model_address_overreach(
        cls,
        *,
        user_text: str,
        partial_address_candidate: str,
        candidate: str,
    ) -> bool:
        generic_non_address_patterns = (
            r"前面.*(?:小区|地址|地方).*(?:错|不对)",
            r"后面.*(?:小区|地址|地方).*(?:错|不对)",
            r"老家那个地址",
            r"那个地址",
            r"(?:换一个|换个)(?:地址|地方)?",
            r"(?:留个|记个|登记个)(?:新)?地址",
        )
        if any(re.search(pattern, user_text or "") for pattern in generic_non_address_patterns):
            return False

        observed_candidate = cls._merge_address_candidate(
            partial_address_candidate,
            cls._prepare_address_for_confirmation(user_text),
        )
        if not observed_candidate:
            return False

        partial_components = extract_address_components(partial_address_candidate)
        candidate_components = extract_address_components(candidate)
        user_components = extract_address_components(cls._prepare_address_for_confirmation(user_text))
        if partial_address_candidate and not (
            user_components.province or user_components.city or user_components.district
        ):
            for level in ("province", "city", "district"):
                partial_value = getattr(partial_components, level)
                candidate_value = getattr(candidate_components, level)
                if (
                    partial_value
                    and cls._normalize_address_text(candidate_value)
                    != cls._normalize_address_text(partial_value)
                ):
                    return True

        observed_components = extract_address_components(observed_candidate)
        if not (
            observed_components.has_admin_region
            or observed_components.town
            or observed_components.has_precise_detail
            or cls._has_nonstandard_address_detail(observed_candidate)
        ):
            return False
        observed_has_site_locality = bool(observed_components.road or observed_components.community)
        observed_has_detail = bool(
            observed_components.has_precise_detail or cls._has_nonstandard_address_detail(observed_candidate)
        )
        candidate_has_site_locality = bool(candidate_components.road or candidate_components.community)
        candidate_has_detail = bool(
            candidate_components.has_precise_detail or cls._has_nonstandard_address_detail(candidate)
        )

        if (
            (observed_components.has_admin_region or observed_components.town)
            and not observed_has_site_locality
            and not observed_has_detail
            and (candidate_has_site_locality or candidate_has_detail)
        ):
            return True
        if (
            observed_components.district
            and not observed_components.city
            and not observed_components.province
            and (
                candidate_components.city
                or candidate_components.province
            )
        ):
            return True
        if (
            observed_components.city
            and not observed_components.province
            and not observed_components.district
            and not observed_has_site_locality
            and not observed_has_detail
            and candidate_components.city
            and comparable_component("city", candidate_components.city)
            != comparable_component("city", observed_components.city)
        ):
            return True
        if observed_has_site_locality and not observed_has_detail and candidate_has_detail:
            return True
        return False

    @classmethod
    def _should_prefer_address_candidate(cls, *, current: str, candidate: str) -> bool:
        current_components = extract_address_components(current)
        candidate_components = extract_address_components(candidate)

        if candidate_components.community and not current_components.community:
            return True
        if candidate_components.road and not current_components.road:
            return True

        current_has_site_locality = bool(current_components.road or current_components.community)
        candidate_has_site_locality = bool(candidate_components.road or candidate_components.community)
        if candidate_has_site_locality and not current_has_site_locality:
            return True

        if candidate_components.building and not current_components.building:
            return True
        if candidate_components.unit and not current_components.unit:
            return True
        if candidate_components.room and not current_components.room:
            return True
        if candidate_components.floor and not current_components.floor:
            return True

        if cls._extract_house_number_token(candidate) and not cls._extract_house_number_token(current):
            return True
        if cls._extract_village_group_token(candidate) and not cls._extract_village_group_token(current):
            return True

        return False

    @classmethod
    def _should_backfill_address_with_model(cls, *, current: str, actual_address: str) -> bool:
        current_components = extract_address_components(current)
        has_precise_detail = bool(
            current_components.building
            or current_components.unit
            or current_components.floor
            or current_components.room
            or cls._extract_house_number_token(current)
            or cls._extract_village_group_token(current)
        )
        if not has_precise_detail:
            return False

        actual_components = extract_address_components(actual_address)
        for field in ("town", "road", "community"):
            actual_value = getattr(actual_components, field)
            current_value = getattr(current_components, field)
            if actual_value and not current_value:
                return True

        return False

    @classmethod
    def _numeric_address_token_value(cls, token: str) -> str:
        normalized = cls._normalize_address_text(token)
        match = re.search(r"[零一二三四五六七八九十两\d]+", normalized)
        if not match:
            return normalized
        number_text = match.group(0)
        if number_text.isdigit():
            return number_text

        mapping = {
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
        if number_text == "十":
            return "10"
        if "十" in number_text:
            left, _, right = number_text.partition("十")
            tens = mapping.get(left, 1 if left == "" else -1)
            units = mapping.get(right, 0 if right == "" else -1)
            if tens >= 0 and units >= 0:
                return str(tens * 10 + units)
        digits: list[str] = []
        for char in number_text:
            if char not in mapping:
                return number_text
            digits.append(str(mapping[char]))
        return "".join(digits)

    @classmethod
    def _numeric_address_tokens_match(cls, left: str, right: str) -> bool:
        return cls._numeric_address_token_value(left) == cls._numeric_address_token_value(right)

    @classmethod
    def _merge_address_detail_replacements(cls, existing: str, new: str) -> str:
        merged = existing
        replaced = False
        detail_patterns = (
            r"\d+\s*室",
            r"\d+\s*单元",
            r"[A-Za-z零一二三四五六七八九十两\d]+\s*(?:号楼|栋|幢|座|楼)",
            r"\d+\s*号",
        )
        for pattern in detail_patterns:
            new_match = re.search(pattern, new)
            existing_match = re.search(pattern, merged)
            if not new_match or not existing_match:
                continue
            if cls._normalize_address_text(new_match.group(0)) == cls._normalize_address_text(existing_match.group(0)):
                continue
            merged = (
                merged[: existing_match.start()]
                + new_match.group(0)
                + merged[existing_match.end() :]
            )
            replaced = True
        return merged if replaced else existing

    @classmethod
    def _merge_precise_detail_components(cls, existing: str, new: str) -> str:
        existing_components = extract_address_components(existing)
        new_components = extract_address_components(new)
        if not new_components.has_precise_detail:
            return existing

        merged = existing
        if new_components.road and not existing_components.road:
            normalized_road = cls._normalize_address_text(new_components.road)
            normalized_merged = cls._normalize_address_text(merged)
            if normalized_road and normalized_road not in normalized_merged:
                detail_anchor_pattern = (
                    r"[A-Za-z零一二三四五六七八九十两\d]+\s*(?:"
                    + "|".join(re.escape(suffix) for suffix in BUILDING_SUFFIXES)
                    + r")|\d+\s*单元|[零一二三四五六七八九十两\d]+\s*层|\d{2,4}\s*室"
                )
                insertion_match = re.search(detail_anchor_pattern, merged)
                if insertion_match:
                    merged = (
                        merged[: insertion_match.start()]
                        + new_components.road
                        + merged[insertion_match.start() :]
                    )
                else:
                    merged = f"{merged}{new_components.road}"
        replacements = (
            ("building", existing_components.building, new_components.building, r"[A-Za-z零一二三四五六七八九十两\d]+\s*(?:号楼|栋|幢|座|楼)"),
            ("unit", existing_components.unit, new_components.unit, r"\d+\s*单元"),
            ("floor", existing_components.floor, new_components.floor, r"[零一二三四五六七八九十两\d]+\s*层"),
            ("room", existing_components.room, new_components.room, r"\d{2,4}\s*室"),
        )
        changed = False
        for _, existing_value, new_value, pattern in replacements:
            if not new_value:
                continue
            if existing_value:
                if cls._normalize_address_text(existing_value) == cls._normalize_address_text(new_value):
                    continue
                merged = re.sub(pattern, new_value, merged, count=1)
                changed = True
                continue
            merged = f"{merged}{new_value}"
            changed = True
        return merged if changed else existing

    @classmethod
    def _is_detail_only_confirmation_mismatch(
        cls,
        *,
        confirmation_address: str,
        actual_address: str,
    ) -> bool:
        confirmation = extract_address_components(confirmation_address)
        actual = extract_address_components(actual_address)
        prefix_matches = cls._address_prefix_without_precise_detail(
            confirmation_address
        ) == cls._address_prefix_without_precise_detail(actual_address)
        locality_matches = (
            confirmation.province == actual.province
            and confirmation.city == actual.city
            and confirmation.district == actual.district
            and confirmation.town == actual.town
            and confirmation.road == actual.road
            and confirmation.community == actual.community
        )
        if not prefix_matches and not locality_matches:
            return False
        return (
            confirmation.building != actual.building
            or confirmation.unit != actual.unit
            or confirmation.floor != actual.floor
            or confirmation.room != actual.room
        )

    @classmethod
    def _address_prefix_without_precise_detail(cls, address: str) -> str:
        value = str(address or "").strip()
        if not value:
            return ""
        patterns = (
            r"\d+\s*室.*$",
            r"\d+\s*单元.*$",
            r"\d+\s*层.*$",
            r"[A-Za-z零一二三四五六七八九十两\d]+\s*(?:号楼|栋|幢|座|楼).*$",
        )
        for pattern in patterns:
            stripped = re.sub(pattern, "", value)
            if stripped != value:
                return cls._normalize_address_text(stripped)
        return cls._normalize_address_text(value)

    @classmethod
    def _address_followup_kind(cls, candidate: str) -> str:
        components = extract_address_components(candidate)
        if (components.city or components.province) and not components.district:
            return "district"
        if components.district and not components.has_locality:
            return "locality"
        if components.has_locality and not components.has_precise_detail:
            return "building"
        if components.has_precise_detail and not components.has_locality:
            return "locality"
        return "full"

    @staticmethod
    def _normalize_prompt_text(text: str) -> str:
        normalized = (text or "").strip()
        normalized = re.sub(r"^好的[，,\s]*", "", normalized)
        return normalized.rstrip("。！？!?")

    @staticmethod
    def _resolve_prompt_variants(prompt_config: str | PromptConfig) -> tuple[list[str], list[float]]:
        if isinstance(prompt_config, str):
            return [prompt_config], [1.0]

        texts: list[str] = []
        weights: list[float] = []
        for variant in prompt_config:
            if isinstance(variant, str):
                texts.append(variant)
                weights.append(1.0)
                continue

            text, weight = variant
            texts.append(text)
            weights.append(max(0.0, float(weight)))

        if not texts:
            raise ValueError("Prompt variants must not be empty.")
        if sum(weights) <= 0:
            weights = [1.0] * len(texts)
        return texts, weights

    @classmethod
    def _prompt_signatures(cls, prompt_config: str | PromptConfig) -> set[str]:
        texts, _ = cls._resolve_prompt_variants(prompt_config)
        return {cls._normalize_prompt_text(text) for text in texts if text.strip()}

    @classmethod
    def _signature_matches_prompt(cls, signature: str, prompt_config: str | PromptConfig) -> bool:
        normalized_signature = cls._normalize_prompt_text(signature)
        signatures = cls._prompt_signatures(prompt_config)
        return normalized_signature in signatures or any(
            normalized_signature.endswith(expected_signature)
            for expected_signature in signatures
        )

    @classmethod
    def summarize_prompt_variants(
        cls,
        prompt_config: str | PromptConfig,
        *,
        limit: int = 3,
        **format_kwargs: str,
    ) -> str:
        texts, _ = cls._resolve_prompt_variants(prompt_config)
        rendered_texts = [
            text.format(**format_kwargs) if format_kwargs else text for text in texts[: max(1, limit)]
        ]
        return "、".join(f"“{text}”" for text in rendered_texts if text)

    @classmethod
    def summarize_prompt_variants(
        cls,
        prompt_config: str | PromptConfig,
        *,
        limit: int = 3,
        **format_kwargs: str,
    ) -> str:
        texts, _ = cls._resolve_prompt_variants(prompt_config)
        rendered_texts = [
            text.format(**format_kwargs) if format_kwargs else text for text in texts[: max(1, limit)]
        ]
        return " / ".join(f'"{text}"' for text in rendered_texts if text)

    @classmethod
    def is_phone_keypad_prompt(cls, text: str) -> bool:
        normalized = cls._normalize_prompt_text(text)
        return normalized in cls._prompt_signatures(cls.PHONE_KEYPAD_PROMPT) or normalized in cls._prompt_signatures(
            cls.PHONE_KEYPAD_RETRY_PROMPT
        )

    @classmethod
    def is_address_collection_prompt(cls, text: str) -> bool:
        normalized = cls._normalize_prompt_text(text)
        return (
            normalized in cls._prompt_signatures(cls.ADDRESS_PROMPT)
            or normalized in cls._prompt_signatures(cls.ADDRESS_RECOLLECTION_PROMPT)
            or normalized.startswith("好的，您是在")
            or normalized.startswith("请问是")
            or normalized in cls._prompt_signatures(cls.ADDRESS_PROVINCE_CITY_FOLLOWUP_PROMPT)
            or normalized in cls._prompt_signatures(cls.ADDRESS_FULL_REGION_FOLLOWUP_PROMPT)
            or normalized in cls._prompt_signatures(cls.ADDRESS_CITY_DISTRICT_ONLY_FOLLOWUP_PROMPT)
            or normalized in cls._prompt_signatures(cls.ADDRESS_CITY_DISTRICT_INFO_FOLLOWUP_PROMPT)
            or normalized in cls._prompt_signatures(cls.ADDRESS_CITY_DISTRICT_TOWN_TEMPLATE)
            or normalized in cls._prompt_signatures(cls.ADDRESS_FULL_REGION_COMPACT_FOLLOWUP_PROMPT)
            or normalized in cls._prompt_signatures(cls.ADDRESS_REGION_STREET_FOLLOWUP_PROMPT)
            or normalized in cls._prompt_signatures(cls.ADDRESS_DISTRICT_STREET_FOLLOWUP_PROMPT)
            or normalized in cls._prompt_signatures(cls.ADDRESS_LOCALITY_FOLLOWUP_PROMPT)
            or normalized in cls._prompt_signatures(cls.ADDRESS_LOCALITY_WHICH_FOLLOWUP_PROMPT)
            or normalized in cls._prompt_signatures(cls.ADDRESS_RURAL_DETAIL_FOLLOWUP_PROMPT)
            or normalized.startswith("好的，请问您是在哪个省哪个市呢")
            or normalized.startswith("好的，还请您说一下完整的省、市、区")
            or normalized.startswith("好的，麻烦您再补充一下是在哪个市和哪个区县呢")
            or normalized.startswith("好的，麻烦您再补充一下城市和区县信息")
            or normalized.startswith("请您说一下完整的省市区信息")
            or normalized.startswith("好的，请您说一下省、市、区和街道")
            or normalized.startswith("好的，请您继续说一下区和街道")
            or normalized.startswith("请问具体是在哪个小区或村呢？尽量详细到门牌号")
            or normalized.startswith("请问是在哪个小区或哪个村呢？尽量详细到门牌号")
            or normalized.startswith("好的，请您继续说一下小区、楼栋和门牌号")
            or normalized.startswith("好的，请您提供一下详细的地址")
        )

    @classmethod
    def is_phone_confirmation_prompt(cls, text: str) -> bool:
        normalized = cls._normalize_prompt_text(text)
        return normalized.startswith("号码是") and "对吗" in normalized

    @classmethod
    def is_address_confirmation_prompt(cls, text: str) -> bool:
        normalized = cls._normalize_prompt_text(text)
        return (
            (normalized.startswith("跟您确认一下，地址是") and "对吗" in normalized)
            or (normalized.startswith("您的地址是") and "对吗" in normalized)
        )

    @classmethod
    def is_surname_prompt(cls, text: str) -> bool:
        return cls._signature_matches_prompt(text, cls.SURNAME_PROMPT)

    @classmethod
    def is_contactable_prompt(cls, text: str) -> bool:
        return cls._signature_matches_prompt(text, cls.CONTACTABLE_PROMPT)

    @classmethod
    def is_product_arrival_prompt(cls, text: str) -> bool:
        normalized = cls._normalize_prompt_text(text)
        return normalized.startswith("请问") and normalized.endswith("已经送到了吗")

    @classmethod
    def is_product_model_prompt(cls, text: str) -> bool:
        return cls._signature_matches_prompt(text, cls.PRODUCT_MODEL_PROMPT)

    @classmethod
    def is_closing_notice_prompt(cls, text: str) -> bool:
        normalized = cls._normalize_prompt_text(text)
        return normalized.startswith("您的工单已受理成功")

    @classmethod
    def is_satisfaction_prompt(cls, text: str) -> bool:
        normalized = cls._normalize_prompt_text(text)
        return "对本次通话服务打分" in normalized and "1、非常满意" in normalized

    def _choose_prompt_text(self, prompt_config: str | PromptConfig, **format_kwargs: str) -> str:
        texts, weights = self._resolve_prompt_variants(prompt_config)
        selected = self.rng.choices(texts, weights=weights, k=1)[0]
        return selected.format(**format_kwargs) if format_kwargs else selected

    def _with_optional_ok_prefix(self, text: str) -> str:
        normalized = text.strip()
        if not normalized or normalized.startswith("好的"):
            return normalized
        if self.rng.random() < self.ok_prefix_probability:
            return f"好的，{normalized}"
        return normalized

    def _surname_prompt(self) -> str:
        return self._with_optional_ok_prefix(self._choose_prompt_text(self.SURNAME_PROMPT))

    def _contactable_prompt(self) -> str:
        return self._choose_prompt_text(self.CONTACTABLE_PROMPT)

    def _phone_keypad_prompt(self) -> str:
        return self._with_optional_ok_prefix(self._choose_prompt_text(self.PHONE_KEYPAD_PROMPT))

    def _phone_keypad_retry_prompt(self) -> str:
        return self._choose_prompt_text(self.PHONE_KEYPAD_RETRY_PROMPT)

    def _phone_confirmation_prompt(self, phone: str) -> str:
        return self._with_optional_ok_prefix(self._choose_prompt_text(self.PHONE_CONFIRMATION_TEMPLATE, phone=phone))

    @staticmethod
    def _format_prompt_config(prompt_config: PromptConfig, **format_kwargs: str) -> PromptConfig:
        formatted: PromptConfig = []
        for variant in prompt_config:
            if isinstance(variant, str):
                formatted.append(variant.format(**format_kwargs))
                continue
            text, weight = variant
            formatted.append((text.format(**format_kwargs), weight))
        return formatted

    @staticmethod
    def _product_name(scenario: Scenario) -> str:
        value = str(scenario.product.category).strip()
        return value or "空气能热水机"

    def _fault_issue_prompt(self, scenario: Scenario) -> str:
        prompt_config = self._format_prompt_config(self.FAULT_ISSUE_PROMPT, product=self._product_name(scenario))
        return self._with_optional_ok_prefix(self._choose_prompt_text(prompt_config))

    def _address_prompt(self) -> str:
        return self._with_optional_ok_prefix(self._choose_prompt_text(self.ADDRESS_PROMPT))

    def _address_city_district_followup_prompt(self, city: str) -> str:
        prompt_config = self._format_prompt_config(
            self.ADDRESS_CITY_DISTRICT_FOLLOWUP_TEMPLATE,
            city=city,
        )
        return self._choose_prompt_text(prompt_config)

    def _address_province_city_followup_prompt(self) -> str:
        return self._choose_prompt_text(self.ADDRESS_PROVINCE_CITY_FOLLOWUP_PROMPT)

    def _address_full_region_followup_prompt(self) -> str:
        return self._choose_prompt_text(self.ADDRESS_FULL_REGION_FOLLOWUP_PROMPT)

    def _address_city_district_only_followup_prompt(self) -> str:
        return self._choose_prompt_text(self.ADDRESS_CITY_DISTRICT_ONLY_FOLLOWUP_PROMPT)

    def _address_city_district_info_followup_prompt(self) -> str:
        return self._choose_prompt_text(self.ADDRESS_CITY_DISTRICT_INFO_FOLLOWUP_PROMPT)

    def _address_city_district_town_followup_prompt(self, city: str) -> str:
        prompt_config = self._format_prompt_config(
            self.ADDRESS_CITY_DISTRICT_TOWN_TEMPLATE,
            city=city,
        )
        return self._choose_prompt_text(prompt_config)

    def _address_full_region_compact_followup_prompt(self) -> str:
        return self._choose_prompt_text(self.ADDRESS_FULL_REGION_COMPACT_FOLLOWUP_PROMPT)

    def _address_province_city_district_street_followup_prompt(self, province: str) -> str:
        prompt_config = self._format_prompt_config(
            self.ADDRESS_PROVINCE_CITY_DISTRICT_STREET_FOLLOWUP_TEMPLATE,
            province=province,
        )
        return self._choose_prompt_text(prompt_config)

    def _address_region_street_followup_prompt(self) -> str:
        return self._choose_prompt_text(self.ADDRESS_REGION_STREET_FOLLOWUP_PROMPT)

    def _address_district_street_followup_prompt(self) -> str:
        return self._choose_prompt_text(self.ADDRESS_DISTRICT_STREET_FOLLOWUP_PROMPT)

    def _address_locality_followup_prompt(self) -> str:
        return self._choose_prompt_text(self.ADDRESS_LOCALITY_FOLLOWUP_PROMPT)

    def _address_locality_which_followup_prompt(self) -> str:
        return self._choose_prompt_text(self.ADDRESS_LOCALITY_WHICH_FOLLOWUP_PROMPT)

    def _address_rural_detail_followup_prompt(self) -> str:
        return self._choose_prompt_text(self.ADDRESS_RURAL_DETAIL_FOLLOWUP_PROMPT)

    @staticmethod
    def _address_has_site_locality(components: AddressComponents) -> bool:
        return bool(components.road or components.community)

    @classmethod
    def _address_has_confirmation_anchor(
        cls,
        candidate: str,
        components: AddressComponents | None = None,
    ) -> bool:
        components = components or extract_address_components(candidate)
        return bool(
            components.community
            or components.has_precise_detail
            or cls._extract_village_group_token(candidate)
            or cls._has_landmark_delivery_detail(candidate)
        )

    @classmethod
    def _requires_city_level_followup(cls, candidate: str) -> bool:
        components = extract_address_components(candidate)
        return bool(
            candidate
            and not components.city
            and (
                components.district
                or components.has_locality
                or components.has_precise_detail
                or cls._has_nonstandard_address_detail(candidate)
            )
        )

    @staticmethod
    def _is_county_district(district: str) -> bool:
        normalized = normalize_address_text(district)
        return normalized.endswith("县")

    @staticmethod
    def _is_noncounty_district(district: str) -> bool:
        normalized = normalize_address_text(district)
        return bool(normalized) and normalized.endswith("区") and not normalized.endswith("县")

    @classmethod
    def _should_use_locality_which_followup(
        cls,
        candidate: str,
        components: AddressComponents | None = None,
    ) -> bool:
        components = components or extract_address_components(candidate)
        if cls._address_has_confirmation_anchor(candidate, components):
            return False

        normalized_candidate = cls._normalize_address_text(candidate)
        has_province = bool(components.province)
        has_city = bool(components.city)
        has_district = bool(components.district)
        has_town = bool(components.town)
        has_road = bool(components.road)

        district_is_county = cls._is_county_district(components.district)
        province_only_remainder = normalized_candidate
        if has_province:
            normalized_province = cls._normalize_address_text(components.province)
            if normalized_province and normalized_candidate.startswith(normalized_province):
                province_only_remainder = normalized_candidate[len(normalized_province) :]
        matches_province_plus_district_only = bool(
            has_province
            and not has_town
            and not has_road
            and re.fullmatch(r"[\u4e00-\u9fa5]{1,24}(?:(?<!小)区|县|旗)", province_only_remainder)
        )

        return bool(
            matches_province_plus_district_only
            or (has_province and has_district and not has_city and not has_town and not has_road)
            or (has_city and has_town and not has_province and not has_district and not has_road)
            or (has_district and district_is_county and not has_province and not has_city and not has_town and not has_road)
            or (has_district and district_is_county and has_town and not has_province and not has_city and not has_road)
        )

    def _address_special_followup_prompt(self, candidate: str, actual_address: str = "") -> str:
        components = extract_address_components(candidate)
        normalized_candidate = self._normalize_address_text(candidate)
        has_province = bool(components.province)
        has_city = bool(components.city)
        has_district = bool(components.district)
        has_town = bool(components.town)
        has_road = bool(components.road)
        has_community = bool(components.community)
        has_precise_detail = bool(components.has_precise_detail)
        has_nonstandard_detail = bool(
            self._extract_village_group_token(candidate)
            or self._extract_house_number_token(candidate)
            or self._has_landmark_delivery_detail(candidate)
        )
        has_anchor = bool(has_community or has_precise_detail or has_nonstandard_detail)

        district_is_noncounty = self._is_noncounty_district(components.district)
        city_for_followup = self._address_city_for_followup(candidate, actual_address)
        province_tail = normalized_candidate
        if has_province:
            normalized_province = self._normalize_address_text(components.province)
            if normalized_province and normalized_candidate.startswith(normalized_province):
                province_tail = normalized_candidate[len(normalized_province) :]
        province_tail_components = extract_address_components(province_tail) if province_tail != normalized_candidate else AddressComponents()
        province_tail_has_anchor = bool(
            province_tail_components.community
            or province_tail_components.has_precise_detail
            or self._extract_village_group_token(province_tail)
            or self._extract_house_number_token(province_tail)
            or self._has_landmark_delivery_detail(province_tail)
        )
        matches_province_town_only = bool(
            has_province
            and province_tail
            and province_tail_components.town
            and not province_tail_components.city
            and not province_tail_components.district
            and not province_tail_components.road
        )
        matches_province_community_only = bool(
            has_province
            and province_tail
            and province_tail_has_anchor
            and not province_tail_components.city
            and not province_tail_components.district
            and not province_tail_components.town
            and not province_tail_components.road
        )

        if has_city and not has_province and not has_district and not has_town and not has_road and not has_anchor:
            if city_for_followup:
                return self._address_city_district_followup_prompt(city_for_followup)

        if has_district and district_is_noncounty and not has_province and not has_city:
            return self._address_province_city_followup_prompt()

        if has_town and not has_province and not has_city and not has_district and not has_road and not has_anchor:
            return self._address_full_region_followup_prompt()

        if has_province and has_district and not has_city and not has_town and not has_road and not has_anchor:
            return self._address_locality_which_followup_prompt()

        if (
            matches_province_town_only
            or (
                has_province
                and has_town
                and not has_city
                and not has_district
                and not has_road
            )
        ):
            return self._address_city_district_only_followup_prompt()

        if has_anchor and not has_province and not has_city and not has_district and not has_town and not has_road:
            return self._address_region_street_followup_prompt()

        if (
            matches_province_community_only
            or (
                has_province
                and has_anchor
                and not has_city
                and not has_district
                and not has_town
                and not has_road
            )
        ):
            return self._address_city_district_info_followup_prompt()

        if (
            has_province
            and has_city
            and has_anchor
            and not has_district
            and not has_town
            and not has_road
        ):
            if city_for_followup:
                return self._address_city_district_town_followup_prompt(city_for_followup)

        if has_city and has_anchor and not has_province and not has_district and not has_town and not has_road:
            if city_for_followup:
                return self._address_city_district_town_followup_prompt(city_for_followup)

        if has_town and has_anchor and not has_province and not has_city and not has_district and not has_road:
            return self._address_full_region_compact_followup_prompt()

        if self._should_use_locality_which_followup(candidate, components):
            return self._address_locality_which_followup_prompt()
        return ""

    def _address_followup_prompt(self, candidate: str, actual_address: str) -> str:
        components = extract_address_components(candidate)
        has_confirmation_anchor = self._address_has_confirmation_anchor(candidate, components)
        special_prompt = self._address_special_followup_prompt(candidate, actual_address)
        if special_prompt:
            return special_prompt
        if self._requires_city_level_followup(candidate):
            return self._address_region_street_followup_prompt()
        if components.province and not components.city:
            return self._address_province_city_district_street_followup_prompt(components.province)
        if not components.district:
            if components.province or components.city:
                city = self._address_city_for_followup(candidate, actual_address)
                if city:
                    return self._address_city_district_followup_prompt(city)
                return self._address_district_street_followup_prompt()
            if (
                components.has_locality
                or components.has_precise_detail
                or self._has_nonstandard_address_detail(candidate)
            ):
                return self._address_region_street_followup_prompt()
            city = self._address_city_for_followup(candidate, actual_address)
            if city:
                return self._address_district_street_followup_prompt()
        if components.district and not components.has_locality:
            return self._address_locality_followup_prompt()
        if components.has_locality and not self._address_has_site_locality(components):
            return self._address_locality_followup_prompt()
        if components.has_locality and not has_confirmation_anchor:
            return self._address_locality_followup_prompt()
        if components.has_precise_detail and not components.has_locality:
            return self._address_locality_followup_prompt()
        return self._choose_prompt_text(self.ADDRESS_PROMPT)

    def _address_followup_prompt_for_actual(self, *, candidate: str, actual_address: str) -> str:
        components = extract_address_components(candidate)
        has_confirmation_anchor = self._address_has_confirmation_anchor(candidate, components)
        special_prompt = self._address_special_followup_prompt(candidate, actual_address)
        if special_prompt:
            return special_prompt
        if self._requires_city_level_followup(candidate):
            return self._address_region_street_followup_prompt()
        if not components.district and (
            components.has_locality
            or components.has_precise_detail
            or self._has_nonstandard_address_detail(candidate)
        ):
            return self._address_followup_prompt(candidate, actual_address)
        if self._is_rural_address_candidate(candidate) and not has_confirmation_anchor:
            return self._address_rural_detail_followup_prompt()
        if components.has_locality and not self._address_has_site_locality(components):
            return self._address_locality_followup_prompt()
        if components.has_locality and not has_confirmation_anchor:
            return self._address_locality_followup_prompt()
        if components.has_precise_detail and not components.has_locality:
            return self._address_locality_followup_prompt()
        return self._address_followup_prompt(candidate, actual_address)

    def _address_followup_prompt_for_scenario(self, *, scenario: Scenario, candidate: str) -> str:
        actual_address = scenario.customer.address
        if self._interactive_test_freeform_enabled(scenario) and (
            not self._manual_test_uses_address_precision_reference(scenario)
            or not self._has_known_value(actual_address)
        ):
            if not self._has_unknown_actual_confirmation_precision(candidate):
                return self._address_followup_prompt_for_unknown_actual(candidate)
        return self._address_followup_prompt_for_actual(
            candidate=candidate,
            actual_address=actual_address,
        )

    def _address_followup_prompt_for_unknown_actual(self, candidate: str) -> str:
        components = extract_address_components(candidate)
        has_confirmation_anchor = self._address_has_confirmation_anchor(candidate, components)
        special_prompt = self._address_special_followup_prompt(candidate)
        if special_prompt:
            return special_prompt
        if self._requires_city_level_followup(candidate):
            return self._address_region_street_followup_prompt()
        if components.province and not components.city:
            return self._address_province_city_district_street_followup_prompt(components.province)
        if not components.district:
            if components.province or components.city:
                if components.city:
                    return self._address_city_district_followup_prompt(components.city)
                return self._address_district_street_followup_prompt()
            if (
                components.has_locality
                or components.has_precise_detail
                or self._has_nonstandard_address_detail(candidate)
            ):
                return self._address_region_street_followup_prompt()
        if self._is_rural_address_candidate(candidate) and not has_confirmation_anchor:
            return self._address_rural_detail_followup_prompt()
        if components.has_locality and not self._address_has_site_locality(components):
            return self._address_locality_followup_prompt()
        if components.has_locality and not has_confirmation_anchor:
            return self._address_locality_followup_prompt()
        if components.has_precise_detail and not components.has_locality:
            return self._address_locality_followup_prompt()
        return self._address_followup_prompt(candidate, "")

    @staticmethod
    def _address_city_for_followup(candidate: str, actual_address: str) -> str:
        candidate_components = extract_address_components(candidate)
        actual_components = extract_address_components(actual_address)
        city = candidate_components.city or actual_components.city
        if city:
            return city if city.endswith("市") else f"{city}市"
        return ""

    @staticmethod
    def _interactive_test_freeform_enabled(scenario: Scenario) -> bool:
        return bool(scenario.hidden_context.get("interactive_test_freeform", False))

    @staticmethod
    def _manual_test_uses_address_precision_reference(scenario: Scenario) -> bool:
        if not bool(scenario.hidden_context.get("interactive_test_freeform", False)):
            return True
        return bool(scenario.hidden_context.get("manual_test_address_precision_reference", False))

    @staticmethod
    def _has_known_value(value: str) -> bool:
        normalized = str(value or "").strip().lower()
        return normalized not in {"", "未知", "unknown", "n/a", "na", "null", "none"}

    @classmethod
    def _extract_mobile_phone(cls, text: str) -> str:
        digits = re.sub(r"\D", "", text or "")
        match = MOBILE_PHONE_PATTERN.search(digits)
        return match.group(0) if match else ""

    @classmethod
    def _extract_freeform_surname(cls, text: str) -> str:
        cleaned = str(text or "").strip()
        if not cleaned or cls._classify_yes_no(cleaned) in {"yes", "no"}:
            return ""

        explicit_patterns = (
            r"(?:我姓|姓)\s*([一-龥])",
            r"(?:免贵姓|贵姓)\s*([一-龥])",
            r"(?:我叫|名字是|姓名是)\s*([一-龥]{2,4})",
        )
        for pattern in explicit_patterns:
            match = re.search(pattern, cleaned)
            if match:
                return match.group(1)[0]

        compact = re.sub(r"[，,。！？!?：:\s]", "", cleaned)
        compact = re.sub(r"^(好的|嗯|啊|呃|额|是|对)+", "", compact)
        split_surname_prefixes = (
            "弓长",
            "木子",
            "口天",
            "耳东",
            "关耳",
            "言午",
            "双木",
            "立早",
            "古月",
            "子小",
            "走肖",
            "三横",
            "禾火",
            "双口",
            "示申",
            "山今",
            "女马",
            "鱼羊",
            "酉告",
            "单人",
            "提土",
            "门耳",
            "车干",
            "虫二",
            "草头",
            "日京",
            "两土",
        )
        if any(compact.startswith(prefix) and len(compact) == len(prefix) + 1 for prefix in split_surname_prefixes):
            return compact[-1]
        if re.fullmatch(r"[一-龥]{1,4}", compact):
            return compact[0]
        return ""

    @classmethod
    def _is_rural_address_candidate(cls, text: str) -> bool:
        normalized = cls._normalize_address_text(text)
        patterns = (
            r"自然村",
            r"行政村",
            r"村委会",
            r"村民组",
            r"屯",
            r"村(?!镇|街道|路|街|大道|巷|弄|社区|小区|花园|公寓|苑|府|里|大厦|中心|广场|城)",
            r"\d+组",
            r"[零一二三四五六七八九十两]+组",
            r"\d+队",
        )
        return any(re.search(pattern, normalized) for pattern in patterns)

    @classmethod
    def _contains_rural_no_building_statement(cls, text: str) -> bool:
        normalized = cls._normalize_address_text(text)
        patterns = (
            r"村.*没.*栋",
            r"村.*没有.*栋",
            r"没.*楼栋",
            r"没有.*楼栋",
            r"没.*单元",
            r"没有.*单元",
            r"不是楼房",
            r"自建房",
            r"平房",
        )
        return any(re.search(pattern, normalized) for pattern in patterns)

    @staticmethod
    def _address_component_count(components: AddressComponents) -> int:
        return sum(
            1
            for value in (
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
            if value
        )

    @classmethod
    def _address_input_makes_progress(
        cls,
        *,
        existing: str,
        incoming: str,
        merged: str,
    ) -> bool:
        normalized_incoming = cls._normalize_address_text(incoming)
        if not normalized_incoming:
            return False
        existing_components = extract_address_components(existing)
        incoming_components = extract_address_components(incoming)
        merged_components = extract_address_components(merged)
        incoming_component_count = cls._address_component_count(incoming_components)
        address_like_markers = bool(
            re.search(r"(省|市|区|县|镇|乡|街道|路|街|大道|巷|弄|胡同|小区|花园|公寓|苑|府|里|村|大厦|中心|广场|城|栋|幢|座|楼|单元|室|\d)", normalized_incoming)
        )
        if incoming_component_count == 0 and not address_like_markers:
            return False
        if cls._normalize_address_text(merged) != cls._normalize_address_text(existing):
            return True
        return (
            incoming_component_count > 0
            and cls._address_component_count(merged_components) > cls._address_component_count(existing_components)
        )

    @staticmethod
    def _remember_address_followup_prompt(
        runtime_state: ServiceRuntimeState,
        prompt: str,
    ) -> str:
        runtime_state.last_address_followup_prompt = prompt
        return prompt

    def _repeat_address_followup_prompt(self, runtime_state: ServiceRuntimeState) -> str:
        if runtime_state.address_vague_retry_count < 2:
            runtime_state.address_vague_retry_count += 1
            if runtime_state.last_address_followup_prompt:
                return runtime_state.last_address_followup_prompt
        runtime_state.address_vague_retry_count = 0
        prompt = self._address_prompt()
        runtime_state.last_address_followup_prompt = prompt
        return prompt

    def _address_confirmation_prompt(
        self,
        address: str,
        *,
        use_known_address_prompt: bool = False,
    ) -> str:
        display_address = self._sanitize_address_for_confirmation_display(address)
        prompt_config = (
            self.KNOWN_ADDRESS_CONFIRMATION_TEMPLATE
            if use_known_address_prompt
            else self.ADDRESS_CONFIRMATION_TEMPLATE
        )
        return self._with_optional_ok_prefix(
            self._choose_prompt_text(prompt_config, address=display_address)
        )

    def _address_recollection_prompt(self) -> str:
        return self._choose_prompt_text(self.ADDRESS_RECOLLECTION_PROMPT)

    @staticmethod
    def _sanitize_address_for_confirmation_display(address: str) -> str:
        return re.sub(r"[，,。！？!?；;：:、]", "", str(address or "")).strip()

    @classmethod
    def _address_candidate_meets_ie_trigger_threshold(cls, candidate: str) -> bool:
        normalized_candidate = cls._normalize_address_text(candidate)
        if not normalized_candidate:
            return False

        components = extract_address_components(normalized_candidate)
        admin_level_count = sum(
            1
            for value in (
                components.province,
                components.city,
                components.district,
                components.town,
            )
            if value
        )
        city_name = comparable_component("city", components.city)
        required_admin_level_count = 2 if city_name in MUNICIPALITY_PREFIXES else 3
        has_locality_or_finer = bool(
            components.community
            or components.has_precise_detail
            or cls._has_nonstandard_address_detail(normalized_candidate)
        )
        has_county_short_path = bool(
            cls._is_county_district(components.district)
            and not components.road
        )
        return has_locality_or_finer and (
            admin_level_count >= required_admin_level_count or has_county_short_path
        )

    def should_insert_address_ie_function_call(
        self,
        *,
        user_text: str,
        transcript: list[DialogueTurn],
        runtime_state: ServiceRuntimeState,
    ) -> bool:
        if not runtime_state.awaiting_full_address:
            return False
        previous_service_text = self._previous_service_text(transcript)
        normalized_previous_service_text = self._normalize_prompt_text(previous_service_text)
        if not (
            self.is_address_collection_prompt(previous_service_text)
            or normalized_previous_service_text.startswith("您是在")
            or normalized_previous_service_text.startswith("请问是")
        ):
            return False

        previous_candidate = runtime_state.partial_address_candidate
        prepared_user_address = self._prepare_address_for_confirmation(user_text)
        if not prepared_user_address:
            return False

        merged_candidate = self._merge_address_candidate(previous_candidate, prepared_user_address)
        if not merged_candidate:
            return False
        return (
            self._address_candidate_meets_ie_trigger_threshold(merged_candidate)
            and not self._address_candidate_meets_ie_trigger_threshold(previous_candidate)
        )

    def should_insert_address_ie_after_observation_confirmation(
        self,
        *,
        user_text: str,
        user_round_index: int,
        transcript: list[DialogueTurn],
        runtime_state: ServiceRuntimeState,
    ) -> bool:
        if not (
            runtime_state.expected_address_confirmation
            and runtime_state.address_confirmation_triggered_by_observation
        ):
            return False
        confirmation_address = str(runtime_state.pending_address_confirmation or "").strip()
        if not confirmation_address:
            return False
        followup_intent = self._classify_observation_address_confirmation_followup_intent(
            user_text,
            confirmation_address=confirmation_address,
            user_round_index=user_round_index,
        )
        if followup_intent in {"modify", "add", "delete"}:
            return True
        if followup_intent == "confirm_only":
            return False
        confirmation_intent = self._classify_confirmation_intent(
            user_text,
            prompt_kind="address_confirmation",
            user_round_index=user_round_index,
        )
        if confirmation_intent in {"yes", "no"}:
            return False
        prepared_user_address = self._prepare_address_for_confirmation(user_text)
        if prepared_user_address:
            merged_candidate = self._merge_address_candidate(
                confirmation_address,
                prepared_user_address,
            )
            if merged_candidate and self._address_input_makes_progress(
                existing=confirmation_address,
                incoming=prepared_user_address,
                merged=merged_candidate,
            ):
                return True
        denial_address, _ = self._resolve_confirmation_denial_address_candidate(
            transcript=transcript,
            user_text=user_text,
            confirmation_address=confirmation_address,
        )
        if not denial_address:
            return False
        return self._normalize_address_text(denial_address) != self._normalize_address_text(confirmation_address)

    def _product_arrival_prompt(self, scenario: Scenario) -> str:
        prompt_config = self._format_prompt_config(self.PRODUCT_ARRIVAL_PROMPT, product=self._product_name(scenario))
        return self._with_optional_ok_prefix(self._choose_prompt_text(prompt_config))

    def _product_model_prompt(self) -> str:
        return self._choose_prompt_text(self.PRODUCT_MODEL_PROMPT)

    def _transition_to_next_slot(
        self,
        *,
        scenario: Scenario,
        collected_slots: dict[str, str],
        slot_updates: dict[str, str],
        runtime_state: ServiceRuntimeState,
        next_slot: str | None,
    ) -> ServicePolicyResult:
        if self._should_run_product_routing(scenario, runtime_state):
            return self._start_product_routing_step(
                scenario=scenario,
                runtime_state=runtime_state,
                slot_updates=slot_updates,
                prepend_fault_ack=self._should_prepend_fault_acknowledgement(
                    scenario=scenario,
                    collected_slots=collected_slots,
                    slot_updates=slot_updates,
                ),
            )

        merged_slots = dict(collected_slots)
        merged_slots.update(slot_updates)
        if merged_slots.get("product_routing_result", "").strip() == ROUTING_RESULT_HUMAN:
            return self._handoff_to_human(
                scenario=scenario,
                runtime_state=runtime_state,
                slot_updates=slot_updates,
                reason="product_routing_human",
            )

        if scenario.request.request_type == "installation" and not runtime_state.product_arrival_checked:
            return self._start_product_arrival_confirmation(
                scenario=scenario,
                runtime_state=runtime_state,
                slot_updates=slot_updates,
            )

        if not next_slot:
            return ServicePolicyResult(
                reply=self._start_closing_sequence(scenario, runtime_state),
                slot_updates=slot_updates,
                is_ready_to_close=False,
            )

        if next_slot == "phone":
            runtime_state.expected_contactable_confirmation = True
        elif next_slot == "address":
            known_address = self._service_known_address_value(scenario)
            if known_address:
                return self._start_address_confirmation(
                    scenario=scenario,
                    runtime_state=runtime_state,
                    address=known_address,
                    slot_updates=slot_updates,
                    use_known_address_prompt=True,
                )
            runtime_state.awaiting_full_address = True
            runtime_state.address_input_attempts = 0
            runtime_state.partial_address_candidate = ""
            runtime_state.address_vague_retry_count = 0
            runtime_state.last_address_followup_prompt = self._address_prompt()

        return ServicePolicyResult(
            reply=self._reply_for_next_slot(
                scenario=scenario,
                collected_slots=collected_slots,
                slot_updates=slot_updates,
                next_slot=next_slot,
            ),
            slot_updates=slot_updates,
            is_ready_to_close=False,
        )

    def _product_routing_steps(self, scenario: Scenario) -> list[dict[str, str]]:
        return get_product_routing_steps(scenario.hidden_context)

    def _update_product_routing_plan(
        self,
        *,
        scenario: Scenario,
        steps: list[dict[str, str]],
        trace: list[str],
        result: str,
    ) -> None:
        hidden_context = scenario.hidden_context if isinstance(scenario.hidden_context, dict) else {}
        summary_parts = [item for item in trace if str(item).strip()]
        if result:
            summary_parts.append(result)
        plan = {
            "enabled": True,
            "result": result,
            "trace": list(trace),
            "steps": list(steps),
            "summary": " -> ".join(summary_parts),
        }
        hidden_context["product_routing_plan"] = plan
        hidden_context["product_routing_result"] = result
        hidden_context["product_routing_trace"] = list(trace)
        hidden_context["product_routing_summary"] = plan["summary"]
        scenario.hidden_context = hidden_context

    def _has_pending_product_routing_step(
        self,
        scenario: Scenario,
        runtime_state: ServiceRuntimeState,
    ) -> bool:
        steps = self._product_routing_steps(scenario)
        return runtime_state.product_routing_step_index < len(steps)

    def _should_run_product_routing(
        self,
        scenario: Scenario,
        runtime_state: ServiceRuntimeState,
    ) -> bool:
        if not self.product_routing_enabled:
            return False
        if bool(scenario.hidden_context.get("interactive_test_skip_product_routing", False)):
            return False
        if runtime_state.product_routing_completed or runtime_state.expected_product_routing_response:
            return False
        return self._has_pending_product_routing_step(scenario, runtime_state)

    def _try_advance_product_routing_from_context(
        self,
        *,
        scenario: Scenario,
        user_text: str,
        user_round_index: int,
        previous_service_signature: str,
        collected_slots: dict[str, str],
        slot_updates: dict[str, str],
        runtime_state: ServiceRuntimeState,
    ) -> ServicePolicyResult | None:
        if not self._should_run_product_routing(scenario, runtime_state):
            return None
        if previous_service_signature != self._normalize_prompt_text(self._build_opening_prompt(scenario)):
            return None

        steps = self._product_routing_steps(scenario)
        if runtime_state.product_routing_step_index >= len(steps):
            return None
        current_step = steps[runtime_state.product_routing_step_index]
        prompt_key = str(current_step.get("prompt_key", "")).strip()
        if not prompt_key:
            return None

        observed_answer_key = infer_product_routing_answer_key(prompt_key, user_text)
        if not observed_answer_key:
            return None

        return self._advance_product_routing_with_answer(
            scenario=scenario,
            collected_slots=collected_slots,
            slot_updates=slot_updates,
            runtime_state=runtime_state,
            observed_answer_key=observed_answer_key,
        )

    def _advance_product_routing_with_answer(
        self,
        *,
        scenario: Scenario,
        collected_slots: dict[str, str],
        slot_updates: dict[str, str],
        runtime_state: ServiceRuntimeState,
        observed_answer_key: str,
        post_answer_trace: list[str] | None = None,
    ) -> ServicePolicyResult:
        runtime_state.product_routing_observed_trace.append(observed_answer_key)
        resolved_post_answer_trace = list(post_answer_trace or [])
        if observed_answer_key == "entry.model" and not resolved_post_answer_trace:
            fallback_model_lookup = infer_model_lookup_answer_key(scenario.product.model)
            if fallback_model_lookup:
                resolved_post_answer_trace.append(fallback_model_lookup)
        if resolved_post_answer_trace:
            runtime_state.product_routing_observed_trace.extend(
                item for item in resolved_post_answer_trace if str(item).strip()
            )
        next_steps, result = next_product_routing_steps_from_observed_trace(
            runtime_state.product_routing_observed_trace,
            model_hint=scenario.product.model,
        )
        self._update_product_routing_plan(
            scenario=scenario,
            steps=next_steps,
            trace=runtime_state.product_routing_observed_trace,
            result=result,
        )
        runtime_state.product_routing_step_index = 0
        if next_steps:
            return self._start_product_routing_step(
                scenario=scenario,
                runtime_state=runtime_state,
                slot_updates=slot_updates,
            )

        runtime_state.product_routing_completed = True
        slot_updates = self._with_product_routing_result_slot(
            scenario=scenario,
            slot_updates=slot_updates,
            result=result,
        )
        if slot_updates.get("product_routing_result", "").strip() == ROUTING_RESULT_HUMAN:
            return self._handoff_to_human(
                scenario=scenario,
                runtime_state=runtime_state,
                slot_updates=slot_updates,
                reason="product_routing_human",
            )
        merged_slots = dict(collected_slots)
        merged_slots.update(slot_updates)
        next_slot = self._next_slot_to_request(merged_slots, effective_required_slots(scenario))
        return self._transition_to_next_slot(
            scenario=scenario,
            collected_slots=collected_slots,
            slot_updates=slot_updates,
            runtime_state=runtime_state,
            next_slot=next_slot,
        )

    def _start_product_routing_step(
        self,
        *,
        scenario: Scenario,
        runtime_state: ServiceRuntimeState,
        slot_updates: dict[str, str],
        prepend_fault_ack: bool = False,
    ) -> ServicePolicyResult:
        steps = self._product_routing_steps(scenario)
        if runtime_state.product_routing_step_index >= len(steps):
            runtime_state.product_routing_completed = True
            return ServicePolicyResult(reply="", slot_updates=slot_updates, is_ready_to_close=False)

        self._update_product_routing_plan(
            scenario=scenario,
            steps=steps[runtime_state.product_routing_step_index :],
            trace=runtime_state.product_routing_observed_trace,
            result="",
        )
        runtime_state.expected_product_routing_response = True
        reply = steps[runtime_state.product_routing_step_index]["prompt"]
        if prepend_fault_ack and runtime_state.product_routing_step_index == 0:
            reply = self._prepend_fault_acknowledgement(reply)
        return ServicePolicyResult(
            reply=reply,
            slot_updates=slot_updates,
            is_ready_to_close=False,
        )

    @classmethod
    def _should_transfer_to_human(cls, text: str) -> bool:
        normalized = re.sub(r"\s+", "", text or "")
        if not normalized:
            return False
        negative_patterns = (
            "不用转人工",
            "先不用转人工",
            "不需要转人工",
            "不用人工",
            "不需要人工",
        )
        if any(pattern in normalized for pattern in negative_patterns):
            return False

        direct_tokens = (
            "转人工",
            "转接人工",
            "人工客服",
            "人工服务",
            "真人客服",
            "人工坐席",
        )
        if any(token in normalized for token in direct_tokens):
            return True

        patterns = (
            r"(给我|帮我|麻烦)?转(到)?人工",
            r"(给我|帮我|麻烦)?接人工",
            r"我要人工",
            r"我要找人工",
            r"我要转人工",
            r"转人工吧",
            r"找人工(客服|服务)?",
        )
        return any(re.search(pattern, normalized) for pattern in patterns)

    @staticmethod
    def _reset_runtime_state_for_terminal_close(runtime_state: ServiceRuntimeState) -> None:
        runtime_state.expected_contactable_confirmation = False
        runtime_state.awaiting_phone_keypad_input = False
        runtime_state.expected_phone_number_confirmation = False
        runtime_state.pending_phone_number_confirmation = ""
        runtime_state.expected_address_confirmation = False
        runtime_state.address_confirmation_triggered_by_observation = False
        runtime_state.address_confirmation_started_from_known_address = False
        runtime_state.expected_product_arrival_confirmation = False
        runtime_state.pending_address_confirmation = ""
        runtime_state.awaiting_full_address = False
        runtime_state.partial_address_candidate = ""
        runtime_state.last_address_followup_prompt = ""
        runtime_state.expected_product_routing_response = False
        runtime_state.product_routing_completed = True
        runtime_state.awaiting_closing_ack = False
        runtime_state.awaiting_satisfaction_rating = False

    def _handoff_to_human(
        self,
        *,
        scenario: Scenario,
        runtime_state: ServiceRuntimeState,
        slot_updates: dict[str, str],
        reason: str,
    ) -> ServicePolicyResult:
        self._reset_runtime_state_for_terminal_close(runtime_state)
        updated_slot_updates = self._with_product_routing_result_slot(
            scenario=scenario,
            slot_updates=slot_updates,
            result=ROUTING_RESULT_HUMAN,
        )
        return ServicePolicyResult(
            reply=self.HUMAN_HANDOFF_REPLY,
            slot_updates=updated_slot_updates,
            is_ready_to_close=True,
            close_status="transferred",
            close_reason=reason,
        )
