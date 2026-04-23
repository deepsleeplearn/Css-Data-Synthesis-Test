from __future__ import annotations

import json
import os
import sqlite3
import tempfile
import unittest
from dataclasses import asdict
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient

import frontend.server as frontend_server
from css_data_synthesis_test.scenario_factory import ScenarioFactory
from css_data_synthesis_test.product_routing import ROUTING_RESULT_HUMAN
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
                        },
                        {
                            "username": "chat-admin",
                            "display_name": "测试管理员",
                            "password": "admin123",
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
        frontend_server.CHAT_STORAGE_PATH = Path(self.temp_dir.name) / "frontend_chat_messages.json"
        frontend_server.CHAT_RECALL_STORAGE_PATH = Path(self.temp_dir.name) / "frontend_chat_message_recalls.json"
        frontend_server.chat_state = frontend_server._empty_chat_state()
        frontend_server.chat_state_loaded = False
        frontend_server._SESSION_REVIEW_DB_STATE_PATH = None
        frontend_server._mark_review_db_unready()
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
        frontend_server.chat_state = frontend_server._empty_chat_state()
        frontend_server.chat_state_loaded = False
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

    def _login_admin(self):
        response = self.client.post(
            "/api/auth/login",
            json={"username": "chat-admin", "password": "admin123"},
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["user"]["username"], "chat-admin")
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

    def test_start_session_keeps_cli_metadata_out_of_terminal(self):
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
        self.assertEqual(payload["terminal_entries"], [])
        self.assertFalse(payload["persist_to_db_default"])
        self.assertEqual(len(frontend_server.sessions[payload["session_id"]]["checkpoints"]), 1)
        self.assertEqual(
            frontend_server.sessions[payload["session_id"]]["checkpoints"][0]["completed_rounds"],
            0,
        )

    def test_mock_known_address_endpoint_returns_realistic_prefill(self):
        self._login()

        response = self.client.get("/api/mock-known-address", params={"scenario_id": "frontend_case"})

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("known_address", payload)
        self.assertRegex(payload["known_address"], r"(省|市).*(区|县|市|镇).*(街道|镇).*(幢|号|栋|座|楼)")

    def test_fault_issue_categories_endpoint_returns_repair_reference_keys(self):
        self._login()
        reference_path = Path(self.temp_dir.name) / "utterance_reference_library.json"
        reference_path.write_text(
            json.dumps(
                {
                    "报修": {
                        "不制热/无热水": [],
                        "故障码（P1/P4/P2/P5/PF等）": [],
                        "设备不启动/通电不工作": [],
                    },
                    "报装": {"安装预约/时间调整": []},
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        response = self.client.get("/api/reference/fault-issue-categories")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(
            payload["categories"],
            ["不制热/无热水", "故障码（P1/P4/P2/P5/PF等）", "设备不启动/通电不工作"],
        )

    def test_punctuation_predict_endpoint_returns_punctuated_text(self):
        self._login()

        with patch("frontend.server._punctuate_user_text_for_session", return_value="我在江苏省苏州市。"):
            response = self.client.post(
                "/api/punctuation/predict",
                json={"text": "我在江苏省苏州市"},
            )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["input_text"], "我在江苏省苏州市")
        self.assertEqual(payload["punctuated_text"], "我在江苏省苏州市。")

    def test_chat_state_lists_online_users_and_accepts_group_messages(self):
        self._login()

        initial_state = self.client.get("/api/chat/state", params={"chat_visible": True})
        self.assertEqual(initial_state.status_code, 200)
        initial_payload = initial_state.json()
        self.assertFalse(initial_payload["chat_admin"])
        self.assertTrue(initial_payload["chat_visible"])
        self.assertEqual(initial_payload["online_count"], 1)
        self.assertEqual(initial_payload["online_users"][0]["username"], "tester")
        self.assertEqual(initial_payload["messages"], [])

        post_response = self.client.post("/api/chat/messages", json={"text": "大家先看前端回归结果。"})
        self.assertEqual(post_response.status_code, 200)
        post_payload = post_response.json()
        self.assertEqual(post_payload["message"]["id"], 1)
        self.assertEqual(post_payload["message"]["display_name"], "前端测试账号")

        latest_state = self.client.get("/api/chat/state", params={"since_message_id": 0, "chat_visible": True})
        self.assertEqual(latest_state.status_code, 200)
        latest_payload = latest_state.json()
        self.assertEqual(latest_payload["latest_message_id"], 1)
        self.assertEqual(len(latest_payload["messages"]), 1)
        self.assertEqual(latest_payload["messages"][0]["text"], "大家先看前端回归结果。")
        self.assertEqual(latest_payload["storage_path"], str(frontend_server.CHAT_STORAGE_PATH))

    def test_chat_messages_persist_to_local_file_and_can_be_reloaded(self):
        self._login()

        response = self.client.post("/api/chat/messages", json={"text": "这条消息需要落盘。"})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(frontend_server.CHAT_STORAGE_PATH.exists())

        persisted_payload = json.loads(frontend_server.CHAT_STORAGE_PATH.read_text(encoding="utf-8"))
        self.assertEqual(persisted_payload["last_message_id"], 1)
        self.assertEqual(persisted_payload["messages"][0]["text"], "这条消息需要落盘。")

        frontend_server.chat_state = frontend_server._empty_chat_state()
        frontend_server.chat_state_loaded = False

        reloaded_state = self.client.get("/api/chat/state")
        self.assertEqual(reloaded_state.status_code, 200)
        reloaded_payload = reloaded_state.json()
        self.assertEqual(len(reloaded_payload["messages"]), 1)
        self.assertEqual(reloaded_payload["messages"][0]["text"], "这条消息需要落盘。")

    def test_chat_state_returns_all_existing_messages_on_initial_load(self):
        self._login()
        self.client.post("/api/chat/messages", json={"text": "第一条历史消息"})
        self.client.post("/api/chat/messages", json={"text": "第二条历史消息"})

        initial_state = self.client.get("/api/chat/state", params={"since_message_id": 0, "chat_visible": True})

        self.assertEqual(initial_state.status_code, 200)
        payload = initial_state.json()
        self.assertEqual([item["text"] for item in payload["messages"]], ["第一条历史消息", "第二条历史消息"])

    def test_user_can_recall_own_message_without_mutating_persisted_message_file(self):
        self._login()
        post_response = self.client.post("/api/chat/messages", json={"text": "这条消息稍后撤回。"})
        self.assertEqual(post_response.status_code, 200)

        recall_response = self.client.post("/api/chat/messages/1/recall")
        self.assertEqual(recall_response.status_code, 200)
        recall_payload = recall_response.json()
        self.assertTrue(recall_payload["recalled"])
        self.assertTrue(recall_payload["full_sync"])
        self.assertEqual(recall_payload["snapshot_revision"], 1)
        self.assertTrue(recall_payload["messages"][0]["recalled"])

        latest_state = self.client.get(
            "/api/chat/state",
            params={"since_message_id": 1, "since_snapshot_revision": 0, "chat_visible": True},
        )
        self.assertEqual(latest_state.status_code, 200)
        state_payload = latest_state.json()
        self.assertTrue(state_payload["full_sync"])
        self.assertEqual(state_payload["snapshot_revision"], 1)
        self.assertTrue(state_payload["messages"][0]["recalled"])

        persisted_payload = json.loads(frontend_server.CHAT_STORAGE_PATH.read_text(encoding="utf-8"))
        self.assertEqual(persisted_payload["messages"][0]["text"], "这条消息稍后撤回。")
        self.assertNotIn("recalled", persisted_payload["messages"][0])

        recall_payload = json.loads(frontend_server.CHAT_RECALL_STORAGE_PATH.read_text(encoding="utf-8"))
        self.assertEqual(recall_payload["recalled_message_ids"], [1])

    def test_user_cannot_recall_other_users_message(self):
        author_client = TestClient(frontend_server.app)

        author_login = author_client.post(
            "/api/auth/login",
            json={"username": "tester", "password": "pass123"},
        )
        self.assertEqual(author_login.status_code, 200)
        create_response = author_client.post("/api/chat/messages", json={"text": "这条消息不允许别人撤回。"})
        self.assertEqual(create_response.status_code, 200)

        self._login_admin()
        forbidden = self.client.post("/api/chat/messages/1/recall")
        self.assertEqual(forbidden.status_code, 403)

    def test_recalled_message_is_visible_to_other_logged_in_clients(self):
        viewer_client = TestClient(frontend_server.app)

        self._login()
        self.client.post("/api/chat/messages", json={"text": "这条消息会被撤回。"})

        viewer_login = viewer_client.post(
            "/api/auth/login",
            json={"username": "chat-admin", "password": "admin123"},
        )
        self.assertEqual(viewer_login.status_code, 200)
        viewer_state_before = viewer_client.get(
            "/api/chat/state",
            params={"since_message_id": 0, "since_snapshot_revision": 0, "chat_visible": False},
        )
        self.assertEqual(viewer_state_before.status_code, 200)
        self.assertFalse(viewer_state_before.json()["messages"][0]["recalled"])

        recall_response = self.client.post("/api/chat/messages/1/recall")
        self.assertEqual(recall_response.status_code, 200)

        viewer_state_after = viewer_client.get(
            "/api/chat/state",
            params={"since_message_id": 1, "since_snapshot_revision": 0, "chat_visible": False},
        )
        self.assertEqual(viewer_state_after.status_code, 200)
        viewer_payload = viewer_state_after.json()
        self.assertTrue(viewer_payload["full_sync"])
        self.assertEqual(viewer_payload["snapshot_revision"], 1)
        self.assertEqual(len(viewer_payload["messages"]), 1)
        self.assertTrue(viewer_payload["messages"][0]["recalled"])

    def test_only_admin_can_clear_chat_history(self):
        self._login()
        self.client.post("/api/chat/messages", json={"text": "普通账号消息"})

        forbidden = self.client.post("/api/chat/history/clear")
        self.assertEqual(forbidden.status_code, 403)

        self.client.post("/api/auth/logout")
        self._login_admin()

        allowed = self.client.post("/api/chat/history/clear")
        self.assertEqual(allowed.status_code, 200)
        payload = allowed.json()
        self.assertTrue(payload["cleared"])
        self.assertEqual(payload["messages"], [])
        self.assertEqual(payload["latest_message_id"], 0)
        self.assertFalse(frontend_server.CHAT_STORAGE_PATH.exists())
        self.assertFalse(frontend_server.CHAT_RECALL_STORAGE_PATH.exists())

        state_after_clear = self.client.get("/api/chat/state")
        self.assertEqual(state_after_clear.status_code, 200)
        self.assertEqual(state_after_clear.json()["messages"], [])

    def test_clear_chat_history_is_visible_to_other_logged_in_clients(self):
        viewer_client = TestClient(frontend_server.app)

        self._login()
        self.client.post("/api/chat/messages", json={"text": "需要被全员清空的消息"})

        viewer_login = viewer_client.post(
            "/api/auth/login",
            json={"username": "tester", "password": "pass123"},
        )
        self.assertEqual(viewer_login.status_code, 200)
        viewer_state_before = viewer_client.get("/api/chat/state", params={"since_message_id": 0, "chat_visible": False})
        self.assertEqual(viewer_state_before.status_code, 200)
        self.assertEqual(len(viewer_state_before.json()["messages"]), 1)

        self.client.post("/api/auth/logout")
        self._login_admin()
        clear_response = self.client.post("/api/chat/history/clear")
        self.assertEqual(clear_response.status_code, 200)

        viewer_state_after = viewer_client.get("/api/chat/state", params={"since_message_id": 1, "chat_visible": False})
        self.assertEqual(viewer_state_after.status_code, 200)
        self.assertEqual(viewer_state_after.json()["latest_message_id"], 0)
        self.assertEqual(viewer_state_after.json()["messages"], [])

    def test_latest_self_message_readers_only_include_users_with_visible_chat(self):
        reader_client = TestClient(frontend_server.app)

        self._login()
        self.client.get("/api/chat/state", params={"chat_visible": True})
        self.client.post("/api/chat/messages", json={"text": "请确认这条消息的已读成员"})

        reader_login = reader_client.post(
            "/api/auth/login",
            json={"username": "chat-admin", "password": "admin123"},
        )
        self.assertEqual(reader_login.status_code, 200)

        hidden_reader_state = reader_client.get("/api/chat/state", params={"chat_visible": False})
        self.assertEqual(hidden_reader_state.status_code, 200)

        hidden_readers = self.client.get("/api/chat/messages/latest-readers", params={"chat_visible": True})
        self.assertEqual(hidden_readers.status_code, 200)
        hidden_payload = hidden_readers.json()
        self.assertEqual(hidden_payload["latest_self_message_text"], "请确认这条消息的已读成员")
        self.assertEqual(hidden_payload["read_by"], [])

        visible_reader_state = reader_client.get("/api/chat/state", params={"chat_visible": True})
        self.assertEqual(visible_reader_state.status_code, 200)

        visible_readers = self.client.get("/api/chat/messages/latest-readers", params={"chat_visible": True})
        self.assertEqual(visible_readers.status_code, 200)
        visible_payload = visible_readers.json()
        self.assertGreater(visible_payload["latest_self_message_id"], 0)
        self.assertEqual([item["username"] for item in visible_payload["read_by"]], ["chat-admin"])

    def test_session_view_exposes_started_and_ended_timestamps(self):
        self._login()
        start_payload = self.client.post(
            "/api/session/start",
            json={"scenario_id": "frontend_case"},
        ).json()
        session_id = start_payload["session_id"]

        self.assertRegex(start_payload["started_at"], r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$")
        self.assertEqual(start_payload["ended_at"], "")

        quit_payload = self.client.post(
            "/api/session/respond",
            json={"session_id": session_id, "text": "/quit"},
        ).json()

        self.assertRegex(quit_payload["started_at"], r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$")
        self.assertRegex(quit_payload["ended_at"], r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$")

    def test_session_view_exposes_address_granularity_runtime_state(self):
        self._login()
        start_payload = self.client.post(
            "/api/session/start",
            json={"scenario_id": "frontend_case"},
        ).json()
        session_id = start_payload["session_id"]
        session = frontend_server.sessions[session_id]
        session["runtime_state"].awaiting_full_address = True
        session["runtime_state"].partial_address_candidate = "江苏省南京市玄武区南京农业大学卫岗校区"

        payload = frontend_server._build_session_view(session_id, session)
        runtime_state = payload["runtime_state"]

        self.assertEqual(runtime_state["address_current_candidate"], "江苏省南京市玄武区南京农业大学卫岗校区")
        self.assertEqual(runtime_state["address_slot_province"], "江苏省")
        self.assertEqual(runtime_state["address_slot_city"], "南京市")
        self.assertEqual(runtime_state["address_slot_district"], "玄武区")
        self.assertEqual(runtime_state["address_slot_community"], "南京农业大学卫岗校区")
        self.assertEqual(runtime_state["address_slot_landmark"], "")
        self.assertIn("address_missing_required_precision", runtime_state)

    def test_start_session_accepts_manual_call_start_time(self):
        self._login()

        response = self.client.post(
            "/api/session/start",
            json={
                "scenario_id": "frontend_case",
                "call_start_time": "2026-04-18 09:30:45",
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        session = frontend_server.sessions[payload["session_id"]]
        self.assertEqual(session["scenario"].call_start_time, "2026-04-18 09:30:45")
        self.assertEqual(payload["scenario"]["call_start_time"], "2026-04-18 09:30:45")

    def test_start_session_rejects_invalid_manual_call_start_time(self):
        self._login()

        response = self.client.post(
            "/api/session/start",
            json={
                "scenario_id": "frontend_case",
                "call_start_time": "2026/04/18 09:30",
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("通话开始时间格式必须为", response.json()["detail"])

    def test_start_session_can_use_click_time_as_call_start_time(self):
        self._login()

        with patch("frontend.server._current_display_timestamp", return_value="2026-04-18 15:03:39"):
            response = self.client.post(
                "/api/session/start",
                json={
                    "scenario_id": "frontend_case",
                    "call_start_time": "2026-04-17 01:02:03",
                    "use_session_start_time_as_call_start_time": True,
                },
            )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        session = frontend_server.sessions[payload["session_id"]]
        self.assertEqual(session["scenario"].call_start_time, "2026-04-18 15:03:39")
        self.assertEqual(payload["scenario"]["call_start_time"], "2026-04-18 15:03:39")
        self.assertEqual(session["started_at"], "2026-04-18 15:03:39")

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

    def test_session_respond_keeps_first_round_user_text_unpunctuated(self):
        self._login()
        start_payload = self.client.post(
            "/api/session/start",
            json={"scenario_id": "frontend_case"},
        ).json()
        session_id = start_payload["session_id"]

        with patch("frontend.server._punctuate_user_text_for_session", return_value="美的空气能热水器需要维修。") as punctuate_mock:
            reply_response = self.client.post(
                "/api/session/respond",
                json={"session_id": session_id, "text": "美的空气能热水器需要维修"},
            )

        self.assertEqual(reply_response.status_code, 200)
        payload = reply_response.json()
        session = frontend_server.sessions[session_id]
        punctuate_mock.assert_not_called()
        self.assertEqual(session["transcript"][0].text, "美的空气能热水器需要维修")
        self.assertEqual(session["trace"][0]["user_text"], "美的空气能热水器需要维修")
        self.assertEqual(payload["transcript"][0]["text"], "美的空气能热水器需要维修")
        self.assertEqual(payload["terminal_entries"][0]["text"], "美的空气能热水器需要维修")

    def test_session_respond_punctuates_user_text_from_second_round(self):
        self._login()
        start_payload = self.client.post(
            "/api/session/start",
            json={"scenario_id": "frontend_case"},
        ).json()
        session_id = start_payload["session_id"]

        first_reply_response = self.client.post(
            "/api/session/respond",
            json={"session_id": session_id, "text": "美的空气能热水器需要维修"},
        )
        self.assertEqual(first_reply_response.status_code, 200)

        with patch("frontend.server._punctuate_user_text_for_session", return_value="我姓张。") as punctuate_mock:
            second_reply_response = self.client.post(
                "/api/session/respond",
                json={"session_id": session_id, "text": "我姓张"},
            )

        self.assertEqual(second_reply_response.status_code, 200)
        punctuate_mock.assert_called_once_with("我姓张")
        payload = second_reply_response.json()
        session = frontend_server.sessions[session_id]
        self.assertEqual(session["transcript"][2].text, "我姓张。")
        self.assertEqual(session["trace"][1]["user_text"], "我姓张。")
        self.assertEqual(payload["transcript"][2]["text"], "我姓张。")
        self.assertEqual(payload["terminal_entries"][2]["text"], "我姓张。")

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

    def test_auto_generated_known_address_is_preserved_when_frontend_input_is_empty(self):
        self._login()
        frontend_server.config.openai_api_key = "test-key"
        base_scenario = frontend_server.factory.load_from_file(Path(self.temp_dir.name) / "seed_scenarios.json")[0]
        generated_scenario = base_scenario.with_generated_hidden_settings(
            customer=base_scenario.customer,
            request=base_scenario.request,
            hidden_context={
                **dict(base_scenario.hidden_context),
                "service_known_address": True,
                "service_known_address_value": "浙江省杭州市余杭区良渚街道玉鸟路88号",
                "service_known_address_matches_actual": True,
            },
        )

        with patch("frontend.server.HiddenSettingsTool") as tool_cls:
            tool_cls.return_value.generate_for_scenario.return_value = generated_scenario
            start_response = self.client.post(
                "/api/session/start",
                json={
                    "scenario_id": "frontend_case",
                    "auto_generate_hidden_settings": True,
                    "known_address": "",
                },
            )

        self.assertEqual(start_response.status_code, 200)
        start_payload = start_response.json()
        session = frontend_server.sessions[start_payload["session_id"]]
        self.assertTrue(session["scenario"].hidden_context["service_known_address"])
        self.assertEqual(
            session["scenario"].hidden_context["service_known_address_value"],
            "浙江省杭州市余杭区良渚街道玉鸟路88号",
        )
        self.assertIn(
            "使用隐藏设定中的已知地址，客服将优先核对: 浙江省杭州市余杭区良渚街道玉鸟路88号",
            start_payload["initial_lines"],
        )
        tool_cls.return_value.generate_for_scenario.assert_called_once_with(
            base_scenario,
            use_utterance_reference=True,
        )

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
        self.assertEqual(rewind_payload["terminal_entries"], [])
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

    def test_rewind_clears_pending_product_routing_trace_without_aftereffects(self):
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
            "trace": ["brand_series.lieyan"],
            "summary": "brand_series.lieyan -> 楼宇 + 可直接确认机型",
            "steps": [
                {
                    "prompt_key": "brand_or_series",
                    "prompt": "请问您的空气能是什么具体品牌或系列呢？",
                    "answer_key": "brand_series.lieyan",
                    "answer_value": "烈焰",
                    "answer_instruction": "自然表达系列是烈焰。",
                }
            ],
        }
        session["scenario"].hidden_context["product_routing_result"] = ""
        session["scenario"].hidden_context["product_routing_trace"] = ["brand_series.lieyan"]
        session["checkpoints"][0]["scenario"] = session["scenario"].to_dict()

        self.client.post(
            "/api/session/respond",
            json={"session_id": session_id, "text": "你好"},
        )
        self.client.post(
            "/api/session/respond",
            json={"session_id": session_id, "text": "是的"},
        )

        first_reply = self.client.post(
            "/api/session/respond",
            json={"session_id": session_id, "text": "烈焰"},
        )
        self.assertEqual(first_reply.status_code, 200)
        self.assertEqual(
            first_reply.json()["runtime_state"]["product_routing_observed_trace"],
            ["brand_series.lieyan"],
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
        rewind_payload = rewind_response.json()
        self.assertEqual(rewind_payload["runtime_state"]["product_routing_observed_trace"], [])
        self.assertEqual(
            frontend_server.sessions[session_id]["scenario"].hidden_context["product_routing_trace"],
            [],
        )

        second_reply = self.client.post(
            "/api/session/respond",
            json={"session_id": session_id, "text": "烈焰"},
        )
        self.assertEqual(second_reply.status_code, 200)
        self.assertEqual(
            second_reply.json()["runtime_state"]["product_routing_observed_trace"],
            ["brand_series.lieyan"],
        )

        second_rewind = self.client.post(
            "/api/session/rewind",
            json={
                "session_id": session_id,
                "clicked_user_round_index": 3,
                "restore_checkpoint_index": 2,
            },
        )
        self.assertEqual(second_rewind.status_code, 200)
        self.assertEqual(second_rewind.json()["runtime_state"]["product_routing_observed_trace"], [])
        self.assertEqual(
            frontend_server.sessions[session_id]["scenario"].hidden_context["product_routing_trace"],
            [],
        )

        third_reply = self.client.post(
            "/api/session/respond",
            json={"session_id": session_id, "text": "烈焰"},
        )
        self.assertEqual(third_reply.status_code, 200)
        self.assertEqual(
            third_reply.json()["runtime_state"]["product_routing_observed_trace"],
            ["brand_series.lieyan"],
        )

    def test_review_endpoint_persists_session_to_sqlite_when_enabled(self):
        self._login()
        start_payload = self.client.post(
            "/api/session/start",
            json={
                "scenario_id": "frontend_case",
                "persist_to_db": True,
                "known_address": "浙江省杭州市余杭区良渚街道玉鸟路1号",
                "call_start_time": "2026-04-18 09:30:45",
            },
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
                "SELECT scenario_id, username, status, is_correct, failed_flow_stage, reviewer_notes, "
                "started_at, ended_at, reviewed_at, review_payload_json "
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
        self.assertRegex(row[6], r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$")
        self.assertRegex(row[7], r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$")
        self.assertRegex(row[8], r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$")
        saved_payload = json.loads(row[9])
        self.assertEqual(saved_payload["username"], "tester")
        self.assertEqual(saved_payload["review"]["failed_flow_stage"], "address_collection")
        self.assertEqual(saved_payload["review"]["username"], "tester")
        self.assertEqual(saved_payload["review"]["notes"], "地址追问层级不对")
        self.assertRegex(saved_payload["started_at"], r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$")
        self.assertRegex(saved_payload["ended_at"], r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$")
        self.assertEqual(saved_payload["status"], "aborted")
        self.assertEqual(saved_payload["call_start_time"], "2026-04-18 09:30:45")
        self.assertEqual(saved_payload["session_config"]["known_address"], "浙江省杭州市余杭区良渚街道玉鸟路1号")
        self.assertEqual(saved_payload["session_config"]["call_start_time"], "2026-04-18 09:30:45")
        self.assertIn("issue_description", saved_payload["collected_slots"])
        self.assertIn("previous_user_intent_model_inference_used", saved_payload["transcript"][1])
        self.assertEqual(
            saved_payload["transcript"][1]["previous_user_intent_model_inference_used"],
            saved_payload["transcript"][1]["model_intent_inference_used"],
        )
        self.assertNotIn("trace", saved_payload)
        self.assertNotIn("checkpoints", saved_payload)
        self.assertNotIn("terminal_entries", saved_payload)
        self.assertNotIn("scenario", saved_payload)

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
                    json.dumps(
                        {
                            "session_id": "legacy-session",
                            "call_start_time": "2026-01-01 09:30:00",
                            "session_config": {"known_address": "上海市浦东新区张江镇博云路2号"},
                            "collected_slots": {"surname": "张", "address": "上海市浦东新区张江镇博云路2号"},
                        },
                        ensure_ascii=False,
                    ),
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
                "SELECT session_id, username, started_at, ended_at, reviewed_at, review_payload_json "
                "FROM manual_test_reviews WHERE session_id = ?",
                ("legacy-session",),
            ).fetchone()
            new_row = conn.execute(
                "SELECT session_id, username, started_at, ended_at, reviewed_at, review_payload_json "
                "FROM manual_test_reviews WHERE session_id = ?",
                (session_id,),
            ).fetchone()

        self.assertIn("username", columns)
        self.assertEqual(count, 2)
        self.assertEqual(legacy_row[0], "legacy-session")
        self.assertIsNone(legacy_row[1])
        self.assertEqual(legacy_row[2], "2026-01-01 08:00:00")
        self.assertEqual(legacy_row[3], "2026-01-01 08:01:00")
        self.assertEqual(legacy_row[4], "2026-01-01 08:02:00")
        legacy_payload = json.loads(legacy_row[5])
        self.assertEqual(legacy_payload["session_id"], "legacy-session")
        self.assertEqual(legacy_payload["call_start_time"], "2026-01-01 09:30:00")
        self.assertEqual(legacy_payload["session_config"]["known_address"], "上海市浦东新区张江镇博云路2号")
        self.assertEqual(legacy_payload["collected_slots"]["surname"], "张")
        self.assertEqual(new_row[0], session_id)
        self.assertEqual(new_row[1], "tester")
        self.assertRegex(new_row[2], r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$")
        self.assertRegex(new_row[3], r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$")
        self.assertRegex(new_row[4], r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$")

    def test_review_endpoint_rebuilds_corrupt_database_and_persists_new_row(self):
        self.db_path.write_bytes(b"not-a-valid-sqlite-database")

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
        archived = list(self.db_path.parent.glob(f"{self.db_path.name}.malformed_*"))
        self.assertTrue(archived)
        with sqlite3.connect(self.db_path) as conn:
            count = conn.execute("SELECT COUNT(*) FROM manual_test_reviews").fetchone()[0]
        self.assertEqual(count, 1)

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
        self.assertIn("/api/chat/state", app_response.text)
        self.assertIn("/api/chat/messages", app_response.text)
        self.assertIn("/api/chat/history/clear", app_response.text)
        self.assertIn("/api/chat/messages/latest-readers", app_response.text)
        self.assertIn("terminal-turn-trigger", app_response.text)
        self.assertNotIn("/api/session/review/dismiss", app_response.text)
        self.assertIn('id="chat-window"', index_response.text)
        self.assertIn('id="chat-launcher"', index_response.text)
        self.assertIn('id="chat-admin-controls"', index_response.text)

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
