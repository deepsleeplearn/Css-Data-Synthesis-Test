from __future__ import annotations

import json
import sqlite3
import sys
import threading
import traceback
import uuid
import hashlib
import os
import secrets
from datetime import datetime, timedelta, timezone
from dataclasses import asdict, replace
from pathlib import Path
from typing import Any

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
    from css_data_synthesis_test.agents import ServiceAgent
    from css_data_synthesis_test.cli import (
        _hydrate_manual_test_scenario_locally,
        _manual_test_requires_generated_hidden_settings,
        _resolve_interactive_max_rounds,
    )
    from css_data_synthesis_test.config import load_config
    from css_data_synthesis_test.hidden_settings_tool import HiddenSettingsTool
    from css_data_synthesis_test.llm import OpenAIChatClient
    from css_data_synthesis_test.manual_test import (
        MANUAL_TEST_EXIT_COMMANDS,
        MANUAL_TEST_HELP_COMMAND,
        MANUAL_TEST_SHOW_SLOTS_COMMAND,
        MANUAL_TEST_SHOW_STATE_COMMAND,
        _manual_command_token,
        _sanitize_manual_user_text,
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
        effective_required_slots,
    )
    from css_data_synthesis_test.service_policy import ServiceRuntimeState
except ImportError as exc:  # pragma: no cover
    print(f"Error: Could not import core modules. {exc}")
    print(f"sys.path: {sys.path}")
    sys.exit(1)

app = FastAPI(title="Multi-Agent Data Synthesis Frontend")
AUTH_SESSION_COOKIE = "frontend_auth_session"
AUTH_SESSION_TTL = timedelta(hours=12)
DEFAULT_REGISTERED_ACCOUNTS_FILE = PROJECT_ROOT / "frontend" / "registered_accounts.local.json"

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
SESSION_REVIEW_DB_LOCK = threading.Lock()
SESSION_REDIS_URL = os.getenv("FRONTEND_SESSION_REDIS_URL", "").strip()
SESSION_REDIS_TTL_SECONDS = int(os.getenv("FRONTEND_SESSION_REDIS_TTL_SECONDS", "43200") or "43200")
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
    max_rounds: int | None = None
    persist_to_db: bool = False


class RespondRequest(BaseModel):
    session_id: str
    text: str


class RewindSessionRequest(BaseModel):
    session_id: str
    clicked_user_round_index: int = 0
    restore_checkpoint_index: int | None = None
    target_round_index: int | None = None


class LoginRequest(BaseModel):
    username: str
    password: str


class ReviewSessionRequest(BaseModel):
    session_id: str
    is_correct: bool
    failed_flow_stage: str = ""
    notes: str = ""
    persist_to_db: bool = False


def _scenario_file() -> Path:
    return config.data_dir / "seed_scenarios.json"


def _registered_accounts_file() -> Path:
    configured = os.getenv("FRONTEND_REGISTERED_ACCOUNTS_FILE", "").strip()
    if configured:
        return Path(configured).expanduser()
    return DEFAULT_REGISTERED_ACCOUNTS_FILE


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


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
    auth_sessions[token] = {
        "username": account["username"],
        "display_name": account["display_name"],
        "expires_at": datetime.now(timezone.utc) + AUTH_SESSION_TTL,
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

    session["expires_at"] = datetime.now(timezone.utc) + AUTH_SESSION_TTL
    return {
        "username": str(session["username"]),
        "display_name": str(session["display_name"]),
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


def _prepare_manual_test_scenario(req: StartSessionRequest) -> tuple[Scenario, str, int]:
    scenario = _resolve_scenario(
        scenario_id=req.scenario_id,
        scenario_index=req.scenario_index,
    )

    if req.auto_generate_hidden_settings:
        if not config.openai_api_key or "YOUR_API_KEY" in config.openai_api_key:
            raise ValueError("未配置 OPENAI_API_KEY，请检查 .env 文件。")
        tool = HiddenSettingsTool(llm_client, config)
        scenario = tool.generate_for_scenario(scenario)
    elif _manual_test_requires_generated_hidden_settings(scenario):
        scenario = _hydrate_manual_test_scenario_locally(scenario)

    scenario, known_address_notice = _apply_known_address(scenario, req.known_address)
    scenario.hidden_context["interactive_test_freeform"] = True
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
        session["ended_at"] = _utc_now_iso()


def _review_prompt_payload(session: dict[str, Any]) -> dict[str, Any]:
    return {
        "review_required": session["status"] != "active" and not bool(session.get("review_submitted", False)),
        "review_options": FLOW_REVIEW_OPTIONS,
        "persist_to_db_default": bool(session.get("session_config", {}).get("persist_to_db", False)),
    }


def _serialize_transcript(transcript: list[DialogueTurn]) -> list[dict[str, Any]]:
    return [turn.to_display_dict() for turn in transcript]


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
        return Scenario.from_dict(dict(checkpoint_scenario))

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
    entry = {
        "entry_type": "turn",
        "tone": "service" if turn.speaker == SERVICE_SPEAKER else "user",
        "speaker": display_turn["speaker"],
        "text": display_turn["text"],
        "round_index": display_turn["round_index"],
        "round_label": display_turn["round_label"],
        "round_count_snapshot": display_turn["round_index"],
    }
    if turn.speaker == USER_SPEAKER:
        entry["restore_checkpoint_index"] = max(int(display_turn["round_index"]) - 1, 0)
    terminal_entries.append(entry)


def _copy_terminal_entries(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [dict(entry) for entry in entries]


def _build_session_view(session_id: str, session: dict[str, Any]) -> dict[str, Any]:
    transcript = session["transcript"]
    return {
        "session_id": session_id,
        "scenario": session["scenario"].to_dict(),
        "session_config": dict(session.get("session_config", {})),
        "required_slots": list(session["required_slots"]),
        "collected_slots": dict(session["collected_slots"]),
        "runtime_state": asdict(session["runtime_state"]),
        "rounds_limit": session["rounds_limit"],
        "status": session["status"],
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


def _ensure_review_database() -> None:
    SESSION_REVIEW_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with SESSION_REVIEW_DB_LOCK:
        with sqlite3.connect(SESSION_REVIEW_DB_PATH, timeout=10.0) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("PRAGMA busy_timeout=10000")
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
            conn.commit()


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
    review_payload = {
        **_session_snapshot(session_id, session),
        "username": username,
        "review": {
            "username": username,
            "is_correct": is_correct,
            "failed_flow_stage": failed_flow_stage,
            "notes": notes,
            "persist_to_db": persist_to_db,
        },
    }
    reviewed_at = _utc_now_iso()
    with SESSION_REVIEW_DB_LOCK:
        with sqlite3.connect(SESSION_REVIEW_DB_PATH, timeout=10.0) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("PRAGMA busy_timeout=10000")
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
            "started_at": _utc_now_iso(),
            "ended_at": "",
            "review_submitted": False,
            "session_config": {
                "scenario_id": scenario.scenario_id,
                "known_address": _sanitize_manual_user_text(req.known_address),
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

    scenario = session["scenario"]
    policy = session["policy"]
    required_slots = session["required_slots"]
    user_turn = DialogueTurn(
        speaker=USER_SPEAKER,
        text=sanitized,
        round_index=round_index,
    )
    transcript.append(user_turn)

    try:
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
            "user_text": sanitized,
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
    session["runtime_state"] = ServiceRuntimeState(**dict(checkpoint.get("runtime_state", {})))
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
        "reviewed_at": _utc_now_iso(),
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

    uvicorn.run(app, host="0.0.0.0", port=8000)
