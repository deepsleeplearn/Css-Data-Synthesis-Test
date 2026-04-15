from __future__ import annotations

import unittest
from pathlib import Path

from multi_agent_data_synthesis.config import AppConfig
from multi_agent_data_synthesis.orchestrator import DialogueOrchestrator
from multi_agent_data_synthesis.schemas import (
    SERVICE_SPEAKER,
    USER_SPEAKER,
    Scenario,
)


def build_config() -> AppConfig:
    root = Path("/tmp/multi-agent-data-synthesis-tests")
    return AppConfig(
        openai_base_url="https://example.com/v1/chat/completions",
        openai_api_key="test-api-key",
        user="test-user",
        default_model="gpt-4o",
        user_agent_model="gpt-4o",
        service_agent_model="gpt-4o",
        default_temperature=0.7,
        service_ok_prefix_probability=0.0,
        second_round_include_issue_probability=0.5,
        max_rounds=4,
        max_concurrency=2,
        request_timeout=30,
        data_dir=root,
        output_dir=root,
        hidden_settings_store=root / "hidden_settings_history.jsonl",
        product_routing_enabled=True,
        product_routing_apply_probability=1.0,
        hidden_settings_similarity_threshold=0.82,
        hidden_settings_duplicate_threshold=0.5,
        hidden_settings_max_attempts=3,
        hidden_settings_multi_fault_probability=0.1,
        installation_request_probability=0.5,
        current_call_contactable_probability=0.75,
        phone_collection_second_attempt_probability=0.35,
        phone_collection_third_attempt_probability=0.2,
        phone_collection_invalid_short_probability=0.34,
        phone_collection_invalid_long_probability=0.33,
        phone_collection_invalid_pattern_probability=0.33,
        phone_collection_invalid_digit_mismatch_probability=0.33,
        service_known_address_probability=0.2,
        service_known_address_matches_probability=0.8,
        address_collection_followup_probability=0.35,
        address_segmented_reply_probability=0.35,
        address_segment_rounds_weights={"2": 0.45, "3": 0.35, "4": 0.20},
        address_segment_2_strategy_weights={
            "province_city_district_locality__detail": 0.6,
            "province_city_district__locality_detail": 0.4,
        },
        address_segment_3_strategy_weights={
            "province_city_district__locality__detail": 0.5454545454545454,
            "province_city__district_locality__detail": 0.2727272727272727,
            "province_city__district__locality_detail": 0.18181818181818182,
        },
        address_segment_4_strategy_weights={
            "province_city__district__locality__detail": 1.0,
        },
        address_input_omit_province_city_suffix_probability=0.0,
        address_confirmation_direct_correction_probability=0.5,
        user_reply_off_topic_probability=0.18,
        user_reply_off_topic_target_weights={
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
        },
        user_reply_off_topic_rounds_weights={"1": 0.85, "2": 0.12, "3": 0.03},
        user_address_nonstandard_probability=0.28,
        user_address_nonstandard_style_weights={
            "house_number_only": 0.45,
            "rural_group_number": 0.25,
            "landmark_poi": 0.30,
        },
        address_known_mismatch_start_level_weights={
            "province": 0.05,
            "city": 0.10,
            "district": 0.15,
            "locality": 0.25,
            "building": 0.15,
            "unit": 0.10,
            "floor": 0.05,
            "room": 0.15,
        },
        address_known_mismatch_rewrite_end_level_weights={
            "province": 0.05,
            "city": 0.08,
            "district": 0.10,
            "locality": 0.14,
            "building": 0.16,
            "unit": 0.16,
            "floor": 0.11,
            "room": 0.20,
        },
    )


def build_scenario() -> Scenario:
    return Scenario.from_dict(
        {
            "scenario_id": "fault_case_001",
            "product": {
                "brand": "美的",
                "category": "空气能热水器",
                "model": "KF-01",
                "purchase_channel": "京东",
            },
            "customer": {
                "full_name": "张三",
                "surname": "张",
                "phone": "13800000001",
                "address": "上海市浦东新区测试路1号",
                "persona": "普通用户",
                "speech_style": "简洁",
            },
            "request": {
                "request_type": "fault",
                "issue": "启动后显示E4，热水不出来",
                "desired_resolution": "尽快安排维修",
                "availability": "明天下午",
            },
            "required_slots": ["issue_description", "request_type"],
            "max_turns": 2,
        }
    )


class StubUserAgent:
    async def respond_async(self, *, scenario: Scenario, transcript: list, round_index: int) -> dict:
        if round_index == 1:
            return {
                "reply": "对，是的，我家空气能热水器启动后显示E4故障码，热水不出来。",
                "call_complete": False,
            }
        return {"reply": "好的。", "call_complete": True}


class StubServiceAgent:
    def build_initial_user_utterance(self, scenario: Scenario) -> str:
        return "美的空气能热水器需要维修"

    def respond(self, *, scenario: Scenario, transcript: list, collected_slots: dict, runtime_state) -> dict:
        service_turns = [turn for turn in transcript if turn.speaker == SERVICE_SPEAKER]
        if not service_turns:
            return {
                "reply": "您好，很高兴为您服务，请问是美的空气能热水器需要维修吗？",
                "slot_updates": {},
                "is_ready_to_close": False,
                "used_model_intent_inference": False,
            }
        return {
            "reply": "请您在拨号盘上输入您的联系方式，并以#号键结束。",
            "slot_updates": {"phone_contactable": "no"},
            "is_ready_to_close": False,
            "used_model_intent_inference": True,
        }


class DialogueOrchestratorTests(unittest.IsolatedAsyncioTestCase):
    async def test_generate_dialogue_starts_with_user_and_exports_chinese_labels(self):
        orchestrator = DialogueOrchestrator(build_config())
        orchestrator.user_agent = StubUserAgent()
        sample = await orchestrator.generate_dialogue_async(build_scenario())

        self.assertGreaterEqual(len(sample.transcript), 3)
        self.assertEqual(sample.transcript[0].speaker, USER_SPEAKER)
        self.assertEqual(sample.transcript[0].text, "美的空气能热水器需要维修")
        self.assertEqual(sample.transcript[1].speaker, SERVICE_SPEAKER)
        self.assertEqual(sample.transcript[1].text, "您好，很高兴为您服务，请问是美的空气能热水器需要维修吗？")

        exported = sample.to_dict()
        self.assertEqual(exported["transcript"][0]["speaker"], "用户")
        self.assertEqual(exported["transcript"][1]["speaker"], "客服")
        self.assertEqual(exported["transcript"][0]["text"], "美的空气能热水器需要维修")
        self.assertIn("客服:", exported["dialogue_text"])
        self.assertIn("用户:", exported["dialogue_text"])

    async def test_generate_dialogue_marks_service_round_when_model_intent_is_used(self):
        orchestrator = DialogueOrchestrator(build_config())
        orchestrator.user_agent = StubUserAgent()
        orchestrator.service_agent = StubServiceAgent()

        sample = await orchestrator.generate_dialogue_async(build_scenario())
        exported = sample.to_dict()

        self.assertEqual(exported["transcript"][3]["round_label"], "2*")
        self.assertTrue(exported["transcript"][3]["model_intent_inference_used"])
        self.assertIn("[2*] 客服:", exported["dialogue_text"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
