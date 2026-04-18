from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

from css_data_synthesis_test.schemas import DialogueSample

GENERATED_DIALOGUES_TABLE = "generated_dialogues"


def write_jsonl(samples: list[DialogueSample], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("a", encoding="utf-8") as handle:
        for sample in samples:
            handle.write(json.dumps(sample.to_dict(), ensure_ascii=False) + "\n")


def write_json(samples: list[DialogueSample], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps([sample.to_dict() for sample in samples], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def write_sqlite(samples: list[DialogueSample], db_path: Path) -> int:
    """将生成的对话样本持久化到 SQLite，返回实际写入的记录数。"""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    generated_at = datetime.now(timezone.utc).isoformat()
    written = 0
    with sqlite3.connect(db_path, timeout=10.0) as conn:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA busy_timeout=10000")
        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {GENERATED_DIALOGUES_TABLE} (
                dialogue_id TEXT PRIMARY KEY,
                scenario_id TEXT NOT NULL,
                status TEXT NOT NULL,
                rounds_used INTEGER NOT NULL,
                missing_slots_json TEXT NOT NULL,
                collected_slots_json TEXT NOT NULL,
                generated_at TEXT NOT NULL,
                dialogue_payload_json TEXT NOT NULL
            )
            """
        )
        for sample in samples:
            dialogue_id = str(uuid.uuid4())
            payload = sample.to_dict()
            conn.execute(
                f"""
                INSERT INTO {GENERATED_DIALOGUES_TABLE} (
                    dialogue_id,
                    scenario_id,
                    status,
                    rounds_used,
                    missing_slots_json,
                    collected_slots_json,
                    generated_at,
                    dialogue_payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    dialogue_id,
                    sample.scenario_id,
                    sample.status,
                    sample.rounds_used,
                    json.dumps(sample.missing_slots, ensure_ascii=False),
                    json.dumps(sample.collected_slots, ensure_ascii=False),
                    generated_at,
                    json.dumps(payload, ensure_ascii=False),
                ),
            )
            written += 1
        conn.commit()
    return written
