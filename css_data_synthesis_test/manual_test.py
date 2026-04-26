from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from css_data_synthesis_test.schemas import (
    DialogueSample,
    DialogueTurn,
    Scenario,
    SUPPLEMENTARY_COLLECTED_SLOTS,
    SERVICE_SPEAKER,
    USER_SPEAKER,
    build_display_transcript,
    display_speaker,
    effective_required_slots,
)
from css_data_synthesis_test.scenario_factory import ScenarioFactory
from css_data_synthesis_test.function_call import (
    build_address_model_observation,
    build_telephone_model_observation,
)
from css_data_synthesis_test.service_policy import (
    ServiceDialoguePolicy,
    ServicePolicyResult,
    ServiceRuntimeState,
)
from css_data_synthesis_test.validator import validate_dialogue


InputFunc = Callable[[str], str]
PrintFunc = Callable[[str], None]
MANUAL_TEST_EXIT_COMMANDS = {"/quit", "/exit"}
MANUAL_TEST_SHOW_SLOTS_COMMAND = "/slots"
MANUAL_TEST_SHOW_STATE_COMMAND = "/state"
MANUAL_TEST_HELP_COMMAND = "/help"


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


def _sanitize_manual_user_text(raw: str) -> str:
    normalized = unicodedata.normalize("NFKC", str(raw or ""))
    cleaned_chars: list[str] = []
    for char in normalized:
        category = unicodedata.category(char)
        if category in {"Cc", "Cf", "Cs", "Co", "Cn"}:
            if char in {"\t", "\n", "\r"}:
                cleaned_chars.append(" ")
            continue
        cleaned_chars.append(char)
    cleaned = "".join(cleaned_chars)
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip()


def _manual_command_token(text: str) -> str:
    return re.sub(r"\s+", "", _sanitize_manual_user_text(text)).lower()


def load_manual_test_scenario(
    scenario_file: Path,
    *,
    scenario_id: str = "",
    scenario_index: int = 0,
) -> Scenario:
    factory = ScenarioFactory()
    scenarios = factory.load_from_file(scenario_file)
    if scenario_id:
        for scenario in scenarios:
            if scenario.scenario_id == scenario_id:
                return scenario
        raise ValueError(f"Scenario id not found: {scenario_id}")
    if scenario_index < 0 or scenario_index >= len(scenarios):
        raise ValueError(f"Scenario index out of range: {scenario_index}")
    return scenarios[scenario_index]


def default_manual_test_output_path(scenario_id: str) -> Path:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    safe_scenario_id = "".join(char if char.isalnum() or char in {"-", "_"} else "_" for char in scenario_id)
    return Path("outputs/manual_tests") / f"{safe_scenario_id}_{timestamp}.json"


def run_manual_test_session(
    scenario: Scenario,
    *,
    output_path: Path | None,
    max_rounds: int | None = None,
    ok_prefix_probability: float = 0.7,
    policy: ServiceDialoguePolicy | None = None,
    show_address_state: bool = False,
    show_final_slots: bool = False,
    input_func: InputFunc = input,
    print_func: PrintFunc = print,
) -> dict[str, Any]:
    resolved_policy = policy or ServiceDialoguePolicy(ok_prefix_probability=ok_prefix_probability)
    runtime_state = ServiceRuntimeState()
    transcript: list[DialogueTurn] = []
    required_slots = effective_required_slots(scenario)
    collected_slots = {slot: "" for slot in required_slots}
    for slot in SUPPLEMENTARY_COLLECTED_SLOTS:
        collected_slots.setdefault(slot, "")
    collected_slots["product_routing_result"] = str(
        scenario.hidden_context.get("product_routing_result", "")
    ).strip()
    rounds_limit = max_rounds or scenario.max_turns or 20
    trace: list[dict[str, Any]] = []
    status = "incomplete"
    aborted_reason = ""

    _print_session_header(scenario, output_path, print_func)

    for round_index in range(1, rounds_limit + 1):
        user_text: str | None = None
        while user_text is None:
            try:
                raw = input_func(f"[{round_index}] 用户: ")
            except EOFError:
                status = "aborted"
                aborted_reason = "eof"
                user_text = None
                break
            except KeyboardInterrupt:
                status = "aborted"
                aborted_reason = "keyboard_interrupt"
                print_func("\n手工测试已中断。")
                user_text = None
                break

            sanitized = _sanitize_manual_user_text(raw)
            command_token = _manual_command_token(raw)
            if not sanitized:
                print_func("输入不能为空。输入 /help 查看可用命令。")
                continue
            if command_token in MANUAL_TEST_EXIT_COMMANDS:
                status = "aborted"
                aborted_reason = "user_exit"
                user_text = None
                break
            if command_token == MANUAL_TEST_SHOW_SLOTS_COMMAND:
                print_func(json.dumps(collected_slots, ensure_ascii=False, indent=2))
                continue
            if command_token == MANUAL_TEST_SHOW_STATE_COMMAND:
                print_func(json.dumps(asdict(runtime_state), ensure_ascii=False, indent=2))
                continue
            if command_token == MANUAL_TEST_HELP_COMMAND:
                print_func("可用命令: /help, /slots, /state, /quit")
                continue
            user_text = sanitized

        if status == "aborted":
            break
        if user_text is None:
            status = "aborted"
            if not aborted_reason:
                aborted_reason = "empty_exit"
            break

        transcript.append(
            DialogueTurn(
                speaker=USER_SPEAKER,
                text=user_text,
                round_index=round_index,
            )
        )
        previous_service_text = ""
        for previous_turn in reversed(transcript[:-1]):
            if previous_turn.speaker == SERVICE_SPEAKER:
                previous_service_text = previous_turn.text
                break
        if runtime_state.awaiting_phone_keypad_input and resolved_policy.is_phone_keypad_prompt(previous_service_text):
            auto_phone_observation = build_telephone_model_observation(transcript)
            runtime_state.pending_phone_ie_observation = dict(auto_phone_observation)
            transcript[-1].post_display_lines.append(
                resolved_policy.PHONE_IE_FUNCTION_CALL_DISPLAY
            )
            transcript[-1].post_display_lines.append(
                f"observation: {json.dumps(auto_phone_observation, ensure_ascii=False)}"
            )
            for line in transcript[-1].post_display_lines:
                print_func(line)
        should_insert_for_collection = False
        if hasattr(resolved_policy, "should_insert_address_ie_function_call"):
            should_insert_for_collection = bool(
                resolved_policy.should_insert_address_ie_function_call(
                    user_text=user_text,
                    transcript=transcript,
                    runtime_state=runtime_state,
                )
            )
        should_insert_for_confirmation_correction = (
            not should_insert_for_collection
            and hasattr(resolved_policy, "should_insert_address_ie_after_observation_confirmation")
            and bool(
                resolved_policy.should_insert_address_ie_after_observation_confirmation(
                    user_text=user_text,
                    user_round_index=round_index,
                    transcript=transcript,
                    runtime_state=runtime_state,
                )
            )
        )
        auto_address_observation: dict[str, Any] | None = None
        if should_insert_for_collection or should_insert_for_confirmation_correction:
            auto_address_observation = build_address_model_observation(transcript)
            transcript[-1].post_display_lines.append(
                resolved_policy.ADDRESS_IE_FUNCTION_CALL_DISPLAY
            )
            transcript[-1].post_display_lines.append(
                f"observation: {json.dumps(auto_address_observation, ensure_ascii=False)}"
            )
            for line in transcript[-1].post_display_lines:
                print_func(line)

        service_result = _build_auto_address_confirmation_result(
            policy=resolved_policy,
            runtime_state=runtime_state,
            observation=auto_address_observation,
        )
        if service_result is None:
            service_result = resolved_policy.respond(
                scenario=scenario,
                transcript=transcript,
                collected_slots=collected_slots,
                runtime_state=runtime_state,
            )
        _merge_slots(collected_slots, service_result.slot_updates, required_slots)
        _merge_slots(
            collected_slots,
            service_result.slot_updates,
            list(SUPPLEMENTARY_COLLECTED_SLOTS),
        )

        used_model_intent_inference = bool(
            getattr(resolved_policy, "last_used_model_intent_inference", False)
        )
        attempted_model_intent_inference = bool(
            getattr(resolved_policy, "last_model_intent_inference_attempted", used_model_intent_inference)
        )
        unapplied_model_intent_inference = bool(
            attempted_model_intent_inference and not used_model_intent_inference
        )
        transcript.append(
            DialogueTurn(
                speaker=SERVICE_SPEAKER,
                text=service_result.reply,
                round_index=round_index,
                model_intent_inference_used=used_model_intent_inference,
                model_intent_inference_attempted=attempted_model_intent_inference,
                model_intent_inference_unapplied=unapplied_model_intent_inference,
            )
        )
        user_round_label = str(round_index)
        service_round_label = f"{round_index}{'*' if attempted_model_intent_inference else ''}"
        print_func(f"[{service_round_label}] {display_speaker(SERVICE_SPEAKER)}: {service_result.reply}")
        if show_address_state and _should_print_address_state(
            runtime_state=runtime_state,
            service_reply=service_result.reply,
            slot_updates=service_result.slot_updates,
        ):
            print_func(
                f"地址状态: {json.dumps(_address_state_snapshot(scenario, runtime_state, collected_slots), ensure_ascii=False)}"
            )

        trace.append(
            {
                "round_index": round_index,
                "user_text": user_text,
                "service_reply": service_result.reply,
                "user_round_label": user_round_label,
                "service_round_label": service_round_label,
                "used_model_intent_inference": used_model_intent_inference,
                "model_intent_inference_attempted": attempted_model_intent_inference,
                "model_intent_inference_unapplied": unapplied_model_intent_inference,
                "slot_updates": dict(service_result.slot_updates),
                "collected_slots_snapshot": dict(collected_slots),
                "runtime_state_snapshot": asdict(runtime_state),
                "is_ready_to_close": service_result.is_ready_to_close,
                "close_status": service_result.close_status,
                "close_reason": service_result.close_reason,
            }
        )

        if service_result.close_status == "transferred":
            status = "transferred"
            aborted_reason = service_result.close_reason
            print_func("--- 已转接人工，会话结束 ---")
            break
        if service_result.is_ready_to_close and _all_required_slots_filled(collected_slots, required_slots):
            status = "completed"
            break

    if status not in {"completed", "aborted", "transferred"}:
        status = "incomplete"
        if rounds_limit > 0 and transcript:
            aborted_reason = "round_limit_reached"

    missing_slots = [slot for slot in required_slots if not collected_slots.get(slot, "").strip()]
    sample = DialogueSample(
        scenario_id=scenario.scenario_id,
        status=status,
        rounds_used=max((turn.round_index for turn in transcript), default=0),
        transcript=transcript,
        collected_slots=collected_slots,
        missing_slots=missing_slots,
        scenario=scenario.to_dict(),
        validation={},
    )
    sample.validation = validate_dialogue(sample)

    payload = {
        "mode": "interactive_service_policy_test",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "aborted_reason": aborted_reason,
        "rounds_limit": rounds_limit,
        "scenario_id": scenario.scenario_id,
        "scenario": scenario.to_dict(),
        "transcript": build_display_transcript(transcript),
        "dialogue_text": "\n".join(
            (
                line
                for turn in build_display_transcript(transcript)
                for line in [
                    turn["text"]
                    if turn.get("display_kind") == "function_call"
                    else f"{turn['speaker']}: {turn['text']}"
                ]
            )
        ),
        "collected_slots": collected_slots,
        "missing_slots": missing_slots,
        "runtime_state_final": asdict(runtime_state),
        "service_trace": trace,
        "validation": sample.validation,
    }
    if show_final_slots:
        print_func(f"最终槽位: {json.dumps(collected_slots, ensure_ascii=False, indent=2)}")
        if missing_slots:
            print_func(f"仍缺失槽位: {json.dumps(missing_slots, ensure_ascii=False)}")
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print_func(f"测试结果已写入: {output_path}")
    else:
        print_func("测试结果未写入文件；如需落盘请传入输出路径。")
    return payload


def _merge_slots(
    collected_slots: dict[str, str],
    slot_updates: dict[str, str],
    required_slots: list[str],
) -> None:
    for slot, value in slot_updates.items():
        if slot in required_slots and value.strip():
            collected_slots[slot] = value.strip()


def _all_required_slots_filled(
    collected_slots: dict[str, str],
    required_slots: list[str],
) -> bool:
    return all(collected_slots.get(slot, "").strip() for slot in required_slots)


def _print_session_header(
    scenario: Scenario,
    output_path: Path | None,
    print_func: PrintFunc,
) -> None:
    print_func(f"场景: {scenario.scenario_id}")
    print_func(f"产品: {scenario.product.brand} {scenario.product.category} {scenario.product.model}")
    print_func(f"诉求: {scenario.request.request_type}")
    if output_path is not None:
        print_func(f"输出文件: {output_path}")
    else:
        print_func("输出文件: 未启用")
    print_func("可用命令: /help, /slots, /state, /quit")


def _address_state_snapshot(
    scenario: Scenario,
    runtime_state: ServiceRuntimeState,
    collected_slots: dict[str, str],
) -> dict[str, Any]:
    current_candidate = (
        runtime_state.pending_address_confirmation
        or runtime_state.partial_address_candidate
        or collected_slots.get("address", "")
    )
    return {
        "actual_address": scenario.customer.address,
        "awaiting_full_address": runtime_state.awaiting_full_address,
        "expected_address_confirmation": runtime_state.expected_address_confirmation,
        "pending_address_confirmation": runtime_state.pending_address_confirmation,
        "partial_address_candidate": runtime_state.partial_address_candidate,
        "address_input_attempts": runtime_state.address_input_attempts,
        "address_vague_retry_count": runtime_state.address_vague_retry_count,
        "last_address_followup_prompt": runtime_state.last_address_followup_prompt,
        "collected_address": collected_slots.get("address", ""),
        "missing_required_precision": ServiceDialoguePolicy._missing_required_address_precision(
            current_candidate,
            scenario.customer.address,
        ) if current_candidate else [],
    }


def _should_print_address_state(
    *,
    runtime_state: ServiceRuntimeState,
    service_reply: str,
    slot_updates: dict[str, str],
) -> bool:
    return bool(
        runtime_state.awaiting_full_address
        or runtime_state.expected_address_confirmation
        or runtime_state.pending_address_confirmation
        or runtime_state.partial_address_candidate
        or slot_updates.get("address", "").strip()
        or ServiceDialoguePolicy.is_address_collection_prompt(service_reply)
        or ServiceDialoguePolicy.is_address_confirmation_prompt(service_reply)
    )
