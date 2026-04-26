from __future__ import annotations

import json
import random
import re
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from css_data_synthesis_test.address_utils import extract_address_components
from css_data_synthesis_test.config import AppConfig
from css_data_synthesis_test.dialogue_plans import decide_second_round_reply_strategy
from css_data_synthesis_test.hidden_settings_tool import (
    COHERENT_ADDRESS_ADMIN_OPTIONS,
    COHERENT_MUNICIPALITY_CITY_DISTRICT_MAP,
    COHERENT_MUNICIPALITY_OPTIONS,
    COHERENT_REGION_CITY_DISTRICT_MAP,
    COHERENT_REGION_OPTIONS,
    HiddenSettingsRepository,
    HiddenSettingsTool,
    SURNAME_OPTIONS,
    UtteranceReferenceSample,
    UserGenerationPlan,
    generate_local_customer_address,
)
from css_data_synthesis_test.prompts import build_user_agent_messages, next_address_input_value
from css_data_synthesis_test.schemas import DialogueTurn, Scenario


class SequenceFakeClient:
    def __init__(self, responses: list[dict]):
        self.responses = responses
        self.calls = 0
        self.requests: list[dict] = []

    def complete_json(self, **kwargs):
        if self.calls >= len(self.responses):
            raise AssertionError("Fake client ran out of prepared responses.")
        self.requests.append(kwargs)
        response = self.responses[self.calls]
        self.calls += 1
        return response


def build_config(
    store_path: Path,
    *,
    utterance_reference_sample_probability: float = 0.0,
    installation_request_probability: float = 0.5,
    hidden_settings_multi_fault_probability: float = 0.1,
    second_round_include_issue_probability: float = 0.5,
    current_call_contactable_probability: float = 0.75,
    phone_collection_second_attempt_probability: float = 0.35,
    phone_collection_third_attempt_probability: float = 0.2,
    phone_collection_invalid_short_probability: float = 0.34,
    phone_collection_invalid_long_probability: float = 0.33,
    phone_collection_invalid_pattern_probability: float = 0.33,
    phone_collection_invalid_digit_mismatch_probability: float = 0.33,
    service_known_address_probability: float = 0.2,
    service_known_address_matches_probability: float = 0.8,
    address_collection_followup_probability: float = 0.35,
    address_segmented_reply_probability: float | None = None,
    address_segment_rounds_weights: dict[str, float] | None = None,
    address_segment_2_strategy_weights: dict[str, float] | None = None,
    address_segment_3_strategy_weights: dict[str, float] | None = None,
    address_segment_4_strategy_weights: dict[str, float] | None = None,
    address_segment_5_strategy_weights: dict[str, float] | None = None,
    address_input_omit_province_city_suffix_probability: float = 0.0,
    address_confirmation_direct_correction_probability: float = 0.5,
    user_reply_off_topic_probability: float = 0.18,
    user_reply_off_topic_target_weights: dict[str, float] | None = None,
    user_reply_off_topic_rounds_weights: dict[str, float] | None = None,
    user_address_nonstandard_probability: float = 0.28,
    user_address_nonstandard_style_weights: dict[str, float] | None = None,
    address_known_mismatch_start_level_weights: dict[str, float] | None = None,
    address_known_mismatch_rewrite_end_level_weights: dict[str, float] | None = None,
) -> AppConfig:
    if address_segmented_reply_probability is None:
        address_segmented_reply_probability = address_collection_followup_probability
    if address_segment_rounds_weights is None:
        address_segment_rounds_weights = {"2": 0.45, "3": 0.35, "4": 0.20}
    if address_segment_2_strategy_weights is None:
        address_segment_2_strategy_weights = {
            "province_city_district_locality__detail": 0.6,
            "province_city_district__locality_detail": 0.4,
        }
    if address_segment_3_strategy_weights is None:
        address_segment_3_strategy_weights = {
            "province_city_district__locality__detail": 0.5454545454545454,
            "province_city__district_locality__detail": 0.2727272727272727,
            "province_city__district__locality_detail": 0.18181818181818182,
        }
    if address_segment_4_strategy_weights is None:
        address_segment_4_strategy_weights = {
            "province_city__district__locality__detail": 1.0,
        }
    if address_segment_5_strategy_weights is None:
        address_segment_5_strategy_weights = {
            "province__city__district__locality__detail": 1.0,
        }
    if address_known_mismatch_start_level_weights is None:
        address_known_mismatch_start_level_weights = {
            "province": 0.05,
            "city": 0.10,
            "district": 0.15,
            "locality": 0.25,
            "building": 0.15,
            "unit": 0.10,
            "floor": 0.05,
            "room": 0.15,
        }
    if address_known_mismatch_rewrite_end_level_weights is None:
        address_known_mismatch_rewrite_end_level_weights = {
            "province": 0.05,
            "city": 0.08,
            "district": 0.10,
            "locality": 0.14,
            "building": 0.16,
            "unit": 0.16,
            "floor": 0.11,
            "room": 0.20,
        }
    if user_address_nonstandard_style_weights is None:
        user_address_nonstandard_style_weights = {
            "house_number_only": 0.45,
            "rural_group_number": 0.25,
            "landmark_poi": 0.30,
        }
    if user_reply_off_topic_target_weights is None:
        user_reply_off_topic_target_weights = {
            "opening_confirmation": 0.08,
            "issue_description": 0.12,
            "surname_collection": 0.10,
            "phone_contact_confirmation": 0.08,
            "phone_keypad_input": 0.04,
            "phone_confirmation": 0.04,
            "address_collection": 0.30,
            "address_confirmation": 0.08,
            "product_arrival_confirmation": 0.08,
            "product_model_collection": 0.05,
            "closing_acknowledgement": 0.03,
        }
    if user_reply_off_topic_rounds_weights is None:
        user_reply_off_topic_rounds_weights = {"1": 0.85, "2": 0.12, "3": 0.03}
    return AppConfig(
        openai_base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        openai_api_key="sk-a5735e44c73347978f9a4664ef8bea7d",
        user="test-user",
        default_model="qwen3.5-plus",
        user_agent_model="qwen3.5-plus",
        service_agent_model="qwen3.5-plus",
        default_temperature=0.7,
        service_ok_prefix_probability=0.7,
        service_query_prefix_weights={"好的": 0.7, "嗯嗯": 0.0, "了解了": 0.0, "": 0.3},
        second_round_include_issue_probability=second_round_include_issue_probability,
        max_rounds=20,
        max_concurrency=5,
        request_timeout=30,
        data_dir=store_path.parent,
        output_dir=store_path.parent,
        hidden_settings_store=store_path,
        utterance_reference_library_path=store_path.parent / "utterance_reference_library.json",
        utterance_reference_sample_probability=utterance_reference_sample_probability,
        product_routing_enabled=True,
        product_routing_apply_probability=1.0,
        hidden_settings_similarity_threshold=0.82,
        hidden_settings_duplicate_threshold=0.5,
        hidden_settings_max_attempts=3,
        hidden_settings_multi_fault_probability=hidden_settings_multi_fault_probability,
        installation_request_probability=installation_request_probability,
        current_call_contactable_probability=current_call_contactable_probability,
        phone_collection_second_attempt_probability=phone_collection_second_attempt_probability,
        phone_collection_third_attempt_probability=phone_collection_third_attempt_probability,
        phone_collection_invalid_short_probability=phone_collection_invalid_short_probability,
        phone_collection_invalid_long_probability=phone_collection_invalid_long_probability,
        phone_collection_invalid_pattern_probability=phone_collection_invalid_pattern_probability,
        phone_collection_invalid_digit_mismatch_probability=phone_collection_invalid_digit_mismatch_probability,
        service_known_address_probability=service_known_address_probability,
        service_known_address_matches_probability=service_known_address_matches_probability,
        address_collection_followup_probability=address_collection_followup_probability,
        address_segmented_reply_probability=address_segmented_reply_probability,
        address_segment_rounds_weights=address_segment_rounds_weights,
        address_segment_2_strategy_weights=address_segment_2_strategy_weights,
        address_segment_3_strategy_weights=address_segment_3_strategy_weights,
        address_segment_4_strategy_weights=address_segment_4_strategy_weights,
        address_segment_5_strategy_weights=address_segment_5_strategy_weights,
        address_input_omit_province_city_suffix_probability=address_input_omit_province_city_suffix_probability,
        address_confirmation_direct_correction_probability=address_confirmation_direct_correction_probability,
        user_reply_off_topic_probability=user_reply_off_topic_probability,
        user_reply_off_topic_target_weights=user_reply_off_topic_target_weights,
        user_reply_off_topic_rounds_weights=user_reply_off_topic_rounds_weights,
        user_address_nonstandard_probability=user_address_nonstandard_probability,
        user_address_nonstandard_style_weights=user_address_nonstandard_style_weights,
        address_known_mismatch_start_level_weights=address_known_mismatch_start_level_weights,
        address_known_mismatch_rewrite_end_level_weights=address_known_mismatch_rewrite_end_level_weights,
    )


def build_base_scenario() -> Scenario:
    return Scenario.from_dict(
        {
            "scenario_id": "midea_heat_pump_fault_test_001",
            "product": {
                "brand": "美的",
                "category": "空气能热水器",
                "model": "KF66/200L-MI(E4)",
                "purchase_channel": "京东官方旗舰店",
            },
            "customer": {
                "full_name": "占位用户",
                "surname": "占",
                "phone": "13800000000",
                "address": "占位地址",
                "persona": "占位画像",
                "speech_style": "占位说话方式",
            },
            "request": {
                "request_type": "fault",
                "issue": "占位问题",
                "desired_resolution": "占位诉求",
                "availability": "占位时间",
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
            "tags": ["midea", "heat_pump_water_heater"],
        }
    )


def build_installation_scenario() -> Scenario:
    return Scenario.from_dict(
        {
            "scenario_id": "midea_heat_pump_installation_test_001",
            "product": {
                "brand": "美的",
                "category": "空气能热水机",
                "model": "RSJ-20/300RDN3-C",
                "purchase_channel": "天猫官方旗舰店",
            },
            "customer": {
                "full_name": "占位用户",
                "surname": "占",
                "phone": "13800000000",
                "address": "占位地址",
                "persona": "占位画像",
                "speech_style": "占位说话方式",
            },
            "request": {
                "request_type": "installation",
                "issue": "占位安装问题",
                "desired_resolution": "占位诉求",
                "availability": "占位时间",
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
            "tags": ["midea", "heat_pump_water_heater", "installation"],
        }
    )


def build_candidate(
    *,
    full_name: str,
    surname: str,
    phone: str,
    address: str,
    persona: str,
    speech_style: str,
    issue: str,
    desired_resolution: str,
    availability: str,
    emotion: str,
    urgency: str,
    prior_attempts: str,
    special_constraints: str,
    gender: str = "",
) -> dict:
    return {
        "customer": {
            "full_name": full_name,
            "surname": surname,
            "phone": phone,
            "address": address,
            "persona": persona,
            "speech_style": speech_style,
        },
        "request": {
            "request_type": "fault",
            "issue": issue,
            "desired_resolution": desired_resolution,
            "availability": availability,
        },
        "hidden_context": {
            "gender": gender,
            "emotion": emotion,
            "urgency": urgency,
            "prior_attempts": prior_attempts,
            "special_constraints": special_constraints,
        },
    }


class HiddenSettingsToolTests(unittest.TestCase):
    def test_second_round_reply_strategy_is_not_derived_from_scenario_id(self):
        with patch(
            "css_data_synthesis_test.dialogue_plans.random.random",
            side_effect=[0.9, 0.1],
        ):
            first = decide_second_round_reply_strategy("same_scenario", 0.5)
            second = decide_second_round_reply_strategy("same_scenario", 0.5)

        self.assertEqual(first, "confirm_only")
        self.assertEqual(second, "confirm_with_issue")

    def test_frontend_auto_configured_known_address_can_force_actual_address_match(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            known_address = "浙江省杭州市余杭区良渚街道玉鸟路88号1幢101室"
            base = build_base_scenario()
            scenario = base.with_generated_hidden_settings(
                customer=base.customer,
                request=base.request,
                hidden_context={
                    **dict(base.hidden_context),
                    "frontend_auto_address_policy_enabled": True,
                    "frontend_auto_configured_known_address": known_address,
                },
            )
            tool = HiddenSettingsTool(
                SequenceFakeClient(
                    [
                        build_candidate(
                            full_name="赵欣",
                            surname="赵",
                            phone="13876543210",
                            address="江苏省扬州市宝应县安宜镇宝应碧桂园3幢5层502室",
                            persona="配合度正常。",
                            speech_style="表达直接。",
                            issue="空气能热水机不出热水。",
                            desired_resolution="安排师傅上门维修。",
                            availability="周六下午",
                            emotion="平静",
                            urgency="中",
                            prior_attempts="还没处理过",
                            special_constraints="白天有人",
                        )
                    ]
                ),
                build_config(
                    Path(temp_dir) / "hidden_settings_history.jsonl",
                    service_known_address_matches_probability=1.0,
                ),
            )

            generated = tool.generate_for_scenario(scenario)

            self.assertEqual(generated.customer.address, known_address)
            self.assertTrue(generated.hidden_context["service_known_address"])
            self.assertEqual(generated.hidden_context["service_known_address_value"], known_address)
            self.assertTrue(generated.hidden_context["service_known_address_matches_actual"])

    def test_frontend_auto_configured_known_address_can_force_actual_address_mismatch(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            known_address = "浙江省杭州市余杭区良渚街道玉鸟路88号1幢101室"
            actual_address = "江苏省扬州市宝应县安宜镇宝应碧桂园3幢5层502室"
            base = build_base_scenario()
            scenario = base.with_generated_hidden_settings(
                customer=base.customer,
                request=base.request,
                hidden_context={
                    **dict(base.hidden_context),
                    "frontend_auto_address_policy_enabled": True,
                    "frontend_auto_configured_known_address": known_address,
                },
            )
            tool = HiddenSettingsTool(
                SequenceFakeClient(
                    [
                        build_candidate(
                            full_name="赵欣",
                            surname="赵",
                            phone="13876543210",
                            address=actual_address,
                            persona="配合度正常。",
                            speech_style="表达直接。",
                            issue="空气能热水机不出热水。",
                            desired_resolution="安排师傅上门维修。",
                            availability="周六下午",
                            emotion="平静",
                            urgency="中",
                            prior_attempts="还没处理过",
                            special_constraints="白天有人",
                        )
                    ]
                ),
                build_config(
                    Path(temp_dir) / "hidden_settings_history.jsonl",
                    service_known_address_matches_probability=0.0,
                    address_confirmation_direct_correction_probability=1.0,
                ),
            )

            generated = tool.generate_for_scenario(scenario)

            self.assertEqual(generated.customer.address, actual_address)
            self.assertTrue(generated.hidden_context["service_known_address"])
            self.assertEqual(generated.hidden_context["service_known_address_value"], known_address)
            self.assertFalse(generated.hidden_context["service_known_address_matches_actual"])
            self.assertEqual(generated.hidden_context["service_known_address_correction_value"], actual_address)

    def test_frontend_auto_empty_known_address_forces_unknown_service_address(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            base = build_base_scenario()
            scenario = base.with_generated_hidden_settings(
                customer=base.customer,
                request=base.request,
                hidden_context={
                    **dict(base.hidden_context),
                    "frontend_auto_address_policy_enabled": True,
                    "frontend_auto_configured_known_address": "",
                },
            )
            tool = HiddenSettingsTool(
                SequenceFakeClient(
                    [
                        build_candidate(
                            full_name="赵欣",
                            surname="赵",
                            phone="13876543210",
                            address="江苏省扬州市宝应县安宜镇宝应碧桂园3幢5层502室",
                            persona="配合度正常。",
                            speech_style="表达直接。",
                            issue="空气能热水机不出热水。",
                            desired_resolution="安排师傅上门维修。",
                            availability="周六下午",
                            emotion="平静",
                            urgency="中",
                            prior_attempts="还没处理过",
                            special_constraints="白天有人",
                        )
                    ]
                ),
                build_config(
                    Path(temp_dir) / "hidden_settings_history.jsonl",
                    service_known_address_probability=1.0,
                ),
            )

            generated = tool.generate_for_scenario(scenario)

            self.assertFalse(generated.hidden_context["service_known_address"])
            self.assertEqual(generated.hidden_context["service_known_address_value"], "")

    def test_reply_noise_target_probabilities_scale_with_total_probability(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store_path = Path(temp_dir) / "hidden_settings_history.jsonl"
            tool = HiddenSettingsTool(
                SequenceFakeClient([]),
                build_config(
                    store_path,
                    user_reply_off_topic_probability=0.2,
                    user_reply_off_topic_target_weights={
                        "address_collection": 0.5,
                        "surname_collection": 0.25,
                    },
                ),
            )

            probabilities = tool._reply_noise_target_probabilities()

            self.assertEqual(probabilities["address_collection"], 0.1)
            self.assertEqual(probabilities["surname_collection"], 0.05)

    def test_generation_plan_can_inject_nonstandard_address_and_reply_noise(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store_path = Path(temp_dir) / "hidden_settings_history.jsonl"
            config = build_config(store_path)
            scenario = build_installation_scenario()
            candidate = build_candidate(
                full_name="王家俊",
                surname="王",
                phone="13773341553",
                address="江苏省苏州市吴中区松涛街幸福家园134号",
                persona="普通家庭用户，讲话比较随意，但愿意配合登记。",
                speech_style="口语化，偶尔先说一半再补充。",
                issue="新买的空气能热水机还没到，想先问清楚安装流程。",
                desired_resolution="先登记信息，等到货后再安排安装。",
                availability="工作日下午或者周末都可以。",
                emotion="平静",
                urgency="中",
                prior_attempts="看过安装说明，但不太确定需要准备什么。",
                special_constraints="小区白天门口停车不太方便。",
            )
            tool = HiddenSettingsTool(SequenceFakeClient([candidate]), config)
            generation_plan = UserGenerationPlan(
                address_style="house_number_only",
                address_instruction="生成可定位但不一定有栋单元室的地址，优先使用路名/街区/社区/园区/沿街商铺 + 明确门牌号，例如“幸福家园134号”“沿街商铺28号”。",
                reply_noise_enabled=True,
                reply_noise_target="address_collection",
                reply_noise_rounds=2,
                reply_noise_instruction="允许在第一次被问地址时，先轻微答偏 1 次，例如只说到区域、先反问一句，或只补一部分地址；后续追问里按地址计划正常补齐。",
            )

            with patch.object(HiddenSettingsTool, "_sample_user_generation_plan", return_value=generation_plan):
                generated = tool.generate_for_scenario(scenario)

            self.assertEqual(generated.hidden_context["user_address_style"], "house_number_only")
            self.assertEqual(generated.hidden_context["user_reply_noise_target"], "address_collection")
            self.assertEqual(generated.hidden_context["user_reply_noise_rounds"], 2)
            request_prompt = tool.client.requests[0]["messages"][-1]["content"]
            self.assertIn("当前地址形态要求: 生成可定位但不一定有栋单元室的地址", request_prompt)
            self.assertIn("本场景用户回复随机性要求: 允许在第一次被问地址时", request_prompt)

    def test_normalize_generated_payload_rejects_multiple_fault_symptoms_by_default(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store_path = Path(temp_dir) / "hidden_settings_history.jsonl"
            tool = HiddenSettingsTool(
                SequenceFakeClient([]),
                build_config(store_path, hidden_settings_multi_fault_probability=0.0),
            )

            with self.assertRaisesRegex(ValueError, "usually describe only one fault symptom"):
                tool._normalize_generated_payload(
                    build_candidate(
                        full_name="李敏",
                        surname="李",
                        phone="13912345678",
                        address="江苏省苏州市吴中区金枫路金色家园88号3幢1201室",
                        persona="说话直接，比较关注老人洗澡热水是否稳定",
                        speech_style="说话简短，偶尔会直接打断补充重点",
                        issue="设备显示 E4 故障码，热水供应极不稳定。",
                        desired_resolution="希望尽快安排师傅上门检查温控和主机运行情况",
                        availability="周五晚上七点后或者周日白天",
                        emotion="有些着急但还算克制",
                        urgency="中高",
                        prior_attempts="重启过一次机器，没有改善",
                        special_constraints="家里有老人，晚上更需要稳定热水",
                    ),
                    "fault",
                    scenario_id="midea_heat_pump_fault_test_001",
                )

    def test_normalize_generated_payload_rejects_live_style_multi_fault_issue_by_default(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store_path = Path(temp_dir) / "hidden_settings_history.jsonl"
            tool = HiddenSettingsTool(SequenceFakeClient([]), build_config(store_path))

            with self.assertRaisesRegex(ValueError, "too many fault symptoms"):
                tool._normalize_generated_payload(
                    build_candidate(
                        full_name="秦志宏",
                        surname="秦",
                        phone="13688889999",
                        address="广东省深圳市南山区科技园路88号中科轩逸小区3栋1402室",
                        persona="刚创业的年轻总经理，工作繁忙但注重品质生活。",
                        speech_style="语速较快，表达直截了当。",
                        issue="设备启动后直接显示 E4 故障码，热水供应中断，设定水温 55°C 但出水为常温。",
                        desired_resolution="希望尽快安排上门处理。",
                        availability="本周四下午 3 点到 5 点。",
                        emotion="略显焦躁",
                        urgency="较为紧急",
                        prior_attempts="重启过设备",
                        special_constraints="小区门禁需提前登记",
                    ),
                    "fault",
                    scenario_id="midea_heat_pump_fault_001",
                )

    def test_normalize_generated_payload_sanitizes_formatted_mobile_phone(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store_path = Path(temp_dir) / "hidden_settings_history.jsonl"
            tool = HiddenSettingsTool(SequenceFakeClient([]), build_config(store_path))

            normalized = tool._normalize_generated_payload(
                build_candidate(
                    full_name="李敏",
                    surname="李",
                    phone="+86 139-1234-5678",
                    address="江苏省苏州市吴中区金枫路金色家园88号3幢1201室",
                    persona="说话直接，比较关注老人洗澡热水是否稳定",
                    speech_style="说话简短，偶尔会直接打断补充重点",
                    issue="家里的美的空气能热水器最近早晚水温不稳定，偶尔会突然变温",
                    desired_resolution="希望尽快安排师傅上门检查温控和主机运行情况",
                    availability="周五晚上七点后或者周日白天",
                    emotion="有些着急但还算克制",
                    urgency="中高",
                    prior_attempts="重启过一次机器，没有改善",
                    special_constraints="家里有老人，晚上更需要稳定热水",
                ),
                "fault",
            )

            self.assertEqual(normalized["customer"]["phone"], "13912345678")

    def test_normalize_generated_payload_rejects_incomplete_partial_address(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store_path = Path(temp_dir) / "hidden_settings_history.jsonl"
            tool = HiddenSettingsTool(SequenceFakeClient([]), build_config(store_path))

            with self.assertRaisesRegex(ValueError, "city-level region"):
                tool._normalize_generated_payload(
                    build_candidate(
                        full_name="李敏",
                        surname="李",
                        phone="13912345678",
                        address="龙城花园南街62号",
                        persona="说话直接，比较关注老人洗澡热水是否稳定",
                        speech_style="说话简短，偶尔会直接打断补充重点",
                        issue="家里的美的空气能热水器最近早晚水温不稳定，偶尔会突然变温",
                        desired_resolution="希望尽快安排师傅上门检查温控和主机运行情况",
                        availability="周五晚上七点后或者周日白天",
                        emotion="有些着急但还算克制",
                        urgency="中高",
                        prior_attempts="重启过一次机器，没有改善",
                        special_constraints="家里有老人，晚上更需要稳定热水",
                    ),
                    "fault",
                )

    def test_normalize_generated_payload_rejects_landmark_only_address_without_community_or_village(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store_path = Path(temp_dir) / "hidden_settings_history.jsonl"
            tool = HiddenSettingsTool(SequenceFakeClient([]), build_config(store_path))

            with self.assertRaisesRegex(ValueError, "community- or village-level locality"):
                tool._normalize_generated_payload(
                    build_candidate(
                        full_name="李敏",
                        surname="李",
                        phone="13912345678",
                        address="贵州省遵义市汇川区深圳大道与延安路交汇处西南角贵州航天医院隔壁药房后巷3号门面",
                        persona="说话直接，比较关注老人洗澡热水是否稳定",
                        speech_style="说话简短，偶尔会直接打断补充重点",
                        issue="家里的美的空气能热水器最近早晚水温不稳定，偶尔会突然变温",
                        desired_resolution="希望尽快安排师傅上门检查温控和主机运行情况",
                        availability="周五晚上七点后或者周日白天",
                        emotion="有些着急但还算克制",
                        urgency="中高",
                        prior_attempts="重启过一次机器，没有改善",
                        special_constraints="家里有老人，晚上更需要稳定热水",
                    ),
                    "fault",
                )

    def test_normalize_generated_payload_keeps_explicit_gender(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store_path = Path(temp_dir) / "hidden_settings_history.jsonl"
            tool = HiddenSettingsTool(SequenceFakeClient([]), build_config(store_path))

            normalized = tool._normalize_generated_payload(
                build_candidate(
                    full_name="李敏",
                    surname="李",
                    phone="13912345678",
                    address="江苏省苏州市吴中区金枫路金色家园88号3幢1201室",
                    persona="普通住户，平时主要在家照顾老人和孩子。",
                    speech_style="表达比较日常，偶尔会重复一句确认下。",
                    issue="家里的美的空气能热水器最近早晚水温不稳定，偶尔会突然变温",
                    desired_resolution="希望尽快安排师傅上门检查温控和主机运行情况",
                    availability="周五晚上七点后或者周日白天",
                    emotion="有些着急但还算克制",
                    urgency="中高",
                    prior_attempts="重启过一次机器，没有改善",
                    special_constraints="家里有老人，晚上更需要稳定热水",
                    gender="女",
                ),
                "fault",
            )

            self.assertEqual(normalized["hidden_context"]["gender"], "女")

    def test_normalize_generated_payload_can_infer_gender_when_missing(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store_path = Path(temp_dir) / "hidden_settings_history.jsonl"
            tool = HiddenSettingsTool(SequenceFakeClient([]), build_config(store_path))

            normalized = tool._normalize_generated_payload(
                build_candidate(
                    full_name="刘强",
                    surname="刘",
                    phone="13688889999",
                    address="广东省深圳市南山区科技园路88号中科轩逸小区3栋1402室",
                    persona="普通上班族，白天忙，处理问题时希望尽快说清楚。",
                    speech_style="说话偏短句，偶尔会想一下再接着说。",
                    issue="家里的空气能热水器这两天制热明显变慢",
                    desired_resolution="想让师傅尽快上门看看机器现在是什么情况",
                    availability="本周四下午 3 点到 5 点",
                    emotion="略显焦躁",
                    urgency="较为紧急",
                    prior_attempts="重启过设备",
                    special_constraints="小区门禁需提前登记",
                ),
                "fault",
            )

            self.assertEqual(normalized["hidden_context"]["gender"], "男")

    def test_rejects_unsupported_brand(self):
        with self.assertRaises(ValueError):
            Scenario.from_dict(
                {
                    "scenario_id": "bad_brand_case",
                    "product": {
                        "brand": "海尔",
                        "category": "空气能热水器",
                        "model": "X1",
                        "purchase_channel": "门店",
                    },
                    "customer": {
                        "full_name": "张三",
                        "surname": "张",
                        "phone": "13800000000",
                        "address": "上海市浦东新区1号",
                        "persona": "普通用户",
                        "speech_style": "表达正常，比较直接",
                    },
                    "request": {
                        "request_type": "fault",
                        "issue": "测试问题",
                        "desired_resolution": "测试诉求",
                        "availability": "周末",
                    },
                    "required_slots": ["surname"],
                    "max_turns": 2,
                    "tags": [],
                }
            )

    def test_generate_hidden_settings_persists_history(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store_path = Path(temp_dir) / "hidden_settings_history.jsonl"
            tool = HiddenSettingsTool(
                SequenceFakeClient(
                    [
                        build_candidate(
                            full_name="李敏",
                            surname="李",
                            phone="13912345678",
                            address="江苏省苏州市吴中区金枫路金色家园88号3幢1201室",
                            persona="说话直接，比较关注老人洗澡热水是否稳定",
                            speech_style="说话简短，偶尔会直接打断补充重点",
                            issue="家里的美的空气能热水器最近早晚水温不稳定，偶尔会突然变温",
                            desired_resolution="希望尽快安排师傅上门检查温控和主机运行情况",
                            availability="周五晚上七点后或者周日白天",
                            emotion="有些着急但还算克制",
                            urgency="中高",
                            prior_attempts="重启过一次机器，没有改善",
                            special_constraints="家里有老人，晚上更需要稳定热水",
                        )
                    ]
                ),
                build_config(store_path),
            )

            scenario = build_base_scenario()
            generated = tool.generate_for_scenario(scenario)

            self.assertEqual(generated.customer.full_name, "李敏")
            self.assertEqual(generated.customer.surname, "李")
            self.assertEqual(generated.customer.speech_style, "说话简短，偶尔会直接打断补充重点")
            self.assertEqual(generated.request.request_type, "fault")
            self.assertTrue(store_path.exists())

            records = HiddenSettingsRepository(store_path).load()
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0].generated_customer["full_name"], "李敏")
            self.assertEqual(records[0].duplicate_rate, 0.0)

    def test_retries_when_candidate_contains_invalid_phone(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store_path = Path(temp_dir) / "hidden_settings_history.jsonl"
            tool = HiddenSettingsTool(
                SequenceFakeClient(
                    [
                        build_candidate(
                            full_name="李敏",
                            surname="李",
                            phone="电话 12345",
                            address="江苏省苏州市吴中区金枫路金色家园88号3幢1201室",
                            persona="说话直接，比较关注老人洗澡热水是否稳定",
                            speech_style="说话简短，偶尔会直接打断补充重点",
                            issue="家里的美的空气能热水器最近早晚水温不稳定，偶尔会突然变温",
                            desired_resolution="希望尽快安排师傅上门检查温控和主机运行情况",
                            availability="周五晚上七点后或者周日白天",
                            emotion="有些着急但还算克制",
                            urgency="中高",
                            prior_attempts="重启过一次机器，没有改善",
                            special_constraints="家里有老人，晚上更需要稳定热水",
                        ),
                        build_candidate(
                            full_name="周岚",
                            surname="周",
                            phone="13755556666",
                            address="浙江省宁波市鄞州区天童南路阳光花园818号2幢602室",
                            persona="语速偏快，希望一次说清楚，但愿意配合客服确认信息",
                            speech_style="语速偏快，表达流畅，会连续补充细节",
                            issue="空气能热水器白天还能用，晚上多人连续洗澡时热水明显不够，外机还会发出闷响",
                            desired_resolution="想先确认故障原因，并尽快预约上门检测",
                            availability="周六上午九点到十二点",
                            emotion="焦虑但理性",
                            urgency="高",
                            prior_attempts="看过面板设置，也清理过外机周围杂物，问题还在",
                            special_constraints="小区周末白天才能进施工人员，工作日家里没人",
                        ),
                    ]
                ),
                build_config(store_path),
            )

            generated = tool.generate_for_scenario(build_base_scenario())

            self.assertEqual(generated.customer.full_name, "周岚")
            self.assertEqual(generated.customer.phone, "13755556666")
            self.assertEqual(tool.client.calls, 2)

    def test_retries_when_candidate_contains_multiple_fault_symptoms_when_probability_is_zero(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store_path = Path(temp_dir) / "hidden_settings_history.jsonl"
            tool = HiddenSettingsTool(
                SequenceFakeClient(
                    [
                        build_candidate(
                            full_name="李敏",
                            surname="李",
                            phone="13912345678",
                            address="江苏省苏州市吴中区金枫路金色家园88号3幢1201室",
                            persona="说话直接，比较关注老人洗澡热水是否稳定",
                            speech_style="说话简短，偶尔会直接打断补充重点",
                            issue="这个热水器最近总是显示E4故障码，热水不稳定，还有外机有点噪音。",
                            desired_resolution="希望尽快安排师傅上门检查温控和主机运行情况",
                            availability="周五晚上七点后或者周日白天",
                            emotion="有些着急但还算克制",
                            urgency="中高",
                            prior_attempts="重启过一次机器，没有改善",
                            special_constraints="家里有老人，晚上更需要稳定热水",
                        ),
                        build_candidate(
                            full_name="周岚",
                            surname="周",
                            phone="13755556666",
                            address="浙江省宁波市鄞州区天童南路阳光花园818号2幢602室",
                            persona="语速偏快，希望一次说清楚，但愿意配合客服确认信息",
                            speech_style="语速偏快，表达流畅，会连续补充细节",
                            issue="空气能热水器一直显示E4故障码。",
                            desired_resolution="想先确认故障原因，并尽快预约上门检测",
                            availability="周六上午九点到十二点",
                            emotion="焦虑但理性",
                            urgency="高",
                            prior_attempts="看过面板设置，问题还在",
                            special_constraints="小区周末白天才能进施工人员，工作日家里没人",
                        ),
                    ]
                ),
                build_config(store_path, hidden_settings_multi_fault_probability=0.0),
            )

            generated = tool.generate_for_scenario(build_base_scenario())

            self.assertEqual(generated.customer.full_name, "周岚")
            self.assertEqual(generated.request.issue, "空气能热水器一直显示E4故障码。")
            self.assertEqual(tool.client.calls, 2)


class UserPromptTests(unittest.TestCase):
    def test_user_prompt_defaults_to_single_fault_point(self):
        messages = build_user_agent_messages(
            build_base_scenario(),
            transcript=[],
            round_index=1,
        )

        self.assertIn("默认只围绕隐藏设定中的 1 个故障点来描述", messages[1]["content"])

    def test_user_prompt_marks_second_round_as_confirm_only_when_configured(self):
        scenario = build_base_scenario()
        messages = build_user_agent_messages(
            scenario,
            transcript=[
                DialogueTurn(
                    speaker="service",
                    text="您好，很高兴为您服务，请问是美的空气能热水器需要维修吗？",
                    round_index=1,
                )
            ],
            round_index=2,
            second_round_reply_strategy="confirm_only",
        )

        self.assertIn("当前这轮是否正在回应客服开场确认: 是", messages[1]["content"])
        self.assertIn("本场景第二轮回复策略: 只做简短确认，不继续补充故障或安装细节", messages[1]["content"])

    def test_user_prompt_marks_second_round_as_confirm_with_issue_when_replying_to_opening(self):
        scenario = build_base_scenario()
        messages = build_user_agent_messages(
            scenario,
            transcript=[
                DialogueTurn(
                    speaker="service",
                    text="您好，很高兴为您服务，请问是美的空气能热水器需要维修吗？",
                    round_index=1,
                )
            ],
            round_index=2,
            second_round_reply_strategy="confirm_with_issue",
        )

        self.assertIn("当前这轮是否正在回应客服开场确认: 是", messages[1]["content"])
        self.assertIn("本场景第二轮回复策略: 确认后顺带用一句话说出当前故障现象或安装需求", messages[1]["content"])

    def test_user_prompt_blocks_topic_regression_during_address_confirmation(self):
        scenario = build_base_scenario()
        messages = build_user_agent_messages(
            scenario,
            transcript=[
                DialogueTurn(
                    speaker="service",
                    text="跟您确认一下，地址是山东省济南市历下区泉城路218号贵和购物中心公寓楼12层1203室，对吗？",
                    round_index=7,
                )
            ],
            round_index=8,
            second_round_reply_strategy="confirm_only",
        )

        self.assertIn("当前客服在核对地址", messages[1]["content"])
        self.assertIn("不要在这一轮再重复故障、电话、型号或其他旧信息", messages[1]["content"])
        self.assertIn("不必逐字复述", messages[1]["content"])

    def test_user_prompt_exposes_natural_contact_owner_label(self):
        scenario = build_base_scenario()
        scenario.hidden_context["gender"] = "女"
        scenario.hidden_context["current_call_contactable"] = False
        scenario.hidden_context["contact_phone_owner"] = "爱人"
        scenario.hidden_context["contact_phone_owner_spoken_label"] = "我老公"

        messages = build_user_agent_messages(
            scenario,
            transcript=[
                DialogueTurn(
                    speaker="service",
                    text="这个来电号码可以联系到您吗？",
                    round_index=3,
                )
            ],
            round_index=4,
            second_round_reply_strategy="confirm_only",
        )

        self.assertIn("可参考这个含义相近的口语称呼: 我老公", messages[1]["content"])
        self.assertIn("可以自然地用含义相近的口语称呼", messages[1]["content"])

    def test_user_prompt_blocks_promising_later_phone_input_during_contactability_question(self):
        scenario = build_base_scenario()
        scenario.hidden_context["current_call_contactable"] = False
        scenario.hidden_context["contact_phone_owner"] = "父亲"

        messages = build_user_agent_messages(
            scenario,
            transcript=[
                DialogueTurn(
                    speaker="service",
                    text="请问您当前这个来电号码能联系到您吗？",
                    round_index=3,
                )
            ],
            round_index=4,
            second_round_reply_strategy="confirm_only",
        )

        self.assertIn("这一轮必须先明确回答“能联系”或“不能联系”", messages[1]["content"])
        self.assertIn("不要说“待会输入号码”“等会再报号码”这类后续流程话", messages[1]["content"])
        self.assertIn("当前客服在确认这个来电号码能否联系到你", messages[1]["content"])
        self.assertIn("不要提前纠正地址", messages[1]["content"])

    def test_user_prompt_blocks_address_correction_during_repeated_contactability_question(self):
        scenario = build_base_scenario()
        scenario.hidden_context["current_call_contactable"] = False
        scenario.hidden_context["contact_phone_owner"] = "父亲"
        scenario.hidden_context["service_known_address"] = True
        scenario.hidden_context["service_known_address_matches_actual"] = False
        scenario.hidden_context["service_known_address_value"] = "贵州省遵义市汇川区南岭社区华新建材城小区5栋3单元5楼201室"
        scenario.hidden_context["service_known_address_rewrite_levels"] = ["unit"]

        messages = build_user_agent_messages(
            scenario,
            transcript=[
                DialogueTurn(
                    speaker="service",
                    text="请问您当前这个来电号码能联系到您吗？",
                    round_index=4,
                ),
                DialogueTurn(
                    speaker="user",
                    text="刚才那个地址不对，应该是2单元。",
                    round_index=4,
                ),
                DialogueTurn(
                    speaker="service",
                    text="请问您当前这个来电号码能联系到您吗？",
                    round_index=5,
                ),
            ],
            round_index=6,
            second_round_reply_strategy="confirm_only",
        )

        self.assertIn("客服已第 2 次确认这个来电号码能否联系到你", messages[1]["content"])
        self.assertIn("不要再跳去说地址纠错", messages[1]["content"])

    def test_user_prompt_exposes_gender_attribute(self):
        scenario = build_base_scenario()
        scenario.hidden_context["gender"] = "女"

        messages = build_user_agent_messages(
            scenario,
            transcript=[],
            round_index=1,
            second_round_reply_strategy="confirm_only",
        )

        self.assertIn("用户性别: 女", messages[1]["content"])

    def test_user_prompt_exposes_address_mismatch_rewrite_plan(self):
        scenario = build_base_scenario()
        scenario.hidden_context["service_known_address"] = True
        scenario.hidden_context["service_known_address_matches_actual"] = False
        scenario.hidden_context["service_known_address_mismatch_start_level"] = "building"
        scenario.hidden_context["service_known_address_rewrite_levels"] = ["building", "unit", "room"]

        messages = build_user_agent_messages(
            scenario,
            transcript=[
                DialogueTurn(
                    speaker="service",
                    text="您的地址是浙江省杭州市西湖区文三路159号阳光花园15幢3单元502室，对吗？",
                    round_index=6,
                )
            ],
            round_index=7,
            second_round_reply_strategy="confirm_only",
        )

        self.assertIn("错误起始粒度: building", messages[1]["content"])
        self.assertIn("需要重塑的地址粒度链路: building -> unit -> room", messages[1]["content"])

    def test_user_prompt_exposes_address_style_and_reply_noise_plan(self):
        scenario = build_base_scenario()
        scenario.hidden_context["user_address_style"] = "landmark_poi"
        scenario.hidden_context["user_address_style_instruction"] = (
            "生成围绕医院、饭店、酒店、学校、产业园、门店等地标的地址，但仍要能定位，最好同时带路名、门牌号或楼层位置。"
        )
        scenario.hidden_context["user_reply_noise_enabled"] = True
        scenario.hidden_context["user_reply_noise_target"] = "address_collection"
        scenario.hidden_context["user_reply_noise_rounds"] = 2
        scenario.hidden_context["user_reply_noise_instruction"] = (
            "允许在前 2 次被问地址时，先轻微答偏，例如只说到区域、先反问一句，或只补一部分地址；超过后按地址计划正常补齐。"
        )

        messages = build_user_agent_messages(
            scenario,
            transcript=[],
            round_index=1,
            second_round_reply_strategy="confirm_only",
        )

        self.assertIn("用户地址形态类型: landmark_poi", messages[1]["content"])
        self.assertIn("用户地址形态说明: 生成围绕医院、饭店、酒店、学校、产业园、门店等地标的地址", messages[1]["content"])
        self.assertIn("是否允许轻微答非所问: 是", messages[1]["content"])
        self.assertIn("若允许，目标环节: address_collection", messages[1]["content"])
        self.assertIn("若允许，该环节最多可轻微答偏的轮数: 2", messages[1]["content"])
        self.assertIn("地址表达要符合“用户地址形态类型”", messages[1]["content"])

    def test_build_messages_exposes_rich_surname_and_nationwide_region_guidance(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store_path = Path(temp_dir) / "hidden_settings_history.jsonl"
            tool = HiddenSettingsTool(SequenceFakeClient([]), build_config(store_path))

            messages = tool._build_messages(
                build_base_scenario(),
                rejection_feedback="",
                generation_plan=UserGenerationPlan(
                    address_style="standard_residential",
                    address_instruction="生成标准小区/公寓住宅地址，通常包含小区、楼栋、单元、楼层或室号。",
                    reply_noise_enabled=False,
                    reply_noise_target="",
                    reply_noise_rounds=0,
                    reply_noise_instruction="整体正常配合客服，绝大多数轮次直接按问答题回答，不需要刻意答非所问。",
                ),
                forced_surname="周",
            )

        self.assertIn("姓氏候选池示例（仅示例，不限于此）", messages[1]["content"])
        self.assertIn("本次指定姓氏: 周", messages[1]["content"])
        self.assertIn("全国地址地区池示例（仅示例，要求覆盖全国随机采样）", messages[1]["content"])
        self.assertIn("地址地区必须在全国范围内随机取样", messages[1]["content"])
        self.assertIn("不要反复集中在“张、王、李、赵”和“广深杭苏”等少数高频选项", messages[0]["content"])

    def test_build_messages_includes_sampled_utterance_reference_when_provided(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store_path = Path(temp_dir) / "hidden_settings_history.jsonl"
            tool = HiddenSettingsTool(SequenceFakeClient([]), build_config(store_path))

            messages = tool._build_messages(
                build_base_scenario(),
                rejection_feedback="",
                generation_plan=UserGenerationPlan(
                    address_style="standard_residential",
                    address_instruction="生成标准小区/公寓住宅地址，通常包含小区、楼栋、单元、楼层或室号。",
                    reply_noise_enabled=False,
                    reply_noise_target="",
                    reply_noise_rounds=0,
                    reply_noise_instruction="整体正常配合客服，绝大多数轮次直接按问答题回答，不需要刻意答非所问。",
                ),
                utterance_reference=UtteranceReferenceSample(
                    intent="报修",
                    category="不制热 / 无热水",
                    summary="空气能热水器不出热水",
                    original="现在一点热水都没有了。",
                ),
            )

        self.assertIn("参考分类: 不制热 / 无热水", messages[1]["content"])
        self.assertIn("参考总结: 空气能热水器不出热水", messages[1]["content"])
        self.assertIn("参考原话: 现在一点热水都没有了。", messages[1]["content"])

    def test_generate_for_scenario_records_library_reference_in_hidden_context(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store_path = Path(temp_dir) / "hidden_settings_history.jsonl"
            reference_path = Path(temp_dir) / "utterance_reference_library.json"
            reference_path.write_text(
                json.dumps(
                    {
                        "报修": {
                            "不制热 / 无热水": [
                                {
                                    "总结": "空气能热水器不出热水",
                                    "原话": "现在一点热水都没有了。",
                                }
                            ]
                        }
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            config = build_config(
                store_path,
                utterance_reference_sample_probability=1.0,
            )
            config = replace(config, utterance_reference_library_path=reference_path)
            client = SequenceFakeClient(
                [
                    {
                        "customer": {
                            "full_name": "李晓梅",
                            "surname": "李",
                            "phone": "13812345678",
                            "address": "浙江省杭州市余杭区良渚街道阳光家园8幢2单元502室",
                            "persona": "普通家庭用户，比较着急洗澡用水问题。",
                            "speech_style": "说话直接，带一点重复。",
                        },
                        "request": {
                            "request_type": "fault",
                            "issue": "空气能热水器不出热水",
                            "desired_resolution": "希望尽快安排师傅上门检查维修",
                            "availability": "明天下午都在家",
                        },
                        "hidden_context": {
                            "gender": "女",
                            "emotion": "着急",
                            "urgency": "较高",
                            "prior_attempts": "重启过一次，没有恢复。",
                            "special_constraints": "家里老人小孩都要洗澡。",
                        },
                    }
                ]
            )
            tool = HiddenSettingsTool(client, config)

            scenario = tool.generate_for_scenario(
                build_base_scenario(),
                use_utterance_reference=True,
            )

        self.assertEqual(scenario.hidden_context["utterance_reference_source"], "library")
        self.assertEqual(scenario.hidden_context["utterance_reference_intent"], "报修")
        self.assertEqual(scenario.hidden_context["utterance_reference_category"], "不制热 / 无热水")
        self.assertEqual(scenario.hidden_context["utterance_reference_summary"], "空气能热水器不出热水")
        self.assertEqual(scenario.hidden_context["utterance_reference_original"], "现在一点热水都没有了。")

    def test_generate_for_scenario_skips_library_reference_when_not_enabled(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store_path = Path(temp_dir) / "hidden_settings_history.jsonl"
            reference_path = Path(temp_dir) / "utterance_reference_library.json"
            reference_path.write_text(
                json.dumps(
                    {
                        "报修": {
                            "不制热 / 无热水": [
                                {
                                    "总结": "空气能热水器不出热水",
                                    "原话": "现在一点热水都没有了。",
                                }
                            ]
                        }
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            config = build_config(
                store_path,
                utterance_reference_sample_probability=1.0,
            )
            config = replace(config, utterance_reference_library_path=reference_path)
            client = SequenceFakeClient(
                [
                    {
                        "customer": {
                            "full_name": "李晓梅",
                            "surname": "李",
                            "phone": "13812345678",
                            "address": "浙江省杭州市余杭区良渚街道阳光家园8幢2单元502室",
                            "persona": "普通家庭用户，比较着急洗澡用水问题。",
                            "speech_style": "说话直接，带一点重复。",
                        },
                        "request": {
                            "request_type": "fault",
                            "issue": "空气能热水器不出热水",
                            "desired_resolution": "希望尽快安排师傅上门检查维修",
                            "availability": "明天下午都在家",
                        },
                        "hidden_context": {
                            "gender": "女",
                            "emotion": "着急",
                            "urgency": "较高",
                            "prior_attempts": "重启过一次，没有恢复。",
                            "special_constraints": "家里老人小孩都要洗澡。",
                        },
                    }
                ]
            )
            tool = HiddenSettingsTool(client, config)

            scenario = tool.generate_for_scenario(build_base_scenario())

        self.assertEqual(scenario.hidden_context["utterance_reference_source"], "model")
        self.assertNotIn("utterance_reference_category", scenario.hidden_context)

    def test_surname_options_are_limited_to_common_top_50_surnames(self):
        self.assertEqual(len(SURNAME_OPTIONS), 50)
        self.assertEqual(
            SURNAME_OPTIONS,
            (
                "王",
                "李",
                "张",
                "刘",
                "陈",
                "杨",
                "黄",
                "赵",
                "吴",
                "周",
                "徐",
                "孙",
                "马",
                "朱",
                "胡",
                "郭",
                "何",
                "高",
                "林",
                "罗",
                "郑",
                "梁",
                "谢",
                "宋",
                "唐",
                "许",
                "韩",
                "冯",
                "邓",
                "曹",
                "彭",
                "曾",
                "肖",
                "田",
                "董",
                "袁",
                "潘",
                "于",
                "蒋",
                "蔡",
                "余",
                "杜",
                "叶",
                "程",
                "苏",
                "魏",
                "吕",
                "丁",
                "任",
                "沈",
            ),
        )

    def test_user_prompt_adds_hard_guardrail_after_repeated_surname_prompt(self):
        scenario = build_base_scenario()

        messages = build_user_agent_messages(
            scenario,
            transcript=[
                DialogueTurn(speaker="service", text="好的，请问您贵姓", round_index=3),
                DialogueTurn(speaker="user", text="对，到货了，但是还没装。", round_index=3),
                DialogueTurn(speaker="service", text="好的，请问您贵姓", round_index=4),
            ],
            round_index=4,
            second_round_reply_strategy="confirm_only",
        )

        self.assertIn("当前已被问姓氏的次数: 2", messages[1]["content"])
        self.assertIn("客服已第 2 次询问姓氏。你这一轮必须直接回答姓氏", messages[1]["content"])
        self.assertIn("如果上一轮你已经对同一个问题答偏了，这一轮不要复述上一轮自己说过的话", messages[1]["content"])

    def test_user_prompt_guides_natural_surname_reply(self):
        scenario = build_base_scenario()
        scenario.customer.full_name = "王建业"
        scenario.customer.surname = "王"

        messages = build_user_agent_messages(
            scenario,
            transcript=[
                DialogueTurn(speaker="service", text="好的，请问您贵姓？", round_index=3),
            ],
            round_index=4,
            second_round_reply_strategy="confirm_only",
        )

        self.assertIn("优先自然回答姓氏相关信息，比如“我姓王”“免贵姓王”", messages[1]["content"])
        self.assertIn("首次优先用自然口语，如“我姓王”“免贵姓王”“姓王”", messages[1]["content"])

    def test_user_prompt_adds_hard_guardrail_after_repeated_address_prompt(self):
        scenario = build_base_scenario()
        scenario.customer.address = "贵州省遵义市汇川区深圳大道康乐社区62号"
        scenario.hidden_context["address_input_rounds"] = [
            "贵州省遵义市汇川区",
            "深圳大道康乐社区62号",
        ]

        messages = build_user_agent_messages(
            scenario,
            transcript=[
                DialogueTurn(
                    speaker="service",
                    text="好的，需要登记下您的地址，麻烦您完整的说下省、市、区、乡镇，精确到门牌号。",
                    round_index=6,
                ),
                DialogueTurn(speaker="user", text="贵州省遵义市汇川区", round_index=6),
                DialogueTurn(speaker="service", text="请问是几栋几单元几楼几号呢？", round_index=7),
            ],
            round_index=8,
            second_round_reply_strategy="confirm_only",
        )

        self.assertIn("客服已第 2 次追问地址。你这一轮必须直接补当前缺失的地址信息", messages[1]["content"])
        self.assertIn("优先按“贵州省遵义市汇川区深圳大道康乐社区62号”来答", messages[1]["content"])

    def test_user_prompt_blocks_room_only_tail_for_full_address_prompt(self):
        scenario = build_base_scenario()
        scenario.customer.address = "四川省绵阳市涪城区未来城小区3栋2单元803室"
        scenario.hidden_context["address_input_rounds"] = ["803室"]

        messages = build_user_agent_messages(
            scenario,
            transcript=[
                DialogueTurn(
                    speaker="service",
                    text="好的，需要登记下您的地址，麻烦您完整的说下省、市、区、乡镇，精确到门牌号。",
                    round_index=10,
                ),
            ],
            round_index=11,
            second_round_reply_strategy="confirm_only",
        )

        self.assertIn("不要只回答室号、楼层、单元或楼栋尾巴", messages[1]["content"])
        self.assertIn("如果客服让你“完整说下省、市、区、乡镇，精确到门牌号”，不要只回“803室”", messages[1]["content"])

    def test_next_address_input_value_does_not_skip_plan_after_off_topic_reply(self):
        scenario = build_base_scenario()
        scenario.customer.address = "江苏省扬州市宝应县安宜镇宝应碧桂园3幢5层502室"
        scenario.hidden_context["address_input_rounds"] = [
            "江苏省扬州市",
            "宝应县安宜镇",
            "宝应碧桂园3幢5层502室",
        ]

        value = next_address_input_value(
            scenario,
            transcript=[
                DialogueTurn(
                    speaker="service",
                    text="需要登记下您的地址，麻烦您完整的说下省、市、区、乡镇，精确到门牌号。",
                    round_index=6,
                ),
                DialogueTurn(speaker="user", text="你先等一下。", round_index=6),
                DialogueTurn(
                    speaker="service",
                    text="需要登记下您的地址，麻烦您完整的说下省、市、区、乡镇，精确到门牌号。",
                    round_index=7,
                ),
            ],
        )

        self.assertEqual(value, "江苏省扬州市")

    def test_next_address_input_value_falls_back_to_full_address_after_repeating_last_segment(self):
        scenario = build_base_scenario()
        scenario.customer.address = "湖北省武汉市江夏区乌龙泉街道大湖村五组32号"
        scenario.hidden_context["address_input_rounds"] = ["大湖村五组32号"]

        value = next_address_input_value(
            scenario,
            transcript=[
                DialogueTurn(
                    speaker="service",
                    text="需要登记下您的地址，麻烦您完整的说下省、市、区、乡镇，精确到门牌号。",
                    round_index=14,
                ),
                DialogueTurn(speaker="user", text="大湖村五组32号。", round_index=14),
                DialogueTurn(
                    speaker="service",
                    text="需要登记下您的地址，麻烦您完整的说下省、市、区、乡镇，精确到门牌号。",
                    round_index=15,
                ),
            ],
        )

        self.assertEqual(value, "湖北省武汉市江夏区乌龙泉街道大湖村五组32号")

    def test_next_address_input_value_lifts_room_only_plan_when_full_address_is_requested(self):
        scenario = build_base_scenario()
        scenario.customer.address = "四川省绵阳市涪城区未来城小区3栋2单元803室"
        scenario.hidden_context["address_input_rounds"] = ["803室"]

        value = next_address_input_value(
            scenario,
            transcript=[
                DialogueTurn(
                    speaker="service",
                    text="好的，需要登记下您的地址，麻烦您完整的说下省、市、区、乡镇，精确到门牌号。",
                    round_index=10,
                ),
            ],
        )

        self.assertEqual(value, "四川省绵阳市涪城区")

    def test_next_address_input_value_follows_region_street_prompt_scope(self):
        scenario = build_base_scenario()
        scenario.customer.address = "四川省绵阳市涪城区石塘街道未来城小区3栋2单元803室"
        scenario.hidden_context["address_input_rounds"] = [
            "未来城小区3栋2单元803室",
        ]

        region_value = next_address_input_value(
            scenario,
            transcript=[
                DialogueTurn(
                    speaker="service",
                    text="好的，请您说一下省、市、区和街道。",
                    round_index=11,
                ),
            ],
        )
        district_value = next_address_input_value(
            scenario,
            transcript=[
                DialogueTurn(
                    speaker="service",
                    text="好的，请您继续说一下区和街道。",
                    round_index=12,
                ),
            ],
        )

        self.assertEqual(region_value, "四川省绵阳市涪城区石塘街道")
        self.assertEqual(district_value, "涪城区石塘街道")

    def test_user_prompt_blocks_repeating_installation_request_during_product_arrival_confirmation(self):
        scenario = build_installation_scenario()
        messages = build_user_agent_messages(
            scenario,
            transcript=[
                DialogueTurn(
                    speaker="user",
                    text="对，是的，我希望安排师傅上门安装一下。",
                    round_index=2,
                ),
                DialogueTurn(
                    speaker="service",
                    text="好的，请问空气能热水机到货了没？",
                    round_index=2,
                ),
            ],
            round_index=3,
            second_round_reply_strategy="confirm_only",
        )

        self.assertIn("当前客服在确认产品是否到货", messages[1]["content"])
        self.assertIn("不要重复前面已经确认过的安装诉求", messages[1]["content"])
        self.assertIn("优先补充新的细节", messages[1]["content"])

    def test_retries_when_candidate_is_too_similar(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store_path = Path(temp_dir) / "hidden_settings_history.jsonl"
            config = build_config(store_path)
            scenario = build_base_scenario()

            first_candidate = build_candidate(
                full_name="李敏",
                surname="李",
                phone="13912345678",
                address="江苏省苏州市吴中区金枫路金色家园88号3幢1201室",
                persona="说话直接，比较关注老人洗澡热水是否稳定",
                speech_style="说话简短，偶尔会直接打断补充重点",
                issue="家里的美的空气能热水器最近早晚水温不稳定，偶尔会突然变温",
                desired_resolution="希望尽快安排师傅上门检查温控和主机运行情况",
                availability="周五晚上七点后或者周日白天",
                emotion="有些着急但还算克制",
                urgency="中高",
                prior_attempts="重启过一次机器，没有改善",
                special_constraints="家里有老人，晚上更需要稳定热水",
            )
            second_candidate = build_candidate(
                full_name="周岚",
                surname="周",
                phone="13755556666",
                address="浙江省宁波市鄞州区天童南路阳光花园818号2幢602室",
                persona="语速偏快，希望一次说清楚，但愿意配合客服确认信息",
                speech_style="语速偏快，表达流畅，会连续补充细节",
                issue="空气能热水器白天还能用，晚上多人连续洗澡时热水明显不够，外机还会发出闷响",
                desired_resolution="想先确认故障原因，并尽快预约上门检测",
                availability="周六上午九点到十二点",
                emotion="焦虑但理性",
                urgency="高",
                prior_attempts="看过面板设置，也清理过外机周围杂物，问题还在",
                special_constraints="小区周末白天才能进施工人员，工作日家里没人",
            )

            seed_tool = HiddenSettingsTool(SequenceFakeClient([first_candidate]), config)
            seed_tool.generate_for_scenario(scenario)

            retry_client = SequenceFakeClient([first_candidate, second_candidate])
            retry_tool = HiddenSettingsTool(retry_client, config)
            generated = retry_tool.generate_for_scenario(scenario.clone_with_id("midea_heat_pump_fault_test_002"))

            self.assertEqual(retry_client.calls, 2)
            self.assertEqual(generated.customer.full_name, "周岚")
            self.assertEqual(generated.customer.phone, "13755556666")
            retry_prompt = retry_client.requests[1]["messages"][-1]["content"]
            self.assertIn("与历史样本相似度过高", retry_prompt)
            self.assertNotIn(first_candidate["customer"]["address"], retry_prompt)
            self.assertNotIn(first_candidate["customer"]["persona"], retry_prompt)
            self.assertNotIn(first_candidate["request"]["issue"], retry_prompt)

            records = HiddenSettingsRepository(store_path).load()
            self.assertEqual(len(records), 2)
            self.assertEqual(records[-1].generated_customer["full_name"], "周岚")

    def test_similarity_rejection_feedback_does_not_leak_history_content(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store_path = Path(temp_dir) / "hidden_settings_history.jsonl"
            tool = HiddenSettingsTool(SequenceFakeClient([]), build_config(store_path))

            feedback = tool._build_rejection_feedback(
                attempt=2,
                duplicate_rate=0.615,
                similarity_score=0.903,
                most_similar_record=tool.repository.load() or type(
                    "RecordStub",
                    (),
                    {
                        "generated_request": {"issue": "历史问题文本"},
                        "generated_customer": {
                            "address": "历史地址文本",
                            "persona": "历史画像文本",
                            "speech_style": "历史说话方式文本",
                        },
                    },
                )(),
            )

            self.assertIn("duplicate_rate=0.615", feedback)
            self.assertIn("similarity_score=0.903", feedback)
            self.assertIn("不要复述历史样本内容", feedback)
            self.assertNotIn("历史问题文本", feedback)
            self.assertNotIn("历史地址文本", feedback)
            self.assertNotIn("历史画像文本", feedback)
            self.assertNotIn("历史说话方式文本", feedback)

    def test_second_round_reply_strategy_can_be_forced_to_confirm_only(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store_path = Path(temp_dir) / "hidden_settings_history.jsonl"
            tool = HiddenSettingsTool(
                SequenceFakeClient(
                    [
                        build_candidate(
                            full_name="李敏",
                            surname="李",
                            phone="13912345678",
                            address="江苏省苏州市吴中区金枫路金色家园88号3幢1201室",
                            persona="说话直接，比较关注老人洗澡热水是否稳定",
                            speech_style="说话简短，偶尔会直接打断补充重点",
                            issue="家里的美的空气能热水器最近早晚水温不稳定。",
                            desired_resolution="希望尽快安排师傅上门检查温控和主机运行情况",
                            availability="周五晚上七点后或者周日白天",
                            emotion="有些着急但还算克制",
                            urgency="中高",
                            prior_attempts="重启过一次机器，没有改善",
                            special_constraints="家里有老人，晚上更需要稳定热水",
                        )
                    ]
                ),
                build_config(store_path, second_round_include_issue_probability=0.0),
            )

            generated = tool.generate_for_scenario(build_base_scenario())

            self.assertEqual(generated.hidden_context["second_round_reply_strategy"], "confirm_only")

    def test_second_round_reply_strategy_can_be_forced_to_confirm_with_issue(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store_path = Path(temp_dir) / "hidden_settings_history.jsonl"
            tool = HiddenSettingsTool(
                SequenceFakeClient(
                    [
                        build_candidate(
                            full_name="李敏",
                            surname="李",
                            phone="13912345678",
                            address="江苏省苏州市吴中区金枫路金色家园88号3幢1201室",
                            persona="说话直接，比较关注老人洗澡热水是否稳定",
                            speech_style="说话简短，偶尔会直接打断补充重点",
                            issue="家里的美的空气能热水器最近早晚水温不稳定。",
                            desired_resolution="希望尽快安排师傅上门检查温控和主机运行情况",
                            availability="周五晚上七点后或者周日白天",
                            emotion="有些着急但还算克制",
                            urgency="中高",
                            prior_attempts="重启过一次机器，没有改善",
                            special_constraints="家里有老人，晚上更需要稳定热水",
                        )
                    ]
                ),
                build_config(store_path, second_round_include_issue_probability=1.0),
            )

            generated = tool.generate_for_scenario(build_base_scenario())

            self.assertEqual(generated.hidden_context["second_round_reply_strategy"], "confirm_with_issue")

    def test_contactable_current_call_plan_can_be_forced(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store_path = Path(temp_dir) / "hidden_settings_history.jsonl"
            tool = HiddenSettingsTool(
                SequenceFakeClient(
                    [
                        build_candidate(
                            full_name="李敏",
                            surname="李",
                            phone="13912345678",
                            address="江苏省苏州市吴中区金枫路金色家园88号3幢1201室",
                            persona="说话直接，比较关注老人洗澡热水是否稳定",
                            speech_style="说话简短，偶尔会直接打断补充重点",
                            issue="家里的美的空气能热水器最近早晚水温不稳定，偶尔会突然变温",
                            desired_resolution="希望尽快安排师傅上门检查温控和主机运行情况",
                            availability="周五晚上七点后或者周日白天",
                            emotion="有些着急但还算克制",
                            urgency="中高",
                            prior_attempts="重启过一次机器，没有改善",
                            special_constraints="家里有老人，晚上更需要稳定热水",
                        )
                    ]
                ),
                build_config(store_path, current_call_contactable_probability=1.0),
            )

            generated = tool.generate_for_scenario(build_base_scenario())

            self.assertTrue(generated.hidden_context["current_call_contactable"])
            self.assertEqual(generated.hidden_context["contact_phone"], generated.customer.phone)
            self.assertEqual(generated.hidden_context["phone_input_attempts_required"], 0)
            self.assertEqual(generated.hidden_context["phone_input_round_3"], f"{generated.customer.phone}#")

    def test_backup_phone_plan_can_require_second_attempt(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store_path = Path(temp_dir) / "hidden_settings_history.jsonl"
            tool = HiddenSettingsTool(
                SequenceFakeClient(
                    [
                        build_candidate(
                            full_name="赵欣",
                            surname="赵",
                            phone="13876543210",
                            address="广东省佛山市顺德区大良街道南国路99号康城花园6栋2203室",
                            persona="语气温和，但希望客服快一点登记完",
                            speech_style="整体简洁，确认信息时会按流程快速回答",
                            issue="新装的空气能热水器试机时发现制热速度偏慢，想尽快预约检查",
                            desired_resolution="尽快安排人员上门确认安装情况和机器状态",
                            availability="周日下午两点后",
                            emotion="有些担心",
                            urgency="中",
                            prior_attempts="暂时还没有自行处理",
                            special_constraints="白天家里只有老人，最好周末联系",
                        )
                    ]
                ),
                build_config(
                    store_path,
                    current_call_contactable_probability=0.0,
                    phone_collection_second_attempt_probability=1.0,
                ),
            )

            generated = tool.generate_for_scenario(build_base_scenario())

            self.assertFalse(generated.hidden_context["current_call_contactable"])
            self.assertEqual(generated.hidden_context["phone_input_attempts_required"], 2)
            self.assertNotEqual(generated.hidden_context["contact_phone"], generated.customer.phone)
            self.assertTrue(str(generated.hidden_context["phone_input_round_1"]).endswith("#"))
            self.assertTrue(str(generated.hidden_context["phone_input_round_2"]).endswith("#"))
            self.assertTrue(str(generated.hidden_context["phone_input_round_3"]).endswith("#"))

    def test_invalid_phone_input_can_force_short_variant(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store_path = Path(temp_dir) / "hidden_settings_history.jsonl"
            tool = HiddenSettingsTool(
                SequenceFakeClient([]),
                build_config(
                    store_path,
                    phone_collection_invalid_short_probability=1.0,
                    phone_collection_invalid_long_probability=0.0,
                    phone_collection_invalid_pattern_probability=0.0,
                    phone_collection_invalid_digit_mismatch_probability=0.0,
                ),
            )

            invalid_input = tool._generate_invalid_phone_input(random.Random(0), "13876543210")
            digits = re.sub(r"\D", "", invalid_input)

            self.assertTrue(invalid_input.endswith("#"))
            self.assertLess(len(digits), 11)

    def test_invalid_phone_input_can_force_long_variant(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store_path = Path(temp_dir) / "hidden_settings_history.jsonl"
            tool = HiddenSettingsTool(
                SequenceFakeClient([]),
                build_config(
                    store_path,
                    phone_collection_invalid_short_probability=0.0,
                    phone_collection_invalid_long_probability=1.0,
                    phone_collection_invalid_pattern_probability=0.0,
                    phone_collection_invalid_digit_mismatch_probability=0.0,
                ),
            )

            invalid_input = tool._generate_invalid_phone_input(random.Random(0), "13876543210")
            digits = re.sub(r"\D", "", invalid_input)

            self.assertTrue(invalid_input.endswith("#"))
            self.assertGreater(len(digits), 11)

    def test_invalid_phone_input_can_force_pattern_variant(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store_path = Path(temp_dir) / "hidden_settings_history.jsonl"
            tool = HiddenSettingsTool(
                SequenceFakeClient([]),
                build_config(
                    store_path,
                    phone_collection_invalid_short_probability=0.0,
                    phone_collection_invalid_long_probability=0.0,
                    phone_collection_invalid_pattern_probability=1.0,
                    phone_collection_invalid_digit_mismatch_probability=0.0,
                ),
            )

            invalid_input = tool._generate_invalid_phone_input(random.Random(0), "13876543210")
            digits = re.sub(r"\D", "", invalid_input)

            self.assertTrue(invalid_input.endswith("#"))
            self.assertEqual(len(digits), 11)
            self.assertIsNone(re.fullmatch(r"1[3-9]\d{9}", digits))

    def test_invalid_phone_input_can_force_digit_mismatch_variant(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store_path = Path(temp_dir) / "hidden_settings_history.jsonl"
            tool = HiddenSettingsTool(
                SequenceFakeClient([]),
                build_config(
                    store_path,
                    phone_collection_invalid_short_probability=0.0,
                    phone_collection_invalid_long_probability=0.0,
                    phone_collection_invalid_pattern_probability=0.0,
                    phone_collection_invalid_digit_mismatch_probability=1.0,
                ),
            )

            valid_phone = "13876543210"
            invalid_input = tool._generate_invalid_phone_input(random.Random(0), valid_phone)
            digits = re.sub(r"\D", "", invalid_input)
            digit_difference_count = sum(
                expected != actual for expected, actual in zip(valid_phone, digits)
            )

            self.assertTrue(invalid_input.endswith("#"))
            self.assertEqual(len(digits), 11)
            self.assertIsNotNone(re.fullmatch(r"1[3-9]\d{9}", digits))
            self.assertNotEqual(digits, valid_phone)
            self.assertIn(digit_difference_count, (1, 2))

    def test_backup_phone_plan_can_require_third_attempt(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store_path = Path(temp_dir) / "hidden_settings_history.jsonl"
            tool = HiddenSettingsTool(
                SequenceFakeClient(
                    [
                        build_candidate(
                            full_name="赵欣",
                            surname="赵",
                            phone="13876543210",
                            address="广东省佛山市顺德区大良街道南国路99号康城花园6栋2203室",
                            persona="语气温和，但希望客服快一点登记完",
                            speech_style="整体简洁，确认信息时会按流程快速回答",
                            issue="新装的空气能热水器试机时发现制热速度偏慢，想尽快预约检查",
                            desired_resolution="尽快安排人员上门确认安装情况和机器状态",
                            availability="周日下午两点后",
                            emotion="有些担心",
                            urgency="中",
                            prior_attempts="暂时还没有自行处理",
                            special_constraints="白天家里只有老人，最好周末联系",
                        )
                    ]
                ),
                build_config(
                    store_path,
                    current_call_contactable_probability=0.0,
                    phone_collection_second_attempt_probability=0.0,
                    phone_collection_third_attempt_probability=1.0,
                ),
            )

            generated = tool.generate_for_scenario(build_base_scenario())

            self.assertFalse(generated.hidden_context["current_call_contactable"])
            self.assertEqual(generated.hidden_context["phone_input_attempts_required"], 3)
            self.assertNotEqual(generated.hidden_context["phone_input_round_1"], generated.hidden_context["contact_phone"] + "#")
            self.assertNotEqual(generated.hidden_context["phone_input_round_2"], generated.hidden_context["contact_phone"] + "#")
            self.assertEqual(generated.hidden_context["phone_input_round_3"], generated.hidden_context["contact_phone"] + "#")

    def test_known_address_plan_can_be_forced(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store_path = Path(temp_dir) / "hidden_settings_history.jsonl"
            tool = HiddenSettingsTool(
                SequenceFakeClient(
                    [
                        build_candidate(
                            full_name="赵欣",
                            surname="赵",
                            phone="13876543210",
                            address="广东省佛山市顺德区大良街道南国路99号康城花园6栋2203室",
                            persona="语气温和，但希望客服快一点登记完",
                            speech_style="整体简洁，确认信息时会按流程快速回答",
                            issue="新装的空气能热水器试机时发现制热速度偏慢，想尽快预约检查",
                            desired_resolution="尽快安排人员上门确认安装情况和机器状态",
                            availability="周日下午两点后",
                            emotion="有些担心",
                            urgency="中",
                            prior_attempts="暂时还没有自行处理",
                            special_constraints="白天家里只有老人，最好周末联系",
                        )
                    ]
                ),
                build_config(
                    store_path,
                    service_known_address_probability=1.0,
                    service_known_address_matches_probability=1.0,
                    address_collection_followup_probability=0.0,
                ),
            )

            generated = tool.generate_for_scenario(build_base_scenario())

            self.assertTrue(generated.hidden_context["service_known_address"])
            self.assertTrue(generated.hidden_context["service_known_address_matches_actual"])
            self.assertEqual(
                generated.hidden_context["service_known_address_value"],
                generated.customer.address,
            )

    def test_address_followup_plan_can_be_forced(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store_path = Path(temp_dir) / "hidden_settings_history.jsonl"
            tool = HiddenSettingsTool(
                SequenceFakeClient(
                    [
                        build_candidate(
                            full_name="赵欣",
                            surname="赵",
                            phone="13876543210",
                            address="广东省佛山市顺德区大良街道南国路99号康城花园6栋2203室",
                            persona="语气温和，但希望客服快一点登记完",
                            speech_style="整体简洁，确认信息时会按流程快速回答",
                            issue="新装的空气能热水器试机时发现制热速度偏慢，想尽快预约检查",
                            desired_resolution="尽快安排人员上门确认安装情况和机器状态",
                            availability="周日下午两点后",
                            emotion="有些担心",
                            urgency="中",
                            prior_attempts="暂时还没有自行处理",
                            special_constraints="白天家里只有老人，最好周末联系",
                        )
                    ]
                ),
                build_config(
                    store_path,
                    service_known_address_probability=0.0,
                    address_collection_followup_probability=1.0,
                ),
            )

            generated = tool.generate_for_scenario(build_base_scenario())

            self.assertFalse(generated.hidden_context["service_known_address"])
            self.assertGreaterEqual(len(generated.hidden_context["address_input_rounds"]), 2)
            self.assertNotEqual(
                generated.hidden_context["address_input_round_1"],
                generated.customer.address,
            )
            self.assertEqual(
                "".join(generated.hidden_context["address_input_rounds"]),
                generated.customer.address,
            )

    def test_address_followup_plan_can_force_specific_round_count_and_strategy(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store_path = Path(temp_dir) / "hidden_settings_history.jsonl"
            tool = HiddenSettingsTool(
                SequenceFakeClient(
                    [
                        build_candidate(
                            full_name="赵欣",
                            surname="赵",
                            phone="13876543210",
                            address="江苏省扬州市宝应县安宜镇宝应碧桂园3幢5层502室",
                            persona="语气温和，但希望客服快一点登记完",
                            speech_style="整体简洁，确认信息时会按流程快速回答",
                            issue="空气能热水器加热速度很慢，想尽快约人看一下",
                            desired_resolution="尽快安排人员上门检查机器情况",
                            availability="周日下午两点后",
                            emotion="有些担心",
                            urgency="中",
                            prior_attempts="暂时还没有自行处理",
                            special_constraints="最好周末联系",
                        )
                    ]
                ),
                build_config(
                    store_path,
                    service_known_address_probability=0.0,
                    address_collection_followup_probability=1.0,
                    address_segmented_reply_probability=1.0,
                    address_segment_rounds_weights={"2": 0.0, "3": 1.0, "4": 0.0},
                    address_segment_3_strategy_weights={
                        "province_city_district__locality__detail": 1.0,
                        "province_city__district_locality__detail": 0.0,
                        "province_city__district__locality_detail": 0.0,
                    },
                ),
            )

            generated = tool.generate_for_scenario(build_base_scenario())

            self.assertEqual(
                generated.hidden_context["address_input_rounds"],
                ["江苏省扬州市宝应县", "安宜镇宝应碧桂园", "3幢5层502室"],
            )

    def test_address_segmented_reply_probability_controls_segmentation(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store_path = Path(temp_dir) / "hidden_settings_history.jsonl"
            tool = HiddenSettingsTool(
                SequenceFakeClient(
                    [
                        build_candidate(
                            full_name="赵欣",
                            surname="赵",
                            phone="13876543210",
                            address="江苏省扬州市宝应县安宜镇宝应碧桂园3幢5层502室",
                            persona="语气温和，但希望客服快一点登记完",
                            speech_style="整体简洁，确认信息时会按流程快速回答",
                            issue="空气能热水器加热速度很慢，想尽快约人看一下",
                            desired_resolution="尽快安排人员上门检查机器情况",
                            availability="周日下午两点后",
                            emotion="有些担心",
                            urgency="中",
                            prior_attempts="暂时还没有自行处理",
                            special_constraints="最好周末联系",
                        )
                    ]
                ),
                build_config(
                    store_path,
                    service_known_address_probability=0.0,
                    address_collection_followup_probability=0.0,
                    address_segmented_reply_probability=1.0,
                    address_segment_rounds_weights={"2": 0.0, "3": 1.0, "4": 0.0},
                    address_segment_3_strategy_weights={
                        "province_city_district__locality__detail": 1.0,
                        "province_city__district_locality__detail": 0.0,
                        "province_city__district__locality_detail": 0.0,
                    },
                ),
            )

            generated = tool.generate_for_scenario(build_base_scenario())

            self.assertEqual(
                generated.hidden_context["address_input_rounds"],
                ["江苏省扬州市宝应县", "安宜镇宝应碧桂园", "3幢5层502室"],
            )

    def test_address_followup_plan_can_use_five_round_segmentation(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store_path = Path(temp_dir) / "hidden_settings_history.jsonl"
            tool = HiddenSettingsTool(
                SequenceFakeClient(
                    [
                        build_candidate(
                            full_name="赵欣",
                            surname="赵",
                            phone="13876543210",
                            address="江苏省扬州市宝应县安宜镇宝应碧桂园3幢5层502室",
                            persona="语气温和，但希望客服快一点登记完",
                            speech_style="整体简洁，确认信息时会按流程快速回答",
                            issue="空气能热水器加热速度很慢，想尽快约人看一下",
                            desired_resolution="尽快安排人员上门检查机器情况",
                            availability="周日下午两点后",
                            emotion="有些担心",
                            urgency="中",
                            prior_attempts="暂时还没有自行处理",
                            special_constraints="最好周末联系",
                        )
                    ]
                ),
                build_config(
                    store_path,
                    service_known_address_probability=0.0,
                    address_segmented_reply_probability=1.0,
                    address_segment_rounds_weights={"2": 0.0, "3": 0.0, "4": 0.0, "5": 1.0},
                    address_segment_5_strategy_weights={
                        "province__city__district__locality__detail": 1.0,
                    },
                ),
            )

            generated = tool.generate_for_scenario(build_base_scenario())

            self.assertEqual(
                generated.hidden_context["address_input_rounds"],
                ["江苏省", "扬州市", "宝应县", "安宜镇宝应碧桂园", "3幢5层502室"],
            )

    def test_local_hydration_generates_real_address_before_segmenting_unknown_seed_address(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store_path = Path(temp_dir) / "hidden_settings_history.jsonl"
            tool = HiddenSettingsTool(
                SequenceFakeClient([]),
                build_config(
                    store_path,
                    service_known_address_probability=1.0,
                    address_segmented_reply_probability=1.0,
                    address_segment_rounds_weights={"2": 0.0, "3": 1.0, "4": 0.0},
                    address_segment_3_strategy_weights={
                        "province_city_district__locality__detail": 1.0,
                        "province_city__district_locality__detail": 0.0,
                        "province_city__district__locality_detail": 0.0,
                    },
                ),
            )
            scenario = build_base_scenario()
            scenario.customer.address = "未知"

            with patch.object(
                tool,
                "_sample_user_generation_plan",
                return_value=UserGenerationPlan(
                    address_style="standard_residential",
                    address_instruction="生成标准小区/公寓住宅地址，通常包含小区、楼栋、单元、楼层或室号。",
                    reply_noise_enabled=False,
                    reply_noise_target="",
                    reply_noise_rounds=0,
                    reply_noise_instruction="整体正常配合客服，绝大多数轮次直接按问答题回答，不需要刻意答非所问。",
                ),
            ):
                hydrated = tool.hydrate_scenario_locally(scenario)

            self.assertNotEqual(hydrated.customer.address, "未知")
            self.assertFalse(hydrated.hidden_context["service_known_address"])
            self.assertEqual(len(hydrated.hidden_context["address_input_rounds"]), 3)
            self.assertEqual(
                "".join(hydrated.hidden_context["address_input_rounds"]),
                hydrated.customer.address,
            )

    def test_address_input_can_omit_province_and_city_suffixes(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store_path = Path(temp_dir) / "hidden_settings_history.jsonl"
            tool = HiddenSettingsTool(
                SequenceFakeClient(
                    [
                        build_candidate(
                            full_name="赵欣",
                            surname="赵",
                            phone="13876543210",
                            address="江苏省南京市鼓楼区汉中门大街288号金陵世纪花园6幢1单元1204室",
                            persona="语气温和，但希望客服快一点登记完",
                            speech_style="整体简洁，确认信息时会按流程快速回答",
                            issue="新装的空气能热水器试机时发现制热速度偏慢，想尽快预约检查",
                            desired_resolution="尽快安排人员上门确认安装情况和机器状态",
                            availability="周日下午两点后",
                            emotion="有些担心",
                            urgency="中",
                            prior_attempts="暂时还没有自行处理",
                            special_constraints="白天家里只有老人，最好周末联系",
                        )
                    ]
                ),
                build_config(
                    store_path,
                    service_known_address_probability=0.0,
                    address_collection_followup_probability=0.0,
                    address_input_omit_province_city_suffix_probability=1.0,
                ),
            )

            generated = tool.generate_for_scenario(build_base_scenario())

            self.assertEqual(
                generated.hidden_context["address_input_round_1"],
                "江苏南京鼓楼区汉中门大街288号金陵世纪花园6幢1单元1204室",
            )
            self.assertEqual(
                generated.hidden_context["address_input_round_2"],
                "江苏南京鼓楼区汉中门大街288号金陵世纪花园6幢1单元1204室",
            )

    def test_address_input_keeps_province_and_city_suffixes_when_disabled(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store_path = Path(temp_dir) / "hidden_settings_history.jsonl"
            tool = HiddenSettingsTool(
                SequenceFakeClient(
                    [
                        build_candidate(
                            full_name="赵欣",
                            surname="赵",
                            phone="13876543210",
                            address="江苏省南京市鼓楼区汉中门大街288号金陵世纪花园6幢1单元1204室",
                            persona="语气温和，但希望客服快一点登记完",
                            speech_style="整体简洁，确认信息时会按流程快速回答",
                            issue="新装的空气能热水器试机时发现制热速度偏慢，想尽快预约检查",
                            desired_resolution="尽快安排人员上门确认安装情况和机器状态",
                            availability="周日下午两点后",
                            emotion="有些担心",
                            urgency="中",
                            prior_attempts="暂时还没有自行处理",
                            special_constraints="白天家里只有老人，最好周末联系",
                        )
                    ]
                ),
                build_config(
                    store_path,
                    service_known_address_probability=0.0,
                    address_collection_followup_probability=0.0,
                    address_input_omit_province_city_suffix_probability=0.0,
                ),
            )

            generated = tool.generate_for_scenario(build_base_scenario())

            self.assertEqual(
                generated.hidden_context["address_input_round_1"],
                "江苏省南京市鼓楼区汉中门大街288号金陵世纪花园6幢1单元1204室",
            )
            self.assertEqual(
                generated.hidden_context["address_input_round_2"],
                "江苏省南京市鼓楼区汉中门大街288号金陵世纪花园6幢1单元1204室",
            )

    def test_mismatched_known_address_followup_starts_from_configured_mismatch_level(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store_path = Path(temp_dir) / "hidden_settings_history.jsonl"
            tool = HiddenSettingsTool(
                SequenceFakeClient(
                    [
                        build_candidate(
                            full_name="赵欣",
                            surname="赵",
                            phone="13876543210",
                            address="湖北省武汉市洪山区尤李湾路56号万珑小区5栋2单元502室",
                            persona="语气温和，但希望客服快一点登记完",
                            speech_style="整体简洁，确认信息时会按流程快速回答",
                            issue="新装的空气能热水器试机时发现制热速度偏慢，想尽快预约检查",
                            desired_resolution="尽快安排人员上门确认安装情况和机器状态",
                            availability="周日下午两点后",
                            emotion="有些担心",
                            urgency="中",
                            prior_attempts="暂时还没有自行处理",
                            special_constraints="白天家里只有老人，最好周末联系",
                        )
                    ]
                ),
                build_config(
                    store_path,
                    service_known_address_probability=1.0,
                    service_known_address_matches_probability=0.0,
                    address_confirmation_direct_correction_probability=0.0,
                    address_collection_followup_probability=0.0,
                    address_segmented_reply_probability=0.0,
                    address_known_mismatch_start_level_weights={
                        "province": 0.0,
                        "city": 0.0,
                        "district": 0.0,
                        "locality": 0.0,
                        "building": 0.0,
                        "unit": 0.0,
                        "floor": 0.0,
                        "room": 1.0,
                    },
                    address_known_mismatch_rewrite_end_level_weights={
                        "province": 0.0,
                        "city": 0.0,
                        "district": 0.0,
                        "locality": 0.0,
                        "building": 0.0,
                        "unit": 0.0,
                        "floor": 0.0,
                        "room": 1.0,
                    },
                ),
            )

            generated = tool.generate_for_scenario(build_base_scenario())

            self.assertTrue(generated.hidden_context["service_known_address"])
            self.assertFalse(generated.hidden_context["service_known_address_matches_actual"])
            self.assertEqual(
                generated.hidden_context["address_input_rounds"],
                ["湖北省武汉市洪山区尤李湾路56号万珑小区5栋2单元502室"],
            )
            self.assertEqual(
                generated.hidden_context["address_input_round_1"],
                "湖北省武汉市洪山区尤李湾路56号万珑小区5栋2单元502室",
            )
            self.assertEqual(
                generated.hidden_context["service_known_address_mismatch_start_level"],
                "room",
            )
            self.assertEqual(
                generated.hidden_context["service_known_address_rewrite_levels"],
                ["room"],
            )
            self.assertEqual(
                generated.hidden_context["service_known_address_rewrite_end_level"],
                "room",
            )
            self.assertEqual(
                generated.hidden_context["service_known_address_correction_value"],
                "尤李湾路56号万珑小区5栋2单元502室",
            )

    def test_stale_known_address_stays_precise(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store_path = Path(temp_dir) / "hidden_settings_history.jsonl"
            tool = HiddenSettingsTool(
                SequenceFakeClient(
                    [
                        build_candidate(
                            full_name="赵欣",
                            surname="赵",
                            phone="13876543210",
                            address="浙江省杭州市西湖区文三路159号阳光花园12幢3单元502室",
                            persona="语气温和，但希望客服快一点登记完",
                            speech_style="整体简洁，确认信息时会按流程快速回答",
                            issue="新装的空气能热水器试机时发现制热速度偏慢，想尽快预约检查",
                            desired_resolution="尽快安排人员上门确认安装情况和机器状态",
                            availability="周日下午两点后",
                            emotion="有些担心",
                            urgency="中",
                            prior_attempts="暂时还没有自行处理",
                            special_constraints="白天家里只有老人，最好周末联系",
                        )
                    ]
                ),
                build_config(
                    store_path,
                    service_known_address_probability=1.0,
                    service_known_address_matches_probability=0.0,
                ),
            )

            generated = tool.generate_for_scenario(build_base_scenario())
            stale_address = str(generated.hidden_context["service_known_address_value"])

            self.assertNotIn("附近", stale_address)
            self.assertIn("省", stale_address)
            self.assertIn("市", stale_address)
            self.assertIn("区", stale_address)

    def test_mismatched_known_address_can_embed_direct_correction_reply(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store_path = Path(temp_dir) / "hidden_settings_history.jsonl"
            tool = HiddenSettingsTool(
                SequenceFakeClient(
                    [
                        build_candidate(
                            full_name="赵欣",
                            surname="赵",
                            phone="13876543210",
                            address="浙江省杭州市西湖区文三路159号阳光花园12幢3单元502室",
                            persona="语气温和，但希望客服快一点登记完",
                            speech_style="整体简洁，确认信息时会按流程快速回答",
                            issue="新装的空气能热水器试机时发现制热速度偏慢，想尽快预约检查",
                            desired_resolution="尽快安排人员上门确认安装情况和机器状态",
                            availability="周日下午两点后",
                            emotion="有些担心",
                            urgency="中",
                            prior_attempts="暂时还没有自行处理",
                            special_constraints="白天家里只有老人，最好周末联系",
                        )
                    ]
                ),
                build_config(
                    store_path,
                    service_known_address_probability=1.0,
                    service_known_address_matches_probability=0.0,
                    address_confirmation_direct_correction_probability=1.0,
                ),
            )

            generated = tool.generate_for_scenario(build_base_scenario())
            reply = str(generated.hidden_context["address_confirmation_no_reply"])
            self.assertNotIn(reply, {"不对。", "不对，不是这个地址。", "不对，地址不对。", "不是这个地址。"})
            self.assertNotIn("正确的是", reply)
            self.assertNotIn("正确地址是", reply)
            self.assertTrue(reply.endswith("。"))

    def test_mismatched_known_address_direct_reply_can_follow_room_level(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store_path = Path(temp_dir) / "hidden_settings_history.jsonl"
            tool = HiddenSettingsTool(
                SequenceFakeClient(
                    [
                        build_candidate(
                            full_name="赵欣",
                            surname="赵",
                            phone="13876543210",
                            address="广东省广州市天河区天府路12号3栋502室",
                            persona="语气温和，但希望客服快一点登记完",
                            speech_style="整体简洁，确认信息时会按流程快速回答",
                            issue="新装的空气能热水器试机时发现制热速度偏慢，想尽快预约检查",
                            desired_resolution="尽快安排人员上门确认安装情况和机器状态",
                            availability="周日下午两点后",
                            emotion="有些担心",
                            urgency="中",
                            prior_attempts="暂时还没有自行处理",
                            special_constraints="白天家里只有老人，最好周末联系",
                        )
                    ]
                ),
                build_config(
                    store_path,
                    service_known_address_probability=1.0,
                    service_known_address_matches_probability=0.0,
                    address_confirmation_direct_correction_probability=1.0,
                    address_segmented_reply_probability=0.0,
                    address_known_mismatch_start_level_weights={
                        "province": 0.0,
                        "city": 0.0,
                        "district": 0.0,
                        "locality": 0.0,
                        "building": 0.0,
                        "unit": 0.0,
                        "floor": 0.0,
                        "room": 1.0,
                    },
                    address_known_mismatch_rewrite_end_level_weights={
                        "province": 0.0,
                        "city": 0.0,
                        "district": 0.0,
                        "locality": 0.0,
                        "building": 0.0,
                        "unit": 0.0,
                        "floor": 0.0,
                        "room": 1.0,
                    },
                ),
            )

            generated = tool.generate_for_scenario(build_base_scenario())

            self.assertIn("天府路12号3栋502室", generated.hidden_context["address_confirmation_no_reply"])
            self.assertEqual(
                generated.hidden_context["service_known_address_correction_value"],
                "天府路12号3栋502室",
            )
            self.assertEqual(generated.hidden_context["service_known_address_rewrite_levels"], ["room"])

    def test_mismatched_known_address_can_rewrite_contiguous_suffix_levels(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store_path = Path(temp_dir) / "hidden_settings_history.jsonl"
            tool = HiddenSettingsTool(
                SequenceFakeClient(
                    [
                        build_candidate(
                            full_name="赵欣",
                            surname="赵",
                            phone="13876543210",
                            address="浙江省杭州市西湖区文三路159号阳光花园12幢3单元502室",
                            persona="语气温和，但希望客服快一点登记完",
                            speech_style="整体简洁，确认信息时会按流程快速回答",
                            issue="新装的空气能热水器试机时发现制热速度偏慢，想尽快预约检查",
                            desired_resolution="尽快安排人员上门确认安装情况和机器状态",
                            availability="周日下午两点后",
                            emotion="有些担心",
                            urgency="中",
                            prior_attempts="暂时还没有自行处理",
                            special_constraints="白天家里只有老人，最好周末联系",
                        )
                    ]
                ),
                build_config(
                    store_path,
                    service_known_address_probability=1.0,
                    service_known_address_matches_probability=0.0,
                    address_confirmation_direct_correction_probability=1.0,
                    address_segmented_reply_probability=0.0,
                    address_known_mismatch_start_level_weights={
                        "province": 0.0,
                        "city": 0.0,
                        "district": 0.0,
                        "locality": 0.0,
                        "building": 1.0,
                        "unit": 0.0,
                        "floor": 0.0,
                        "room": 0.0,
                    },
                    address_known_mismatch_rewrite_end_level_weights={
                        "province": 0.0,
                        "city": 0.0,
                        "district": 0.0,
                        "locality": 0.0,
                        "building": 0.0,
                        "unit": 0.0,
                        "floor": 0.0,
                        "room": 1.0,
                    },
                ),
            )

            generated = tool.generate_for_scenario(build_base_scenario())

            self.assertEqual(
                generated.hidden_context["service_known_address_mismatch_start_level"],
                "building",
            )
            self.assertEqual(
                generated.hidden_context["service_known_address_rewrite_levels"],
                ["building", "unit", "room"],
            )
            self.assertEqual(
                generated.hidden_context["service_known_address_rewrite_end_level"],
                "room",
            )
            self.assertEqual(
                generated.hidden_context["service_known_address_correction_value"],
                "文三路159号阳光花园12幢3单元502室",
            )
            self.assertEqual(
                generated.hidden_context["address_input_rounds"],
                ["浙江省杭州市西湖区文三路159号阳光花园12幢3单元502室"],
            )

    def test_non_phone_address_reply_noise_rounds_are_capped_at_two(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store_path = Path(temp_dir) / "hidden_settings_history.jsonl"
            tool = HiddenSettingsTool(
                SequenceFakeClient(
                    [
                        build_candidate(
                            full_name="王建业",
                            surname="王",
                            phone="13876543210",
                            address="浙江省杭州市西湖区文三路159号阳光花园12幢3单元502室",
                            persona="说话直接，配合度正常。",
                            speech_style="整体简洁。",
                            issue="新买的空气能热水机需要安排安装。",
                            desired_resolution="尽快安排师傅上门安装。",
                            availability="周日下午两点后",
                            emotion="平静",
                            urgency="中",
                            prior_attempts="还没有处理过",
                            special_constraints="白天家里有人",
                        )
                    ]
                ),
                build_config(
                    store_path,
                    user_reply_off_topic_probability=1.0,
                    user_reply_off_topic_target_weights={
                        "opening_confirmation": 0.0,
                        "issue_description": 0.0,
                        "surname_collection": 1.0,
                        "phone_contact_confirmation": 0.0,
                        "phone_keypad_input": 0.0,
                        "phone_confirmation": 0.0,
                        "address_collection": 0.0,
                        "address_confirmation": 0.0,
                        "product_arrival_confirmation": 0.0,
                        "product_model_collection": 0.0,
                        "closing_acknowledgement": 0.0,
                    },
                    user_reply_off_topic_rounds_weights={"3": 1.0},
                ),
            )

            generated = tool.generate_for_scenario(build_installation_scenario())

            self.assertEqual(generated.hidden_context["user_reply_noise_target"], "surname_collection")
            self.assertEqual(generated.hidden_context["user_reply_noise_rounds"], 2)
            self.assertIn("前 2 次被问姓氏", generated.hidden_context["user_reply_noise_instruction"])

    def test_district_level_known_address_mismatch_rewrites_full_suffix(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store_path = Path(temp_dir) / "hidden_settings_history.jsonl"
            tool = HiddenSettingsTool(
                SequenceFakeClient(
                    [
                        build_candidate(
                            full_name="赵欣",
                            surname="赵",
                            phone="13876543210",
                            address="广东省佛山市南海区桂城街道东信花园五期2栋3单元601室",
                            persona="语气温和，但希望客服快一点登记完",
                            speech_style="整体简洁，确认信息时会按流程快速回答",
                            issue="新装的空气能热水器试机时发现制热速度偏慢，想尽快预约检查",
                            desired_resolution="尽快安排人员上门确认安装情况和机器状态",
                            availability="周日下午两点后",
                            emotion="有些担心",
                            urgency="中",
                            prior_attempts="暂时还没有自行处理",
                            special_constraints="白天家里只有老人，最好周末联系",
                        )
                    ]
                ),
                build_config(
                    store_path,
                    service_known_address_probability=1.0,
                    service_known_address_matches_probability=0.0,
                    address_confirmation_direct_correction_probability=1.0,
                    address_known_mismatch_start_level_weights={
                        "province": 0.0,
                        "city": 0.0,
                        "district": 1.0,
                        "locality": 0.0,
                        "building": 0.0,
                        "unit": 0.0,
                        "floor": 0.0,
                        "room": 0.0,
                    },
                    address_known_mismatch_rewrite_end_level_weights={
                        "province": 0.0,
                        "city": 0.0,
                        "district": 1.0,
                        "locality": 0.0,
                        "building": 0.0,
                        "unit": 0.0,
                        "floor": 0.0,
                        "room": 0.0,
                    },
                ),
            )

            generated = tool.generate_for_scenario(build_installation_scenario())

            self.assertEqual(generated.hidden_context["service_known_address_mismatch_start_level"], "district")
            self.assertEqual(
                generated.hidden_context["service_known_address_rewrite_levels"],
                ["district", "locality", "building", "unit", "room"],
            )
            self.assertEqual(
                generated.hidden_context["service_known_address_correction_value"],
                "南海区桂城街道东信花园五期2栋3单元601室",
            )
            self.assertEqual(
                "".join(generated.hidden_context["address_input_rounds"]),
                "广东省佛山市南海区桂城街道东信花园五期2栋3单元601室",
            )
            self.assertNotIn("东信花园五期2栋3单元601室", generated.hidden_context["service_known_address_value"])

    def test_locality_level_known_address_mismatch_rewrites_full_suffix(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store_path = Path(temp_dir) / "hidden_settings_history.jsonl"
            tool = HiddenSettingsTool(
                SequenceFakeClient(
                    [
                        build_candidate(
                            full_name="赵欣",
                            surname="赵",
                            phone="13876543210",
                            address="甘肃省兰州市城关区五泉街道福寿小区8号楼2单元1202室",
                            persona="语气温和，但希望客服快一点登记完",
                            speech_style="整体简洁，确认信息时会按流程快速回答",
                            issue="空气能热水器制热太慢，想尽快安排检查",
                            desired_resolution="尽快安排人员上门确认机器情况",
                            availability="周日下午两点后",
                            emotion="有些担心",
                            urgency="中",
                            prior_attempts="暂时还没有自行处理",
                            special_constraints="白天家里只有老人，最好周末联系",
                        )
                    ]
                ),
                build_config(
                    store_path,
                    service_known_address_probability=1.0,
                    service_known_address_matches_probability=0.0,
                    address_confirmation_direct_correction_probability=1.0,
                    address_known_mismatch_start_level_weights={
                        "province": 0.0,
                        "city": 0.0,
                        "district": 0.0,
                        "locality": 1.0,
                        "building": 0.0,
                        "unit": 0.0,
                        "floor": 0.0,
                        "room": 0.0,
                    },
                    address_known_mismatch_rewrite_end_level_weights={
                        "province": 0.0,
                        "city": 0.0,
                        "district": 0.0,
                        "locality": 1.0,
                        "building": 0.0,
                        "unit": 0.0,
                        "floor": 0.0,
                        "room": 0.0,
                    },
                ),
            )

            generated = tool.generate_for_scenario(build_installation_scenario())

            self.assertEqual(generated.hidden_context["service_known_address_mismatch_start_level"], "locality")
            self.assertEqual(
                generated.hidden_context["service_known_address_rewrite_levels"],
                ["locality", "building", "unit", "room"],
            )
            self.assertEqual(
                generated.hidden_context["service_known_address_correction_value"],
                "五泉街道福寿小区8号楼2单元1202室",
            )
            self.assertEqual(
                "".join(generated.hidden_context["address_input_rounds"]),
                "甘肃省兰州市城关区五泉街道福寿小区8号楼2单元1202室",
            )
            self.assertNotIn("福寿小区8号楼2单元1202室", generated.hidden_context["service_known_address_value"])

    def test_region_option_pools_cover_all_mainland_province_level_regions(self):
        expected_non_municipal_regions = {
            "河北省",
            "山西省",
            "辽宁省",
            "吉林省",
            "黑龙江省",
            "江苏省",
            "浙江省",
            "安徽省",
            "福建省",
            "江西省",
            "山东省",
            "河南省",
            "湖北省",
            "湖南省",
            "广东省",
            "海南省",
            "四川省",
            "贵州省",
            "云南省",
            "陕西省",
            "甘肃省",
            "青海省",
            "内蒙古",
            "广西",
            "西藏",
            "宁夏",
            "新疆",
        }
        expected_municipalities = {"北京市", "上海市", "天津市", "重庆市"}

        self.assertEqual(set(COHERENT_REGION_CITY_DISTRICT_MAP.keys()), expected_non_municipal_regions)
        self.assertEqual(set(COHERENT_MUNICIPALITY_CITY_DISTRICT_MAP.keys()), expected_municipalities)
        self.assertGreaterEqual(len(COHERENT_REGION_OPTIONS), len(expected_non_municipal_regions) * 2)
        self.assertEqual(len(COHERENT_MUNICIPALITY_OPTIONS), len(expected_municipalities))
        self.assertGreaterEqual(len(COHERENT_ADDRESS_ADMIN_OPTIONS), 150)

        for province, cities in COHERENT_REGION_CITY_DISTRICT_MAP.items():
            self.assertGreaterEqual(len(cities), 2, province)
            for city, districts in cities.items():
                self.assertGreaterEqual(len(districts), 3, city)

    def test_generate_local_customer_address_uses_real_admin_division_prefix(self):
        valid_prefixes = {
            f"{option['province']}{option['city']}{option['district']}{option['town']}"
            for option in COHERENT_ADDRESS_ADMIN_OPTIONS
        }

        for seed in range(30):
            address = generate_local_customer_address(f"seed-{seed}")
            self.assertTrue(any(address.startswith(prefix) for prefix in valid_prefixes), address)

    def test_generate_local_customer_address_uses_multiple_detail_templates(self):
        detail_styles: set[str] = set()

        for seed in range(60):
            address = generate_local_customer_address(f"detail-seed-{seed}")
            if "单元" in address and "幢" in address:
                detail_styles.add("building-unit-room")
            elif "号楼" in address and "层" in address:
                detail_styles.add("building-floor-room")
            elif "号楼" in address and "单元" in address:
                detail_styles.add("building-unit-no-room-suffix")
            elif "座" in address and "楼" in address:
                detail_styles.add("seat-floor-room")
            elif "座" in address and "室" in address:
                detail_styles.add("seat-room")
            elif "栋" in address and "单元" in address and "楼" in address:
                detail_styles.add("building-unit-floor-room")
            elif "栋" in address and "室" in address:
                detail_styles.add("building-room")

        self.assertGreaterEqual(len(detail_styles), 3)

    def test_generate_region_stale_address_keeps_valid_province_city_pairing(self):
        stale_address = HiddenSettingsTool._generate_region_stale_address(
            "江苏省苏州市工业园区星湖街888号星辰花园8栋302室",
            random.Random(7),
        )
        components = extract_address_components(stale_address)
        valid_pairs = {(option["province"], option["city"]) for option in COHERENT_REGION_OPTIONS}

        self.assertIn((components.province, components.city), valid_pairs)
        self.assertNotEqual(stale_address, "江苏省苏州市工业园区星湖街888号星辰花园8栋302室")

    def test_mismatched_known_address_can_only_deny_without_correction(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store_path = Path(temp_dir) / "hidden_settings_history.jsonl"
            tool = HiddenSettingsTool(
                SequenceFakeClient(
                    [
                        build_candidate(
                            full_name="赵欣",
                            surname="赵",
                            phone="13876543210",
                            address="浙江省杭州市西湖区文三路159号阳光花园12幢3单元502室",
                            persona="语气温和，但希望客服快一点登记完",
                            speech_style="整体简洁，确认信息时会按流程快速回答",
                            issue="新装的空气能热水器试机时发现制热速度偏慢，想尽快预约检查",
                            desired_resolution="尽快安排人员上门确认安装情况和机器状态",
                            availability="周日下午两点后",
                            emotion="有些担心",
                            urgency="中",
                            prior_attempts="暂时还没有自行处理",
                            special_constraints="白天家里只有老人，最好周末联系",
                        )
                    ]
                ),
                build_config(
                    store_path,
                    service_known_address_probability=1.0,
                    service_known_address_matches_probability=0.0,
                    address_confirmation_direct_correction_probability=0.0,
                ),
            )

            generated = tool.generate_for_scenario(build_base_scenario())
            self.assertNotIn("正确地址是", generated.hidden_context["address_confirmation_no_reply"])

    def test_pick_contact_phone_owner_spoken_label_varies_spouse_title_by_name_hint(self):
        female_label = HiddenSettingsTool._pick_contact_phone_owner_spoken_label(
            "爱人",
            "李敏",
        )
        male_label = HiddenSettingsTool._pick_contact_phone_owner_spoken_label(
            "爱人",
            "刘强",
        )

        self.assertIn(female_label, {"我老公", "我丈夫", "我爱人"})
        self.assertIn(male_label, {"我媳妇", "我老婆", "我爱人"})

    def test_pick_contact_phone_owner_spoken_label_prefers_explicit_gender(self):
        female_label = HiddenSettingsTool._pick_contact_phone_owner_spoken_label(
            "爱人",
            "赵晨",
            "女",
        )
        male_label = HiddenSettingsTool._pick_contact_phone_owner_spoken_label(
            "爱人",
            "赵晨",
            "男",
        )

        self.assertIn(female_label, {"我老公", "我丈夫", "我爱人"})
        self.assertIn(male_label, {"我媳妇", "我老婆", "我爱人"})

    def test_generate_address_correction_can_return_room_only_for_fine_grained_mismatch(self):
        correction = HiddenSettingsTool._generate_address_correction(
            actual_address="河南省郑州市金水区北环路天伦雅苑15号楼2单元503室",
            stale_address="河南省郑州市金水区北环路天伦雅苑15号楼2单元505室",
            rng=random.Random(1),
        )

        self.assertEqual(correction, "503室")

    def test_normalize_known_address_correction_value_expands_room_only_to_locality_anchor(self):
        correction = HiddenSettingsTool._normalize_known_address_correction_value(
            actual_address="河南省郑州市金水区北环路天伦雅苑15号楼2单元503室",
            correction_value="503室",
            rewrite_levels=["room"],
        )

        self.assertEqual(correction, "北环路天伦雅苑15号楼2单元503室")

    def test_generate_address_correction_can_return_full_address_for_cross_region_mismatch(self):
        correction = HiddenSettingsTool._generate_address_correction(
            actual_address="山东省青岛市市南区香港东路银海花园3号楼1203室",
            stale_address="河南省郑州市金水区北环路天伦雅苑15号楼2单元505室",
            rng=random.Random(1),
        )

        self.assertEqual(correction, "山东省青岛市市南区香港东路银海花园3号楼1203室")

    def test_installation_hidden_context_infers_product_arrived(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store_path = Path(temp_dir) / "hidden_settings_history.jsonl"
            tool = HiddenSettingsTool(
                SequenceFakeClient(
                    [
                        {
                            "customer": {
                                "full_name": "赵欣",
                                "surname": "赵",
                                "phone": "13876543210",
                                "address": "广东省佛山市顺德区大良街道南国路99号康城花园6栋2203室",
                                "persona": "说话随意一点，希望安装尽快安排",
                                "speech_style": "说话随意，句子偏短，偶尔会省略主语",
                            },
                            "request": {
                                "request_type": "installation",
                                "issue": "机器已经送到家了，还没拆箱，想装一下",
                                "desired_resolution": "先登记，等后面安排安装",
                                "availability": "周日下午两点后",
                            },
                            "hidden_context": {
                                "emotion": "正常",
                                "urgency": "中",
                                "prior_attempts": "还没自己处理",
                                "special_constraints": "白天家里有人",
                            },
                        }
                    ]
                ),
                build_config(store_path),
            )

            generated = tool.generate_for_scenario(build_installation_scenario())

            self.assertEqual(generated.request.request_type, "installation")
            self.assertEqual(generated.hidden_context["product_arrived"], "yes")


if __name__ == "__main__":
    unittest.main(verbosity=2)
    def test_normalize_generated_payload_can_allow_two_fault_symptoms_when_probability_enabled(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store_path = Path(temp_dir) / "hidden_settings_history.jsonl"
            tool = HiddenSettingsTool(
                SequenceFakeClient([]),
                build_config(store_path, hidden_settings_multi_fault_probability=1.0),
            )

            normalized = tool._normalize_generated_payload(
                build_candidate(
                    full_name="李敏",
                    surname="李",
                    phone="13912345678",
                    address="江苏省苏州市吴中区金枫路金色家园88号3幢1201室",
                    persona="说话直接，比较关注老人洗澡热水是否稳定",
                    speech_style="说话简短，偶尔会直接打断补充重点",
                    issue="设备显示 E4 故障码，热水供应极不稳定。",
                    desired_resolution="希望尽快安排师傅上门检查温控和主机运行情况",
                    availability="周五晚上七点后或者周日白天",
                    emotion="有些着急但还算克制",
                    urgency="中高",
                    prior_attempts="重启过一次机器，没有改善",
                    special_constraints="家里有老人，晚上更需要稳定热水",
                ),
                "fault",
                scenario_id="midea_heat_pump_fault_test_001",
            )

            self.assertEqual(normalized["request"]["issue"], "设备显示 E4 故障码，热水供应极不稳定。")
