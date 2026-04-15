from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from fastapi.testclient import TestClient

import frontend.server as frontend_server
from multi_agent_data_synthesis.scenario_factory import ScenarioFactory
from tests.test_manual_test import build_scenario_payload


class FrontendServerTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        scenario_file = Path(self.temp_dir.name) / "seed_scenarios.json"
        self.db_path = Path(self.temp_dir.name) / "manual_test_reviews.sqlite3"
        scenario_file.write_text(
            json.dumps([build_scenario_payload("frontend_case")], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        frontend_server.sessions.clear()
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
        frontend_server.factory = ScenarioFactory()
        self.client = TestClient(frontend_server.app)

    def tearDown(self):
        frontend_server.sessions.clear()
        self.temp_dir.cleanup()

    def test_start_session_returns_cli_style_header(self):
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

    def test_commands_do_not_consume_round_and_quit_closes_session(self):
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

    def test_review_endpoint_persists_session_to_sqlite_when_enabled(self):
        start_payload = self.client.post(
            "/api/session/start",
            json={"scenario_id": "frontend_case", "persist_to_db": True},
        ).json()
        session_id = start_payload["session_id"]

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
        self.assertTrue(self.db_path.exists())

        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT scenario_id, status, is_correct, failed_flow_stage, reviewer_notes, review_payload_json "
                "FROM manual_test_reviews WHERE session_id = ?",
                (session_id,),
            ).fetchone()

        self.assertIsNotNone(row)
        self.assertEqual(row[0], "frontend_case")
        self.assertEqual(row[1], "aborted")
        self.assertEqual(row[2], 0)
        self.assertEqual(row[3], "address_collection")
        self.assertEqual(row[4], "地址追问层级不对")
        saved_payload = json.loads(row[5])
        self.assertEqual(saved_payload["review"]["failed_flow_stage"], "address_collection")
        self.assertEqual(saved_payload["review"]["notes"], "地址追问层级不对")

    def test_review_endpoint_requires_failed_stage_when_marked_incorrect(self):
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


if __name__ == "__main__":
    unittest.main()
