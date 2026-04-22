from __future__ import annotations

import json
import sqlite3
import sys
import threading
import traceback
import uuid
import argparse
import hashlib
import os
import re
import secrets
import copy
import subprocess
import atexit
import time
from datetime import datetime, timedelta, timezone
from dataclasses import asdict, replace
from pathlib import Path
from typing import Any

import requests
from fastapi import Cookie, Depends, FastAPI, HTTPException, Response, status
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

try:
    import redis
except ImportError:  # pragma: no cover
    redis = None

# Add the project root to sys.path to ensure css_data_synthesis_test can be imported.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from css_data_synthesis_test.address_utils import extract_address_components
    from css_data_synthesis_test.agents import ServiceAgent
    from css_data_synthesis_test.cli import (
        _hydrate_manual_test_scenario_locally,
        _manual_test_requires_generated_hidden_settings,
        _resolve_interactive_max_rounds,
    )
    from css_data_synthesis_test.config import load_config
    from css_data_synthesis_test.function_call import (
        build_address_model_observation,
    )
    from css_data_synthesis_test.hidden_settings_tool import (
        HiddenSettingsTool,
        generate_local_customer_address,
    )
    from css_data_synthesis_test.llm import OpenAIChatClient
    from css_data_synthesis_test.manual_test import (
        MANUAL_TEST_EXIT_COMMANDS,
        MANUAL_TEST_HELP_COMMAND,
        MANUAL_TEST_SHOW_SLOTS_COMMAND,
        MANUAL_TEST_SHOW_STATE_COMMAND,
        _manual_command_token,
        _sanitize_manual_user_text,
    )
    from css_data_synthesis_test.punctuation_service import (
        configure_punctuation_service,
        get_punctuation_service,
        punctuate_text,
    )
    from css_data_synthesis_test.product_routing import (
        PROMPT_BRAND_OR_SERIES,
        PROMPT_CAPACITY,
        PROMPT_PROPERTY_YEAR,
        PROMPT_PURCHASE_OR_PROPERTY,
        PROMPT_USAGE_PURPOSE,
        PROMPT_USAGE_SCENE,
        default_unknown_product_routing_answer_key,
        ensure_product_routing_plan,
    )
    from css_data_synthesis_test.scenario_factory import ScenarioFactory
    from css_data_synthesis_test.schemas import (
        SERVICE_SPEAKER,
        SUPPLEMENTARY_COLLECTED_SLOTS,
        USER_SPEAKER,
        DialogueTurn,
        Scenario,
        build_display_transcript,
        effective_required_slots,
    )
    from css_data_synthesis_test.service_policy import (
        ServiceDialoguePolicy,
        ServicePolicyResult,
        ServiceRuntimeState,
    )
except ImportError as exc:  # pragma: no cover
    print(f"Error: Could not import core modules. {exc}")
    print(f"sys.path: {sys.path}")
    sys.exit(1)

app = FastAPI(title="Multi-Agent Data Synthesis Frontend")
AUTH_SESSION_COOKIE = "frontend_auth_session"
AUTH_SESSION_TTL = timedelta(hours=12)
DEFAULT_REGISTERED_ACCOUNTS_FILE = PROJECT_ROOT / "frontend" / "registered_accounts.local.json"
DISPLAY_TIMEZONE = timezone(timedelta(hours=8))
DISPLAY_TIME_FORMAT = "%Y-%m-%d %H:%M:%S"

try:
    config = replace(load_config(), hidden_settings_store=None)
    llm_client = OpenAIChatClient(config)
    factory = ScenarioFactory(
        installation_request_probability=config.installation_request_probability,
    )
except Exception as exc:  # pragma: no cover
    print(f"Error during initialization: {exc}")
    traceback.print_exc()

sessions: dict[str, dict[str, Any]] = {}
auth_sessions: dict[str, dict[str, Any]] = {}
SESSION_REVIEW_DB_PATH = PROJECT_ROOT / "outputs" / "frontend_manual_test.sqlite3"
SESSION_REVIEW_DB_LOCK = threading.RLock()
_SESSION_REVIEW_DB_STATE_PATH: Path | None = None
_SESSION_REVIEW_DB_SCHEMA_READY = False
_SESSION_REVIEW_DB_NORMALIZED = False
SESSION_REDIS_URL = os.getenv("FRONTEND_SESSION_REDIS_URL", "").strip()
SESSION_REDIS_TTL_SECONDS = int(os.getenv("FRONTEND_SESSION_REDIS_TTL_SECONDS", "43200") or "43200")
CHAT_STORAGE_PATH = PROJECT_ROOT / "outputs" / "frontend_chat_messages.json"
CHAT_RECALL_STORAGE_PATH = PROJECT_ROOT / "outputs" / "frontend_chat_message_recalls.json"
CHAT_STORAGE_LOCK = threading.RLock()
CHAT_PRESENCE_TTL = timedelta(seconds=int(os.getenv("FRONTEND_CHAT_PRESENCE_TTL_SECONDS", "30") or "30"))
LOCAL_PUNCT_API_PORT = int(os.getenv("LOCAL_PUNCT_API_PORT", "8797") or "8797")
LOCAL_PUNCT_API_HOST = os.getenv("LOCAL_PUNCT_API_HOST", "127.0.0.1").strip() or "127.0.0.1"
LOCAL_PUNCT_API_TIMEOUT_SECONDS = float(os.getenv("LOCAL_PUNCT_API_TIMEOUT_SECONDS", "10") or "10")
LOCAL_PUNCT_API_URL = f"http://{LOCAL_PUNCT_API_HOST}:{LOCAL_PUNCT_API_PORT}/predict"
_local_punctuation_api_process: subprocess.Popen[str] | None = None
chat_state: dict[str, Any] = {
    "messages": [],
    "last_message_id": 0,
    "recalled_message_ids": [],
    "snapshot_revision": 0,
}
chat_state_loaded = False
FLOW_REVIEW_OPTIONS = [
    {"key": "opening_confirmation", "label": "开场确认"},
    {"key": "issue_collection", "label": "故障/诉求采集"},
    {"key": "surname_collection", "label": "姓氏采集"},
    {"key": "contact_confirmation", "label": "联系方式确认"},
    {"key": "phone_input", "label": "号码补录/确认"},
    {"key": "address_collection", "label": "地址采集"},
    {"key": "address_confirmation", "label": "地址确认"},
    {"key": "product_arrival_confirmation", "label": "到货确认"},
    {"key": "product_routing", "label": "产品归属判断"},
    {"key": "product_model_collection", "label": "产品型号采集"},
    {"key": "closing", "label": "结束收尾"},
    {"key": "other", "label": "其他"},
]


def _build_service_policy():
    service_agent = ServiceAgent(
        llm_client,
        model=config.service_agent_model,
        temperature=config.default_temperature,
        ok_prefix_probability=config.service_ok_prefix_probability,
        product_routing_enabled=config.product_routing_enabled,
        product_routing_apply_probability=config.product_routing_apply_probability,
    )
    return service_agent.policy


def _session_redis_client():
    if not SESSION_REDIS_URL or redis is None:
        return None
    try:
        return redis.Redis.from_url(SESSION_REDIS_URL, decode_responses=True)
    except Exception:
        return None


def _session_redis_key(session_id: str) -> str:
    return f"frontend:session:{session_id}"


class StartSessionRequest(BaseModel):
    scenario_id: str = ""
    scenario_index: int = 0
    auto_generate_hidden_settings: bool = False
    known_address: str = ""
    call_start_time: str = ""
    use_session_start_time_as_call_start_time: bool = False
    max_rounds: int | None = None
    persist_to_db: bool = False


class RespondRequest(BaseModel):
    session_id: str
    text: str


class PunctuationRequest(BaseModel):
    text: str


class RewindSessionRequest(BaseModel):
    session_id: str
    clicked_user_round_index: int = 0
    restore_checkpoint_index: int | None = None
    target_round_index: int | None = None


class AddressIeDisplayRequest(BaseModel):
    session_id: str
    round_index: int
    enabled: bool = True


class LoginRequest(BaseModel):
    username: str
    password: str


class ReviewSessionRequest(BaseModel):
    session_id: str
    is_correct: bool
    failed_flow_stage: str = ""
    notes: str = ""
    persist_to_db: bool = False


class ChatMessageRequest(BaseModel):
    text: str
    reply_to_message_id: int | None = None


class ChatMessageUpdateRequest(BaseModel):
    text: str


def _empty_chat_state() -> dict[str, Any]:
    return {
        "messages": [],
        "last_message_id": 0,
        "recalled_message_ids": [],
        "snapshot_revision": 0,
    }


def _scenario_file() -> Path:
    return config.data_dir / "seed_scenarios.json"


def _registered_accounts_file() -> Path:
    configured = os.getenv("FRONTEND_REGISTERED_ACCOUNTS_FILE", "").strip()
    if configured:
        return Path(configured).expanduser()
    return DEFAULT_REGISTERED_ACCOUNTS_FILE


def _current_display_timestamp() -> str:
    return datetime.now(DISPLAY_TIMEZONE).strftime(DISPLAY_TIME_FORMAT)


def _stop_local_punctuation_api() -> None:
    global _local_punctuation_api_process
    process = _local_punctuation_api_process
    if process is None:
        return
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=5)
        except Exception:
            process.kill()
    _local_punctuation_api_process = None


atexit.register(_stop_local_punctuation_api)


def _wait_for_local_punctuation_api(timeout_seconds: float = 15.0) -> None:
    deadline = time.time() + max(timeout_seconds, 1.0)
    last_error = ""
    while time.time() < deadline:
        try:
            response = requests.get(
                f"http://{LOCAL_PUNCT_API_HOST}:{LOCAL_PUNCT_API_PORT}/health",
                timeout=1.5,
            )
            if response.status_code < 400:
                return
            last_error = f"status={response.status_code}, body={response.text[:200]}"
        except Exception as exc:
            last_error = str(exc)
        time.sleep(0.25)
    raise RuntimeError(f"local punctuation api not ready: {last_error}")


def _start_local_punctuation_api(*, model_dir: str = "") -> None:
    global _local_punctuation_api_process
    if _local_punctuation_api_process is not None and _local_punctuation_api_process.poll() is None:
        return
    env = os.environ.copy()
    if model_dir:
        env["PUNCT_MODEL_DIR"] = model_dir
    command = [
        sys.executable,
        "-m",
        "uvicorn",
        "css_data_synthesis_test.local_punctuation_api:app",
        "--host",
        LOCAL_PUNCT_API_HOST,
        "--port",
        str(LOCAL_PUNCT_API_PORT),
    ]
    _local_punctuation_api_process = subprocess.Popen(
        command,
        cwd=str(PROJECT_ROOT),
        env=env,
        text=True,
    )
    _wait_for_local_punctuation_api()
    print(
        "[punctuation] local api started url=%s pid=%s"
        % (LOCAL_PUNCT_API_URL, _local_punctuation_api_process.pid if _local_punctuation_api_process else "")
    )


def _punctuate_via_local_api(text: str) -> str:
    response = requests.post(
        LOCAL_PUNCT_API_URL,
        json={"text": text},
        timeout=LOCAL_PUNCT_API_TIMEOUT_SECONDS,
    )
    if response.status_code >= 400:
        raise RuntimeError(f"status={response.status_code}, body={response.text[:300]}")
    payload = response.json()
    punctuated_text = str(payload.get("punctuated_text") or "").strip()
    if punctuated_text:
        return punctuated_text
    raise RuntimeError(f"empty local punctuation response: {response.text[:300]}")


def _punctuate_user_text_for_session(text: str) -> str:
    normalized = str(text or "").strip()
    if not normalized:
        return ""
    try:
        punct_service = get_punctuation_service()
        if punct_service.backend == "local":
            punctuated = _punctuate_via_local_api(normalized)
        else:
            punctuated = punctuate_text(normalized)
        final_text = str(punctuated or normalized).strip()
        print(
            "[punctuation] backend=%s input=%r output=%r changed=%s"
            % (
                punct_service.backend,
                normalized,
                final_text,
                str(final_text != normalized).lower(),
            )
        )
        return final_text
    except Exception as exc:  # pragma: no cover
        print(f"[punctuation] failed input={normalized!r} error={exc!r}")
        print(f"[punctuation] fallback output={normalized!r}")
        return normalized


def _normalize_display_timestamp(value: str) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        return ""
    try:
        return datetime.strptime(normalized, DISPLAY_TIME_FORMAT).strftime(DISPLAY_TIME_FORMAT)
    except ValueError:
        pass

    iso_candidate = normalized.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(iso_candidate)
    except ValueError:
        return normalized
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=DISPLAY_TIMEZONE)
    else:
        parsed = parsed.astimezone(DISPLAY_TIMEZONE)
    return parsed.strftime(DISPLAY_TIME_FORMAT)


def _normalize_manual_call_start_time(value: str) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        return ""
    try:
        return datetime.strptime(normalized, DISPLAY_TIME_FORMAT).strftime(DISPLAY_TIME_FORMAT)
    except ValueError as exc:
        raise ValueError("通话开始时间格式必须为 YYYY-MM-DD HH:MM:SS。") from exc


def _coerce_scenario_call_start_time_to_display(value: str) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        return ""
    try:
        return datetime.strptime(normalized, DISPLAY_TIME_FORMAT).strftime(DISPLAY_TIME_FORMAT)
    except ValueError:
        pass
    iso_candidate = normalized.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(iso_candidate)
    except ValueError:
        parsed = None
    if parsed is not None:
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=DISPLAY_TIMEZONE)
        else:
            parsed = parsed.astimezone(DISPLAY_TIMEZONE)
        return parsed.strftime(DISPLAY_TIME_FORMAT)
    try:
        parsed_time = datetime.strptime(normalized, "%H:%M:%S")
    except ValueError:
        return ""
    current_date = datetime.now(DISPLAY_TIMEZONE).strftime("%Y-%m-%d")
    return f"{current_date} {parsed_time.strftime('%H:%M:%S')}"


def _compact_review_payload_json(
    *,
    session_id: str,
    scenario_id: str,
    username: str,
    status: str,
    aborted_reason: str,
    started_at: str,
    ended_at: str,
    reviewed_at: str,
    review_payload_text: str,
    failed_flow_stage: str,
    reviewer_notes: str,
    persist_to_db: bool,
    is_correct: bool,
    collected_slots: dict[str, Any] | None = None,
    call_start_time: str = "",
    session_config: dict[str, Any] | None = None,
) -> str:
    payload_text = str(review_payload_text or "").strip()
    payload: dict[str, Any] = {}
    try:
        parsed = json.loads(payload_text) if payload_text else {}
    except json.JSONDecodeError:
        parsed = {}
    if isinstance(parsed, dict):
        payload = parsed

    transcript = payload.get("transcript", [])
    if not isinstance(transcript, list):
        transcript = []
    review = payload.get("review", {})
    if not isinstance(review, dict):
        review = {}
    payload_collected_slots = payload.get("collected_slots", {})
    if not isinstance(payload_collected_slots, dict):
        payload_collected_slots = {}
    payload_session_config = payload.get("session_config", {})
    if not isinstance(payload_session_config, dict):
        payload_session_config = {}
    effective_collected_slots = dict(payload_collected_slots)
    if isinstance(collected_slots, dict):
        effective_collected_slots = {str(key): str(value).strip() for key, value in collected_slots.items()}
    effective_call_start_time = (
        str(call_start_time or "").strip()
        or str(payload.get("call_start_time", "")).strip()
        or str(payload_session_config.get("call_start_time", "")).strip()
    )
    effective_session_config = dict(payload_session_config)
    if isinstance(session_config, dict):
        effective_session_config.update(session_config)

    compact_session_config: dict[str, Any] = {}
    known_address = str(effective_session_config.get("known_address", "")).strip()
    if known_address:
        compact_session_config["known_address"] = known_address
    if effective_call_start_time:
        compact_session_config["call_start_time"] = effective_call_start_time
    if "use_session_start_time_as_call_start_time" in effective_session_config:
        compact_session_config["use_session_start_time_as_call_start_time"] = bool(
            effective_session_config.get("use_session_start_time_as_call_start_time", False)
        )
    if "auto_generate_hidden_settings" in effective_session_config:
        compact_session_config["auto_generate_hidden_settings"] = bool(
            effective_session_config.get("auto_generate_hidden_settings", False)
        )

    compact_payload = {
        "session_id": str(session_id or "").strip(),
        "scenario_id": str(scenario_id or "").strip(),
        "username": str(username or "").strip() or str(payload.get("username", "")).strip() or str(review.get("username", "")).strip(),
        "status": str(status or "").strip(),
        "aborted_reason": str(aborted_reason or "").strip(),
        "started_at": _normalize_display_timestamp(started_at),
        "ended_at": _normalize_display_timestamp(ended_at),
        "reviewed_at": _normalize_display_timestamp(reviewed_at),
        "call_start_time": effective_call_start_time,
        "collected_slots": effective_collected_slots,
        "transcript": transcript,
        "review": {
            "username": str(username or "").strip() or str(review.get("username", "")).strip(),
            "is_correct": bool(is_correct),
            "failed_flow_stage": str(failed_flow_stage or "").strip(),
            "notes": str(reviewer_notes or "").strip(),
            "persist_to_db": bool(persist_to_db),
        },
    }
    if compact_session_config:
        compact_payload["session_config"] = compact_session_config
    return json.dumps(compact_payload, ensure_ascii=False)


def _load_registered_accounts() -> dict[str, dict[str, Any]]:
    accounts_file = _registered_accounts_file()
    if not accounts_file.exists():
        return {}

    payload = json.loads(accounts_file.read_text(encoding="utf-8"))
    entries = payload.get("accounts", []) if isinstance(payload, dict) else payload
    if not isinstance(entries, list):
        raise ValueError("备案账号文件格式错误，必须是数组或包含 accounts 数组。")

    accounts: dict[str, dict[str, Any]] = {}
    for item in entries:
        if not isinstance(item, dict):
            raise ValueError("备案账号文件格式错误，账号项必须是对象。")
        username = str(item.get("username", "")).strip()
        if not username:
            raise ValueError("备案账号文件存在空用户名。")
        if username in accounts:
            raise ValueError(f"备案账号重复: {username}")

        password = str(item.get("password", ""))
        password_sha256 = str(item.get("password_sha256", "")).strip().lower()
        if not password and not password_sha256:
            raise ValueError(f"备案账号 {username} 缺少 password 或 password_sha256。")

        accounts[username] = {
            "username": username,
            "display_name": str(item.get("display_name") or item.get("name") or username).strip() or username,
            "password": password,
            "password_sha256": password_sha256,
            "enabled": bool(item.get("enabled", True)),
        }
    return accounts


def _verify_registered_account(account: dict[str, Any], password: str) -> bool:
    if not account.get("enabled", True):
        return False

    password_sha256 = str(account.get("password_sha256", "")).strip().lower()
    if password_sha256:
        computed = hashlib.sha256(password.encode("utf-8")).hexdigest()
        return secrets.compare_digest(computed, password_sha256)

    stored_password = str(account.get("password", ""))
    return bool(stored_password) and secrets.compare_digest(password, stored_password)


def _copy_chat_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    copied: list[dict[str, Any]] = []
    for item in messages:
        copied.append(
            {
                "id": int(item.get("id", 0) or 0),
                "username": str(item.get("username", "")).strip(),
                "display_name": str(item.get("display_name", "")).strip(),
                "text": str(item.get("text", "")),
                "reply_to_message_id": int(item.get("reply_to_message_id", 0) or 0),
                "sent_at": str(item.get("sent_at", "")).strip(),
                "edited_at": str(item.get("edited_at", "")).strip(),
            }
        )
    return copied


def _normalize_recalled_chat_message_ids(values: Any, *, known_message_ids: set[int] | None = None) -> list[int]:
    normalized_ids: list[int] = []
    seen: set[int] = set()
    for value in values if isinstance(values, list) else []:
        try:
            normalized_id = int(value or 0)
        except (TypeError, ValueError):
            continue
        if normalized_id <= 0 or normalized_id in seen:
            continue
        if known_message_ids is not None and normalized_id not in known_message_ids:
            continue
        seen.add(normalized_id)
        normalized_ids.append(normalized_id)
    return normalized_ids


def _copy_chat_messages_for_response(messages: list[dict[str, Any]], recalled_message_ids: set[int] | None = None) -> list[dict[str, Any]]:
    recalled_ids = recalled_message_ids or set()
    copied = _copy_chat_messages(messages)
    for item in copied:
        item["recalled"] = int(item.get("id", 0) or 0) in recalled_ids
    return copied


def _load_chat_state() -> None:
    global chat_state_loaded, chat_state

    with CHAT_STORAGE_LOCK:
        if chat_state_loaded:
            return

        if not CHAT_STORAGE_PATH.exists():
            message_payload: dict[str, Any] = {}
        else:
            try:
                message_payload = json.loads(CHAT_STORAGE_PATH.read_text(encoding="utf-8"))
            except Exception:
                message_payload = {}

        loaded_messages = message_payload.get("messages", [])
        normalized_messages = _copy_chat_messages(loaded_messages if isinstance(loaded_messages, list) else [])
        last_message_id = message_payload.get("last_message_id", 0)
        if not isinstance(last_message_id, int):
            last_message_id = 0
        if normalized_messages:
            last_message_id = max(last_message_id, max(message["id"] for message in normalized_messages))

        known_message_ids = {int(message["id"]) for message in normalized_messages}
        if CHAT_RECALL_STORAGE_PATH.exists():
            try:
                recall_payload = json.loads(CHAT_RECALL_STORAGE_PATH.read_text(encoding="utf-8"))
            except Exception:
                recall_payload = {}
        else:
            recall_payload = {}

        recalled_message_ids = _normalize_recalled_chat_message_ids(
            recall_payload.get("recalled_message_ids", []),
            known_message_ids=known_message_ids,
        )
        snapshot_revision = recall_payload.get("snapshot_revision", 0)
        if not isinstance(snapshot_revision, int) or snapshot_revision < 0:
            snapshot_revision = 0

        chat_state = {
            "messages": normalized_messages,
            "last_message_id": last_message_id,
            "recalled_message_ids": recalled_message_ids,
            "snapshot_revision": snapshot_revision,
        }
        chat_state_loaded = True


def _persist_chat_state() -> None:
    CHAT_STORAGE_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "last_message_id": int(chat_state.get("last_message_id", 0) or 0),
        "messages": _copy_chat_messages(list(chat_state.get("messages", []))),
    }
    CHAT_STORAGE_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _persist_chat_recall_state() -> None:
    CHAT_RECALL_STORAGE_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "snapshot_revision": int(chat_state.get("snapshot_revision", 0) or 0),
        "recalled_message_ids": _normalize_recalled_chat_message_ids(chat_state.get("recalled_message_ids", [])),
    }
    CHAT_RECALL_STORAGE_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _build_online_chat_users(now: datetime | None = None) -> list[dict[str, str]]:
    current_time = now or datetime.now(timezone.utc)
    active_cutoff = current_time - CHAT_PRESENCE_TTL
    users_by_username: dict[str, dict[str, Any]] = {}

    for session in auth_sessions.values():
        last_seen_at = session.get("last_seen_at")
        if not isinstance(last_seen_at, datetime) or last_seen_at < active_cutoff:
            continue

        username = str(session.get("username", "")).strip()
        if not username:
            continue
        existing = users_by_username.get(username)
        if existing is None or last_seen_at > existing["last_seen_at"]:
            users_by_username[username] = {
                "username": username,
                "display_name": str(session.get("display_name", username)).strip() or username,
                "last_seen_at": last_seen_at,
            }

    ordered_users = sorted(
        users_by_username.values(),
        key=lambda item: (str(item["display_name"]).lower(), str(item["username"]).lower()),
    )
    return [
        {
            "username": str(item["username"]),
            "display_name": str(item["display_name"]),
            "last_seen_at": item["last_seen_at"].astimezone(DISPLAY_TIMEZONE).strftime(DISPLAY_TIME_FORMAT),
        }
        for item in ordered_users
    ]


def _is_chat_admin(user: dict[str, str] | None) -> bool:
    if not isinstance(user, dict):
        return False
    return str(user.get("display_name", "")).strip() == "测试管理员"


def _update_chat_visibility(auth_token: str | None, visible: bool) -> None:
    if not auth_token:
        return
    session = auth_sessions.get(auth_token)
    if session is None:
        return
    session["chat_visible"] = bool(visible)


def _chat_visible_user_summaries(
    *,
    exclude_username: str = "",
    now: datetime | None = None,
) -> list[dict[str, str]]:
    current_time = now or datetime.now(timezone.utc)
    active_cutoff = current_time - CHAT_PRESENCE_TTL
    normalized_exclude = str(exclude_username or "").strip()
    users_by_username: dict[str, dict[str, str]] = {}

    for session in auth_sessions.values():
        last_seen_at = session.get("last_seen_at")
        if not isinstance(last_seen_at, datetime) or last_seen_at < active_cutoff:
            continue
        if not bool(session.get("chat_visible", False)):
            continue

        username = str(session.get("username", "")).strip()
        if not username or username == normalized_exclude:
            continue
        users_by_username[username] = {
            "username": username,
            "display_name": str(session.get("display_name", username)).strip() or username,
        }

    return [
        users_by_username[key]
        for key in sorted(users_by_username.keys(), key=lambda item: item.lower())
    ]


def _latest_chat_message_for_username(username: str) -> dict[str, Any] | None:
    normalized_username = str(username or "").strip()
    if not normalized_username:
        return None

    _load_chat_state()
    with CHAT_STORAGE_LOCK:
        recalled_ids = set(_normalize_recalled_chat_message_ids(chat_state.get("recalled_message_ids", [])))
        for message in reversed(list(chat_state.get("messages", []))):
            if int(message.get("id", 0) or 0) in recalled_ids:
                continue
            if str(message.get("username", "")).strip() == normalized_username:
                return dict(message)
    return None


def _prune_auth_sessions(now: datetime | None = None) -> None:
    current_time = now or datetime.now(timezone.utc)
    expired_tokens = [
        token
        for token, session in auth_sessions.items()
        if session.get("expires_at") is None or session["expires_at"] <= current_time
    ]
    for token in expired_tokens:
        auth_sessions.pop(token, None)


def _set_auth_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=AUTH_SESSION_COOKIE,
        value=token,
        httponly=True,
        samesite="lax",
        max_age=int(AUTH_SESSION_TTL.total_seconds()),
    )


def _delete_auth_cookie(response: Response) -> None:
    response.delete_cookie(key=AUTH_SESSION_COOKIE, httponly=True, samesite="lax")


def _create_auth_session(account: dict[str, Any]) -> str:
    _prune_auth_sessions()
    token = secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc)
    auth_sessions[token] = {
        "username": account["username"],
        "display_name": account["display_name"],
        "expires_at": now + AUTH_SESSION_TTL,
        "last_seen_at": now,
        "chat_visible": False,
    }
    return token


def _require_authenticated_user(
    auth_token: str | None = Cookie(default=None, alias=AUTH_SESSION_COOKIE),
) -> dict[str, str]:
    _prune_auth_sessions()
    if not auth_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="请先登录后再访问测试台。",
        )

    session = auth_sessions.get(auth_token)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="登录状态已失效，请重新登录。",
        )

    now = datetime.now(timezone.utc)
    session["expires_at"] = now + AUTH_SESSION_TTL
    session["last_seen_at"] = now
    return {
        "username": str(session["username"]),
        "display_name": str(session["display_name"]),
        "auth_token": auth_token,
    }


def _load_scenarios() -> list[Scenario]:
    scenario_file = _scenario_file()
    if not scenario_file.exists():
        raise FileNotFoundError(f"Scenario file not found: {scenario_file}")
    return factory.load_from_file(scenario_file)


def _resolve_scenario(*, scenario_id: str, scenario_index: int) -> Scenario:
    scenarios = _load_scenarios()
    if scenario_id:
        for scenario in scenarios:
            if scenario.scenario_id == scenario_id:
                return scenario
        raise HTTPException(status_code=404, detail="未找到指定场景")
    if 0 <= scenario_index < len(scenarios):
        return scenarios[scenario_index]
    raise HTTPException(status_code=404, detail="未找到指定场景")


def _apply_known_address(scenario: Scenario, known_address: str) -> tuple[Scenario, str]:
    sanitized = _sanitize_manual_user_text(known_address)
    hidden_context = dict(scenario.hidden_context)
    if not sanitized:
        generated_known_address = str(hidden_context.get("service_known_address_value", "")).strip()
        if bool(hidden_context.get("service_known_address", False)) and generated_known_address:
            return (
                scenario.with_generated_hidden_settings(
                    customer=scenario.customer,
                    request=scenario.request,
                    hidden_context=hidden_context,
                ),
                f"使用隐藏设定中的已知地址，客服将优先核对: {generated_known_address}",
            )
        hidden_context.update(
            {
                "service_known_address": False,
                "service_known_address_value": "",
                "service_known_address_matches_actual": False,
            }
        )
        return (
            scenario.with_generated_hidden_settings(
                customer=scenario.customer,
                request=scenario.request,
                hidden_context=hidden_context,
            ),
            "未设置已知地址，客服将按询问流程采集地址。",
        )

    hidden_context.update(
        {
            "service_known_address": True,
            "service_known_address_value": sanitized,
            "service_known_address_matches_actual": True,
            "address_input_round_1": sanitized,
            "address_input_round_2": sanitized,
            "address_input_round_3": sanitized,
            "address_input_round_4": sanitized,
            "address_input_rounds": [sanitized],
        }
    )
    return (
        scenario.with_generated_hidden_settings(
            customer=replace(scenario.customer, address=sanitized),
            request=scenario.request,
            hidden_context=hidden_context,
        ),
        f"已设置已知地址，客服将优先核对: {sanitized}",
    )


def _resolve_manual_call_start_time(req: StartSessionRequest, scenario: Scenario) -> str:
    if bool(req.use_session_start_time_as_call_start_time):
        return _current_display_timestamp()

    provided = _normalize_manual_call_start_time(req.call_start_time)
    if provided:
        return provided

    scenario_value = _coerce_scenario_call_start_time_to_display(scenario.call_start_time)
    return scenario_value or _current_display_timestamp()


def _prepare_manual_test_scenario(req: StartSessionRequest) -> tuple[Scenario, str, int]:
    scenario = _resolve_scenario(
        scenario_id=req.scenario_id,
        scenario_index=req.scenario_index,
    )

    if req.auto_generate_hidden_settings:
        if not config.openai_api_key or "YOUR_API_KEY" in config.openai_api_key:
            raise ValueError("未配置 OPENAI_API_KEY，请检查 .env 文件。")
        tool = HiddenSettingsTool(llm_client, config)
        scenario = tool.generate_for_scenario(
            scenario,
            use_utterance_reference=True,
        )
    elif _manual_test_requires_generated_hidden_settings(scenario):
        scenario = _hydrate_manual_test_scenario_locally(scenario)

    scenario = scenario.with_call_start_time(_resolve_manual_call_start_time(req, scenario))
    scenario, known_address_notice = _apply_known_address(scenario, req.known_address)
    scenario.hidden_context["interactive_test_freeform"] = True
    scenario.hidden_context["manual_test_address_precision_reference"] = False
    ensure_product_routing_plan(
        scenario.hidden_context,
        enabled=config.product_routing_enabled,
        apply_probability=config.product_routing_apply_probability,
        model_hint=scenario.product.model,
    )
    rounds_limit = _resolve_interactive_max_rounds(
        args_max_rounds=req.max_rounds,
        scenario_max_turns=scenario.max_turns,
        config_max_rounds=config.max_rounds,
    )
    return scenario, known_address_notice, rounds_limit


def _build_initial_lines(
    scenario: Scenario,
    *,
    rounds_limit: int,
    known_address_notice: str,
) -> list[str]:
    return [
        f"场景: {scenario.scenario_id}",
        f"产品: {scenario.product.brand} {scenario.product.category} {scenario.product.model}",
        f"诉求: {scenario.request.request_type}",
        f"轮次上限: {rounds_limit}",
        "输出文件: 未启用",
        "可用命令: /help, /slots, /state, /quit",
        known_address_notice,
    ]


def _build_collected_slots(scenario: Scenario) -> tuple[list[str], dict[str, str]]:
    required_slots = effective_required_slots(scenario)
    collected_slots = {slot: "" for slot in required_slots}
    for slot in SUPPLEMENTARY_COLLECTED_SLOTS:
        collected_slots.setdefault(slot, "")
    collected_slots["product_routing_result"] = str(
        scenario.hidden_context.get("product_routing_result", "")
    ).strip()
    return required_slots, collected_slots


def _session_state(session_id: str) -> dict[str, Any]:
    session = sessions.get(session_id)
    if session is None:
        session = _load_session_from_redis(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="会话已过期或不存在")
    return session


def _next_round_index(transcript: list[DialogueTurn]) -> int:
    user_turns = sum(1 for turn in transcript if turn.speaker == USER_SPEAKER)
    return user_turns + 1


def _completed_round_count(transcript: list[DialogueTurn]) -> int:
    return sum(1 for turn in transcript if turn.speaker == USER_SPEAKER)


def _merge_slots(
    collected_slots: dict[str, str],
    slot_updates: dict[str, str],
    slots_to_update: list[str],
) -> None:
    for slot, value in slot_updates.items():
        if slot in slots_to_update and str(value).strip():
            collected_slots[slot] = str(value).strip()


def _all_required_slots_filled(
    collected_slots: dict[str, str],
    required_slots: list[str],
) -> bool:
    return all(collected_slots.get(slot, "").strip() for slot in required_slots)


def _mark_session_closed(
    session: dict[str, Any],
    *,
    status: str,
    aborted_reason: str = "",
) -> None:
    session["status"] = status
    session["aborted_reason"] = aborted_reason
    if not session.get("ended_at"):
        session["ended_at"] = _current_display_timestamp()


def _review_prompt_payload(session: dict[str, Any]) -> dict[str, Any]:
    return {
        "review_required": session["status"] != "active" and not bool(session.get("review_submitted", False)),
        "review_options": FLOW_REVIEW_OPTIONS,
        "persist_to_db_default": bool(session.get("session_config", {}).get("persist_to_db", False)),
    }


def _serialize_transcript(transcript: list[DialogueTurn]) -> list[dict[str, Any]]:
    return build_display_transcript(transcript)


def _serialize_turns_for_storage(transcript: list[DialogueTurn]) -> list[dict[str, Any]]:
    return [turn.to_dict() for turn in transcript]


def _deserialize_turns_from_storage(items: list[dict[str, Any]] | None) -> list[DialogueTurn]:
    if not isinstance(items, list):
        return []
    turns: list[DialogueTurn] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        turns.append(
            DialogueTurn(
                speaker=str(item.get("speaker", "")).strip(),
                text=str(item.get("text", "")),
                round_index=int(item.get("round_index", 0) or 0),
                model_intent_inference_used=bool(item.get("model_intent_inference_used", False)),
                previous_user_intent_model_inference_used=item.get("previous_user_intent_model_inference_used"),
                post_display_lines=[
                    str(line)
                    for line in item.get("post_display_lines", [])
                    if str(line).strip()
                ] if isinstance(item.get("post_display_lines"), list) else [],
            )
        )
    return turns


def _checkpoint_snapshot(
    session: dict[str, Any],
    *,
    checkpoint_index: int,
    source_round_index: int,
) -> dict[str, Any]:
    transcript = session["transcript"]
    return {
        "checkpoint_index": checkpoint_index,
        "source_round_index": source_round_index,
        "completed_rounds": _completed_round_count(transcript),
        "scenario": session["scenario"].to_dict(),
        "transcript": _serialize_turns_for_storage(transcript),
        "terminal_entries": _copy_terminal_entries(session.get("terminal_entries", [])),
        "collected_slots": dict(session["collected_slots"]),
        "runtime_state": asdict(session["runtime_state"]),
        "status": session["status"],
        "aborted_reason": session.get("aborted_reason", ""),
        "ended_at": session.get("ended_at", ""),
    }


def _append_checkpoint(session: dict[str, Any], *, source_round_index: int) -> None:
    checkpoints = session.setdefault("checkpoints", [])
    checkpoints.append(
        _checkpoint_snapshot(
            session,
            checkpoint_index=len(checkpoints),
            source_round_index=source_round_index,
        )
    )


def _serialize_session_for_storage(session: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "username": str(session.get("username", "")).strip(),
        "scenario": session["scenario"].to_dict(),
        "base_scenario": dict(session.get("base_scenario", {})),
        "runtime_state": asdict(session["runtime_state"]),
        "transcript": _serialize_turns_for_storage(session.get("transcript", [])),
        "trace": list(session.get("trace", [])),
        "terminal_entries": _copy_terminal_entries(session.get("terminal_entries", [])),
        "required_slots": list(session.get("required_slots", [])),
        "collected_slots": dict(session.get("collected_slots", {})),
        "initial_runtime_state": dict(session.get("initial_runtime_state", {})),
        "initial_collected_slots": dict(session.get("initial_collected_slots", {})),
        "rounds_limit": int(session.get("rounds_limit", 0) or 0),
        "status": str(session.get("status", "active")).strip() or "active",
        "aborted_reason": str(session.get("aborted_reason", "")).strip(),
        "started_at": str(session.get("started_at", "")).strip(),
        "ended_at": str(session.get("ended_at", "")).strip(),
        "review_submitted": bool(session.get("review_submitted", False)),
        "session_config": dict(session.get("session_config", {})),
        "review": dict(session.get("review", {})) if isinstance(session.get("review"), dict) else None,
        "checkpoints": list(session.get("checkpoints", [])),
    }
    return payload


def _deserialize_session_from_storage(payload: dict[str, Any]) -> dict[str, Any]:
    scenario = Scenario.from_dict(dict(payload.get("scenario", {})))
    runtime_state = ServiceRuntimeState(**dict(payload.get("runtime_state", {})))
    session: dict[str, Any] = {
        "username": str(payload.get("username", "")).strip(),
        "scenario": scenario,
        "base_scenario": dict(payload.get("base_scenario", {})),
        "policy": _build_service_policy(),
        "runtime_state": runtime_state,
        "transcript": _deserialize_turns_from_storage(payload.get("transcript")),
        "trace": list(payload.get("trace", [])),
        "terminal_entries": _copy_terminal_entries(payload.get("terminal_entries", [])),
        "required_slots": list(payload.get("required_slots", [])),
        "collected_slots": dict(payload.get("collected_slots", {})),
        "initial_runtime_state": dict(payload.get("initial_runtime_state", {})),
        "initial_collected_slots": dict(payload.get("initial_collected_slots", {})),
        "rounds_limit": int(payload.get("rounds_limit", 0) or 0),
        "status": str(payload.get("status", "active")).strip() or "active",
        "aborted_reason": str(payload.get("aborted_reason", "")).strip(),
        "started_at": str(payload.get("started_at", "")).strip(),
        "ended_at": str(payload.get("ended_at", "")).strip(),
        "review_submitted": bool(payload.get("review_submitted", False)),
        "session_config": dict(payload.get("session_config", {})),
        "checkpoints": list(payload.get("checkpoints", [])),
    }
    review = payload.get("review")
    if isinstance(review, dict):
        session["review"] = dict(review)
    return session


def _persist_session(session_id: str, session: dict[str, Any]) -> None:
    redis_client = _session_redis_client()
    if redis_client is None:
        return
    try:
        redis_client.setex(
            _session_redis_key(session_id),
            max(60, SESSION_REDIS_TTL_SECONDS),
            json.dumps(_serialize_session_for_storage(session), ensure_ascii=False),
        )
    except Exception:
        pass


def _load_session_from_redis(session_id: str) -> dict[str, Any] | None:
    redis_client = _session_redis_client()
    if redis_client is None:
        return None
    try:
        payload = redis_client.get(_session_redis_key(session_id))
    except Exception:
        return None
    if not payload:
        return None
    try:
        loaded = _deserialize_session_from_storage(json.loads(payload))
    except Exception:
        return None
    sessions[session_id] = loaded
    return loaded


def _routing_prompt_key_from_text(text: str) -> str:
    normalized = str(text or "").strip()
    mapping = {
        PROMPT_BRAND_OR_SERIES: "brand_or_series",
        PROMPT_USAGE_PURPOSE: "usage_purpose",
        PROMPT_USAGE_SCENE: "usage_scene",
        PROMPT_PURCHASE_OR_PROPERTY: "purchase_or_property",
        PROMPT_PROPERTY_YEAR: "property_year",
        PROMPT_CAPACITY: "capacity_or_hp",
    }
    return mapping.get(normalized, "")


def _rebuild_scenario_for_checkpoint(session: dict[str, Any], checkpoint: dict[str, Any]) -> Scenario:
    checkpoint_scenario = checkpoint.get("scenario")
    if isinstance(checkpoint_scenario, dict):
        scenario = Scenario.from_dict(dict(checkpoint_scenario))
    else:
        base_scenario_payload = session.get("base_scenario")
        if isinstance(base_scenario_payload, dict) and base_scenario_payload:
            scenario = Scenario.from_dict(dict(base_scenario_payload))
        else:
            scenario = Scenario.from_dict(session["scenario"].to_dict())

    runtime_state_payload = dict(checkpoint.get("runtime_state", {}))
    observed_trace = list(runtime_state_payload.get("product_routing_observed_trace", []))
    expected_routing = bool(runtime_state_payload.get("expected_product_routing_response", False))
    checkpoint_transcript = _deserialize_turns_from_storage(checkpoint.get("transcript"))
    last_service_text = ""
    for turn in reversed(checkpoint_transcript):
        if turn.speaker == SERVICE_SPEAKER:
            last_service_text = turn.text
            break

    hidden_context = dict(scenario.hidden_context)
    prompt_key = _routing_prompt_key_from_text(last_service_text) if expected_routing else ""
    if prompt_key:
        hidden_context["product_routing_plan"] = {
            "enabled": True,
            "result": "",
            "trace": list(observed_trace),
            "steps": [
                {
                    "prompt_key": prompt_key,
                    "prompt": last_service_text,
                    "answer_key": default_unknown_product_routing_answer_key(prompt_key),
                    "answer_value": "",
                    "answer_instruction": "围绕当前问题直接回答。",
                }
            ],
            "summary": " -> ".join(item for item in observed_trace if str(item).strip()),
        }
        hidden_context["product_routing_trace"] = list(observed_trace)
        hidden_context["product_routing_result"] = ""
        hidden_context["product_routing_summary"] = hidden_context["product_routing_plan"]["summary"]
    scenario.hidden_context = hidden_context
    return scenario


def _append_terminal_lines(
    session: dict[str, Any],
    *,
    lines: list[str],
    tone: str,
    round_count_snapshot: int,
) -> None:
    terminal_entries = session.setdefault("terminal_entries", [])
    for line in lines:
        terminal_entries.append(
            {
                "entry_type": "line",
                "tone": tone,
                "text": line,
                "round_count_snapshot": round_count_snapshot,
            }
        )


def _append_turn_entry(session: dict[str, Any], turn: DialogueTurn) -> None:
    display_turn = turn.to_display_dict()
    terminal_entries = session.setdefault("terminal_entries", [])
    has_address_ie_display = any(
        str(line).strip().startswith("function_call:")
        for line in turn.post_display_lines
    )
    entry = {
        "entry_type": "turn",
        "tone": "service" if turn.speaker == SERVICE_SPEAKER else "user",
        "speaker": display_turn["speaker"],
        "text": display_turn["text"],
        "round_index": display_turn["round_index"],
        "round_label": display_turn["round_label"],
        "round_count_snapshot": display_turn["round_index"],
        "has_address_ie_display": has_address_ie_display,
    }
    if turn.speaker == USER_SPEAKER:
        entry["restore_checkpoint_index"] = max(int(display_turn["round_index"]) - 1, 0)
    terminal_entries.append(entry)
    for line in turn.post_display_lines:
        normalized_line = str(line).strip()
        if not normalized_line:
            continue
        terminal_entries.append(
            {
                "entry_type": "message",
                "tone": "system",
                "text": normalized_line,
                "round_count_snapshot": display_turn["round_index"],
            }
        )


def _rebuild_terminal_entries_from_transcript(
    session: dict[str, Any],
    *,
    keep_line_entries: bool = True,
) -> None:
    line_entries_by_round: dict[int, list[dict[str, Any]]] = {}
    if keep_line_entries:
        for entry in session.get("terminal_entries", []):
            if str(entry.get("entry_type", "")).strip() != "line":
                continue
            round_snapshot = int(entry.get("round_count_snapshot", 0) or 0)
            line_entries_by_round.setdefault(round_snapshot, []).append(dict(entry))

    rebuilt_entries: list[dict[str, Any]] = list(line_entries_by_round.get(0, []))
    session["terminal_entries"] = rebuilt_entries
    transcript = list(session.get("transcript", []))
    for index, turn in enumerate(transcript):
        _append_turn_entry(session, turn)
        current_round_index = int(turn.round_index or 0)
        next_round_index = int(transcript[index + 1].round_index or 0) if index + 1 < len(transcript) else None
        if next_round_index != current_round_index:
            session["terminal_entries"].extend(line_entries_by_round.get(current_round_index, []))


def _copy_terminal_entries(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [dict(entry) for entry in entries]


def _append_address_ie_display_lines(
    *,
    policy: ServiceDialoguePolicy,
    turn: DialogueTurn,
    transcript: list[DialogueTurn],
    runtime_state: ServiceRuntimeState,
) -> dict[str, Any] | None:
    should_insert_for_collection = policy.should_insert_address_ie_function_call(
        user_text=turn.text,
        transcript=transcript,
        runtime_state=runtime_state,
    )
    should_insert_for_confirmation_correction = (
        not should_insert_for_collection
        and policy.should_insert_address_ie_after_observation_confirmation(
            user_text=turn.text,
            user_round_index=turn.round_index,
            transcript=transcript,
            runtime_state=runtime_state,
        )
    )
    if not (should_insert_for_collection or should_insert_for_confirmation_correction):
        return None
    observation = build_address_model_observation(
        transcript,
        client=llm_client,
    )
    turn.post_display_lines.append(policy.ADDRESS_IE_FUNCTION_CALL_DISPLAY)
    turn.post_display_lines.append(f"observation: {json.dumps(observation, ensure_ascii=False)}")
    return observation


def _address_ie_post_display_lines_for_transcript(transcript: list[DialogueTurn]) -> list[str]:
    observation = build_address_model_observation(
        transcript,
        client=llm_client,
    )
    return [
        ServiceDialoguePolicy.ADDRESS_IE_FUNCTION_CALL_DISPLAY,
        f"observation: {json.dumps(observation, ensure_ascii=False)}",
    ]


def _find_user_turn_by_round_index(transcript: list[DialogueTurn], round_index: int) -> tuple[int, DialogueTurn] | None:
    for index, turn in enumerate(transcript):
        if turn.speaker == USER_SPEAKER and int(turn.round_index) == int(round_index):
            return index, turn
    return None


def _apply_manual_address_ie_display_lines(
    session: dict[str, Any],
    *,
    round_index: int,
    enabled: bool,
) -> bool:
    transcript = session.get("transcript", [])
    turn_match = _find_user_turn_by_round_index(transcript, round_index)
    if turn_match is None:
        raise HTTPException(status_code=404, detail="未找到对应的用户轮次。")

    turn_position, user_turn = turn_match
    preserved_lines = [
        str(line).strip()
        for line in user_turn.post_display_lines
        if str(line).strip()
        and not str(line).strip().startswith("function_call:")
        and not str(line).strip().startswith("observation:")
    ]
    if not enabled:
        changed = preserved_lines != list(user_turn.post_display_lines)
        user_turn.post_display_lines = preserved_lines
    else:
        observation_lines = _address_ie_post_display_lines_for_transcript(transcript[: turn_position + 1])
        updated_lines = preserved_lines + observation_lines
        changed = updated_lines != list(user_turn.post_display_lines)
        user_turn.post_display_lines = updated_lines

    if not changed:
        return False

    _rebuild_terminal_entries_from_transcript(session)
    checkpoints = session.get("checkpoints", [])
    for checkpoint in checkpoints:
        if int(checkpoint.get("source_round_index", 0) or 0) < int(round_index):
            continue
        checkpoint_transcript = _deserialize_turns_from_storage(checkpoint.get("transcript"))
        checkpoint_turn_match = _find_user_turn_by_round_index(checkpoint_transcript, round_index)
        if checkpoint_turn_match is None:
            continue
        checkpoint_turn_position, checkpoint_user_turn = checkpoint_turn_match
        checkpoint_preserved_lines = [
            str(line).strip()
            for line in checkpoint_user_turn.post_display_lines
            if str(line).strip()
            and not str(line).strip().startswith("function_call:")
            and not str(line).strip().startswith("observation:")
        ]
        if enabled:
            checkpoint_observation_lines = _address_ie_post_display_lines_for_transcript(
                checkpoint_transcript[: checkpoint_turn_position + 1]
            )
            checkpoint_user_turn.post_display_lines = checkpoint_preserved_lines + checkpoint_observation_lines
        else:
            checkpoint_user_turn.post_display_lines = checkpoint_preserved_lines
        checkpoint["transcript"] = _serialize_turns_for_storage(checkpoint_transcript)
        checkpoint_session = {"transcript": checkpoint_transcript, "terminal_entries": []}
        _rebuild_terminal_entries_from_transcript(checkpoint_session)
        checkpoint["terminal_entries"] = _copy_terminal_entries(checkpoint_session["terminal_entries"])
    return True


def _build_auto_address_confirmation_result(
    *,
    policy: ServiceDialoguePolicy,
    runtime_state: ServiceRuntimeState,
    observation: dict[str, Any] | None,
) -> ServicePolicyResult | None:
    if not isinstance(observation, dict):
        return None
    error_code = observation.get("error_code", 1)
    try:
        normalized_error_code = int(error_code)
    except (TypeError, ValueError):
        normalized_error_code = 1
    if normalized_error_code != 0:
        return None
    confirmed_address = str(observation.get("address") or "").strip()
    if not confirmed_address:
        return None

    runtime_state.expected_address_confirmation = True
    runtime_state.address_confirmation_triggered_by_observation = True
    runtime_state.address_confirmation_started_from_known_address = False
    runtime_state.awaiting_full_address = False
    runtime_state.pending_address_confirmation = confirmed_address
    runtime_state.partial_address_candidate = ""
    runtime_state.address_vague_retry_count = 0
    runtime_state.last_address_followup_prompt = ""
    return ServicePolicyResult(
        reply=policy._address_confirmation_prompt(confirmed_address),
        slot_updates={},
        is_ready_to_close=False,
    )


def _address_runtime_state_snapshot(
    *,
    scenario: Scenario,
    runtime_state: ServiceRuntimeState,
    collected_slots: dict[str, str],
) -> dict[str, Any]:
    current_candidate = (
        str(runtime_state.pending_address_confirmation or "").strip()
        or str(runtime_state.partial_address_candidate or "").strip()
        or str(collected_slots.get("address", "")).strip()
    )
    if not current_candidate:
        return {}

    components = extract_address_components(current_candidate)
    landmark_candidate = current_candidate
    for token in (
        components.province,
        components.city,
        components.district,
        components.town,
        components.road,
        components.community,
        components.building,
        components.unit,
        components.floor,
        components.room,
    ):
        if token:
            landmark_candidate = landmark_candidate.replace(token, "", 1)
    landmark_candidate = landmark_candidate.strip("，,。！？!?；;：:、 ")
    return {
        "address_current_candidate": current_candidate,
        "address_collected_value": str(collected_slots.get("address", "")).strip(),
        "address_slot_province": components.province,
        "address_slot_city": components.city,
        "address_slot_district": components.district,
        "address_slot_town": components.town,
        "address_slot_road": components.road,
        "address_slot_community": components.community,
        "address_slot_building": components.building,
        "address_slot_unit": components.unit,
        "address_slot_floor": components.floor,
        "address_slot_room": components.room,
        "address_slot_landmark": landmark_candidate,
        "address_missing_required_precision": ServiceDialoguePolicy._missing_required_address_precision(
            current_candidate,
            scenario.customer.address,
        ),
    }


def _build_runtime_state_view(session: dict[str, Any]) -> dict[str, Any]:
    runtime_state = asdict(session["runtime_state"])
    runtime_state.update(
        _address_runtime_state_snapshot(
            scenario=session["scenario"],
            runtime_state=session["runtime_state"],
            collected_slots=session["collected_slots"],
        )
    )
    return runtime_state


def _build_session_view(session_id: str, session: dict[str, Any]) -> dict[str, Any]:
    transcript = session["transcript"]
    return {
        "session_id": session_id,
        "scenario": session["scenario"].to_dict(),
        "session_config": dict(session.get("session_config", {})),
        "required_slots": list(session["required_slots"]),
        "collected_slots": dict(session["collected_slots"]),
        "runtime_state": _build_runtime_state_view(session),
        "rounds_limit": session["rounds_limit"],
        "status": session["status"],
        "started_at": str(session.get("started_at", "")).strip(),
        "ended_at": str(session.get("ended_at", "")).strip(),
        "session_closed": session["status"] != "active",
        "next_round_index": _next_round_index(transcript),
        "completed_rounds": _completed_round_count(transcript),
        "transcript": _serialize_transcript(transcript),
        "terminal_entries": _copy_terminal_entries(session.get("terminal_entries", [])),
        **_review_prompt_payload(session),
    }


def _session_snapshot(session_id: str, session: dict[str, Any]) -> dict[str, Any]:
    scenario = session["scenario"]
    runtime_state = session["runtime_state"]
    transcript = session["transcript"]
    return {
        "session_id": session_id,
        "scenario_id": scenario.scenario_id,
        "session_owner_username": str(session.get("username", "")).strip(),
        "scenario": scenario.to_dict(),
        "status": session["status"],
        "aborted_reason": session.get("aborted_reason", ""),
        "started_at": session.get("started_at", ""),
        "ended_at": session.get("ended_at", ""),
        "rounds_limit": session["rounds_limit"],
        "required_slots": list(session["required_slots"]),
        "session_config": dict(session.get("session_config", {})),
        "collected_slots": dict(session["collected_slots"]),
        "runtime_state_final": asdict(runtime_state),
        "transcript": _serialize_transcript(transcript),
        "terminal_entries": _copy_terminal_entries(session.get("terminal_entries", [])),
        "trace": list(session["trace"]),
        "checkpoints": list(session.get("checkpoints", [])),
    }


def _review_table_columns(conn: sqlite3.Connection) -> set[str]:
    rows = conn.execute("PRAGMA table_info(manual_test_reviews)").fetchall()
    return {str(row[1]).strip() for row in rows}


def _review_db_is_corrupt_error(exc: Exception) -> bool:
    message = str(exc or "").lower()
    return "database disk image is malformed" in message or "malformed" in message or "file is not a database" in message


def _review_db_state_guard() -> None:
    global _SESSION_REVIEW_DB_STATE_PATH, _SESSION_REVIEW_DB_SCHEMA_READY, _SESSION_REVIEW_DB_NORMALIZED
    current_path = SESSION_REVIEW_DB_PATH.resolve()
    if _SESSION_REVIEW_DB_STATE_PATH != current_path:
        _SESSION_REVIEW_DB_STATE_PATH = current_path
        _SESSION_REVIEW_DB_SCHEMA_READY = False
        _SESSION_REVIEW_DB_NORMALIZED = False


def _review_db_sidecar_paths() -> list[Path]:
    return [
        SESSION_REVIEW_DB_PATH,
        Path(f"{SESSION_REVIEW_DB_PATH}-wal"),
        Path(f"{SESSION_REVIEW_DB_PATH}-shm"),
    ]


def _mark_review_db_unready() -> None:
    global _SESSION_REVIEW_DB_SCHEMA_READY, _SESSION_REVIEW_DB_NORMALIZED
    _SESSION_REVIEW_DB_SCHEMA_READY = False
    _SESSION_REVIEW_DB_NORMALIZED = False


def _archive_corrupt_review_database_locked(reason: str) -> list[Path]:
    archived_paths: list[Path] = []
    timestamp = datetime.now(DISPLAY_TIMEZONE).strftime("%Y%m%d_%H%M%S")
    normalized_reason = re.sub(r"[^a-z0-9_]+", "_", str(reason or "").lower()).strip("_") or "corrupt"
    for original_path in _review_db_sidecar_paths():
        if not original_path.exists():
            continue
        archived_path = original_path.with_name(f"{original_path.name}.{normalized_reason}_{timestamp}")
        counter = 1
        while archived_path.exists():
            archived_path = original_path.with_name(f"{original_path.name}.{normalized_reason}_{timestamp}_{counter}")
            counter += 1
        original_path.rename(archived_path)
        archived_paths.append(archived_path)
    return archived_paths


def _open_review_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(SESSION_REVIEW_DB_PATH, timeout=15.0, isolation_level=None)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA busy_timeout=15000")
    return conn


def _normalize_review_database_locked(conn: sqlite3.Connection) -> None:
    global _SESSION_REVIEW_DB_NORMALIZED
    if _SESSION_REVIEW_DB_NORMALIZED:
        return
    rows = conn.execute(
        """
        SELECT session_id, scenario_id, username, status, aborted_reason, is_correct,
               failed_flow_stage, reviewer_notes, persist_to_db,
               started_at, ended_at, reviewed_at, review_payload_json
        FROM manual_test_reviews
        """
    ).fetchall()
    for (
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
        review_payload_json,
    ) in rows:
        normalized_started_at = _normalize_display_timestamp(started_at)
        normalized_ended_at = _normalize_display_timestamp(ended_at)
        normalized_reviewed_at = _normalize_display_timestamp(reviewed_at)
        normalized_payload = _compact_review_payload_json(
            session_id=str(session_id or "").strip(),
            scenario_id=str(scenario_id or "").strip(),
            username=str(username or "").strip(),
            status=str(status or "").strip(),
            aborted_reason=str(aborted_reason or "").strip(),
            started_at=str(started_at or "").strip(),
            ended_at=str(ended_at or "").strip(),
            reviewed_at=str(reviewed_at or "").strip(),
            review_payload_text=str(review_payload_json or ""),
            failed_flow_stage=str(failed_flow_stage or "").strip(),
            reviewer_notes=str(reviewer_notes or "").strip(),
            persist_to_db=bool(persist_to_db),
            is_correct=bool(is_correct),
        )
        if (
            normalized_started_at != str(started_at or "")
            or normalized_ended_at != str(ended_at or "")
            or normalized_reviewed_at != str(reviewed_at or "")
            or normalized_payload != str(review_payload_json or "")
        ):
            conn.execute(
                """
                UPDATE manual_test_reviews
                SET started_at = ?, ended_at = ?, reviewed_at = ?, review_payload_json = ?
                WHERE session_id = ?
                """,
                (
                    normalized_started_at,
                    normalized_ended_at,
                    normalized_reviewed_at,
                    normalized_payload,
                    session_id,
                ),
            )
    _SESSION_REVIEW_DB_NORMALIZED = True


def _ensure_review_database() -> None:
    global _SESSION_REVIEW_DB_SCHEMA_READY
    SESSION_REVIEW_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with SESSION_REVIEW_DB_LOCK:
        _review_db_state_guard()
        if _SESSION_REVIEW_DB_SCHEMA_READY:
            return
        retry_after_reset = True
        while True:
            conn: sqlite3.Connection | None = None
            try:
                conn = _open_review_db_connection()
                conn.execute("BEGIN IMMEDIATE")
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS manual_test_reviews (
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
                if "username" not in _review_table_columns(conn):
                    conn.execute("ALTER TABLE manual_test_reviews ADD COLUMN username TEXT")
                _normalize_review_database_locked(conn)
                conn.commit()
                _SESSION_REVIEW_DB_SCHEMA_READY = True
                return
            except sqlite3.DatabaseError as exc:
                if conn is not None:
                    conn.rollback()
                if retry_after_reset and _review_db_is_corrupt_error(exc):
                    _archive_corrupt_review_database_locked("malformed")
                    _mark_review_db_unready()
                    retry_after_reset = False
                    continue
                raise
            finally:
                if conn is not None:
                    conn.close()


def _persist_review_result(
    *,
    session_id: str,
    session: dict[str, Any],
    username: str,
    is_correct: bool,
    failed_flow_stage: str,
    notes: str,
    persist_to_db: bool,
) -> None:
    _ensure_review_database()
    session_config = dict(session.get("session_config", {}))
    effective_known_address = str(session_config.get("known_address", "")).strip()
    if not effective_known_address:
        hidden_context = session["scenario"].hidden_context if isinstance(session["scenario"].hidden_context, dict) else {}
        generated_known_address = str(hidden_context.get("service_known_address_value", "")).strip()
        if bool(hidden_context.get("service_known_address", False)) and generated_known_address:
            effective_known_address = generated_known_address
    if effective_known_address:
        session_config["known_address"] = effective_known_address
    session_config["call_start_time"] = str(session["scenario"].call_start_time).strip()
    review_payload = {
        "session_id": session_id,
        "scenario_id": session["scenario"].scenario_id,
        "username": username,
        "status": session["status"],
        "aborted_reason": session.get("aborted_reason", ""),
        "started_at": str(session.get("started_at", "")).strip(),
        "ended_at": str(session.get("ended_at", "")).strip(),
        "call_start_time": str(session["scenario"].call_start_time).strip(),
        "collected_slots": dict(session.get("collected_slots", {})),
        "transcript": _serialize_transcript(session["transcript"]),
        "review": {
            "username": username,
            "is_correct": is_correct,
            "failed_flow_stage": failed_flow_stage,
            "notes": notes,
            "persist_to_db": persist_to_db,
        },
    }
    if session_config:
        review_payload["session_config"] = session_config
    reviewed_at = _current_display_timestamp()
    with SESSION_REVIEW_DB_LOCK:
        retry_after_reset = True
        while True:
            conn: sqlite3.Connection | None = None
            try:
                _ensure_review_database()
                conn = _open_review_db_connection()
                conn.execute("BEGIN IMMEDIATE")
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
                    ON CONFLICT(session_id) DO UPDATE SET
                        scenario_id=excluded.scenario_id,
                        username=excluded.username,
                        status=excluded.status,
                        aborted_reason=excluded.aborted_reason,
                        is_correct=excluded.is_correct,
                        failed_flow_stage=excluded.failed_flow_stage,
                        reviewer_notes=excluded.reviewer_notes,
                        persist_to_db=excluded.persist_to_db,
                        started_at=excluded.started_at,
                        ended_at=excluded.ended_at,
                        reviewed_at=excluded.reviewed_at,
                        review_payload_json=excluded.review_payload_json
                    """,
                    (
                        session_id,
                        review_payload["scenario_id"],
                        username,
                        review_payload["status"],
                        review_payload["aborted_reason"],
                        1 if is_correct else 0,
                        failed_flow_stage,
                        notes,
                        1 if persist_to_db else 0,
                        review_payload["started_at"],
                        review_payload["ended_at"],
                        reviewed_at,
                        json.dumps(review_payload, ensure_ascii=False),
                    ),
                )
                conn.commit()
                return
            except sqlite3.DatabaseError as exc:
                if conn is not None:
                    conn.rollback()
                if retry_after_reset and _review_db_is_corrupt_error(exc):
                    _archive_corrupt_review_database_locked("malformed")
                    _mark_review_db_unready()
                    retry_after_reset = False
                    continue
                raise
            finally:
                if conn is not None:
                    conn.close()


@app.get("/api/auth/me")
def auth_me(current_user: dict[str, str] = Depends(_require_authenticated_user)):
    return {
        "authenticated": True,
        "user": current_user,
    }


@app.post("/api/auth/login")
def auth_login(req: LoginRequest, response: Response):
    username = req.username.strip()
    password = req.password
    if not username or not password:
        raise HTTPException(status_code=400, detail="请输入账号和密码。")

    try:
        accounts = _load_registered_accounts()
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    if not accounts:
        raise HTTPException(
            status_code=503,
            detail=f"未配置备案账号，请先维护文件: {_registered_accounts_file()}",
        )

    account = accounts.get(username)
    if account is None or not _verify_registered_account(account, password):
        raise HTTPException(status_code=401, detail="账号或密码错误，或账号未备案。")

    token = _create_auth_session(account)
    _set_auth_cookie(response, token)
    return {
        "ok": True,
        "user": {
            "username": account["username"],
            "display_name": account["display_name"],
        },
    }


@app.post("/api/auth/logout")
def auth_logout(
    response: Response,
    auth_token: str | None = Cookie(default=None, alias=AUTH_SESSION_COOKIE),
):
    if auth_token:
        auth_sessions.pop(auth_token, None)
    _delete_auth_cookie(response)
    return {"ok": True}


@app.get("/api/chat/state")
def chat_state_view(
    since_message_id: int = 0,
    since_snapshot_revision: int = 0,
    chat_visible: bool = False,
    current_user: dict[str, str] = Depends(_require_authenticated_user),
):
    _load_chat_state()
    _update_chat_visibility(current_user.get("auth_token"), chat_visible)

    with CHAT_STORAGE_LOCK:
        known_messages = list(chat_state.get("messages", []))
        normalized_since = max(int(since_message_id or 0), 0)
        snapshot_revision = max(int(chat_state.get("snapshot_revision", 0) or 0), 0)
        normalized_snapshot_revision = max(int(since_snapshot_revision or 0), 0)
        requires_full_sync = normalized_since <= 0 or normalized_snapshot_revision != snapshot_revision
        if normalized_since > 0 and not requires_full_sync:
            message_slice = [message for message in known_messages if int(message.get("id", 0) or 0) > normalized_since]
        else:
            message_slice = known_messages

        latest_message_id = int(chat_state.get("last_message_id", 0) or 0)
        recalled_message_ids = set(_normalize_recalled_chat_message_ids(chat_state.get("recalled_message_ids", [])))

    online_users = _build_online_chat_users()
    chat_admin = _is_chat_admin(current_user)
    return {
        "ok": True,
        "current_user": {
            "username": current_user["username"],
            "display_name": current_user["display_name"],
        },
        "chat_visible": bool(chat_visible),
        "chat_admin": chat_admin,
        "online_count": len(online_users),
        "online_users": online_users,
        "messages": _copy_chat_messages_for_response(message_slice, recalled_message_ids),
        "latest_message_id": latest_message_id,
        "snapshot_revision": snapshot_revision,
        "full_sync": requires_full_sync,
        "storage_path": str(CHAT_STORAGE_PATH),
    }


@app.post("/api/chat/messages")
def create_chat_message(
    req: ChatMessageRequest,
    current_user: dict[str, str] = Depends(_require_authenticated_user),
):
    normalized_text = str(req.text or "").strip()
    normalized_reply_to_message_id = max(int(req.reply_to_message_id or 0), 0)
    if not normalized_text:
        raise HTTPException(status_code=400, detail="聊天消息不能为空。")
    if len(normalized_text) > 1000:
        raise HTTPException(status_code=400, detail="聊天消息不能超过 1000 个字符。")

    _load_chat_state()

    with CHAT_STORAGE_LOCK:
        recalled_message_ids = set(_normalize_recalled_chat_message_ids(chat_state.get("recalled_message_ids", [])))
        if normalized_reply_to_message_id > 0:
            reply_target = next(
                (
                    message
                    for message in list(chat_state.get("messages", []))
                    if int(message.get("id", 0) or 0) == normalized_reply_to_message_id
                ),
                None,
            )
            if reply_target is None or normalized_reply_to_message_id in recalled_message_ids:
                raise HTTPException(status_code=400, detail="指定回复的消息不存在或已失效。")
        next_message_id = int(chat_state.get("last_message_id", 0) or 0) + 1
        message = {
            "id": next_message_id,
            "username": current_user["username"],
            "display_name": current_user["display_name"],
            "text": normalized_text,
            "reply_to_message_id": normalized_reply_to_message_id,
            "sent_at": _current_display_timestamp(),
        }
        chat_messages = list(chat_state.get("messages", []))
        chat_messages.append(message)
        chat_state["messages"] = chat_messages
        chat_state["last_message_id"] = next_message_id
        _persist_chat_state()
        snapshot_revision = int(chat_state.get("snapshot_revision", 0) or 0)

    return {
        "ok": True,
        "message": {**dict(message), "recalled": False},
        "snapshot_revision": snapshot_revision,
        "storage_path": str(CHAT_STORAGE_PATH),
    }


@app.post("/api/chat/messages/{message_id}/recall")
def recall_chat_message(
    message_id: int,
    current_user: dict[str, str] = Depends(_require_authenticated_user),
):
    normalized_message_id = max(int(message_id or 0), 0)
    if normalized_message_id <= 0:
        raise HTTPException(status_code=400, detail="撤回消息编号无效。")

    _load_chat_state()

    with CHAT_STORAGE_LOCK:
        known_messages = list(chat_state.get("messages", []))
        target_message = next(
            (message for message in known_messages if int(message.get("id", 0) or 0) == normalized_message_id),
            None,
        )
        if target_message is None:
            raise HTTPException(status_code=404, detail="未找到要撤回的消息。")
        if str(target_message.get("username", "")).strip() != current_user["username"]:
            raise HTTPException(status_code=403, detail="只能撤回自己发送的消息。")

        recalled_message_ids = _normalize_recalled_chat_message_ids(chat_state.get("recalled_message_ids", []))
        if normalized_message_id not in recalled_message_ids:
            recalled_message_ids.append(normalized_message_id)
            recalled_message_ids.sort()
            chat_state["recalled_message_ids"] = recalled_message_ids
            chat_state["snapshot_revision"] = int(chat_state.get("snapshot_revision", 0) or 0) + 1
            _persist_chat_recall_state()

        snapshot_revision = int(chat_state.get("snapshot_revision", 0) or 0)
        latest_message_id = int(chat_state.get("last_message_id", 0) or 0)
        recalled_ids = set(_normalize_recalled_chat_message_ids(chat_state.get("recalled_message_ids", [])))

    return {
        "ok": True,
        "recalled": True,
        "message_id": normalized_message_id,
        "messages": _copy_chat_messages_for_response(known_messages, recalled_ids),
        "latest_message_id": latest_message_id,
        "snapshot_revision": snapshot_revision,
        "full_sync": True,
        "storage_path": str(CHAT_STORAGE_PATH),
    }


@app.patch("/api/chat/messages/{message_id}")
def update_chat_message(
    message_id: int,
    req: ChatMessageUpdateRequest,
    current_user: dict[str, str] = Depends(_require_authenticated_user),
):
    normalized_message_id = max(int(message_id or 0), 0)
    normalized_text = str(req.text or "").strip()
    if normalized_message_id <= 0:
        raise HTTPException(status_code=400, detail="编辑消息编号无效。")
    if not normalized_text:
        raise HTTPException(status_code=400, detail="聊天消息不能为空。")
    if len(normalized_text) > 1000:
        raise HTTPException(status_code=400, detail="聊天消息不能超过 1000 个字符。")

    _load_chat_state()

    with CHAT_STORAGE_LOCK:
        known_messages = list(chat_state.get("messages", []))
        target_message: dict[str, Any] | None = None
        target_index = -1
        for index, message in enumerate(known_messages):
            if int(message.get("id", 0) or 0) == normalized_message_id:
                target_message = message
                target_index = index
                break

        if target_message is None or target_index < 0:
            raise HTTPException(status_code=404, detail="未找到要编辑的消息。")
        if str(target_message.get("username", "")).strip() != current_user["username"]:
            raise HTTPException(status_code=403, detail="只能编辑自己发送的消息。")

        recalled_message_ids = set(_normalize_recalled_chat_message_ids(chat_state.get("recalled_message_ids", [])))
        if normalized_message_id in recalled_message_ids:
            raise HTTPException(status_code=400, detail="已撤回的消息不能编辑。")

        updated_message = dict(target_message)
        updated_message["text"] = normalized_text
        updated_message["edited_at"] = _current_display_timestamp()
        known_messages[target_index] = updated_message
        chat_state["messages"] = known_messages
        chat_state["snapshot_revision"] = int(chat_state.get("snapshot_revision", 0) or 0) + 1
        _persist_chat_state()
        _persist_chat_recall_state()

        snapshot_revision = int(chat_state.get("snapshot_revision", 0) or 0)
        latest_message_id = int(chat_state.get("last_message_id", 0) or 0)
        recalled_ids = set(_normalize_recalled_chat_message_ids(chat_state.get("recalled_message_ids", [])))

    return {
        "ok": True,
        "edited": True,
        "message": {**dict(updated_message), "recalled": False},
        "messages": _copy_chat_messages_for_response(known_messages, recalled_ids),
        "latest_message_id": latest_message_id,
        "snapshot_revision": snapshot_revision,
        "full_sync": True,
        "storage_path": str(CHAT_STORAGE_PATH),
    }


@app.get("/api/chat/messages/latest-readers")
def latest_chat_message_readers(
    chat_visible: bool = False,
    current_user: dict[str, str] = Depends(_require_authenticated_user),
):
    _update_chat_visibility(current_user.get("auth_token"), chat_visible)
    latest_message = _latest_chat_message_for_username(current_user["username"])
    readers = _chat_visible_user_summaries(exclude_username=current_user["username"])
    return {
        "ok": True,
        "latest_self_message_id": int(latest_message.get("id", 0) or 0) if latest_message else 0,
        "latest_self_message_text": str(latest_message.get("text", "")) if latest_message else "",
        "read_by": readers,
    }


@app.post("/api/chat/history/clear")
def clear_chat_history(
    current_user: dict[str, str] = Depends(_require_authenticated_user),
):
    if not _is_chat_admin(current_user):
        raise HTTPException(status_code=403, detail="只有测试管理员可以清空聊天历史。")

    _load_chat_state()

    with CHAT_STORAGE_LOCK:
        chat_state["messages"] = []
        chat_state["last_message_id"] = 0
        chat_state["recalled_message_ids"] = []
        chat_state["snapshot_revision"] = int(chat_state.get("snapshot_revision", 0) or 0) + 1
        if CHAT_STORAGE_PATH.exists():
            CHAT_STORAGE_PATH.unlink()
        if CHAT_RECALL_STORAGE_PATH.exists():
            CHAT_RECALL_STORAGE_PATH.unlink()

    return {
        "ok": True,
        "cleared": True,
        "latest_message_id": 0,
        "messages": [],
        "snapshot_revision": int(chat_state.get("snapshot_revision", 0) or 0),
        "full_sync": True,
        "storage_path": str(CHAT_STORAGE_PATH),
    }


@app.get("/api/scenarios")
def list_scenarios(current_user: dict[str, str] = Depends(_require_authenticated_user)):
    try:
        scenarios = _load_scenarios()
        return [
            {
                "id": scenario.scenario_id,
                "index": index,
                "product": f"{scenario.product.brand} {scenario.product.model}",
                "request": scenario.request.request_type,
                "issue": scenario.request.issue,
                "max_turns": scenario.max_turns,
            }
            for index, scenario in enumerate(scenarios)
        ]
    except Exception as exc:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"加载场景列表失败: {exc}") from exc


@app.get("/api/mock-known-address")
def get_mock_known_address(
    scenario_id: str = "",
    current_user: dict[str, str] = Depends(_require_authenticated_user),
):
    _ = current_user
    seed = scenario_id or "manual-test"
    address = generate_local_customer_address(
        f"{seed}:frontend-known-address:{secrets.token_hex(8)}",
        "standard_residential",
    )
    return {"known_address": address}


@app.get("/api/reference/fault-issue-categories")
def get_fault_issue_categories(
    current_user: dict[str, str] = Depends(_require_authenticated_user),
):
    _ = current_user
    library_path = config.data_dir / "utterance_reference_library.json"
    if not library_path.exists():
        raise HTTPException(status_code=404, detail="未找到话术参考库文件。")

    payload = json.loads(library_path.read_text(encoding="utf-8"))
    repair_bucket = payload.get("报修", {}) if isinstance(payload, dict) else {}
    if not isinstance(repair_bucket, dict):
        return {"categories": []}

    categories = [str(key).strip() for key in repair_bucket.keys() if str(key).strip()]
    return {"categories": categories}


@app.post("/api/punctuation/predict")
def predict_punctuation(
    req: PunctuationRequest,
    current_user: dict[str, str] = Depends(_require_authenticated_user),
):
    _ = current_user
    normalized = _sanitize_manual_user_text(req.text)
    if not normalized:
        return {"ok": True, "input_text": "", "punctuated_text": ""}
    punctuated_text = _punctuate_user_text_for_session(normalized)
    return {
        "ok": True,
        "input_text": normalized,
        "punctuated_text": punctuated_text,
    }


@app.post("/api/session/start")
def start_session(
    req: StartSessionRequest,
    current_user: dict[str, str] = Depends(_require_authenticated_user),
):
    try:
        scenario, known_address_notice, rounds_limit = _prepare_manual_test_scenario(req)
        required_slots, collected_slots = _build_collected_slots(scenario)
        initial_runtime_state = asdict(ServiceRuntimeState())
        initial_lines = _build_initial_lines(
            scenario,
            rounds_limit=rounds_limit,
            known_address_notice=known_address_notice,
        )

        session_id = str(uuid.uuid4())
        sessions[session_id] = {
            "username": current_user["username"],
            "scenario": scenario,
            "base_scenario": scenario.to_dict(),
            "policy": _build_service_policy(),
            "runtime_state": ServiceRuntimeState(),
            "transcript": [],
            "trace": [],
            "terminal_entries": [],
            "checkpoints": [],
            "required_slots": required_slots,
            "collected_slots": collected_slots,
            "initial_runtime_state": dict(initial_runtime_state),
            "initial_collected_slots": dict(collected_slots),
            "rounds_limit": rounds_limit,
            "status": "active",
            "aborted_reason": "",
            "started_at": _current_display_timestamp(),
            "ended_at": "",
            "review_submitted": False,
            "session_config": {
                "scenario_id": scenario.scenario_id,
                "known_address": _sanitize_manual_user_text(req.known_address),
                "call_start_time": scenario.call_start_time,
                "use_session_start_time_as_call_start_time": bool(req.use_session_start_time_as_call_start_time),
                "max_rounds": req.max_rounds,
                "auto_generate_hidden_settings": bool(req.auto_generate_hidden_settings),
                "persist_to_db": bool(req.persist_to_db),
            },
        }
        _append_checkpoint(sessions[session_id], source_round_index=0)
        _persist_session(session_id, sessions[session_id])
        return {
            **_build_session_view(session_id, sessions[session_id]),
            "initial_lines": initial_lines,
            "persist_to_db_default": bool(req.persist_to_db),
        }
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"初始化对话失败: {exc}") from exc


@app.post("/api/session/respond")
def respond(
    req: RespondRequest,
    current_user: dict[str, str] = Depends(_require_authenticated_user),
):
    session = _session_state(req.session_id)
    if session["status"] != "active":
        raise HTTPException(status_code=409, detail="当前会话已结束，请重新开始。")

    raw_text = str(req.text or "")
    sanitized = _sanitize_manual_user_text(raw_text)
    if not sanitized:
        raise HTTPException(status_code=400, detail="输入不能为空。输入 /help 查看可用命令。")

    command_token = _manual_command_token(raw_text)
    runtime_state = session["runtime_state"]
    transcript = session["transcript"]
    collected_slots = session["collected_slots"]
    completed_rounds = _completed_round_count(transcript)

    if command_token == MANUAL_TEST_HELP_COMMAND:
        output_lines = ["可用命令: /help, /slots, /state, /quit"]
        _append_terminal_lines(
            session,
            lines=output_lines,
            tone="system",
            round_count_snapshot=completed_rounds,
        )
        _persist_session(req.session_id, session)
        return {
            "mode": "command",
            "output_lines": output_lines,
            **_build_session_view(req.session_id, session),
        }

    if command_token == MANUAL_TEST_SHOW_SLOTS_COMMAND:
        output_lines = [json.dumps(collected_slots, ensure_ascii=False, indent=2)]
        _append_terminal_lines(
            session,
            lines=output_lines,
            tone="system",
            round_count_snapshot=completed_rounds,
        )
        _persist_session(req.session_id, session)
        return {
            "mode": "command",
            "output_lines": output_lines,
            **_build_session_view(req.session_id, session),
        }

    if command_token == MANUAL_TEST_SHOW_STATE_COMMAND:
        output_lines = [json.dumps(asdict(runtime_state), ensure_ascii=False, indent=2)]
        _append_terminal_lines(
            session,
            lines=output_lines,
            tone="system",
            round_count_snapshot=completed_rounds,
        )
        _persist_session(req.session_id, session)
        return {
            "mode": "command",
            "output_lines": output_lines,
            **_build_session_view(req.session_id, session),
        }

    if command_token in MANUAL_TEST_EXIT_COMMANDS:
        output_lines = ["会话已结束。"]
        _mark_session_closed(session, status="aborted", aborted_reason="user_exit")
        _append_terminal_lines(
            session,
            lines=output_lines,
            tone="system",
            round_count_snapshot=completed_rounds,
        )
        _persist_session(req.session_id, session)
        return {
            "mode": "command",
            "output_lines": output_lines,
            **_build_session_view(req.session_id, session),
        }

    round_index = _next_round_index(transcript)
    rounds_limit = int(session["rounds_limit"])
    if round_index > rounds_limit:
        output_lines = ["已达到最大轮次，会话结束。"]
        _mark_session_closed(session, status="incomplete", aborted_reason="round_limit_reached")
        _append_terminal_lines(
            session,
            lines=output_lines,
            tone="system",
            round_count_snapshot=completed_rounds,
        )
        _persist_session(req.session_id, session)
        return {
            "mode": "command",
            "output_lines": output_lines,
            **_build_session_view(req.session_id, session),
        }

    punctuated_user_text = (
        sanitized if round_index == 1 else _punctuate_user_text_for_session(sanitized)
    )

    scenario = session["scenario"]
    policy = session["policy"]
    required_slots = session["required_slots"]
    user_turn = DialogueTurn(
        speaker=USER_SPEAKER,
        text=punctuated_user_text,
        round_index=round_index,
    )
    transcript.append(user_turn)
    auto_address_observation = _append_address_ie_display_lines(
        policy=policy,
        turn=user_turn,
        transcript=transcript,
        runtime_state=runtime_state,
    )

    try:
        service_result = _build_auto_address_confirmation_result(
            policy=policy,
            runtime_state=runtime_state,
            observation=auto_address_observation,
        )
        if service_result is None:
            service_result = policy.respond(
                scenario=scenario,
                transcript=transcript,
                collected_slots=collected_slots,
                runtime_state=runtime_state,
            )
    except Exception as exc:
        transcript.pop()
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"生成回复时出错: {exc}") from exc

    _merge_slots(collected_slots, service_result.slot_updates, required_slots)
    _merge_slots(collected_slots, service_result.slot_updates, list(SUPPLEMENTARY_COLLECTED_SLOTS))

    used_model_intent_inference = bool(
        getattr(policy, "last_used_model_intent_inference", False)
    )
    service_turn = DialogueTurn(
        speaker=SERVICE_SPEAKER,
        text=service_result.reply,
        round_index=round_index,
        model_intent_inference_used=used_model_intent_inference,
        previous_user_intent_model_inference_used=used_model_intent_inference,
    )
    transcript.append(service_turn)
    _append_turn_entry(session, user_turn)
    _append_turn_entry(session, service_turn)

    session["trace"].append(
        {
            "round_index": round_index,
            "user_text": punctuated_user_text,
            "service_reply": service_result.reply,
            "used_model_intent_inference": used_model_intent_inference,
            "previous_user_intent_model_inference_used": used_model_intent_inference,
            "slot_updates": dict(service_result.slot_updates),
            "collected_slots_snapshot": dict(collected_slots),
            "runtime_state_snapshot": asdict(runtime_state),
            "is_ready_to_close": service_result.is_ready_to_close,
            "close_status": getattr(service_result, "close_status", ""),
            "close_reason": getattr(service_result, "close_reason", ""),
        }
    )

    output_lines: list[str] = []
    if getattr(service_result, "close_status", "") == "transferred":
        _mark_session_closed(
            session,
            status="transferred",
            aborted_reason=getattr(service_result, "close_reason", ""),
        )
        output_lines.append("--- 已转接人工，会话结束 ---")
    elif service_result.is_ready_to_close and _all_required_slots_filled(collected_slots, required_slots):
        _mark_session_closed(session, status="completed")
        output_lines.append("--- 会话已完成 ---")
    elif round_index >= rounds_limit:
        _mark_session_closed(session, status="incomplete", aborted_reason="round_limit_reached")
        output_lines.append("--- 已达到最大轮次，会话结束 ---")
    if output_lines:
        _append_terminal_lines(
            session,
            lines=output_lines,
            tone="system",
            round_count_snapshot=round_index,
        )
    _append_checkpoint(session, source_round_index=round_index)
    _persist_session(req.session_id, session)

    return {
        "mode": "reply",
        "service_turn": service_turn.to_display_dict(),
        "output_lines": output_lines,
        "is_ready_to_close": service_result.is_ready_to_close,
        "close_status": getattr(service_result, "close_status", ""),
        "close_reason": getattr(service_result, "close_reason", ""),
        **_build_session_view(req.session_id, session),
    }


@app.post("/api/session/rewind")
def rewind_session(
    req: RewindSessionRequest,
    current_user: dict[str, str] = Depends(_require_authenticated_user),
):
    session = _session_state(req.session_id)
    if session.get("review_submitted"):
        raise HTTPException(status_code=409, detail="当前会话评审已提交，不能再回退。")

    checkpoints = list(session.get("checkpoints", []))
    if not checkpoints:
        raise HTTPException(status_code=409, detail="当前会话缺少可恢复的状态节点。")
    completed_rounds = _completed_round_count(session["transcript"])
    clicked_user_round_index = int(req.clicked_user_round_index)
    requested_checkpoint_index = req.restore_checkpoint_index
    if requested_checkpoint_index is None and req.target_round_index is not None:
        requested_checkpoint_index = int(req.target_round_index)
        if clicked_user_round_index < 1:
            clicked_user_round_index = requested_checkpoint_index + 1
    if requested_checkpoint_index is None:
        if clicked_user_round_index < 1:
            raise HTTPException(status_code=400, detail="被删除的用户轮次无效。")
        requested_checkpoint_index = clicked_user_round_index - 1
    target_checkpoint_index = int(requested_checkpoint_index)
    if target_checkpoint_index < 0 or target_checkpoint_index >= len(checkpoints):
        raise HTTPException(status_code=400, detail="被删除的用户轮次无效。")
    if clicked_user_round_index < 1:
        clicked_user_round_index = target_checkpoint_index + 1
    target_round_index = target_checkpoint_index
    checkpoint = checkpoints[target_checkpoint_index]
    if not isinstance(checkpoint, dict):
        raise HTTPException(status_code=409, detail="当前会话状态节点损坏，无法回退。")

    session["scenario"] = _rebuild_scenario_for_checkpoint(session, checkpoint)
    session["policy"] = _build_service_policy()
    session["transcript"] = _deserialize_turns_from_storage(checkpoint.get("transcript"))
    session["terminal_entries"] = _copy_terminal_entries(checkpoint.get("terminal_entries", []))
    session["collected_slots"] = dict(checkpoint.get("collected_slots", {}))
    session["runtime_state"] = ServiceRuntimeState(**copy.deepcopy(dict(checkpoint.get("runtime_state", {}))))
    session["status"] = "active"
    session["aborted_reason"] = ""
    session["ended_at"] = ""
    session["review_submitted"] = False
    session.pop("review", None)
    session["trace"] = [
        trace_item
        for trace_item in session["trace"]
        if int(trace_item.get("round_index", 0)) <= target_round_index
    ]
    session["checkpoints"] = checkpoints[:target_checkpoint_index + 1]
    _persist_session(req.session_id, session)

    return {
        "mode": "rewind",
        "rewound_from_round": completed_rounds,
        "clicked_user_round_index": clicked_user_round_index,
        "target_round_index": target_round_index,
        **_build_session_view(req.session_id, session),
    }


@app.post("/api/session/address-ie-display")
def update_address_ie_display(
    req: AddressIeDisplayRequest,
    current_user: dict[str, str] = Depends(_require_authenticated_user),
):
    session = _session_state(req.session_id)
    if session.get("review_submitted"):
        raise HTTPException(status_code=409, detail="当前会话评审已提交，不能再修改展示内容。")
    changed = _apply_manual_address_ie_display_lines(
        session,
        round_index=req.round_index,
        enabled=bool(req.enabled),
    )
    _persist_session(req.session_id, session)
    return {
        "ok": True,
        "changed": changed,
        "round_index": int(req.round_index),
        "enabled": bool(req.enabled),
        **_build_session_view(req.session_id, session),
    }


@app.post("/api/session/review")
def review_session(
    req: ReviewSessionRequest,
    current_user: dict[str, str] = Depends(_require_authenticated_user),
):
    session = _session_state(req.session_id)
    if session["status"] == "active":
        raise HTTPException(status_code=409, detail="当前会话尚未结束，不能提交评审。")
    if not req.is_correct and not req.failed_flow_stage.strip():
        raise HTTPException(status_code=400, detail="请先选择出错流程。")

    failed_flow_stage = req.failed_flow_stage.strip()
    notes = req.notes.strip()
    if req.persist_to_db:
        try:
            _persist_review_result(
                session_id=req.session_id,
                session=session,
                username=current_user["username"],
                is_correct=bool(req.is_correct),
                failed_flow_stage=failed_flow_stage,
                notes=notes,
                persist_to_db=bool(req.persist_to_db),
            )
        except Exception as exc:
            traceback.print_exc()
            raise HTTPException(status_code=500, detail=f"写入 SQLite 失败: {exc}") from exc

    session["review_submitted"] = True
    session["review"] = {
        "username": current_user["username"],
        "is_correct": bool(req.is_correct),
        "failed_flow_stage": failed_flow_stage,
        "notes": notes,
        "persist_to_db": bool(req.persist_to_db),
        "reviewed_at": _current_display_timestamp(),
    }
    _persist_session(req.session_id, session)
    return {
        "ok": True,
        "session_id": req.session_id,
        "username": current_user["username"],
        "persisted_to_db": bool(req.persist_to_db),
        "db_path": str(SESSION_REVIEW_DB_PATH) if req.persist_to_db else "",
        "review_required": False,
    }


static_dir = PROJECT_ROOT / "frontend" / "static"
if static_dir.exists():
    @app.get("/")
    def serve_frontend_index():
        return FileResponse(static_dir / "index.html")

    app.mount("/static", StaticFiles(directory=str(static_dir), html=False), name="static")
else:  # pragma: no cover
    print(f"Warning: Static directory not found at {static_dir}")


if __name__ == "__main__":  # pragma: no cover
    import uvicorn

    parser = argparse.ArgumentParser(description="Frontend manual test server")
    parser.add_argument(
        "--host",
        default=os.getenv("FRONTEND_HOST", "0.0.0.0"),
        help="Server host.",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("FRONTEND_PORT", "8000") or "8000"),
        help="Server port.",
    )
    args = parser.parse_args()
    configure_punctuation_service()
    if get_punctuation_service().backend == "local":
        _start_local_punctuation_api(model_dir=str(get_punctuation_service().model_dir))
    print(
        "[punctuation] configured backend=%s model_dir=%s api_url=%s"
        % (
            get_punctuation_service().backend,
            str(get_punctuation_service().model_dir),
            get_punctuation_service().api_url,
        )
    )
    uvicorn.run(app, host=args.host, port=args.port)
