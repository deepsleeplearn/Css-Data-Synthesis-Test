from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path
from typing import Any

from css_data_synthesis_test.schemas import SERVICE_SPEAKER, display_speaker, normalize_speaker


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


def _cli_round_label(turn: dict[str, Any]) -> str:
    round_label = str(turn.get("round_label", "")).strip()
    if round_label:
        return round_label

    round_index = str(turn.get("round_index", "")).strip()
    if not round_index:
        return "?"

    used_model_intent_inference = bool(
        turn.get("previous_user_intent_model_inference_used", turn.get("model_intent_inference_used", False))
    )
    speaker = normalize_speaker(str(turn.get("speaker", "")).strip())
    if speaker == SERVICE_SPEAKER and used_model_intent_inference:
        return f"{round_index}*"
    return round_index


def _known_address_line(payload: dict[str, Any]) -> str:
    session_config = payload.get("session_config", {})
    if not isinstance(session_config, dict):
        return "已知地址: 未设置"

    known_address = str(session_config.get("known_address", "")).strip()
    if not known_address:
        return "已知地址: 未设置"
    return f"已知地址: {known_address}"


def _final_slots_lines(payload: dict[str, Any]) -> list[str]:
    collected_slots = payload.get("collected_slots", {})
    if not isinstance(collected_slots, dict) or not collected_slots:
        return []

    lines = [
        "",
        f"最终槽位: {json.dumps(collected_slots, ensure_ascii=False, indent=2)}",
    ]
    missing_slots = payload.get("missing_slots", [])
    if isinstance(missing_slots, list) and missing_slots:
        lines.append(f"仍缺失槽位: {json.dumps(missing_slots, ensure_ascii=False)}")
    return lines


def format_review_record_as_cli(record: dict[str, Any], *, show_final_slots: bool = False) -> str:
    payload = record.get("review_payload", {})
    scenario = payload.get("scenario", {}) if isinstance(payload, dict) else {}
    product = scenario.get("product", {}) if isinstance(scenario, dict) else {}
    request = scenario.get("request", {}) if isinstance(scenario, dict) else {}
    review = payload.get("review", {}) if isinstance(payload, dict) else {}

    product_line = " ".join(
        part
        for part in (
            str(product.get("brand", "")).strip(),
            str(product.get("category", "")).strip(),
            str(product.get("model", "")).strip(),
        )
        if part
    ) or "-"
    scenario_id = str(record.get("scenario_id", "")).strip() or str(scenario.get("scenario_id", "")).strip() or "-"
    request_type = str(request.get("request_type", "")).strip() or "-"
    rounds_limit = payload.get("rounds_limit")

    lines = [
        f"Session ID: {str(record.get('session_id', '')).strip() or '-'}",
        f"评审账号: {str(record.get('username', '')).strip() or '-'}",
        f"场景: {scenario_id}",
        f"产品: {product_line}",
        f"诉求: {request_type}",
    ]
    if rounds_limit not in (None, ""):
        lines.append(f"轮次上限: {rounds_limit}")
    lines.extend(
        [
            "输出文件: 未启用",
            "可用命令: /help, /slots, /state, /quit",
            _known_address_line(payload if isinstance(payload, dict) else {}),
            "",
        ]
    )

    transcript = record.get("transcript", [])
    if isinstance(transcript, list) and transcript:
        for turn in transcript:
            if not isinstance(turn, dict):
                continue
            speaker = display_speaker(str(turn.get("speaker", "")).strip())
            text = str(turn.get("text", "")).strip()
            lines.append(f"[{_cli_round_label(turn)}] {speaker}: {text}")
    else:
        lines.append("[无对话内容]")

    status = str(record.get("status", "")).strip()
    aborted_reason = str(record.get("aborted_reason", "")).strip()
    if status == "completed":
        lines.append("--- 会话已完成 ---")
    elif status == "transferred":
        lines.append("--- 已转接人工，会话结束 ---")
    elif status == "incomplete" or aborted_reason == "round_limit_reached":
        lines.append("--- 已达到最大轮次，会话结束 ---")
    elif status == "aborted":
        lines.append("会话已结束。")

    if isinstance(review, dict) and review:
        review_state = review.get("is_correct")
        if review_state is True:
            correctness_text = "正确"
        elif review_state is False:
            correctness_text = "错误"
        else:
            correctness_text = "-"

        lines.extend(
            [
                "",
                f"评审结果: {correctness_text}",
                f"出错流程: {str(review.get('failed_flow_stage', '')).strip() or '-'}",
                f"评审备注: {str(review.get('notes', '')).strip() or '-'}",
            ]
        )

    if show_final_slots and isinstance(payload, dict):
        lines.extend(_final_slots_lines(payload))

    return "\n".join(lines)


def format_review_records(
    records: list[dict[str, Any]],
    *,
    output_format: str = "json",
    show_final_slots: bool = False,
) -> str:
    if output_format == "cli":
        rendered_records: list[str] = []
        show_separator = len(records) > 1
        for index, record in enumerate(records, start=1):
            content = format_review_record_as_cli(record, show_final_slots=show_final_slots)
            if show_separator:
                content = f"===== 记录 {index}/{len(records)} =====\n{content}"
            rendered_records.append(content)
        return "\n\n".join(rendered_records)
    return json.dumps(records, ensure_ascii=False, indent=2)


def main() -> None:
    """
    Example: python -m review_db.fetch_reviews -s 6d237d90-053a-4ffa-8e6e-993a11b4032b -f cli
    """
    parser = argparse.ArgumentParser(description="从 manual_test_reviews SQLite 拉取记录")
    parser.add_argument("--db_path", default="./outputs/frontend_manual_test.sqlite3", help="SQLite 文件路径")
    parser.add_argument("--session-id", "-s", default="", help="只拉取指定 session_id")
    parser.add_argument("--limit", type=int, default=0, help="返回的最大记录数，0 表示不限制")
    parser.add_argument(
        "--format",
        "-f",
        choices=("json", "cli"),
        default="json",
        help="输出格式：json 为结构化结果，cli 为还原终端样式输出",
    )
    parser.add_argument(
        "--show-final-slots",
        action="store_true",
        help="仅在 cli 输出时，额外打印会话结束时的最终槽位信息",
    )
    args = parser.parse_args()

    records = fetch_manual_test_reviews(
        args.db_path,
        session_id=args.session_id,
        limit=args.limit or None,
    )
    print(
        format_review_records(
            records,
            output_format=args.format,
            show_final_slots=bool(args.show_final_slots),
        )
    )


if __name__ == "__main__":
    main()
