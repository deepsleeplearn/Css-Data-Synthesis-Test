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

# Add the project root to sys.path to ensure multi_agent_data_synthesis can be imported.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from multi_agent_data_synthesis.agents import ServiceAgent
    from multi_agent_data_synthesis.cli import (
        _hydrate_manual_test_scenario_locally,
        _manual_test_requires_generated_hidden_settings,
        _resolve_interactive_max_rounds,
    )
    from multi_agent_data_synthesis.config import load_config
    from multi_agent_data_synthesis.hidden_settings_tool import HiddenSettingsTool
    from multi_agent_data_synthesis.llm import OpenAIChatClient
    from multi_agent_data_synthesis.manual_test import (
        MANUAL_TEST_EXIT_COMMANDS,
        MANUAL_TEST_HELP_COMMAND,
        MANUAL_TEST_SHOW_SLOTS_COMMAND,
        MANUAL_TEST_SHOW_STATE_COMMAND,
        _manual_command_token,
        _sanitize_manual_user_text,
    )
    from multi_agent_data_synthesis.product_routing import ensure_product_routing_plan
    from multi_agent_data_synthesis.scenario_factory import ScenarioFactory
    from multi_agent_data_synthesis.schemas import (
        SERVICE_SPEAKER,
        SUPPLEMENTARY_COLLECTED_SLOTS,
        USER_SPEAKER,
        DialogueTurn,
        Scenario,
        effective_required_slots,
    )
    from multi_agent_data_synthesis.service_policy import ServiceRuntimeState
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
        raise HTTPException(status_code=404, detail="会话已过期或不存在")
    return session


def _next_round_index(transcript: list[DialogueTurn]) -> int:
    user_turns = sum(1 for turn in transcript if turn.speaker == USER_SPEAKER)
    return user_turns + 1


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


def _session_snapshot(session_id: str, session: dict[str, Any]) -> dict[str, Any]:
    scenario = session["scenario"]
    runtime_state = session["runtime_state"]
    transcript = session["transcript"]
    return {
        "session_id": session_id,
        "scenario_id": scenario.scenario_id,
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
        "trace": list(session["trace"]),
    }


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
            conn.commit()


def _persist_review_result(
    *,
    session_id: str,
    session: dict[str, Any],
    is_correct: bool,
    failed_flow_stage: str,
    notes: str,
    persist_to_db: bool,
) -> None:
    _ensure_review_database()
    review_payload = {
        **_session_snapshot(session_id, session),
        "review": {
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
                ON CONFLICT(session_id) DO UPDATE SET
                    scenario_id=excluded.scenario_id,
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
        service_agent = ServiceAgent(
            llm_client,
            model=config.service_agent_model,
            temperature=config.default_temperature,
            ok_prefix_probability=config.service_ok_prefix_probability,
            product_routing_enabled=config.product_routing_enabled,
            product_routing_apply_probability=config.product_routing_apply_probability,
        )

        session_id = str(uuid.uuid4())
        sessions[session_id] = {
            "scenario": scenario,
            "policy": service_agent.policy,
            "runtime_state": ServiceRuntimeState(),
            "transcript": [],
            "trace": [],
            "required_slots": required_slots,
            "collected_slots": collected_slots,
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
        return {
            "session_id": session_id,
            "scenario": scenario.to_dict(),
            "required_slots": required_slots,
            "collected_slots": collected_slots,
            "runtime_state": asdict(ServiceRuntimeState()),
            "rounds_limit": rounds_limit,
            "next_round_index": 1,
            "status": "active",
            "initial_lines": _build_initial_lines(
                scenario,
                rounds_limit=rounds_limit,
                known_address_notice=known_address_notice,
            ),
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

    if command_token == MANUAL_TEST_HELP_COMMAND:
        return {
            "mode": "command",
            "output_lines": ["可用命令: /help, /slots, /state, /quit"],
            "collected_slots": collected_slots,
            "runtime_state": asdict(runtime_state),
            "status": session["status"],
            "session_closed": False,
            "next_round_index": _next_round_index(transcript),
            **_review_prompt_payload(session),
        }

    if command_token == MANUAL_TEST_SHOW_SLOTS_COMMAND:
        return {
            "mode": "command",
            "output_lines": [json.dumps(collected_slots, ensure_ascii=False, indent=2)],
            "collected_slots": collected_slots,
            "runtime_state": asdict(runtime_state),
            "status": session["status"],
            "session_closed": False,
            "next_round_index": _next_round_index(transcript),
            **_review_prompt_payload(session),
        }

    if command_token == MANUAL_TEST_SHOW_STATE_COMMAND:
        return {
            "mode": "command",
            "output_lines": [json.dumps(asdict(runtime_state), ensure_ascii=False, indent=2)],
            "collected_slots": collected_slots,
            "runtime_state": asdict(runtime_state),
            "status": session["status"],
            "session_closed": False,
            "next_round_index": _next_round_index(transcript),
            **_review_prompt_payload(session),
        }

    if command_token in MANUAL_TEST_EXIT_COMMANDS:
        _mark_session_closed(session, status="aborted", aborted_reason="user_exit")
        return {
            "mode": "command",
            "output_lines": ["会话已结束。"],
            "collected_slots": collected_slots,
            "runtime_state": asdict(runtime_state),
            "status": session["status"],
            "session_closed": True,
            "next_round_index": _next_round_index(transcript),
            **_review_prompt_payload(session),
        }

    round_index = _next_round_index(transcript)
    rounds_limit = int(session["rounds_limit"])
    if round_index > rounds_limit:
        _mark_session_closed(session, status="incomplete", aborted_reason="round_limit_reached")
        return {
            "mode": "command",
            "output_lines": ["已达到最大轮次，会话结束。"],
            "collected_slots": collected_slots,
            "runtime_state": asdict(runtime_state),
            "status": session["status"],
            "session_closed": True,
            "next_round_index": round_index,
            **_review_prompt_payload(session),
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
    )
    transcript.append(service_turn)

    session["trace"].append(
        {
            "round_index": round_index,
            "user_text": sanitized,
            "service_reply": service_result.reply,
            "used_model_intent_inference": used_model_intent_inference,
            "slot_updates": dict(service_result.slot_updates),
            "collected_slots_snapshot": dict(collected_slots),
            "runtime_state_snapshot": asdict(runtime_state),
            "is_ready_to_close": service_result.is_ready_to_close,
        }
    )

    output_lines: list[str] = []
    if service_result.is_ready_to_close and _all_required_slots_filled(collected_slots, required_slots):
        _mark_session_closed(session, status="completed")
        output_lines.append("--- 会话已完成 ---")
    elif round_index >= rounds_limit:
        _mark_session_closed(session, status="incomplete", aborted_reason="round_limit_reached")
        output_lines.append("--- 已达到最大轮次，会话结束 ---")

    return {
        "mode": "reply",
        "service_turn": service_turn.to_display_dict(),
        "output_lines": output_lines,
        "collected_slots": collected_slots,
        "runtime_state": asdict(runtime_state),
        "status": session["status"],
        "session_closed": session["status"] != "active",
        "next_round_index": _next_round_index(transcript),
        "is_ready_to_close": service_result.is_ready_to_close,
        **_review_prompt_payload(session),
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
        "is_correct": bool(req.is_correct),
        "failed_flow_stage": failed_flow_stage,
        "notes": notes,
        "persist_to_db": bool(req.persist_to_db),
        "reviewed_at": _utc_now_iso(),
    }
    return {
        "ok": True,
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
