from __future__ import annotations

import random
import unittest

from multi_agent_data_synthesis.address_utils import extract_address_components
from multi_agent_data_synthesis.schemas import DialogueTurn, Scenario
from multi_agent_data_synthesis.service_policy import (
    ServiceDialoguePolicy,
    ServiceRuntimeState,
)


def build_scenario(
    *,
    service_known_address: bool = False,
    service_known_address_value: str = "",
    service_known_address_matches_actual: bool = False,
    call_start_time: str = "10:30:00",
) -> Scenario:
    return Scenario.from_dict(
        {
            "scenario_id": "midea_heat_pump_fault_policy_001",
            "product": {
                "brand": "美的",
                "category": "空气能热水器",
                "model": "KF66/200L-MI(E4)",
                "purchase_channel": "京东官方旗舰店",
            },
            "customer": {
                "full_name": "张丽",
                "surname": "张",
                "phone": "13800138001",
                "address": "上海市浦东新区锦绣路1888弄6号1202室",
                "persona": "上班族",
                "speech_style": "表达清楚，偏简短",
            },
            "request": {
                "request_type": "fault",
                "issue": "空气能热水器加热很慢",
                "desired_resolution": "安排售后上门检查",
                "availability": "工作日晚上七点后或者周末全天",
            },
            "call_start_time": call_start_time,
            "hidden_context": {
                "current_call_contactable": False,
                "contact_phone_owner": "爱人",
                "contact_phone": "13900139002",
                "phone_input_attempts_required": 2,
                "phone_input_round_1": "23900139002#",
                "phone_input_round_2": "13900139002#",
                "phone_input_round_3": "13900139002#",
                "service_known_address": service_known_address,
                "service_known_address_value": service_known_address_value,
                "service_known_address_matches_actual": service_known_address_matches_actual,
                "address_input_round_1": "上海市浦东新区锦绣路1888弄6号",
                "address_input_round_2": "上海市浦东新区锦绣路1888弄6号1202室",
            },
            "required_slots": [
                "issue_description",
                "surname",
                "phone",
                "address",
                "product_model",
                "request_type",
                "availability",
            ],
            "max_turns": 20,
            "tags": ["fault"],
        }
    )


def build_installation_scenario(
    *,
    product_arrived: str = "yes",
    category: str = "空气能热水机",
    call_start_time: str = "10:30:00",
) -> Scenario:
    return Scenario.from_dict(
        {
            "scenario_id": "midea_heat_pump_installation_policy_001",
            "product": {
                "brand": "美的",
                "category": category,
                "model": "RSJ-20/300RDN3-C",
                "purchase_channel": "天猫官方旗舰店",
            },
            "customer": {
                "full_name": "王强",
                "surname": "王",
                "phone": "13900139002",
                "address": "杭州市余杭区五常大道666号3幢1单元802室",
                "persona": "说话比较随意，想赶紧把安装的事定下来",
                "speech_style": "说话比较随意，确认流程时会很快接话",
            },
            "request": {
                "request_type": "installation",
                "issue": "新买的空气能热水机已经送到家了，想约安装",
                "desired_resolution": "先登记信息，等后续专人联系安装",
                "availability": "周六上午或者周日下午",
            },
            "call_start_time": call_start_time,
            "hidden_context": {
                "current_call_contactable": True,
                "contact_phone_owner": "本人当前来电",
                "contact_phone": "13900139002",
                "phone_input_attempts_required": 0,
                "phone_input_round_1": "13900139002#",
                "phone_input_round_2": "13900139002#",
                "phone_input_round_3": "13900139002#",
                "service_known_address": False,
                "service_known_address_value": "",
                "service_known_address_matches_actual": False,
                "address_input_round_1": "杭州市余杭区五常大道666号3幢1单元802室",
                "address_input_round_2": "杭州市余杭区五常大道666号3幢1单元802室",
                "product_arrived": product_arrived,
            },
            "required_slots": [
                "issue_description",
                "surname",
                "phone",
                "address",
                "product_model",
                "request_type",
                "availability",
            ],
            "max_turns": 20,
            "tags": ["installation"],
        }
    )


def build_freeform_cli_scenario(
    *,
    request_type: str = "installation",
) -> Scenario:
    return Scenario.from_dict(
        {
            "scenario_id": "manual_cli_freeform_001",
            "product": {
                "brand": "美的",
                "category": "空气能热水机",
                "model": "未知",
                "purchase_channel": "未知",
            },
            "customer": {
                "full_name": "未知",
                "surname": "未知",
                "phone": "未知",
                "address": "未知",
                "persona": "未知",
                "speech_style": "未知",
            },
            "request": {
                "request_type": request_type,
                "issue": "未知",
                "desired_resolution": "未知",
                "availability": "未知",
            },
            "call_start_time": "10:30:00",
            "hidden_context": {
                "interactive_test_freeform": True,
            },
            "required_slots": [
                "issue_description",
                "surname",
                "phone",
                "address",
                "request_type",
            ],
            "max_turns": 20,
            "tags": ["manual-test"],
        }
    )


class ServicePolicyTests(unittest.TestCase):
    def test_weighted_prompt_variants_can_be_selected(self):
        original_prompt = ServiceDialoguePolicy.SURNAME_PROMPT
        ServiceDialoguePolicy.SURNAME_PROMPT = [
            ("请问您贵姓", 0.0),
            ("麻烦问下您姓什么？", 1.0),
        ]
        try:
            policy = ServiceDialoguePolicy(ok_prefix_probability=0.0, rng=random.Random(0))
            state = ServiceRuntimeState()
            scenario = build_scenario()
            transcript = [
                DialogueTurn(
                    speaker="service",
                    text="您好，很高兴为您服务，请问是美的空气能热水器需要维修吗？",
                    round_index=1,
                ),
                DialogueTurn(
                    speaker="user",
                    text="对，是的。我家这个热水器最近水压不太稳定，洗澡的时候花洒出水会变小。",
                    round_index=1,
                ),
            ]
            collected_slots = {
                "issue_description": "",
                "surname": "",
                "phone": "",
                "address": "",
                "product_model": "",
                "request_type": "",
                "availability": "",
                "phone_contactable": "",
                "phone_contact_owner": "",
                "phone_collection_attempts": "",
            }

            result = policy.respond(
                scenario=scenario,
                transcript=transcript,
                collected_slots=collected_slots,
                runtime_state=state,
            )

            self.assertEqual(result.reply, "非常抱歉，给您添麻烦了，我这就安排是否上门维修，麻烦问下您姓什么？")
        finally:
            ServiceDialoguePolicy.SURNAME_PROMPT = original_prompt

    def test_alternative_prompt_variant_still_matches_slot_extraction(self):
        original_prompt = ServiceDialoguePolicy.SURNAME_PROMPT
        ServiceDialoguePolicy.SURNAME_PROMPT = [
            ("请问您贵姓", 1.0),
            ("麻烦问下您姓什么？", 1.0),
        ]
        try:
            policy = ServiceDialoguePolicy()
            state = ServiceRuntimeState()
            scenario = build_scenario()
            transcript = [
                DialogueTurn(
                    speaker="service",
                    text="您好，很高兴为您服务，请问是美的空气能热水器需要维修吗？",
                    round_index=1,
                ),
                DialogueTurn(speaker="user", text="对，家里热水器加热很慢。", round_index=1),
                DialogueTurn(speaker="service", text="好的，麻烦问下您姓什么？", round_index=2),
                DialogueTurn(speaker="user", text="我姓张。", round_index=2),
            ]
            collected_slots = {
                "issue_description": "对，家里热水器加热很慢。",
                "surname": "",
                "phone": "",
                "address": "",
                "product_model": "",
                "request_type": "fault",
                "availability": "",
                "phone_contactable": "",
                "phone_contact_owner": "",
                "phone_collection_attempts": "",
            }

            result = policy.respond(
                scenario=scenario,
                transcript=transcript,
                collected_slots=collected_slots,
                runtime_state=state,
            )

            self.assertEqual(result.slot_updates["surname"], "张")
            self.assertEqual(result.reply, "请问您当前这个来电号码能联系到您吗？")
        finally:
            ServiceDialoguePolicy.SURNAME_PROMPT = original_prompt

    def test_optional_ok_prefix_can_be_disabled(self):
        policy = ServiceDialoguePolicy(ok_prefix_probability=0.0)
        state = ServiceRuntimeState()
        scenario = build_scenario()
        transcript = [
            DialogueTurn(speaker="service", text="您好，很高兴为您服务，请问是美的空气能热水器需要维修吗？", round_index=1),
            DialogueTurn(speaker="user", text="哎对，是的。我家这个热水器最近水压不太稳定，洗澡的时候花洒出水会变小。", round_index=1),
        ]
        collected_slots = {
            "issue_description": "",
            "surname": "",
            "phone": "",
            "address": "",
            "product_model": "",
            "request_type": "",
            "availability": "",
            "phone_contactable": "",
            "phone_contact_owner": "",
            "phone_collection_attempts": "",
        }

        result = policy.respond(
            scenario=scenario,
            transcript=transcript,
            collected_slots=collected_slots,
            runtime_state=state,
        )

        self.assertEqual(result.reply, "非常抱歉，给您添麻烦了，我这就安排是否上门维修，请问您贵姓？")

    def test_opening_prompt_is_fixed(self):
        policy = ServiceDialoguePolicy()

        result = policy.respond(
            scenario=build_scenario(),
            transcript=[],
            collected_slots={
                "issue_description": "",
                "surname": "",
                "phone": "",
                "address": "",
                "product_model": "",
                "request_type": "",
                "availability": "",
            },
            runtime_state=ServiceRuntimeState(),
        )

        self.assertEqual(
            result.reply,
            "您好，很高兴为您服务，请问是美的空气能热水器需要维修吗？",
        )

    def test_opening_colloquial_yes_does_not_count_as_issue_detail(self):
        policy = ServiceDialoguePolicy(ok_prefix_probability=0.0)
        state = ServiceRuntimeState()
        scenario = build_scenario()
        transcript = [
            DialogueTurn(speaker="service", text="您好，很高兴为您服务，请问是美的空气能热水器需要维修吗？", round_index=1),
            DialogueTurn(speaker="user", text="是滴", round_index=1),
        ]
        collected_slots = {
            "issue_description": "",
            "surname": "",
            "phone": "",
            "address": "",
            "product_model": "",
            "request_type": "",
            "availability": "",
            "phone_contactable": "",
            "phone_contact_owner": "",
            "phone_collection_attempts": "",
        }

        result = policy.respond(
            scenario=scenario,
            transcript=transcript,
            collected_slots=collected_slots,
            runtime_state=state,
        )

        self.assertNotIn("issue_description", result.slot_updates)
        self.assertEqual(result.reply, "请问空气能热水器现在是出现了什么问题？")

    def test_opening_intent_forces_model_fallback_when_rule_cannot_match(self):
        def fake_opening_inference(*, user_text: str, user_round_index: int):
            self.assertEqual(user_text, "可不么")
            self.assertEqual(user_round_index, 1)
            return {"intent": "yes"}

        policy = ServiceDialoguePolicy(
            ok_prefix_probability=0.0,
            opening_intent_inference_callback=fake_opening_inference,
        )
        state = ServiceRuntimeState()
        scenario = build_scenario()
        transcript = [
            DialogueTurn(speaker="service", text="您好，很高兴为您服务，请问是美的空气能热水器需要维修吗？", round_index=1),
            DialogueTurn(speaker="user", text="可不么", round_index=1),
        ]
        collected_slots = {
            "issue_description": "",
            "surname": "",
            "phone": "",
            "address": "",
            "product_model": "",
            "request_type": "",
            "availability": "",
            "phone_contactable": "",
            "phone_contact_owner": "",
            "phone_collection_attempts": "",
        }

        result = policy.respond(
            scenario=scenario,
            transcript=transcript,
            collected_slots=collected_slots,
            runtime_state=state,
        )

        self.assertEqual(result.reply, "请问空气能热水器现在是出现了什么问题？")
        self.assertTrue(policy.last_used_model_intent_inference)

    def test_initial_user_utterance_is_config_driven(self):
        policy = ServiceDialoguePolicy()

        self.assertEqual(
            policy.build_initial_user_utterance(build_scenario()),
            "美的空气能热水器需要维修",
        )
        self.assertEqual(
            policy.build_initial_user_utterance(build_installation_scenario(category="燃气热水器")),
            "美的燃气热水器需要安装",
        )

    def test_user_first_opening_uses_fixed_opening_prompt(self):
        policy = ServiceDialoguePolicy()
        state = ServiceRuntimeState()
        scenario = build_scenario()

        result = policy.respond(
            scenario=scenario,
            transcript=[
                DialogueTurn(speaker="user", text="美的空气能热水器需要维修", round_index=1),
            ],
            collected_slots={
                "issue_description": "",
                "surname": "",
                "phone": "",
                "address": "",
                "product_model": "",
                "request_type": "",
                "availability": "",
                "phone_contactable": "",
                "phone_contact_owner": "",
                "phone_collection_attempts": "",
            },
            runtime_state=state,
        )

        self.assertEqual(result.slot_updates["request_type"], "fault")
        self.assertNotIn("issue_description", result.slot_updates)
        self.assertEqual(result.reply, "您好，很高兴为您服务，请问是美的空气能热水器需要维修吗？")

    def test_opening_and_arrival_prompts_use_custom_product_name(self):
        policy = ServiceDialoguePolicy()
        scenario = build_installation_scenario(category="燃气热水器")

        opening_result = policy.respond(
            scenario=scenario,
            transcript=[],
            collected_slots={
                "issue_description": "",
                "surname": "",
                "phone": "",
                "address": "",
                "product_model": "",
                "request_type": "",
                "availability": "",
                "product_arrived": "",
            },
            runtime_state=ServiceRuntimeState(),
        )

        self.assertEqual(
            opening_result.reply,
            "您好，很高兴为您服务，请问是美的燃气热水器需要安装吗？",
        )

        arrival_result = policy.respond(
            scenario=scenario,
            transcript=[
                DialogueTurn(
                    speaker="service",
                    text="您好，很高兴为您服务，请问是美的燃气热水器需要安装吗？",
                    round_index=1,
                ),
                DialogueTurn(speaker="user", text="对，是要装燃气热水器。", round_index=1),
            ],
            collected_slots={
                "issue_description": "",
                "surname": "",
                "phone": "",
                "address": "",
                "product_model": "",
                "request_type": "",
                "availability": "",
                "phone_contactable": "",
                "phone_contact_owner": "",
                "phone_collection_attempts": "",
                "product_arrived": "",
            },
            runtime_state=ServiceRuntimeState(),
        )

        self.assertEqual(arrival_result.slot_updates["request_type"], "installation")
        self.assertEqual(arrival_result.reply, "好的，请问燃气热水器到货了没？")
        self.assertTrue(arrival_result.slot_updates["issue_description"])

    def test_installation_opening_confirmation_asks_arrival_before_collecting_identity_slots(self):
        policy = ServiceDialoguePolicy()
        state = ServiceRuntimeState()
        scenario = build_installation_scenario()
        transcript = [
            DialogueTurn(
                speaker="service",
                text="您好，很高兴为您服务，请问是美的空气能热水机需要安装吗？",
                round_index=1,
            ),
            DialogueTurn(speaker="user", text="对，是要安装。", round_index=1),
        ]
        collected_slots = {
            "issue_description": "",
            "surname": "",
            "phone": "",
            "address": "",
            "product_model": "",
            "request_type": "",
            "availability": "",
            "phone_contactable": "",
            "phone_contact_owner": "",
            "phone_collection_attempts": "",
            "product_arrived": "",
        }

        result = policy.respond(
            scenario=scenario,
            transcript=transcript,
            collected_slots=collected_slots,
            runtime_state=state,
        )

        self.assertEqual(result.reply, "好的，请问空气能热水机到货了没？")
        self.assertEqual(result.slot_updates["request_type"], "installation")
        self.assertFalse(result.slot_updates.get("surname", ""))
        self.assertFalse(result.slot_updates.get("phone", ""))
        self.assertFalse(result.slot_updates.get("address", ""))
        self.assertTrue(state.expected_product_arrival_confirmation)

    def test_contactable_yes_uses_current_call_phone(self):
        policy = ServiceDialoguePolicy()
        state = ServiceRuntimeState(expected_contactable_confirmation=True)
        scenario = build_scenario()
        transcript = [
            DialogueTurn(speaker="service", text="您好，很高兴为您服务，请问是美的空气能热水器需要维修吗？", round_index=1),
            DialogueTurn(speaker="user", text="对，家里热水器加热很慢。", round_index=1),
            DialogueTurn(speaker="service", text="好的，请问您贵姓", round_index=2),
            DialogueTurn(speaker="user", text="我姓张。", round_index=2),
            DialogueTurn(speaker="service", text="请问您当前这个来电号码能联系到您吗？", round_index=3),
            DialogueTurn(speaker="user", text="可以联系到我。", round_index=3),
        ]
        collected_slots = {
            "issue_description": "对，家里热水器加热很慢。",
            "surname": "张",
            "phone": "",
            "address": "",
            "product_model": "",
            "request_type": "fault",
            "availability": "",
            "phone_contactable": "",
            "phone_contact_owner": "",
            "phone_collection_attempts": "",
        }

        result = policy.respond(
            scenario=scenario,
            transcript=transcript,
            collected_slots=collected_slots,
            runtime_state=state,
        )

        self.assertEqual(result.slot_updates["phone"], "13800138001")
        self.assertEqual(result.slot_updates["phone_contactable"], "yes")
        self.assertEqual(
            result.reply,
            "好的，需要登记下您的地址，麻烦您完整的说下省、市、区、乡镇，精确到门牌号。",
        )

    def test_cli_freeform_surname_capture_accepts_full_name(self):
        policy = ServiceDialoguePolicy()
        state = ServiceRuntimeState(product_arrival_checked=True)
        scenario = build_freeform_cli_scenario()
        transcript = [
            DialogueTurn(speaker="service", text="请问您贵姓？", round_index=3),
            DialogueTurn(speaker="user", text="王泽胜", round_index=3),
        ]
        collected_slots = {
            "issue_description": "需要安装空气能热水机。",
            "surname": "",
            "phone": "",
            "address": "",
            "request_type": "installation",
            "phone_contactable": "",
            "phone_contact_owner": "",
            "phone_collection_attempts": "",
            "product_arrived": "yes",
        }

        result = policy.respond(
            scenario=scenario,
            transcript=transcript,
            collected_slots=collected_slots,
            runtime_state=state,
        )

        self.assertEqual(result.slot_updates["surname"], "王")
        self.assertEqual(result.reply, "请问您当前这个来电号码能联系到您吗？")

    def test_cli_freeform_contactable_yes_without_known_phone_collects_digits(self):
        policy = ServiceDialoguePolicy()
        state = ServiceRuntimeState(expected_contactable_confirmation=True)
        scenario = build_freeform_cli_scenario()
        transcript = [
            DialogueTurn(speaker="service", text="请问您当前这个来电号码能联系到您吗？", round_index=4),
            DialogueTurn(speaker="user", text="可以，13800138001", round_index=4),
        ]
        collected_slots = {
            "issue_description": "需要安装空气能热水机。",
            "surname": "王",
            "phone": "",
            "address": "",
            "request_type": "installation",
            "phone_contactable": "",
            "phone_contact_owner": "",
            "phone_collection_attempts": "",
            "product_arrived": "yes",
        }

        result = policy.respond(
            scenario=scenario,
            transcript=transcript,
            collected_slots=collected_slots,
            runtime_state=state,
        )

        self.assertEqual(result.reply, "好的，号码是13800138001，对吗？")
        self.assertEqual(result.slot_updates["phone_contactable"], "yes")
        self.assertEqual(result.slot_updates["phone_contact_owner"], "本人当前来电")
        self.assertTrue(state.expected_phone_number_confirmation)
        self.assertEqual(state.pending_phone_number_confirmation, "13800138001")

    def test_cli_freeform_contactable_yes_uses_mock_current_call_phone(self):
        policy = ServiceDialoguePolicy()
        state = ServiceRuntimeState(expected_contactable_confirmation=True)
        scenario = build_freeform_cli_scenario(request_type="fault")
        scenario.hidden_context["contact_phone"] = "13912345678"
        scenario.hidden_context["contact_phone_owner"] = "本人当前来电"
        transcript = [
            DialogueTurn(speaker="service", text="请问您当前这个来电号码能联系到您吗？", round_index=4),
            DialogueTurn(speaker="user", text="可以的", round_index=4),
        ]
        collected_slots = {
            "issue_description": "热水器不加热，想报修。",
            "surname": "王",
            "phone": "",
            "address": "",
            "request_type": "fault",
            "phone_contactable": "",
            "phone_contact_owner": "",
            "phone_collection_attempts": "",
            "product_arrived": "",
        }

        result = policy.respond(
            scenario=scenario,
            transcript=transcript,
            collected_slots=collected_slots,
            runtime_state=state,
        )

        self.assertEqual(result.slot_updates["phone"], "13912345678")
        self.assertEqual(result.slot_updates["phone_contactable"], "yes")
        self.assertEqual(result.slot_updates["phone_contact_owner"], "本人当前来电")
        self.assertEqual(result.reply, "好的，需要登记下您的地址，麻烦您完整的说下省、市、区、乡镇，精确到门牌号。")
        self.assertFalse(state.awaiting_phone_keypad_input)

    def test_cli_freeform_contactable_switch_to_another_number_counts_as_no(self):
        policy = ServiceDialoguePolicy(ok_prefix_probability=0.0)
        state = ServiceRuntimeState(expected_contactable_confirmation=True)
        scenario = build_freeform_cli_scenario()
        scenario.hidden_context["contact_phone_owner"] = "另一个号码"
        transcript = [
            DialogueTurn(speaker="service", text="请问您当前这个来电号码能联系到您吗？", round_index=4),
            DialogueTurn(speaker="user", text="联系另一个", round_index=4),
        ]
        collected_slots = {
            "issue_description": "需要安装空气能热水机。",
            "surname": "王",
            "phone": "",
            "address": "",
            "request_type": "installation",
            "phone_contactable": "",
            "phone_contact_owner": "",
            "phone_collection_attempts": "",
            "product_arrived": "yes",
        }

        result = policy.respond(
            scenario=scenario,
            transcript=transcript,
            collected_slots=collected_slots,
            runtime_state=state,
        )

        self.assertEqual(result.reply, "请您在拨号盘上输入您的联系方式，并以#号键结束。")
        self.assertEqual(result.slot_updates["phone_contactable"], "no")
        self.assertEqual(result.slot_updates["phone_contact_owner"], "另一个号码")
        self.assertTrue(state.awaiting_phone_keypad_input)

    def test_cli_freeform_contactable_change_one_phrase_counts_as_no(self):
        policy = ServiceDialoguePolicy(ok_prefix_probability=0.0)
        state = ServiceRuntimeState(expected_contactable_confirmation=True)
        scenario = build_freeform_cli_scenario()
        scenario.hidden_context["contact_phone_owner"] = "另一个号码"
        transcript = [
            DialogueTurn(speaker="service", text="请问您当前这个来电号码能联系到您吗？", round_index=4),
            DialogueTurn(speaker="user", text="换一个吧", round_index=4),
        ]
        collected_slots = {
            "issue_description": "需要安装空气能热水机。",
            "surname": "王",
            "phone": "",
            "address": "",
            "request_type": "installation",
            "phone_contactable": "",
            "phone_contact_owner": "",
            "phone_collection_attempts": "",
            "product_arrived": "yes",
        }

        result = policy.respond(
            scenario=scenario,
            transcript=transcript,
            collected_slots=collected_slots,
            runtime_state=state,
        )

        self.assertEqual(result.reply, "请您在拨号盘上输入您的联系方式，并以#号键结束。")
        self.assertEqual(result.slot_updates["phone_contactable"], "no")
        self.assertEqual(result.slot_updates["phone_contact_owner"], "另一个号码")
        self.assertTrue(state.awaiting_phone_keypad_input)

    def test_cli_freeform_contactable_family_member_contact_counts_as_no(self):
        policy = ServiceDialoguePolicy(ok_prefix_probability=0.0)
        state = ServiceRuntimeState(expected_contactable_confirmation=True)
        scenario = build_freeform_cli_scenario()
        scenario.hidden_context["contact_phone_owner"] = "儿子"
        transcript = [
            DialogueTurn(speaker="service", text="请问您当前这个来电号码能联系到您吗？", round_index=4),
            DialogueTurn(speaker="user", text="可能我那时有事，你联系我儿子吧", round_index=4),
        ]
        collected_slots = {
            "issue_description": "需要安装空气能热水机。",
            "surname": "王",
            "phone": "",
            "address": "",
            "request_type": "installation",
            "phone_contactable": "",
            "phone_contact_owner": "",
            "phone_collection_attempts": "",
            "product_arrived": "yes",
        }

        result = policy.respond(
            scenario=scenario,
            transcript=transcript,
            collected_slots=collected_slots,
            runtime_state=state,
        )

        self.assertEqual(result.reply, "请您在拨号盘上输入您的联系方式，并以#号键结束。")
        self.assertEqual(result.slot_updates["phone_contactable"], "no")
        self.assertEqual(result.slot_updates["phone_contact_owner"], "儿子")
        self.assertTrue(state.awaiting_phone_keypad_input)

    def test_cli_freeform_contactable_spouse_owner_short_phrase_counts_as_no(self):
        policy = ServiceDialoguePolicy(ok_prefix_probability=0.0)
        state = ServiceRuntimeState(expected_contactable_confirmation=True)
        scenario = build_freeform_cli_scenario()
        transcript = [
            DialogueTurn(speaker="service", text="请问您当前这个来电号码能联系到您吗？", round_index=4),
            DialogueTurn(speaker="user", text="留一个我老伴的", round_index=4),
        ]
        collected_slots = {
            "issue_description": "需要安装空气能热水机。",
            "surname": "王",
            "phone": "",
            "address": "",
            "request_type": "installation",
            "phone_contactable": "",
            "phone_contact_owner": "",
            "phone_collection_attempts": "",
            "product_arrived": "yes",
        }

        result = policy.respond(
            scenario=scenario,
            transcript=transcript,
            collected_slots=collected_slots,
            runtime_state=state,
        )

        self.assertEqual(result.reply, "请您在拨号盘上输入您的联系方式，并以#号键结束。")
        self.assertEqual(result.slot_updates["phone_contactable"], "no")
        self.assertEqual(result.slot_updates["phone_contact_owner"], "老伴")
        self.assertTrue(state.awaiting_phone_keypad_input)

    def test_cli_freeform_contactable_mixed_can_but_use_spouse_number_still_counts_as_no(self):
        policy = ServiceDialoguePolicy(ok_prefix_probability=0.0)
        state = ServiceRuntimeState(expected_contactable_confirmation=True)
        scenario = build_freeform_cli_scenario()
        transcript = [
            DialogueTurn(speaker="service", text="请问您当前这个来电号码能联系到您吗？", round_index=4),
            DialogueTurn(speaker="user", text="可以是可以，但是我可能之后不在家，你记我老伴的吧", round_index=4),
        ]
        collected_slots = {
            "issue_description": "需要安装空气能热水机。",
            "surname": "王",
            "phone": "",
            "address": "",
            "request_type": "installation",
            "phone_contactable": "",
            "phone_contact_owner": "",
            "phone_collection_attempts": "",
            "product_arrived": "yes",
        }

        result = policy.respond(
            scenario=scenario,
            transcript=transcript,
            collected_slots=collected_slots,
            runtime_state=state,
        )

        self.assertEqual(result.reply, "请您在拨号盘上输入您的联系方式，并以#号键结束。")
        self.assertEqual(result.slot_updates["phone_contactable"], "no")
        self.assertEqual(result.slot_updates["phone_contact_owner"], "老伴")
        self.assertTrue(state.awaiting_phone_keypad_input)

    def test_cli_freeform_contactable_leave_spouse_number_when_not_home_counts_as_no(self):
        policy = ServiceDialoguePolicy(ok_prefix_probability=0.0)
        state = ServiceRuntimeState(expected_contactable_confirmation=True)
        scenario = build_freeform_cli_scenario()
        transcript = [
            DialogueTurn(speaker="service", text="请问您当前这个来电号码能联系到您吗？", round_index=10),
            DialogueTurn(speaker="user", text="留个我老婆的吧，到时候可能我不在家", round_index=10),
        ]
        collected_slots = {
            "issue_description": "需要安装空气能热水机。",
            "surname": "王",
            "phone": "",
            "address": "",
            "request_type": "installation",
            "phone_contactable": "",
            "phone_contact_owner": "",
            "phone_collection_attempts": "",
            "product_arrived": "yes",
        }

        result = policy.respond(
            scenario=scenario,
            transcript=transcript,
            collected_slots=collected_slots,
            runtime_state=state,
        )

        self.assertEqual(result.reply, "请您在拨号盘上输入您的联系方式，并以#号键结束。")
        self.assertEqual(result.slot_updates["phone_contactable"], "no")
        self.assertEqual(result.slot_updates["phone_contact_owner"], "老婆")
        self.assertTrue(state.awaiting_phone_keypad_input)

    def test_cli_freeform_address_confirmation_uses_confirmed_address(self):
        policy = ServiceDialoguePolicy()
        state = ServiceRuntimeState(
            expected_address_confirmation=True,
            product_arrival_checked=True,
            pending_address_confirmation="上海市浦东新区锦绣路1888弄6号1202室",
        )
        scenario = build_freeform_cli_scenario()
        transcript = [
            DialogueTurn(
                speaker="service",
                text="跟您确认一下，地址是上海市浦东新区锦绣路1888弄6号1202室，对吗？",
                round_index=5,
            ),
            DialogueTurn(speaker="user", text="对", round_index=5),
        ]
        collected_slots = {
            "issue_description": "需要安装空气能热水机。",
            "surname": "王",
            "phone": "13800138001",
            "address": "",
            "request_type": "installation",
            "phone_contactable": "yes",
            "phone_contact_owner": "本人当前来电",
            "phone_collection_attempts": "0",
            "product_arrived": "yes",
        }

        result = policy.respond(
            scenario=scenario,
            transcript=transcript,
            collected_slots=collected_slots,
            runtime_state=state,
        )

        self.assertEqual(result.slot_updates["address"], "上海市浦东新区锦绣路1888弄6号1202室")
        self.assertFalse(state.expected_address_confirmation)

    def test_asking_phone_sets_confirmation_state(self):
        policy = ServiceDialoguePolicy()
        state = ServiceRuntimeState()
        scenario = build_scenario()
        transcript = [
            DialogueTurn(speaker="service", text="您好，很高兴为您服务，请问是美的空气能热水器需要维修吗？", round_index=1),
            DialogueTurn(speaker="user", text="对，家里热水器加热很慢。", round_index=1),
            DialogueTurn(speaker="service", text="好的，请问您贵姓", round_index=2),
            DialogueTurn(speaker="user", text="我姓张。", round_index=2),
        ]
        collected_slots = {
            "issue_description": "对，家里热水器加热很慢。",
            "surname": "张",
            "phone": "",
            "address": "",
            "product_model": "",
            "request_type": "fault",
            "availability": "",
            "phone_contactable": "",
            "phone_contact_owner": "",
            "phone_collection_attempts": "",
        }

        result = policy.respond(
            scenario=scenario,
            transcript=transcript,
            collected_slots=collected_slots,
            runtime_state=state,
        )

        self.assertEqual(result.reply, "请问您当前这个来电号码能联系到您吗？")
        self.assertTrue(state.expected_contactable_confirmation)

    def test_fault_opening_with_issue_description_moves_to_surname(self):
        policy = ServiceDialoguePolicy()
        state = ServiceRuntimeState()
        scenario = build_scenario()
        transcript = [
            DialogueTurn(speaker="service", text="您好，很高兴为您服务，请问是美的空气能热水器需要维修吗？", round_index=1),
            DialogueTurn(
                speaker="user",
                text="哎对，是的。我家这个热水器最近水压不太稳定，洗澡的时候花洒出水会变小，想让师傅上门看看。",
                round_index=1,
            ),
        ]
        collected_slots = {
            "issue_description": "",
            "surname": "",
            "phone": "",
            "address": "",
            "product_model": "",
            "request_type": "",
            "availability": "",
            "phone_contactable": "",
            "phone_contact_owner": "",
            "phone_collection_attempts": "",
        }

        result = policy.respond(
            scenario=scenario,
            transcript=transcript,
            collected_slots=collected_slots,
            runtime_state=state,
        )

        self.assertEqual(
            result.slot_updates["issue_description"],
            "哎对，是的。我家这个热水器最近水压不太稳定，洗澡的时候花洒出水会变小，想让师傅上门看看。",
        )
        self.assertEqual(result.slot_updates["request_type"], "fault")
        self.assertEqual(result.reply, "非常抱歉，给您添麻烦了，我这就安排是否上门维修，请问您贵姓？")

    def test_fault_opening_with_issue_description_uses_model_summary_even_when_rule_matches(self):
        def fake_issue_extraction(*, user_text: str, user_round_index: int):
            self.assertEqual(
                user_text,
                "哎对，是的。我家这个热水器最近水压不太稳定，洗澡的时候花洒出水会变小，想让师傅上门看看。",
            )
            self.assertEqual(user_round_index, 1)
            return {"issue_description": "热水器水压不稳定，洗澡时花洒出水变小"}

        policy = ServiceDialoguePolicy(
            issue_description_extraction_callback=fake_issue_extraction,
        )
        state = ServiceRuntimeState()
        scenario = build_scenario()
        transcript = [
            DialogueTurn(speaker="service", text="您好，很高兴为您服务，请问是美的空气能热水器需要维修吗？", round_index=1),
            DialogueTurn(
                speaker="user",
                text="哎对，是的。我家这个热水器最近水压不太稳定，洗澡的时候花洒出水会变小，想让师傅上门看看。",
                round_index=1,
            ),
        ]
        collected_slots = {
            "issue_description": "",
            "surname": "",
            "phone": "",
            "address": "",
            "product_model": "",
            "request_type": "",
            "availability": "",
            "phone_contactable": "",
            "phone_contact_owner": "",
            "phone_collection_attempts": "",
        }

        result = policy.respond(
            scenario=scenario,
            transcript=transcript,
            collected_slots=collected_slots,
            runtime_state=state,
        )

        self.assertEqual(
            result.slot_updates["issue_description"],
            "热水器水压不稳定，洗澡时花洒出水变小",
        )
        self.assertTrue(policy.last_used_model_intent_inference)

    def test_fault_opening_without_issue_description_asks_fixed_followup(self):
        policy = ServiceDialoguePolicy()
        state = ServiceRuntimeState()
        scenario = build_scenario()
        transcript = [
            DialogueTurn(speaker="service", text="您好，很高兴为您服务，请问是美的空气能热水器需要维修吗？", round_index=1),
            DialogueTurn(speaker="user", text="哎对，是的。", round_index=1),
        ]
        collected_slots = {
            "issue_description": "",
            "surname": "",
            "phone": "",
            "address": "",
            "product_model": "",
            "request_type": "",
            "availability": "",
            "phone_contactable": "",
            "phone_contact_owner": "",
            "phone_collection_attempts": "",
        }

        result = policy.respond(
            scenario=scenario,
            transcript=transcript,
            collected_slots=collected_slots,
            runtime_state=state,
        )

        self.assertNotIn("issue_description", result.slot_updates)
        self.assertEqual(result.slot_updates["request_type"], "fault")
        self.assertEqual(result.reply, "好的，请问空气能热水器现在是出现了什么问题？")

    def test_fault_opening_greeting_only_does_not_fill_issue_description(self):
        policy = ServiceDialoguePolicy()
        state = ServiceRuntimeState()
        scenario = build_scenario()
        transcript = [
            DialogueTurn(speaker="service", text="您好，很高兴为您服务，请问是美的空气能热水器需要维修吗？", round_index=1),
            DialogueTurn(speaker="user", text="你好", round_index=1),
        ]
        collected_slots = {
            "issue_description": "",
            "surname": "",
            "phone": "",
            "address": "",
            "product_model": "",
            "request_type": "",
            "availability": "",
            "phone_contactable": "",
            "phone_contact_owner": "",
            "phone_collection_attempts": "",
        }

        result = policy.respond(
            scenario=scenario,
            transcript=transcript,
            collected_slots=collected_slots,
            runtime_state=state,
        )

        self.assertNotIn("issue_description", result.slot_updates)
        self.assertEqual(result.reply, "好的，请问空气能热水器现在是出现了什么问题？")

    def test_initial_freeform_user_turn_does_not_fill_issue_description(self):
        policy = ServiceDialoguePolicy(ok_prefix_probability=0.0)
        state = ServiceRuntimeState()
        scenario = build_freeform_cli_scenario(request_type="fault")
        transcript = [
            DialogueTurn(speaker="user", text="侬好", round_index=1),
        ]
        collected_slots = {
            "issue_description": "",
            "surname": "",
            "phone": "",
            "address": "",
            "request_type": "",
            "phone_contactable": "",
            "phone_contact_owner": "",
            "phone_collection_attempts": "",
            "product_arrived": "",
        }

        result = policy.respond(
            scenario=scenario,
            transcript=transcript,
            collected_slots=collected_slots,
            runtime_state=state,
        )

        self.assertNotIn("issue_description", result.slot_updates)
        self.assertEqual(result.slot_updates["request_type"], "fault")
        self.assertEqual(result.reply, "您好，很高兴为您服务，请问是美的空气能热水机需要维修吗？")

    def test_cli_freeform_with_product_routing_plan_runs_routing_before_fault_question(self):
        policy = ServiceDialoguePolicy(ok_prefix_probability=0.0)
        state = ServiceRuntimeState()
        scenario = build_freeform_cli_scenario(request_type="fault")
        scenario.hidden_context["product_routing_plan"] = {
            "enabled": True,
            "result": "家用 + 可直接确认机型",
            "trace": ["entry.unknown"],
            "summary": "entry.unknown -> 家用 + 可直接确认机型",
            "steps": [
                {
                    "prompt_key": "brand_or_series",
                    "prompt": "请问您的空气能是什么品牌或系列呢？",
                    "answer_key": "entry.unknown",
                    "answer_value": "不知道品牌或系列",
                    "answer_instruction": "自然表达自己不知道品牌或系列。",
                }
            ],
        }
        transcript = [
            DialogueTurn(
                speaker="service",
                text="您好，很高兴为您服务，请问是美的空气能热水机需要维修吗？",
                round_index=1,
            ),
            DialogueTurn(speaker="user", text="是的", round_index=1),
        ]
        collected_slots = {
            "issue_description": "",
            "surname": "",
            "phone": "",
            "address": "",
            "request_type": "",
            "phone_contactable": "",
            "phone_contact_owner": "",
            "phone_collection_attempts": "",
            "product_arrived": "",
        }

        result = policy.respond(
            scenario=scenario,
            transcript=transcript,
            collected_slots=collected_slots,
            runtime_state=state,
        )

        self.assertEqual(result.reply, "请问您的空气能是什么品牌或系列呢？")
        self.assertTrue(state.expected_product_routing_response)

    def test_cli_freeform_fault_issue_detail_then_product_routing_starts_with_apology(self):
        policy = ServiceDialoguePolicy(ok_prefix_probability=0.0)
        state = ServiceRuntimeState()
        scenario = build_freeform_cli_scenario(request_type="fault")
        scenario.hidden_context["product_routing_plan"] = {
            "enabled": True,
            "result": "家用 + 可直接确认机型",
            "trace": ["entry.unknown"],
            "summary": "entry.unknown -> 家用 + 可直接确认机型",
            "steps": [
                {
                    "prompt_key": "brand_or_series",
                    "prompt": "请问您的空气能是什么品牌或系列呢？",
                    "answer_key": "entry.unknown",
                    "answer_value": "不知道品牌或系列",
                    "answer_instruction": "自然表达自己不知道品牌或系列。",
                }
            ],
        }
        transcript = [
            DialogueTurn(
                speaker="service",
                text="您好，很高兴为您服务，请问是美的空气能热水机需要维修吗？",
                round_index=1,
            ),
            DialogueTurn(speaker="user", text="是的，热水器不加热，想报修。", round_index=1),
        ]
        collected_slots = {
            "issue_description": "",
            "surname": "",
            "phone": "",
            "address": "",
            "request_type": "",
            "phone_contactable": "",
            "phone_contact_owner": "",
            "phone_collection_attempts": "",
            "product_arrived": "",
        }

        result = policy.respond(
            scenario=scenario,
            transcript=transcript,
            collected_slots=collected_slots,
            runtime_state=state,
        )

        self.assertEqual(
            result.reply,
            "非常抱歉，给您添麻烦了，我这就安排是否上门维修，请问您的空气能是什么品牌或系列呢？",
        )
        self.assertEqual(result.slot_updates["issue_description"], "是的，热水器不加热，想报修。")
        self.assertTrue(state.expected_product_routing_response)

    def test_cli_freeform_fault_issue_detail_uses_model_extraction_for_clean_description(self):
        def fake_opening_inference(*, user_text: str, user_round_index: int):
            self.assertEqual(user_text, "是滴是滴，出水太少，洗的不爽")
            self.assertEqual(user_round_index, 2)
            return {"intent": "issue_detail"}

        def fake_issue_extraction(*, user_text: str, user_round_index: int):
            self.assertEqual(user_text, "是滴是滴，出水太少，洗的不爽")
            self.assertEqual(user_round_index, 2)
            return {"issue_description": "出水太少，洗澡体验差"}

        policy = ServiceDialoguePolicy(
            ok_prefix_probability=0.0,
            opening_intent_inference_callback=fake_opening_inference,
            issue_description_extraction_callback=fake_issue_extraction,
        )
        state = ServiceRuntimeState()
        scenario = build_freeform_cli_scenario(request_type="fault")
        scenario.hidden_context["product_routing_plan"] = {
            "enabled": True,
            "result": "楼宇 + 可直接确认机型",
            "trace": ["entry.unknown"],
            "summary": "entry.unknown -> 楼宇 + 可直接确认机型",
            "steps": [
                {
                    "prompt_key": "brand_or_series",
                    "prompt": "请问您的空气能是什么品牌或系列呢？",
                    "answer_key": "entry.unknown",
                    "answer_value": "不知道品牌或系列",
                    "answer_instruction": "自然表达自己不知道品牌或系列。",
                }
            ],
        }
        transcript = [
            DialogueTurn(
                speaker="service",
                text="您好，很高兴为您服务，请问是美的空气能热水机需要维修吗？",
                round_index=1,
            ),
            DialogueTurn(speaker="user", text="是滴是滴，出水太少，洗的不爽", round_index=2),
        ]
        collected_slots = {
            "issue_description": "",
            "surname": "",
            "phone": "",
            "address": "",
            "request_type": "",
            "phone_contactable": "",
            "phone_contact_owner": "",
            "phone_collection_attempts": "",
            "product_arrived": "",
        }

        result = policy.respond(
            scenario=scenario,
            transcript=transcript,
            collected_slots=collected_slots,
            runtime_state=state,
        )

        self.assertEqual(result.slot_updates["issue_description"], "出水太少，洗澡体验差")
        self.assertEqual(
            result.reply,
            "非常抱歉，给您添麻烦了，我这就安排是否上门维修，请问您的空气能是什么品牌或系列呢？",
        )

    def test_cli_freeform_fault_issue_detail_falls_back_to_raw_text_when_extraction_is_empty(self):
        def fake_opening_inference(*, user_text: str, user_round_index: int):
            return {"intent": "issue_detail"}

        def fake_issue_extraction(*, user_text: str, user_round_index: int):
            return {"issue_description": ""}

        policy = ServiceDialoguePolicy(
            ok_prefix_probability=0.0,
            opening_intent_inference_callback=fake_opening_inference,
            issue_description_extraction_callback=fake_issue_extraction,
        )
        state = ServiceRuntimeState()
        scenario = build_freeform_cli_scenario(request_type="fault")
        transcript = [
            DialogueTurn(
                speaker="service",
                text="您好，很高兴为您服务，请问是美的空气能热水机需要维修吗？",
                round_index=1,
            ),
            DialogueTurn(speaker="user", text="出水太少，洗的不爽", round_index=2),
        ]
        collected_slots = {
            "issue_description": "",
            "surname": "",
            "phone": "",
            "address": "",
            "request_type": "",
            "phone_contactable": "",
            "phone_contact_owner": "",
            "phone_collection_attempts": "",
            "product_arrived": "",
        }

        result = policy.respond(
            scenario=scenario,
            transcript=transcript,
            collected_slots=collected_slots,
            runtime_state=state,
        )

        self.assertEqual(result.slot_updates["issue_description"], "出水太少，洗的不爽")

    def test_cli_freeform_fault_opening_forces_model_judgement_before_routing(self):
        callback_calls: list[tuple[str, int]] = []

        def fake_opening_inference(*, user_text: str, user_round_index: int):
            callback_calls.append((user_text, user_round_index))
            return {"intent": "yes"}

        policy = ServiceDialoguePolicy(
            ok_prefix_probability=0.0,
            opening_intent_inference_callback=fake_opening_inference,
        )
        state = ServiceRuntimeState()
        scenario = build_freeform_cli_scenario(request_type="fault")
        scenario.hidden_context["product_routing_plan"] = {
            "enabled": True,
            "result": "家用 + 可直接确认机型",
            "trace": ["entry.unknown"],
            "summary": "entry.unknown -> 家用 + 可直接确认机型",
            "steps": [
                {
                    "prompt_key": "brand_or_series",
                    "prompt": "请问您的空气能是什么品牌或系列呢？",
                    "answer_key": "entry.unknown",
                    "answer_value": "不知道品牌或系列",
                    "answer_instruction": "自然表达自己不知道品牌或系列。",
                }
            ],
        }
        transcript = [
            DialogueTurn(
                speaker="service",
                text="您好，很高兴为您服务，请问是美的空气能热水机需要维修吗？",
                round_index=1,
            ),
            DialogueTurn(speaker="user", text="是滴是滴", round_index=2),
        ]
        collected_slots = {
            "issue_description": "",
            "surname": "",
            "phone": "",
            "address": "",
            "request_type": "",
            "phone_contactable": "",
            "phone_contact_owner": "",
            "phone_collection_attempts": "",
            "product_arrived": "",
        }

        result = policy.respond(
            scenario=scenario,
            transcript=transcript,
            collected_slots=collected_slots,
            runtime_state=state,
        )

        self.assertEqual(callback_calls, [("是滴是滴", 2)])
        self.assertTrue(policy.last_used_model_intent_inference)
        self.assertNotIn("issue_description", result.slot_updates)
        self.assertEqual(result.reply, "请问您的空气能是什么品牌或系列呢？")
        self.assertTrue(state.expected_product_routing_response)

    def test_cli_freeform_product_routing_asks_property_year_after_property_bundle(self):
        policy = ServiceDialoguePolicy(ok_prefix_probability=0.0)
        state = ServiceRuntimeState(
            expected_product_routing_response=True,
            product_routing_step_index=0,
            product_routing_observed_trace=["entry.unknown", "purpose.unknown", "scene.yes"],
        )
        scenario = build_freeform_cli_scenario(request_type="fault")
        scenario.hidden_context["product_routing_plan"] = {
            "enabled": True,
            "result": "家用 + 可直接确认机型",
            "trace": ["purchase.self_buy"],
            "summary": "purchase.self_buy -> 家用 + 可直接确认机型",
            "steps": [
                {
                    "prompt_key": "purchase_or_property",
                    "prompt": "请问是您自己购买的，还是楼盘配套赠送的呢？",
                    "answer_key": "purchase.self_buy",
                    "answer_value": "自己购买",
                    "answer_instruction": "自然表达机器是自己购买的。",
                }
            ],
        }

        result = policy.respond(
            scenario=scenario,
            transcript=[
                DialogueTurn(speaker="service", text="请问是您自己购买的，还是楼盘配套赠送的呢？", round_index=5),
                DialogueTurn(speaker="user", text="当时买房送的吧", round_index=6),
            ],
            collected_slots={
                "issue_description": "",
                "surname": "",
                "phone": "",
                "address": "",
                "request_type": "",
                "phone_contactable": "",
                "phone_contact_owner": "",
                "phone_collection_attempts": "",
                "product_arrived": "",
            },
            runtime_state=state,
        )

        self.assertEqual(result.reply, "请问是21年之前的楼盘，还是之后的呢？")
        self.assertEqual(
            state.product_routing_observed_trace,
            ["entry.unknown", "purpose.unknown", "scene.yes", "purchase.property_bundle"],
        )

    def test_cli_freeform_product_routing_maps_short_gift_reply_to_property_year(self):
        policy = ServiceDialoguePolicy(ok_prefix_probability=0.0)
        state = ServiceRuntimeState(
            expected_product_routing_response=True,
            product_routing_step_index=0,
            product_routing_observed_trace=["entry.unknown", "purpose.water", "capacity.below_threshold"],
        )
        scenario = build_freeform_cli_scenario(request_type="fault")
        scenario.hidden_context["product_routing_plan"] = {
            "enabled": True,
            "result": "家用 + 可直接确认机型",
            "trace": ["purchase.self_buy"],
            "summary": "purchase.self_buy -> 家用 + 可直接确认机型",
            "steps": [
                {
                    "prompt_key": "purchase_or_property",
                    "prompt": "请问是您自己购买的，还是楼盘配套赠送的呢？",
                    "answer_key": "purchase.self_buy",
                    "answer_value": "自己购买",
                    "answer_instruction": "自然表达机器是自己购买的。",
                }
            ],
        }

        result = policy.respond(
            scenario=scenario,
            transcript=[
                DialogueTurn(speaker="service", text="请问是您自己购买的，还是楼盘配套赠送的呢？", round_index=5),
                DialogueTurn(speaker="user", text="送的", round_index=6),
            ],
            collected_slots={
                "issue_description": "",
                "surname": "",
                "phone": "",
                "address": "",
                "request_type": "",
                "phone_contactable": "",
                "phone_contact_owner": "",
                "phone_collection_attempts": "",
                "product_arrived": "",
            },
            runtime_state=state,
        )

        self.assertEqual(result.reply, "请问是21年之前的楼盘，还是之后的呢？")
        self.assertEqual(
            state.product_routing_observed_trace,
            ["entry.unknown", "purpose.water", "capacity.below_threshold", "purchase.property_bundle"],
        )

    def test_cli_freeform_product_routing_maps_baigei_reply_to_property_year(self):
        policy = ServiceDialoguePolicy(ok_prefix_probability=0.0)
        state = ServiceRuntimeState(
            expected_product_routing_response=True,
            product_routing_step_index=0,
            product_routing_observed_trace=["entry.unknown", "purpose.water", "capacity.below_threshold"],
        )
        scenario = build_freeform_cli_scenario(request_type="fault")
        scenario.hidden_context["product_routing_plan"] = {
            "enabled": True,
            "result": "家用 + 可直接确认机型",
            "trace": ["purchase.self_buy"],
            "summary": "purchase.self_buy -> 家用 + 可直接确认机型",
            "steps": [
                {
                    "prompt_key": "purchase_or_property",
                    "prompt": "请问是您自己购买的，还是楼盘配套赠送的呢？",
                    "answer_key": "purchase.self_buy",
                    "answer_value": "自己购买",
                    "answer_instruction": "自然表达机器是自己购买的。",
                }
            ],
        }

        result = policy.respond(
            scenario=scenario,
            transcript=[
                DialogueTurn(speaker="service", text="请问是您自己购买的，还是楼盘配套赠送的呢？", round_index=5),
                DialogueTurn(speaker="user", text="白给的", round_index=6),
            ],
            collected_slots={
                "issue_description": "",
                "surname": "",
                "phone": "",
                "address": "",
                "request_type": "",
                "phone_contactable": "",
                "phone_contact_owner": "",
                "phone_collection_attempts": "",
                "product_arrived": "",
            },
            runtime_state=state,
        )

        self.assertEqual(result.reply, "请问是21年之前的楼盘，还是之后的呢？")
        self.assertEqual(
            state.product_routing_observed_trace,
            ["entry.unknown", "purpose.water", "capacity.below_threshold", "purchase.property_bundle"],
        )

    def test_product_routing_uses_model_fallback_when_local_rule_cannot_classify(self):
        def fake_routing_inference(*, prompt_key: str, user_text: str):
            self.assertEqual(prompt_key, "purchase_or_property")
            self.assertEqual(user_text, "房子交付时候就有")
            return {
                "prompt_key": "purchase_or_property",
                "answer_key": "purchase.property_bundle",
            }

        policy = ServiceDialoguePolicy(
            ok_prefix_probability=0.0,
            product_routing_intent_inference_callback=fake_routing_inference,
        )
        state = ServiceRuntimeState(
            expected_product_routing_response=True,
            product_routing_step_index=0,
            product_routing_observed_trace=["entry.unknown", "purpose.unknown", "scene.yes"],
        )
        scenario = build_freeform_cli_scenario(request_type="fault")
        scenario.hidden_context["product_routing_plan"] = {
            "enabled": True,
            "result": "家用 + 可直接确认机型",
            "trace": ["purchase.self_buy"],
            "summary": "purchase.self_buy -> 家用 + 可直接确认机型",
            "steps": [
                {
                    "prompt_key": "purchase_or_property",
                    "prompt": "请问是您自己购买的，还是楼盘配套赠送的呢？",
                    "answer_key": "purchase.self_buy",
                    "answer_value": "自己购买",
                    "answer_instruction": "自然表达机器是自己购买的。",
                }
            ],
        }

        result = policy.respond(
            scenario=scenario,
            transcript=[
                DialogueTurn(speaker="service", text="请问是您自己购买的，还是楼盘配套赠送的呢？", round_index=5),
                DialogueTurn(speaker="user", text="房子交付时候就有", round_index=6),
            ],
            collected_slots={
                "issue_description": "",
                "surname": "",
                "phone": "",
                "address": "",
                "request_type": "",
                "phone_contactable": "",
                "phone_contact_owner": "",
                "phone_collection_attempts": "",
                "product_arrived": "",
            },
            runtime_state=state,
        )

        self.assertEqual(result.reply, "请问是21年之前的楼盘，还是之后的呢？")

    def test_product_routing_falls_back_to_unknown_branch_when_model_returns_invalid_answer_key_for_prompt(self):
        def fake_routing_inference(*, prompt_key: str, user_text: str):
            self.assertEqual(prompt_key, "capacity_or_hp")
            self.assertEqual(user_text, "这个我真没概念")
            return {
                "prompt_key": "capacity_or_hp",
                "answer_key": "purchase.self_buy",
            }

        policy = ServiceDialoguePolicy(
            ok_prefix_probability=0.0,
            product_routing_intent_inference_callback=fake_routing_inference,
        )
        state = ServiceRuntimeState(
            expected_product_routing_response=True,
            product_routing_step_index=0,
            product_routing_observed_trace=["entry.unknown", "purpose.water"],
        )
        scenario = build_freeform_cli_scenario(request_type="fault")
        scenario.hidden_context["product_routing_plan"] = {
            "enabled": True,
            "result": "家用 + 可直接确认机型",
            "trace": ["capacity.unknown"],
            "summary": "capacity.unknown -> 家用 + 可直接确认机型",
            "steps": [
                {
                    "prompt_key": "capacity_or_hp",
                    "prompt": "请问机器是多少升的，或者多少匹数的呢？",
                    "answer_key": "capacity.unknown",
                    "answer_value": "不清楚容量或匹数",
                    "answer_instruction": "自然表达自己不清楚容量或匹数。",
                }
            ],
        }

        result = policy.respond(
            scenario=scenario,
            transcript=[
                DialogueTurn(speaker="service", text="请问机器是多少升的，或者多少匹数的呢？", round_index=5),
                DialogueTurn(speaker="user", text="这个我真没概念", round_index=6),
            ],
            collected_slots={
                "issue_description": "",
                "surname": "",
                "phone": "",
                "address": "",
                "request_type": "",
                "phone_contactable": "",
                "phone_contact_owner": "",
                "phone_collection_attempts": "",
                "product_arrived": "",
            },
            runtime_state=state,
        )

        self.assertEqual(result.reply, "请问是在家庭、别墅、公寓或理发店使用的吗？")
        self.assertEqual(state.product_routing_observed_trace, ["entry.unknown", "purpose.water", "capacity.unknown"])
        self.assertTrue(state.expected_product_routing_response)
        self.assertFalse(policy.last_used_model_intent_inference)

    def test_product_routing_reasks_when_prompt_has_no_unknown_branch_and_model_returns_empty(self):
        def fake_routing_inference(*, prompt_key: str, user_text: str):
            self.assertEqual(prompt_key, "property_year")
            self.assertEqual(user_text, "这个我真说不好")
            return {
                "prompt_key": "property_year",
                "answer_key": "",
            }

        policy = ServiceDialoguePolicy(
            ok_prefix_probability=0.0,
            product_routing_intent_inference_callback=fake_routing_inference,
        )
        state = ServiceRuntimeState(
            expected_product_routing_response=True,
            product_routing_step_index=0,
            product_routing_observed_trace=["entry.unknown", "purpose.unknown", "scene.yes", "purchase.property_bundle"],
        )
        scenario = build_freeform_cli_scenario(request_type="fault")
        scenario.hidden_context["product_routing_plan"] = {
            "enabled": True,
            "result": "家用 + 可直接确认机型",
            "trace": ["property_year.before_2021"],
            "summary": "property_year.before_2021 -> 家用 + 可直接确认机型",
            "steps": [
                {
                    "prompt_key": "property_year",
                    "prompt": "请问是21年之前的楼盘，还是之后的呢？",
                    "answer_key": "property_year.before_2021",
                    "answer_value": "21年之前的楼盘",
                    "answer_instruction": "自然表达楼盘属于 2021 年之前。",
                }
            ],
        }

        result = policy.respond(
            scenario=scenario,
            transcript=[
                DialogueTurn(speaker="service", text="请问是21年之前的楼盘，还是之后的呢？", round_index=6),
                DialogueTurn(speaker="user", text="这个我真说不好", round_index=7),
            ],
            collected_slots={
                "issue_description": "",
                "surname": "",
                "phone": "",
                "address": "",
                "request_type": "",
                "phone_contactable": "",
                "phone_contact_owner": "",
                "phone_collection_attempts": "",
                "product_arrived": "",
            },
            runtime_state=state,
        )

        self.assertEqual(result.reply, "请问是21年之前的楼盘，还是之后的呢？")
        self.assertEqual(
            state.product_routing_observed_trace,
            ["entry.unknown", "purpose.unknown", "scene.yes", "purchase.property_bundle"],
        )
        self.assertTrue(state.expected_product_routing_response)
        self.assertFalse(policy.last_used_model_intent_inference)

    def test_address_confirmation_uses_model_fallback_when_rule_cannot_classify(self):
        def fake_confirmation_inference(*, prompt_kind: str, user_text: str):
            self.assertEqual(prompt_kind, "address_confirmation")
            self.assertEqual(user_text, "嗯就是你刚说那个地方")
            return {"intent": "yes"}

        policy = ServiceDialoguePolicy(
            confirmation_intent_inference_callback=fake_confirmation_inference,
        )
        state = ServiceRuntimeState(
            expected_address_confirmation=True,
            pending_address_confirmation="上海市浦东新区锦绣路1888弄6号1202室",
        )
        scenario = build_freeform_cli_scenario()

        result = policy.respond(
            scenario=scenario,
            transcript=[
                DialogueTurn(
                    speaker="service",
                    text="跟您确认一下，地址是上海市浦东新区锦绣路1888弄6号1202室，对吗？",
                    round_index=5,
                ),
                DialogueTurn(
                    speaker="user",
                    text="嗯就是你刚说那个地方",
                    round_index=5,
                ),
            ],
            collected_slots={
                "issue_description": "需要安装空气能热水机。",
                "surname": "王",
                "phone": "13800138001",
                "address": "",
                "request_type": "installation",
                "phone_contactable": "yes",
                "phone_contact_owner": "本人当前来电",
                "phone_collection_attempts": "0",
                "product_arrived": "yes",
            },
            runtime_state=state,
        )

        self.assertEqual(result.slot_updates["address"], "上海市浦东新区锦绣路1888弄6号1202室")
        self.assertFalse(state.expected_address_confirmation)

    def test_contactable_uses_model_fallback_when_positive_prefix_is_overridden_by_later_switch_request(self):
        def fake_contact_inference(*, user_text: str, user_round_index: int):
            self.assertEqual(user_text, "可以，不过还是打备用号码吧")
            self.assertEqual(user_round_index, 4)
            return {"intent": "no"}

        policy = ServiceDialoguePolicy(
            ok_prefix_probability=0.0,
            contact_intent_inference_callback=fake_contact_inference,
        )
        state = ServiceRuntimeState(expected_contactable_confirmation=True)
        scenario = build_freeform_cli_scenario()
        scenario.hidden_context["contact_phone_owner"] = "另一个号码"

        result = policy.respond(
            scenario=scenario,
            transcript=[
                DialogueTurn(speaker="service", text="请问您当前这个来电号码能联系到您吗？", round_index=4),
                DialogueTurn(speaker="user", text="可以，不过还是打备用号码吧", round_index=4),
            ],
            collected_slots={
                "issue_description": "需要安装空气能热水机。",
                "surname": "王",
                "phone": "",
                "address": "",
                "request_type": "installation",
                "phone_contactable": "",
                "phone_contact_owner": "",
                "phone_collection_attempts": "",
                "product_arrived": "yes",
            },
            runtime_state=state,
        )

        self.assertEqual(result.reply, "请您在拨号盘上输入您的联系方式，并以#号键结束。")
        self.assertEqual(result.slot_updates["phone_contactable"], "no")
        self.assertEqual(result.slot_updates["phone_contact_owner"], "另一个号码")
        self.assertTrue(state.awaiting_phone_keypad_input)
        self.assertTrue(policy.last_used_model_intent_inference)

    def test_fault_issue_followup_response_adds_apology_before_next_collection(self):
        policy = ServiceDialoguePolicy()
        state = ServiceRuntimeState()
        scenario = build_scenario()
        transcript = [
            DialogueTurn(speaker="service", text="好的，很高兴为您服务，请问空气能热水器现在是出现了什么问题？", round_index=2),
            DialogueTurn(speaker="user", text="就是最近加热特别慢，洗澡的时候水还忽冷忽热。", round_index=2),
        ]
        collected_slots = {
            "issue_description": "",
            "surname": "",
            "phone": "",
            "address": "",
            "product_model": "",
            "request_type": "fault",
            "availability": "",
            "phone_contactable": "",
            "phone_contact_owner": "",
            "phone_collection_attempts": "",
        }

        result = policy.respond(
            scenario=scenario,
            transcript=transcript,
            collected_slots=collected_slots,
            runtime_state=state,
        )

        self.assertEqual(result.slot_updates["issue_description"], "就是最近加热特别慢，洗澡的时候水还忽冷忽热。")
        self.assertEqual(result.reply, "非常抱歉，给您添麻烦了，我这就安排是否上门维修，请问您贵姓？")

    def test_fault_issue_followup_response_uses_model_extraction(self):
        def fake_issue_extraction(*, user_text: str, user_round_index: int):
            self.assertEqual(user_text, "是滴是滴，出水太少，洗的不爽")
            self.assertEqual(user_round_index, 2)
            return {"issue_description": "出水太少，洗澡体验差"}

        policy = ServiceDialoguePolicy(
            issue_description_extraction_callback=fake_issue_extraction,
        )
        state = ServiceRuntimeState()
        scenario = build_freeform_cli_scenario(request_type="fault")
        transcript = [
            DialogueTurn(speaker="service", text="好的，请问空气能热水机现在是出现了什么问题？", round_index=2),
            DialogueTurn(speaker="user", text="是滴是滴，出水太少，洗的不爽", round_index=2),
        ]
        collected_slots = {
            "issue_description": "",
            "surname": "",
            "phone": "",
            "address": "",
            "request_type": "fault",
            "phone_contactable": "",
            "phone_contact_owner": "",
            "phone_collection_attempts": "",
            "product_arrived": "",
        }

        result = policy.respond(
            scenario=scenario,
            transcript=transcript,
            collected_slots=collected_slots,
            runtime_state=state,
        )

        self.assertEqual(result.slot_updates["issue_description"], "出水太少，洗澡体验差")
        self.assertTrue(policy.last_used_model_intent_inference)

    def test_surname_answer_after_apology_prefixed_prompt_is_not_asked_again(self):
        policy = ServiceDialoguePolicy()
        state = ServiceRuntimeState()
        scenario = build_scenario()
        transcript = [
            DialogueTurn(
                speaker="service",
                text="非常抱歉，给您添麻烦了，我这就安排是否上门维修，请问您贵姓",
                round_index=2,
            ),
            DialogueTurn(speaker="user", text="姓孙。", round_index=2),
        ]
        scenario_data = scenario.to_dict()
        scenario_data["customer"]["surname"] = "孙"
        scenario = Scenario.from_dict(scenario_data)
        collected_slots = {
            "issue_description": "就是最近加热特别慢，洗澡的时候水还忽冷忽热。",
            "surname": "",
            "phone": "",
            "address": "",
            "product_model": "",
            "request_type": "fault",
            "availability": "",
            "phone_contactable": "",
            "phone_contact_owner": "",
            "phone_collection_attempts": "",
        }

        result = policy.respond(
            scenario=scenario,
            transcript=transcript,
            collected_slots=collected_slots,
            runtime_state=state,
        )

        self.assertEqual(result.slot_updates["surname"], "孙")
        self.assertEqual(result.reply, "请问您当前这个来电号码能联系到您吗？")

    def test_invalid_then_valid_keypad_input_then_confirmation(self):
        policy = ServiceDialoguePolicy()
        state = ServiceRuntimeState(awaiting_phone_keypad_input=True, phone_input_attempts=0)
        scenario = build_scenario()
        collected_slots = {
            "issue_description": "对，家里热水器加热很慢。",
            "surname": "张",
            "phone": "",
            "address": "",
            "product_model": "",
            "request_type": "fault",
            "availability": "",
            "phone_contactable": "no",
            "phone_contact_owner": "爱人",
            "phone_collection_attempts": "",
        }

        first_transcript = [
            DialogueTurn(speaker="service", text="好的，请您在拨号盘上输入您的联系方式，并以#号键结束", round_index=4),
            DialogueTurn(speaker="user", text="23900139002#", round_index=4),
        ]
        first_result = policy.respond(
            scenario=scenario,
            transcript=first_transcript,
            collected_slots=collected_slots,
            runtime_state=state,
        )
        self.assertEqual(
            first_result.reply,
            "您输入的号码有误，请重新在拨号盘上输入您的联系方式，并以#号键结束。",
        )
        self.assertEqual(first_result.slot_updates["phone_collection_attempts"], "1")

        second_transcript = [
            DialogueTurn(speaker="service", text="您输入的号码有误，请重新在拨号盘上输入您的联系方式，并以#号键结束", round_index=5),
            DialogueTurn(speaker="user", text="13900139002#", round_index=5),
        ]
        second_result = policy.respond(
            scenario=scenario,
            transcript=second_transcript,
            collected_slots=collected_slots,
            runtime_state=state,
        )
        self.assertEqual(second_result.slot_updates["phone_collection_attempts"], "2")
        self.assertEqual(second_result.slot_updates.get("phone", ""), "")
        self.assertEqual(second_result.reply, "好的，号码是13900139002，对吗？")
        self.assertTrue(state.expected_phone_number_confirmation)

    def test_confirmed_keypad_phone_moves_to_next_slot(self):
        policy = ServiceDialoguePolicy()
        state = ServiceRuntimeState(
            expected_phone_number_confirmation=True,
            phone_input_attempts=2,
            pending_phone_number_confirmation="13900139002",
        )
        scenario = build_scenario()
        transcript = [
            DialogueTurn(speaker="service", text="好的，号码是13900139002，对吗？", round_index=6),
            DialogueTurn(speaker="user", text="对，就是这个。", round_index=6),
        ]
        collected_slots = {
            "issue_description": "对，家里热水器加热很慢。",
            "surname": "张",
            "phone": "",
            "address": "",
            "product_model": "",
            "request_type": "fault",
            "availability": "",
            "phone_contactable": "no",
            "phone_contact_owner": "爱人",
            "phone_collection_attempts": "2",
        }

        result = policy.respond(
            scenario=scenario,
            transcript=transcript,
            collected_slots=collected_slots,
            runtime_state=state,
        )

        self.assertEqual(result.slot_updates["phone"], "13900139002")
        self.assertEqual(result.reply, "好的，需要登记下您的地址，麻烦您完整的说下省、市、区、乡镇，精确到门牌号。")

    def test_third_keypad_attempt_can_succeed(self):
        policy = ServiceDialoguePolicy()
        state = ServiceRuntimeState(awaiting_phone_keypad_input=True, phone_input_attempts=2)
        scenario = build_scenario()
        transcript = [
            DialogueTurn(speaker="service", text="您输入的号码有误，请重新在拨号盘上输入您的联系方式，并以#号键结束", round_index=6),
            DialogueTurn(speaker="user", text="13900139002#", round_index=6),
        ]
        collected_slots = {
            "issue_description": "对，家里热水器加热很慢。",
            "surname": "张",
            "phone": "",
            "address": "",
            "product_model": "",
            "request_type": "fault",
            "availability": "",
            "phone_contactable": "no",
            "phone_contact_owner": "爱人",
            "phone_collection_attempts": "2",
        }

        result = policy.respond(
            scenario=scenario,
            transcript=transcript,
            collected_slots=collected_slots,
            runtime_state=state,
        )

        self.assertEqual(result.reply, "好的，号码是13900139002，对吗？")
        self.assertEqual(result.slot_updates["phone_collection_attempts"], "3")

    def test_known_address_confirmation_yes_completes_address(self):
        policy = ServiceDialoguePolicy()
        state = ServiceRuntimeState(expected_address_confirmation=True)
        scenario = build_scenario(
            service_known_address=True,
            service_known_address_value="上海市浦东新区锦绣路1888弄6号1202室",
            service_known_address_matches_actual=True,
        )
        transcript = [
            DialogueTurn(speaker="service", text="好的，您的地址是上海市浦东新区锦绣路1888弄6号1202室，对吗？", round_index=5),
            DialogueTurn(speaker="user", text="对，就是这个地址。", round_index=5),
        ]
        collected_slots = {
            "issue_description": "对，家里热水器加热很慢。",
            "surname": "张",
            "phone": "13800138001",
            "address": "",
            "product_model": "",
            "request_type": "fault",
            "availability": "",
            "phone_contactable": "yes",
            "phone_contact_owner": "本人当前来电",
            "phone_collection_attempts": "0",
        }

        result = policy.respond(
            scenario=scenario,
            transcript=transcript,
            collected_slots=collected_slots,
            runtime_state=state,
        )

        self.assertEqual(result.slot_updates["address"], "上海市浦东新区锦绣路1888弄6号1202室")
        self.assertEqual(
            result.reply,
            "好的，您的工单已受理成功，2小时内服务人员会电话联系，预约具体上门时间。",
        )

    def test_known_address_confirmation_room_only_correction_starts_confirmation(self):
        policy = ServiceDialoguePolicy()
        state = ServiceRuntimeState(expected_address_confirmation=True)
        scenario = build_scenario(
            service_known_address=True,
            service_known_address_value="上海市浦东新区锦绣路1888弄6号1201室",
            service_known_address_matches_actual=False,
        )
        transcript = [
            DialogueTurn(speaker="service", text="好的，您的地址是上海市浦东新区锦绣路1888弄6号1201室，对吗？", round_index=5),
            DialogueTurn(speaker="user", text="不太对，不用写1201室，就是1202室。", round_index=5),
        ]
        collected_slots = {
            "issue_description": "对，家里热水器加热很慢。",
            "surname": "张",
            "phone": "13800138001",
            "address": "",
            "product_model": "",
            "request_type": "fault",
            "availability": "",
            "phone_contactable": "yes",
            "phone_contact_owner": "本人当前来电",
            "phone_collection_attempts": "0",
        }

        result = policy.respond(
            scenario=scenario,
            transcript=transcript,
            collected_slots=collected_slots,
            runtime_state=state,
        )

        self.assertEqual(
            result.reply,
            "好的，跟您确认一下，地址是上海市浦东新区锦绣路1888弄6号1202室，对吗？",
        )
        self.assertTrue(state.expected_address_confirmation)
        self.assertEqual(state.pending_address_confirmation, "上海市浦东新区锦绣路1888弄6号1202室")

    def test_known_address_confirmation_no_with_direct_correction_starts_confirmation(self):
        policy = ServiceDialoguePolicy()
        state = ServiceRuntimeState(expected_address_confirmation=True)
        scenario = build_scenario(
            service_known_address=True,
            service_known_address_value="云南省昆明市盘龙区北京路1000号山水花园3栋801室",
            service_known_address_matches_actual=False,
        )
        scenario_data = scenario.to_dict()
        scenario_data["customer"]["address"] = "云南省昆明市盘龙区北京路1000号山水花园3栋802室"
        scenario = Scenario.from_dict(scenario_data)
        transcript = [
            DialogueTurn(
                speaker="service",
                text="好的，您的地址是云南省昆明市盘龙区北京路1000号山水花园3栋801室，对吗？",
                round_index=5,
            ),
            DialogueTurn(
                speaker="user",
                text="不对，正确地址是云南省昆明市盘龙区北京路1000号山水花园3栋802室。",
                round_index=5,
            ),
        ]
        collected_slots = {
            "issue_description": "对，家里热水器加热很慢。",
            "surname": "张",
            "phone": "13800138001",
            "address": "",
            "product_model": "",
            "request_type": "fault",
            "availability": "",
            "phone_contactable": "yes",
            "phone_contact_owner": "本人当前来电",
            "phone_collection_attempts": "0",
        }

        result = policy.respond(
            scenario=scenario,
            transcript=transcript,
            collected_slots=collected_slots,
            runtime_state=state,
        )

        self.assertEqual(
            result.reply,
            "好的，跟您确认一下，地址是云南省昆明市盘龙区北京路1000号山水花园3栋802室，对吗？",
        )
        self.assertTrue(state.expected_address_confirmation)

    def test_known_address_confirmation_no_with_rural_group_correction_starts_confirmation(self):
        policy = ServiceDialoguePolicy()
        state = ServiceRuntimeState(expected_address_confirmation=True)
        scenario_data = build_installation_scenario().to_dict()
        scenario_data["customer"]["address"] = "湖南省岳阳市岳阳县新开镇柴桥村四组25号"
        scenario_data["hidden_context"]["service_known_address"] = True
        scenario_data["hidden_context"]["service_known_address_value"] = "湖南省岳阳市岳阳县新开镇滨江花园四组25号"
        scenario_data["hidden_context"]["service_known_address_matches_actual"] = False
        scenario = Scenario.from_dict(scenario_data)
        collected_slots = {
            "issue_description": "想约安装。",
            "surname": "陈",
            "phone": "13800138001",
            "address": "",
            "product_model": "",
            "request_type": "installation",
            "availability": "",
            "phone_contactable": "yes",
            "phone_contact_owner": "本人当前来电",
            "phone_collection_attempts": "0",
            "product_arrived": "yes",
        }

        result = policy.respond(
            scenario=scenario,
            transcript=[
                DialogueTurn(
                    speaker="service",
                    text="好的，您的地址是湖南省岳阳市岳阳县新开镇滨江花园四组25号，对吗？",
                    round_index=5,
                ),
                DialogueTurn(
                    speaker="user",
                    text="不对，地址不对。是新开镇柴桥村四组25号。",
                    round_index=6,
                ),
            ],
            collected_slots=collected_slots,
            runtime_state=state,
        )

        self.assertEqual(
            result.reply,
            "好的，跟您确认一下，地址是湖南省岳阳市岳阳县新开镇柴桥村四组25号，对吗？",
        )
        self.assertTrue(state.expected_address_confirmation)
        self.assertEqual(state.pending_address_confirmation, "湖南省岳阳市岳阳县新开镇柴桥村四组25号")

    def test_known_address_confirmation_no_with_house_number_locality_correction_starts_confirmation(self):
        policy = ServiceDialoguePolicy()
        state = ServiceRuntimeState(expected_address_confirmation=True)
        scenario_data = build_installation_scenario().to_dict()
        scenario_data["customer"]["address"] = "广东省佛山市南海区桂城街道康怡苑62号"
        scenario_data["hidden_context"]["service_known_address"] = True
        scenario_data["hidden_context"]["service_known_address_value"] = "广东省佛山市南海区桂城街道金色家园62号"
        scenario_data["hidden_context"]["service_known_address_matches_actual"] = False
        scenario = Scenario.from_dict(scenario_data)
        collected_slots = {
            "issue_description": "想约安装。",
            "surname": "王",
            "phone": "13900139002",
            "address": "",
            "product_model": "",
            "request_type": "installation",
            "availability": "",
            "phone_contactable": "yes",
            "phone_contact_owner": "本人当前来电",
            "phone_collection_attempts": "0",
            "product_arrived": "yes",
        }

        result = policy.respond(
            scenario=scenario,
            transcript=[
                DialogueTurn(
                    speaker="service",
                    text="好的，您的地址是广东省佛山市南海区桂城街道金色家园62号，对吗？",
                    round_index=5,
                ),
                DialogueTurn(
                    speaker="user",
                    text="不对，地址不对。是桂城街道康怡苑62号。",
                    round_index=6,
                ),
            ],
            collected_slots=collected_slots,
            runtime_state=state,
        )

        self.assertEqual(
            result.reply,
            "好的，跟您确认一下，地址是广东省佛山市南海区桂城街道康怡苑62号，对吗？",
        )
        self.assertTrue(state.expected_address_confirmation)
        self.assertEqual(state.pending_address_confirmation, "广东省佛山市南海区桂城街道康怡苑62号")

    def test_known_address_confirmation_does_not_inherit_old_building_when_user_rewrites_locality(self):
        policy = ServiceDialoguePolicy()
        state = ServiceRuntimeState(
            expected_address_confirmation=True,
            pending_address_confirmation="广东省佛山市南海区幸福花园A栋502室",
        )
        scenario_data = build_installation_scenario().to_dict()
        scenario_data["customer"]["address"] = "广东省佛山市南海区桂城街人民医院小区502室"
        scenario_data["hidden_context"]["service_known_address"] = True
        scenario_data["hidden_context"]["service_known_address_value"] = "广东省佛山市南海区幸福花园A栋502室"
        scenario_data["hidden_context"]["service_known_address_matches_actual"] = False
        scenario = Scenario.from_dict(scenario_data)
        collected_slots = {
            "issue_description": "想约安装。",
            "surname": "王",
            "phone": "13900139002",
            "address": "",
            "product_model": "",
            "request_type": "installation",
            "availability": "",
            "phone_contactable": "yes",
            "phone_contact_owner": "本人当前来电",
            "phone_collection_attempts": "0",
            "product_arrived": "yes",
        }

        result = policy.respond(
            scenario=scenario,
            transcript=[
                DialogueTurn(
                    speaker="service",
                    text="您的地址是广东省佛山市南海区幸福花园A栋502室，对吗？",
                    round_index=7,
                ),
                DialogueTurn(
                    speaker="user",
                    text="不是这个地址，应该是桂城街人民医院小区502室。",
                    round_index=8,
                ),
            ],
            collected_slots=collected_slots,
            runtime_state=state,
        )

        self.assertEqual(
            result.reply,
            "好的，跟您确认一下，地址是广东省佛山市南海区桂城街人民医院小区502室，对吗？",
        )
        self.assertEqual(
            state.pending_address_confirmation,
            "广东省佛山市南海区桂城街人民医院小区502室",
        )
        self.assertNotIn("A栋", state.pending_address_confirmation)

    def test_known_address_confirmation_locality_rewrite_clears_old_suffix_and_full_followup_confirms(self):
        policy = ServiceDialoguePolicy()
        state = ServiceRuntimeState(
            expected_address_confirmation=True,
            pending_address_confirmation="甘肃省兰州市城关区五泉街道幸福花园6号楼1单元402室",
        )
        scenario_data = build_scenario(
            service_known_address=True,
            service_known_address_value="甘肃省兰州市城关区五泉街道幸福花园6号楼1单元402室",
            service_known_address_matches_actual=False,
        ).to_dict()
        scenario_data["customer"]["address"] = "甘肃省兰州市城关区五泉街道福寿小区8号楼2单元1202室"
        scenario = Scenario.from_dict(scenario_data)
        collected_slots = {
            "issue_description": "热水器加热慢。",
            "surname": "张",
            "phone": "13800138001",
            "address": "",
            "product_model": "",
            "request_type": "fault",
            "availability": "",
            "phone_contactable": "yes",
            "phone_contact_owner": "本人当前来电",
            "phone_collection_attempts": "0",
        }

        first_result = policy.respond(
            scenario=scenario,
            transcript=[
                DialogueTurn(
                    speaker="service",
                    text="您的地址是甘肃省兰州市城关区五泉街道幸福花园6号楼1单元402室，对吗？",
                    round_index=7,
                ),
                DialogueTurn(
                    speaker="user",
                    text="不对，应该是福寿小区，不是幸福花园。",
                    round_index=8,
                ),
            ],
            collected_slots=collected_slots,
            runtime_state=state,
        )

        self.assertEqual(first_result.reply, "请问是几栋几单元几楼几号呢？")
        self.assertTrue(state.awaiting_full_address)
        self.assertEqual(state.partial_address_candidate, "甘肃省兰州市城关区五泉街道福寿小区")

        second_result = policy.respond(
            scenario=scenario,
            transcript=[
                DialogueTurn(speaker="service", text="请问是几栋几单元几楼几号呢？", round_index=8),
                DialogueTurn(
                    speaker="user",
                    text="应该是五泉街道福寿小区8号楼2单元1202室。",
                    round_index=9,
                ),
            ],
            collected_slots=collected_slots,
            runtime_state=state,
        )

        self.assertEqual(
            second_result.reply,
            "好的，跟您确认一下，地址是甘肃省兰州市城关区五泉街道福寿小区8号楼2单元1202室，对吗？",
        )
        self.assertTrue(state.expected_address_confirmation)
        self.assertEqual(
            state.pending_address_confirmation,
            "甘肃省兰州市城关区五泉街道福寿小区8号楼2单元1202室",
        )

    def test_known_address_confirmation_with_district_only_correction_can_confirm_directly(self):
        policy = ServiceDialoguePolicy(ok_prefix_probability=0.0)
        state = ServiceRuntimeState(
            expected_address_confirmation=True,
            pending_address_confirmation="甘肃省兰州市城关区雁南路福源佳园小区4号楼2单元",
        )
        scenario_data = build_scenario(
            service_known_address=True,
            service_known_address_value="甘肃省兰州市城关区雁南路福源佳园小区4号楼2单元",
            service_known_address_matches_actual=False,
        ).to_dict()
        scenario_data["customer"]["full_name"] = "钟离志刚"
        scenario_data["customer"]["surname"] = "钟离"
        scenario_data["customer"]["phone"] = "17829663412"
        scenario_data["customer"]["address"] = "甘肃省兰州市七里河区雁南路福源佳园小区4号楼2单元"
        scenario_data["hidden_context"]["address_confirmation_no_reply"] = (
            "不是，应该是七里河区雁南路福源佳园小区4号楼2单元。"
        )
        scenario = Scenario.from_dict(scenario_data)
        collected_slots = {
            "issue_description": "最近热水器出水温度时冷时热。",
            "surname": "钟离",
            "phone": "17829663412",
            "address": "",
            "product_model": "",
            "request_type": "fault",
            "availability": "",
            "phone_contactable": "yes",
            "phone_contact_owner": "本人当前来电",
            "phone_collection_attempts": "0",
        }

        result = policy.respond(
            scenario=scenario,
            transcript=[
                DialogueTurn(
                    speaker="service",
                    text="好的，您的地址是甘肃省兰州市城关区雁南路福源佳园小区4号楼2单元，对吗？",
                    round_index=8,
                ),
                DialogueTurn(
                    speaker="user",
                    text="不是，应该是七里河区雁南路福源佳园小区4号楼2单元。",
                    round_index=9,
                ),
            ],
            collected_slots=collected_slots,
            runtime_state=state,
        )

        self.assertEqual(
            result.reply,
            "跟您确认一下，地址是甘肃省兰州市七里河区雁南路福源佳园小区4号楼2单元，对吗？",
        )
        self.assertTrue(state.expected_address_confirmation)
        self.assertFalse(state.awaiting_full_address)
        self.assertEqual(
            state.pending_address_confirmation,
            "甘肃省兰州市七里河区雁南路福源佳园小区4号楼2单元",
        )

    def test_known_address_confirmation_with_autonomous_region_rural_address_can_confirm(self):
        policy = ServiceDialoguePolicy(ok_prefix_probability=0.0)
        state = ServiceRuntimeState(
            expected_address_confirmation=True,
            pending_address_confirmation="广西柳州市鱼峰区通挽镇锦绣苑第五组",
        )
        scenario_data = build_scenario(
            service_known_address=True,
            service_known_address_value="广西柳州市鱼峰区通挽镇锦绣苑第五组",
            service_known_address_matches_actual=False,
        ).to_dict()
        scenario_data["customer"]["address"] = "广西壮族自治区来宾市武宣县通挽镇石坡村第五组17号"
        scenario = Scenario.from_dict(scenario_data)
        collected_slots = {
            "issue_description": "热水器加热慢。",
            "surname": "张",
            "phone": "13800138001",
            "address": "",
            "product_model": "",
            "request_type": "fault",
            "availability": "",
            "phone_contactable": "yes",
            "phone_contact_owner": "本人当前来电",
            "phone_collection_attempts": "0",
        }

        first_result = policy.respond(
            scenario=scenario,
            transcript=[
                DialogueTurn(
                    speaker="service",
                    text="您的地址是广西柳州市鱼峰区通挽镇锦绣苑第五组，对吗？",
                    round_index=5,
                ),
                DialogueTurn(
                    speaker="user",
                    text="不对，应该不是这个地址，我家是广西壮族自治区来宾市武宣县通挽镇石坡村第五组。",
                    round_index=6,
                ),
            ],
            collected_slots=collected_slots,
            runtime_state=state,
        )

        self.assertEqual(first_result.reply, "好的，请您提供一下详细的地址，具体到门牌号。")
        self.assertEqual(
            state.partial_address_candidate,
            "广西壮族自治区来宾市武宣县通挽镇石坡村第五组",
        )

        second_result = policy.respond(
            scenario=scenario,
            transcript=[
                DialogueTurn(
                    speaker="service",
                    text="好的，请您提供一下详细的地址，具体到门牌号。",
                    round_index=6,
                ),
                DialogueTurn(
                    speaker="user",
                    text="我家是广西壮族自治区来宾市武宣县通挽镇石坡村第五组17号。",
                    round_index=7,
                ),
            ],
            collected_slots=collected_slots,
            runtime_state=state,
        )

        self.assertEqual(
            second_result.reply,
            "跟您确认一下，地址是广西壮族自治区来宾市武宣县通挽镇石坡村第五组17号，对吗？",
        )
        self.assertTrue(state.expected_address_confirmation)
        self.assertEqual(
            state.pending_address_confirmation,
            "广西壮族自治区来宾市武宣县通挽镇石坡村第五组17号",
        )

    def test_known_address_confirmation_can_use_model_fallback_to_extract_correction(self):
        callback_calls: list[dict[str, str]] = []

        def fake_address_inference(**kwargs):
            callback_calls.append(kwargs)
            return {
                "address_candidate": "新开镇柴桥村四组25号",
                "granularity": "locality_with_detail",
            }

        policy = ServiceDialoguePolicy(address_inference_callback=fake_address_inference)
        state = ServiceRuntimeState(expected_address_confirmation=True)
        scenario_data = build_installation_scenario().to_dict()
        scenario_data["customer"]["address"] = "湖南省岳阳市岳阳县新开镇柴桥村四组25号"
        scenario_data["hidden_context"]["service_known_address"] = True
        scenario_data["hidden_context"]["service_known_address_value"] = "湖南省岳阳市岳阳县新开镇滨江花园四组25号"
        scenario_data["hidden_context"]["service_known_address_matches_actual"] = False
        scenario = Scenario.from_dict(scenario_data)
        collected_slots = {
            "issue_description": "想约安装。",
            "surname": "陈",
            "phone": "13800138001",
            "address": "",
            "product_model": "",
            "request_type": "installation",
            "availability": "",
            "phone_contactable": "yes",
            "phone_contact_owner": "本人当前来电",
            "phone_collection_attempts": "0",
            "product_arrived": "yes",
        }

        result = policy.respond(
            scenario=scenario,
            transcript=[
                DialogueTurn(
                    speaker="service",
                    text="好的，您的地址是湖南省岳阳市岳阳县新开镇滨江花园四组25号，对吗？",
                    round_index=5,
                ),
                DialogueTurn(
                    speaker="user",
                    text="不对，前面小区说错了，我说的是老家那个地址。",
                    round_index=6,
                ),
            ],
            collected_slots=collected_slots,
            runtime_state=state,
        )

        self.assertEqual(len(callback_calls), 1)
        self.assertEqual(
            result.reply,
            "好的，跟您确认一下，地址是湖南省岳阳市岳阳县新开镇柴桥村四组25号，对吗？",
        )
        self.assertTrue(state.expected_address_confirmation)

    def test_known_address_confirmation_no_with_generic_denial_restarts_full_address_collection(self):
        policy = ServiceDialoguePolicy()
        state = ServiceRuntimeState(expected_address_confirmation=True)
        scenario_data = build_scenario(
            service_known_address=True,
            service_known_address_value="北京市朝阳区五星街道幸福小区5号楼2单元305室",
            service_known_address_matches_actual=False,
        ).to_dict()
        scenario_data["customer"]["address"] = "北京市朝阳区五星街道幸福小区5号楼2单元302室"
        scenario = Scenario.from_dict(scenario_data)
        transcript = [
            DialogueTurn(
                speaker="service",
                text="您的地址是北京市朝阳区五星街道幸福小区5号楼2单元305室，对吗？",
                round_index=5,
            ),
            DialogueTurn(
                speaker="user",
                text="不对，地址不对。",
                round_index=6,
            ),
        ]
        collected_slots = {
            "issue_description": "热水器加热慢。",
            "surname": "张",
            "phone": "13800138001",
            "address": "",
            "product_model": "",
            "request_type": "fault",
            "availability": "",
            "phone_contactable": "yes",
            "phone_contact_owner": "本人当前来电",
            "phone_collection_attempts": "0",
        }

        result = policy.respond(
            scenario=scenario,
            transcript=transcript,
            collected_slots=collected_slots,
            runtime_state=state,
        )

        self.assertEqual(result.reply, "好的，需要登记下您的地址，麻烦您完整的说下省、市、区、乡镇，精确到门牌号。")
        self.assertTrue(state.awaiting_full_address)
        self.assertEqual(state.partial_address_candidate, "")

    def test_known_address_confirmation_ignores_room_suffix_only_denial_and_confirms_canonical_merged_address(self):
        policy = ServiceDialoguePolicy()
        state = ServiceRuntimeState(expected_address_confirmation=True)
        scenario_data = build_scenario(
            service_known_address=True,
            service_known_address_value="广东省佛山市南海区桂城街道金域蓝湾小区9栋302",
            service_known_address_matches_actual=False,
        ).to_dict()
        scenario_data["customer"]["address"] = "广东省佛山市南海区桂城街道金域蓝湾小区8栋302室"
        scenario = Scenario.from_dict(scenario_data)
        collected_slots = {
            "issue_description": "热水器加热慢。",
            "surname": "张",
            "phone": "13800138001",
            "address": "",
            "product_model": "",
            "request_type": "fault",
            "availability": "",
            "phone_contactable": "yes",
            "phone_contact_owner": "本人当前来电",
            "phone_collection_attempts": "0",
        }

        first_result = policy.respond(
            scenario=scenario,
            transcript=[
                DialogueTurn(
                    speaker="service",
                    text="好的，您的地址是广东省佛山市南海区桂城街道金域蓝湾小区9栋302，对吗？",
                    round_index=7,
                ),
                DialogueTurn(speaker="user", text="不是，正确的是302室。", round_index=8),
            ],
            collected_slots=collected_slots,
            runtime_state=state,
        )

        self.assertEqual(first_result.reply, "好的，需要登记下您的地址，麻烦您完整的说下省、市、区、乡镇，精确到门牌号。")
        self.assertTrue(state.awaiting_full_address)
        self.assertEqual(state.partial_address_candidate, "")

        second_result = policy.respond(
            scenario=scenario,
            transcript=[
                DialogueTurn(
                    speaker="service",
                    text="好的，需要登记下您的地址，麻烦您完整的说下省、市、区、乡镇，精确到门牌号。",
                    round_index=8,
                ),
                DialogueTurn(
                    speaker="user",
                    text="哦，小区是金域蓝湾，楼栋是8栋，房间是302室。",
                    round_index=9,
                ),
            ],
            collected_slots=collected_slots,
            runtime_state=state,
        )

        self.assertEqual(
            second_result.reply,
            "好的，跟您确认一下，地址是广东省佛山市南海区桂城街道金域蓝湾小区8栋302室，对吗？",
        )
        self.assertEqual(
            state.pending_address_confirmation,
            "广东省佛山市南海区桂城街道金域蓝湾小区8栋302室",
        )

    def test_known_address_confirmation_no_with_cross_city_correction_starts_confirmation(self):
        policy = ServiceDialoguePolicy()
        state = ServiceRuntimeState(expected_address_confirmation=True)
        scenario_data = build_scenario(
            service_known_address=True,
            service_known_address_value="河南省郑州市金水区北环路天伦雅苑15号楼2单元505室",
            service_known_address_matches_actual=False,
        ).to_dict()
        scenario_data["customer"]["address"] = "山东省青岛市市南区香港东路银海花园3号楼1203室"
        scenario = Scenario.from_dict(scenario_data)
        transcript = [
            DialogueTurn(
                speaker="service",
                text="好的，您的地址是河南省郑州市金水区北环路天伦雅苑15号楼2单元505室，对吗？",
                round_index=5,
            ),
            DialogueTurn(
                speaker="user",
                text="不对，我现在地址是山东省青岛市市南区香港东路银海花园3号楼1203室。",
                round_index=5,
            ),
        ]
        collected_slots = {
            "issue_description": "对，家里热水器加热很慢。",
            "surname": "张",
            "phone": "13800138001",
            "address": "",
            "product_model": "",
            "request_type": "fault",
            "availability": "",
            "phone_contactable": "yes",
            "phone_contact_owner": "本人当前来电",
            "phone_collection_attempts": "0",
        }

        result = policy.respond(
            scenario=scenario,
            transcript=transcript,
            collected_slots=collected_slots,
            runtime_state=state,
        )

        self.assertEqual(
            result.reply,
            "好的，跟您确认一下，地址是山东省青岛市市南区香港东路银海花园3号楼1203室，对吗？",
        )
        self.assertTrue(state.expected_address_confirmation)

    def test_address_followup_after_partial_input(self):
        policy = ServiceDialoguePolicy()
        state = ServiceRuntimeState(awaiting_full_address=True, address_input_attempts=0)
        scenario = build_scenario()
        collected_slots = {
            "issue_description": "对，家里热水器加热很慢。",
            "surname": "张",
            "phone": "13800138001",
            "address": "",
            "product_model": "",
            "request_type": "fault",
            "availability": "",
            "phone_contactable": "yes",
            "phone_contact_owner": "本人当前来电",
            "phone_collection_attempts": "0",
        }

        first_result = policy.respond(
            scenario=scenario,
            transcript=[
                DialogueTurn(speaker="service", text="好的，需要登记下您的地址，麻烦您完整的说下省、市、区、乡镇，精确到门牌号。", round_index=5),
                DialogueTurn(speaker="user", text="上海市浦东新区锦绣路1888弄6号", round_index=5),
            ],
            collected_slots=collected_slots,
            runtime_state=state,
        )
        self.assertEqual(
            first_result.reply,
            "请问是几栋几单元几楼几号呢？",
        )

    def test_address_followup_merges_prefix_and_confirms_most_complete_address(self):
        policy = ServiceDialoguePolicy()
        state = ServiceRuntimeState(
            awaiting_full_address=True,
            address_input_attempts=1,
            partial_address_candidate="广西玉林市",
        )
        scenario_data = build_installation_scenario().to_dict()
        scenario_data["customer"]["address"] = "广西省玉林市陆川县乌石镇桅杆村第三组28号"
        scenario = Scenario.from_dict(scenario_data)
        collected_slots = {
            "issue_description": "想约安装。",
            "surname": "陈",
            "phone": "13800138001",
            "address": "",
            "product_model": "",
            "request_type": "installation",
            "availability": "",
            "phone_contactable": "yes",
            "phone_contact_owner": "本人当前来电",
            "phone_collection_attempts": "0",
            "product_arrived": "yes",
        }

        result = policy.respond(
            scenario=scenario,
            transcript=[
                DialogueTurn(
                    speaker="service",
                    text="好的，您是在广西玉林市的哪个区县呢？具体小区门牌号也提供一下呢？",
                    round_index=8,
                ),
                DialogueTurn(
                    speaker="user",
                    text="陆川县乌石镇桅杆村第三组28号。",
                    round_index=9,
                ),
            ],
            collected_slots=collected_slots,
            runtime_state=state,
        )

        self.assertEqual(
            result.reply,
            "好的，跟您确认一下，地址是广西省玉林市陆川县乌石镇桅杆村第三组28号，对吗？",
        )
        self.assertEqual(
            state.pending_address_confirmation,
            "广西省玉林市陆川县乌石镇桅杆村第三组28号",
        )

    def test_complete_address_requires_confirmation_before_slot_update(self):
        policy = ServiceDialoguePolicy()
        state = ServiceRuntimeState(awaiting_full_address=True, address_input_attempts=1)
        scenario = build_scenario()
        collected_slots = {
            "issue_description": "对，家里热水器加热很慢。",
            "surname": "张",
            "phone": "13800138001",
            "address": "",
            "product_model": "",
            "request_type": "fault",
            "availability": "",
            "phone_contactable": "yes",
            "phone_contact_owner": "本人当前来电",
            "phone_collection_attempts": "0",
        }

        second_result = policy.respond(
            scenario=scenario,
            transcript=[
                DialogueTurn(speaker="service", text="请问是几栋几单元几楼几号呢？", round_index=6),
                DialogueTurn(speaker="user", text="好的，地址是上海市浦东新区锦绣路1888弄6号1202室。", round_index=6),
            ],
            collected_slots=collected_slots,
            runtime_state=state,
        )
        self.assertEqual(second_result.slot_updates, {})
        self.assertEqual(
            second_result.reply,
            "好的，跟您确认一下，地址是上海市浦东新区锦绣路1888弄6号1202室，对吗？",
        )
        self.assertTrue(state.expected_address_confirmation)
        self.assertEqual(state.pending_address_confirmation, "上海市浦东新区锦绣路1888弄6号1202室")

    def test_complete_address_without_province_city_suffixes_still_starts_confirmation(self):
        policy = ServiceDialoguePolicy()
        state = ServiceRuntimeState(awaiting_full_address=True, address_input_attempts=1)
        scenario_data = build_scenario().to_dict()
        scenario_data["customer"]["address"] = "江苏省南京市鼓楼区汉中门大街288号金陵世纪花园6幢1单元1204室"
        scenario = Scenario.from_dict(scenario_data)
        collected_slots = {
            "issue_description": "家里热水器噪音很大。",
            "surname": "张",
            "phone": "13800138001",
            "address": "",
            "product_model": "",
            "request_type": "fault",
            "availability": "",
            "phone_contactable": "yes",
            "phone_contact_owner": "本人当前来电",
            "phone_collection_attempts": "0",
        }

        result = policy.respond(
            scenario=scenario,
            transcript=[
                DialogueTurn(speaker="service", text="好的，需要登记下您的地址，麻烦您完整的说下省、市、区、乡镇，精确到门牌号。", round_index=6),
                DialogueTurn(speaker="user", text="江苏南京鼓楼区汉中门大街288号金陵世纪花园6幢1单元1204室", round_index=6),
            ],
            collected_slots=collected_slots,
            runtime_state=state,
        )

        self.assertEqual(
            result.reply,
            "好的，跟您确认一下，地址是江苏省南京市鼓楼区汉中门大街288号金陵世纪花园6幢1单元1204室，对吗？",
        )
        self.assertTrue(state.expected_address_confirmation)
        self.assertEqual(
            state.pending_address_confirmation,
            "江苏省南京市鼓楼区汉中门大街288号金陵世纪花园6幢1单元1204室",
        )

    def test_storefront_house_number_address_can_start_confirmation_without_building_unit(self):
        policy = ServiceDialoguePolicy()
        state = ServiceRuntimeState(awaiting_full_address=True, address_input_attempts=1)
        scenario_data = build_installation_scenario().to_dict()
        scenario_data["customer"]["address"] = "贵州省遵义市汇川区深圳大道康乐社区62号门面"
        scenario = Scenario.from_dict(scenario_data)
        collected_slots = {
            "issue_description": "想约安装。",
            "surname": "王",
            "phone": "13900139002",
            "address": "",
            "product_model": "",
            "request_type": "installation",
            "availability": "",
            "phone_contactable": "yes",
            "phone_contact_owner": "本人当前来电",
            "phone_collection_attempts": "0",
            "product_arrived": "yes",
        }

        result = policy.respond(
            scenario=scenario,
            transcript=[
                DialogueTurn(
                    speaker="service",
                    text="好的，需要登记下您的地址，麻烦您完整的说下省、市、区、乡镇，精确到门牌号。",
                    round_index=6,
                ),
                DialogueTurn(
                    speaker="user",
                    text="贵州省遵义市汇川区深圳大道康乐社区62号门面",
                    round_index=6,
                ),
            ],
            collected_slots=collected_slots,
            runtime_state=state,
        )

        self.assertEqual(
            result.reply,
            "好的，跟您确认一下，地址是贵州省遵义市汇川区深圳大道康乐社区62号门面，对吗？",
        )
        self.assertTrue(state.expected_address_confirmation)
        self.assertEqual(state.pending_address_confirmation, "贵州省遵义市汇川区深圳大道康乐社区62号门面")

    def test_locality_with_building_unit_then_room_can_start_confirmation(self):
        policy = ServiceDialoguePolicy()
        state = ServiceRuntimeState(
            awaiting_full_address=True,
            address_input_attempts=1,
            partial_address_candidate="江苏省扬州市宝应县阳光锦城4栋1单元",
            last_address_followup_prompt="请问是几栋几单元几楼几号呢？",
        )
        scenario_data = build_scenario().to_dict()
        scenario_data["customer"]["address"] = "江苏省扬州市宝应县阳光锦城4栋1单元402室"
        scenario = Scenario.from_dict(scenario_data)

        result = policy.respond(
            scenario=scenario,
            transcript=[
                DialogueTurn(speaker="service", text="请问是几栋几单元几楼几号呢？", round_index=17),
                DialogueTurn(speaker="user", text="4栋1单元402室", round_index=17),
            ],
            collected_slots={
                "issue_description": "热水器温度不稳。",
                "surname": "王",
                "phone": "13773341553",
                "address": "",
                "product_model": "",
                "request_type": "fault",
                "availability": "",
                "phone_contactable": "yes",
                "phone_contact_owner": "本人当前来电",
                "phone_collection_attempts": "0",
            },
            runtime_state=state,
        )

        self.assertEqual(
            result.reply,
            "好的，跟您确认一下，地址是江苏省扬州市宝应县阳光锦城4栋1单元402室，对吗？",
        )
        self.assertTrue(state.expected_address_confirmation)

    def test_extract_address_components_splits_community_lane_and_building(self):
        components = extract_address_components("上海市青浦区徐泾镇西郊一区1785弄40号楼301室")

        self.assertEqual(components.city, "上海市")
        self.assertEqual(components.district, "青浦区")
        self.assertEqual(components.town, "徐泾镇")
        self.assertEqual(components.community, "西郊一区")
        self.assertEqual(components.road, "1785弄")
        self.assertEqual(components.building, "40号楼")
        self.assertEqual(components.room, "301室")

    def test_extract_address_components_preserves_suffixless_community_before_building(self):
        components = extract_address_components("浙江省台州市三门县江南壹号5栋")

        self.assertEqual(components.province, "浙江省")
        self.assertEqual(components.city, "台州市")
        self.assertEqual(components.district, "三门县")
        self.assertEqual(components.community, "江南壹号")
        self.assertEqual(components.building, "5栋")

    def test_locality_with_numeric_lane_and_building_room_preserves_lane_and_starts_confirmation(self):
        policy = ServiceDialoguePolicy()
        state = ServiceRuntimeState(
            awaiting_full_address=True,
            address_input_attempts=2,
            partial_address_candidate="上海市青浦区徐泾镇西郊一区",
            last_address_followup_prompt="请问是几栋几单元几楼几号呢？",
        )
        scenario_data = build_scenario().to_dict()
        scenario_data["customer"]["address"] = "上海市青浦区徐泾镇西郊一区1785弄40号楼301室"
        scenario = Scenario.from_dict(scenario_data)

        result = policy.respond(
            scenario=scenario,
            transcript=[
                DialogueTurn(speaker="service", text="请问是几栋几单元几楼几号呢？", round_index=17),
                DialogueTurn(speaker="user", text="1785 弄 40 号楼 301 室", round_index=17),
            ],
            collected_slots={
                "issue_description": "热水器温度不稳。",
                "surname": "王",
                "phone": "13773341553",
                "address": "",
                "product_model": "",
                "request_type": "fault",
                "availability": "",
                "phone_contactable": "yes",
                "phone_contact_owner": "本人当前来电",
                "phone_collection_attempts": "0",
            },
            runtime_state=state,
        )

        self.assertEqual(
            result.reply,
            "好的，跟您确认一下，地址是上海市青浦区徐泾镇西郊一区1785弄40号楼301室，对吗？",
        )
        self.assertTrue(state.expected_address_confirmation)
        self.assertEqual(state.pending_address_confirmation, "上海市青浦区徐泾镇西郊一区1785弄40号楼301室")

    def test_opening_repeated_affirmation_is_not_misclassified_as_issue_detail(self):
        policy = ServiceDialoguePolicy()

        self.assertEqual(policy._classify_opening_intent("啊这这这是滴是滴"), "yes")
        self.assertFalse(policy._opening_response_contains_issue_detail("啊这这这是滴是滴"))

    def test_town_is_preserved_when_partial_address_is_extended_with_community_detail(self):
        policy = ServiceDialoguePolicy()
        state = ServiceRuntimeState(
            awaiting_full_address=True,
            address_input_attempts=1,
            partial_address_candidate="江苏省扬州市宝应县安宜镇",
            last_address_followup_prompt="好的，请您继续说一下小区、楼栋和门牌号。",
        )
        scenario_data = build_scenario().to_dict()
        scenario_data["customer"]["address"] = "江苏省扬州市宝应县阳光锦城3号楼2单元402室"
        scenario = Scenario.from_dict(scenario_data)

        result = policy.respond(
            scenario=scenario,
            transcript=[
                DialogueTurn(speaker="service", text="好的，请您继续说一下小区、楼栋和门牌号。", round_index=11),
                DialogueTurn(speaker="user", text="阳光锦城3号楼2单元402室", round_index=11),
            ],
            collected_slots={
                "issue_description": "热水器温度不稳。",
                "surname": "王",
                "phone": "13773341553",
                "address": "",
                "product_model": "",
                "request_type": "fault",
                "availability": "",
                "phone_contactable": "yes",
                "phone_contact_owner": "本人当前来电",
                "phone_collection_attempts": "0",
            },
            runtime_state=state,
        )

        self.assertEqual(
            result.reply,
            "好的，跟您确认一下，地址是江苏省扬州市宝应县安宜镇阳光锦城3号楼2单元402室，对吗？",
        )
        self.assertTrue(state.expected_address_confirmation)

    def test_address_with_non_standard_whitespace_still_starts_confirmation(self):
        policy = ServiceDialoguePolicy()
        state = ServiceRuntimeState(
            awaiting_full_address=True,
            address_input_attempts=1,
            partial_address_candidate="江苏省扬州市宝应县安宜镇",
            last_address_followup_prompt="好的，请您继续说一下小区、楼栋和门牌号。",
        )
        scenario_data = build_scenario().to_dict()
        scenario_data["customer"]["address"] = "江苏省扬州市宝应县安宜镇阳光锦城3号楼2单元402室"
        scenario = Scenario.from_dict(scenario_data)

        result = policy.respond(
            scenario=scenario,
            transcript=[
                DialogueTurn(speaker="service", text="好的，请您继续说一下小区、楼栋和门牌号。", round_index=11),
                DialogueTurn(speaker="user", text="阳光锦城\u30003\u00a0号楼\t2 单元\n402", round_index=11),
            ],
            collected_slots={
                "issue_description": "热水器温度不稳。",
                "surname": "王",
                "phone": "13773341553",
                "address": "",
                "product_model": "",
                "request_type": "fault",
                "availability": "",
                "phone_contactable": "yes",
                "phone_contact_owner": "本人当前来电",
                "phone_collection_attempts": "0",
            },
            runtime_state=state,
        )

        self.assertEqual(
            result.reply,
            "好的，跟您确认一下，地址是江苏省扬州市宝应县安宜镇阳光锦城3号楼2单元402室，对吗？",
        )
        self.assertTrue(state.expected_address_confirmation)

    def test_locality_with_building_unit_then_floor_room_can_start_confirmation(self):
        policy = ServiceDialoguePolicy()
        state = ServiceRuntimeState(
            awaiting_full_address=True,
            address_input_attempts=2,
            partial_address_candidate="江苏省扬州市宝应县阳光锦城4栋1单元",
            last_address_followup_prompt="请问是几栋几单元几楼几号呢？",
        )
        scenario_data = build_scenario().to_dict()
        scenario_data["customer"]["address"] = "江苏省扬州市宝应县阳光锦城4栋1单元四层402室"
        scenario = Scenario.from_dict(scenario_data)

        result = policy.respond(
            scenario=scenario,
            transcript=[
                DialogueTurn(speaker="service", text="请问是几栋几单元几楼几号呢？", round_index=18),
                DialogueTurn(speaker="user", text="四层啊402室", round_index=18),
            ],
            collected_slots={
                "issue_description": "热水器温度不稳。",
                "surname": "王",
                "phone": "13773341553",
                "address": "",
                "product_model": "",
                "request_type": "fault",
                "availability": "",
                "phone_contactable": "yes",
                "phone_contact_owner": "本人当前来电",
                "phone_collection_attempts": "0",
            },
            runtime_state=state,
        )

        self.assertEqual(
            result.reply,
            "好的，跟您确认一下，地址是江苏省扬州市宝应县阳光锦城4栋1单元四层402室，对吗？",
        )
        self.assertTrue(state.expected_address_confirmation)

    def test_address_collection_uses_model_fallback_to_complete_candidate(self):
        def fake_address_inference(**kwargs):
            self.assertEqual(kwargs["user_text"], "就四楼那个")
            return {
                "address_candidate": "四层402室",
                "merged_address_candidate": "江苏省扬州市宝应县阳光锦城4栋1单元四层402室",
                "granularity": "complete",
            }

        policy = ServiceDialoguePolicy(address_inference_callback=fake_address_inference)
        state = ServiceRuntimeState(
            awaiting_full_address=True,
            address_input_attempts=2,
            partial_address_candidate="江苏省扬州市宝应县阳光锦城4栋1单元",
            last_address_followup_prompt="请问是几栋几单元几楼几号呢？",
        )
        scenario_data = build_scenario().to_dict()
        scenario_data["customer"]["address"] = "江苏省扬州市宝应县阳光锦城4栋1单元四层402室"
        scenario = Scenario.from_dict(scenario_data)

        result = policy.respond(
            scenario=scenario,
            transcript=[
                DialogueTurn(speaker="service", text="请问是几栋几单元几楼几号呢？", round_index=19),
                DialogueTurn(speaker="user", text="就四楼那个", round_index=19),
            ],
            collected_slots={
                "issue_description": "热水器温度不稳。",
                "surname": "王",
                "phone": "13773341553",
                "address": "",
                "product_model": "",
                "request_type": "fault",
                "availability": "",
                "phone_contactable": "yes",
                "phone_contact_owner": "本人当前来电",
                "phone_collection_attempts": "0",
            },
            runtime_state=state,
        )

        self.assertEqual(
            result.reply,
            "好的，跟您确认一下，地址是江苏省扬州市宝应县阳光锦城4栋1单元四层402室，对吗？",
        )
        self.assertTrue(policy.last_used_model_intent_inference)

    def test_address_collection_uses_model_backfill_when_rule_candidate_misses_community(self):
        callback_calls: list[dict[str, str]] = []

        def fake_address_inference(**kwargs):
            callback_calls.append(kwargs)
            self.assertEqual(kwargs["user_text"], "5栋302室")
            return {
                "address_candidate": "江南壹号5栋302室",
                "merged_address_candidate": "浙江省台州市三门县海润街道江南壹号5栋302室",
                "granularity": "complete",
            }

        policy = ServiceDialoguePolicy(address_inference_callback=fake_address_inference)
        state = ServiceRuntimeState(
            awaiting_full_address=True,
            address_input_attempts=1,
            partial_address_candidate="浙江省台州市三门县海润街道",
            last_address_followup_prompt="好的，请您继续说一下小区、楼栋和门牌号。",
        )
        scenario_data = build_scenario().to_dict()
        scenario_data["customer"]["address"] = "浙江省台州市三门县海润街道江南壹号5栋302室"
        scenario = Scenario.from_dict(scenario_data)

        result = policy.respond(
            scenario=scenario,
            transcript=[
                DialogueTurn(speaker="service", text="好的，请您继续说一下小区、楼栋和门牌号。", round_index=19),
                DialogueTurn(speaker="user", text="5栋302室", round_index=19),
            ],
            collected_slots={
                "issue_description": "热水器温度不稳。",
                "surname": "王",
                "phone": "13773341553",
                "address": "",
                "product_model": "",
                "request_type": "fault",
                "availability": "",
                "phone_contactable": "yes",
                "phone_contact_owner": "本人当前来电",
                "phone_collection_attempts": "0",
            },
            runtime_state=state,
        )

        self.assertEqual(len(callback_calls), 1)
        self.assertEqual(
            result.reply,
            "好的，跟您确认一下，地址是浙江省台州市三门县海润街道江南壹号5栋302室，对吗？",
        )
        self.assertTrue(state.expected_address_confirmation)
        self.assertEqual(
            state.pending_address_confirmation,
            "浙江省台州市三门县海润街道江南壹号5栋302室",
        )
        self.assertTrue(policy.last_used_model_intent_inference)

    def test_address_collection_uses_model_backfill_when_rule_candidate_misses_road(self):
        callback_calls: list[dict[str, str]] = []

        def fake_address_inference(**kwargs):
            callback_calls.append(kwargs)
            self.assertEqual(kwargs["user_text"], "40号楼301室")
            return {
                "address_candidate": "1785弄40号楼301室",
                "merged_address_candidate": "上海市青浦区徐泾镇西郊一区1785弄40号楼301室",
                "granularity": "complete",
            }

        policy = ServiceDialoguePolicy(address_inference_callback=fake_address_inference)
        state = ServiceRuntimeState(
            awaiting_full_address=True,
            address_input_attempts=1,
            partial_address_candidate="上海市青浦区徐泾镇西郊一区",
            last_address_followup_prompt="请问是几栋几单元几楼几号呢？",
        )
        scenario_data = build_scenario().to_dict()
        scenario_data["customer"]["address"] = "上海市青浦区徐泾镇西郊一区1785弄40号楼301室"
        scenario = Scenario.from_dict(scenario_data)

        result = policy.respond(
            scenario=scenario,
            transcript=[
                DialogueTurn(speaker="service", text="请问是几栋几单元几楼几号呢？", round_index=20),
                DialogueTurn(speaker="user", text="40号楼301室", round_index=20),
            ],
            collected_slots={
                "issue_description": "热水器温度不稳。",
                "surname": "王",
                "phone": "13773341553",
                "address": "",
                "product_model": "",
                "request_type": "fault",
                "availability": "",
                "phone_contactable": "yes",
                "phone_contact_owner": "本人当前来电",
                "phone_collection_attempts": "0",
            },
            runtime_state=state,
        )

        self.assertEqual(len(callback_calls), 1)
        self.assertEqual(
            result.reply,
            "好的，跟您确认一下，地址是上海市青浦区徐泾镇西郊一区1785弄40号楼301室，对吗？",
        )
        self.assertTrue(state.expected_address_confirmation)
        self.assertEqual(
            state.pending_address_confirmation,
            "上海市青浦区徐泾镇西郊一区1785弄40号楼301室",
        )
        self.assertTrue(policy.last_used_model_intent_inference)

    def test_address_collection_accepts_current_candidate_when_user_says_this_place_is_enough(self):
        policy = ServiceDialoguePolicy()
        state = ServiceRuntimeState(
            awaiting_full_address=True,
            address_input_attempts=2,
            partial_address_candidate="上海市青浦区古桐公寓39号楼",
            last_address_followup_prompt="请问是几栋几单元几楼几号呢？",
        )
        scenario_data = build_scenario().to_dict()
        scenario_data["customer"]["address"] = "上海市青浦区古桐公寓39号楼"
        scenario = Scenario.from_dict(scenario_data)

        result = policy.respond(
            scenario=scenario,
            transcript=[
                DialogueTurn(speaker="service", text="请问是几栋几单元几楼几号呢？", round_index=15),
                DialogueTurn(speaker="user", text="直接这地方就行了", round_index=15),
            ],
            collected_slots={
                "issue_description": "热水器温度不稳。",
                "surname": "王",
                "phone": "13773341553",
                "address": "",
                "product_model": "",
                "request_type": "fault",
                "availability": "",
                "phone_contactable": "yes",
                "phone_contact_owner": "本人当前来电",
                "phone_collection_attempts": "0",
            },
            runtime_state=state,
        )

        self.assertEqual(
            result.reply,
            "好的，跟您确认一下，地址是上海市青浦区古桐公寓39号楼，对吗？",
        )
        self.assertFalse(policy.last_used_model_intent_inference)

    def test_address_collection_accepts_current_candidate_when_user_says_finished(self):
        policy = ServiceDialoguePolicy()
        state = ServiceRuntimeState(
            awaiting_full_address=True,
            address_input_attempts=3,
            partial_address_candidate="上海市青浦区徐泾镇西郊一区1785弄41号楼",
            last_address_followup_prompt="请问是几栋几单元几楼几号呢？",
        )
        scenario_data = build_scenario().to_dict()
        scenario_data["customer"]["address"] = "上海市青浦区徐泾镇西郊一区1785弄41号楼"
        scenario = Scenario.from_dict(scenario_data)

        result = policy.respond(
            scenario=scenario,
            transcript=[
                DialogueTurn(speaker="service", text="请问是几栋几单元几楼几号呢？", round_index=15),
                DialogueTurn(speaker="user", text="我说完了啊", round_index=15),
            ],
            collected_slots={
                "issue_description": "热水器温度不稳。",
                "surname": "王",
                "phone": "13773341553",
                "address": "",
                "product_model": "",
                "request_type": "fault",
                "availability": "",
                "phone_contactable": "yes",
                "phone_contact_owner": "本人当前来电",
                "phone_collection_attempts": "0",
            },
            runtime_state=state,
        )

        self.assertEqual(
            result.reply,
            "好的，跟您确认一下，地址是上海市青浦区徐泾镇西郊一区1785弄41号楼，对吗？",
        )

    def test_address_collection_accepts_current_candidate_when_user_can_only_provide_minimum(self):
        policy = ServiceDialoguePolicy()
        state = ServiceRuntimeState(
            awaiting_full_address=True,
            address_input_attempts=3,
            partial_address_candidate="上海市青浦区徐泾镇西郊一区1785弄41号楼",
            last_address_followup_prompt="请问是几栋几单元几楼几号呢？",
        )
        scenario_data = build_scenario().to_dict()
        scenario_data["customer"]["address"] = "上海市青浦区徐泾镇西郊一区1785弄41号楼"
        scenario = Scenario.from_dict(scenario_data)

        result = policy.respond(
            scenario=scenario,
            transcript=[
                DialogueTurn(speaker="service", text="请问是几栋几单元几楼几号呢？", round_index=15),
                DialogueTurn(speaker="user", text="我只能提供到这了", round_index=15),
            ],
            collected_slots={
                "issue_description": "热水器温度不稳。",
                "surname": "王",
                "phone": "13773341553",
                "address": "",
                "product_model": "",
                "request_type": "fault",
                "availability": "",
                "phone_contactable": "yes",
                "phone_contact_owner": "本人当前来电",
                "phone_collection_attempts": "0",
            },
            runtime_state=state,
        )

        self.assertEqual(
            result.reply,
            "好的，跟您确认一下，地址是上海市青浦区徐泾镇西郊一区1785弄41号楼，对吗？",
        )

    def test_address_collection_can_use_history_model_summary_when_user_says_this_place_is_enough(self):
        callback_calls: list[dict[str, str]] = []

        def fake_address_inference(**kwargs):
            callback_calls.append(kwargs)
            self.assertIn("古桐公寓39号楼", kwargs["dialogue_history"])
            return {
                "address_candidate": "",
                "merged_address_candidate": "上海市青浦区古桐公寓39号楼",
                "granularity": "complete",
            }

        policy = ServiceDialoguePolicy(address_inference_callback=fake_address_inference)
        state = ServiceRuntimeState(
            awaiting_full_address=True,
            address_input_attempts=2,
            partial_address_candidate="",
            last_address_followup_prompt="请问是几栋几单元几楼几号呢？",
        )
        scenario_data = build_scenario().to_dict()
        scenario_data["customer"]["address"] = "上海市青浦区古桐公寓39号楼"
        scenario = Scenario.from_dict(scenario_data)

        result = policy.respond(
            scenario=scenario,
            transcript=[
                DialogueTurn(speaker="service", text="好的，需要登记下您的地址，麻烦您完整的说下省、市、区、乡镇，精确到门牌号。", round_index=13),
                DialogueTurn(speaker="user", text="上海市青浦区", round_index=13),
                DialogueTurn(speaker="service", text="好的，请您继续说一下小区、楼栋和门牌号。", round_index=14),
                DialogueTurn(speaker="user", text="古桐公寓39号楼", round_index=14),
                DialogueTurn(speaker="service", text="请问是几栋几单元几楼几号呢？", round_index=15),
                DialogueTurn(speaker="user", text="直接这地方就行了", round_index=15),
            ],
            collected_slots={
                "issue_description": "热水器温度不稳。",
                "surname": "王",
                "phone": "13773341553",
                "address": "",
                "product_model": "",
                "request_type": "fault",
                "availability": "",
                "phone_contactable": "yes",
                "phone_contact_owner": "本人当前来电",
                "phone_collection_attempts": "0",
            },
            runtime_state=state,
        )

        self.assertEqual(
            result.reply,
            "好的，跟您确认一下，地址是上海市青浦区古桐公寓39号楼，对吗？",
        )
        self.assertTrue(policy.last_used_model_intent_inference)
        self.assertEqual(len(callback_calls), 1)

    def test_address_collection_model_fallback_does_not_jump_from_town_only_to_locality(self):
        def fake_address_inference(**kwargs):
            self.assertEqual(kwargs["user_text"], "上海市青浦区徐泾镇")
            return {
                "address_candidate": "上海市青浦区徐泾镇西郊一区",
                "merged_address_candidate": "上海市青浦区徐泾镇西郊一区",
                "granularity": "locality",
            }

        policy = ServiceDialoguePolicy(address_inference_callback=fake_address_inference)
        state = ServiceRuntimeState(awaiting_full_address=True)
        scenario_data = build_scenario().to_dict()
        scenario_data["customer"]["address"] = "上海市青浦区徐泾镇西郊一区1785弄41号楼"
        scenario = Scenario.from_dict(scenario_data)

        result = policy.respond(
            scenario=scenario,
            transcript=[
                DialogueTurn(
                    speaker="service",
                    text="需要登记下您的地址，麻烦您完整的说下省、市、区、乡镇，精确到门牌号。",
                    round_index=10,
                ),
                DialogueTurn(speaker="user", text="上海市青浦区徐泾镇", round_index=10),
            ],
            collected_slots={
                "issue_description": "热水器温度不稳。",
                "surname": "郑",
                "phone": "13773341553",
                "address": "",
                "product_model": "",
                "request_type": "fault",
                "availability": "",
                "phone_contactable": "yes",
                "phone_contact_owner": "本人当前来电",
                "phone_collection_attempts": "0",
            },
            runtime_state=state,
        )

        self.assertEqual(result.reply, "好的，请您继续说一下小区、楼栋和门牌号。")
        self.assertEqual(state.partial_address_candidate, "上海市青浦区徐泾镇")
        self.assertFalse(policy.last_used_model_intent_inference)

    def test_address_collection_nonstandard_delivery_point_can_confirm_directly(self):
        policy = ServiceDialoguePolicy()
        state = ServiceRuntimeState(
            awaiting_full_address=True,
            partial_address_candidate="上海市青浦区徐泾镇",
            last_address_followup_prompt="好的，请您继续说一下小区、楼栋和门牌号。",
        )
        scenario_data = build_scenario().to_dict()
        scenario_data["customer"]["address"] = "上海市青浦区徐泾镇美的创新园区A8外卖柜"
        scenario = Scenario.from_dict(scenario_data)

        result = policy.respond(
            scenario=scenario,
            transcript=[
                DialogueTurn(
                    speaker="service",
                    text="好的，请您继续说一下小区、楼栋和门牌号。",
                    round_index=11,
                ),
                DialogueTurn(speaker="user", text="美的创新园区A8外卖柜", round_index=11),
            ],
            collected_slots={
                "issue_description": "热水器温度不稳。",
                "surname": "郑",
                "phone": "13773341553",
                "address": "",
                "product_model": "",
                "request_type": "fault",
                "availability": "",
                "phone_contactable": "yes",
                "phone_contact_owner": "本人当前来电",
                "phone_collection_attempts": "0",
            },
            runtime_state=state,
        )

        self.assertEqual(
            result.reply,
            "好的，跟您确认一下，地址是上海市青浦区徐泾镇美的创新园区A8外卖柜，对吗？",
        )
        self.assertTrue(state.expected_address_confirmation)
        self.assertEqual(
            state.pending_address_confirmation,
            "上海市青浦区徐泾镇美的创新园区A8外卖柜",
        )

    def test_address_collection_accepts_nonstandard_delivery_point_when_user_says_thats_enough(self):
        policy = ServiceDialoguePolicy()
        state = ServiceRuntimeState(
            awaiting_full_address=True,
            address_input_attempts=2,
            partial_address_candidate="上海市青浦区徐泾镇美的创新园区A8外卖柜",
            last_address_followup_prompt="好的，请您继续说一下小区、楼栋和门牌号。",
        )
        scenario_data = build_scenario().to_dict()
        scenario_data["customer"]["address"] = "上海市青浦区徐泾镇美的创新园区A8外卖柜"
        scenario = Scenario.from_dict(scenario_data)

        result = policy.respond(
            scenario=scenario,
            transcript=[
                DialogueTurn(
                    speaker="service",
                    text="好的，请您继续说一下小区、楼栋和门牌号。",
                    round_index=12,
                ),
                DialogueTurn(speaker="user", text="已经说了啊，到那就行", round_index=12),
            ],
            collected_slots={
                "issue_description": "热水器温度不稳。",
                "surname": "郑",
                "phone": "13773341553",
                "address": "",
                "product_model": "",
                "request_type": "fault",
                "availability": "",
                "phone_contactable": "yes",
                "phone_contact_owner": "本人当前来电",
                "phone_collection_attempts": "0",
            },
            runtime_state=state,
        )

        self.assertEqual(
            result.reply,
            "好的，跟您确认一下，地址是上海市青浦区徐泾镇美的创新园区A8外卖柜，对吗？",
        )
        self.assertTrue(state.expected_address_confirmation)

    def test_canonical_confirmation_address_prefers_most_complete_matching_version(self):
        self.assertEqual(
            ServiceDialoguePolicy._canonical_confirmation_address(
                "桂城街道康怡苑62号",
                "广东省佛山市南海区桂城街道康怡苑62号",
            ),
            "广东省佛山市南海区桂城街道康怡苑62号",
        )
        self.assertEqual(
            ServiceDialoguePolicy._canonical_confirmation_address(
                "北京路1000号山水花园3栋802室",
                "云南省昆明市盘龙区北京路1000号山水花园3栋802室",
            ),
            "云南省昆明市盘龙区北京路1000号山水花园3栋802室",
        )

    def test_address_detail_only_input_can_still_start_confirmation_when_precise_enough(self):
        policy = ServiceDialoguePolicy()
        state = ServiceRuntimeState(awaiting_full_address=True, address_input_attempts=0)
        scenario = build_scenario()
        collected_slots = {
            "issue_description": "对，家里热水器加热很慢。",
            "surname": "张",
            "phone": "13800138001",
            "address": "",
            "product_model": "",
            "request_type": "fault",
            "availability": "",
            "phone_contactable": "yes",
            "phone_contact_owner": "本人当前来电",
            "phone_collection_attempts": "0",
        }

        first_result = policy.respond(
            scenario=scenario,
            transcript=[
                DialogueTurn(speaker="service", text="好的，需要登记下您的地址，麻烦您完整的说下省、市、区、乡镇，精确到门牌号。", round_index=5),
                DialogueTurn(speaker="user", text="锦绣路1888弄6号1202室", round_index=5),
            ],
            collected_slots=collected_slots,
            runtime_state=state,
        )

        self.assertEqual(
            first_result.reply,
            "好的，跟您确认一下，地址是上海市浦东新区锦绣路1888弄6号1202室，对吗？",
        )

    def test_address_confirmation_strips_trailing_non_address_content(self):
        policy = ServiceDialoguePolicy()
        state = ServiceRuntimeState(awaiting_full_address=True, address_input_attempts=1)
        scenario_data = build_scenario().to_dict()
        scenario_data["customer"]["address"] = "江苏省南京市鼓楼区汉中门大街288号金陵世纪花园6幢1单元1204室"
        scenario = Scenario.from_dict(scenario_data)
        collected_slots = {
            "issue_description": "家里热水器噪音很大。",
            "surname": "张",
            "phone": "13800138001",
            "address": "",
            "product_model": "",
            "request_type": "fault",
            "availability": "",
            "phone_contactable": "yes",
            "phone_contact_owner": "本人当前来电",
            "phone_collection_attempts": "0",
        }

        result = policy.respond(
            scenario=scenario,
            transcript=[
                DialogueTurn(speaker="service", text="好的，需要登记下您的地址，麻烦您完整的说下省、市、区、乡镇，精确到门牌号。", round_index=4),
                DialogueTurn(
                    speaker="user",
                    text="好的，地址是江苏省南京市鼓楼区汉中门大街 288 号金陵世纪花园 6 幢 1 单元 1204 室。麻烦您催一下师傅，爸妈这几天被吵得都没睡好觉，挺着急的。",
                    round_index=4,
                ),
            ],
            collected_slots=collected_slots,
            runtime_state=state,
        )

        self.assertEqual(
            result.reply,
            "好的，跟您确认一下，地址是江苏省南京市鼓楼区汉中门大街 288 号金陵世纪花园 6 幢 1 单元 1204 室，对吗？",
        )
        self.assertEqual(
            state.pending_address_confirmation,
            "江苏省南京市鼓楼区汉中门大街 288 号金陵世纪花园 6 幢 1 单元 1204 室",
        )

    def test_partial_address_after_denying_full_known_address_requires_more_detail(self):
        policy = ServiceDialoguePolicy()
        state = ServiceRuntimeState(awaiting_full_address=True, address_input_attempts=0)
        scenario_data = build_scenario().to_dict()
        scenario_data["customer"]["address"] = "湖北省武汉市洪山区尤李湾路56号万珑小区5栋2单元502室"
        scenario = Scenario.from_dict(scenario_data)
        collected_slots = {
            "issue_description": "对，家里热水器加热很慢。",
            "surname": "张",
            "phone": "13800138001",
            "address": "",
            "product_model": "",
            "request_type": "fault",
            "availability": "",
            "phone_contactable": "yes",
            "phone_contact_owner": "本人当前来电",
            "phone_collection_attempts": "0",
        }

        result = policy.respond(
            scenario=scenario,
            transcript=[
                DialogueTurn(speaker="service", text="需要登记下您的地址，麻烦您完整的说下省、市、区、乡镇，精确到门牌号。", round_index=10),
                DialogueTurn(
                    speaker="user",
                    text="湖北省武汉市洪山区尤李湾路56号万珑小区5栋2单元",
                    round_index=11,
                ),
            ],
            collected_slots=collected_slots,
            runtime_state=state,
        )

        self.assertEqual(result.reply, "请问是几栋几单元几楼几号呢？")
        self.assertFalse(state.expected_address_confirmation)
        self.assertEqual(
            state.partial_address_candidate,
            "湖北省武汉市洪山区尤李湾路56号万珑小区5栋2单元",
        )

    def test_missing_house_number_uses_house_number_followup_instead_of_building_prompt(self):
        policy = ServiceDialoguePolicy()
        state = ServiceRuntimeState(
            awaiting_full_address=True,
            partial_address_candidate="江苏省扬州市宝应县安宜镇",
            last_address_followup_prompt="好的，请您继续说一下小区、楼栋和门牌号。",
        )
        scenario_data = build_scenario().to_dict()
        scenario_data["customer"]["address"] = "江苏省扬州市宝应县安宜镇阳光锦城88号3号楼2单元402室"
        scenario = Scenario.from_dict(scenario_data)
        collected_slots = {
            "issue_description": "热水器加热慢。",
            "surname": "王",
            "phone": "13773341553",
            "address": "",
            "product_model": "",
            "request_type": "fault",
            "availability": "",
            "phone_contactable": "yes",
            "phone_contact_owner": "本人当前来电",
            "phone_collection_attempts": "0",
        }

        result = policy.respond(
            scenario=scenario,
            transcript=[
                DialogueTurn(speaker="service", text="好的，请您继续说一下小区、楼栋和门牌号。", round_index=12),
                DialogueTurn(speaker="user", text="阳光锦城3号楼2单元402室", round_index=12),
            ],
            collected_slots=collected_slots,
            runtime_state=state,
        )

        self.assertEqual(result.reply, "好的，请您再说一下具体门牌号。")
        self.assertFalse(state.expected_address_confirmation)

    def test_missing_house_number_reask_frustration_does_not_start_confirmation(self):
        policy = ServiceDialoguePolicy()
        state = ServiceRuntimeState(
            awaiting_full_address=True,
            partial_address_candidate="江苏省扬州市宝应县安宜镇阳光锦城3号楼2单元402",
            last_address_followup_prompt="好的，请您再说一下具体门牌号。",
        )
        scenario_data = build_scenario().to_dict()
        scenario_data["customer"]["address"] = "江苏省扬州市宝应县安宜镇阳光锦城88号3号楼2单元402室"
        scenario = Scenario.from_dict(scenario_data)
        collected_slots = {
            "issue_description": "热水器加热慢。",
            "surname": "王",
            "phone": "13773341553",
            "address": "",
            "product_model": "",
            "request_type": "fault",
            "availability": "",
            "phone_contactable": "yes",
            "phone_contact_owner": "本人当前来电",
            "phone_collection_attempts": "0",
        }

        result = policy.respond(
            scenario=scenario,
            transcript=[
                DialogueTurn(speaker="service", text="好的，请您再说一下具体门牌号。", round_index=9),
                DialogueTurn(speaker="user", text="我说了啊", round_index=9),
            ],
            collected_slots=collected_slots,
            runtime_state=state,
        )

        self.assertEqual(result.reply, "好的，请您再说一下具体门牌号。")
        self.assertFalse(state.expected_address_confirmation)
        self.assertEqual(
            state.partial_address_candidate,
            "江苏省扬州市宝应县安宜镇阳光锦城3号楼2单元402",
        )

    def test_address_collection_asks_by_granularity_for_segmented_replies(self):
        policy = ServiceDialoguePolicy()
        scenario_data = build_scenario().to_dict()
        scenario_data["customer"]["address"] = "江苏省扬州市宝应县安宜镇宝应碧桂园3幢5层502室"
        scenario = Scenario.from_dict(scenario_data)
        collected_slots = {
            "issue_description": "热水器加热慢。",
            "surname": "张",
            "phone": "13800138001",
            "address": "",
            "product_model": "",
            "request_type": "fault",
            "availability": "",
            "phone_contactable": "yes",
            "phone_contact_owner": "本人当前来电",
            "phone_collection_attempts": "0",
        }
        state = ServiceRuntimeState(awaiting_full_address=True)

        province_city_result = policy.respond(
            scenario=scenario,
            transcript=[
                DialogueTurn(
                    speaker="service",
                    text="好的，需要登记下您的地址，麻烦您完整的说下省、市、区、乡镇，精确到门牌号。",
                    round_index=5,
                ),
                DialogueTurn(speaker="user", text="江苏省扬州市", round_index=5),
            ],
            collected_slots=collected_slots,
            runtime_state=state,
        )
        self.assertEqual(
            province_city_result.reply,
            "好的，您是在扬州市的哪个区县呢？具体小区门牌号也提供一下呢？",
        )

        district_result = policy.respond(
            scenario=scenario,
            transcript=[
                DialogueTurn(
                    speaker="service",
                    text="好的，您是在扬州市的哪个区县呢？具体小区门牌号也提供一下呢？",
                    round_index=6,
                ),
                DialogueTurn(speaker="user", text="宝应县", round_index=6),
            ],
            collected_slots=collected_slots,
            runtime_state=state,
        )
        self.assertEqual(district_result.reply, "好的，请您继续说一下小区、楼栋和门牌号。")

        community_result = policy.respond(
            scenario=scenario,
            transcript=[
                DialogueTurn(
                    speaker="service",
                    text="好的，请您继续说一下小区、楼栋和门牌号。",
                    round_index=7,
                ),
                DialogueTurn(speaker="user", text="碧桂园", round_index=7),
            ],
            collected_slots=collected_slots,
            runtime_state=state,
        )
        self.assertEqual(community_result.reply, "请问是几栋几单元几楼几号呢？")

        precise_result = policy.respond(
            scenario=scenario,
            transcript=[
                DialogueTurn(speaker="service", text="请问是几栋几单元几楼几号呢？", round_index=8),
                DialogueTurn(speaker="user", text="三栋 502", round_index=8),
            ],
            collected_slots=collected_slots,
            runtime_state=state,
        )
        self.assertEqual(
            precise_result.reply,
            "好的，跟您确认一下，地址是江苏省扬州市宝应县安宜镇宝应碧桂园3幢5层502室，对吗？",
        )

    def test_address_collection_town_only_reply_asks_for_locality_before_building(self):
        policy = ServiceDialoguePolicy()
        state = ServiceRuntimeState(awaiting_full_address=True)
        scenario_data = build_scenario().to_dict()
        scenario_data["customer"]["address"] = "上海市青浦区徐泾镇西郊一区1785弄41号楼"
        scenario = Scenario.from_dict(scenario_data)
        collected_slots = {
            "issue_description": "热水器温度不稳。",
            "surname": "王",
            "phone": "13773341553",
            "address": "",
            "product_model": "",
            "request_type": "fault",
            "availability": "",
            "phone_contactable": "yes",
            "phone_contact_owner": "本人当前来电",
            "phone_collection_attempts": "0",
        }

        result = policy.respond(
            scenario=scenario,
            transcript=[
                DialogueTurn(
                    speaker="service",
                    text="需要登记下您的地址，麻烦您完整的说下省、市、区、乡镇，精确到门牌号。",
                    round_index=13,
                ),
                DialogueTurn(speaker="user", text="上海市青浦区徐泾镇", round_index=14),
            ],
            collected_slots=collected_slots,
            runtime_state=state,
        )

        self.assertEqual(result.reply, "好的，请您继续说一下小区、楼栋和门牌号。")
        self.assertEqual(state.partial_address_candidate, "上海市青浦区徐泾镇")

    def test_segmented_address_keeps_city_when_province_city_are_spoken_without_suffixes(self):
        policy = ServiceDialoguePolicy()
        state = ServiceRuntimeState(awaiting_full_address=True, product_arrival_checked=True)
        scenario_data = build_freeform_cli_scenario(request_type="installation").to_dict()
        scenario_data["customer"]["address"] = "甘肃省兰州市七里河区工林路688号汇林现代城3号楼2单元502室"
        scenario = Scenario.from_dict(scenario_data)
        collected_slots = {
            "issue_description": "需要安装空气能热水机。",
            "surname": "轩",
            "phone": "13509589087",
            "address": "",
            "request_type": "installation",
            "phone_contactable": "no",
            "phone_contact_owner": "我父亲",
            "phone_collection_attempts": "1",
            "product_arrived": "yes",
        }

        province_city_result = policy.respond(
            scenario=scenario,
            transcript=[
                DialogueTurn(
                    speaker="service",
                    text="需要登记下您的地址，麻烦您完整的说下省、市、区、乡镇，精确到门牌号。",
                    round_index=6,
                ),
                DialogueTurn(speaker="user", text="甘肃兰州", round_index=6),
            ],
            collected_slots=collected_slots,
            runtime_state=state,
        )
        self.assertEqual(
            province_city_result.reply,
            "好的，您是在兰州市的哪个区县呢？具体小区门牌号也提供一下呢？",
        )

        district_result = policy.respond(
            scenario=scenario,
            transcript=[
                DialogueTurn(
                    speaker="service",
                    text="好的，您是在兰州市的哪个区县呢？具体小区门牌号也提供一下呢？",
                    round_index=7,
                ),
                DialogueTurn(speaker="user", text="七里河区", round_index=7),
            ],
            collected_slots=collected_slots,
            runtime_state=state,
        )
        self.assertEqual(district_result.reply, "好的，请您继续说一下小区、楼栋和门牌号。")

        precise_result = policy.respond(
            scenario=scenario,
            transcript=[
                DialogueTurn(
                    speaker="service",
                    text="好的，请您继续说一下小区、楼栋和门牌号。",
                    round_index=8,
                ),
                DialogueTurn(
                    speaker="user",
                    text="工林路688号汇林现代城3号楼2单元502室",
                    round_index=8,
                ),
            ],
            collected_slots=collected_slots,
            runtime_state=state,
        )
        self.assertEqual(
            precise_result.reply,
            "好的，跟您确认一下，地址是甘肃省兰州市七里河区工林路688号汇林现代城3号楼2单元502室，对吗？",
        )
        self.assertTrue(state.expected_address_confirmation)
        self.assertEqual(
            state.pending_address_confirmation,
            "甘肃省兰州市七里河区工林路688号汇林现代城3号楼2单元502室",
        )

    def test_rural_address_collection_asks_for_house_number_not_building(self):
        policy = ServiceDialoguePolicy()
        state = ServiceRuntimeState(awaiting_full_address=True)
        scenario = build_freeform_cli_scenario()
        collected_slots = {
            "issue_description": "需要安装空气能热水机。",
            "surname": "李",
            "phone": "13773341553",
            "address": "",
            "request_type": "installation",
            "phone_contactable": "no",
            "phone_contact_owner": "",
            "phone_collection_attempts": "2",
            "product_arrived": "yes",
        }

        result = policy.respond(
            scenario=scenario,
            transcript=[
                DialogueTurn(
                    speaker="service",
                    text="好的，您是在扬州市的哪个区县呢？具体小区门牌号也提供一下呢？",
                    round_index=12,
                ),
                DialogueTurn(speaker="user", text="宝应县广阳湖古镇村", round_index=12),
            ],
            collected_slots=collected_slots,
            runtime_state=state,
        )

        self.assertEqual(result.reply, "好的，请您提供一下详细的地址，具体到门牌号。")

    def test_freeform_unknown_actual_address_with_community_and_building_reasks_for_room(self):
        policy = ServiceDialoguePolicy()
        state = ServiceRuntimeState(
            awaiting_full_address=True,
            partial_address_candidate="浙江省台州市三门县",
            last_address_followup_prompt="好的，请您继续说一下小区、楼栋和门牌号。",
        )
        scenario = build_freeform_cli_scenario()
        collected_slots = {
            "issue_description": "需要安装空气能热水机。",
            "surname": "李",
            "phone": "13773341553",
            "address": "",
            "request_type": "installation",
            "phone_contactable": "no",
            "phone_contact_owner": "",
            "phone_collection_attempts": "2",
            "product_arrived": "yes",
        }

        result = policy.respond(
            scenario=scenario,
            transcript=[
                DialogueTurn(
                    speaker="service",
                    text="好的，请您继续说一下小区、楼栋和门牌号。",
                    round_index=13,
                ),
                DialogueTurn(speaker="user", text="江南壹号13幢", round_index=13),
            ],
            collected_slots=collected_slots,
            runtime_state=state,
        )

        self.assertEqual(result.reply, "请问是几栋几单元几楼几号呢？")
        self.assertFalse(state.expected_address_confirmation)
        self.assertEqual(state.partial_address_candidate, "浙江省台州市三门县江南壹号13幢")

    def test_freeform_unknown_actual_address_with_room_can_start_confirmation(self):
        policy = ServiceDialoguePolicy()
        state = ServiceRuntimeState(
            awaiting_full_address=True,
            partial_address_candidate="浙江省台州市三门县",
            last_address_followup_prompt="好的，请您继续说一下小区、楼栋和门牌号。",
        )
        scenario = build_freeform_cli_scenario()
        collected_slots = {
            "issue_description": "需要安装空气能热水机。",
            "surname": "李",
            "phone": "13773341553",
            "address": "",
            "request_type": "installation",
            "phone_contactable": "no",
            "phone_contact_owner": "",
            "phone_collection_attempts": "2",
            "product_arrived": "yes",
        }

        result = policy.respond(
            scenario=scenario,
            transcript=[
                DialogueTurn(
                    speaker="service",
                    text="好的，请您继续说一下小区、楼栋和门牌号。",
                    round_index=13,
                ),
                DialogueTurn(speaker="user", text="江南壹号13幢502室", round_index=13),
            ],
            collected_slots=collected_slots,
            runtime_state=state,
        )

        self.assertEqual(
            result.reply,
            "好的，跟您确认一下，地址是浙江省台州市三门县江南壹号13幢502室，对吗？",
        )
        self.assertTrue(state.expected_address_confirmation)
        self.assertEqual(
            state.pending_address_confirmation,
            "浙江省台州市三门县江南壹号13幢502室",
        )

    def test_rural_address_with_she_and_house_number_starts_confirmation(self):
        policy = ServiceDialoguePolicy()
        state = ServiceRuntimeState(
            awaiting_full_address=True,
            partial_address_candidate="青海省海东市",
            last_address_followup_prompt="好的，您是在海东市的哪个区县呢？具体小区门牌号也提供一下呢？",
        )
        scenario_data = build_installation_scenario().to_dict()
        scenario_data["customer"]["address"] = "青海省海东市民和回族土族自治县中川乡红崖子村三社14号"
        scenario = Scenario.from_dict(scenario_data)
        collected_slots = {
            "issue_description": "想约安装。",
            "surname": "王",
            "phone": "13900139002",
            "address": "",
            "product_model": "",
            "request_type": "installation",
            "availability": "",
            "phone_contactable": "yes",
            "phone_contact_owner": "本人当前来电",
            "phone_collection_attempts": "0",
            "product_arrived": "yes",
        }

        result = policy.respond(
            scenario=scenario,
            transcript=[
                DialogueTurn(
                    speaker="service",
                    text="好的，您是在海东市的哪个区县呢？具体小区门牌号也提供一下呢？",
                    round_index=7,
                ),
                DialogueTurn(
                    speaker="user",
                    text="在民和回族土族自治县中川乡红崖子村三社14号。",
                    round_index=7,
                ),
            ],
            collected_slots=collected_slots,
            runtime_state=state,
        )

        self.assertEqual(
            result.reply,
            "好的，跟您确认一下，地址是青海省海东市民和回族土族自治县中川乡红崖子村三社14号，对吗？",
        )
        self.assertTrue(state.expected_address_confirmation)
        self.assertEqual(
            state.pending_address_confirmation,
            "青海省海东市民和回族土族自治县中川乡红崖子村三社14号",
        )

    def test_rural_group_and_house_number_suffix_merges_with_existing_village_prefix(self):
        policy = ServiceDialoguePolicy()
        state = ServiceRuntimeState(
            awaiting_full_address=True,
            partial_address_candidate="江苏省扬州市宝应县广阳湖镇葛庄村",
            last_address_followup_prompt="好的，请您提供一下详细的地址，具体到门牌号。",
        )
        scenario_data = build_installation_scenario().to_dict()
        scenario_data["customer"]["address"] = "江苏省扬州市宝应县广阳湖镇葛庄村10组4号"
        scenario = Scenario.from_dict(scenario_data)
        collected_slots = {
            "issue_description": "想约安装。",
            "surname": "郭",
            "phone": "13773341553",
            "address": "",
            "product_model": "",
            "request_type": "installation",
            "availability": "",
            "phone_contactable": "yes",
            "phone_contact_owner": "本人当前来电",
            "phone_collection_attempts": "0",
            "product_arrived": "yes",
        }

        result = policy.respond(
            scenario=scenario,
            transcript=[
                DialogueTurn(
                    speaker="service",
                    text="好的，请您提供一下详细的地址，具体到门牌号。",
                    round_index=11,
                ),
                DialogueTurn(
                    speaker="user",
                    text="10组4号",
                    round_index=12,
                ),
            ],
            collected_slots=collected_slots,
            runtime_state=state,
        )

        self.assertEqual(
            result.reply,
            "好的，跟您确认一下，地址是江苏省扬州市宝应县广阳湖镇葛庄村10组4号，对吗？",
        )
        self.assertTrue(state.expected_address_confirmation)
        self.assertEqual(
            state.pending_address_confirmation,
            "江苏省扬州市宝应县广阳湖镇葛庄村10组4号",
        )

    def test_rural_group_and_house_number_suffix_with_spaces_starts_confirmation(self):
        policy = ServiceDialoguePolicy()
        state = ServiceRuntimeState(
            awaiting_full_address=True,
            partial_address_candidate="江苏省扬州市宝应县广阳湖镇葛庄村",
            last_address_followup_prompt="好的，请您提供一下详细的地址，具体到门牌号。",
        )
        scenario_data = build_installation_scenario().to_dict()
        scenario_data["customer"]["address"] = "江苏省扬州市宝应县广阳湖镇葛庄村10组4号"
        scenario = Scenario.from_dict(scenario_data)
        collected_slots = {
            "issue_description": "想约安装。",
            "surname": "郭",
            "phone": "13773341553",
            "address": "",
            "product_model": "",
            "request_type": "installation",
            "availability": "",
            "phone_contactable": "yes",
            "phone_contact_owner": "本人当前来电",
            "phone_collection_attempts": "0",
            "product_arrived": "yes",
        }

        result = policy.respond(
            scenario=scenario,
            transcript=[
                DialogueTurn(
                    speaker="service",
                    text="好的，请您提供一下详细的地址，具体到门牌号。",
                    round_index=11,
                ),
                DialogueTurn(
                    speaker="user",
                    text="10 组 4 号",
                    round_index=12,
                ),
            ],
            collected_slots=collected_slots,
            runtime_state=state,
        )

        self.assertEqual(
            result.reply,
            "好的，跟您确认一下，地址是江苏省扬州市宝应县广阳湖镇葛庄村10 组 4 号，对吗？",
        )
        self.assertTrue(state.expected_address_confirmation)

    def test_rural_no_building_statement_switches_followup_prompt(self):
        policy = ServiceDialoguePolicy()
        state = ServiceRuntimeState(
            awaiting_full_address=True,
            partial_address_candidate="江苏省扬州市宝应县广阳湖古镇村",
            last_address_followup_prompt="请问是几栋几单元几楼几号呢？",
        )
        scenario = build_freeform_cli_scenario()
        collected_slots = {
            "issue_description": "需要安装空气能热水机。",
            "surname": "李",
            "phone": "13773341553",
            "address": "",
            "request_type": "installation",
            "phone_contactable": "no",
            "phone_contact_owner": "",
            "phone_collection_attempts": "2",
            "product_arrived": "yes",
        }

        result = policy.respond(
            scenario=scenario,
            transcript=[
                DialogueTurn(speaker="service", text="请问是几栋几单元几楼几号呢？", round_index=13),
                DialogueTurn(speaker="user", text="我这是村没栋啊", round_index=13),
            ],
            collected_slots=collected_slots,
            runtime_state=state,
        )

        self.assertEqual(result.reply, "好的，请您提供一下详细的地址，具体到门牌号。")
        self.assertEqual(state.partial_address_candidate, "江苏省扬州市宝应县广阳湖古镇村")

    def test_vague_address_reply_repeats_same_prompt_up_to_two_times(self):
        policy = ServiceDialoguePolicy()
        state = ServiceRuntimeState(
            awaiting_full_address=True,
            last_address_followup_prompt="好的，您是在扬州市的哪个区县呢？具体小区门牌号也提供一下呢？",
        )
        scenario_data = build_scenario().to_dict()
        scenario_data["customer"]["address"] = "江苏省扬州市宝应县安宜镇宝应碧桂园3幢5层502室"
        scenario = Scenario.from_dict(scenario_data)
        collected_slots = {
            "issue_description": "热水器加热慢。",
            "surname": "张",
            "phone": "13800138001",
            "address": "",
            "product_model": "",
            "request_type": "fault",
            "availability": "",
            "phone_contactable": "yes",
            "phone_contact_owner": "本人当前来电",
            "phone_collection_attempts": "0",
        }
        state.partial_address_candidate = "江苏省扬州市"

        first_retry = policy.respond(
            scenario=scenario,
            transcript=[
                DialogueTurn(
                    speaker="service",
                    text="好的，您是在扬州市的哪个区县呢？具体小区门牌号也提供一下呢？",
                    round_index=6,
                ),
                DialogueTurn(speaker="user", text="嗯", round_index=6),
            ],
            collected_slots=collected_slots,
            runtime_state=state,
        )
        self.assertEqual(
            first_retry.reply,
            "好的，您是在扬州市的哪个区县呢？具体小区门牌号也提供一下呢？",
        )
        self.assertEqual(state.address_vague_retry_count, 1)

        second_retry = policy.respond(
            scenario=scenario,
            transcript=[
                DialogueTurn(
                    speaker="service",
                    text="好的，您是在扬州市的哪个区县呢？具体小区门牌号也提供一下呢？",
                    round_index=7,
                ),
                DialogueTurn(speaker="user", text="不知道怎么说", round_index=7),
            ],
            collected_slots=collected_slots,
            runtime_state=state,
        )
        self.assertEqual(
            second_retry.reply,
            "好的，您是在扬州市的哪个区县呢？具体小区门牌号也提供一下呢？",
        )
        self.assertEqual(state.address_vague_retry_count, 2)

        reset_prompt = policy.respond(
            scenario=scenario,
            transcript=[
                DialogueTurn(
                    speaker="service",
                    text="好的，您是在扬州市的哪个区县呢？具体小区门牌号也提供一下呢？",
                    round_index=8,
                ),
                DialogueTurn(speaker="user", text="随便吧", round_index=8),
            ],
            collected_slots=collected_slots,
            runtime_state=state,
        )
        self.assertEqual(
            reset_prompt.reply,
            "好的，需要登记下您的地址，麻烦您完整的说下省、市、区、乡镇，精确到门牌号。",
        )
        self.assertEqual(state.address_vague_retry_count, 0)

    def test_confirmed_collected_address_moves_to_next_slot(self):
        policy = ServiceDialoguePolicy()
        state = ServiceRuntimeState(
            expected_address_confirmation=True,
            pending_address_confirmation="上海市浦东新区锦绣路1888弄6号1202室",
        )
        scenario = build_scenario()
        transcript = [
            DialogueTurn(
                speaker="service",
                text="好的，跟您确认一下，地址是上海市浦东新区锦绣路1888弄6号1202室，对吗？",
                round_index=7,
            ),
            DialogueTurn(speaker="user", text="对，就是这个地址。", round_index=7),
        ]
        collected_slots = {
            "issue_description": "对，家里热水器加热很慢。",
            "surname": "张",
            "phone": "13800138001",
            "address": "",
            "product_model": "",
            "request_type": "fault",
            "availability": "",
            "phone_contactable": "yes",
            "phone_contact_owner": "本人当前来电",
            "phone_collection_attempts": "0",
        }

        result = policy.respond(
            scenario=scenario,
            transcript=transcript,
            collected_slots=collected_slots,
            runtime_state=state,
        )

        self.assertEqual(result.slot_updates["address"], "上海市浦东新区锦绣路1888弄6号1202室")
        self.assertEqual(
            result.reply,
            "好的，您的工单已受理成功，2小时内服务人员会电话联系，预约具体上门时间。",
        )

    def test_installation_address_confirmation_after_arrival_starts_fixed_closing_flow(self):
        policy = ServiceDialoguePolicy()
        state = ServiceRuntimeState(
            expected_address_confirmation=True,
            product_arrival_checked=True,
            pending_address_confirmation="杭州市余杭区五常大道666号3幢1单元802室",
        )
        scenario = build_installation_scenario()
        transcript = [
            DialogueTurn(
                speaker="service",
                text="好的，跟您确认一下，地址是杭州市余杭区五常大道666号3幢1单元802室，对吗？",
                round_index=6,
            ),
            DialogueTurn(speaker="user", text="对，就是这个。", round_index=6),
        ]
        collected_slots = {
            "issue_description": "我这边想报装空气能热水机。",
            "surname": "王",
            "phone": "13900139002",
            "address": "",
            "product_model": "",
            "request_type": "installation",
            "availability": "",
            "phone_contactable": "yes",
            "phone_contact_owner": "本人当前来电",
            "phone_collection_attempts": "0",
            "product_arrived": "yes",
        }

        result = policy.respond(
            scenario=scenario,
            transcript=transcript,
            collected_slots=collected_slots,
            runtime_state=state,
        )

        self.assertEqual(result.slot_updates["address"], "杭州市余杭区五常大道666号3幢1单元802室")
        self.assertEqual(
            result.reply,
            "好的，您的工单已受理成功，2小时内服务人员会电话联系，预约具体上门时间。",
        )
        self.assertFalse(result.is_ready_to_close)
        self.assertTrue(state.awaiting_closing_ack)

    def test_installation_arrival_confirmation_then_starts_surname_collection(self):
        policy = ServiceDialoguePolicy()
        state = ServiceRuntimeState(expected_product_arrival_confirmation=True)
        scenario = build_installation_scenario(product_arrived="yes")
        transcript = [
            DialogueTurn(speaker="service", text="好的，请问空气能热水机到货了没？", round_index=7),
            DialogueTurn(speaker="user", text="到了，放家里了。", round_index=7),
        ]
        collected_slots = {
            "issue_description": "我这边想报装空气能热水机。",
            "surname": "",
            "phone": "",
            "address": "",
            "product_model": "",
            "request_type": "installation",
            "availability": "",
            "phone_contactable": "",
            "phone_contact_owner": "",
            "phone_collection_attempts": "",
            "product_arrived": "",
        }

        result = policy.respond(
            scenario=scenario,
            transcript=transcript,
            collected_slots=collected_slots,
            runtime_state=state,
        )

        self.assertEqual(result.slot_updates["product_arrived"], "yes")
        self.assertEqual(result.reply, "好的，请问您贵姓？")
        self.assertFalse(result.is_ready_to_close)
        self.assertTrue(state.product_arrival_checked)
        self.assertFalse(state.expected_product_arrival_confirmation)

    def test_fault_closing_flow_requires_ack_then_rating_then_end(self):
        policy = ServiceDialoguePolicy()
        state = ServiceRuntimeState()
        scenario = build_scenario(call_start_time="10:30:00")
        collected_slots = {
            "issue_description": "对，家里热水器加热很慢。",
            "surname": "张",
            "phone": "13800138001",
            "address": "上海市浦东新区锦绣路1888弄6号1202室",
            "product_model": "",
            "request_type": "fault",
            "availability": "",
            "phone_contactable": "yes",
            "phone_contact_owner": "本人当前来电",
            "phone_collection_attempts": "0",
            "product_arrived": "",
        }

        appointment = policy.respond(
            scenario=scenario,
            transcript=[
                DialogueTurn(
                    speaker="service",
                    text="跟您确认一下，地址是上海市浦东新区锦绣路1888弄6号1202室，对吗？",
                    round_index=7,
                ),
                DialogueTurn(speaker="user", text="对。", round_index=7),
            ],
            collected_slots=collected_slots,
            runtime_state=state,
        )

        self.assertEqual(
            appointment.reply,
            "好的，您的工单已受理成功，2小时内服务人员会电话联系，预约具体上门时间。",
        )
        self.assertFalse(appointment.is_ready_to_close)
        self.assertTrue(state.awaiting_closing_ack)

        fee_and_survey = policy.respond(
            scenario=scenario,
            transcript=[
                DialogueTurn(
                    speaker="service",
                    text="好的，您的工单已受理成功，2小时内服务人员会电话联系，预约具体上门时间。",
                    round_index=8,
                ),
                DialogueTurn(speaker="user", text="好的", round_index=8),
            ],
            collected_slots=collected_slots,
            runtime_state=state,
        )

        self.assertEqual(
            fee_and_survey.reply,
            "温馨提示，如维修服务产生费用，工程师会详细说明并出示收费标准。 还需要麻烦您对本次通话服务打分，1、非常满意，2、较满意，3、一般，4、较不满，5、非常不满",
        )
        self.assertFalse(fee_and_survey.is_ready_to_close)
        self.assertTrue(state.awaiting_satisfaction_rating)

        end = policy.respond(
            scenario=scenario,
            transcript=[
                DialogueTurn(
                    speaker="service",
                    text="温馨提示，如维修服务产生费用，工程师会详细说明并出示收费标准。 还需要麻烦您对本次通话服务打分，1、非常满意，2、较满意，3、一般，4、较不满，5、非常不满",
                    round_index=9,
                ),
                DialogueTurn(speaker="user", text="1", round_index=9),
            ],
            collected_slots=collected_slots,
            runtime_state=state,
        )

        self.assertEqual(end.reply, "谢谢您的宝贵意见，微信关注“美的官方”，更多服务随心享，再见！")
        self.assertTrue(end.is_ready_to_close)

    def test_address_components_recognize_community_and_letter_building(self):
        components = extract_address_components("广东省佛山市顺德区陈村镇美景豪庭J座4单元502室")

        self.assertEqual(components.community, "美景豪庭")
        self.assertEqual(components.building, "J座")
        self.assertEqual(components.unit, "4单元")
        self.assertEqual(components.room, "502室")

    def test_town_name_with_village_character_does_not_trigger_rural_followup(self):
        policy = ServiceDialoguePolicy()
        state = ServiceRuntimeState(awaiting_full_address=True)
        scenario_data = build_scenario().to_dict()
        scenario_data["customer"]["address"] = "广东省佛山市顺德区陈村镇美景豪庭J座4单元502室"
        scenario = Scenario.from_dict(scenario_data)
        collected_slots = {
            "issue_description": "热水器加热慢。",
            "surname": "张",
            "phone": "13800138001",
            "address": "",
            "product_model": "",
            "request_type": "fault",
            "availability": "",
            "phone_contactable": "yes",
            "phone_contact_owner": "本人当前来电",
            "phone_collection_attempts": "0",
        }

        result = policy.respond(
            scenario=scenario,
            transcript=[
                DialogueTurn(
                    speaker="service",
                    text="好的，您是在佛山市的哪个区县呢？具体小区门牌号也提供一下呢？",
                    round_index=14,
                ),
                DialogueTurn(speaker="user", text="顺德区陈村镇", round_index=14),
            ],
            collected_slots=collected_slots,
            runtime_state=state,
        )

        self.assertEqual(result.reply, "好的，请您继续说一下小区、楼栋和门牌号。")
        self.assertEqual(state.partial_address_candidate, "顺德区陈村镇")

    def test_segmented_address_with_letter_building_starts_confirmation(self):
        policy = ServiceDialoguePolicy()
        state = ServiceRuntimeState(
            awaiting_full_address=True,
            partial_address_candidate="广东省佛山市顺德区陈村镇",
            last_address_followup_prompt="好的，请您继续说一下小区、楼栋和门牌号。",
        )
        scenario_data = build_scenario().to_dict()
        scenario_data["customer"]["address"] = "广东省佛山市顺德区陈村镇美景豪庭J座4单元502室"
        scenario = Scenario.from_dict(scenario_data)
        collected_slots = {
            "issue_description": "热水器加热慢。",
            "surname": "张",
            "phone": "13800138001",
            "address": "",
            "product_model": "",
            "request_type": "fault",
            "availability": "",
            "phone_contactable": "yes",
            "phone_contact_owner": "本人当前来电",
            "phone_collection_attempts": "0",
        }

        result = policy.respond(
            scenario=scenario,
            transcript=[
                DialogueTurn(
                    speaker="service",
                    text="好的，请您继续说一下小区、楼栋和门牌号。",
                    round_index=15,
                ),
                DialogueTurn(
                    speaker="user",
                    text="美景豪庭J座 4 单元 502 室",
                    round_index=15,
                ),
            ],
            collected_slots=collected_slots,
            runtime_state=state,
        )

        self.assertEqual(
            result.reply,
            "好的，跟您确认一下，地址是广东省佛山市顺德区陈村镇美景豪庭J座4单元502室，对吗？",
        )
        self.assertTrue(state.expected_address_confirmation)
        self.assertEqual(
            state.pending_address_confirmation,
            "广东省佛山市顺德区陈村镇美景豪庭J座4单元502室",
        )

    def test_address_reask_frustration_confirms_existing_candidate(self):
        policy = ServiceDialoguePolicy()
        state = ServiceRuntimeState(
            awaiting_full_address=True,
            partial_address_candidate="广东省佛山市顺德区陈村镇美景豪庭J座4单元502室",
            last_address_followup_prompt="好的，请您继续说一下小区、楼栋和门牌号。",
        )
        scenario_data = build_scenario().to_dict()
        scenario_data["customer"]["address"] = "广东省佛山市顺德区陈村镇美景豪庭J座4单元502室"
        scenario = Scenario.from_dict(scenario_data)
        collected_slots = {
            "issue_description": "热水器加热慢。",
            "surname": "张",
            "phone": "13800138001",
            "address": "",
            "product_model": "",
            "request_type": "fault",
            "availability": "",
            "phone_contactable": "yes",
            "phone_contact_owner": "本人当前来电",
            "phone_collection_attempts": "0",
        }

        result = policy.respond(
            scenario=scenario,
            transcript=[
                DialogueTurn(
                    speaker="service",
                    text="好的，请您继续说一下小区、楼栋和门牌号。",
                    round_index=16,
                ),
                DialogueTurn(speaker="user", text="啥我已经提供了啊", round_index=16),
            ],
            collected_slots=collected_slots,
            runtime_state=state,
        )

        self.assertEqual(
            result.reply,
            "好的，跟您确认一下，地址是广东省佛山市顺德区陈村镇美景豪庭J座4单元502室，对吗？",
        )
        self.assertTrue(state.expected_address_confirmation)
        self.assertEqual(
            state.pending_address_confirmation,
            "广东省佛山市顺德区陈村镇美景豪庭J座4单元502室",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
