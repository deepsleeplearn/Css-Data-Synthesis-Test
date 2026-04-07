from __future__ import annotations

import random
import unittest

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

        self.assertEqual(result.reply, "非常抱歉，给您添麻烦了，我这就安排是否上门维修，请问您贵姓")

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
        self.assertEqual(result.reply, "非常抱歉，给您添麻烦了，我这就安排是否上门维修，请问您贵姓")

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
        self.assertEqual(result.reply, "非常抱歉，给您添麻烦了，我这就安排是否上门维修，请问您贵姓")

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
            "您输入的号码有误，请重新在拨号盘上输入您的联系方式，并以#号键结束",
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
            "请您继续提供一下小区、楼栋和门牌号。",
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
                DialogueTurn(speaker="service", text="请您继续提供一下小区、楼栋和门牌号。", round_index=6),
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

    def test_address_followup_requests_region_when_user_first_provides_detail_only(self):
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

        self.assertEqual(first_result.reply, "请您再补充一下省、市、区和乡镇街道。")
        self.assertEqual(state.partial_address_candidate, "锦绣路1888弄6号1202室")

        second_result = policy.respond(
            scenario=scenario,
            transcript=[
                DialogueTurn(speaker="service", text="请您再补充一下省、市、区和乡镇街道。", round_index=6),
                DialogueTurn(speaker="user", text="上海市浦东新区", round_index=6),
            ],
            collected_slots=collected_slots,
            runtime_state=state,
        )

        self.assertEqual(
            second_result.reply,
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

        self.assertEqual(result.reply, "请您继续提供一下小区、楼栋和门牌号。")
        self.assertFalse(state.expected_address_confirmation)
        self.assertEqual(
            state.partial_address_candidate,
            "湖北省武汉市洪山区尤李湾路56号万珑小区5栋2单元",
        )

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
        self.assertEqual(result.reply, "好的，请问您贵姓")
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


if __name__ == "__main__":
    unittest.main(verbosity=2)
