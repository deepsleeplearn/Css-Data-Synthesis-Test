from __future__ import annotations

import json
import os
import sqlite3
import tempfile
import unittest
from dataclasses import asdict
from pathlib import Path
from types import SimpleNamespace

from fastapi.testclient import TestClient

import frontend.server as frontend_server
from multi_agent_data_synthesis.scenario_factory import ScenarioFactory
from multi_agent_data_synthesis.product_routing import ROUTING_RESULT_HUMAN
from tests.test_manual_test import build_scenario_payload


class FrontendServerTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        scenario_file = Path(self.temp_dir.name) / "seed_scenarios.json"
        self.db_path = Path(self.temp_dir.name) / "manual_test_reviews.sqlite3"
        self.accounts_file = Path(self.temp_dir.name) / "registered_accounts.local.json"
        scenario_file.write_text(
            json.dumps([build_scenario_payload("frontend_case")], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        self.accounts_file.write_text(
            json.dumps(
                {
                    "accounts": [
                        {
                            "username": "tester",
                            "display_name": "前端测试账号",
                            "password": "pass123",
                            "enabled": True,
                        }
                    ]
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        frontend_server.sessions.clear()
        frontend_server.auth_sessions.clear()
        frontend_server.SESSION_REVIEW_DB_PATH = self.db_path
        frontend_server.config = SimpleNamespace(
            data_dir=Path(self.temp_dir.name),
            openai_api_key="",
            product_routing_enabled=False,
            product_routing_apply_probability=0.0,
            service_agent_model="gpt-4o",
            default_temperature=0.0,
            service_ok_prefix_probability=0.0,
            max_rounds=6,
            installation_request_probability=0.5,
        )
        frontend_server.SESSION_REDIS_URL = ""
        frontend_server.factory = ScenarioFactory()
        self.previous_accounts_file = os.environ.get("FRONTEND_REGISTERED_ACCOUNTS_FILE")
        os.environ["FRONTEND_REGISTERED_ACCOUNTS_FILE"] = str(self.accounts_file)
        self.client = TestClient(frontend_server.app)

    def tearDown(self):
        frontend_server.sessions.clear()
        frontend_server.auth_sessions.clear()
        if self.previous_accounts_file is None:
            os.environ.pop("FRONTEND_REGISTERED_ACCOUNTS_FILE", None)
        else:
            os.environ["FRONTEND_REGISTERED_ACCOUNTS_FILE"] = self.previous_accounts_file
        self.temp_dir.cleanup()

    def _login(self):
        response = self.client.post(
            "/api/auth/login",
            json={"username": "tester", "password": "pass123"},
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["user"]["username"], "tester")
        return payload

    def test_protected_api_requires_login(self):
        response = self.client.get("/api/scenarios")
        self.assertEqual(response.status_code, 401)

    def test_login_rejects_unregistered_account(self):
        response = self.client.post(
            "/api/auth/login",
            json={"username": "tester", "password": "wrong-password"},
        )

        self.assertEqual(response.status_code, 401)

    def test_start_session_returns_cli_style_header(self):
        self._login()
        response = self.client.post(
            "/api/session/start",
            json={"scenario_id": "frontend_case", "known_address": ""},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "active")
        self.assertEqual(payload["next_round_index"], 1)
        self.assertIn("场景: frontend_case", payload["initial_lines"])
        self.assertIn("可用命令: /help, /slots, /state, /quit", payload["initial_lines"])
        self.assertIn("未设置已知地址，客服将按询问流程采集地址。", payload["initial_lines"])
        self.assertFalse(payload["persist_to_db_default"])
        self.assertEqual(len(frontend_server.sessions[payload["session_id"]]["checkpoints"]), 1)
        self.assertEqual(
            frontend_server.sessions[payload["session_id"]]["checkpoints"][0]["completed_rounds"],
            0,
        )

    def test_commands_do_not_consume_round_and_quit_closes_session(self):
        self._login()
        start_payload = self.client.post(
            "/api/session/start",
            json={"scenario_id": "frontend_case"},
        ).json()
        session_id = start_payload["session_id"]

        help_response = self.client.post(
            "/api/session/respond",
            json={"session_id": session_id, "text": " /help "},
        )
        self.assertEqual(help_response.status_code, 200)
        help_payload = help_response.json()
        self.assertEqual(help_payload["mode"], "command")
        self.assertEqual(help_payload["next_round_index"], 1)
        self.assertEqual(len(frontend_server.sessions[session_id]["transcript"]), 0)

        reply_response = self.client.post(
            "/api/session/respond",
            json={"session_id": session_id, "text": "美的空气能热水器需要维修"},
        )
        self.assertEqual(reply_response.status_code, 200)
        reply_payload = reply_response.json()
        self.assertEqual(reply_payload["mode"], "reply")
        self.assertEqual(reply_payload["service_turn"]["round_label"], "1")
        self.assertEqual(reply_payload["next_round_index"], 2)
        self.assertEqual(len(frontend_server.sessions[session_id]["transcript"]), 2)

        quit_response = self.client.post(
            "/api/session/respond",
            json={"session_id": session_id, "text": "/quit"},
        )
        self.assertEqual(quit_response.status_code, 200)
        quit_payload = quit_response.json()
        self.assertEqual(quit_payload["status"], "aborted")
        self.assertTrue(quit_payload["session_closed"])
        self.assertTrue(quit_payload["review_required"])
        self.assertGreater(len(quit_payload["review_options"]), 0)

        closed_response = self.client.post(
            "/api/session/respond",
            json={"session_id": session_id, "text": "继续"},
        )
        self.assertEqual(closed_response.status_code, 409)

    def test_known_address_and_round_limit_follow_manual_mode(self):
        self._login()
        start_response = self.client.post(
            "/api/session/start",
            json={
                "scenario_id": "frontend_case",
                "known_address": "浙江省杭州市余杭区良渚街道玉鸟路1号",
                "max_rounds": 1,
            },
        )

        self.assertEqual(start_response.status_code, 200)
        start_payload = start_response.json()
        session = frontend_server.sessions[start_payload["session_id"]]
        self.assertTrue(session["scenario"].hidden_context["service_known_address"])
        self.assertEqual(
            session["scenario"].customer.address,
            "浙江省杭州市余杭区良渚街道玉鸟路1号",
        )

        reply_response = self.client.post(
            "/api/session/respond",
            json={"session_id": start_payload["session_id"], "text": "热水器加热很慢"},
        )

        self.assertEqual(reply_response.status_code, 200)
        reply_payload = reply_response.json()
        self.assertEqual(reply_payload["status"], "incomplete")
        self.assertTrue(reply_payload["session_closed"])
        self.assertIn("--- 已达到最大轮次，会话结束 ---", reply_payload["output_lines"])
        self.assertTrue(reply_payload["review_required"])

    def test_rewind_endpoint_restores_session_snapshot_and_reopens_session(self):
        self._login()
        start_payload = self.client.post(
            "/api/session/start",
            json={"scenario_id": "frontend_case"},
        ).json()
        session_id = start_payload["session_id"]

        first_reply = self.client.post(
            "/api/session/respond",
            json={"session_id": session_id, "text": "美的空气能热水器需要维修"},
        )
        self.assertEqual(first_reply.status_code, 200)
        first_round_snapshot = dict(frontend_server.sessions[session_id]["trace"][0]["collected_slots_snapshot"])
        first_round_state = dict(frontend_server.sessions[session_id]["trace"][0]["runtime_state_snapshot"])
        self.assertEqual(len(frontend_server.sessions[session_id]["checkpoints"]), 2)

        second_reply = self.client.post(
            "/api/session/respond",
            json={"session_id": session_id, "text": "我姓张"},
        )
        self.assertEqual(second_reply.status_code, 200)
        self.assertEqual(second_reply.json()["next_round_index"], 3)
        self.assertEqual(len(frontend_server.sessions[session_id]["checkpoints"]), 3)

        quit_payload = self.client.post(
            "/api/session/respond",
            json={"session_id": session_id, "text": "/quit"},
        ).json()
        self.assertTrue(quit_payload["session_closed"])
        self.assertTrue(quit_payload["review_required"])

        rewind_response = self.client.post(
            "/api/session/rewind",
            json={"session_id": session_id, "clicked_user_round_index": 2},
        )
        self.assertEqual(rewind_response.status_code, 200)
        rewind_payload = rewind_response.json()

        self.assertEqual(rewind_payload["mode"], "rewind")
        self.assertEqual(rewind_payload["clicked_user_round_index"], 2)
        self.assertEqual(rewind_payload["status"], "active")
        self.assertFalse(rewind_payload["session_closed"])
        self.assertFalse(rewind_payload["review_required"])
        self.assertEqual(rewind_payload["next_round_index"], 2)
        self.assertEqual(len(rewind_payload["transcript"]), 2)
        self.assertEqual(rewind_payload["collected_slots"], first_round_snapshot)
        self.assertEqual(rewind_payload["runtime_state"], first_round_state)
        self.assertTrue(all(entry["round_count_snapshot"] <= 1 for entry in rewind_payload["terminal_entries"]))
        self.assertNotIn("会话已结束。", [entry["text"] for entry in rewind_payload["terminal_entries"]])

        session = frontend_server.sessions[session_id]
        self.assertEqual(session["status"], "active")
        self.assertEqual(session["aborted_reason"], "")
        self.assertEqual(session["ended_at"], "")
        self.assertEqual(len(session["trace"]), 1)
        self.assertEqual(len(session["checkpoints"]), 2)
        self.assertEqual(len(session["transcript"]), 2)
        self.assertEqual(session["collected_slots"], first_round_snapshot)
        self.assertEqual(asdict(session["runtime_state"]), first_round_state)

    def test_rewind_to_initial_checkpoint_clears_all_dialogue(self):
        self._login()
        start_payload = self.client.post(
            "/api/session/start",
            json={"scenario_id": "frontend_case"},
        ).json()
        session_id = start_payload["session_id"]

        reply_response = self.client.post(
            "/api/session/respond",
            json={"session_id": session_id, "text": "美的空气能热水器需要维修"},
        )
        self.assertEqual(reply_response.status_code, 200)

        rewind_response = self.client.post(
            "/api/session/rewind",
            json={"session_id": session_id, "clicked_user_round_index": 1},
        )
        self.assertEqual(rewind_response.status_code, 200)
        rewind_payload = rewind_response.json()

        self.assertEqual(rewind_payload["status"], "active")
        self.assertEqual(rewind_payload["next_round_index"], 1)
        self.assertEqual(rewind_payload["transcript"], [])
        self.assertEqual(len(rewind_payload["terminal_entries"]), 8)
        self.assertEqual(frontend_server.sessions[session_id]["checkpoints"][0]["completed_rounds"], 0)
        self.assertEqual(len(frontend_server.sessions[session_id]["checkpoints"]), 1)

    def test_rewind_clicked_third_user_round_restores_second_round_checkpoint(self):
        self._login()
        start_payload = self.client.post(
            "/api/session/start",
            json={"scenario_id": "frontend_case"},
        ).json()
        session_id = start_payload["session_id"]

        self.client.post(
            "/api/session/respond",
            json={"session_id": session_id, "text": "你好"},
        )
        self.client.post(
            "/api/session/respond",
            json={"session_id": session_id, "text": "是的"},
        )
        third_round_response = self.client.post(
            "/api/session/respond",
            json={"session_id": session_id, "text": "不知道"},
        )
        self.assertEqual(third_round_response.status_code, 200)
        fourth_round_response = self.client.post(
            "/api/session/respond",
            json={"session_id": session_id, "text": "单独生活用水的"},
        )
        self.assertEqual(fourth_round_response.status_code, 200)

        rewind_response = self.client.post(
            "/api/session/rewind",
            json={"session_id": session_id, "clicked_user_round_index": 3},
        )
        self.assertEqual(rewind_response.status_code, 200)
        rewind_payload = rewind_response.json()

        self.assertEqual(rewind_payload["clicked_user_round_index"], 3)
        self.assertEqual(rewind_payload["target_round_index"], 2)
        self.assertEqual(rewind_payload["next_round_index"], 3)
        self.assertEqual(len(rewind_payload["transcript"]), 4)
        self.assertEqual(rewind_payload["transcript"][-1]["speaker"], "客服")
        self.assertEqual(rewind_payload["transcript"][-1]["round_index"], 2)
        self.assertEqual(len(frontend_server.sessions[session_id]["checkpoints"]), 3)

    def test_rewind_clicked_second_user_round_restores_first_round_checkpoint(self):
        self._login()
        start_payload = self.client.post(
            "/api/session/start",
            json={"scenario_id": "frontend_case"},
        ).json()
        session_id = start_payload["session_id"]

        self.client.post(
            "/api/session/respond",
            json={"session_id": session_id, "text": "你好"},
        )
        self.client.post(
            "/api/session/respond",
            json={"session_id": session_id, "text": "是的"},
        )

        rewind_response = self.client.post(
            "/api/session/rewind",
            json={
                "session_id": session_id,
                "clicked_user_round_index": 2,
                "restore_checkpoint_index": 1,
            },
        )
        self.assertEqual(rewind_response.status_code, 200)
        rewind_payload = rewind_response.json()

        self.assertEqual(rewind_payload["clicked_user_round_index"], 2)
        self.assertEqual(rewind_payload["target_round_index"], 1)
        self.assertEqual(rewind_payload["next_round_index"], 2)
        self.assertEqual(len(rewind_payload["transcript"]), 2)
        self.assertEqual(rewind_payload["transcript"][-1]["speaker"], "客服")
        self.assertEqual(rewind_payload["transcript"][-1]["round_index"], 1)

    def test_rewind_accepts_legacy_target_round_index_payload(self):
        self._login()
        start_payload = self.client.post(
            "/api/session/start",
            json={"scenario_id": "frontend_case"},
        ).json()
        session_id = start_payload["session_id"]

        self.client.post(
            "/api/session/respond",
            json={"session_id": session_id, "text": "你好"},
        )
        self.client.post(
            "/api/session/respond",
            json={"session_id": session_id, "text": "是的"},
        )

        rewind_response = self.client.post(
            "/api/session/rewind",
            json={
                "session_id": session_id,
                "target_round_index": 1,
            },
        )
        self.assertEqual(rewind_response.status_code, 200)
        rewind_payload = rewind_response.json()

        self.assertEqual(rewind_payload["clicked_user_round_index"], 2)
        self.assertEqual(rewind_payload["target_round_index"], 1)
        self.assertEqual(rewind_payload["next_round_index"], 2)
        self.assertEqual(len(rewind_payload["transcript"]), 2)

    def test_rewind_restores_product_routing_plan_from_checkpoint(self):
        self._login()
        start_payload = self.client.post(
            "/api/session/start",
            json={"scenario_id": "frontend_case"},
        ).json()
        session_id = start_payload["session_id"]
        session = frontend_server.sessions[session_id]
        frontend_server.config.product_routing_enabled = True
        frontend_server.config.product_routing_apply_probability = 1.0
        session["policy"] = frontend_server._build_service_policy()
        session["scenario"].hidden_context["interactive_test_freeform"] = True
        session["scenario"].hidden_context["product_routing_plan"] = {
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
        session["scenario"].hidden_context["product_routing_result"] = ""
        session["checkpoints"][0]["scenario"] = session["scenario"].to_dict()

        self.client.post(
            "/api/session/respond",
            json={"session_id": session_id, "text": "你好"},
        )
        self.client.post(
            "/api/session/respond",
            json={"session_id": session_id, "text": "是的"},
        )
        self.client.post(
            "/api/session/respond",
            json={"session_id": session_id, "text": "不清楚"},
        )
        self.client.post(
            "/api/session/respond",
            json={"session_id": session_id, "text": "单独生活用水的"},
        )

        rewind_response = self.client.post(
            "/api/session/rewind",
            json={
                "session_id": session_id,
                "clicked_user_round_index": 3,
                "restore_checkpoint_index": 2,
            },
        )
        self.assertEqual(rewind_response.status_code, 200)
        self.assertEqual(
            frontend_server.sessions[session_id]["scenario"].hidden_context["product_routing_plan"]["steps"][0]["prompt_key"],
            "brand_or_series",
        )

        reply_response = self.client.post(
            "/api/session/respond",
            json={"session_id": session_id, "text": "酷风的"},
        )
        self.assertEqual(reply_response.status_code, 200)
        reply_payload = reply_response.json()
        self.assertEqual(reply_payload["status"], "transferred")
        self.assertEqual(reply_payload["collected_slots"]["product_routing_result"], ROUTING_RESULT_HUMAN)

    def test_review_endpoint_persists_session_to_sqlite_when_enabled(self):
        self._login()
        start_payload = self.client.post(
            "/api/session/start",
            json={"scenario_id": "frontend_case", "persist_to_db": True},
        ).json()
        session_id = start_payload["session_id"]

        reply_payload = self.client.post(
            "/api/session/respond",
            json={"session_id": session_id, "text": "美的空气能热水器需要维修"},
        ).json()
        self.assertEqual(reply_payload["mode"], "reply")

        quit_payload = self.client.post(
            "/api/session/respond",
            json={"session_id": session_id, "text": "/quit"},
        ).json()

        self.assertTrue(quit_payload["review_required"])

        review_response = self.client.post(
            "/api/session/review",
            json={
                "session_id": session_id,
                "is_correct": False,
                "failed_flow_stage": "address_collection",
                "notes": "地址追问层级不对",
                "persist_to_db": True,
            },
        )

        self.assertEqual(review_response.status_code, 200)
        review_payload = review_response.json()
        self.assertTrue(review_payload["persisted_to_db"])
        self.assertEqual(review_payload["session_id"], session_id)
        self.assertEqual(review_payload["username"], "tester")
        self.assertTrue(self.db_path.exists())

        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT scenario_id, username, status, is_correct, failed_flow_stage, reviewer_notes, review_payload_json "
                "FROM manual_test_reviews WHERE session_id = ?",
                (session_id,),
            ).fetchone()

        self.assertIsNotNone(row)
        self.assertEqual(row[0], "frontend_case")
        self.assertEqual(row[1], "tester")
        self.assertEqual(row[2], "aborted")
        self.assertEqual(row[3], 0)
        self.assertEqual(row[4], "address_collection")
        self.assertEqual(row[5], "地址追问层级不对")
        saved_payload = json.loads(row[6])
        self.assertEqual(saved_payload["username"], "tester")
        self.assertEqual(saved_payload["review"]["failed_flow_stage"], "address_collection")
        self.assertEqual(saved_payload["review"]["username"], "tester")
        self.assertEqual(saved_payload["review"]["notes"], "地址追问层级不对")
        self.assertIn("previous_user_intent_model_inference_used", saved_payload["transcript"][1])
        self.assertEqual(
            saved_payload["transcript"][1]["previous_user_intent_model_inference_used"],
            saved_payload["transcript"][1]["model_intent_inference_used"],
        )
        self.assertEqual(
            saved_payload["trace"][0]["previous_user_intent_model_inference_used"],
            saved_payload["trace"][0]["used_model_intent_inference"],
        )

    def test_review_endpoint_migrates_existing_database_without_losing_rows(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE manual_test_reviews (
                    session_id TEXT PRIMARY KEY,
                    scenario_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    aborted_reason TEXT NOT NULL,
                    is_correct INTEGER NOT NULL,
                    failed_flow_stage TEXT NOT NULL,
                    reviewer_notes TEXT NOT NULL,
                    persist_to_db INTEGER NOT NULL,
                    started_at TEXT NOT NULL,
                    ended_at TEXT NOT NULL,
                    reviewed_at TEXT NOT NULL,
                    review_payload_json TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                INSERT INTO manual_test_reviews (
                    session_id,
                    scenario_id,
                    status,
                    aborted_reason,
                    is_correct,
                    failed_flow_stage,
                    reviewer_notes,
                    persist_to_db,
                    started_at,
                    ended_at,
                    reviewed_at,
                    review_payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "legacy-session",
                    "legacy-scenario",
                    "completed",
                    "",
                    1,
                    "",
                    "",
                    1,
                    "2026-01-01T00:00:00+00:00",
                    "2026-01-01T00:01:00+00:00",
                    "2026-01-01T00:02:00+00:00",
                    json.dumps({"session_id": "legacy-session"}, ensure_ascii=False),
                ),
            )
            conn.commit()

        self._login()
        start_payload = self.client.post(
            "/api/session/start",
            json={"scenario_id": "frontend_case", "persist_to_db": True},
        ).json()
        session_id = start_payload["session_id"]
        self.client.post(
            "/api/session/respond",
            json={"session_id": session_id, "text": "/quit"},
        )
        review_response = self.client.post(
            "/api/session/review",
            json={
                "session_id": session_id,
                "is_correct": True,
                "failed_flow_stage": "",
                "notes": "",
                "persist_to_db": True,
            },
        )

        self.assertEqual(review_response.status_code, 200)
        with sqlite3.connect(self.db_path) as conn:
            columns = [row[1] for row in conn.execute("PRAGMA table_info(manual_test_reviews)").fetchall()]
            count = conn.execute("SELECT COUNT(*) FROM manual_test_reviews").fetchone()[0]
            legacy_row = conn.execute(
                "SELECT session_id, username FROM manual_test_reviews WHERE session_id = ?",
                ("legacy-session",),
            ).fetchone()
            new_row = conn.execute(
                "SELECT session_id, username FROM manual_test_reviews WHERE session_id = ?",
                (session_id,),
            ).fetchone()

        self.assertIn("username", columns)
        self.assertEqual(count, 2)
        self.assertEqual(legacy_row, ("legacy-session", None))
        self.assertEqual(new_row, (session_id, "tester"))

    def test_review_endpoint_requires_failed_stage_when_marked_incorrect(self):
        self._login()
        start_payload = self.client.post(
            "/api/session/start",
            json={"scenario_id": "frontend_case"},
        ).json()
        session_id = start_payload["session_id"]
        self.client.post(
            "/api/session/respond",
            json={"session_id": session_id, "text": "/quit"},
        )

        review_response = self.client.post(
            "/api/session/review",
            json={
                "session_id": session_id,
                "is_correct": False,
                "failed_flow_stage": "",
                "notes": "缺少流程选择",
                "persist_to_db": False,
            },
        )

        self.assertEqual(review_response.status_code, 400)

    def test_frontend_static_files_include_review_close_control(self):
        index_response = self.client.get("/")
        self.assertEqual(index_response.status_code, 200)
        self.assertIn('id="review-close-btn"', index_response.text)
        self.assertIn('id="review-toggle-btn"', index_response.text)
        self.assertIn("点击任意用户行可删除该行及其下方所有内容", index_response.text)

        app_response = self.client.get("/static/app.js")
        self.assertEqual(app_response.status_code, 200)
        self.assertIn("打开评审", app_response.text)
        self.assertIn("/api/session/rewind", app_response.text)
        self.assertIn("terminal-turn-trigger", app_response.text)
        self.assertNotIn("/api/session/review/dismiss", app_response.text)

    def test_user_requested_human_handoff_closes_session_and_keeps_review_flow(self):
        self._login()
        start_payload = self.client.post(
            "/api/session/start",
            json={"scenario_id": "frontend_case"},
        ).json()
        session_id = start_payload["session_id"]

        reply_response = self.client.post(
            "/api/session/respond",
            json={"session_id": session_id, "text": "帮我转人工"},
        )

        self.assertEqual(reply_response.status_code, 200)
        reply_payload = reply_response.json()
        self.assertEqual(reply_payload["status"], "transferred")
        self.assertTrue(reply_payload["session_closed"])
        self.assertEqual(reply_payload["service_turn"]["text"], "请稍等，正在为您转接人工服务。")
        self.assertIn("--- 已转接人工，会话结束 ---", reply_payload["output_lines"])
        self.assertEqual(reply_payload["close_status"], "transferred")
        self.assertEqual(reply_payload["close_reason"], "user_requested_human")
        self.assertEqual(reply_payload["collected_slots"]["product_routing_result"], "转人工")
        self.assertTrue(reply_payload["review_required"])


if __name__ == "__main__":
    unittest.main()
