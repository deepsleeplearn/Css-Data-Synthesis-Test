from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from multi_agent_data_synthesis.manual_test import (
    load_manual_test_scenario,
    run_manual_test_session,
)
from multi_agent_data_synthesis.schemas import Scenario
from multi_agent_data_synthesis.service_policy import ServicePolicyResult


def build_scenario_payload(scenario_id: str) -> dict:
    return {
        "scenario_id": scenario_id,
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
        "call_start_time": "10:30:00",
        "hidden_context": {
            "current_call_contactable": True,
            "service_known_address": False,
            "service_known_address_value": "",
            "service_known_address_matches_actual": False,
        },
        "required_slots": [
            "issue_description",
            "surname",
            "phone",
            "address",
            "request_type",
        ],
        "max_turns": 6,
        "tags": ["fault"],
    }


class ManualTestModuleTests(unittest.TestCase):
    def test_load_manual_test_scenario_prefers_scenario_id(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            scenario_file = Path(temp_dir) / "scenarios.json"
            scenario_file.write_text(
                json.dumps(
                    [
                        build_scenario_payload("case_001"),
                        build_scenario_payload("case_002"),
                    ],
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )

            scenario = load_manual_test_scenario(
                scenario_file,
                scenario_id="case_002",
                scenario_index=0,
            )

            self.assertEqual(scenario.scenario_id, "case_002")

    def test_run_manual_test_session_writes_json_report(self):
        scenario = Scenario.from_dict(build_scenario_payload("manual_case_001"))
        prompts: list[str] = []
        outputs: list[str] = []
        replies = iter(["美的空气能热水器需要维修", "/quit"])

        def fake_input(prompt: str) -> str:
            prompts.append(prompt)
            return next(replies)

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "manual_test_result.json"
            payload = run_manual_test_session(
                scenario,
                output_path=output_path,
                max_rounds=4,
                input_func=fake_input,
                print_func=outputs.append,
            )

            self.assertEqual(payload["status"], "aborted")
            self.assertEqual(payload["aborted_reason"], "user_exit")
            self.assertTrue(output_path.exists())
            saved = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(saved["scenario_id"], "manual_case_001")
            self.assertEqual(saved["status"], "aborted")
            self.assertEqual(len(saved["transcript"]), 2)
            self.assertEqual(saved["transcript"][0]["speaker"], "用户")
            self.assertEqual(saved["transcript"][1]["speaker"], "客服")
            self.assertEqual(len(saved["service_trace"]), 1)
            self.assertGreaterEqual(len(prompts), 2)
            self.assertTrue(any("测试结果已写入" in line for line in outputs))

    def test_run_manual_test_session_marks_service_turn_when_model_intent_is_used(self):
        class StubPolicy:
            def __init__(self):
                self.last_used_model_intent_inference = False
                self.calls = 0

            def respond(self, *, scenario, transcript, collected_slots, runtime_state):
                self.calls += 1
                self.last_used_model_intent_inference = True
                return ServicePolicyResult(
                    reply="请您在拨号盘上输入您的联系方式，并以#号键结束。",
                    slot_updates={"phone_contactable": "no"},
                    is_ready_to_close=False,
                )

        scenario = Scenario.from_dict(build_scenario_payload("manual_case_002"))
        outputs: list[str] = []
        replies = iter(["可能我那时有事，你联系我儿子吧", "/quit"])

        def fake_input(prompt: str) -> str:
            return next(replies)

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "manual_test_result.json"
            payload = run_manual_test_session(
                scenario,
                output_path=output_path,
                max_rounds=4,
                policy=StubPolicy(),
                input_func=fake_input,
                print_func=outputs.append,
            )

            self.assertEqual(payload["service_trace"][0]["service_round_label"], "1*")
            self.assertTrue(payload["service_trace"][0]["used_model_intent_inference"])
            self.assertTrue(any("[1*] 客服:" in line for line in outputs))

    def test_run_manual_test_session_can_skip_file_write(self):
        scenario = Scenario.from_dict(build_scenario_payload("manual_case_003"))
        outputs: list[str] = []
        replies = iter(["美的空气能热水器需要维修", "/quit"])

        def fake_input(prompt: str) -> str:
            return next(replies)

        payload = run_manual_test_session(
            scenario,
            output_path=None,
            max_rounds=4,
            input_func=fake_input,
            print_func=outputs.append,
        )

        self.assertEqual(payload["status"], "aborted")
        self.assertTrue(any("输出文件: 未启用" in line for line in outputs))
        self.assertTrue(any("测试结果未写入文件" in line for line in outputs))


if __name__ == "__main__":
    unittest.main(verbosity=2)
