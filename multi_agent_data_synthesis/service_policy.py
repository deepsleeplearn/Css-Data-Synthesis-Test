from __future__ import annotations

import random
import re
from dataclasses import dataclass

from multi_agent_data_synthesis.address_utils import (
    MUNICIPALITY_PREFIXES,
    PROVINCE_PREFIXES,
    AddressComponents,
    compact_address_text,
    components_match,
    extract_address_components,
    normalize_address_text,
)
from multi_agent_data_synthesis.schemas import (
    DialogueTurn,
    Scenario,
    SERVICE_SPEAKER,
    USER_SPEAKER,
    effective_required_slots,
    normalize_speaker,
)
from multi_agent_data_synthesis.static_utterances import (
    appointment_utterance,
    ask_satisfaction_utterance,
    end_utterance,
    fee_collect_utterance,
)


MOBILE_PHONE_PATTERN = re.compile(r"^1[3-9]\d{9}$")
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
    expected_product_arrival_confirmation: bool = False
    product_arrival_checked: bool = False
    pending_address_confirmation: str = ""
    awaiting_full_address: bool = False
    address_input_attempts: int = 0
    partial_address_candidate: str = ""
    address_vague_retry_count: int = 0
    last_address_followup_prompt: str = ""
    awaiting_closing_ack: bool = False
    awaiting_satisfaction_rating: bool = False


@dataclass
class ServicePolicyResult:
    reply: str
    slot_updates: dict[str, str]
    is_ready_to_close: bool


class ServiceDialoguePolicy:
    FAULT_ACKNOWLEDGEMENT_PREFIX = "非常抱歉，给您添麻烦了，我这就安排师傅上门维修"

    SURNAME_PROMPT = "请问您贵姓？"
    CONTACTABLE_PROMPT = "请问您当前这个来电号码能联系到您吗？"
    PHONE_KEYPAD_PROMPT = "请您在拨号盘上输入您的联系方式，并以#号键结束。"
    PHONE_KEYPAD_RETRY_PROMPT = "您输入的号码有误，请重新在拨号盘上输入您的联系方式，并以#号键结束。"
    PHONE_CONFIRMATION_TEMPLATE = "号码是{phone}，对吗？"
    FAULT_ISSUE_PROMPT = "请问{product}现在是出现了什么问题？"
    ADDRESS_PROMPT = "需要登记下您的地址，麻烦您完整的说下省、市、区、乡镇，精确到门牌号。"
    ADDRESS_CITY_DISTRICT_FOLLOWUP_TEMPLATE = "好的，您是在{city}的哪个区县呢？具体小区门牌号也提供一下呢？"
    ADDRESS_LOCALITY_FOLLOWUP_PROMPT = "好的，请您继续说一下小区、楼栋和门牌号。"
    ADDRESS_BUILDING_FOLLOWUP_PROMPT = "请问是几栋几单元几楼几号呢？"
    ADDRESS_CONFIRMATION_TEMPLATE = "跟您确认一下，地址是{address}，对吗？"
    KNOWN_ADDRESS_CONFIRMATION_TEMPLATE = "您的地址是{address}，对吗？"
    PRODUCT_ARRIVAL_PROMPT = "请问{product}到货了没？"
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
    ADDRESS_CITY_DISTRICT_FOLLOWUP_TEMPLATE: PromptConfig = [
        ("好的，您是在{city}的哪个区县呢？具体小区门牌号也提供一下呢？", 1.0)
    ]
    ADDRESS_LOCALITY_FOLLOWUP_PROMPT: PromptConfig = [("好的，请您继续说一下小区、楼栋和门牌号。", 1.0)]
    ADDRESS_BUILDING_FOLLOWUP_PROMPT: PromptConfig = [("请问是几栋几单元几楼几号呢？", 1.0)]
    ADDRESS_CONFIRMATION_TEMPLATE: PromptConfig = [("跟您确认一下，地址是{address}，对吗？", 1.0)]
    KNOWN_ADDRESS_CONFIRMATION_TEMPLATE: PromptConfig = [("您的地址是{address}，对吗？", 1.0)]
    PRODUCT_ARRIVAL_PROMPT: PromptConfig = [("请问{product}到货了没？", 1.0)]
    PRODUCT_MODEL_PROMPT: PromptConfig = [("请问产品型号方便提供一下吗？", 1.0)]
    def __init__(
        self,
        ok_prefix_probability: float = 1.0,
        rng: random.Random | None = None,
    ):
        self.ok_prefix_probability = max(0.0, min(1.0, ok_prefix_probability))
        self.rng = rng or random.Random()

    def respond(
        self,
        *,
        scenario: Scenario,
        transcript: list[DialogueTurn],
        collected_slots: dict[str, str],
        runtime_state: ServiceRuntimeState,
    ) -> ServicePolicyResult:
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
            collected_slots=collected_slots,
        )
        required_slots = effective_required_slots(scenario)
        merged_slots = dict(collected_slots)
        merged_slots.update(slot_updates)

        if runtime_state.expected_contactable_confirmation:
            return self._handle_contactable_confirmation(
                scenario=scenario,
                user_text=last_user_turn.text,
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
                collected_slots=merged_slots,
                runtime_state=runtime_state,
            )

        if runtime_state.expected_address_confirmation:
            return self._handle_address_confirmation(
                scenario=scenario,
                user_text=last_user_turn.text,
                collected_slots=merged_slots,
                runtime_state=runtime_state,
                slot_updates=slot_updates,
            )

        if runtime_state.expected_product_arrival_confirmation:
            return self._handle_product_arrival_confirmation(
                scenario=scenario,
                user_text=last_user_turn.text,
                collected_slots=merged_slots,
                slot_updates=slot_updates,
                runtime_state=runtime_state,
            )

        if runtime_state.awaiting_full_address:
            return self._handle_full_address_input(
                scenario=scenario,
                user_text=last_user_turn.text,
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

        if (
            "issue_description" in collected_slots
            and not collected_slots["issue_description"].strip()
            and user_text.strip()
            and self._normalize_prompt_text(user_text)
            != self._normalize_prompt_text(self.build_initial_user_utterance(scenario))
            and self._opening_response_contains_issue_detail(user_text)
        ):
            slot_updates["issue_description"] = user_text.strip()

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
        collected_slots: dict[str, str],
        runtime_state: ServiceRuntimeState,
    ) -> ServicePolicyResult:
        intent = self._classify_yes_no(user_text)
        runtime_state.expected_contactable_confirmation = False

        if intent == "yes":
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
            owner = self._contact_phone_owner(scenario)
            if owner:
                slot_updates["phone_contact_owner"] = owner
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
        collected_slots: dict[str, str],
        runtime_state: ServiceRuntimeState,
    ) -> ServicePolicyResult:
        intent = self._classify_yes_no(user_text)
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
        collected_slots: dict[str, str],
        runtime_state: ServiceRuntimeState,
        slot_updates: dict[str, str],
    ) -> ServicePolicyResult:
        intent = self._classify_yes_no(user_text)
        runtime_state.expected_address_confirmation = False
        confirmation_address = (
            runtime_state.pending_address_confirmation
            or self._service_known_address_value(scenario)
            or scenario.customer.address
        )

        if intent == "yes":
            slot_updates = dict(slot_updates)
            slot_updates["address"] = scenario.customer.address
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
            denial_address = self._extract_address_candidate_from_denial(
                user_text=user_text,
                confirmation_address=confirmation_address,
            )
            if denial_address:
                runtime_state.awaiting_full_address = True
                runtime_state.address_input_attempts = 1
                runtime_state.pending_address_confirmation = ""
                merged_candidate = self._merge_address_candidate(confirmation_address, denial_address)
                runtime_state.partial_address_candidate = merged_candidate
                runtime_state.address_vague_retry_count = 0
                normalized_candidate = self._normalize_address_text(merged_candidate)
                if self._is_complete_address(normalized_candidate, scenario.customer.address):
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
                        self._address_followup_prompt_for_actual(
                        candidate=normalized_candidate,
                        actual_address=scenario.customer.address,
                        ),
                    ),
                    slot_updates=slot_updates,
                    is_ready_to_close=False,
                )
            if self._is_detail_only_confirmation_mismatch(
                confirmation_address=confirmation_address,
                actual_address=scenario.customer.address,
            ):
                runtime_state.awaiting_full_address = True
                runtime_state.address_input_attempts = 0
                runtime_state.pending_address_confirmation = ""
                runtime_state.partial_address_candidate = confirmation_address
                runtime_state.address_vague_retry_count = 0
                return ServicePolicyResult(
                    reply=self._remember_address_followup_prompt(
                        runtime_state,
                        self._address_building_followup_prompt(),
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
                reply=self._remember_address_followup_prompt(runtime_state, self._address_prompt()),
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
        collected_slots: dict[str, str],
        runtime_state: ServiceRuntimeState,
        slot_updates: dict[str, str],
    ) -> ServicePolicyResult:
        prepared_address = self._prepare_address_for_confirmation(user_text)
        previous_candidate = runtime_state.partial_address_candidate
        combined_address = self._merge_address_candidate(
            previous_candidate,
            prepared_address,
        )
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

        if self._is_complete_address(address_candidate, scenario.customer.address):
            return self._start_address_confirmation(
                scenario=scenario,
                runtime_state=runtime_state,
                address=combined_address,
                slot_updates=slot_updates,
                use_known_address_prompt=False,
            )

        return ServicePolicyResult(
            reply=self._remember_address_followup_prompt(
                runtime_state,
                self._address_followup_prompt_for_actual(
                    candidate=address_candidate,
                    actual_address=scenario.customer.address,
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
        collected_slots: dict[str, str],
        slot_updates: dict[str, str],
        runtime_state: ServiceRuntimeState,
    ) -> ServicePolicyResult:
        intent = self._classify_yes_no(user_text)

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
        collected_slots: dict[str, str],
    ) -> dict[str, str]:
        slot_updates: dict[str, str] = {}

        if (
            "issue_description" in collected_slots
            and not collected_slots["issue_description"].strip()
            and user_text.strip()
        ):
            if previous_service_signature == self._normalize_prompt_text(self._build_opening_prompt(scenario)):
                if self._opening_response_contains_issue_detail(user_text):
                    slot_updates["issue_description"] = user_text.strip()
                elif (
                    scenario.request.request_type == "installation"
                    and self._classify_yes_no(user_text) == "yes"
                ):
                    slot_updates["issue_description"] = user_text.strip()
            elif self._signature_matches_prompt(
                previous_service_signature,
                self._format_prompt_config(self.FAULT_ISSUE_PROMPT, product=self._product_name(scenario)),
            ):
                slot_updates["issue_description"] = user_text.strip()

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
            and scenario.customer.surname in user_text
        ):
            slot_updates["surname"] = scenario.customer.surname

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

    def _appointment_prompt_for_scenario(self, scenario: Scenario) -> str:
        return appointment_utterance(
            brand=scenario.product.brand,
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
        return end_utterance(brand=scenario.product.brand)

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
            "可以",
            "能联系",
            "能打通",
            "是的",
            "对",
            "对的",
            "就是这个",
            "没错",
            "正确",
            "到了",
            "到货了",
            "已经到了",
            "已经到货",
            "可以联系",
            "行",
            "嗯",
        )

        if any(keyword in normalized for keyword in negative_keywords):
            return "no"
        if any(keyword in normalized for keyword in positive_keywords):
            return "yes"
        return None

    @classmethod
    def _opening_response_contains_issue_detail(cls, text: str) -> bool:
        normalized = (text or "").strip()
        if not normalized:
            return False
        compact = re.sub(r"[，。！？、,.!\s]", "", normalized)
        positive_only_patterns = (
            r"^(对|对的|是|是的|嗯|嗯嗯|哎对|对啊|好|好的|没错|对没错)+$",
        )
        if any(re.fullmatch(pattern, compact) for pattern in positive_only_patterns):
            return False
        if cls._classify_yes_no(normalized) == "yes" and len(compact) <= 6:
            return False
        return True

    @staticmethod
    def _contact_phone_owner(scenario: Scenario) -> str:
        value = scenario.hidden_context.get("contact_phone_owner", "")
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
            return address
        if cls._compact_address_text(address) == cls._compact_address_text(actual_address):
            return actual_address
        candidate_components = extract_address_components(address)
        actual_components = extract_address_components(actual_address)
        if candidate_components.has_precise_detail and components_match(candidate_components, actual_components):
            return actual_address
        return address

    @staticmethod
    def _prepare_address_for_confirmation(text: str) -> str:
        cleaned = (text or "").strip().strip("，,。！？!?")
        prefix_patterns = (
            r"^(好的[，,\s]*)?地址是",
            r"^(好的[，,\s]*)?我家地址是",
            r"^(好的[，,\s]*)?详细地址是",
            r"^(好的[，,\s]*)?我的地址是",
            r"^(好的[，,\s]*)?我现在地址是",
        )
        for pattern in prefix_patterns:
            cleaned = re.sub(pattern, "", cleaned)
        cleaned = re.split(r"[。！？!?]", cleaned, maxsplit=1)[0]
        cleaned = re.split(r"[，,]\s*(?:麻烦|另外|还有|辛苦|谢谢|尽快|催一下|师傅)", cleaned, maxsplit=1)[0]
        return cleaned.strip().strip("，,。！？!?")

    @classmethod
    def _extract_address_candidate_from_denial(
        cls,
        *,
        user_text: str,
        confirmation_address: str,
    ) -> str:
        prepared = cls._prepare_address_for_confirmation(user_text)
        if not prepared:
            return ""

        cleaned = prepared
        cleanup_patterns = (
            r"^(不对|不是这个地址|地址不对|不太对)[，,\s]*",
        )
        for pattern in cleanup_patterns:
            cleaned = re.sub(pattern, "", cleaned)
        cleaned = re.sub(r"^(正确地址是|地址是|是)[，,\s]*", "", cleaned)
        correction_patterns = (
            r"(?:就是|改成|换成|应该是|应为)\s*([^，,。！？!?]+)$",
            r"(?:正确的是|正确地址是)\s*([^，,。！？!?]+)$",
        )
        for pattern in correction_patterns:
            match = re.search(pattern, cleaned)
            if match:
                cleaned = match.group(1)
                break

        cleaned = cleaned.strip("，,。！？!? ")
        normalized = cls._normalize_address_text(cleaned)
        normalized_confirmation = cls._normalize_address_text(confirmation_address)
        if not normalized or normalized == normalized_confirmation:
            return ""
        components = extract_address_components(cleaned)
        if components.has_precise_detail:
            return cleaned
        if cls._address_has_admin_region(cleaned):
            return cleaned
        strong_detail_markers = r"(路|街|大道|巷|弄|胡同|小区|花园|公寓|苑|府|里|村|大厦|中心|广场|城|栋|幢|座|楼|单元|室|号)"
        if re.search(strong_detail_markers, normalized) and cls._address_has_detail_info(cleaned):
            return cleaned
        return ""

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
        normalized_actual = cls._normalize_address_text(actual_address)
        compact_candidate = cls._compact_address_text(candidate)
        compact_actual = cls._compact_address_text(actual_address)
        if candidate == normalized_actual or compact_candidate == compact_actual:
            return True
        candidate_components = extract_address_components(candidate)
        actual_components = extract_address_components(actual_address)
        if (
            candidate_components.has_precise_detail
            and components_match(candidate_components, actual_components)
            and (candidate_components.has_admin_region or candidate_components.has_locality)
            and cls._has_required_address_precision(candidate, actual_address)
        ):
            return True
        return (
            cls._address_has_region_info(candidate)
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
        return components.has_locality and components.has_precise_detail

    @classmethod
    def _has_required_address_precision(cls, candidate: str, actual_address: str) -> bool:
        candidate_components = extract_address_components(candidate)
        actual_components = extract_address_components(actual_address)
        if actual_components.room and not candidate_components.room:
            return False
        if actual_components.unit and not candidate_components.unit:
            return False
        if actual_components.building and not candidate_components.building:
            return False
        return True

    @classmethod
    def _merge_address_candidate(cls, existing: str, new: str) -> str:
        prepared_existing = cls._prepare_address_for_confirmation(existing)
        prepared_new = cls._prepare_address_for_confirmation(new)
        if not prepared_existing:
            return prepared_new
        if not prepared_new:
            return prepared_existing

        normalized_existing = cls._normalize_address_text(prepared_existing)
        normalized_new = cls._normalize_address_text(prepared_new)
        if normalized_existing in normalized_new:
            return prepared_new
        if normalized_new in normalized_existing:
            return prepared_existing

        existing_has_region = cls._address_has_region_info(prepared_existing)
        existing_has_detail = cls._address_has_detail_info(prepared_existing)
        new_has_region = cls._address_has_region_info(prepared_new)
        new_has_detail = cls._address_has_detail_info(prepared_new)
        existing_has_admin_region = cls._address_has_admin_region(prepared_existing)
        new_has_admin_region = cls._address_has_admin_region(prepared_new)

        if new_has_region and new_has_detail:
            return prepared_new

        if not new_has_admin_region:
            detail_merged = cls._merge_address_detail_replacements(prepared_existing, prepared_new)
            if detail_merged != prepared_existing:
                return detail_merged

        if new_has_admin_region and not existing_has_admin_region and existing_has_detail and not new_has_detail:
            return f"{prepared_new}{prepared_existing}"
        if existing_has_admin_region and not new_has_admin_region and new_has_detail and not existing_has_detail:
            return f"{prepared_existing}{prepared_new}"
        return f"{prepared_existing}{prepared_new}"

    @classmethod
    def _merge_address_detail_replacements(cls, existing: str, new: str) -> str:
        merged = existing
        replaced = False
        detail_patterns = (
            r"\d+\s*室",
            r"\d+\s*单元",
            r"\d+\s*(?:号楼|栋|幢|座|楼)",
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
            r"\d+\s*(?:号楼|栋|幢|座|楼).*$",
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
            or normalized.startswith("好的，您是在")
            or normalized in cls._prompt_signatures(cls.ADDRESS_LOCALITY_FOLLOWUP_PROMPT)
            or normalized in cls._prompt_signatures(cls.ADDRESS_BUILDING_FOLLOWUP_PROMPT)
            or normalized.startswith("好的，请您继续说一下小区、楼栋和门牌号")
            or normalized.startswith("请问是几栋几单元几楼几号")
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
    def is_closing_notice_prompt(cls, text: str) -> bool:
        normalized = cls._normalize_prompt_text(text)
        return normalized.startswith("您的工单已受理成功")

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
        return value or "空气能热水器"

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

    def _address_locality_followup_prompt(self) -> str:
        return self._choose_prompt_text(self.ADDRESS_LOCALITY_FOLLOWUP_PROMPT)

    def _address_building_followup_prompt(self) -> str:
        return self._choose_prompt_text(self.ADDRESS_BUILDING_FOLLOWUP_PROMPT)

    def _address_followup_prompt(self, candidate: str, actual_address: str) -> str:
        components = extract_address_components(candidate)
        if not components.district:
            city = self._address_city_for_followup(candidate, actual_address)
            if city:
                return self._address_city_district_followup_prompt(city)
        if components.district and not components.has_locality:
            return self._address_locality_followup_prompt()
        if components.has_locality and not components.has_precise_detail:
            return self._address_building_followup_prompt()
        if components.has_precise_detail and not components.has_locality:
            return self._address_locality_followup_prompt()
        return self._choose_prompt_text(self.ADDRESS_PROMPT)

    def _address_followup_prompt_for_actual(self, *, candidate: str, actual_address: str) -> str:
        components = extract_address_components(candidate)
        if components.has_locality and not self._has_required_address_precision(candidate, actual_address):
            return self._address_building_followup_prompt()
        if components.has_locality and not components.has_precise_detail:
            return self._address_building_followup_prompt()
        if components.has_precise_detail and not components.has_locality:
            return self._address_locality_followup_prompt()
        return self._address_followup_prompt(candidate, actual_address)

    @staticmethod
    def _address_city_for_followup(candidate: str, actual_address: str) -> str:
        candidate_components = extract_address_components(candidate)
        actual_components = extract_address_components(actual_address)
        city = candidate_components.city or actual_components.city
        if city:
            return city if city.endswith("市") else f"{city}市"
        return ""

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
        prompt_config = (
            self.KNOWN_ADDRESS_CONFIRMATION_TEMPLATE
            if use_known_address_prompt
            else self.ADDRESS_CONFIRMATION_TEMPLATE
        )
        return self._with_optional_ok_prefix(
            self._choose_prompt_text(prompt_config, address=address)
        )

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
