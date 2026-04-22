from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import css_data_synthesis_test.manual_test as manual_test_module
from css_data_synthesis_test.manual_test import (
    _manual_command_token,
    _sanitize_manual_user_text,
    load_manual_test_scenario,
    run_manual_test_session,
)
from css_data_synthesis_test.schemas import Scenario
from css_data_synthesis_test.service_policy import ServiceDialoguePolicy, ServicePolicyResult


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
    def test_sanitize_manual_user_text_removes_abnormal_unicode_whitespace(self):
        sanitized = _sanitize_manual_user_text("  阳光锦城\u30003\u00a0号楼\u200b2 单元\r\n402  ")

        self.assertEqual(sanitized, "阳光锦城 3 号楼2 单元 402")

    def test_manual_command_token_tolerates_whitespace_noise(self):
        self.assertEqual(_manual_command_token(" \u3000/ state \n"), "/state")

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

            self.assertEqual(payload["service_trace"][0]["user_round_label"], "1")
            self.assertEqual(payload["service_trace"][0]["service_round_label"], "1*")
            self.assertTrue(payload["service_trace"][0]["used_model_intent_inference"])
            self.assertEqual(payload["transcript"][1]["round_label"], "1*")
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

    def test_run_manual_test_session_can_print_address_state_when_enabled(self):
        class StubPolicy:
            def __init__(self):
                self.last_used_model_intent_inference = False

            def respond(self, *, scenario, transcript, collected_slots, runtime_state):
                runtime_state.awaiting_full_address = True
                runtime_state.partial_address_candidate = "江苏省扬州市宝应县安宜镇"
                runtime_state.last_address_followup_prompt = "请问具体是在哪个小区或村呢？尽量详细到门牌号。"
                return ServicePolicyResult(
                    reply="请问具体是在哪个小区或村呢？尽量详细到门牌号。",
                    slot_updates={},
                    is_ready_to_close=False,
                )

        scenario = Scenario.from_dict(build_scenario_payload("manual_case_004"))
        outputs: list[str] = []
        replies = iter(["江苏省扬州市宝应县安宜镇", "/quit"])

        def fake_input(prompt: str) -> str:
            return next(replies)

        run_manual_test_session(
            scenario,
            output_path=None,
            max_rounds=4,
            policy=StubPolicy(),
            show_address_state=True,
            input_func=fake_input,
            print_func=outputs.append,
        )

        self.assertTrue(any(line.startswith("地址状态: ") for line in outputs))
        self.assertTrue(any("安宜镇" in line for line in outputs if line.startswith("地址状态: ")))
        self.assertTrue(any('"actual_address"' in line for line in outputs if line.startswith("地址状态: ")))
        self.assertTrue(any('"missing_required_precision"' in line for line in outputs if line.startswith("地址状态: ")))

    def test_run_manual_test_session_preserves_normal_text_after_sanitizing_input(self):
        class StubPolicy:
            def __init__(self):
                self.last_used_model_intent_inference = False

            def respond(self, *, scenario, transcript, collected_slots, runtime_state):
                return ServicePolicyResult(
                    reply="好的，请继续。",
                    slot_updates={},
                    is_ready_to_close=False,
                )

        scenario = Scenario.from_dict(build_scenario_payload("manual_case_005"))
        replies = iter(["  阳光锦城\u30003\u00a0号楼\u200b2 单元\r\n402  ", "/quit"])

        def fake_input(prompt: str) -> str:
            return next(replies)

        payload = run_manual_test_session(
            scenario,
            output_path=None,
            max_rounds=4,
            policy=StubPolicy(),
            input_func=fake_input,
            print_func=lambda _: None,
        )

        self.assertEqual(payload["service_trace"][0]["user_text"], "阳光锦城 3 号楼2 单元 402")

    def test_run_manual_test_session_can_print_final_slots_and_keep_product_routing_result(self):
        class StubPolicy:
            def __init__(self):
                self.last_used_model_intent_inference = False

            def respond(self, *, scenario, transcript, collected_slots, runtime_state):
                return ServicePolicyResult(
                    reply="好的，请继续。",
                    slot_updates={"product_routing_result": "楼宇 + 可直接确认机型"},
                    is_ready_to_close=False,
                )

        scenario = Scenario.from_dict(build_scenario_payload("manual_case_006"))
        outputs: list[str] = []
        replies = iter(["美的空气能热水器需要维修", "/quit"])

        def fake_input(prompt: str) -> str:
            return next(replies)

        payload = run_manual_test_session(
            scenario,
            output_path=None,
            max_rounds=4,
            policy=StubPolicy(),
            show_final_slots=True,
            input_func=fake_input,
            print_func=outputs.append,
        )

        self.assertEqual(payload["collected_slots"]["product_routing_result"], "楼宇 + 可直接确认机型")
        self.assertTrue(any("最终槽位:" in line for line in outputs))

    def test_manual_test_observation_confirmation_confirm_only_does_not_repeat_function_call(self):
        scenario_payload = build_scenario_payload("manual_case_007")
        scenario_payload["customer"]["address"] = "江苏省扬州市宝应县安宜镇阳光锦城"
        scenario_payload["required_slots"] = ["address"]
        scenario_payload["max_turns"] = 8
        scenario = Scenario.from_dict(scenario_payload)
        policy = ServiceDialoguePolicy()
        outputs: list[str] = []
        replies = iter(
            [
                "美的空气能热水器需要维修",
                "是的",
                "宝应县",
                "阳光锦城",
                "是的，安宜镇",
                "/quit",
            ]
        )

        def fake_input(prompt: str) -> str:
            return next(replies)

        original_builder = manual_test_module.build_address_model_observation

        def fake_build_address_model_observation(transcript):
            last_user = next(
                (turn.text for turn in reversed(transcript) if turn.speaker == "user"),
                "",
            )
            if "阳光锦城" in last_user or "安宜镇" in last_user:
                return {
                    "address": "江苏省扬州市宝应县安宜镇阳光锦城",
                    "error_code": 0,
                    "error_msg": "已成功获取完整地址",
                }
            return {
                "address": "",
                "error_code": 1,
                "error_msg": "未获取完整地址",
            }

        manual_test_module.build_address_model_observation = fake_build_address_model_observation
        try:
            run_manual_test_session(
                scenario,
                output_path=None,
                max_rounds=8,
                policy=policy,
                input_func=fake_input,
                print_func=outputs.append,
            )
        finally:
            manual_test_module.build_address_model_observation = original_builder

        function_call_lines = [line for line in outputs if line.startswith("function_call:")]
        self.assertEqual(len(function_call_lines), 1)
        self.assertTrue(
            any(
                line == "[5] 客服: 好的，您的工单已受理成功，2小时内服务人员会电话联系，预约具体上门时间。"
                for line in outputs
            )
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
