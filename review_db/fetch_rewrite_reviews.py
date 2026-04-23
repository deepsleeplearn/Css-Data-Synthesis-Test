from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path
from typing import Any


REWRITE_REVIEW_TABLE = "rewrite_reviews"
OPTIONAL_COLUMNS = (
    "record_id",
    "username",
    "source",
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
    record = payload.get("record", {}) if isinstance(payload.get("record", {}), dict) else {}
    return {
        "record_id": str(row["record_id"]).strip() if "record_id" in available_columns and row["record_id"] is not None else "",
        "username": str(row["username"]).strip() if "username" in available_columns and row["username"] is not None else "",
        "source": str(row["source"]).strip() if "source" in available_columns and row["source"] is not None else "",
        "reviewed_at": str(row["reviewed_at"]).strip() if "reviewed_at" in available_columns and row["reviewed_at"] is not None else "",
        "review_payload": payload,
        "record": record,
        "conversations": record.get("conversations", []) if isinstance(record.get("conversations", []), list) else [],
        "rewrited": record.get("rewrited", []) if isinstance(record.get("rewrited", []), list) else [],
    }


def fetch_rewrite_reviews(
    db_path: str | Path,
    *,
    record_id: str = "",
    username: str = "",
    source: str = "",
    limit: int | None = None,
) -> list[dict[str, Any]]:
    resolved_db_path = Path(db_path).expanduser()
    if not resolved_db_path.exists():
        raise FileNotFoundError(f"SQLite 文件不存在: {resolved_db_path}")

    with sqlite3.connect(resolved_db_path) as conn:
        conn.row_factory = sqlite3.Row
        available_columns = _table_columns(conn, REWRITE_REVIEW_TABLE)
        if not available_columns:
            raise ValueError(f"表不存在或不可读取: {REWRITE_REVIEW_TABLE}")

        select_columns = [column for column in OPTIONAL_COLUMNS if column in available_columns]
        order_column = "reviewed_at" if "reviewed_at" in available_columns else "rowid"
        query = f"SELECT {', '.join(select_columns)} FROM {REWRITE_REVIEW_TABLE}"
        conditions: list[str] = []
        params: list[Any] = []
        if record_id.strip():
            conditions.append("record_id = ?")
            params.append(record_id.strip())
        if username.strip():
            conditions.append("username = ?")
            params.append(username.strip())
        if source.strip():
            conditions.append("source = ?")
            params.append(source.strip())
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += f" ORDER BY {order_column} DESC"
        if limit is not None and limit > 0:
            query += " LIMIT ?"
            params.append(int(limit))

        rows = conn.execute(query, params).fetchall()
        return [_normalize_record(row, available_columns) for row in rows]


def _stringify_value(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value).strip()


def _format_rewrited_line(item: dict[str, Any], index: int) -> str:
    role = str(item.get("from", "")).strip() or "系统"
    rendered_value = _stringify_value(item.get("value")) or "-"
    return f"[{index}] {role}: {rendered_value}"


def _format_conversation_line(item: dict[str, Any], index: int) -> str:
    role = str(item.get("role", "")).strip() or "系统"
    content = _stringify_value(item.get("content")) or "-"
    return f"[{index}] {role}: {content}"


def format_rewrite_review_record_as_cli(record: dict[str, Any]) -> str:
    payload_record = record.get("record", {}) if isinstance(record.get("record"), dict) else {}
    lines = [
        f"Record ID: {str(record.get('record_id', '')).strip() or '-'}",
        f"评审账号: {str(record.get('username', '')).strip() or '-'}",
        f"来源: {str(record.get('source', '')).strip() or '-'}",
        f"评审时间: {str(record.get('reviewed_at', '')).strip() or '-'}",
    ]
    session_id = str(payload_record.get("session_id", "")).strip()
    auto_mode_id = str(payload_record.get("auto_mode_id", "")).strip()
    if session_id:
        lines.append(f"Session ID: {session_id}")
    if auto_mode_id:
        lines.append(f"Auto Mode ID: {auto_mode_id}")
    lines.append("")

    rewrited = record.get("rewrited", [])
    conversations = record.get("conversations", [])
    if isinstance(rewrited, list) and rewrited:
        lines.append("rewrited:")
        lines.extend(
            _format_rewrited_line(item, index)
            for index, item in enumerate(rewrited, start=1)
            if isinstance(item, dict)
        )
    elif isinstance(conversations, list) and conversations:
        lines.append("conversations:")
        lines.extend(
            _format_conversation_line(item, index)
            for index, item in enumerate(conversations, start=1)
            if isinstance(item, dict)
        )
    else:
        lines.append("[无可显示的改写记录]")
    return "\n".join(lines)


def format_rewrite_review_records(
    records: list[dict[str, Any]],
    *,
    output_format: str = "json",
) -> str:
    if output_format == "cli":
        rendered_records: list[str] = []
        show_separator = len(records) > 1
        for index, record in enumerate(records, start=1):
            content = format_rewrite_review_record_as_cli(record)
            if show_separator:
                content = f"===== 记录 {index}/{len(records)} =====\n{content}"
            rendered_records.append(content)
        return "\n\n".join(rendered_records)
    return json.dumps(records, ensure_ascii=False, indent=2)


def main() -> None:
    parser = argparse.ArgumentParser(description="从 rewrite_reviews SQLite 拉取改写评审记录")
    parser.add_argument(
        "--db_path",
        default="./outputs/frontend_rewrite_review.sqlite3",
        help="SQLite 文件路径",
    )
    parser.add_argument("--record-id", "-r", default="", help="只拉取指定 record_id")
    parser.add_argument("--username", default="", help="只拉取指定评审账号")
    parser.add_argument("--source", default="", help="按来源过滤（manual_test / auto_mode 等）")
    parser.add_argument("--limit", type=int, default=0, help="返回的最大记录数，0 表示不限制")
    parser.add_argument(
        "--format",
        "-f",
        choices=("json", "cli"),
        default="json",
        help="输出格式：json 为结构化结果，cli 为可读文本",
    )
    args = parser.parse_args()

    records = fetch_rewrite_reviews(
        args.db_path,
        record_id=args.record_id,
        username=args.username,
        source=args.source,
        limit=args.limit or None,
    )
    print(
        format_rewrite_review_records(
            records,
            output_format=args.format,
        )
    )


if __name__ == "__main__":
    main()
