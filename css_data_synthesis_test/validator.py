from __future__ import annotations

import re

from css_data_synthesis_test.schemas import (
    DialogueSample,
    Scenario,
    SERVICE_SPEAKER,
    USER_SPEAKER,
    effective_required_slots,
    normalize_speaker,
)
from css_data_synthesis_test.service_policy import ServiceDialoguePolicy


ISSUE_KEYWORD_PATTERN = re.compile(
    r"(故障|报码|故障码|报错|报警|显示|不加热|没热水|热水不稳定|忽冷忽热|温度上不去|升温慢|"
    r"漏水|渗水|滴水|异响|噪音|不启动|启动不了|无法启动|跳闸|停机|维修)"
)
ADDRESS_LIKE_PATTERN = re.compile(
    r"(省|市|区|县|镇|乡|街道|路|街|大道|巷|弄|胡同|小区|花园|公寓|苑|府|里|村|大厦|中心|广场|城|"
    r"栋|幢|单元|室|号楼|号)"
)
PHONE_DIGIT_PATTERN = re.compile(r"1[3-9]\d{9}")


def _contains_issue_detail(text: str) -> bool:
    return bool(ISSUE_KEYWORD_PATTERN.search(text or ""))


def _contains_address_detail(text: str) -> bool:
    return bool(ADDRESS_LIKE_PATTERN.search(text or ""))


def _contains_phone_number(text: str) -> bool:
    return bool(PHONE_DIGIT_PATTERN.search(text or ""))


def _classify_yes_no(text: str) -> str | None:
    return ServiceDialoguePolicy._classify_yes_no(text)


def _contains_surname_answer(text: str) -> bool:
    return bool(ServiceDialoguePolicy._extract_freeform_surname(text))


def _contains_product_arrival_answer(text: str) -> bool:
    return _classify_yes_no(text) in {"yes", "no"}


def _contains_product_model_answer(text: str) -> bool:
    normalized = (text or "").strip()
    if not normalized:
        return False
    if _classify_yes_no(normalized) in {"yes", "no"}:
        return False
    if _contains_issue_detail(normalized) or _contains_address_detail(normalized) or _contains_phone_number(normalized):
        return False
    compact = re.sub(r"[，。！？、,.!\s]", "", normalized)
    return len(compact) >= 2


def _validate_topic_regression(sample: DialogueSample) -> list[str]:
    issues: list[str] = []
    transcript = sample.transcript
    for index in range(1, len(transcript)):
        previous_turn = transcript[index - 1]
        current_turn = transcript[index]
        if (
            normalize_speaker(previous_turn.speaker) != SERVICE_SPEAKER
            or normalize_speaker(current_turn.speaker) != USER_SPEAKER
        ):
            continue

        service_text = previous_turn.text
        user_text = current_turn.text
        intent = _classify_yes_no(user_text)

        if ServiceDialoguePolicy.is_phone_confirmation_prompt(service_text):
            if _contains_issue_detail(user_text) or _contains_address_detail(user_text) or _contains_phone_number(user_text):
                issues.append(
                    f"user introduced unrelated or repeated details after phone confirmation at round {current_turn.round_index}"
                )
        elif ServiceDialoguePolicy.is_address_confirmation_prompt(service_text):
            if intent == "yes" and (_contains_issue_detail(user_text) or _contains_address_detail(user_text) or _contains_phone_number(user_text)):
                issues.append(
                    f"user introduced unrelated or repeated details after address confirmation at round {current_turn.round_index}"
                )
        elif ServiceDialoguePolicy.is_closing_notice_prompt(service_text):
            if _contains_issue_detail(user_text) or _contains_address_detail(user_text) or _contains_phone_number(user_text):
                issues.append(
                    f"user repeated prior details during closing acknowledgement at round {current_turn.round_index}"
                )
    return issues


def _validate_repeated_slot_collection(sample: DialogueSample) -> list[str]:
    issues: list[str] = []
    transcript = sample.transcript
    prompt_counts = {
        "surname": 0,
        "product_arrival": 0,
        "product_model": 0,
    }
    previous_off_topic_reply = {
        "surname": "",
        "product_arrival": "",
        "product_model": "",
    }
    prompt_specs = (
        ("surname", ServiceDialoguePolicy.is_surname_prompt, _contains_surname_answer),
        ("product_arrival", ServiceDialoguePolicy.is_product_arrival_prompt, _contains_product_arrival_answer),
        ("product_model", ServiceDialoguePolicy.is_product_model_prompt, _contains_product_model_answer),
    )

    for index in range(1, len(transcript)):
        previous_turn = transcript[index - 1]
        current_turn = transcript[index]
        if (
            normalize_speaker(previous_turn.speaker) != SERVICE_SPEAKER
            or normalize_speaker(current_turn.speaker) != USER_SPEAKER
        ):
            continue

        normalized_user = re.sub(r"\s+", "", current_turn.text or "")
        for slot_name, prompt_matcher, answer_matcher in prompt_specs:
            if not prompt_matcher(previous_turn.text):
                continue

            prompt_counts[slot_name] += 1
            if answer_matcher(current_turn.text):
                previous_off_topic_reply[slot_name] = ""
                break

            if prompt_counts[slot_name] >= 3:
                issues.append(
                    f"user still did not answer {slot_name} after {prompt_counts[slot_name]} prompts at round {current_turn.round_index}"
                )
            if (
                previous_off_topic_reply[slot_name]
                and normalized_user
                and normalized_user == previous_off_topic_reply[slot_name]
            ):
                issues.append(
                    f"user repeated the same off-topic reply during {slot_name} collection at round {current_turn.round_index}"
                )
            previous_off_topic_reply[slot_name] = normalized_user
            break

    return issues


def validate_dialogue(sample: DialogueSample) -> dict:
    issues = []

    if not sample.transcript:
        issues.append("transcript is empty")
    else:
        first_speaker = normalize_speaker(sample.transcript[0].speaker)
        if first_speaker not in {SERVICE_SPEAKER, USER_SPEAKER}:
            issues.append("dialogue must start with user or service")
        else:
            expected = first_speaker
            for turn in sample.transcript:
                if normalize_speaker(turn.speaker) != expected:
                    issues.append(
                        f"speaker order mismatch at round {turn.round_index}: expected {expected}"
                    )
                    break
                expected = USER_SPEAKER if expected == SERVICE_SPEAKER else SERVICE_SPEAKER

    required_slots: list[str] | None = None
    if sample.scenario:
        try:
            scenario = Scenario.from_dict(sample.scenario)
            required_slots = effective_required_slots(scenario)
        except (KeyError, TypeError, ValueError):
            required_slots = None
    if required_slots is None:
        missing_required = [slot for slot in sample.missing_slots if not sample.collected_slots.get(slot)]
    else:
        missing_required = [slot for slot in required_slots if not sample.collected_slots.get(slot)]
    if missing_required and sample.status == "completed":
        issues.append("status marked completed but required slots are still missing")
    issues.extend(_validate_topic_regression(sample))
    issues.extend(_validate_repeated_slot_collection(sample))

    return {
        "passed": not issues,
        "issues": issues,
        "required_slots_complete": not missing_required,
    }
