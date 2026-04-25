from __future__ import annotations

import random
import unittest

from css_data_synthesis_test.address_utils import extract_address_components
from css_data_synthesis_test.schemas import DialogueTurn, Scenario
from css_data_synthesis_test.service_policy import (
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

            self.assertEqual(result.reply, "非常抱歉，给您添麻烦了，我这就安排师傅上门维修，麻烦问下您姓什么？")
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

        self.assertEqual(result.reply, "非常抱歉，给您添麻烦了，我这就安排师傅上门维修，请问您贵姓？")

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

    def test_water_heater_opening_yes_asks_fixed_type_prompt(self):
        def fake_resolution(*, user_text: str, current_brand: str, current_request_type: str, previous_service_text: str, user_round_index: int):
            return {"intent": "yes", "brand": "", "request_type": "", "heater_type": ""}

        policy = ServiceDialoguePolicy(
            water_heater_opening_resolution_callback=fake_resolution,
        )
        scenario = build_scenario()
        scenario.product.category = "热水器"
        scenario.hidden_context["ivr_opening_overridden"] = True
        scenario.hidden_context["ivr_product_kind"] = "water_heater"
        state = ServiceRuntimeState(
            expected_water_heater_opening_confirmation=True,
            pending_water_heater_brand="美的",
            pending_water_heater_request_type="fault",
        )

        result = policy.respond(
            scenario=scenario,
            transcript=[
                DialogueTurn(speaker="service", text="您好，很高兴为您服务，请问是美的热水器需要维修吗？", round_index=1),
                DialogueTurn(speaker="user", text="对，是的。", round_index=2),
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

        self.assertEqual(result.reply, "好的，请问您的热水器是空气能热水器，还是燃气热水器、还是电热水器？")
        self.assertTrue(state.expected_water_heater_type_selection)

    def test_water_heater_opening_request_correction_updates_fixed_type_prompt(self):
        def fake_resolution(*, user_text: str, current_brand: str, current_request_type: str, previous_service_text: str, user_round_index: int):
            return {"intent": "no", "brand": "", "request_type": "installation", "heater_type": ""}

        policy = ServiceDialoguePolicy(
            water_heater_opening_resolution_callback=fake_resolution,
        )
        scenario = build_scenario()
        scenario.product.category = "热水器"
        scenario.hidden_context["ivr_opening_overridden"] = True
        scenario.hidden_context["ivr_product_kind"] = "water_heater"
        state = ServiceRuntimeState(
            expected_water_heater_opening_confirmation=True,
            pending_water_heater_brand="美的",
            pending_water_heater_request_type="fault",
        )

        result = policy.respond(
            scenario=scenario,
            transcript=[
                DialogueTurn(speaker="service", text="您好，很高兴为您服务，请问是美的热水器需要维修吗？", round_index=1),
                DialogueTurn(speaker="user", text="不是维修，是安装。", round_index=2),
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

        self.assertEqual(result.reply, "好的，请问您要安装的美的热水器是空气能热水器，还是燃气热水器、还是电热水器？")
        self.assertEqual(state.pending_water_heater_request_type, "installation")

    def test_water_heater_opening_short_request_correction_updates_fixed_type_prompt(self):
        def fake_resolution(*, user_text: str, current_brand: str, current_request_type: str, previous_service_text: str, user_round_index: int):
            return {"intent": "no", "brand": "", "request_type": "installation", "heater_type": ""}

        policy = ServiceDialoguePolicy(
            water_heater_opening_resolution_callback=fake_resolution,
        )
        scenario = build_scenario()
        scenario.product.category = "热水器"
        scenario.hidden_context["ivr_opening_overridden"] = True
        scenario.hidden_context["ivr_product_kind"] = "water_heater"
        state = ServiceRuntimeState(
            expected_water_heater_opening_confirmation=True,
            pending_water_heater_brand="美的",
            pending_water_heater_request_type="fault",
        )

        result = policy.respond(
            scenario=scenario,
            transcript=[
                DialogueTurn(speaker="service", text="您好，很高兴为您服务，请问是美的热水器需要维修吗？", round_index=1),
                DialogueTurn(speaker="user", text="是安装。", round_index=2),
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

        self.assertEqual(result.reply, "好的，请问您要安装的美的热水器是空气能热水器，还是燃气热水器、还是电热水器？")
        self.assertEqual(state.pending_water_heater_request_type, "installation")

    def test_water_heater_type_air_energy_enters_product_routing(self):
        def fake_resolution(*, user_text: str, current_brand: str, current_request_type: str, previous_service_text: str, user_round_index: int):
            return {"intent": "no", "brand": "", "request_type": "", "heater_type": "air_energy"}

        policy = ServiceDialoguePolicy(
            water_heater_opening_resolution_callback=fake_resolution,
        )
        scenario = build_scenario()
        scenario.product.category = "热水器"
        scenario.hidden_context["ivr_opening_overridden"] = True
        scenario.hidden_context["ivr_product_kind"] = "water_heater"
        scenario.hidden_context["product_routing_plan"] = {
            "enabled": True,
            "steps": [
                {
                    "prompt_key": "brand_or_series",
                    "prompt": "请问您的空气能是什么具体品牌或系列呢？",
                    "answer_key": "entry.unknown",
                    "answer_value": "不知道品牌或系列",
                    "answer_instruction": "自然表达自己不知道品牌或系列。",
                }
            ],
            "trace": [],
            "result": "",
            "summary": "",
        }
        state = ServiceRuntimeState(
            expected_water_heater_type_selection=True,
            pending_water_heater_brand="美的",
            pending_water_heater_request_type="fault",
        )

        result = policy.respond(
            scenario=scenario,
            transcript=[
                DialogueTurn(speaker="service", text="好的，请问您的热水器是空气能热水器，还是燃气热水器、还是电热水器？", round_index=2),
                DialogueTurn(speaker="user", text="空气能热水器。", round_index=3),
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
                "product_routing_result": "",
            },
            runtime_state=state,
        )

        self.assertEqual(result.reply, "请问您的空气能是什么具体品牌或系列呢？")
        self.assertEqual(scenario.product.category, "空气能热水机")
        self.assertEqual(result.slot_updates["request_type"], "fault")
        self.assertTrue(state.expected_product_routing_response)

    def test_water_heater_request_changed_to_installation_then_gas_asks_arrival(self):
        responses = [
            {"intent": "no", "brand": "", "request_type": "installation", "heater_type": ""},
            {"intent": "no", "brand": "", "request_type": "", "heater_type": "gas"},
        ]

        def fake_resolution(*, user_text: str, current_brand: str, current_request_type: str, previous_service_text: str, user_round_index: int):
            return responses.pop(0)

        policy = ServiceDialoguePolicy(
            water_heater_opening_resolution_callback=fake_resolution,
        )
        scenario = build_scenario()
        scenario.product.category = "热水器"
        scenario.hidden_context["ivr_opening_overridden"] = True
        scenario.hidden_context["ivr_product_kind"] = "water_heater"
        state = ServiceRuntimeState(
            expected_water_heater_opening_confirmation=True,
            pending_water_heater_brand="美的",
            pending_water_heater_request_type="fault",
        )

        first_result = policy.respond(
            scenario=scenario,
            transcript=[
                DialogueTurn(speaker="service", text="您好，很高兴为您服务，请问是美的热水器需要维修吗？", round_index=1),
                DialogueTurn(speaker="user", text="是安装。", round_index=2),
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
        self.assertEqual(
            first_result.reply,
            "好的，请问您要安装的美的热水器是空气能热水器，还是燃气热水器、还是电热水器？",
        )

        second_result = policy.respond(
            scenario=scenario,
            transcript=[
                DialogueTurn(speaker="service", text=first_result.reply, round_index=2),
                DialogueTurn(speaker="user", text="燃气热水器。", round_index=3),
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
        self.assertEqual(second_result.reply, "好的，请问燃气热水器已经送到了吗？")
        self.assertEqual(scenario.request.request_type, "installation")
        self.assertEqual(second_result.slot_updates["request_type"], "installation")

    def test_water_heater_request_changed_to_fault_then_electric_asks_issue(self):
        responses = [
            {"intent": "no", "brand": "", "request_type": "fault", "heater_type": ""},
            {"intent": "no", "brand": "", "request_type": "", "heater_type": "electric"},
        ]

        def fake_resolution(*, user_text: str, current_brand: str, current_request_type: str, previous_service_text: str, user_round_index: int):
            return responses.pop(0)

        policy = ServiceDialoguePolicy(
            water_heater_opening_resolution_callback=fake_resolution,
        )
        scenario = build_scenario()
        scenario.product.category = "热水器"
        scenario.request.request_type = "installation"
        scenario.hidden_context["ivr_opening_overridden"] = True
        scenario.hidden_context["ivr_product_kind"] = "water_heater"
        state = ServiceRuntimeState(
            expected_water_heater_opening_confirmation=True,
            pending_water_heater_brand="美的",
            pending_water_heater_request_type="installation",
        )

        first_result = policy.respond(
            scenario=scenario,
            transcript=[
                DialogueTurn(speaker="service", text="您好，很高兴为您服务，请问是美的热水器需要安装吗？", round_index=1),
                DialogueTurn(speaker="user", text="是维修。", round_index=2),
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
        self.assertEqual(
            first_result.reply,
            "好的，请问您要维修的美的热水器是空气能热水器，还是燃气热水器、还是电热水器？",
        )

        second_result = policy.respond(
            scenario=scenario,
            transcript=[
                DialogueTurn(speaker="service", text=first_result.reply, round_index=2),
                DialogueTurn(speaker="user", text="电热水器。", round_index=3),
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
        self.assertEqual(second_result.reply, "好的，请问电热水器现在是出现了什么问题？")
        self.assertEqual(scenario.request.request_type, "fault")
        self.assertEqual(second_result.slot_updates["request_type"], "fault")

    def test_water_heater_opening_brand_and_request_correction_updates_fixed_type_prompt(self):
        def fake_resolution(*, user_text: str, current_brand: str, current_request_type: str, previous_service_text: str, user_round_index: int):
            return {"intent": "no", "brand": "海尔", "request_type": "installation", "heater_type": ""}

        policy = ServiceDialoguePolicy(
            water_heater_opening_resolution_callback=fake_resolution,
        )
        scenario = build_scenario()
        scenario.product.category = "热水器"
        scenario.hidden_context["ivr_opening_overridden"] = True
        scenario.hidden_context["ivr_product_kind"] = "water_heater"
        state = ServiceRuntimeState(
            expected_water_heater_opening_confirmation=True,
            pending_water_heater_brand="美的",
            pending_water_heater_request_type="fault",
        )

        result = policy.respond(
            scenario=scenario,
            transcript=[
                DialogueTurn(
                    speaker="service",
                    text="您好，很高兴为您服务，请问是美的热水器需要维修吗？",
                    round_index=1,
                ),
                DialogueTurn(speaker="user", text="不是美的，是海尔，要安装。", round_index=2),
            ],
            collected_slots={
                "issue_description": "",
                "surname": "",
                "phone": "",
                "address": "",
                "product_model": "",
                "request_type": "",
                "availability": "",
            },
            runtime_state=state,
        )

        self.assertEqual(
            result.reply,
            "好的，请问您要安装的海尔热水器是空气能热水器，还是燃气热水器、还是电热水器？",
        )
        self.assertTrue(state.expected_water_heater_type_selection)

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

        self.assertEqual(result.reply, "请您在电话拨号盘上输入您的联系号码，并以#号键结束。")
        self.assertEqual(result.slot_updates["phone_contactable"], "yes")
        self.assertEqual(result.slot_updates["phone_contact_owner"], "本人当前来电")
        self.assertTrue(state.awaiting_phone_keypad_input)

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

    def test_cli_freeform_contactable_bare_neng_uses_mock_current_call_phone(self):
        policy = ServiceDialoguePolicy()
        state = ServiceRuntimeState(expected_contactable_confirmation=True)
        scenario = build_freeform_cli_scenario(request_type="fault")
        scenario.hidden_context["contact_phone"] = "13912345678"
        scenario.hidden_context["contact_phone_owner"] = "本人当前来电"
        transcript = [
            DialogueTurn(speaker="service", text="请问您当前这个来电号码能联系到您吗？", round_index=4),
            DialogueTurn(speaker="user", text="能", round_index=4),
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

        self.assertEqual(result.reply, "请您在电话拨号盘上输入您的联系号码，并以#号键结束。")
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

        self.assertEqual(result.reply, "请您在电话拨号盘上输入您的联系号码，并以#号键结束。")
        self.assertEqual(result.slot_updates["phone_contactable"], "no")
        self.assertEqual(result.slot_updates["phone_contact_owner"], "另一个号码")
        self.assertTrue(state.awaiting_phone_keypad_input)

    def test_cli_freeform_contactable_spoken_valid_phone_skips_keypad_and_confirms_directly(self):
        def fake_contact_inference(*, user_text: str, user_round_index: int):
            self.assertEqual(user_text, "你联系这个号码吧，13978201465")
            self.assertEqual(user_round_index, 4)
            return {"intent": "no"}

        policy = ServiceDialoguePolicy(
            ok_prefix_probability=0.0,
            contact_intent_inference_callback=fake_contact_inference,
        )
        state = ServiceRuntimeState(expected_contactable_confirmation=True)
        scenario = build_freeform_cli_scenario()
        scenario.hidden_context["contact_phone_owner"] = "另一个号码"
        transcript = [
            DialogueTurn(speaker="service", text="请问您当前这个来电号码能联系到您吗？", round_index=4),
            DialogueTurn(speaker="user", text="你联系这个号码吧，13978201465", round_index=4),
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

        self.assertEqual(result.reply, "请您在电话拨号盘上输入您的联系号码，并以#号键结束。")
        self.assertEqual(result.slot_updates["phone_contactable"], "no")
        self.assertEqual(result.slot_updates["phone_contact_owner"], "另一个号码")
        self.assertTrue(state.awaiting_phone_keypad_input)
        self.assertTrue(policy.last_used_model_intent_inference)

    def test_cli_freeform_contactable_spoken_invalid_phone_still_uses_keypad(self):
        def fake_contact_inference(*, user_text: str, user_round_index: int):
            self.assertEqual(user_text, "你联系这个号码吧，1397820146")
            self.assertEqual(user_round_index, 4)
            return {"intent": "no"}

        policy = ServiceDialoguePolicy(
            ok_prefix_probability=0.0,
            contact_intent_inference_callback=fake_contact_inference,
        )
        state = ServiceRuntimeState(expected_contactable_confirmation=True)
        scenario = build_freeform_cli_scenario()
        scenario.hidden_context["contact_phone_owner"] = "另一个号码"
        transcript = [
            DialogueTurn(speaker="service", text="请问您当前这个来电号码能联系到您吗？", round_index=4),
            DialogueTurn(speaker="user", text="你联系这个号码吧，1397820146", round_index=4),
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

        self.assertEqual(result.reply, "请您在电话拨号盘上输入您的联系号码，并以#号键结束。")
        self.assertEqual(result.slot_updates["phone_contactable"], "no")
        self.assertEqual(result.slot_updates["phone_contact_owner"], "另一个号码")
        self.assertTrue(state.awaiting_phone_keypad_input)
        self.assertFalse(state.expected_phone_number_confirmation)
        self.assertTrue(policy.last_used_model_intent_inference)

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

        self.assertEqual(result.reply, "请您在电话拨号盘上输入您的联系号码，并以#号键结束。")
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

        self.assertEqual(result.reply, "请您在电话拨号盘上输入您的联系号码，并以#号键结束。")
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

        self.assertEqual(result.reply, "请您在电话拨号盘上输入您的联系号码，并以#号键结束。")
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

        self.assertEqual(result.reply, "请您在电话拨号盘上输入您的联系号码，并以#号键结束。")
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
        self.assertEqual(result.reply, "非常抱歉，给您添麻烦了，我这就安排师傅上门维修，请问您贵姓？")

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

    def test_initial_freeform_user_turn_can_transfer_to_human(self):
        policy = ServiceDialoguePolicy(ok_prefix_probability=0.0)
        state = ServiceRuntimeState()
        scenario = build_freeform_cli_scenario(request_type="fault")
        transcript = [
            DialogueTurn(speaker="user", text="帮我转人工", round_index=1),
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
            "product_routing_result": "",
        }

        result = policy.respond(
            scenario=scenario,
            transcript=transcript,
            collected_slots=collected_slots,
            runtime_state=state,
        )

        self.assertEqual(result.reply, "请稍等，正在为您转接人工服务。")
        self.assertEqual(result.close_status, "transferred")
        self.assertEqual(result.close_reason, "user_requested_human")
        self.assertEqual(result.slot_updates["request_type"], "fault")
        self.assertEqual(result.slot_updates["product_routing_result"], "转人工")

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
            "非常抱歉，给您添麻烦了，我这就安排师傅上门维修，请问您的空气能是什么品牌或系列呢？",
        )
        self.assertEqual(result.slot_updates["issue_description"], "是的，热水器不加热，想报修。")
        self.assertTrue(state.expected_product_routing_response)

    def test_cli_freeform_fault_opening_product_info_does_not_fill_issue_description(self):
        policy = ServiceDialoguePolicy(ok_prefix_probability=0.0)
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
                    "prompt": "请问您的空气能是什么具体品牌或系列呢？",
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
            DialogueTurn(speaker="user", text="是的额，一个750升的热水器", round_index=2),
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
        self.assertEqual(result.reply, "请问您的空气能是什么具体品牌或系列呢？")
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
            "非常抱歉，给您添麻烦了，我这就安排师傅上门维修，请问您的空气能是什么品牌或系列呢？",
        )

    def test_fault_opening_forces_model_intent_inference_before_product_routing(self):
        opening_calls: list[tuple[str, int]] = []
        extraction_calls: list[tuple[str, int]] = []

        def fake_opening_inference(*, user_text: str, user_round_index: int):
            opening_calls.append((user_text, user_round_index))
            return {"intent": "issue_detail"}

        def fake_issue_extraction(*, user_text: str, user_round_index: int):
            extraction_calls.append((user_text, user_round_index))
            return {"issue_description": "机器现在不出热水了"}

        policy = ServiceDialoguePolicy(
            ok_prefix_probability=0.0,
            opening_intent_inference_callback=fake_opening_inference,
            issue_description_extraction_callback=fake_issue_extraction,
        )
        state = ServiceRuntimeState()
        scenario = build_scenario()
        scenario.hidden_context["product_routing_plan"] = {
            "enabled": True,
            "result": "家用 + 可直接确认机型",
            "trace": ["entry.unknown"],
            "summary": "entry.unknown -> 家用 + 可直接确认机型",
            "steps": [
                {
                    "prompt_key": "brand_or_series",
                    "prompt": "请问您的空气能是什么具体品牌或系列呢？",
                    "answer_key": "entry.unknown",
                    "answer_value": "不知道品牌或系列",
                    "answer_instruction": "自然表达自己不知道品牌或系列。",
                }
            ],
        }
        transcript = [
            DialogueTurn(
                speaker="service",
                text="您好，很高兴为您服务，请问是美的空气能热水器需要维修吗？",
                round_index=1,
            ),
            DialogueTurn(
                speaker="user",
                text="对，是的，机器现在不出热水了。",
                round_index=2,
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
            "product_arrived": "",
        }

        result = policy.respond(
            scenario=scenario,
            transcript=transcript,
            collected_slots=collected_slots,
            runtime_state=state,
        )

        self.assertEqual(opening_calls, [("对，是的，机器现在不出热水了。", 2)])
        self.assertEqual(extraction_calls, [("对，是的，机器现在不出热水了。", 2)])
        self.assertEqual(result.slot_updates["issue_description"], "机器现在不出热水了")
        self.assertEqual(
            result.reply,
            "非常抱歉，给您添麻烦了，我这就安排师傅上门维修，请问您的空气能是什么具体品牌或系列呢？",
        )
        self.assertTrue(state.expected_product_routing_response)

    def test_cli_freeform_fault_model_issue_detail_without_specific_fault_does_not_fallback_to_raw_text(self):
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
            DialogueTurn(speaker="user", text="是的额，一个750升的热水器", round_index=2),
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
        self.assertEqual(result.reply, "请问您的空气能是什么品牌或系列呢？")

    def test_cli_freeform_fault_issue_detail_does_not_fallback_to_raw_text_when_model_extraction_is_empty(self):
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

        self.assertNotIn("issue_description", result.slot_updates)
        self.assertEqual(result.reply, "请问空气能热水机现在是出现了什么问题？")

    def test_fault_issue_prompt_uses_model_extraction_and_then_prepends_apology(self):
        def fake_issue_extraction(*, user_text: str, user_round_index: int):
            self.assertEqual(user_text, "出水不热，开到 80 度烧了两小时都才只要 40 度")
            self.assertEqual(user_round_index, 5)
            return {"issue_description": "出水不热，设定80度加热两小时后水温只有40度"}

        policy = ServiceDialoguePolicy(
            ok_prefix_probability=0.0,
            issue_description_extraction_callback=fake_issue_extraction,
        )
        state = ServiceRuntimeState(product_routing_completed=True)
        scenario = build_freeform_cli_scenario(request_type="fault")
        transcript = [
            DialogueTurn(speaker="service", text="请问空气能热水机现在是出现了什么问题？", round_index=5),
            DialogueTurn(speaker="user", text="出水不热，开到 80 度烧了两小时都才只要 40 度", round_index=5),
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
            "product_routing_result": "楼宇 + 可直接确认机型",
        }

        result = policy.respond(
            scenario=scenario,
            transcript=transcript,
            collected_slots=collected_slots,
            runtime_state=state,
        )

        self.assertEqual(
            result.slot_updates["issue_description"],
            "出水不热，设定80度加热两小时后水温只有40度",
        )
        self.assertEqual(result.reply, "非常抱歉，给您添麻烦了，我这就安排师傅上门维修，请问您贵姓？")

    def test_fault_issue_prompt_requires_specific_fault_description(self):
        policy = ServiceDialoguePolicy(ok_prefix_probability=0.0)
        state = ServiceRuntimeState()
        scenario = build_scenario()
        transcript = [
            DialogueTurn(speaker="service", text="请问空气能热水器现在是出现了什么问题？", round_index=2),
            DialogueTurn(speaker="user", text="就是东西坏了", round_index=2),
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

        self.assertNotIn("issue_description", result.slot_updates)
        self.assertEqual(result.reply, "请问空气能热水器现在是出现了什么问题？")

    def test_fault_issue_prompt_accepts_component_broken_description(self):
        policy = ServiceDialoguePolicy(ok_prefix_probability=0.0)
        state = ServiceRuntimeState()
        scenario = build_scenario()
        transcript = [
            DialogueTurn(speaker="service", text="请问空气能热水器现在是出现了什么问题？", round_index=5),
            DialogueTurn(speaker="user", text="面板坏了", round_index=6),
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

        self.assertEqual(result.slot_updates["issue_description"], "面板坏了")
        self.assertEqual(result.reply, "非常抱歉，给您添麻烦了，我这就安排师傅上门维修，请问您贵姓？")

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

    def test_cli_freeform_product_routing_cooling_or_little_swan_transfers_to_human(self):
        policy = ServiceDialoguePolicy(ok_prefix_probability=0.0)
        state = ServiceRuntimeState(
            expected_product_routing_response=True,
            product_routing_step_index=0,
            product_routing_observed_trace=[],
        )
        scenario = build_freeform_cli_scenario(request_type="fault")
        scenario.hidden_context["product_routing_plan"] = {
            "enabled": True,
            "result": "",
            "trace": [],
            "summary": "",
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

        result = policy.respond(
            scenario=scenario,
            transcript=[
                DialogueTurn(speaker="service", text="请问您的空气能是什么品牌或系列呢？", round_index=2),
                DialogueTurn(speaker="user", text="小天鹅", round_index=3),
            ],
            collected_slots={
                "issue_description": "热水器不加热",
                "surname": "",
                "phone": "",
                "address": "",
                "request_type": "fault",
                "phone_contactable": "",
                "phone_contact_owner": "",
                "phone_collection_attempts": "",
                "product_arrived": "",
                "product_routing_result": "",
            },
            runtime_state=state,
        )

        self.assertEqual(result.reply, "请稍等，正在为您转接人工服务。")
        self.assertEqual(result.close_status, "transferred")
        self.assertEqual(result.close_reason, "product_routing_human")
        self.assertEqual(result.slot_updates["product_routing_result"], "转人工")

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

    def test_product_routing_routes_to_building_when_property_year_is_unknown(self):
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

        self.assertEqual(result.reply, "请问空气能热水机现在是出现了什么问题？")
        self.assertEqual(result.slot_updates["product_routing_result"], "楼宇 + 可直接确认机型")
        self.assertEqual(
            state.product_routing_observed_trace,
            ["entry.unknown", "purpose.unknown", "scene.yes", "purchase.property_bundle", "property_year.unknown"],
        )
        self.assertTrue(state.product_routing_completed)
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

    def test_address_confirmation_always_invokes_model_even_when_heuristic_is_no(self):
        calls: list[tuple[str, str]] = []

        def fake_confirmation_inference(*, prompt_kind: str, user_text: str):
            calls.append((prompt_kind, user_text))
            return {"intent": "no"}

        policy = ServiceDialoguePolicy(
            confirmation_intent_inference_callback=fake_confirmation_inference,
        )
        state = ServiceRuntimeState(expected_address_confirmation=True)
        scenario = build_scenario(
            service_known_address=True,
            service_known_address_value="广东省佛山市禅城区祖庙街道恒大绿洲3号楼3层304室",
            service_known_address_matches_actual=False,
        )

        result = policy.respond(
            scenario=scenario,
            transcript=[
                DialogueTurn(
                    speaker="service",
                    text="好的，您的地址是广东省佛山市禅城区祖庙街道恒大绿洲3号楼3层304室，对吗？",
                    round_index=6,
                ),
                DialogueTurn(speaker="user", text="不是,换一个", round_index=7),
            ],
            collected_slots={
                "issue_description": "漏水。",
                "surname": "张",
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

        self.assertEqual(calls, [("address_confirmation", "不是,换一个")])
        self.assertEqual(result.reply, "好的，需要登记下您的地址，麻烦您完整的说下省、市、区、乡镇，精确到门牌号。")

    def test_address_confirmation_switch_request_does_not_call_address_extraction_model(self):
        confirmation_calls: list[tuple[str, str]] = []
        address_inference_called = False

        def fake_confirmation_inference(*, prompt_kind: str, user_text: str):
            confirmation_calls.append((prompt_kind, user_text))
            return {"intent": "no"}

        def fake_address_inference(**_: str):
            nonlocal address_inference_called
            address_inference_called = True
            return {
                "address_candidate": "新地址",
                "merged_address_candidate": "新地址",
                "granularity": "locality",
            }

        policy = ServiceDialoguePolicy(
            confirmation_intent_inference_callback=fake_confirmation_inference,
            address_inference_callback=fake_address_inference,
        )
        state = ServiceRuntimeState(expected_address_confirmation=True)
        scenario = build_scenario(
            service_known_address=True,
            service_known_address_value="贵州省遵义市播州区南白街道锦绣苑8号楼5层501室",
            service_known_address_matches_actual=False,
        )

        result = policy.respond(
            scenario=scenario,
            transcript=[
                DialogueTurn(
                    speaker="service",
                    text="好的，您的地址是贵州省遵义市播州区南白街道锦绣苑8号楼5层501室，对吗？",
                    round_index=5,
                ),
                DialogueTurn(speaker="user", text="不是,留个新地址", round_index=6),
            ],
            collected_slots={
                "issue_description": "面板故障。",
                "surname": "汪",
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

        self.assertEqual(confirmation_calls, [("address_confirmation", "不是,留个新地址")])
        self.assertFalse(address_inference_called)
        self.assertEqual(result.reply, "好的，需要登记下您的地址，麻烦您完整的说下省、市、区、乡镇，精确到门牌号。")
        self.assertEqual(state.partial_address_candidate, "")

    def test_address_confirmation_move_phrase_restarts_full_address_collection(self):
        confirmation_calls: list[tuple[str, str]] = []
        address_inference_called = False

        def fake_confirmation_inference(*, prompt_kind: str, user_text: str):
            confirmation_calls.append((prompt_kind, user_text))
            return {"intent": "no"}

        def fake_address_inference(**_: str):
            nonlocal address_inference_called
            address_inference_called = True
            return {
                "address_candidate": "我换地方了",
                "merged_address_candidate": "我换地方了",
                "granularity": "locality",
            }

        policy = ServiceDialoguePolicy(
            confirmation_intent_inference_callback=fake_confirmation_inference,
            address_inference_callback=fake_address_inference,
        )
        state = ServiceRuntimeState(expected_address_confirmation=True)
        scenario = build_scenario(
            service_known_address=True,
            service_known_address_value="湖南省长沙市芙蓉区湘湖街道幸福花园2号楼5层504室",
            service_known_address_matches_actual=False,
        )

        result = policy.respond(
            scenario=scenario,
            transcript=[
                DialogueTurn(
                    speaker="service",
                    text="好的，您的地址是湖南省长沙市芙蓉区湘湖街道幸福花园2号楼5层504室，对吗？",
                    round_index=5,
                ),
                DialogueTurn(speaker="user", text="不是,我换地方了", round_index=6),
            ],
            collected_slots={
                "issue_description": "面板故障。",
                "surname": "汪",
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

        self.assertEqual(confirmation_calls, [("address_confirmation", "不是,我换地方了")])
        self.assertFalse(address_inference_called)
        self.assertEqual(result.reply, "好的，需要登记下您的地址，麻烦您完整的说下省、市、区、乡镇，精确到门牌号。")

    def test_address_confirmation_weak_rule_case_uses_model_for_region_correction(self):
        confirmation_calls: list[tuple[str, str]] = []
        address_calls: list[dict[str, str]] = []

        def fake_confirmation_inference(*, prompt_kind: str, user_text: str):
            confirmation_calls.append((prompt_kind, user_text))
            return {"intent": "no"}

        def fake_address_inference(**kwargs: str):
            address_calls.append(kwargs)
            self.assertEqual(kwargs["confirmation_address"], "天津市南开区万兴街道碧桂园9座6楼603室")
            self.assertEqual(kwargs["user_text"], "不在天津,在江苏")
            return {
                "address_candidate": "江苏",
                "merged_address_candidate": "江苏",
                "granularity": "admin_region",
            }

        policy = ServiceDialoguePolicy(
            confirmation_intent_inference_callback=fake_confirmation_inference,
            address_inference_callback=fake_address_inference,
        )
        state = ServiceRuntimeState(expected_address_confirmation=True)
        scenario = build_freeform_cli_scenario(request_type="fault")
        scenario.hidden_context["service_known_address"] = True
        scenario.hidden_context["service_known_address_value"] = "天津市南开区万兴街道碧桂园9座6楼603室"
        scenario.hidden_context["service_known_address_matches_actual"] = False

        result = policy.respond(
            scenario=scenario,
            transcript=[
                DialogueTurn(
                    speaker="service",
                    text="好的，您的地址是天津市南开区万兴街道碧桂园9座6楼603室，对吗？",
                    round_index=6,
                ),
                DialogueTurn(speaker="user", text="不在天津,在江苏", round_index=7),
            ],
            collected_slots={
                "issue_description": "不制热。",
                "surname": "张",
                "phone": "13800138001",
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

        self.assertEqual(confirmation_calls, [("address_confirmation", "不在天津,在江苏")])
        self.assertEqual(len(address_calls), 1)
        self.assertEqual(
            result.reply,
            "好的，请问是江苏省哪个城市的哪个区和街道呢？",
        )
        self.assertEqual(state.partial_address_candidate, "江苏省")
        self.assertTrue(state.awaiting_full_address)

    def test_address_confirmation_switch_with_county_and_community_reasks_region_not_building(self):
        def fake_confirmation_inference(*, prompt_kind: str, user_text: str):
            self.assertEqual(prompt_kind, "address_confirmation")
            self.assertEqual(user_text, "不是,换一个,我在三门县江南壹号")
            return {"intent": "no"}

        policy = ServiceDialoguePolicy(
            confirmation_intent_inference_callback=fake_confirmation_inference,
        )
        state = ServiceRuntimeState(expected_address_confirmation=True)
        scenario = build_scenario(
            service_known_address=True,
            service_known_address_value="青海省西宁市城中区饮马街街道新湖国际11幢3单元1701室",
            service_known_address_matches_actual=False,
        )
        scenario.hidden_context["interactive_test_freeform"] = True
        scenario.hidden_context["manual_test_address_precision_reference"] = False

        result = policy.respond(
            scenario=scenario,
            transcript=[
                DialogueTurn(
                    speaker="service",
                    text="好的，您的地址是青海省西宁市城中区饮马街街道新湖国际11幢3单元1701室，对吗？",
                    round_index=5,
                ),
                DialogueTurn(speaker="user", text="不是,换一个,我在三门县江南壹号", round_index=6),
            ],
            collected_slots={
                "issue_description": "面板故障。",
                "surname": "汪",
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

        self.assertEqual(state.partial_address_candidate, "三门县江南壹号")
        self.assertEqual(result.reply, "好的，请您说一下省、市、区和街道。")

    def test_address_confirmation_cross_city_correction_without_province_does_not_inherit_old_province(self):
        def fake_confirmation_inference(*, prompt_kind: str, user_text: str):
            self.assertEqual(prompt_kind, "address_confirmation")
            self.assertEqual(user_text, "不是,我在扬州市宝应县")
            return {"intent": "no"}

        policy = ServiceDialoguePolicy(
            confirmation_intent_inference_callback=fake_confirmation_inference,
        )
        state = ServiceRuntimeState(expected_address_confirmation=True)
        scenario_data = build_scenario(
            service_known_address=True,
            service_known_address_value="四川省绵阳市涪城区石塘街道学府佳苑1号楼1单元303室",
            service_known_address_matches_actual=False,
        ).to_dict()
        scenario_data["customer"]["address"] = "江苏省扬州市宝应县阳光锦城10号楼510室"
        scenario = Scenario.from_dict(scenario_data)

        result = policy.respond(
            scenario=scenario,
            transcript=[
                DialogueTurn(
                    speaker="service",
                    text="好的，您的地址是四川省绵阳市涪城区石塘街道学府佳苑1号楼1单元303室，对吗？",
                    round_index=5,
                ),
                DialogueTurn(
                    speaker="user",
                    text="不是,我在扬州市宝应县",
                    round_index=6,
                ),
            ],
            collected_slots={
                "issue_description": "不制热。",
                "surname": "张",
                "phone": "13800138001",
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

        self.assertEqual(result.reply, "请问具体是在哪个小区或村呢？尽量详细到门牌号。")
        self.assertFalse(state.partial_address_candidate.startswith("四川省"))
        self.assertTrue(state.partial_address_candidate.endswith("扬州市宝应县"))

    def test_address_confirmation_cross_city_correction_prefers_model_province_backfill(self):
        confirmation_calls: list[tuple[str, str]] = []
        address_calls: list[dict[str, str]] = []

        def fake_confirmation_inference(*, prompt_kind: str, user_text: str):
            confirmation_calls.append((prompt_kind, user_text))
            return {"intent": "no"}

        def fake_address_inference(**kwargs: str):
            address_calls.append(kwargs)
            self.assertEqual(
                kwargs["confirmation_address"],
                "四川省绵阳市涪城区石塘街道学府佳苑1号楼1单元303室",
            )
            self.assertEqual(kwargs["user_text"], "不是,我在扬州市宝应县")
            return {
                "address_candidate": "扬州市宝应县",
                "merged_address_candidate": "江苏省扬州市宝应县",
                "granularity": "admin_region",
            }

        policy = ServiceDialoguePolicy(
            confirmation_intent_inference_callback=fake_confirmation_inference,
            address_inference_callback=fake_address_inference,
        )
        state = ServiceRuntimeState(expected_address_confirmation=True)
        scenario_data = build_scenario(
            service_known_address=True,
            service_known_address_value="四川省绵阳市涪城区石塘街道学府佳苑1号楼1单元303室",
            service_known_address_matches_actual=False,
        ).to_dict()
        scenario_data["customer"]["address"] = "江苏省扬州市宝应县阳光锦城10号楼510室"
        scenario = Scenario.from_dict(scenario_data)

        result = policy.respond(
            scenario=scenario,
            transcript=[
                DialogueTurn(
                    speaker="service",
                    text="好的，您的地址是四川省绵阳市涪城区石塘街道学府佳苑1号楼1单元303室，对吗？",
                    round_index=5,
                ),
                DialogueTurn(
                    speaker="user",
                    text="不是,我在扬州市宝应县",
                    round_index=6,
                ),
            ],
            collected_slots={
                "issue_description": "不制热。",
                "surname": "张",
                "phone": "13800138001",
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

        self.assertEqual(confirmation_calls, [("address_confirmation", "不是,我在扬州市宝应县")])
        self.assertEqual(len(address_calls), 1)
        self.assertEqual(result.reply, "请问具体是在哪个小区或村呢？尽量详细到门牌号。")
        self.assertEqual(state.partial_address_candidate, "江苏省扬州市宝应县")

    def test_cross_city_partial_region_then_detail_does_not_mix_old_province(self):
        policy = ServiceDialoguePolicy()
        state = ServiceRuntimeState(
            awaiting_full_address=True,
            address_input_attempts=1,
            partial_address_candidate="扬州市宝应县",
            last_address_followup_prompt="请问具体是在哪个小区或村呢？尽量详细到门牌号。",
        )
        scenario_data = build_scenario().to_dict()
        scenario_data["customer"]["address"] = "江苏省扬州市宝应县阳光锦城10号楼510室"
        scenario = Scenario.from_dict(scenario_data)

        result = policy.respond(
            scenario=scenario,
            transcript=[
                DialogueTurn(
                    speaker="service",
                    text="请问具体是在哪个小区或村呢？尽量详细到门牌号。",
                    round_index=7,
                ),
                DialogueTurn(
                    speaker="user",
                    text="阳光锦城 10 号楼 510 室",
                    round_index=7,
                ),
            ],
            collected_slots={
                "issue_description": "不制热。",
                "surname": "张",
                "phone": "13800138001",
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
            "好的，跟您确认一下，地址是江苏省扬州市宝应县阳光锦城10号楼510室，对吗？",
        )
        self.assertEqual(
            state.pending_address_confirmation,
            "江苏省扬州市宝应县阳光锦城10号楼510室",
        )

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

        self.assertEqual(result.reply, "请您在电话拨号盘上输入您的联系号码，并以#号键结束。")
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
        self.assertEqual(result.reply, "非常抱歉，给您添麻烦了，我这就安排师傅上门维修，请问您贵姓？")

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
                text="非常抱歉，给您添麻烦了，我这就安排师傅上门维修，请问您贵姓",
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
            "非常抱歉输入有误，请您在拨号盘输入上门服务时的联系号码，输完后按#号键结束。",
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
        self.assertEqual(state.pending_phone_number_confirmation, "13900139002")

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
        self.assertEqual(result.slot_updates.get("phone", ""), "")
        self.assertTrue(state.expected_phone_number_confirmation)
        self.assertEqual(state.pending_phone_number_confirmation, "13900139002")

    def test_third_invalid_keypad_attempt_enters_sms_fill_confirmation(self):
        policy = ServiceDialoguePolicy()
        state = ServiceRuntimeState(awaiting_phone_keypad_input=True, phone_input_attempts=2)
        scenario = build_scenario()
        transcript = [
            DialogueTurn(speaker="service", text="非常抱歉输入有误，请您在拨号盘输入上门服务时的联系号码，输完后按#号键结束。", round_index=6),
            DialogueTurn(speaker="user", text="12345#", round_index=6),
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

        self.assertEqual(result.reply, "很抱歉，我们将为您下发短信，您可点击短信链接，补充信息并提交，您看是否可以？")
        self.assertTrue(state.expected_phone_sms_fill_confirmation)
        self.assertFalse(state.awaiting_phone_keypad_input)

    def test_third_confirmed_phone_denial_enters_sms_fill_confirmation(self):
        policy = ServiceDialoguePolicy()
        state = ServiceRuntimeState(
            expected_phone_number_confirmation=True,
            phone_input_attempts=3,
            pending_phone_number_confirmation="13900139002",
        )
        scenario = build_scenario()
        transcript = [
            DialogueTurn(speaker="service", text="好的，号码是13900139002，对吗？", round_index=7),
            DialogueTurn(speaker="user", text="不是", round_index=7),
        ]

        result = policy.respond(
            scenario=scenario,
            transcript=transcript,
            collected_slots={
                "issue_description": "对，家里热水器加热很慢。",
                "surname": "张",
                "phone": "",
                "address": "",
                "product_model": "",
                "request_type": "fault",
                "availability": "",
                "phone_contactable": "no",
                "phone_contact_owner": "爱人",
                "phone_collection_attempts": "3",
            },
            runtime_state=state,
        )

        self.assertEqual(result.reply, "很抱歉，我们将为您下发短信，您可点击短信链接，补充信息并提交，您看是否可以？")
        self.assertTrue(state.expected_phone_sms_fill_confirmation)
        self.assertFalse(state.awaiting_phone_keypad_input)

    def test_phone_sms_fill_confirmation_yes_closes_with_sms_sent(self):
        policy = ServiceDialoguePolicy()
        state = ServiceRuntimeState(expected_phone_sms_fill_confirmation=True)
        scenario = build_scenario()
        transcript = [
            DialogueTurn(speaker="service", text="很抱歉，我们将为您下发短信，您可点击短信链接，补充信息并提交，您看是否可以？", round_index=7),
            DialogueTurn(speaker="user", text="可以", round_index=7),
        ]

        result = policy.respond(
            scenario=scenario,
            transcript=transcript,
            collected_slots={
                "issue_description": "对，家里热水器加热很慢。",
                "surname": "张",
                "phone": "",
                "address": "",
                "product_model": "",
                "request_type": "fault",
                "availability": "",
                "phone_contactable": "no",
                "phone_contact_owner": "爱人",
                "phone_collection_attempts": "3",
            },
            runtime_state=state,
        )

        self.assertEqual(result.reply, "短信已发送，请稍后留意查看，感谢您的来电，再见！")
        self.assertTrue(result.is_ready_to_close)

    def test_phone_sms_fill_confirmation_non_yes_transfers_to_human(self):
        policy = ServiceDialoguePolicy()
        state = ServiceRuntimeState(expected_phone_sms_fill_confirmation=True)
        scenario = build_scenario()
        transcript = [
            DialogueTurn(speaker="service", text="很抱歉，我们将为您下发短信，您可点击短信链接，补充信息并提交，您看是否可以？", round_index=7),
            DialogueTurn(speaker="user", text="不用了", round_index=7),
        ]

        result = policy.respond(
            scenario=scenario,
            transcript=transcript,
            collected_slots={
                "issue_description": "对，家里热水器加热很慢。",
                "surname": "张",
                "phone": "",
                "address": "",
                "product_model": "",
                "request_type": "fault",
                "availability": "",
                "phone_contactable": "no",
                "phone_contact_owner": "爱人",
                "phone_collection_attempts": "3",
            },
            runtime_state=state,
        )

        self.assertEqual(result.reply, "请稍等，正在为您转接人工服务。")
        self.assertTrue(result.is_ready_to_close)
        self.assertEqual(result.close_reason, "phone_collection_failed")

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

    def test_known_address_confirmation_plain_no_reasks_full_address_without_polluting_candidate(self):
        policy = ServiceDialoguePolicy()
        state = ServiceRuntimeState(expected_address_confirmation=True)
        scenario = build_scenario(
            service_known_address=True,
            service_known_address_value="四川省南充市顺庆区中城街道碧桂园15座903室",
            service_known_address_matches_actual=False,
        )
        transcript = [
            DialogueTurn(
                speaker="service",
                text="好的，您的地址是四川省南充市顺庆区中城街道碧桂园15座903室，对吗？",
                round_index=6,
            ),
            DialogueTurn(speaker="user", text="不是", round_index=6),
        ]
        collected_slots = {
            "issue_description": "不制热。",
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
            "了解了，麻烦您重新提供一下地址，包括省、市、区、乡镇。",
        )
        self.assertEqual(state.partial_address_candidate, "")
        self.assertTrue(state.awaiting_full_address)

    def test_known_address_confirmation_plain_no_restarts_collection_with_fixed_prompt_and_keeps_ie_entry(self):
        policy = ServiceDialoguePolicy()
        state = ServiceRuntimeState(
            expected_address_confirmation=True,
            pending_address_confirmation="四川省南充市顺庆区中城街道碧桂园15座903室",
            address_confirmation_started_from_known_address=True,
        )
        scenario = build_scenario(
            service_known_address=True,
            service_known_address_value="四川省南充市顺庆区中城街道碧桂园15座903室",
            service_known_address_matches_actual=False,
        )
        transcript = [
            DialogueTurn(
                speaker="service",
                text="好的，您的地址是四川省南充市顺庆区中城街道碧桂园15座903室，对吗？",
                round_index=6,
            ),
            DialogueTurn(speaker="user", text="不是", round_index=6),
        ]
        collected_slots = {
            "issue_description": "不制热。",
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

        self.assertEqual(result.reply, "了解了，麻烦您重新提供一下地址，包括省、市、区、乡镇。")
        self.assertTrue(state.awaiting_full_address)
        self.assertTrue(
            policy.should_insert_address_ie_function_call(
                user_text="四川省南充市顺庆区中城街道碧桂园15座903室",
                transcript=[
                    DialogueTurn(
                        speaker="service",
                        text=result.reply,
                        round_index=7,
                    ),
                    DialogueTurn(
                        speaker="user",
                        text="四川省南充市顺庆区中城街道碧桂园15座903室",
                        round_index=8,
                    ),
                ],
                runtime_state=state,
            )
        )

    def test_corrected_address_confirmation_yes_uses_pending_confirmation_address(self):
        policy = ServiceDialoguePolicy()
        state = ServiceRuntimeState(
            expected_address_confirmation=True,
            pending_address_confirmation="浙江省衢州市柯城区绿茵名都小区21号楼2单元1403室",
        )
        scenario = build_scenario(
            service_known_address=True,
            service_known_address_value="贵州省遵义市汇川区上海路街道幸福花园11座1004室",
            service_known_address_matches_actual=False,
        )
        scenario_data = scenario.to_dict()
        scenario_data["customer"]["address"] = "贵州省遵义市汇川区上海路街道幸福花园11座1004室"
        scenario = Scenario.from_dict(scenario_data)
        transcript = [
            DialogueTurn(
                speaker="service",
                text="好的，跟您确认一下，地址是浙江省衢州市柯城区绿茵名都小区21号楼2单元1403室，对吗？",
                round_index=15,
            ),
            DialogueTurn(speaker="user", text="是的。", round_index=15),
        ]
        collected_slots = {
            "issue_description": "洗澡时漏水。",
            "surname": "郭",
            "phone": "13773341553",
            "address": "",
            "product_model": "",
            "request_type": "fault",
            "availability": "",
            "phone_contactable": "no",
            "phone_contact_owner": "本人当前来电",
            "phone_collection_attempts": "1",
        }

        result = policy.respond(
            scenario=scenario,
            transcript=transcript,
            collected_slots=collected_slots,
            runtime_state=state,
        )

        self.assertEqual(
            result.slot_updates["address"],
            "浙江省衢州市柯城区绿茵名都小区21号楼2单元1403室",
        )

    def test_observation_address_confirmation_plain_no_restarts_collection_with_fixed_prompt(self):
        policy = ServiceDialoguePolicy()
        state = ServiceRuntimeState(
            expected_address_confirmation=True,
            address_confirmation_triggered_by_observation=True,
            pending_address_confirmation="江苏省扬州市宝应县御景豪庭10号楼401室",
        )
        transcript = [
            DialogueTurn(
                speaker="service",
                text="好的，跟您确认一下，地址是江苏省扬州市宝应县御景豪庭10号楼401室，对吗？",
                round_index=9,
            ),
            DialogueTurn(speaker="user", text="不对", round_index=10),
        ]
        scenario = build_scenario()
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

        self.assertFalse(
            policy.should_insert_address_ie_after_observation_confirmation(
                user_text="不对",
                user_round_index=10,
                transcript=transcript,
                runtime_state=state,
            )
        )

        result = policy.respond(
            scenario=scenario,
            transcript=transcript,
            collected_slots=collected_slots,
            runtime_state=state,
        )

        self.assertEqual(result.reply, "了解了，麻烦您重新提供一下地址，包括省、市、区、乡镇。")
        self.assertTrue(state.awaiting_full_address)
        self.assertEqual(state.partial_address_candidate, "")

    def test_observation_address_confirmation_yes_with_repeated_same_components_skips_ie_and_advances(self):
        policy = ServiceDialoguePolicy()
        state = ServiceRuntimeState(
            expected_address_confirmation=True,
            address_confirmation_triggered_by_observation=True,
            pending_address_confirmation="江苏省扬州市宝应县御景豪庭10号楼401室",
        )
        transcript = [
            DialogueTurn(
                speaker="service",
                text="好的，跟您确认一下，地址是江苏省扬州市宝应县御景豪庭10号楼401室，对吗？",
                round_index=9,
            ),
            DialogueTurn(
                speaker="user",
                text="对，就是扬州市宝应县御景豪庭10号楼401室。",
                round_index=10,
            ),
        ]
        scenario = build_scenario()
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

        self.assertFalse(
            policy.should_insert_address_ie_after_observation_confirmation(
                user_text="对，就是扬州市宝应县御景豪庭10号楼401室。",
                user_round_index=10,
                transcript=transcript,
                runtime_state=state,
            )
        )

        result = policy.respond(
            scenario=scenario,
            transcript=transcript,
            collected_slots=collected_slots,
            runtime_state=state,
        )

        self.assertEqual(result.slot_updates["address"], "江苏省扬州市宝应县御景豪庭10号楼401室")
        self.assertFalse(state.expected_address_confirmation)
        self.assertFalse(state.awaiting_full_address)
        self.assertNotIn("地址是", result.reply)

    def test_observation_address_confirmation_model_add_without_real_progress_does_not_trigger_ie(self):
        def fake_confirmation_inference(*, prompt_kind: str, user_text: str, **_: str):
            if prompt_kind == "address_confirmation_observation_followup":
                return {"intent": "add"}
            if prompt_kind == "address_confirmation":
                return {"intent": "yes"}
            return {"intent": "unknown"}

        policy = ServiceDialoguePolicy(
            confirmation_intent_inference_callback=fake_confirmation_inference,
        )
        state = ServiceRuntimeState(
            expected_address_confirmation=True,
            address_confirmation_triggered_by_observation=True,
            pending_address_confirmation="江苏省扬州市宝应县安宜镇阳光锦城",
        )
        transcript = [
            DialogueTurn(
                speaker="service",
                text="好的，跟您确认一下，地址是江苏省扬州市宝应县安宜镇阳光锦城，对吗？",
                round_index=9,
            ),
            DialogueTurn(
                speaker="user",
                text="嗯嗯，是的，宝应县安宜镇。",
                round_index=10,
            ),
        ]

        self.assertFalse(
            policy.should_insert_address_ie_after_observation_confirmation(
                user_text="嗯嗯，是的，宝应县安宜镇。",
                user_round_index=10,
                transcript=transcript,
                runtime_state=state,
            )
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

    def test_known_address_confirmation_community_correction_keeps_existing_district(self):
        policy = ServiceDialoguePolicy()
        state = ServiceRuntimeState(expected_address_confirmation=True)
        scenario_data = build_installation_scenario().to_dict()
        scenario_data["customer"]["address"] = "河北省唐山市路北区幸福社区32号"
        scenario_data["hidden_context"]["service_known_address"] = True
        scenario_data["hidden_context"]["service_known_address_value"] = "河北省唐山市路北区金色家园32号"
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

        first_result = policy.respond(
            scenario=scenario,
            transcript=[
                DialogueTurn(
                    speaker="service",
                    text="好的，您的地址是河北省唐山市路北区金色家园32号，对吗？",
                    round_index=12,
                ),
                DialogueTurn(
                    speaker="user",
                    text="不是，得是幸福社区。",
                    round_index=13,
                ),
            ],
            collected_slots=collected_slots,
            runtime_state=state,
        )

        self.assertEqual(first_result.reply, "好的，请您再说一下具体门牌号。")
        self.assertTrue(state.awaiting_full_address)

        second_result = policy.respond(
            scenario=scenario,
            transcript=[
                DialogueTurn(speaker="service", text=first_result.reply, round_index=14),
                DialogueTurn(speaker="user", text="幸福社区32号。", round_index=14),
            ],
            collected_slots=collected_slots,
            runtime_state=state,
        )

        self.assertEqual(
            second_result.reply,
            "好的，跟您确认一下，地址是河北省唐山市路北区幸福社区32号，对吗？",
        )
        self.assertEqual(state.pending_address_confirmation, "河北省唐山市路北区幸福社区32号")

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

    def test_road_house_number_address_can_start_confirmation_without_community(self):
        policy = ServiceDialoguePolicy()
        state = ServiceRuntimeState(awaiting_full_address=True, address_input_attempts=1)
        scenario_data = build_installation_scenario().to_dict()
        scenario_data["customer"]["address"] = "四川省绵阳市涪城区天府路12号"
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
                    text="四川省绵阳市涪城区天府路12号",
                    round_index=6,
                ),
            ],
            collected_slots=collected_slots,
            runtime_state=state,
        )

        self.assertEqual(
            result.reply,
            "好的，跟您确认一下，地址是四川省绵阳市涪城区天府路12号，对吗？",
        )
        self.assertTrue(state.expected_address_confirmation)
        self.assertEqual(state.pending_address_confirmation, "四川省绵阳市涪城区天府路12号")

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

    def test_poi_address_with_full_region_context_can_confirm_directly(self):
        policy = ServiceDialoguePolicy()
        state = ServiceRuntimeState(
            awaiting_full_address=True,
            address_input_attempts=1,
            partial_address_candidate="江苏省南京市玄武区",
            last_address_followup_prompt="请问具体是在哪个小区或村呢？尽量详细到门牌号。",
        )
        scenario_data = build_scenario().to_dict()
        scenario_data["customer"]["address"] = "江苏省南京市玄武区南京农业大学卫岗校区"
        scenario = Scenario.from_dict(scenario_data)

        result = policy.respond(
            scenario=scenario,
            transcript=[
                DialogueTurn(
                    speaker="service",
                    text="请问具体是在哪个小区或村呢？尽量详细到门牌号。",
                    round_index=9,
                ),
                DialogueTurn(
                    speaker="user",
                    text="南京农业大学卫岗校区",
                    round_index=9,
                ),
            ],
            collected_slots={
                "issue_description": "机器不制热。",
                "surname": "王",
                "phone": "13800138001",
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
            "好的，跟您确认一下，地址是江苏省南京市玄武区南京农业大学卫岗校区，对吗？",
        )
        self.assertTrue(state.expected_address_confirmation)
        self.assertEqual(
            state.pending_address_confirmation,
            "江苏省南京市玄武区南京农业大学卫岗校区",
        )

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

    def test_extract_address_components_preserves_suffixless_community_without_building(self):
        components = extract_address_components("三门县江南壹号")

        self.assertEqual(components.district, "三门县")
        self.assertEqual(components.community, "江南壹号")

    def test_extract_address_components_splits_town_and_suffixless_community_without_admin_prefix(self):
        components = extract_address_components("徐泾镇西郊一区")

        self.assertEqual(components.district, "")
        self.assertEqual(components.town, "徐泾镇")
        self.assertEqual(components.community, "西郊一区")

    def test_extract_address_candidate_from_denial_ignores_pure_no_text(self):
        candidate = ServiceDialoguePolicy._extract_address_candidate_from_denial(
            user_text="不是",
            confirmation_address="四川省南充市顺庆区中城街道碧桂园15座903室",
        )

        self.assertEqual(candidate, "")

    def test_extract_address_candidate_from_denial_accepts_immediate_corrected_address(self):
        candidate = ServiceDialoguePolicy._extract_address_candidate_from_denial(
            user_text="不是，浙江省台州市三门县江南壹号5栋302室",
            confirmation_address="四川省南充市顺庆区中城街道碧桂园15座903室",
        )

        self.assertEqual(candidate, "浙江省台州市三门县江南壹号5栋302室")

    def test_extract_address_candidate_from_denial_strips_switch_prefix_before_real_address(self):
        candidate = ServiceDialoguePolicy._extract_address_candidate_from_denial(
            user_text="换个地址,三门县江南壹号",
            confirmation_address="北京市海淀区中关村街道新湖国际4号楼1单元801室",
        )

        self.assertEqual(candidate, "三门县江南壹号")

    def test_extract_address_candidate_from_denial_ignores_switch_request_phrase(self):
        candidate = ServiceDialoguePolicy._extract_address_candidate_from_denial(
            user_text="不是,换一个",
            confirmation_address="广东省佛山市禅城区祖庙街道恒大绿洲3号楼3层304室",
        )

        self.assertEqual(candidate, "")

    def test_extract_address_candidate_from_denial_ignores_new_address_switch_phrase(self):
        candidate = ServiceDialoguePolicy._extract_address_candidate_from_denial(
            user_text="不是,留个新地址",
            confirmation_address="贵州省遵义市播州区南白街道锦绣苑8号楼5层501室",
        )

        self.assertEqual(candidate, "")

    def test_extract_address_candidate_from_denial_ignores_move_phrase_without_new_address(self):
        candidate = ServiceDialoguePolicy._extract_address_candidate_from_denial(
            user_text="不是,我换地方了",
            confirmation_address="湖南省长沙市芙蓉区湘湖街道幸福花园2号楼5层504室",
        )

        self.assertEqual(candidate, "")

    def test_extract_strong_address_candidate_from_denial_rejects_province_only_correction(self):
        candidate = ServiceDialoguePolicy._extract_strong_address_candidate_from_denial(
            user_text="不在天津,在江苏",
            confirmation_address="天津市南开区万兴街道碧桂园9座6楼603室",
        )

        self.assertEqual(candidate, "")

    def test_prepare_address_for_confirmation_strips_discourse_prefix_before_landmark_address(self):
        prepared = ServiceDialoguePolicy._prepare_address_for_confirmation("啥,我在南京邮电大学仙林校区")

        self.assertEqual(prepared, "南京邮电大学仙林校区")

    def test_extract_address_components_treats_road_house_number_as_road_plus_detail(self):
        components = extract_address_components("四川省绵阳市涪城区天府路12号")

        self.assertEqual(components.province, "四川省")
        self.assertEqual(components.city, "绵阳市")
        self.assertEqual(components.district, "涪城区")
        self.assertEqual(components.road, "天府路")
        self.assertEqual(components.community, "")
        self.assertEqual(ServiceDialoguePolicy._extract_house_number_token("四川省绵阳市涪城区天府路12号"), "12号")

    def test_extract_address_components_keeps_road_house_number_with_building_room(self):
        components = extract_address_components("四川省绵阳市涪城区天府路12号3栋502室")

        self.assertEqual(components.road, "天府路")
        self.assertEqual(components.community, "")
        self.assertEqual(components.building, "3栋")
        self.assertEqual(components.room, "502室")
        self.assertEqual(
            ServiceDialoguePolicy._extract_house_number_token("四川省绵阳市涪城区天府路12号3栋502室"),
            "12号",
        )

    def test_extract_address_components_preserves_community_before_house_number(self):
        components = extract_address_components("贵州省遵义市汇川区深圳大道康乐社区62号门面")

        self.assertEqual(components.road, "深圳大道")
        self.assertEqual(components.community, "康乐社区")
        self.assertEqual(
            ServiceDialoguePolicy._extract_house_number_token("贵州省遵义市汇川区深圳大道康乐社区62号门面"),
            "62号",
        )

    def test_extract_address_components_does_not_treat_shequ_as_district(self):
        components = extract_address_components("幸福社区32号")

        self.assertEqual(components.district, "")
        self.assertEqual(components.community, "幸福社区")
        self.assertEqual(ServiceDialoguePolicy._extract_house_number_token("幸福社区32号"), "32号")

    def test_extract_address_components_treats_campus_as_locality_not_district(self):
        components = extract_address_components("南京农业大学卫岗校区")

        self.assertEqual(components.district, "")
        self.assertEqual(components.community, "南京农业大学卫岗校区")

    def test_extract_address_components_treats_hospital_as_locality(self):
        components = extract_address_components("江苏省南京市玄武区鼓楼医院")

        self.assertEqual(components.province, "江苏省")
        self.assertEqual(components.city, "南京市")
        self.assertEqual(components.district, "玄武区")
        self.assertEqual(components.community, "鼓楼医院")

    def test_extract_address_components_canonicalizes_suffixless_province_city(self):
        components = extract_address_components("江苏南京")

        self.assertEqual(components.province, "江苏省")
        self.assertEqual(components.city, "南京市")

    def test_extract_address_components_does_not_treat_market_as_city(self):
        components = extract_address_components("金谷农贸市场5巷西17号")

        self.assertEqual(components.province, "")
        self.assertEqual(components.city, "")
        self.assertEqual(components.district, "")
        self.assertEqual(components.road, "金谷农贸市场5巷")

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
            last_address_followup_prompt="请问具体是在哪个小区或村呢？尽量详细到门牌号。",
        )
        scenario_data = build_scenario().to_dict()
        scenario_data["customer"]["address"] = "江苏省扬州市宝应县阳光锦城3号楼2单元402室"
        scenario = Scenario.from_dict(scenario_data)

        result = policy.respond(
            scenario=scenario,
            transcript=[
                DialogueTurn(speaker="service", text="请问具体是在哪个小区或村呢？尽量详细到门牌号。", round_index=11),
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

    def test_merge_address_candidate_completes_region_prefix_before_existing_locality(self):
        merged = ServiceDialoguePolicy._merge_address_candidate("三门县江南壹号", "浙江省台州市三门县")

        self.assertEqual(merged, "浙江省台州市三门县江南壹号")

    def test_address_with_non_standard_whitespace_still_starts_confirmation(self):
        policy = ServiceDialoguePolicy()
        state = ServiceRuntimeState(
            awaiting_full_address=True,
            address_input_attempts=1,
            partial_address_candidate="江苏省扬州市宝应县安宜镇",
            last_address_followup_prompt="请问具体是在哪个小区或村呢？尽量详细到门牌号。",
        )
        scenario_data = build_scenario().to_dict()
        scenario_data["customer"]["address"] = "江苏省扬州市宝应县安宜镇阳光锦城3号楼2单元402室"
        scenario = Scenario.from_dict(scenario_data)

        result = policy.respond(
            scenario=scenario,
            transcript=[
                DialogueTurn(speaker="service", text="请问具体是在哪个小区或村呢？尽量详细到门牌号。", round_index=11),
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

    def test_address_collection_prefers_model_slot_extraction_when_callback_is_available(self):
        callback_calls: list[str] = []

        def fake_address_inference(**kwargs):
            callback_calls.append(kwargs["user_text"])
            return {
                "address_candidate": "徐泾镇西郊一区",
                "merged_address_candidate": "上海市青浦区徐泾镇西郊一区",
                "granularity": "locality",
            }

        policy = ServiceDialoguePolicy(address_inference_callback=fake_address_inference)
        state = ServiceRuntimeState(
            awaiting_full_address=True,
            address_input_attempts=1,
            partial_address_candidate="上海市青浦区",
            last_address_followup_prompt="请问具体是在哪个小区或村呢？尽量详细到门牌号。",
        )
        scenario_data = build_scenario().to_dict()
        scenario_data["customer"]["address"] = "上海市青浦区徐泾镇西郊一区1785弄40号楼301室"
        scenario = Scenario.from_dict(scenario_data)

        result = policy.respond(
            scenario=scenario,
            transcript=[
                DialogueTurn(
                    speaker="service",
                    text="请问具体是在哪个小区或村呢？尽量详细到门牌号。",
                    round_index=8,
                ),
                DialogueTurn(speaker="user", text="徐泾镇西郊一区", round_index=8),
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

        self.assertEqual(callback_calls, ["徐泾镇西郊一区"])
        self.assertEqual(state.partial_address_candidate, "上海市青浦区徐泾镇西郊一区")
        self.assertEqual(result.reply, "请问是几栋几单元几楼几号呢？")

    def test_interactive_frontend_address_confirmation_does_not_compare_against_preset_actual_address(self):
        policy = ServiceDialoguePolicy()
        scenario = build_scenario()
        scenario.hidden_context["interactive_test_freeform"] = True
        scenario.hidden_context["manual_test_address_precision_reference"] = False

        can_confirm = policy._can_start_address_confirmation(
            scenario=scenario,
            candidate="浙江省台州市三门县江南壹号10号楼501室",
        )

        self.assertTrue(can_confirm)

    def test_address_collection_with_model_callback_does_not_fall_back_to_non_address_text(self):
        def fake_address_inference(**kwargs):
            self.assertEqual(kwargs["user_text"], "就是那个地方")
            return {
                "address_candidate": "",
                "merged_address_candidate": "",
                "granularity": "none",
            }

        policy = ServiceDialoguePolicy(address_inference_callback=fake_address_inference)
        state = ServiceRuntimeState(
            awaiting_full_address=True,
            address_input_attempts=0,
            last_address_followup_prompt="好的，需要登记下您的地址，麻烦您完整的说下省、市、区、乡镇，精确到门牌号。",
        )
        scenario_data = build_installation_scenario().to_dict()
        scenario_data["customer"]["address"] = "四川省绵阳市涪城区天府路12号"
        scenario = Scenario.from_dict(scenario_data)

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
                    text="就是那个地方",
                    round_index=6,
                ),
            ],
            collected_slots={
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
            },
            runtime_state=state,
        )

        self.assertEqual(result.reply, "好的，需要登记下您的地址，麻烦您完整的说下省、市、区、乡镇，精确到门牌号。")
        self.assertFalse(state.expected_address_confirmation)
        self.assertEqual(state.partial_address_candidate, "")

    def test_address_collection_with_model_callback_prefers_strong_rule_match_before_model(self):
        def fake_address_inference(**kwargs):
            raise AssertionError("Strong exact address match should not call model.")

        policy = ServiceDialoguePolicy(address_inference_callback=fake_address_inference)
        state = ServiceRuntimeState(
            awaiting_full_address=True,
            address_input_attempts=0,
            last_address_followup_prompt="好的，需要登记下您的地址，麻烦您完整的说下省、市、区、乡镇，精确到门牌号。",
        )
        scenario_data = build_installation_scenario().to_dict()
        scenario_data["customer"]["address"] = "四川省绵阳市涪城区天府路12号"
        scenario = Scenario.from_dict(scenario_data)

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
                    text="四川省绵阳市涪城区天府路12号",
                    round_index=6,
                ),
            ],
            collected_slots={
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
            },
            runtime_state=state,
        )

        self.assertEqual(
            result.reply,
            "好的，跟您确认一下，地址是四川省绵阳市涪城区天府路12号，对吗？",
        )
        self.assertTrue(state.expected_address_confirmation)

    def test_address_collection_with_model_callback_prefers_strong_rule_for_province_city(self):
        def fake_address_inference(**kwargs):
            raise AssertionError("Province-city strong rule match should not call model.")

        policy = ServiceDialoguePolicy(address_inference_callback=fake_address_inference)
        state = ServiceRuntimeState(
            awaiting_full_address=True,
            address_input_attempts=0,
            last_address_followup_prompt="好的，需要登记下您的地址，麻烦您完整的说下省、市、区、乡镇，精确到门牌号。",
        )
        scenario_data = build_scenario().to_dict()
        scenario_data["customer"]["address"] = "浙江省台州市三门县海润街道江南壹号5栋302室"
        scenario = Scenario.from_dict(scenario_data)

        result = policy.respond(
            scenario=scenario,
            transcript=[
                DialogueTurn(
                    speaker="service",
                    text="好的，需要登记下您的地址，麻烦您完整的说下省、市、区、乡镇，精确到门牌号。",
                    round_index=10,
                ),
                DialogueTurn(speaker="user", text="浙江省台州市", round_index=11),
            ],
            collected_slots={
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
            },
            runtime_state=state,
        )

        self.assertEqual(
            result.reply,
            "好的，您是在台州市的哪个区县呢？具体小区门牌号也提供一下呢？",
        )
        self.assertEqual(state.partial_address_candidate, "浙江省台州市")

    def test_address_collection_rejects_model_overreach_when_market_name_contains_shi(self):
        def fake_address_inference(**kwargs):
            self.assertEqual(kwargs["partial_address_candidate"], "广西钦州钦南区")
            self.assertEqual(kwargs["user_text"], "金谷农贸市场5巷西17号")
            return {
                "address_candidate": "金谷农贸市场5巷西17号",
                "merged_address_candidate": "广西钦州钦南区金谷农贸市5巷西17号",
                "granularity": "complete",
            }

        policy = ServiceDialoguePolicy(address_inference_callback=fake_address_inference)
        state = ServiceRuntimeState(
            awaiting_full_address=True,
            partial_address_candidate="广西钦州钦南区",
            last_address_followup_prompt="请问具体是在哪个小区或村呢？尽量详细到门牌号。",
        )
        scenario = build_freeform_cli_scenario()
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
            transcript=[
                DialogueTurn(
                    speaker="service",
                    text="请问具体是在哪个小区或村呢？尽量详细到门牌号。",
                    round_index=8,
                ),
                DialogueTurn(
                    speaker="user",
                    text="金谷农贸市场5巷西17号",
                    round_index=9,
                ),
            ],
            collected_slots=collected_slots,
            runtime_state=state,
        )

        self.assertEqual(
            result.reply,
            "好的，跟您确认一下，地址是广西钦州市钦南区金谷农贸市场5巷西17号，对吗？",
        )
        self.assertEqual(
            state.pending_address_confirmation,
            "广西钦州市钦南区金谷农贸市场5巷西17号",
        )

    def test_address_collection_strips_non_address_chatter_before_school_locality(self):
        policy = ServiceDialoguePolicy()
        state = ServiceRuntimeState(
            awaiting_full_address=True,
            partial_address_candidate="江苏南京市栖霞区",
            last_address_followup_prompt="请问具体是在哪个小区或村呢？尽量详细到门牌号。",
        )
        scenario = build_freeform_cli_scenario(request_type="fault")
        collected_slots = {
            "issue_description": "不制热。",
            "surname": "张",
            "phone": "13800138001",
            "address": "",
            "request_type": "fault",
            "phone_contactable": "yes",
            "phone_contact_owner": "本人当前来电",
            "phone_collection_attempts": "0",
        }

        result = policy.respond(
            scenario=scenario,
            transcript=[
                DialogueTurn(
                    speaker="service",
                    text="请问具体是在哪个小区或村呢？尽量详细到门牌号。",
                    round_index=9,
                ),
                DialogueTurn(
                    speaker="user",
                    text="啥,我在南京邮电大学仙林校区",
                    round_index=9,
                ),
            ],
            collected_slots=collected_slots,
            runtime_state=state,
        )

        self.assertEqual(
            result.reply,
            "好的，跟您确认一下，地址是江苏省南京市栖霞区南京邮电大学仙林校区，对吗？",
        )
        self.assertEqual(
            state.pending_address_confirmation,
            "江苏省南京市栖霞区南京邮电大学仙林校区",
        )

    def test_address_collection_with_poi_detail_uses_model_when_rule_underparses_tail(self):
        callback_calls: list[str] = []

        def fake_address_inference(**kwargs):
            callback_calls.append(kwargs["user_text"])
            self.assertEqual(kwargs["user_text"], "台州市第三小学学生宿舍")
            return {
                "address_candidate": "第三小学学生宿舍",
                "merged_address_candidate": "浙江省台州市三门县第三小学学生宿舍",
                "granularity": "detail",
            }

        policy = ServiceDialoguePolicy(address_inference_callback=fake_address_inference)
        state = ServiceRuntimeState(
            awaiting_full_address=True,
            address_input_attempts=1,
            partial_address_candidate="浙江省台州市三门县",
            last_address_followup_prompt="请问具体是在哪个小区或村呢？尽量详细到门牌号。",
        )
        scenario_data = build_scenario().to_dict()
        scenario_data["customer"]["address"] = "浙江省台州市三门县第三小学学生宿舍"
        scenario = Scenario.from_dict(scenario_data)

        result = policy.respond(
            scenario=scenario,
            transcript=[
                DialogueTurn(
                    speaker="service",
                    text="请问具体是在哪个小区或村呢？尽量详细到门牌号。",
                    round_index=12,
                ),
                DialogueTurn(speaker="user", text="台州市第三小学学生宿舍", round_index=13),
            ],
            collected_slots={
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
            },
            runtime_state=state,
        )

        self.assertEqual(callback_calls, ["台州市第三小学学生宿舍"])
        self.assertEqual(
            result.reply,
            "好的，跟您确认一下，地址是浙江省台州市三门县第三小学学生宿舍，对吗？",
        )
        self.assertTrue(state.expected_address_confirmation)

    def test_address_collection_with_model_callback_merges_granularity_across_rounds(self):
        def fake_address_inference(**kwargs):
            user_text = kwargs["user_text"]
            if user_text == "四川省绵阳市":
                return {
                    "address_candidate": "四川省绵阳市",
                    "merged_address_candidate": "四川省绵阳市",
                    "granularity": "admin_region",
                }
            if user_text == "涪城区天府路":
                return {
                    "address_candidate": "涪城区天府路",
                    "merged_address_candidate": "四川省绵阳市涪城区天府路",
                    "granularity": "locality",
                }
            if user_text == "12号":
                return {
                    "address_candidate": "12号",
                    "merged_address_candidate": "四川省绵阳市涪城区天府路12号",
                    "granularity": "detail",
                }
            raise AssertionError(f"Unexpected user_text: {user_text}")

        policy = ServiceDialoguePolicy(address_inference_callback=fake_address_inference)
        scenario_data = build_installation_scenario().to_dict()
        scenario_data["customer"]["address"] = "四川省绵阳市涪城区天府路12号"
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
        state = ServiceRuntimeState(
            awaiting_full_address=True,
            address_input_attempts=0,
            last_address_followup_prompt="好的，需要登记下您的地址，麻烦您完整的说下省、市、区、乡镇，精确到门牌号。",
        )

        first_result = policy.respond(
            scenario=scenario,
            transcript=[
                DialogueTurn(
                    speaker="service",
                    text="好的，需要登记下您的地址，麻烦您完整的说下省、市、区、乡镇，精确到门牌号。",
                    round_index=6,
                ),
                DialogueTurn(speaker="user", text="四川省绵阳市", round_index=6),
            ],
            collected_slots=collected_slots,
            runtime_state=state,
        )
        self.assertEqual(
            first_result.reply,
            "好的，您是在绵阳市的哪个区县呢？具体小区门牌号也提供一下呢？",
        )
        self.assertEqual(state.partial_address_candidate, "四川省绵阳市")

        second_result = policy.respond(
            scenario=scenario,
            transcript=[
                DialogueTurn(speaker="service", text=first_result.reply, round_index=7),
                DialogueTurn(speaker="user", text="涪城区天府路", round_index=7),
            ],
            collected_slots=collected_slots,
            runtime_state=state,
        )
        self.assertEqual(second_result.reply, "好的，请您再说一下具体门牌号。")
        self.assertEqual(state.partial_address_candidate, "四川省绵阳市涪城区天府路")

        third_result = policy.respond(
            scenario=scenario,
            transcript=[
                DialogueTurn(speaker="service", text=second_result.reply, round_index=8),
                DialogueTurn(speaker="user", text="12号", round_index=8),
            ],
            collected_slots=collected_slots,
            runtime_state=state,
        )
        self.assertEqual(
            third_result.reply,
            "好的，跟您确认一下，地址是四川省绵阳市涪城区天府路12号，对吗？",
        )
        self.assertTrue(state.expected_address_confirmation)

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
            last_address_followup_prompt="请问具体是在哪个小区或村呢？尽量详细到门牌号。",
        )
        scenario_data = build_scenario().to_dict()
        scenario_data["customer"]["address"] = "浙江省台州市三门县海润街道江南壹号5栋302室"
        scenario = Scenario.from_dict(scenario_data)

        result = policy.respond(
            scenario=scenario,
            transcript=[
                DialogueTurn(speaker="service", text="请问具体是在哪个小区或村呢？尽量详细到门牌号。", round_index=19),
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
                DialogueTurn(speaker="service", text="请问具体是在哪个小区或村呢？尽量详细到门牌号。", round_index=14),
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

    def test_address_collection_accepts_current_candidate_via_model_stop_intent(self):
        callback_calls: list[str] = []

        def fake_acceptance_inference(
            *,
            user_text: str,
            partial_address_candidate: str,
            last_address_followup_prompt: str,
            dialogue_history: str,
        ):
            callback_calls.append(user_text)
            self.assertEqual(partial_address_candidate, "上海市青浦区古桐公寓39号楼")
            self.assertEqual(last_address_followup_prompt, "请问是几栋几单元几楼几号呢？")
            return {"intent": "yes"}

        policy = ServiceDialoguePolicy(
            address_collection_acceptance_inference_callback=fake_acceptance_inference,
        )
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
                DialogueTurn(speaker="user", text="后面电话联系吧，就先这样", round_index=15),
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

        self.assertEqual(callback_calls, ["后面电话联系吧，就先这样"])
        self.assertEqual(
            result.reply,
            "好的，跟您确认一下，地址是上海市青浦区古桐公寓39号楼，对吗？",
        )
        self.assertTrue(policy.last_used_model_intent_inference)

    def test_address_collection_model_stop_intent_no_does_not_override_address_detail_input(self):
        def fake_acceptance_inference(**kwargs):
            return {"intent": "no"}

        policy = ServiceDialoguePolicy(
            address_collection_acceptance_inference_callback=fake_acceptance_inference,
        )
        state = ServiceRuntimeState(
            awaiting_full_address=True,
            address_input_attempts=1,
            partial_address_candidate="上海市青浦区徐泾镇",
            last_address_followup_prompt="请问具体是在哪个小区或村呢？尽量详细到门牌号。",
        )
        scenario_data = build_scenario().to_dict()
        scenario_data["customer"]["address"] = "上海市青浦区徐泾镇西郊一区1785弄40号楼301室"
        scenario = Scenario.from_dict(scenario_data)

        result = policy.respond(
            scenario=scenario,
            transcript=[
                DialogueTurn(
                    speaker="service",
                    text="请问具体是在哪个小区或村呢？尽量详细到门牌号。",
                    round_index=15,
                ),
                DialogueTurn(speaker="user", text="西郊一区1785弄40号楼301室", round_index=15),
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

        self.assertEqual(result.reply, "请问具体是在哪个小区或村呢？尽量详细到门牌号。")

    def test_address_collection_model_fallback_does_not_backfill_province_city_from_district_only(self):
        def fake_address_inference(**kwargs):
            self.assertEqual(kwargs["user_text"], "纳雍县")
            return {
                "address_candidate": "纳雍县",
                "merged_address_candidate": "贵州省毕节市纳雍县",
                "granularity": "admin_region",
            }

        policy = ServiceDialoguePolicy(address_inference_callback=fake_address_inference)
        state = ServiceRuntimeState(awaiting_full_address=True)
        scenario_data = build_scenario().to_dict()
        scenario_data["customer"]["address"] = "贵州省毕节市纳雍县厍东关乡联合村三组42号"
        scenario = Scenario.from_dict(scenario_data)

        result = policy.respond(
            scenario=scenario,
            transcript=[
                DialogueTurn(
                    speaker="service",
                    text="需要登记下您的地址，麻烦您完整的说下省、市、区、乡镇，精确到门牌号。",
                    round_index=10,
                ),
                DialogueTurn(speaker="user", text="纳雍县", round_index=10),
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

        self.assertEqual(result.reply, "好的，请您说一下省、市、区和街道。")
        self.assertEqual(state.partial_address_candidate, "纳雍县")
        self.assertFalse(policy.last_used_model_intent_inference)

    def test_model_address_overreach_allows_province_backfill_for_prefecture_level_city(self):
        self.assertFalse(
            ServiceDialoguePolicy._is_model_address_overreach(
                user_text="兰州市",
                partial_address_candidate="",
                candidate="甘肃省兰州市",
            )
        )

    def test_model_address_overreach_blocks_higher_region_backfill_for_county_level_city(self):
        self.assertTrue(
            ServiceDialoguePolicy._is_model_address_overreach(
                user_text="诸暨市",
                partial_address_candidate="",
                candidate="浙江省绍兴市诸暨市",
            )
        )

    def test_address_collection_nonstandard_delivery_point_can_confirm_directly(self):
        policy = ServiceDialoguePolicy()
        state = ServiceRuntimeState(
            awaiting_full_address=True,
            partial_address_candidate="上海市青浦区徐泾镇",
            last_address_followup_prompt="请问具体是在哪个小区或村呢？尽量详细到门牌号。",
        )
        scenario_data = build_scenario().to_dict()
        scenario_data["customer"]["address"] = "上海市青浦区徐泾镇美的创新园区A8外卖柜"
        scenario = Scenario.from_dict(scenario_data)

        result = policy.respond(
            scenario=scenario,
            transcript=[
                DialogueTurn(
                    speaker="service",
                    text="请问具体是在哪个小区或村呢？尽量详细到门牌号。",
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
            last_address_followup_prompt="请问具体是在哪个小区或村呢？尽量详细到门牌号。",
        )
        scenario_data = build_scenario().to_dict()
        scenario_data["customer"]["address"] = "上海市青浦区徐泾镇美的创新园区A8外卖柜"
        scenario = Scenario.from_dict(scenario_data)

        result = policy.respond(
            scenario=scenario,
            transcript=[
                DialogueTurn(
                    speaker="service",
                    text="请问具体是在哪个小区或村呢？尽量详细到门牌号。",
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
            last_address_followup_prompt="请问具体是在哪个小区或村呢？尽量详细到门牌号。",
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
                DialogueTurn(speaker="service", text="请问具体是在哪个小区或村呢？尽量详细到门牌号。", round_index=12),
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
        self.assertEqual(district_result.reply, "请问具体是在哪个小区或村呢？尽量详细到门牌号。")

        community_result = policy.respond(
            scenario=scenario,
            transcript=[
                DialogueTurn(
                    speaker="service",
                    text="请问具体是在哪个小区或村呢？尽量详细到门牌号。",
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

        self.assertEqual(result.reply, "请问具体是在哪个小区或村呢？尽量详细到门牌号。")
        self.assertEqual(state.partial_address_candidate, "上海市青浦区徐泾镇")

    def test_address_collection_province_only_reply_asks_for_city_district_and_street(self):
        policy = ServiceDialoguePolicy()
        state = ServiceRuntimeState(awaiting_full_address=True)
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

        result = policy.respond(
            scenario=scenario,
            transcript=[
                DialogueTurn(
                    speaker="service",
                    text="需要登记下您的地址，麻烦您完整的说下省、市、区、乡镇，精确到门牌号。",
                    round_index=5,
                ),
                DialogueTurn(speaker="user", text="江苏省", round_index=5),
            ],
            collected_slots=collected_slots,
            runtime_state=state,
        )

        self.assertEqual(result.reply, "好的，请问是江苏省哪个城市的哪个区和街道呢？")
        self.assertEqual(state.partial_address_candidate, "江苏省")

    def test_address_collection_locality_first_reply_backtracks_to_region_then_locality(self):
        policy = ServiceDialoguePolicy()
        state = ServiceRuntimeState(awaiting_full_address=True)
        scenario_data = build_scenario().to_dict()
        scenario_data["customer"]["address"] = "江苏省淮安市淮阴区幸福家园3号楼2单元502室"
        scenario = Scenario.from_dict(scenario_data)
        collected_slots = {
            "issue_description": "热水器不出热水。",
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

        locality_first_result = policy.respond(
            scenario=scenario,
            transcript=[
                DialogueTurn(
                    speaker="service",
                    text="需要登记下您的地址，麻烦您完整的说下省、市、区、乡镇，精确到门牌号。",
                    round_index=13,
                ),
                DialogueTurn(speaker="user", text="幸福家园3号楼", round_index=14),
            ],
            collected_slots=collected_slots,
            runtime_state=state,
        )

        self.assertEqual(locality_first_result.reply, "好的，请您说一下省、市、区和街道。")
        self.assertEqual(state.partial_address_candidate, "幸福家园3号楼")

        province_city_result = policy.respond(
            scenario=scenario,
            transcript=[
                DialogueTurn(
                    speaker="service",
                    text="好的，请您说一下省、市、区和街道。",
                    round_index=15,
                ),
                DialogueTurn(speaker="user", text="江苏省淮安市", round_index=16),
            ],
            collected_slots=collected_slots,
            runtime_state=state,
        )

        self.assertEqual(
            province_city_result.reply,
            "好的，您是在淮安市的哪个区县呢？具体小区门牌号也提供一下呢？",
        )

        district_result = policy.respond(
            scenario=scenario,
            transcript=[
                DialogueTurn(
                    speaker="service",
                    text="好的，您是在淮安市的哪个区县呢？具体小区门牌号也提供一下呢？",
                    round_index=17,
                ),
                DialogueTurn(speaker="user", text="淮阴区", round_index=18),
            ],
            collected_slots=collected_slots,
            runtime_state=state,
        )

        self.assertEqual(district_result.reply, "请问具体是在哪个小区或村呢？尽量详细到门牌号。")

    def test_address_collection_requires_province_city_when_user_only_provides_district_first(self):
        policy = ServiceDialoguePolicy()
        state = ServiceRuntimeState(awaiting_full_address=True, product_arrival_checked=True)
        scenario_data = build_scenario().to_dict()
        scenario_data["customer"]["address"] = "贵州省毕节市纳雍县厍东关乡联合村三组42号"
        scenario = Scenario.from_dict(scenario_data)
        collected_slots = {
            "issue_description": "热水器不制热。",
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
                DialogueTurn(speaker="user", text="纳雍县", round_index=14),
            ],
            collected_slots=collected_slots,
            runtime_state=state,
        )

        self.assertEqual(result.reply, "好的，请您说一下省、市、区和街道。")
        self.assertEqual(state.partial_address_candidate, "纳雍县")

    def test_address_collection_requires_region_when_user_provides_locality_and_detail_without_city(self):
        policy = ServiceDialoguePolicy()
        state = ServiceRuntimeState(awaiting_full_address=True, product_arrival_checked=True)
        scenario_data = build_scenario().to_dict()
        scenario_data["customer"]["address"] = "云南省昆明市西山区书香门第小区5号楼1单元102室"
        scenario = Scenario.from_dict(scenario_data)
        collected_slots = {
            "issue_description": "热水器不制热。",
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
                DialogueTurn(speaker="user", text="书香门第小区5号楼1单元102室", round_index=14),
            ],
            collected_slots=collected_slots,
            runtime_state=state,
        )

        self.assertEqual(result.reply, "好的，请您说一下省、市、区和街道。")
        self.assertEqual(state.partial_address_candidate, "书香门第小区5号楼1单元102室")
        self.assertFalse(state.expected_address_confirmation)

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
            "好的，请您继续说一下区和街道。",
        )

        district_result = policy.respond(
            scenario=scenario,
            transcript=[
                DialogueTurn(
                    speaker="service",
                    text="好的，请您继续说一下区和街道。",
                    round_index=7,
                ),
                DialogueTurn(speaker="user", text="七里河区", round_index=7),
            ],
            collected_slots=collected_slots,
            runtime_state=state,
        )
        self.assertEqual(district_result.reply, "请问具体是在哪个小区或村呢？尽量详细到门牌号。")

        precise_result = policy.respond(
            scenario=scenario,
            transcript=[
                DialogueTurn(
                    speaker="service",
                    text="请问具体是在哪个小区或村呢？尽量详细到门牌号。",
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
            last_address_followup_prompt="请问具体是在哪个小区或村呢？尽量详细到门牌号。",
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
                    text="请问具体是在哪个小区或村呢？尽量详细到门牌号。",
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

    def test_partial_locality_then_region_updates_candidate_and_asks_for_building_detail(self):
        policy = ServiceDialoguePolicy()
        state = ServiceRuntimeState(
            awaiting_full_address=True,
            partial_address_candidate="三门县江南壹号",
            last_address_followup_prompt="好的，请您说一下省、市、区和街道。",
        )
        scenario_data = build_scenario().to_dict()
        scenario_data["customer"]["address"] = "浙江省台州市三门县海润街道江南壹号5栋302室"
        scenario = Scenario.from_dict(scenario_data)

        result = policy.respond(
            scenario=scenario,
            transcript=[
                DialogueTurn(
                    speaker="service",
                    text="好的，请您说一下省、市、区和街道。",
                    round_index=13,
                ),
                DialogueTurn(speaker="user", text="浙江省台州市三门县", round_index=13),
            ],
            collected_slots={
                "issue_description": "漏水。",
                "surname": "陈",
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

        self.assertEqual(result.reply, "请问是几栋几单元几楼几号呢？")
        self.assertEqual(state.partial_address_candidate, "浙江省台州市三门县江南壹号")

    def test_district_plus_community_without_city_reasks_for_region_street(self):
        policy = ServiceDialoguePolicy()
        state = ServiceRuntimeState(awaiting_full_address=True, address_input_attempts=1)
        scenario_data = build_scenario().to_dict()
        scenario_data["customer"]["address"] = "江苏省扬州市宝应县御景豪庭10号楼401室"
        scenario = Scenario.from_dict(scenario_data)

        result = policy.respond(
            scenario=scenario,
            transcript=[
                DialogueTurn(
                    speaker="service",
                    text="好的，需要登记下您的地址，麻烦您完整的说下省、市、区、乡镇，精确到门牌号。",
                    round_index=13,
                ),
                DialogueTurn(speaker="user", text="宝应县御景豪庭", round_index=13),
            ],
            collected_slots={
                "issue_description": "漏水。",
                "surname": "陈",
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

        self.assertEqual(result.reply, "好的，请您说一下省、市、区和街道。")
        self.assertEqual(state.partial_address_candidate, "宝应县御景豪庭")

    def test_partial_district_community_then_province_city_updates_candidate(self):
        policy = ServiceDialoguePolicy()
        state = ServiceRuntimeState(
            awaiting_full_address=True,
            partial_address_candidate="宝应县御景豪庭",
            last_address_followup_prompt="好的，请您说一下省、市、区和街道。",
        )
        scenario_data = build_scenario().to_dict()
        scenario_data["customer"]["address"] = "江苏省扬州市宝应县御景豪庭10号楼401室"
        scenario = Scenario.from_dict(scenario_data)

        result = policy.respond(
            scenario=scenario,
            transcript=[
                DialogueTurn(speaker="service", text="好的，请您说一下省、市、区和街道。", round_index=15),
                DialogueTurn(speaker="user", text="江苏省扬州市", round_index=15),
            ],
            collected_slots={
                "issue_description": "漏水。",
                "surname": "陈",
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

        self.assertEqual(result.reply, "请问是几栋几单元几楼几号呢？")
        self.assertEqual(state.partial_address_candidate, "江苏省扬州市宝应县御景豪庭")

    def test_partial_district_community_detail_then_province_city_starts_confirmation(self):
        policy = ServiceDialoguePolicy()
        state = ServiceRuntimeState(
            awaiting_full_address=True,
            partial_address_candidate="宝应县御景豪庭10号楼401室",
            last_address_followup_prompt="好的，请您说一下省、市、区和街道。",
        )
        scenario_data = build_scenario().to_dict()
        scenario_data["customer"]["address"] = "江苏省扬州市宝应县御景豪庭10号楼401室"
        scenario = Scenario.from_dict(scenario_data)

        result = policy.respond(
            scenario=scenario,
            transcript=[
                DialogueTurn(speaker="service", text="好的，请您说一下省、市、区和街道。", round_index=15),
                DialogueTurn(speaker="user", text="江苏省扬州市", round_index=15),
            ],
            collected_slots={
                "issue_description": "漏水。",
                "surname": "陈",
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
            "好的，跟您确认一下，地址是江苏省扬州市宝应县御景豪庭10号楼401室，对吗？",
        )
        self.assertTrue(state.expected_address_confirmation)
        self.assertEqual(state.pending_address_confirmation, "江苏省扬州市宝应县御景豪庭10号楼401室")

    def test_district_community_then_province_city_then_detail_starts_confirmation(self):
        policy = ServiceDialoguePolicy()
        scenario_data = build_scenario().to_dict()
        scenario_data["customer"]["address"] = "江苏省扬州市宝应县御景豪庭10号楼401室"
        scenario = Scenario.from_dict(scenario_data)
        collected_slots = {
            "issue_description": "漏水。",
            "surname": "陈",
            "phone": "13773341553",
            "address": "",
            "product_model": "",
            "request_type": "fault",
            "availability": "",
            "phone_contactable": "yes",
            "phone_contact_owner": "本人当前来电",
            "phone_collection_attempts": "0",
        }

        state = ServiceRuntimeState(awaiting_full_address=True)
        first = policy.respond(
            scenario=scenario,
            transcript=[
                DialogueTurn(
                    speaker="service",
                    text="好的，需要登记下您的地址，麻烦您完整的说下省、市、区、乡镇，精确到门牌号。",
                    round_index=13,
                ),
                DialogueTurn(speaker="user", text="宝应县御景豪庭", round_index=13),
            ],
            collected_slots=collected_slots,
            runtime_state=state,
        )
        self.assertEqual(first.reply, "好的，请您说一下省、市、区和街道。")
        self.assertEqual(state.partial_address_candidate, "宝应县御景豪庭")

        second = policy.respond(
            scenario=scenario,
            transcript=[
                DialogueTurn(speaker="service", text=first.reply, round_index=14),
                DialogueTurn(speaker="user", text="江苏省扬州市", round_index=14),
            ],
            collected_slots=collected_slots,
            runtime_state=state,
        )
        self.assertEqual(second.reply, "请问是几栋几单元几楼几号呢？")
        self.assertEqual(state.partial_address_candidate, "江苏省扬州市宝应县御景豪庭")

        third = policy.respond(
            scenario=scenario,
            transcript=[
                DialogueTurn(speaker="service", text=second.reply, round_index=15),
                DialogueTurn(speaker="user", text="10号楼401室", round_index=15),
            ],
            collected_slots=collected_slots,
            runtime_state=state,
        )
        self.assertEqual(
            third.reply,
            "好的，跟您确认一下，地址是江苏省扬州市宝应县御景豪庭10号楼401室，对吗？",
        )
        self.assertTrue(state.expected_address_confirmation)
        self.assertEqual(state.pending_address_confirmation, "江苏省扬州市宝应县御景豪庭10号楼401室")

    def test_freeform_unknown_actual_address_with_room_can_start_confirmation(self):
        policy = ServiceDialoguePolicy()
        state = ServiceRuntimeState(
            awaiting_full_address=True,
            partial_address_candidate="浙江省台州市三门县",
            last_address_followup_prompt="请问具体是在哪个小区或村呢？尽量详细到门牌号。",
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
                    text="请问具体是在哪个小区或村呢？尽量详细到门牌号。",
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

    def test_closing_flow_uses_product_routing_colmo_brand_for_appointment_and_ending(self):
        policy = ServiceDialoguePolicy()
        state = ServiceRuntimeState()
        scenario_data = build_scenario(call_start_time="10:30:00").to_dict()
        scenario_data["hidden_context"]["product_routing_trace"] = ["brand_series.colmo"]
        scenario_data["hidden_context"]["product_routing_result"] = "家用 + 可直接确认机型"
        scenario = Scenario.from_dict(scenario_data)
        collected_slots = {
            "issue_description": "面板故障。",
            "surname": "汪",
            "phone": "13800138001",
            "address": "山东省济南市历城区华山街道恒大绿洲18号楼2单元602室",
            "product_model": "",
            "request_type": "fault",
            "availability": "",
            "phone_contactable": "yes",
            "phone_contact_owner": "本人当前来电",
            "phone_collection_attempts": "0",
            "product_arrived": "",
            "product_routing_result": "家用 + 可直接确认机型",
        }

        appointment = policy.respond(
            scenario=scenario,
            transcript=[
                DialogueTurn(
                    speaker="service",
                    text="您的地址是山东省济南市历城区华山街道恒大绿洲18号楼2单元602室，对吗？",
                    round_index=6,
                ),
                DialogueTurn(speaker="user", text="是的。", round_index=6),
            ],
            collected_slots=collected_slots,
            runtime_state=state,
        )

        self.assertEqual(
            appointment.reply,
            "好的，您的工单已受理成功，1小时内服务人员会电话联系，预约具体上门时间。",
        )
        self.assertTrue(state.awaiting_closing_ack)

        policy.respond(
            scenario=scenario,
            transcript=[
                DialogueTurn(
                    speaker="service",
                    text="好的，您的工单已受理成功，1小时内服务人员会电话联系，预约具体上门时间。",
                    round_index=7,
                ),
                DialogueTurn(speaker="user", text="好的", round_index=7),
            ],
            collected_slots=collected_slots,
            runtime_state=state,
        )

        end = policy.respond(
            scenario=scenario,
            transcript=[
                DialogueTurn(
                    speaker="service",
                    text="温馨提示，如维修服务产生费用，工程师会详细说明并出示收费标准。 还需要麻烦您对本次通话服务打分，1、非常满意，2、较满意，3、一般，4、较不满，5、非常不满",
                    round_index=8,
                ),
                DialogueTurn(speaker="user", text="1", round_index=8),
            ],
            collected_slots=collected_slots,
            runtime_state=state,
        )

        self.assertEqual(end.reply, "感谢您选择COLMO，微信关注“COLMO公众号”，更多服务随心享，再见！")
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

        self.assertEqual(result.reply, "请问具体是在哪个小区或村呢？尽量详细到门牌号。")
        self.assertEqual(state.partial_address_candidate, "顺德区陈村镇")

    def test_segmented_address_with_letter_building_starts_confirmation(self):
        policy = ServiceDialoguePolicy()
        state = ServiceRuntimeState(
            awaiting_full_address=True,
            partial_address_candidate="广东省佛山市顺德区陈村镇",
            last_address_followup_prompt="请问具体是在哪个小区或村呢？尽量详细到门牌号。",
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
                    text="请问具体是在哪个小区或村呢？尽量详细到门牌号。",
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

    def test_segmented_address_confirmation_display_strips_internal_punctuation(self):
        policy = ServiceDialoguePolicy()
        state = ServiceRuntimeState(
            awaiting_full_address=True,
            partial_address_candidate="浙江省杭州市",
            last_address_followup_prompt="好的，您是在杭州市的哪个区县呢？具体小区门牌号也提供一下呢？",
        )
        scenario_data = build_scenario().to_dict()
        scenario_data["customer"]["address"] = "浙江省杭州市西湖区文二路89号4单元302室"
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
                    text="好的，您是在杭州市的哪个区县呢？具体小区门牌号也提供一下呢？",
                    round_index=12,
                ),
                DialogueTurn(
                    speaker="user",
                    text="西湖区，文二路，89号，4单元302室。",
                    round_index=12,
                ),
            ],
            collected_slots=collected_slots,
            runtime_state=state,
        )

        self.assertEqual(
            result.reply,
            "好的，跟您确认一下，地址是浙江省杭州市西湖区文二路89号4单元302室，对吗？",
        )

    def test_address_confirmation_adds_room_suffix_when_user_omits_shi_suffix(self):
        policy = ServiceDialoguePolicy()
        state = ServiceRuntimeState(
            awaiting_full_address=True,
            partial_address_candidate="浙江省台州市三门县",
            last_address_followup_prompt="请问具体是在哪个小区或村呢？尽量详细到门牌号。",
        )
        scenario_data = build_scenario().to_dict()
        scenario_data["customer"]["address"] = "浙江省台州市三门县新湖国际18幢1单元502室"
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
                    text="请问具体是在哪个小区或村呢？尽量详细到门牌号。",
                    round_index=15,
                ),
                DialogueTurn(
                    speaker="user",
                    text="新湖国际 18 幢 1 单元 502",
                    round_index=15,
                ),
            ],
            collected_slots=collected_slots,
            runtime_state=state,
        )

        self.assertEqual(
            result.reply,
            "好的，跟您确认一下，地址是浙江省台州市三门县新湖国际18幢1单元502室，对吗？",
        )
        self.assertEqual(
            state.pending_address_confirmation,
            "浙江省台州市三门县新湖国际18幢1单元502室",
        )

    def test_address_reask_frustration_confirms_existing_candidate(self):
        policy = ServiceDialoguePolicy()
        state = ServiceRuntimeState(
            awaiting_full_address=True,
            partial_address_candidate="广东省佛山市顺德区陈村镇美景豪庭J座4单元502室",
            last_address_followup_prompt="请问具体是在哪个小区或村呢？尽量详细到门牌号。",
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
                    text="请问具体是在哪个小区或村呢？尽量详细到门牌号。",
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

    def test_cli_freeform_surname_capture_can_use_model_only_for_split_form(self):
        def fake_surname_inference(*, user_text: str, user_round_index: int):
            self.assertEqual(user_text, "关耳郑")
            self.assertEqual(user_round_index, 3)
            return {"surname": "郑"}

        policy = ServiceDialoguePolicy(surname_inference_callback=fake_surname_inference)
        state = ServiceRuntimeState(product_arrival_checked=True)
        scenario = build_freeform_cli_scenario()
        transcript = [
            DialogueTurn(speaker="service", text="请问您贵姓？", round_index=3),
            DialogueTurn(speaker="user", text="关耳郑", round_index=3),
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

        self.assertEqual(result.slot_updates["surname"], "郑")
        self.assertEqual(result.reply, "请问您当前这个来电号码能联系到您吗？")
        self.assertTrue(policy.last_used_model_intent_inference)

    def test_apology_prefixed_surname_prompt_uses_same_model_path(self):
        def fake_surname_inference(*, user_text: str, user_round_index: int):
            self.assertEqual(user_text, "啊，我姓什么，东耳郑")
            self.assertEqual(user_round_index, 9)
            return {"surname": "郑"}

        policy = ServiceDialoguePolicy(surname_inference_callback=fake_surname_inference)
        state = ServiceRuntimeState(product_arrival_checked=True)
        scenario = build_freeform_cli_scenario(request_type="fault")
        transcript = [
            DialogueTurn(
                speaker="service",
                text="非常抱歉，给您添麻烦了，我这就安排师傅上门维修，请问您贵姓？",
                round_index=8,
            ),
            DialogueTurn(speaker="user", text="啊，我姓什么，东耳郑", round_index=9),
        ]
        collected_slots = {
            "issue_description": "热水器不加热。",
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

        self.assertEqual(result.slot_updates["surname"], "郑")
        self.assertEqual(result.reply, "请问您当前这个来电号码能联系到您吗？")
        self.assertTrue(policy.last_used_model_intent_inference)

    def test_unknown_actual_address_town_only_reply_keeps_locality_followup(self):
        policy = ServiceDialoguePolicy(ok_prefix_probability=0.0)
        state = ServiceRuntimeState(
            awaiting_full_address=True,
            partial_address_candidate="上海市青浦区",
            last_address_followup_prompt="请问具体是在哪个小区或村呢？尽量详细到门牌号。",
        )
        scenario = build_freeform_cli_scenario(request_type="fault")
        collected_slots = {
            "issue_description": "热水器不加热。",
            "surname": "郑",
            "phone": "13800138001",
            "address": "",
            "request_type": "fault",
            "phone_contactable": "yes",
            "phone_contact_owner": "本人当前来电",
            "phone_collection_attempts": "0",
            "product_arrived": "",
        }

        result = policy.respond(
            scenario=scenario,
            transcript=[
                DialogueTurn(
                    speaker="service",
                    text="请问具体是在哪个小区或村呢？尽量详细到门牌号。",
                    round_index=6,
                ),
                DialogueTurn(speaker="user", text="徐泾镇", round_index=7),
            ],
            collected_slots=collected_slots,
            runtime_state=state,
        )

        self.assertEqual(result.reply, "请问具体是在哪个小区或村呢？尽量详细到门牌号。")
        self.assertEqual(state.partial_address_candidate, "上海市青浦区徐泾镇")

    def test_opening_brand_correction_can_skip_first_product_routing_prompt(self):
        policy = ServiceDialoguePolicy(ok_prefix_probability=0.0)
        state = ServiceRuntimeState()
        scenario = build_freeform_cli_scenario(request_type="fault")
        scenario.hidden_context["product_routing_plan"] = {
            "enabled": True,
            "result": "",
            "trace": [],
            "summary": "",
            "steps": [
                {
                    "prompt_key": "brand_or_series",
                    "prompt": "请问您的空气能是什么具体品牌或系列呢？",
                    "answer_key": "entry.unknown",
                    "answer_value": "不知道品牌或系列",
                    "answer_instruction": "自然表达自己不知道品牌或系列。",
                }
            ],
        }

        result = policy.respond(
            scenario=scenario,
            transcript=[
                DialogueTurn(
                    speaker="service",
                    text="您好，很高兴为您服务，请问是美的空气能热水机需要维修吗？",
                    round_index=1,
                ),
                DialogueTurn(speaker="user", text="不是，是小天鹅的", round_index=2),
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
                "product_routing_result": "",
            },
            runtime_state=state,
        )

        self.assertEqual(result.reply, "请稍等，正在为您转接人工服务。")
        self.assertEqual(result.close_status, "transferred")
        self.assertEqual(result.close_reason, "product_routing_human")
        self.assertEqual(result.slot_updates["product_routing_result"], "转人工")
        self.assertEqual(state.product_routing_observed_trace, ["brand_series.cooling_or_little_swan"])

    def test_freeform_address_collection_uses_model_only_to_strip_chatter(self):
        def fake_address_inference(**kwargs):
            self.assertEqual(
                kwargs["user_text"],
                "云南南省西双版纳景洪市,我看一下,那个叫雨林名苑2栋2栋2单元405。",
            )
            return {
                "address_candidate": "云南省西双版纳景洪市雨林名苑2栋2单元405",
                "merged_address_candidate": "云南省西双版纳景洪市雨林名苑2栋2单元405",
                "granularity": "complete",
            }

        policy = ServiceDialoguePolicy(address_inference_callback=fake_address_inference)
        state = ServiceRuntimeState(awaiting_full_address=True)
        scenario = build_freeform_cli_scenario()
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
            transcript=[
                DialogueTurn(
                    speaker="service",
                    text="需要登记下您的地址，麻烦您完整的说下省、市、区、乡镇，精确到门牌号。",
                    round_index=8,
                ),
                DialogueTurn(
                    speaker="user",
                    text="云南南省西双版纳景洪市,我看一下,那个叫雨林名苑2栋2栋2单元405。",
                    round_index=9,
                ),
            ],
            collected_slots=collected_slots,
            runtime_state=state,
        )

        self.assertEqual(
            result.reply,
            "好的，跟您确认一下，地址是云南省西双版纳景洪市雨林名苑2栋2单元405，对吗？",
        )
        self.assertTrue(state.expected_address_confirmation)
        self.assertEqual(
            state.pending_address_confirmation,
            "云南省西双版纳景洪市雨林名苑2栋2单元405",
        )

    def test_address_confirmation_reorders_detail_granularity_after_model_extraction(self):
        def fake_address_inference(**kwargs):
            return {
                "address_candidate": "浙江省宁波市海曙区文苑风荷3单元2301室23楼",
                "merged_address_candidate": "浙江省宁波市海曙区文苑风荷3单元2301室23楼",
                "granularity": "complete",
            }

        policy = ServiceDialoguePolicy(address_inference_callback=fake_address_inference)
        state = ServiceRuntimeState(awaiting_full_address=True)
        scenario = build_freeform_cli_scenario()
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
            transcript=[
                DialogueTurn(
                    speaker="service",
                    text="请问是几栋几单元几楼几号呢？",
                    round_index=14,
                ),
                DialogueTurn(speaker="user", text="3单元2301室23楼", round_index=15),
            ],
            collected_slots=collected_slots,
            runtime_state=state,
        )

        self.assertEqual(
            result.reply,
            "好的，跟您确认一下，地址是浙江省宁波市海曙区文苑风荷3单元23楼2301室，对吗？",
        )
        self.assertEqual(
            state.pending_address_confirmation,
            "浙江省宁波市海曙区文苑风荷3单元23楼2301室",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
