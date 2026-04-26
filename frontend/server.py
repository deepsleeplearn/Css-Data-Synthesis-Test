from __future__ import annotations

import asyncio
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
import random
from datetime import datetime, timedelta, timezone
from dataclasses import asdict, is_dataclass, replace
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
    from css_data_synthesis_test.agents import ServiceAgent, UserAgent
    from css_data_synthesis_test.cli import (
        _hydrate_manual_test_scenario_locally,
        _manual_test_requires_generated_hidden_settings,
        _resolve_interactive_max_rounds,
    )
    from css_data_synthesis_test.config import (
        DEFAULT_PRODUCT_ROUTING_BRAND_SERIES_WEIGHTS,
        DEFAULT_PRODUCT_ROUTING_ENTRY_WEIGHTS,
        DEFAULT_PRODUCT_ROUTING_HISTORY_CONFIRMATION_WEIGHTS,
        DEFAULT_AUTO_MODE_IVR_PRODUCT_KIND_WEIGHTS,
        DEFAULT_AUTO_MODE_HISTORY_DEVICE_BRAND_WEIGHTS,
        DEFAULT_AUTO_MODE_HISTORY_DEVICE_CATEGORY_WEIGHTS,
        DEFAULT_AUTO_MODE_WATER_HEATER_OPENING_REPLY_WEIGHTS,
        DEFAULT_PRODUCT_ROUTING_PROPERTY_YEAR_WEIGHTS,
        DEFAULT_PRODUCT_ROUTING_PURCHASE_OR_PROPERTY_WEIGHTS,
        DEFAULT_PRODUCT_ROUTING_USAGE_SCENE_WEIGHTS,
        load_config,
    )
    from css_data_synthesis_test.function_call import (
        build_address_model_observation,
        build_ie_model_observation,
        build_telephone_model_observation,
        format_address_observation_line,
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
        planned_product_routing_step,
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
FRONTEND_MODEL_OPTIONS = ("gpt-4o", "qwen3-32b")

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
auto_mode_jobs: dict[str, dict[str, Any]] = {}
AUTO_MODE_JOB_LOCK = threading.RLock()
SESSION_REVIEW_DB_PATH = PROJECT_ROOT / "outputs" / "frontend_manual_test.sqlite3"
SESSION_REVIEW_DB_LOCK = threading.RLock()
_SESSION_REVIEW_DB_STATE_PATH: Path | None = None
_SESSION_REVIEW_DB_SCHEMA_READY = False
_SESSION_REVIEW_DB_NORMALIZED = False
REWRITE_REVIEW_DB_PATH = PROJECT_ROOT / "outputs" / "frontend_rewrite_review.sqlite3"
REWRITE_REVIEW_DB_LOCK = threading.RLock()
_REWRITE_REVIEW_DB_SCHEMA_READY = False
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


def _normalize_frontend_model_name(model_name: str) -> str:
    normalized = str(model_name or "").strip()
    if normalized in FRONTEND_MODEL_OPTIONS:
        return normalized
    configured_default = str(getattr(config, "default_model", "") or "").strip()
    if configured_default in FRONTEND_MODEL_OPTIONS:
        return configured_default
    return "gpt-4o"


def _config_for_model(model_name: str):
    normalized_model = _normalize_frontend_model_name(model_name)
    endpoints = getattr(config, "model_endpoints", {}) or {}
    selected_endpoint = dict(endpoints.get(normalized_model, {}))
    selected_base_url = str(selected_endpoint.get("base_url") or getattr(config, "openai_base_url", "") or "")
    selected_api_key = str(selected_endpoint.get("api_key") or getattr(config, "openai_api_key", "") or "")
    selected_user = str(selected_endpoint.get("user") or getattr(config, "user", "") or "")
    if is_dataclass(config):
        return replace(
            config,
            default_model=normalized_model,
            user_agent_model=normalized_model,
            service_agent_model=normalized_model,
            openai_base_url=selected_base_url,
            openai_api_key=selected_api_key,
            user=selected_user,
        )
    active_config = copy.copy(config)
    setattr(active_config, "default_model", normalized_model)
    setattr(active_config, "user_agent_model", normalized_model)
    setattr(active_config, "service_agent_model", normalized_model)
    if not hasattr(active_config, "model_endpoints"):
        setattr(active_config, "model_endpoints", {})
    if not hasattr(active_config, "openai_base_url"):
        setattr(active_config, "openai_base_url", "")
    if not hasattr(active_config, "openai_api_key"):
        setattr(active_config, "openai_api_key", "")
    if not hasattr(active_config, "user"):
        setattr(active_config, "user", "")
    active_config.openai_base_url = selected_base_url
    active_config.openai_api_key = selected_api_key
    active_config.user = selected_user
    if not hasattr(active_config, "request_timeout"):
        setattr(active_config, "request_timeout", 90.0)
    if not hasattr(active_config, "second_round_include_issue_probability"):
        setattr(active_config, "second_round_include_issue_probability", 0.4)
    return active_config


def _client_for_model(model_name: str) -> OpenAIChatClient:
    return OpenAIChatClient(_config_for_model(model_name))


def _disable_unavailable_model_callbacks(agent: ServiceAgent, active_config: Any) -> ServiceAgent:
    if str(getattr(active_config, "openai_api_key", "") or "").strip():
        return agent
    # Unit tests and offline runs often stub config without credentials. Keep the
    # original deterministic routing fallback instead of forcing a failed model call.
    agent.policy.product_routing_intent_inference_callback = None
    return agent


def _build_service_policy(model_name: str = ""):
    active_config = _config_for_model(model_name)
    service_agent = ServiceAgent(
        OpenAIChatClient(active_config),
        model=active_config.service_agent_model,
        temperature=active_config.default_temperature,
        ok_prefix_probability=active_config.service_ok_prefix_probability,
        query_prefix_weights=active_config.service_query_prefix_weights,
        product_routing_enabled=active_config.product_routing_enabled,
        product_routing_apply_probability=active_config.product_routing_apply_probability,
    )
    _disable_unavailable_model_callbacks(service_agent, active_config)
    return service_agent.policy


def _build_service_agent(model_name: str = "") -> ServiceAgent:
    active_config = _config_for_model(model_name)
    service_agent = ServiceAgent(
        OpenAIChatClient(active_config),
        model=active_config.service_agent_model,
        temperature=active_config.default_temperature,
        ok_prefix_probability=active_config.service_ok_prefix_probability,
        query_prefix_weights=active_config.service_query_prefix_weights,
        product_routing_enabled=active_config.product_routing_enabled,
        product_routing_apply_probability=active_config.product_routing_apply_probability,
    )
    return _disable_unavailable_model_callbacks(service_agent, active_config)


def _build_user_agent(model_name: str = "") -> UserAgent:
    active_config = _config_for_model(model_name)
    return UserAgent(
        OpenAIChatClient(active_config),
        model=active_config.user_agent_model,
        temperature=active_config.default_temperature,
        second_round_include_issue_probability=active_config.second_round_include_issue_probability,
    )


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
    product_category: str = ""
    request_type: str = ""
    model_name: str = "gpt-4o"
    history_device_brand: str = ""
    history_device_category: str = ""
    history_device_purchase_date: str = ""
    auto_generate_hidden_settings: bool = False
    known_address: str = ""
    ivr_utterance: str = ""
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
    entity_type: str = "addressInfo"


class RewriteIeObservationRequest(BaseModel):
    entity_type: str = "addressInfo"
    dialogue_lines: list[str] = []
    model_name: str = "gpt-4o"


class LoginRequest(BaseModel):
    username: str
    password: str


class ReviewSessionRequest(BaseModel):
    session_id: str
    is_correct: bool
    failed_flow_stage: str = ""
    notes: str = ""
    persist_to_db: bool = False


class RewriteReviewRequest(BaseModel):
    record_id: str
    record: dict[str, Any]


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


def _list_enabled_registered_accounts() -> list[dict[str, str]]:
    accounts = _load_registered_accounts()
    enabled_accounts = [
        {
            "username": str(account.get("username", "")).strip(),
            "display_name": str(account.get("display_name", "")).strip() or str(account.get("username", "")).strip(),
        }
        for account in accounts.values()
        if bool(account.get("enabled", True))
    ]
    return sorted(
        [item for item in enabled_accounts if item["username"]],
        key=lambda item: (str(item["display_name"]).lower(), str(item["username"]).lower()),
    )


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


def _apply_frontend_auto_address_policy_seed(scenario: Scenario, known_address: str) -> Scenario:
    hidden_context = dict(scenario.hidden_context)
    sanitized = _sanitize_manual_user_text(known_address)
    hidden_context.update(
        {
            "frontend_auto_address_policy_enabled": True,
            "frontend_auto_configured_known_address": sanitized,
        }
    )
    return scenario.with_generated_hidden_settings(
        customer=scenario.customer,
        request=scenario.request,
        hidden_context=hidden_context,
    )


def _frontend_auto_known_address_notice(scenario: Scenario, known_address: str) -> str:
    sanitized = _sanitize_manual_user_text(known_address)
    if sanitized:
        matches = bool(scenario.hidden_context.get("service_known_address_matches_actual", False))
        suffix = "真实地址与已知地址一致" if matches else "真实地址按概率生成为不同地址"
        return f"使用会话配置中的已知地址，客服将优先核对: {sanitized}；{suffix}。"
    return "会话配置未设置已知地址，客服将按未知地址采集。"


def _parse_history_device_purchase_date(value: str) -> tuple[str, str, str]:
    normalized = str(value or "").strip()
    if not normalized:
        return "", "", ""
    try:
        parsed = datetime.strptime(normalized, "%Y-%m-%d")
    except ValueError:
        return "", "", ""
    return normalized, str(parsed.year), str(parsed.month)


def _apply_manual_history_device(scenario: Scenario, req: StartSessionRequest) -> tuple[Scenario, str]:
    brand = _sanitize_manual_user_text(req.history_device_brand)
    category = _sanitize_manual_user_text(req.history_device_category)
    purchase_date, purchase_year, purchase_month = _parse_history_device_purchase_date(
        req.history_device_purchase_date
    )
    hidden_context = dict(scenario.hidden_context)
    if not (brand and category and purchase_date):
        hidden_context.update(
            {
                "product_routing_has_history_device": False,
                "air_energy_history_device": {},
            }
        )
        return (
            scenario.with_generated_hidden_settings(
                customer=scenario.customer,
                request=scenario.request,
                hidden_context=hidden_context,
            ),
            "未设置历史设备，归属流程按无历史设备处理。",
        )

    history_device = {
        "brand": brand,
        "category": category,
        "purchase_date": purchase_date,
        "purchase_year": purchase_year,
        "purchase_month": purchase_month,
    }
    hidden_context.update(
        {
            "product_routing_has_history_device": True,
            "air_energy_history_device": history_device,
        }
    )
    return (
        scenario.with_generated_hidden_settings(
            customer=scenario.customer,
            request=scenario.request,
            hidden_context=hidden_context,
        ),
        f"已设置历史设备: {purchase_year}年{purchase_month}月 {brand}{category}",
    )


def _attach_product_routing_weight_overrides(hidden_context: dict[str, Any]) -> None:
    def _config_weight_map(attr: str, default: dict[str, float]) -> dict[str, float]:
        value = getattr(config, attr, None)
        if isinstance(value, dict):
            return dict(value)
        return dict(default)

    hidden_context.update(
        {
            "product_routing_entry_weights": _config_weight_map(
                "product_routing_entry_weights",
                DEFAULT_PRODUCT_ROUTING_ENTRY_WEIGHTS,
            ),
            "product_routing_brand_series_weights": _config_weight_map(
                "product_routing_brand_series_weights",
                DEFAULT_PRODUCT_ROUTING_BRAND_SERIES_WEIGHTS,
            ),
            "product_routing_usage_scene_weights": _config_weight_map(
                "product_routing_usage_scene_weights",
                DEFAULT_PRODUCT_ROUTING_USAGE_SCENE_WEIGHTS,
            ),
            "product_routing_purchase_or_property_weights": _config_weight_map(
                "product_routing_purchase_or_property_weights",
                DEFAULT_PRODUCT_ROUTING_PURCHASE_OR_PROPERTY_WEIGHTS,
            ),
            "product_routing_property_year_weights": _config_weight_map(
                "product_routing_property_year_weights",
                DEFAULT_PRODUCT_ROUTING_PROPERTY_YEAR_WEIGHTS,
            ),
            "product_routing_history_confirmation_weights": _config_weight_map(
                "product_routing_history_confirmation_weights",
                DEFAULT_PRODUCT_ROUTING_HISTORY_CONFIRMATION_WEIGHTS,
            ),
        }
    )


def _reset_product_routing_plan(hidden_context: dict[str, Any]) -> None:
    for key in (
        "product_routing_plan",
        "product_routing_initial_plan",
        "product_routing_result",
        "product_routing_trace",
        "product_routing_summary",
    ):
        hidden_context.pop(key, None)


def _resolve_manual_call_start_time(req: StartSessionRequest, scenario: Scenario) -> str:
    if bool(req.use_session_start_time_as_call_start_time):
        return _current_display_timestamp()

    provided = _normalize_manual_call_start_time(req.call_start_time)
    if provided:
        return provided

    scenario_value = _coerce_scenario_call_start_time_to_display(scenario.call_start_time)
    return scenario_value or _current_display_timestamp()


def _normalize_ivr_request_type(value: str) -> str:
    normalized = str(value or "").strip().lower()
    if normalized in {"installation", "install", "安装"}:
        return "installation"
    if normalized in {"fault", "repair", "maintenance", "维修", "报修"}:
        return "fault"
    return ""


def _normalize_manual_product_category(value: str) -> str:
    normalized = str(value or "").strip()
    mapping = {
        "空气能热水机": "空气能热水机",
        "空气能热水器": "空气能热水机",
        "热水器": "热水器",
        "燃气热水器": "燃气热水器",
        "电热水器": "电热水器",
    }
    return mapping.get(normalized, "")


def _weighted_choice(weights: dict[str, float], default: str) -> str:
    normalized_weights: dict[str, float] = {}
    for key, value in (weights or {}).items():
        try:
            weight = max(0.0, float(value))
        except (TypeError, ValueError):
            weight = 0.0
        if weight > 0.0:
            normalized_weights[str(key)] = weight
    if not normalized_weights:
        return default
    return random.choices(
        population=list(normalized_weights.keys()),
        weights=list(normalized_weights.values()),
        k=1,
    )[0]


def _copy_start_request(req: StartSessionRequest, updates: dict[str, Any]) -> StartSessionRequest:
    payload = req.model_dump() if hasattr(req, "model_dump") else req.dict()
    payload.update(updates)
    return StartSessionRequest(**payload)


def _manual_product_category_slug(category: str) -> str:
    mapping = {
        "空气能热水机": "air_energy",
        "热水器": "water_heater",
        "燃气热水器": "gas_water_heater",
        "电热水器": "electric_water_heater",
    }
    return mapping.get(str(category or "").strip(), "air_energy")


def _resolve_manual_base_scenario(request_type: str) -> Scenario:
    normalized_request_type = _normalize_ivr_request_type(request_type) or "fault"
    scenarios = _load_scenarios()
    for scenario in scenarios:
        if str(scenario.request.request_type or "").strip() == normalized_request_type:
            return scenario
    return scenarios[0]


def _auto_mode_ivr_request(req: StartSessionRequest) -> tuple[StartSessionRequest, str]:
    request_type = _normalize_ivr_request_type(req.request_type) or "fault"
    action = "安装" if request_type == "installation" else "维修"
    product_kind = _weighted_choice(
        getattr(config, "auto_mode_ivr_product_kind_weights", DEFAULT_AUTO_MODE_IVR_PRODUCT_KIND_WEIGHTS),
        "air_energy",
    )
    if product_kind == "water_heater":
        return (
            _copy_start_request(
                req,
                {
                    "product_category": "热水器",
                    "request_type": request_type,
                    "ivr_utterance": f"热水器需要{action}",
                },
            ),
            "water_heater",
        )
    return (
        _copy_start_request(
            req,
            {
                "product_category": "空气能热水机",
                "request_type": request_type,
                "ivr_utterance": f"空气能热水器需要{action}",
            },
        ),
        "air_energy",
    )


def _history_device_category_options_for_brand(brand: str) -> list[str]:
    normalized_brand = str(brand or "").strip()
    if normalized_brand in {"COLMO", "真暖", "真省", "雪焰", "暖家", "煤改电", "真享"}:
        return ["家用空气能热水机"]
    if normalized_brand == "烈焰":
        return ["空气能热水机"]
    return ["家用空气能热水机", "空气能热水机"]


def _random_history_device_purchase_date() -> str:
    today = datetime.now(DISPLAY_TIMEZONE).date()
    start = today.replace(year=max(2018, today.year - 7), month=1, day=1)
    span_days = max(1, (today - start).days)
    return (start + timedelta(days=random.randint(0, span_days))).strftime("%Y-%m-%d")


def _auto_mode_history_device_request(req: StartSessionRequest) -> StartSessionRequest:
    probability = max(0.0, min(1.0, float(getattr(config, "auto_mode_history_device_probability", 0.35))))
    if random.random() >= probability:
        return _copy_start_request(
            req,
            {
                "history_device_brand": "",
                "history_device_category": "",
                "history_device_purchase_date": "",
            },
        )

    brand = _weighted_choice(
        getattr(
            config,
            "auto_mode_history_device_brand_weights",
            DEFAULT_AUTO_MODE_HISTORY_DEVICE_BRAND_WEIGHTS,
        ),
        "美的",
    )
    allowed_categories = set(_history_device_category_options_for_brand(brand))
    raw_category_weights = getattr(
        config,
        "auto_mode_history_device_category_weights",
        DEFAULT_AUTO_MODE_HISTORY_DEVICE_CATEGORY_WEIGHTS,
    )
    category_weights = {
        key: value
        for key, value in dict(raw_category_weights).items()
        if str(key).strip() in allowed_categories
    }
    category = _weighted_choice(category_weights, next(iter(allowed_categories)))
    return _copy_start_request(
        req,
        {
            "history_device_brand": brand,
            "history_device_category": category,
            "history_device_purchase_date": _random_history_device_purchase_date(),
        },
    )


def _opposite_request_type(request_type: str) -> str:
    return "fault" if _normalize_ivr_request_type(request_type) == "installation" else "installation"


def _request_action_label(request_type: str) -> str:
    return "安装" if _normalize_ivr_request_type(request_type) == "installation" else "维修"


def _build_water_heater_opening_reply_plan(scenario: Scenario) -> dict[str, str]:
    hidden_context = scenario.hidden_context if isinstance(scenario.hidden_context, dict) else {}
    if str(hidden_context.get("ivr_product_kind", "")).strip() != "water_heater":
        return {}

    strategy = _weighted_choice(
        getattr(
            config,
            "auto_mode_water_heater_opening_reply_weights",
            DEFAULT_AUTO_MODE_WATER_HEATER_OPENING_REPLY_WEIGHTS,
        ),
        "confirm",
    )
    current_request_type = _normalize_ivr_request_type(scenario.request.request_type) or "fault"
    changed_request_type = _opposite_request_type(current_request_type)
    changed_action = _request_action_label(changed_request_type)
    reply_map = {
        "confirm": "对，是的。",
        "change_brand": "是的，COLMO的。",
        "change_product_type": "对，是空气能热水器。",
        "change_request": f"不是，是{changed_action}。",
        "change_brand_request": f"COLMO的，是{changed_action}。",
    }
    label_map = {
        "confirm": "仅确认品牌/品类/诉求，不修改",
        "change_brand": "修改品牌为 COLMO",
        "change_product_type": "补充细分品类为空气能热水器",
        "change_request": f"修改诉求为{changed_action}",
        "change_brand_request": f"修改品牌为 COLMO，并修改诉求为{changed_action}",
    }
    return {
        "strategy": strategy,
        "label": label_map.get(strategy, label_map["confirm"]),
        "reply": reply_map.get(strategy, reply_map["confirm"]),
    }


def _attach_auto_mode_opening_reply_plan(scenario: Scenario) -> None:
    plan = _build_water_heater_opening_reply_plan(scenario)
    if not plan:
        return
    scenario.hidden_context["auto_mode_water_heater_opening_reply_strategy"] = plan["strategy"]
    scenario.hidden_context["auto_mode_water_heater_opening_reply_label"] = plan["label"]
    scenario.hidden_context["auto_mode_water_heater_opening_reply"] = plan["reply"]


def _apply_manual_session_configuration(
    scenario: Scenario,
    *,
    product_category: str,
    request_type: str,
    ivr_utterance: str,
    preserve_request_details: bool = False,
) -> tuple[Scenario, str, bool]:
    normalized_product_category = _normalize_manual_product_category(product_category) or "空气能热水机"
    normalized_request_type = _normalize_ivr_request_type(request_type) or "fault"
    action = "安装" if normalized_request_type == "installation" else "维修"
    sanitized_ivr = _sanitize_manual_user_text(ivr_utterance)
    hidden_context = dict(scenario.hidden_context)
    hidden_context.update(
        {
            "manual_product_category": normalized_product_category,
            "manual_request_type": normalized_request_type,
            "ivr_utterance": sanitized_ivr,
            "ivr_request_type": normalized_request_type,
            "ivr_product_kind": (
                "water_heater"
                if normalized_product_category == "热水器"
                else "air_energy"
                if normalized_product_category == "空气能热水机"
                else ""
            ),
            "ivr_opening_overridden": normalized_product_category == "热水器",
        }
    )
    configured = replace(
        scenario,
        scenario_id=f"manual_config_{_manual_product_category_slug(normalized_product_category)}_{normalized_request_type}",
        product=replace(scenario.product, category=normalized_product_category),
        request=replace(
            scenario.request,
            request_type=normalized_request_type,
            issue=(
                scenario.request.issue
                if preserve_request_details and _sanitize_manual_user_text(scenario.request.issue)
                else f"{normalized_product_category}需要{action}"
            ),
            desired_resolution=(
                scenario.request.desired_resolution
                if preserve_request_details and _sanitize_manual_user_text(scenario.request.desired_resolution)
                else f"安排{action}"
            ),
        ),
        hidden_context=hidden_context,
    )
    ivr_notice = (
        f"已记录 IVR 原话: {sanitized_ivr}；首轮仍按当前产品和诉求配置启动。"
        if sanitized_ivr
        else f"首轮将按当前配置固定生成: 美的{normalized_product_category}需要{action}"
    )
    return configured, ivr_notice, True


def _infer_ivr_request_type(text: str) -> str:
    normalized = str(text or "").strip()
    if re.search(r"(安装|装机|安装一下|上门安装)", normalized):
        return "installation"
    if re.search(r"(维修|报修|修一下|坏了|故障|不出热水|漏水|不启动|异常)", normalized):
        return "fault"
    return ""


def _infer_ivr_product_kind(text: str) -> str:
    normalized = str(text or "").strip()
    if "空气能" in normalized:
        return "air_energy"
    if re.search(r"(热水器|热水机)", normalized):
        return "water_heater"
    return ""


def _classify_ivr_opening_with_model(
    ivr_text: str,
    *,
    active_client: OpenAIChatClient | None = None,
    active_config: Any | None = None,
) -> dict[str, str]:
    sanitized = _sanitize_manual_user_text(ivr_text)
    if not sanitized:
        return {"product_kind": "", "request_type": ""}
    resolved_client = active_client or llm_client
    resolved_config = active_config or config
    system_prompt = """你是家电客服电话 IVR 首轮意图识别助手。

任务：只根据用户在进入人工客服前的一句 IVR 诉求，判断产品意图和诉求类型。

分类规则：
1. product_kind 只允许输出：
   - air_energy: 用户明确表达的是空气能、空气能热水器、空气能热水机
   - water_heater: 用户只表达热水器/热水机，看不出是空气能
   - unknown: 看不出来
2. request_type 只允许输出：
   - installation: 安装
   - fault: 维修/报修/故障处理
   - unknown: 看不出来
3. 只有明确出现“空气能”或等价表达时，才能判为 air_energy。
4. 只说“热水器”“热水机”时，一律判为 water_heater。

只返回 JSON：
{
  "product_kind": "air_energy|water_heater|unknown",
  "request_type": "installation|fault|unknown"
}"""
    try:
        payload = resolved_client.complete_json(
            model=resolved_config.service_agent_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"IVR原话: {sanitized}\n只返回 JSON。"},
            ],
            temperature=0.0,
        )
    except Exception:
        return {"product_kind": "", "request_type": ""}
    return {
        "product_kind": str(payload.get("product_kind", "")).strip(),
        "request_type": str(payload.get("request_type", "")).strip(),
    }


def _apply_ivr_opening_override(
    scenario: Scenario,
    ivr_utterance: str,
    *,
    active_client: OpenAIChatClient | None = None,
    active_config: Any | None = None,
) -> tuple[Scenario, str, bool]:
    sanitized = _sanitize_manual_user_text(ivr_utterance)
    if not sanitized:
        return scenario, "", False

    inferred_request_type = _infer_ivr_request_type(sanitized)
    inferred_product_kind = _infer_ivr_product_kind(sanitized)
    model_result = _classify_ivr_opening_with_model(
        sanitized,
        active_client=active_client,
        active_config=active_config,
    )

    request_type = _normalize_ivr_request_type(model_result.get("request_type", "")) or inferred_request_type
    product_kind = str(model_result.get("product_kind", "")).strip().lower() or inferred_product_kind

    if product_kind not in {"air_energy", "water_heater"} or request_type not in {"installation", "fault"}:
        return scenario, f"已记录 IVR 原话，但未触发首轮固定覆写: {sanitized}", False

    category = "空气能热水机" if product_kind == "air_energy" else "热水器"
    action = "安装" if request_type == "installation" else "维修"
    hidden_context = dict(scenario.hidden_context)
    hidden_context.update(
        {
            "ivr_utterance": sanitized,
            "ivr_product_kind": product_kind,
            "ivr_request_type": request_type,
            "ivr_opening_overridden": True,
        }
    )
    updated_scenario = replace(
        scenario,
        product=replace(scenario.product, category=category),
        request=replace(
            scenario.request,
            request_type=request_type,
            issue=sanitized,
            desired_resolution=f"安排{action}",
        ),
        hidden_context=hidden_context,
    )
    return (
        updated_scenario,
        f"IVR 首轮固定为: 美的{category}需要{action}",
        True,
    )


def _prepare_manual_test_scenario(
    req: StartSessionRequest,
    *,
    force_local_hidden_settings: bool = False,
    frontend_auto_address_policy: bool = False,
) -> tuple[Scenario, str, int, str, bool]:
    active_config = _config_for_model(req.model_name)
    active_client = OpenAIChatClient(active_config)
    manual_request_type = _normalize_ivr_request_type(req.request_type)
    manual_product_category = _normalize_manual_product_category(req.product_category)
    if manual_request_type or manual_product_category:
        scenario = _resolve_manual_base_scenario(manual_request_type or "fault")
    else:
        scenario = _resolve_scenario(
            scenario_id=req.scenario_id,
            scenario_index=req.scenario_index,
        )

    if frontend_auto_address_policy:
        scenario = _apply_frontend_auto_address_policy_seed(scenario, req.known_address)

    if req.auto_generate_hidden_settings:
        if not active_config.openai_api_key or "YOUR_API_KEY" in active_config.openai_api_key:
            raise ValueError("未配置所选模型的 API_KEY，请检查 .env 文件。")
        tool = HiddenSettingsTool(active_client, active_config)
        scenario = tool.generate_for_scenario(
            scenario,
            use_utterance_reference=True,
        )
    elif force_local_hidden_settings:
        tool = HiddenSettingsTool(active_client, active_config)
        scenario = tool.hydrate_scenario_locally(scenario)
    elif _manual_test_requires_generated_hidden_settings(scenario):
        scenario = _hydrate_manual_test_scenario_locally(scenario)

    scenario = scenario.with_call_start_time(_resolve_manual_call_start_time(req, scenario))
    if frontend_auto_address_policy:
        known_address_notice = _frontend_auto_known_address_notice(scenario, req.known_address)
    else:
        scenario, known_address_notice = _apply_known_address(scenario, req.known_address)
    scenario, history_device_notice = _apply_manual_history_device(scenario, req)
    if manual_request_type or manual_product_category:
        scenario, ivr_notice, ivr_opening_enabled = _apply_manual_session_configuration(
            scenario,
            product_category=manual_product_category or "空气能热水机",
            request_type=manual_request_type or "fault",
            ivr_utterance=req.ivr_utterance,
            preserve_request_details=bool(req.auto_generate_hidden_settings),
        )
    else:
        scenario, ivr_notice, ivr_opening_enabled = _apply_ivr_opening_override(
            scenario,
            req.ivr_utterance,
            active_client=active_client,
            active_config=active_config,
        )
    _attach_product_routing_weight_overrides(scenario.hidden_context)
    _reset_product_routing_plan(scenario.hidden_context)
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
    combined_notice = (
        f"{known_address_notice}；{history_device_notice}"
        if history_device_notice.startswith("已设置历史设备")
        else known_address_notice
    )
    return scenario, combined_notice, rounds_limit, ivr_notice, ivr_opening_enabled


def _format_bool_zh(value: Any) -> str:
    return "是" if bool(value) else "否"


def _build_auto_mode_preview_lines(scenario: Scenario) -> list[str]:
    hidden_context = scenario.hidden_context if isinstance(scenario.hidden_context, dict) else {}
    request_action = _request_action_label(str(scenario.request.request_type or ""))
    ivr_product_kind = str(hidden_context.get("ivr_product_kind", "")).strip()
    scenario_category = str(scenario.product.category or "").strip()
    if ivr_product_kind == "water_heater" or scenario_category == "热水器":
        ivr_product_label = "热水器"
    else:
        ivr_product_label = "空气能热水机"
    lines = [
        f"IVR首轮: 美的{ivr_product_label}需要{request_action}",
    ]

    opening_reply = str(hidden_context.get("auto_mode_water_heater_opening_reply", "")).strip()
    opening_label = str(hidden_context.get("auto_mode_water_heater_opening_reply_label", "")).strip()
    if opening_reply:
        lines.append(f"用户品牌品类确认策略: {opening_label}；预期回复: {opening_reply}")
    else:
        lines.append("用户品牌品类确认策略: 按常规开场确认/问题描述策略执行。")

    history_device = hidden_context.get("air_energy_history_device")
    if isinstance(history_device, dict) and history_device:
        brand = str(history_device.get("brand", "")).strip()
        category = str(history_device.get("category", "")).strip()
        year = str(history_device.get("purchase_year", "")).strip()
        month = str(history_device.get("purchase_month", "")).strip()
        lines.append(f"历史设备相关信息: 有；{year}年{month}月 {brand}{category}。")
    else:
        lines.append("历史设备相关信息: 无。")

    routing_summary = str(hidden_context.get("product_routing_summary", "")).strip()
    if routing_summary:
        lines.append(f"产品归属路径: {routing_summary}")
    else:
        lines.append("产品归属路径: 本次未预设或未触发产品归属中间路由。")

    contactable = bool(hidden_context.get("current_call_contactable", True))
    phone_attempts = str(hidden_context.get("phone_input_attempts_required", "0")).strip() or "0"
    phone_owner = str(hidden_context.get("contact_phone_owner_spoken_label", "")).strip() or "本人当前来电"
    if contactable:
        lines.append("电话沟通策略: 当前来电号码可联系，用户会确认当前号码。")
    else:
        lines.append(f"电话沟通策略: 当前来电不可联系，登记{phone_owner}；拨号盘第 {phone_attempts} 次输入有效号码。")

    service_known_address = bool(hidden_context.get("service_known_address", False))
    service_address = str(hidden_context.get("service_known_address_value", "")).strip()
    service_address_matches = bool(hidden_context.get("service_known_address_matches_actual", False))
    address_rounds = hidden_context.get("address_input_rounds", [])
    if not isinstance(address_rounds, list):
        address_rounds = []
    normalized_rounds = [str(item).strip() for item in address_rounds if str(item).strip()]
    if service_known_address:
        lines.append(
            "地址沟通策略: 客服先核对已知地址；"
            f"地址是否正确: {_format_bool_zh(service_address_matches)}；"
            f"核对地址: {service_address or '未提供'}。"
        )
    else:
        rounds_text = " / ".join(normalized_rounds) if normalized_rounds else str(scenario.customer.address or "").strip()
        lines.append(f"地址沟通策略: 客服从零采集地址；用户分段回复计划: {rounds_text or '未设置'}。")
    return lines


def _create_auto_mode_job(req: StartSessionRequest) -> tuple[str, dict[str, Any]]:
    selected_model_name = _normalize_frontend_model_name(req.model_name)
    req, _ = _auto_mode_ivr_request(req)
    req = _auto_mode_history_device_request(req)
    scenario, _known_address_notice, rounds_limit, _ivr_notice, ivr_opening_enabled = _prepare_manual_test_scenario(
        req,
        force_local_hidden_settings=not bool(req.auto_generate_hidden_settings),
        frontend_auto_address_policy=True,
    )
    _attach_auto_mode_opening_reply_plan(scenario)
    scenario = replace(scenario, max_turns=rounds_limit)
    auto_mode_preview_lines = _build_auto_mode_preview_lines(scenario)
    required_slots = effective_required_slots(scenario)
    collected_slots = {slot: "" for slot in required_slots}
    for slot in SUPPLEMENTARY_COLLECTED_SLOTS:
        collected_slots.setdefault(slot, "")
    collected_slots["product_routing_result"] = str(
        scenario.hidden_context.get("product_routing_result", "")
    ).strip()

    started_at = _current_display_timestamp()
    auto_mode_id = f"auto-{datetime.now(DISPLAY_TIMEZONE).strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:8]}"
    session = {
        "auto_mode_id": auto_mode_id,
        "model_name": selected_model_name,
        "scenario": scenario,
        "runtime_state": ServiceRuntimeState(),
        "transcript": [],
        "terminal_entries": [],
        "auto_mode_preview_lines": auto_mode_preview_lines,
        "required_slots": required_slots,
        "collected_slots": collected_slots,
        "rounds_limit": rounds_limit,
        "status": "active",
        "started_at": started_at,
        "ended_at": "",
        "session_config": {
            "scenario_id": scenario.scenario_id,
            "model_name": selected_model_name,
            "product_category": str(req.product_category or "").strip(),
            "request_type": str(req.request_type or "").strip(),
            "history_device_brand": str(req.history_device_brand or "").strip(),
            "history_device_category": str(req.history_device_category or "").strip(),
            "history_device_purchase_date": str(req.history_device_purchase_date or "").strip(),
            "known_address": _sanitize_manual_user_text(req.known_address),
            "ivr_utterance": _sanitize_manual_user_text(req.ivr_utterance),
            "ivr_opening_enabled": bool(ivr_opening_enabled),
            "call_start_time": scenario.call_start_time,
            "use_session_start_time_as_call_start_time": bool(req.use_session_start_time_as_call_start_time),
            "max_rounds": req.max_rounds,
            "auto_generate_hidden_settings": bool(req.auto_generate_hidden_settings),
            "persist_to_db": bool(req.persist_to_db),
        },
    }
    job_id = str(uuid.uuid4())
    job = {
        "session": session,
        "done": False,
        "error": "",
        "abort_requested": False,
        "created_at": time.time(),
        "updated_at": time.time(),
    }
    with AUTO_MODE_JOB_LOCK:
        auto_mode_jobs[job_id] = job
    return job_id, job


def _build_auto_mode_job_view(job_id: str, job: dict[str, Any]) -> dict[str, Any]:
    session = job["session"]
    transcript = session["transcript"]
    return {
        "job_id": job_id,
        "auto_mode_id": str(session.get("auto_mode_id", "")).strip(),
        "mode": "auto_mode",
        "status": session["status"],
        "scenario": session["scenario"].to_dict(),
        "session_config": dict(session.get("session_config", {})),
        "required_slots": list(session["required_slots"]),
        "collected_slots": dict(session["collected_slots"]),
        "runtime_state": _build_runtime_state_view(session),
        "rounds_limit": session["rounds_limit"],
        "started_at": str(session.get("started_at", "")).strip(),
        "ended_at": str(session.get("ended_at", "")).strip(),
        "session_closed": bool(job.get("done")),
        "next_round_index": _next_round_index(transcript),
        "completed_rounds": _completed_round_count(transcript),
        "terminal_entries": _copy_terminal_entries(session.get("terminal_entries", [])),
        "auto_mode_preview_lines": [
            str(line).strip()
            for line in session.get("auto_mode_preview_lines", [])
            if str(line).strip()
        ],
        "job_done": bool(job.get("done")),
        "job_error": str(job.get("error", "")).strip(),
    }


def _normalize_auto_mode_service_action(
    action: dict[str, Any] | ServicePolicyResult,
    *,
    policy: ServiceDialoguePolicy,
) -> dict[str, Any]:
    if isinstance(action, ServicePolicyResult):
        normalized = {
            "reply": action.reply,
            "slot_updates": dict(action.slot_updates),
            "is_ready_to_close": bool(action.is_ready_to_close),
            "close_status": str(action.close_status or "").strip(),
            "close_reason": str(action.close_reason or "").strip(),
            "used_model_intent_inference": bool(
                getattr(policy, "last_used_model_intent_inference", False)
            ),
            "model_intent_inference_attempted": bool(
                getattr(
                    policy,
                    "last_model_intent_inference_attempted",
                    getattr(policy, "last_used_model_intent_inference", False),
                )
            ),
        }
        normalized["model_intent_inference_unapplied"] = bool(
            normalized["model_intent_inference_attempted"]
            and not normalized["used_model_intent_inference"]
        )
        return normalized
    normalized = {
        "reply": str(action.get("reply", "")).strip(),
        "slot_updates": dict(action.get("slot_updates", {})),
        "is_ready_to_close": bool(action.get("is_ready_to_close", False)),
        "close_status": str(action.get("close_status", "")).strip(),
        "close_reason": str(action.get("close_reason", "")).strip(),
        "used_model_intent_inference": bool(action.get("used_model_intent_inference", False)),
        "model_intent_inference_attempted": bool(
            action.get("model_intent_inference_attempted", action.get("used_model_intent_inference", False))
        ),
    }
    normalized["model_intent_inference_unapplied"] = bool(
        normalized["model_intent_inference_attempted"]
        and not normalized["used_model_intent_inference"]
    )
    return normalized


def _finalize_auto_mode_job(
    job_id: str,
    *,
    status_value: str = "",
    error_message: str = "",
) -> None:
    with AUTO_MODE_JOB_LOCK:
        job = auto_mode_jobs.get(job_id)
        if not job:
            return
        session = job["session"]
        session["status"] = status_value or ("error" if error_message else session.get("status", "completed"))
        session["ended_at"] = _current_display_timestamp()
        if error_message:
            _append_terminal_lines(
                session,
                lines=[f"[自动模式错误] {error_message}"],
                tone="error",
                round_count_snapshot=_completed_round_count(session.get("transcript", [])),
            )
        job["done"] = True
        job["error"] = error_message
        job["updated_at"] = time.time()


def _is_auto_mode_abort_requested(job_id: str) -> bool:
    with AUTO_MODE_JOB_LOCK:
        job = auto_mode_jobs.get(job_id)
        if not job:
            return True
        return bool(job.get("abort_requested"))


def _run_auto_mode_job_thread(job_id: str) -> None:
    asyncio.run(_run_auto_mode_job_async(job_id))


async def _run_auto_mode_job_async(job_id: str) -> None:
    with AUTO_MODE_JOB_LOCK:
        job = auto_mode_jobs.get(job_id)
        if not job:
            return
        session = job["session"]
        scenario = session["scenario"]
        runtime_state = session["runtime_state"]
        transcript = session["transcript"]
        collected_slots = session["collected_slots"]
        required_slots = session["required_slots"]
        rounds_limit = int(session["rounds_limit"])
        job["updated_at"] = time.time()

    model_name = str(session.get("model_name") or session.get("session_config", {}).get("model_name") or "").strip()
    service_agent = _build_service_agent(model_name)
    user_agent = _build_user_agent(model_name)
    active_config = _config_for_model(model_name)
    active_client = OpenAIChatClient(active_config)

    try:
        if _is_auto_mode_abort_requested(job_id):
            _finalize_auto_mode_job(job_id, status_value="aborted", error_message="已强制结束自动模式。")
            return
        initial_user_utterance = service_agent.build_initial_user_utterance(scenario)
        opening_user_turn = DialogueTurn(
            speaker=USER_SPEAKER,
            text=initial_user_utterance,
            round_index=1,
        )
        with AUTO_MODE_JOB_LOCK:
            transcript.append(opening_user_turn)
            _append_turn_entry(session, opening_user_turn)
            job["updated_at"] = time.time()
        if _is_auto_mode_abort_requested(job_id):
            _finalize_auto_mode_job(job_id, status_value="aborted", error_message="已强制结束自动模式。")
            return

        opening_action = _normalize_auto_mode_service_action(
            service_agent.respond(
                scenario=scenario,
                transcript=transcript,
                collected_slots=collected_slots,
                runtime_state=runtime_state,
            ),
            policy=service_agent.policy,
        )
        opening_service_turn = DialogueTurn(
            speaker=SERVICE_SPEAKER,
            text=opening_action["reply"],
            round_index=1,
            model_intent_inference_used=bool(opening_action.get("used_model_intent_inference", False)),
            model_intent_inference_attempted=bool(opening_action.get("model_intent_inference_attempted", False)),
            model_intent_inference_unapplied=bool(opening_action.get("model_intent_inference_unapplied", False)),
            previous_user_intent_model_inference_used=bool(
                opening_action.get("used_model_intent_inference", False)
            ),
            previous_user_intent_model_inference_attempted=bool(
                opening_action.get("model_intent_inference_attempted", False)
            ),
            previous_user_intent_model_inference_unapplied=bool(
                opening_action.get("model_intent_inference_unapplied", False)
            ),
        )
        with AUTO_MODE_JOB_LOCK:
            _merge_slots(collected_slots, opening_action["slot_updates"], required_slots)
            _merge_slots(
                collected_slots,
                opening_action["slot_updates"],
                list(SUPPLEMENTARY_COLLECTED_SLOTS),
            )
            transcript.append(opening_service_turn)
            _append_turn_entry(session, opening_service_turn)
            job["updated_at"] = time.time()
        if _is_auto_mode_abort_requested(job_id):
            _finalize_auto_mode_job(job_id, status_value="aborted", error_message="已强制结束自动模式。")
            return

        ready_to_close = opening_action["is_ready_to_close"]
        forced_close_status = str(opening_action.get("close_status", "")).strip()

        if not forced_close_status and not (
            ready_to_close and _all_required_slots_filled(collected_slots, required_slots)
        ):
            for round_index in range(2, rounds_limit + 1):
                if _is_auto_mode_abort_requested(job_id):
                    _finalize_auto_mode_job(job_id, status_value="aborted", error_message="已强制结束自动模式。")
                    return
                user_action = await user_agent.respond_async(
                    scenario=scenario,
                    transcript=transcript,
                    round_index=round_index,
                )
                user_turn = DialogueTurn(
                    speaker=USER_SPEAKER,
                    text=user_action["reply"],
                    round_index=round_index,
                )
                _append_phone_ie_display_lines(
                    policy=service_agent.policy,
                    turn=user_turn,
                    transcript=transcript + [user_turn],
                    runtime_state=runtime_state,
                    client=active_client,
                    model=active_config.service_agent_model,
                )
                auto_address_observation = _append_address_ie_display_lines(
                    policy=service_agent.policy,
                    turn=user_turn,
                    transcript=transcript + [user_turn],
                    runtime_state=runtime_state,
                    client=active_client,
                    model=active_config.service_agent_model,
                )
                with AUTO_MODE_JOB_LOCK:
                    transcript.append(user_turn)
                    _append_turn_entry(session, user_turn)
                    job["updated_at"] = time.time()
                if _is_auto_mode_abort_requested(job_id):
                    _finalize_auto_mode_job(job_id, status_value="aborted", error_message="已强制结束自动模式。")
                    return

                service_action = _build_auto_address_confirmation_result(
                    policy=service_agent.policy,
                    runtime_state=runtime_state,
                    observation=auto_address_observation,
                )
                if service_action is None:
                    service_action = _normalize_auto_mode_service_action(
                        service_agent.respond(
                            scenario=scenario,
                            transcript=transcript,
                            collected_slots=collected_slots,
                            runtime_state=runtime_state,
                        ),
                        policy=service_agent.policy,
                    )
                else:
                    service_action = _normalize_auto_mode_service_action(
                        service_action,
                        policy=service_agent.policy,
                    )
                service_turn = DialogueTurn(
                    speaker=SERVICE_SPEAKER,
                    text=service_action["reply"],
                    round_index=round_index,
                    model_intent_inference_used=bool(
                        service_action.get("used_model_intent_inference", False)
                    ),
                    model_intent_inference_attempted=bool(
                        service_action.get("model_intent_inference_attempted", False)
                    ),
                    model_intent_inference_unapplied=bool(
                        service_action.get("model_intent_inference_unapplied", False)
                    ),
                    previous_user_intent_model_inference_used=bool(
                        service_action.get("used_model_intent_inference", False)
                    ),
                    previous_user_intent_model_inference_attempted=bool(
                        service_action.get("model_intent_inference_attempted", False)
                    ),
                    previous_user_intent_model_inference_unapplied=bool(
                        service_action.get("model_intent_inference_unapplied", False)
                    ),
                )
                with AUTO_MODE_JOB_LOCK:
                    _merge_slots(collected_slots, service_action["slot_updates"], required_slots)
                    _merge_slots(
                        collected_slots,
                        service_action["slot_updates"],
                        list(SUPPLEMENTARY_COLLECTED_SLOTS),
                    )
                    transcript.append(service_turn)
                    _append_turn_entry(session, service_turn)
                    job["updated_at"] = time.time()
                if _is_auto_mode_abort_requested(job_id):
                    _finalize_auto_mode_job(job_id, status_value="aborted", error_message="已强制结束自动模式。")
                    return

                ready_to_close = service_action["is_ready_to_close"]
                forced_close_status = str(service_action.get("close_status", "")).strip()
                if forced_close_status:
                    break
                if ready_to_close and _all_required_slots_filled(collected_slots, required_slots):
                    break

        missing_slots = [
            slot for slot in required_slots if not collected_slots.get(slot, "").strip()
        ]
        status_value = forced_close_status or (
            "completed" if ready_to_close and not missing_slots else "incomplete"
        )
        _finalize_auto_mode_job(job_id, status_value=status_value)
    except Exception as exc:
        traceback.print_exc()
        _finalize_auto_mode_job(job_id, status_value="error", error_message=str(exc))


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
                model_intent_inference_attempted=bool(item.get("model_intent_inference_attempted", False)),
                model_intent_inference_unapplied=bool(item.get("model_intent_inference_unapplied", False)),
                previous_user_intent_model_inference_used=item.get("previous_user_intent_model_inference_used"),
                previous_user_intent_model_inference_attempted=item.get("previous_user_intent_model_inference_attempted"),
                previous_user_intent_model_inference_unapplied=item.get("previous_user_intent_model_inference_unapplied"),
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


def _restore_checkpoint_index_for_round(
    session: dict[str, Any],
    *,
    round_index: int,
) -> int:
    checkpoints = list(session.get("checkpoints", []))
    if not checkpoints:
        return max(int(round_index) - 1, 0)

    target_round = int(round_index or 0)
    best_index = 0
    best_source_round = -1
    for checkpoint in checkpoints:
        if not isinstance(checkpoint, dict):
            continue
        checkpoint_index = int(checkpoint.get("checkpoint_index", 0) or 0)
        source_round_index = int(checkpoint.get("source_round_index", 0) or 0)
        if source_round_index >= target_round:
            continue
        if source_round_index >= best_source_round:
            best_source_round = source_round_index
            best_index = checkpoint_index
    return max(best_index, 0)


def _serialize_session_for_storage(session: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "username": str(session.get("username", "")).strip(),
        "model_name": _normalize_frontend_model_name(
            str(session.get("model_name") or session.get("session_config", {}).get("model_name") or "")
        ),
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
    model_name = _normalize_frontend_model_name(
        str(payload.get("model_name") or payload.get("session_config", {}).get("model_name") or "")
    )
    session: dict[str, Any] = {
        "username": str(payload.get("username", "")).strip(),
        "model_name": model_name,
        "scenario": scenario,
        "base_scenario": dict(payload.get("base_scenario", {})),
        "policy": _build_service_policy(model_name),
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
    if normalized in mapping:
        return mapping[normalized]
    for prompt, prompt_key in mapping.items():
        if normalized.endswith(prompt):
            return prompt_key
    return ""


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
        planned_step = planned_product_routing_step(
            hidden_context,
            observed_trace,
            prompt_key=prompt_key,
        )
        fallback_step = {
            "prompt_key": prompt_key,
            "prompt": last_service_text,
            "answer_key": default_unknown_product_routing_answer_key(prompt_key),
            "answer_value": "",
            "answer_instruction": "围绕当前问题直接回答。",
        }
        if planned_step:
            planned_step = dict(planned_step)
            planned_step["prompt"] = last_service_text
        else:
            planned_step = fallback_step
        hidden_context["product_routing_plan"] = {
            "enabled": True,
            "result": "",
            "trace": list(observed_trace),
            "steps": [planned_step],
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
        "model_intent_inference_used": bool(display_turn.get("model_intent_inference_used", False)),
        "model_intent_inference_attempted": bool(display_turn.get("model_intent_inference_attempted", False)),
        "model_intent_inference_unapplied": bool(display_turn.get("model_intent_inference_unapplied", False)),
        "round_count_snapshot": display_turn["round_index"],
        "has_address_ie_display": has_address_ie_display,
    }
    if turn.speaker == USER_SPEAKER:
        entry["restore_checkpoint_index"] = _restore_checkpoint_index_for_round(
            session,
            round_index=int(display_turn["round_index"] or 0),
        )
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
    client: OpenAIChatClient | None = None,
    model: str = "",
) -> dict[str, Any] | None:
    resolved_client = client or llm_client
    resolved_model = model or config.service_agent_model
    previous_service_text = ""
    for previous_turn in reversed(transcript[:-1]):
        if previous_turn.speaker == SERVICE_SPEAKER:
            previous_service_text = previous_turn.text
            break
    if (
        runtime_state.expected_address_confirmation
        and not runtime_state.address_confirmation_triggered_by_observation
        and (
            runtime_state.address_confirmation_started_from_known_address
            or (
                policy.is_address_confirmation_prompt(previous_service_text)
                and policy._normalize_prompt_text(previous_service_text).startswith("您的地址是")
            )
        )
    ):
        confirmation_intent = policy._classify_confirmation_intent(
            turn.text,
            prompt_kind="address_confirmation",
            user_round_index=turn.round_index,
        )
        if confirmation_intent == "yes":
            confirmation_address = str(
                runtime_state.pending_address_confirmation or ""
            ).strip()
            if confirmation_address:
                observation = build_address_model_observation(
                    confirmation_address,
                    client=resolved_client,
                    model=resolved_model,
                )
                turn.post_display_lines.append(policy.ADDRESS_IE_FUNCTION_CALL_DISPLAY)
                turn.post_display_lines.append(
                    f"observation: {json.dumps(observation, ensure_ascii=False)}"
                )
                return None
        if confirmation_intent == "no":
            confirmation_address = str(
                runtime_state.pending_address_confirmation or ""
            ).strip()
            denial_address = ""
            if confirmation_address:
                denial_address, _ = policy._resolve_confirmation_denial_address_candidate(
                    transcript=transcript,
                    user_text=turn.text,
                    confirmation_address=confirmation_address,
                )
            if denial_address:
                observation = build_address_model_observation(
                    transcript,
                    client=resolved_client,
                    model=resolved_model,
                )
                turn.post_display_lines.append(policy.ADDRESS_IE_FUNCTION_CALL_DISPLAY)
                turn.post_display_lines.append(
                    f"observation: {json.dumps(observation, ensure_ascii=False)}"
                )
                return observation

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
        client=resolved_client,
        model=resolved_model,
    )
    turn.post_display_lines.append(policy.ADDRESS_IE_FUNCTION_CALL_DISPLAY)
    turn.post_display_lines.append(f"observation: {json.dumps(observation, ensure_ascii=False)}")
    return observation


def _predict_address_ie_entity_type(
    *,
    policy: ServiceDialoguePolicy,
    turn: DialogueTurn,
    transcript: list[DialogueTurn],
    runtime_state: ServiceRuntimeState,
) -> str:
    previous_service_text = ""
    for previous_turn in reversed(transcript[:-1]):
        if previous_turn.speaker == SERVICE_SPEAKER:
            previous_service_text = previous_turn.text
            break
    if (
        runtime_state.expected_address_confirmation
        and not runtime_state.address_confirmation_triggered_by_observation
        and (
            runtime_state.address_confirmation_started_from_known_address
            or (
                policy.is_address_confirmation_prompt(previous_service_text)
                and policy._normalize_prompt_text(previous_service_text).startswith("您的地址是")
            )
        )
    ):
        confirmation_intent = policy._classify_confirmation_intent(
            turn.text,
            prompt_kind="address_confirmation",
            user_round_index=turn.round_index,
        )
        confirmation_address = str(runtime_state.pending_address_confirmation or "").strip()
        if confirmation_intent == "yes" and confirmation_address:
            return "addressInfo"
        if confirmation_intent == "no" and confirmation_address:
            denial_address, _ = policy._resolve_confirmation_denial_address_candidate(
                transcript=transcript,
                user_text=turn.text,
                confirmation_address=confirmation_address,
            )
            if denial_address:
                return "addressInfo"

    if policy.should_insert_address_ie_function_call(
        user_text=turn.text,
        transcript=transcript,
        runtime_state=runtime_state,
    ):
        return "addressInfo"
    if policy.should_insert_address_ie_after_observation_confirmation(
        user_text=turn.text,
        user_round_index=turn.round_index,
        transcript=transcript,
        runtime_state=runtime_state,
    ):
        return "addressInfo"
    return ""


def _predict_phone_ie_entity_type(
    *,
    policy: ServiceDialoguePolicy,
    transcript: list[DialogueTurn],
    runtime_state: ServiceRuntimeState,
) -> str:
    if not runtime_state.awaiting_phone_keypad_input:
        return ""
    previous_service_text = ""
    for previous_turn in reversed(transcript[:-1]):
        if previous_turn.speaker == SERVICE_SPEAKER:
            previous_service_text = previous_turn.text
            break
    if policy.is_phone_keypad_prompt(previous_service_text):
        return "telephone"
    return ""


def _predict_ie_entity_type_for_turn(
    *,
    policy: ServiceDialoguePolicy,
    turn: DialogueTurn,
    transcript: list[DialogueTurn],
    runtime_state: ServiceRuntimeState,
) -> str:
    phone_entity_type = _predict_phone_ie_entity_type(
        policy=policy,
        transcript=transcript,
        runtime_state=runtime_state,
    )
    if phone_entity_type:
        return phone_entity_type
    return _predict_address_ie_entity_type(
        policy=policy,
        turn=turn,
        transcript=transcript,
        runtime_state=runtime_state,
    )


def _append_phone_ie_display_lines(
    *,
    policy: ServiceDialoguePolicy,
    turn: DialogueTurn,
    transcript: list[DialogueTurn],
    runtime_state: ServiceRuntimeState,
    client: OpenAIChatClient | None = None,
    model: str = "",
) -> dict[str, Any] | None:
    resolved_client = client or llm_client
    resolved_model = model or config.service_agent_model
    if not runtime_state.awaiting_phone_keypad_input:
        return None
    previous_service_text = ""
    for previous_turn in reversed(transcript[:-1]):
        if previous_turn.speaker == SERVICE_SPEAKER:
            previous_service_text = previous_turn.text
            break
    if not policy.is_phone_keypad_prompt(previous_service_text):
        return None
    observation = build_telephone_model_observation(
        transcript,
        client=resolved_client,
        model=resolved_model,
    )
    runtime_state.pending_phone_ie_observation = dict(observation)
    turn.post_display_lines.append(policy.PHONE_IE_FUNCTION_CALL_DISPLAY)
    turn.post_display_lines.append(f"observation: {json.dumps(observation, ensure_ascii=False)}")
    return observation


def _normalize_manual_ie_entity_type(entity_type: str) -> str:
    normalized = str(entity_type or "").strip() or "addressInfo"
    if normalized in {"addressInfo", "address"}:
        return "addressInfo"
    if normalized in {"telephone", "telephone_number"}:
        return "telephone"
    raise HTTPException(status_code=400, detail="当前仅支持地址或电话 function_call。")


def _ie_post_display_lines_for_transcript(
    transcript: list[DialogueTurn],
    *,
    entity_type: str = "addressInfo",
    client: OpenAIChatClient | None = None,
    model: str = "",
) -> list[str]:
    normalized_entity_type = _normalize_manual_ie_entity_type(entity_type)
    resolved_client = client or llm_client
    resolved_model = model or config.service_agent_model
    if normalized_entity_type == "telephone":
        observation = build_telephone_model_observation(
            transcript,
            client=resolved_client,
            model=resolved_model,
        )
        return [
            ServiceDialoguePolicy.PHONE_IE_FUNCTION_CALL_DISPLAY,
            f"observation: {json.dumps(observation, ensure_ascii=False)}",
        ]

    observation = build_address_model_observation(
        transcript,
        client=resolved_client,
        model=resolved_model,
    )
    return [
        ServiceDialoguePolicy.ADDRESS_IE_FUNCTION_CALL_DISPLAY,
        f"observation: {json.dumps(observation, ensure_ascii=False)}",
    ]


def _address_ie_post_display_lines_for_transcript(transcript: list[DialogueTurn]) -> list[str]:
    return _ie_post_display_lines_for_transcript(transcript, entity_type="addressInfo")


def _find_user_turn_by_round_index(transcript: list[DialogueTurn], round_index: int) -> tuple[int, DialogueTurn] | None:
    for index, turn in enumerate(transcript):
        if turn.speaker == USER_SPEAKER and int(turn.round_index) == int(round_index):
            return index, turn
    return None


def _apply_manual_ie_display_lines(
    session: dict[str, Any],
    *,
    round_index: int,
    enabled: bool,
    entity_type: str = "addressInfo",
) -> bool:
    normalized_entity_type = _normalize_manual_ie_entity_type(entity_type)
    active_config = _config_for_model(
        str(session.get("model_name") or session.get("session_config", {}).get("model_name") or "")
    )
    active_client = OpenAIChatClient(active_config)
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
        observation_lines = _ie_post_display_lines_for_transcript(
            transcript[: turn_position + 1],
            entity_type=normalized_entity_type,
            client=active_client,
            model=active_config.service_agent_model,
        )
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
            checkpoint_observation_lines = _ie_post_display_lines_for_transcript(
                checkpoint_transcript[: checkpoint_turn_position + 1],
                entity_type=normalized_entity_type,
                client=active_client,
                model=active_config.service_agent_model,
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
    confirmed_address = str(observation.get("address") or "").strip()
    error_msg = str(observation.get("error_msg") or "").strip()

    if normalized_error_code == 0:
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

    fixed_reply = {
        "已成功获取四级地址，缺少详细地址信息": "不好意思，我这边没有定位到这个地址，请重新提供一下小区、楼栋和门牌号",
        "缺少乡镇或街道以及详细地址": "不好意思，我这边没有定位到这个地址，请重新提供一下小区、楼栋和门牌号",
        "缺少区县、乡镇或街道以及详细地址": "不好意思，我这边没有定位到这个地址，麻烦您再说下区县和乡镇",
        "缺少市、区县、乡镇或街道以及详细地址": "不好意思，我这边没有定位到这个地址，请重新说一下是哪个城市的哪个区和街道呢？",
        "未成功获取有效地址": "不好意思，我这边没有定位到这个地址，麻烦您再完整的说下省、市、区、乡镇，精确到门牌号",
        "缺少乡镇或街道": "不好意思，我没定位到这个街道或镇，麻烦您再说一下呢？",
    }.get(error_msg)
    if not fixed_reply:
        return None

    runtime_state.expected_address_confirmation = False
    runtime_state.address_confirmation_triggered_by_observation = False
    runtime_state.address_confirmation_started_from_known_address = False
    runtime_state.awaiting_full_address = True
    runtime_state.pending_address_confirmation = ""
    if confirmed_address and confirmed_address != "无法判断":
        runtime_state.partial_address_candidate = confirmed_address
    runtime_state.address_vague_retry_count = 0
    runtime_state.last_address_followup_prompt = fixed_reply
    return ServicePolicyResult(
        reply=fixed_reply,
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


def _normalize_rewrite_review_role(raw_role: Any) -> str:
    role = str(raw_role or "").strip()
    lowered = role.lower()
    if not role:
        return ""
    if lowered in {"user", "human", "customer", "caller"} or role == "用户":
        return "用户"
    if lowered in {"service", "assistant", "agent"} or role == "客服":
        return "客服"
    if lowered == "function_call":
        return "function_call"
    if lowered == "observation":
        return "observation"
    if lowered in {"system", "tool"} or role == "系统":
        return "系统"
    return role


def _rewrite_review_value_present(value: Any) -> bool:
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, dict)):
        return bool(value)
    if value is None:
        return False
    return bool(str(value).strip())


def _validate_rewrite_review_record(record_id: str, record: dict[str, Any]) -> None:
    rewrited = record.get("rewrited")
    if not isinstance(rewrited, list) or not rewrited:
        raise HTTPException(status_code=400, detail="当前记录未提交 rewrited，不能提交评审。")

    conflict_messages: list[str] = []
    normalized_dialogue: list[tuple[int, str]] = []

    for index, item in enumerate(rewrited):
        if not isinstance(item, dict):
            raise HTTPException(status_code=400, detail=f"记录 {record_id} 的 rewrited 第 {index + 1} 项格式无效。")
        role = _normalize_rewrite_review_role(item.get("from"))
        value = item.get("value")
        has_value = _rewrite_review_value_present(value)
        if role == "function_call":
            previous = rewrited[index - 1] if index > 0 and isinstance(rewrited[index - 1], dict) else None
            previous_role = _normalize_rewrite_review_role(previous.get("from")) if previous else ""
            previous_has_value = _rewrite_review_value_present(previous.get("value")) if previous else False
            if previous_role != "用户" or not previous_has_value:
                conflict_messages.append(
                    f"第 {index + 1} 行 function_call 上一行必须是带内容的“用户”"
                    if previous
                    else f"第 {index + 1} 行 function_call 前缺少用户行"
                )
        if has_value and role in {"用户", "客服"}:
            normalized_dialogue.append((index, role))

    if len(normalized_dialogue) < 2:
        raise HTTPException(status_code=400, detail="当前记录有效对话不足 2 行，不能提交评审。")

    for index in range(1, len(normalized_dialogue)):
        previous_index, previous_role = normalized_dialogue[index - 1]
        current_index, current_role = normalized_dialogue[index]
        if previous_role == current_role:
            conflict_messages.append(
                f"第 {previous_index + 1} 行和第 {current_index + 1} 行连续为“{current_role}”"
            )

    if conflict_messages:
        raise HTTPException(
            status_code=400,
            detail=f"当前记录未通过角色交替/结构校验：{'；'.join(conflict_messages)}",
        )


def _ensure_rewrite_review_database() -> None:
    global _REWRITE_REVIEW_DB_SCHEMA_READY
    REWRITE_REVIEW_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with REWRITE_REVIEW_DB_LOCK:
        if _REWRITE_REVIEW_DB_SCHEMA_READY:
            return
        conn = sqlite3.connect(REWRITE_REVIEW_DB_PATH, timeout=15.0, isolation_level=None)
        try:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS rewrite_reviews (
                    record_id TEXT PRIMARY KEY,
                    username TEXT NOT NULL,
                    source TEXT NOT NULL,
                    reviewed_at TEXT NOT NULL,
                    review_payload_json TEXT NOT NULL
                )
                """
            )
            _REWRITE_REVIEW_DB_SCHEMA_READY = True
        finally:
            conn.close()


def _persist_rewrite_review_result(
    *,
    record_id: str,
    record: dict[str, Any],
    username: str,
) -> str:
    _ensure_rewrite_review_database()
    reviewed_at = _current_display_timestamp()
    review_payload = {
        "record_id": record_id,
        "username": username,
        "source": str(record.get("source", "")).strip(),
        "reviewed_at": reviewed_at,
        "record": record,
    }
    with REWRITE_REVIEW_DB_LOCK:
        conn = sqlite3.connect(REWRITE_REVIEW_DB_PATH, timeout=15.0, isolation_level=None)
        try:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute(
                """
                INSERT INTO rewrite_reviews (
                    record_id,
                    username,
                    source,
                    reviewed_at,
                    review_payload_json
                ) VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(record_id) DO UPDATE SET
                    username=excluded.username,
                    source=excluded.source,
                    reviewed_at=excluded.reviewed_at,
                    review_payload_json=excluded.review_payload_json
                """,
                (
                    record_id,
                    username,
                    str(record.get("source", "")).strip(),
                    reviewed_at,
                    json.dumps(review_payload, ensure_ascii=False),
                ),
            )
            conn.commit()
            return reviewed_at
        except Exception:
            conn.rollback()
            raise
        finally:
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


@app.get("/api/auth/mention-users")
def auth_mention_users(current_user: dict[str, str] = Depends(_require_authenticated_user)):
    return {
        "users": _list_enabled_registered_accounts(),
        "username": current_user["username"],
    }


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
    auto_mode: bool = False,
    current_user: dict[str, str] = Depends(_require_authenticated_user),
):
    _ = current_user
    if auto_mode and random.random() >= max(0.0, min(1.0, float(config.service_known_address_probability))):
        return {"known_address": ""}
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
        scenario, known_address_notice, rounds_limit, ivr_notice, ivr_opening_enabled = _prepare_manual_test_scenario(req)
        required_slots, collected_slots = _build_collected_slots(scenario)
        initial_lines = _build_initial_lines(
            scenario,
            rounds_limit=rounds_limit,
            known_address_notice=known_address_notice,
        )

        session_id = str(uuid.uuid4())
        selected_model_name = _normalize_frontend_model_name(req.model_name)
        policy = _build_service_policy(selected_model_name)
        sessions[session_id] = {
            "username": current_user["username"],
            "model_name": selected_model_name,
            "scenario": scenario,
            "base_scenario": scenario.to_dict(),
            "policy": policy,
            "runtime_state": ServiceRuntimeState(),
            "transcript": [],
            "trace": [],
            "terminal_entries": [],
            "checkpoints": [],
            "required_slots": required_slots,
            "collected_slots": collected_slots,
            "initial_runtime_state": {},
            "initial_collected_slots": {},
            "rounds_limit": rounds_limit,
            "status": "active",
            "aborted_reason": "",
            "started_at": _current_display_timestamp(),
            "ended_at": "",
            "review_submitted": False,
            "session_config": {
                "scenario_id": scenario.scenario_id,
                "model_name": selected_model_name,
                "product_category": str(req.product_category or "").strip(),
                "request_type": str(req.request_type or "").strip(),
                "history_device_brand": str(req.history_device_brand or "").strip(),
                "history_device_category": str(req.history_device_category or "").strip(),
                "history_device_purchase_date": str(req.history_device_purchase_date or "").strip(),
                "known_address": _sanitize_manual_user_text(req.known_address),
                "ivr_utterance": _sanitize_manual_user_text(req.ivr_utterance),
                "ivr_opening_enabled": bool(ivr_opening_enabled),
                "call_start_time": scenario.call_start_time,
                "use_session_start_time_as_call_start_time": bool(req.use_session_start_time_as_call_start_time),
                "max_rounds": req.max_rounds,
                "auto_generate_hidden_settings": bool(req.auto_generate_hidden_settings),
                "persist_to_db": bool(req.persist_to_db),
            },
        }
        sessions[session_id]["initial_runtime_state"] = asdict(sessions[session_id]["runtime_state"])
        sessions[session_id]["initial_collected_slots"] = dict(collected_slots)
        _append_checkpoint(sessions[session_id], source_round_index=0)
        if ivr_opening_enabled:
            opening_user_turn = DialogueTurn(
                speaker=USER_SPEAKER,
                text=policy.build_initial_user_utterance(scenario),
                round_index=1,
            )
            sessions[session_id]["transcript"].append(opening_user_turn)
            _append_turn_entry(sessions[session_id], opening_user_turn)
            opening_action = policy.respond(
                scenario=scenario,
                transcript=sessions[session_id]["transcript"],
                collected_slots=sessions[session_id]["collected_slots"],
                runtime_state=sessions[session_id]["runtime_state"],
            )
            _merge_slots(collected_slots, opening_action.slot_updates, required_slots)
            _merge_slots(
                collected_slots,
                opening_action.slot_updates,
                list(SUPPLEMENTARY_COLLECTED_SLOTS),
            )
            opening_service_turn = DialogueTurn(
                speaker=SERVICE_SPEAKER,
                text=opening_action.reply,
                round_index=1,
                model_intent_inference_used=bool(
                    getattr(policy, "last_used_model_intent_inference", False)
                ),
                model_intent_inference_attempted=bool(
                    getattr(
                        policy,
                        "last_model_intent_inference_attempted",
                        getattr(policy, "last_used_model_intent_inference", False),
                    )
                ),
                model_intent_inference_unapplied=bool(
                    getattr(
                        policy,
                        "last_model_intent_inference_attempted",
                        getattr(policy, "last_used_model_intent_inference", False),
                    )
                    and not getattr(policy, "last_used_model_intent_inference", False)
                ),
                previous_user_intent_model_inference_used=bool(
                    getattr(policy, "last_used_model_intent_inference", False)
                ),
                previous_user_intent_model_inference_attempted=bool(
                    getattr(
                        policy,
                        "last_model_intent_inference_attempted",
                        getattr(policy, "last_used_model_intent_inference", False),
                    )
                ),
                previous_user_intent_model_inference_unapplied=bool(
                    getattr(
                        policy,
                        "last_model_intent_inference_attempted",
                        getattr(policy, "last_used_model_intent_inference", False),
                    )
                    and not getattr(policy, "last_used_model_intent_inference", False)
                ),
            )
            sessions[session_id]["transcript"].append(opening_service_turn)
            _append_turn_entry(sessions[session_id], opening_service_turn)
            _append_checkpoint(sessions[session_id], source_round_index=1)
        _persist_session(session_id, sessions[session_id])
        return {
            **_build_session_view(session_id, sessions[session_id]),
            "initial_lines": initial_lines,
            "ivr_notice": ivr_notice,
            "persist_to_db_default": bool(req.persist_to_db),
        }
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"初始化对话失败: {exc}") from exc


@app.post("/api/session/auto-mode")
async def run_auto_mode(
    req: StartSessionRequest,
    current_user: dict[str, str] = Depends(_require_authenticated_user),
):
    if not _is_chat_admin(current_user):
        raise HTTPException(status_code=403, detail="只有测试管理员可以使用自动模式。")
    try:
        job_id, job = _create_auto_mode_job(req)
        initial_view = _build_auto_mode_job_view(job_id, job)
        worker = threading.Thread(
            target=_run_auto_mode_job_thread,
            args=(job_id,),
            daemon=True,
        )
        worker.start()
        return initial_view
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"自动模式启动失败: {exc}") from exc


@app.get("/api/session/auto-mode/{job_id}")
def get_auto_mode_job(
    job_id: str,
    current_user: dict[str, str] = Depends(_require_authenticated_user),
):
    if not _is_chat_admin(current_user):
        raise HTTPException(status_code=403, detail="只有测试管理员可以使用自动模式。")
    with AUTO_MODE_JOB_LOCK:
        job = auto_mode_jobs.get(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="自动模式任务不存在或已失效。")
        return _build_auto_mode_job_view(job_id, job)


@app.post("/api/session/auto-mode/{job_id}/abort")
def abort_auto_mode_job(
    job_id: str,
    current_user: dict[str, str] = Depends(_require_authenticated_user),
):
    if not _is_chat_admin(current_user):
        raise HTTPException(status_code=403, detail="只有测试管理员可以使用自动模式。")
    with AUTO_MODE_JOB_LOCK:
        job = auto_mode_jobs.get(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="自动模式任务不存在或已失效。")
        if not bool(job.get("done")):
            job["abort_requested"] = True
            job["updated_at"] = time.time()
            _append_terminal_lines(
                job["session"],
                lines=["已收到强制结束请求，正在停止自动模式..."],
                tone="system",
                round_count_snapshot=_completed_round_count(job["session"].get("transcript", [])),
            )
        return _build_auto_mode_job_view(job_id, job)


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
    active_config = _config_for_model(
        str(session.get("model_name") or session.get("session_config", {}).get("model_name") or "")
    )
    active_client = OpenAIChatClient(active_config)
    user_turn = DialogueTurn(
        speaker=USER_SPEAKER,
        text=punctuated_user_text,
        round_index=round_index,
    )
    transcript.append(user_turn)
    _append_phone_ie_display_lines(
        policy=policy,
        turn=user_turn,
        transcript=transcript,
        runtime_state=runtime_state,
        client=active_client,
        model=active_config.service_agent_model,
    )
    auto_address_observation = _append_address_ie_display_lines(
        policy=policy,
        turn=user_turn,
        transcript=transcript,
        runtime_state=runtime_state,
        client=active_client,
        model=active_config.service_agent_model,
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
    attempted_model_intent_inference = bool(
        getattr(policy, "last_model_intent_inference_attempted", used_model_intent_inference)
    )
    unapplied_model_intent_inference = bool(
        attempted_model_intent_inference and not used_model_intent_inference
    )
    service_turn = DialogueTurn(
        speaker=SERVICE_SPEAKER,
        text=service_result.reply,
        round_index=round_index,
        model_intent_inference_used=used_model_intent_inference,
        model_intent_inference_attempted=attempted_model_intent_inference,
        model_intent_inference_unapplied=unapplied_model_intent_inference,
        previous_user_intent_model_inference_used=used_model_intent_inference,
        previous_user_intent_model_inference_attempted=attempted_model_intent_inference,
        previous_user_intent_model_inference_unapplied=unapplied_model_intent_inference,
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
            "model_intent_inference_attempted": attempted_model_intent_inference,
            "model_intent_inference_unapplied": unapplied_model_intent_inference,
            "previous_user_intent_model_inference_used": used_model_intent_inference,
            "previous_user_intent_model_inference_attempted": attempted_model_intent_inference,
            "previous_user_intent_model_inference_unapplied": unapplied_model_intent_inference,
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


@app.post("/api/session/pending-ie")
def predict_pending_ie(
    req: RespondRequest,
    current_user: dict[str, str] = Depends(_require_authenticated_user),
):
    session = _session_state(req.session_id)
    if session["status"] != "active":
        raise HTTPException(status_code=409, detail="当前会话已结束，请重新开始。")

    raw_text = str(req.text or "")
    sanitized = _sanitize_manual_user_text(raw_text)
    if not sanitized:
        raise HTTPException(status_code=400, detail="输入不能为空。")

    transcript = session["transcript"]
    round_index = _next_round_index(transcript)
    if _manual_command_token(raw_text):
        return {"entity_type": "", "round_index": round_index}
    if round_index > int(session["rounds_limit"]):
        return {"entity_type": "", "round_index": round_index}

    punctuated_user_text = (
        sanitized if round_index == 1 else _punctuate_user_text_for_session(sanitized)
    )
    user_turn = DialogueTurn(
        speaker=USER_SPEAKER,
        text=punctuated_user_text,
        round_index=round_index,
    )
    entity_type = _predict_ie_entity_type_for_turn(
        policy=session["policy"],
        turn=user_turn,
        transcript=transcript + [user_turn],
        runtime_state=copy.deepcopy(session["runtime_state"]),
    )
    return {"entity_type": entity_type, "round_index": round_index}


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
    session["policy"] = _build_service_policy(
        str(session.get("model_name") or session.get("session_config", {}).get("model_name") or "")
    )
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
    entity_type = _normalize_manual_ie_entity_type(req.entity_type)
    changed = _apply_manual_ie_display_lines(
        session,
        round_index=req.round_index,
        enabled=bool(req.enabled),
        entity_type=entity_type,
    )
    _persist_session(req.session_id, session)
    return {
        "ok": True,
        "changed": changed,
        "round_index": int(req.round_index),
        "enabled": bool(req.enabled),
        "entity_type": entity_type,
        **_build_session_view(req.session_id, session),
    }


@app.post("/api/rewrite/ie-observation")
def build_rewrite_ie_observation(
    req: RewriteIeObservationRequest,
    current_user: dict[str, str] = Depends(_require_authenticated_user),
):
    entity_type = str(req.entity_type or "").strip() or "addressInfo"
    if entity_type not in {"addressInfo", "address", "telephone", "telephone_number"}:
        raise HTTPException(status_code=400, detail="当前仅支持地址或电话 observation。")
    dialogue_lines = [
        str(line).strip()
        for line in req.dialogue_lines
        if str(line).strip()
    ]
    if not dialogue_lines:
        raise HTTPException(status_code=400, detail="请先在 function_call 上方保留用户/客服对话内容。")

    active_config = _config_for_model(req.model_name)
    observation = build_ie_model_observation(
        dialogue_lines,
        entity_type,
        client=OpenAIChatClient(active_config),
        model=active_config.service_agent_model,
    )
    return {"observation": observation}


@app.post("/api/rewrite/review")
def review_rewrite_record(
    req: RewriteReviewRequest,
    current_user: dict[str, str] = Depends(_require_authenticated_user),
):
    record_id = str(req.record_id or "").strip()
    if not record_id:
        raise HTTPException(status_code=400, detail="缺少记录 id，不能提交评审。")
    record = dict(req.record or {})
    if not record:
        raise HTTPException(status_code=400, detail="缺少记录内容，不能提交评审。")
    if str(record.get("id", "")).strip() != record_id:
        record["id"] = record_id
    _validate_rewrite_review_record(record_id, record)
    try:
        reviewed_at = _persist_rewrite_review_result(
            record_id=record_id,
            record=record,
            username=current_user["username"],
        )
    except Exception as exc:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"写入改写评审 SQLite 失败: {exc}") from exc
    return {
        "ok": True,
        "record_id": record_id,
        "username": current_user["username"],
        "db_path": str(REWRITE_REVIEW_DB_PATH),
        "reviewed_at": reviewed_at,
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
