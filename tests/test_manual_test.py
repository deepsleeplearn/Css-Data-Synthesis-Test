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


if __name__ == "__main__":
    unittest.main(verbosity=2)
