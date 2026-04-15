from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path
from typing import Any


REVIEW_TABLE = "manual_test_reviews"
OPTIONAL_COLUMNS = (
    "session_id",
    "scenario_id",
    "username",
    "status",
    "aborted_reason",
    "is_correct",
    "failed_flow_stage",
    "reviewer_notes",
    "persist_to_db",
    "started_at",
    "ended_at",
    "reviewed_at",
    "review_payload_json",
)


def _table_columns(conn: sqlite3.Connection, table_name: str) -> set[str]:
    rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    return {str(row[1]).strip() for row in rows}


def _load_review_payload(payload_text: str) -> dict[str, Any]:
    if not payload_text:
        return {}
    try:
        payload = json.loads(payload_text)
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _normalize_record(row: sqlite3.Row, available_columns: set[str]) -> dict[str, Any]:
    payload = _load_review_payload(str(row["review_payload_json"]) if "review_payload_json" in available_columns else "")
    review = payload.get("review", {}) if isinstance(payload.get("review", {}), dict) else {}
    username = ""
    if "username" in available_columns and row["username"] is not None:
        username = str(row["username"]).strip()
    if not username:
        username = str(payload.get("username", "")).strip() or str(review.get("username", "")).strip()

    return {
        "session_id": str(row["session_id"]).strip() if "session_id" in available_columns else "",
        "scenario_id": str(row["scenario_id"]).strip() if "scenario_id" in available_columns and row["scenario_id"] is not None else "",
        "username": username,
        "status": str(row["status"]).strip() if "status" in available_columns and row["status"] is not None else "",
        "aborted_reason": (
            str(row["aborted_reason"]).strip()
            if "aborted_reason" in available_columns and row["aborted_reason"] is not None
            else ""
        ),
        "is_correct": row["is_correct"] if "is_correct" in available_columns else None,
        "failed_flow_stage": (
            str(row["failed_flow_stage"]).strip()
            if "failed_flow_stage" in available_columns and row["failed_flow_stage"] is not None
            else ""
        ),
        "reviewer_notes": (
            str(row["reviewer_notes"]).strip()
            if "reviewer_notes" in available_columns and row["reviewer_notes"] is not None
            else ""
        ),
        "persist_to_db": row["persist_to_db"] if "persist_to_db" in available_columns else None,
        "started_at": str(row["started_at"]).strip() if "started_at" in available_columns and row["started_at"] is not None else "",
        "ended_at": str(row["ended_at"]).strip() if "ended_at" in available_columns and row["ended_at"] is not None else "",
        "reviewed_at": str(row["reviewed_at"]).strip() if "reviewed_at" in available_columns and row["reviewed_at"] is not None else "",
        "review_payload": payload,
        "transcript": payload.get("transcript", []) if isinstance(payload.get("transcript", []), list) else [],
        "trace": payload.get("trace", []) if isinstance(payload.get("trace", []), list) else [],
    }


def fetch_manual_test_reviews(
    db_path: str | Path,
    *,
    session_id: str = "",
    limit: int | None = None,
) -> list[dict[str, Any]]:
    resolved_db_path = Path(db_path).expanduser()
    if not resolved_db_path.exists():
        raise FileNotFoundError(f"SQLite 文件不存在: {resolved_db_path}")

    with sqlite3.connect(resolved_db_path) as conn:
        conn.row_factory = sqlite3.Row
        available_columns = _table_columns(conn, REVIEW_TABLE)
        if not available_columns:
            raise ValueError(f"表不存在或不可读取: {REVIEW_TABLE}")

        select_columns = [column for column in OPTIONAL_COLUMNS if column in available_columns]
        order_column = "reviewed_at" if "reviewed_at" in available_columns else "rowid"
        query = f"SELECT {', '.join(select_columns)} FROM {REVIEW_TABLE}"
        params: list[Any] = []
        if session_id.strip():
            query += " WHERE session_id = ?"
            params.append(session_id.strip())
        query += f" ORDER BY {order_column} DESC"
        if limit is not None and limit > 0:
            query += " LIMIT ?"
            params.append(int(limit))

        rows = conn.execute(query, params).fetchall()
        return [_normalize_record(row, available_columns) for row in rows]


def main() -> None:
    parser = argparse.ArgumentParser(description="从 manual_test_reviews SQLite 拉取记录")
    parser.add_argument("db_path", help="SQLite 文件路径")
    parser.add_argument("--session-id", default="", help="只拉取指定 session_id")
    parser.add_argument("--limit", type=int, default=0, help="返回的最大记录数，0 表示不限制")
    args = parser.parse_args()

    records = fetch_manual_test_reviews(
        args.db_path,
        session_id=args.session_id,
        limit=args.limit or None,
    )
    print(json.dumps(records, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
