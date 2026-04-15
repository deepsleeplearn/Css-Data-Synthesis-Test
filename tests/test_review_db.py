from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from review_db.fetch_reviews import fetch_manual_test_reviews


class ReviewDbFetchTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "reviews.sqlite3"

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_fetch_reviews_supports_legacy_database_without_username_column(self):
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
                    "legacy-case",
                    "aborted",
                    "user_exit",
                    0,
                    "address_collection",
                    "legacy notes",
                    1,
                    "2026-01-01T00:00:00+00:00",
                    "2026-01-01T00:01:00+00:00",
                    "2026-01-01T00:02:00+00:00",
                    json.dumps(
                        {
                            "session_id": "legacy-session",
                            "review": {"notes": "legacy notes"},
                            "transcript": [],
                            "trace": [],
                        },
                        ensure_ascii=False,
                    ),
                ),
            )
            conn.commit()

        records = fetch_manual_test_reviews(self.db_path)

        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["session_id"], "legacy-session")
        self.assertEqual(records[0]["username"], "")
        self.assertEqual(records[0]["scenario_id"], "legacy-case")

    def test_fetch_reviews_returns_username_and_transcript_from_newer_database(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE manual_test_reviews (
                    session_id TEXT PRIMARY KEY,
                    scenario_id TEXT NOT NULL,
                    username TEXT,
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
                    username,
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
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "new-session",
                    "new-case",
                    "tester",
                    "completed",
                    "",
                    1,
                    "",
                    "",
                    1,
                    "2026-02-01T00:00:00+00:00",
                    "2026-02-01T00:01:00+00:00",
                    "2026-02-01T00:02:00+00:00",
                    json.dumps(
                        {
                            "session_id": "new-session",
                            "username": "tester",
                            "transcript": [
                                {
                                    "speaker": "客服",
                                    "text": "好的",
                                    "previous_user_intent_model_inference_used": False,
                                }
                            ],
                            "trace": [{"previous_user_intent_model_inference_used": False}],
                        },
                        ensure_ascii=False,
                    ),
                ),
            )
            conn.commit()

        records = fetch_manual_test_reviews(self.db_path, session_id="new-session")

        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["username"], "tester")
        self.assertEqual(records[0]["transcript"][0]["speaker"], "客服")
        self.assertFalse(records[0]["trace"][0]["previous_user_intent_model_inference_used"])


if __name__ == "__main__":
    unittest.main()
