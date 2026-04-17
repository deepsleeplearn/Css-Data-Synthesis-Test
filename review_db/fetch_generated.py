from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path
from typing import Any

from multi_agent_data_synthesis.schemas import SERVICE_SPEAKER, display_speaker, normalize_speaker


GENERATED_TABLE = "generated_dialogues"
OPTIONAL_COLUMNS = (
    "dialogue_id",
    "scenario_id",
    "status",
    "rounds_used",
    "missing_slots_json",
    "collected_slots_json",
    "generated_at",
    "dialogue_payload_json",
)


def _table_columns(conn: sqlite3.Connection, table_name: str) -> set[str]:
    rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    return {str(row[1]).strip() for row in rows}


def _load_payload(payload_text: str) -> dict[str, Any]:
    if not payload_text:
        return {}
    try:
        payload = json.loads(payload_text)
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _normalize_record(row: sqlite3.Row, available_columns: set[str]) -> dict[str, Any]:
    payload = _load_payload(
        str(row["dialogue_payload_json"]) if "dialogue_payload_json" in available_columns else ""
    )

    # missing_slots / collected_slots: prefer dedicated columns, fall back to payload
    missing_slots: list[Any] = []
    if "missing_slots_json" in available_columns and row["missing_slots_json"]:
        try:
            missing_slots = json.loads(str(row["missing_slots_json"]))
        except json.JSONDecodeError:
            pass
    if not missing_slots:
        missing_slots = payload.get("missing_slots", [])

    collected_slots: dict[str, Any] = {}
    if "collected_slots_json" in available_columns and row["collected_slots_json"]:
        try:
            collected_slots = json.loads(str(row["collected_slots_json"]))
        except json.JSONDecodeError:
            pass
    if not collected_slots:
        collected_slots = payload.get("collected_slots", {})

    # Inject back into payload so format helpers can read them
    if isinstance(payload, dict):
        payload.setdefault("missing_slots", missing_slots)
        payload.setdefault("collected_slots", collected_slots)

    return {
        # Use "session_id" key to stay compatible with fetch_reviews output format
        "session_id": str(row["dialogue_id"]).strip() if "dialogue_id" in available_columns else "",
        "dialogue_id": str(row["dialogue_id"]).strip() if "dialogue_id" in available_columns else "",
        "scenario_id": (
            str(row["scenario_id"]).strip()
            if "scenario_id" in available_columns and row["scenario_id"] is not None
            else ""
        ),
        "status": (
            str(row["status"]).strip()
            if "status" in available_columns and row["status"] is not None
            else ""
        ),
        "rounds_used": row["rounds_used"] if "rounds_used" in available_columns else None,
        "generated_at": (
            str(row["generated_at"]).strip()
            if "generated_at" in available_columns and row["generated_at"] is not None
            else ""
        ),
        "missing_slots": missing_slots if isinstance(missing_slots, list) else [],
        "collected_slots": collected_slots if isinstance(collected_slots, dict) else {},
        "dialogue_payload": payload,
        # Aliases kept for compatibility with format helpers that expect review_payload
        "review_payload": payload,
        "transcript": payload.get("transcript", []) if isinstance(payload.get("transcript", []), list) else [],
        "trace": payload.get("trace", []) if isinstance(payload.get("trace", []), list) else [],
    }


def fetch_generated_dialogues(
    db_path: str | Path,
    *,
    dialogue_id: str = "",
    scenario_id: str = "",
    status: str = "",
    limit: int | None = None,
) -> list[dict[str, Any]]:
    resolved_db_path = Path(db_path).expanduser()
    if not resolved_db_path.exists():
        raise FileNotFoundError(f"SQLite 文件不存在: {resolved_db_path}")

    with sqlite3.connect(resolved_db_path) as conn:
        conn.row_factory = sqlite3.Row
        available_columns = _table_columns(conn, GENERATED_TABLE)
        if not available_columns:
            raise ValueError(f"表不存在或不可读取: {GENERATED_TABLE}")

        select_columns = [col for col in OPTIONAL_COLUMNS if col in available_columns]
        order_column = "generated_at" if "generated_at" in available_columns else "rowid"
        query = f"SELECT {', '.join(select_columns)} FROM {GENERATED_TABLE}"

        conditions: list[str] = []
        params: list[Any] = []
        if dialogue_id.strip():
            conditions.append("dialogue_id = ?")
            params.append(dialogue_id.strip())
        if scenario_id.strip():
            conditions.append("scenario_id = ?")
            params.append(scenario_id.strip())
        if status.strip():
            conditions.append("status = ?")
            params.append(status.strip())
        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += f" ORDER BY {order_column} DESC"
        if limit is not None and limit > 0:
            query += " LIMIT ?"
            params.append(int(limit))

        rows = conn.execute(query, params).fetchall()
        return [_normalize_record(row, available_columns) for row in rows]


# ── CLI formatting helpers (mirrors fetch_reviews.py) ────────────────────────

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


def format_generated_record_as_cli(record: dict[str, Any], *, show_final_slots: bool = False) -> str:
    payload = record.get("dialogue_payload", {})
    scenario = payload.get("scenario", {}) if isinstance(payload, dict) else {}
    product = scenario.get("product", {}) if isinstance(scenario, dict) else {}
    request = scenario.get("request", {}) if isinstance(scenario, dict) else {}

    product_line = " ".join(
        part
        for part in (
            str(product.get("brand", "")).strip(),
            str(product.get("category", "")).strip(),
            str(product.get("model", "")).strip(),
        )
        if part
    ) or "-"
    scenario_id = (
        str(record.get("scenario_id", "")).strip()
        or str(scenario.get("scenario_id", "")).strip()
        or "-"
    )
    request_type = str(request.get("request_type", "")).strip() or "-"
    rounds_used = record.get("rounds_used")

    lines = [
        f"Dialogue ID: {str(record.get('dialogue_id', '')).strip() or '-'}",
        f"场景: {scenario_id}",
        f"产品: {product_line}",
        f"诉求: {request_type}",
        f"生成时间: {str(record.get('generated_at', '')).strip() or '-'}",
    ]
    if rounds_used not in (None, ""):
        lines.append(f"实际轮次: {rounds_used}")
    lines.append("")

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
    if status == "completed":
        lines.append("--- 对话已完成 ---")
    elif status == "transferred":
        lines.append("--- 已转接人工，对话结束 ---")
    elif status == "incomplete":
        lines.append("--- 未完成（轮次耗尽或中断）---")

    if show_final_slots and isinstance(payload, dict):
        lines.extend(_final_slots_lines(payload))

    return "\n".join(lines)


def format_generated_records(
    records: list[dict[str, Any]],
    *,
    output_format: str = "json",
    show_final_slots: bool = False,
) -> str:
    if output_format == "cli":
        rendered: list[str] = []
        show_separator = len(records) > 1
        for index, record in enumerate(records, start=1):
            content = format_generated_record_as_cli(record, show_final_slots=show_final_slots)
            if show_separator:
                content = f"===== 记录 {index}/{len(records)} =====\n{content}"
            rendered.append(content)
        return "\n\n".join(rendered)
    return json.dumps(records, ensure_ascii=False, indent=2)


def main() -> None:
    """
    Example: python -m review_db.fetch_generated -s <dialogue_id> -f cli
    """
    parser = argparse.ArgumentParser(description="从 generated_dialogues SQLite 拉取自动生成对话记录")
    parser.add_argument(
        "--db_path",
        default="./outputs/generated_dialogues.sqlite3",
        help="SQLite 文件路径",
    )
    parser.add_argument("--dialogue-id", "-s", default="", help="只拉取指定 dialogue_id")
    parser.add_argument("--scenario-id", default="", help="只拉取指定 scenario_id")
    parser.add_argument("--status", default="", help="按状态过滤（completed / incomplete / transferred）")
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
        help="仅在 cli 输出时，额外打印最终槽位信息",
    )
    args = parser.parse_args()

    records = fetch_generated_dialogues(
        args.db_path,
        dialogue_id=args.dialogue_id,
        scenario_id=args.scenario_id,
        status=args.status,
        limit=args.limit or None,
    )
    print(
        format_generated_records(
            records,
            output_format=args.format,
            show_final_slots=bool(args.show_final_slots),
        )
    )


if __name__ == "__main__":
    main()
