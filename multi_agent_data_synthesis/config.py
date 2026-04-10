from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    load_dotenv = None


ROOT_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = ROOT_DIR / ".env"


def _refresh_env_from_file() -> None:
    if load_dotenv:
        load_dotenv(ENV_PATH, override=True)

LLMS = {
    "gpt-4o": {
        "base_url": "",
        "api_key": "",
        "user": ""
    }
}

DEFAULT_MODEL_REQUEST_PROFILES = {
    "default": {
        "include_temperature": True,
        "include_max_tokens": True,
        "temperature_param": "temperature",
        "max_tokens_param": "max_tokens",
        "include_enable_thinking": True,
        "enable_thinking_param": "enable_thinking",
    },
    "gpt-5.3-chat": {
        "include_temperature": False,
        "include_max_tokens": False,
    },
}
DEFAULT_ADDRESS_SEGMENT_ROUNDS_WEIGHTS = {
    "2": 0.45,
    "3": 0.35,
    "4": 0.20,
}
DEFAULT_ADDRESS_SEGMENT_STRATEGY_WEIGHTS = {
    "province_city__district__locality__detail": 0.20,
    "province_city_district__locality__detail": 0.30,
    "province_city__district_locality__detail": 0.15,
    "province_city__district__locality_detail": 0.10,
    "province_city_district_locality__detail": 0.15,
    "province_city_district__locality_detail": 0.10,
}
DEFAULT_ADDRESS_KNOWN_MISMATCH_START_LEVEL_WEIGHTS = {
    "province": 0.05,
    "city": 0.10,
    "district": 0.15,
    "locality": 0.25,
    "building": 0.15,
    "unit": 0.10,
    "floor": 0.05,
    "room": 0.15,
}
DEFAULT_ADDRESS_KNOWN_MISMATCH_REWRITE_END_LEVEL_WEIGHTS = {
    "province": 0.05,
    "city": 0.08,
    "district": 0.10,
    "locality": 0.14,
    "building": 0.16,
    "unit": 0.16,
    "floor": 0.11,
    "room": 0.20,
}
DEFAULT_USER_ADDRESS_NONSTANDARD_STYLE_WEIGHTS = {
    "house_number_only": 0.45,
    "rural_group_number": 0.25,
    "landmark_poi": 0.30,
}
DEFAULT_USER_REPLY_OFF_TOPIC_TARGET_WEIGHTS = {
    "opening_confirmation": 0.08,
    "issue_description": 0.12,
    "surname_collection": 0.10,
    "phone_contact_confirmation": 0.08,
    "phone_keypad_input": 0.04,
    "phone_confirmation": 0.04,
    "address_collection": 0.30,
    "address_confirmation": 0.08,
    "product_arrival_confirmation": 0.08,
    "product_model_collection": 0.05,
    "closing_acknowledgement": 0.03,
}
DEFAULT_USER_REPLY_OFF_TOPIC_ROUNDS_WEIGHTS = {
    "1": 0.85,
    "2": 0.12,
    "3": 0.03,
}


@dataclass(frozen=True)
class AppConfig:
    openai_base_url: str
    openai_api_key: str
    user: str
    default_model: str
    user_agent_model: str
    service_agent_model: str
    default_temperature: float
    service_ok_prefix_probability: float
    second_round_include_issue_probability: float
    max_rounds: int
    max_concurrency: int
    request_timeout: float
    data_dir: Path
    output_dir: Path
    hidden_settings_store: Path
    hidden_settings_similarity_threshold: float
    hidden_settings_duplicate_threshold: float
    hidden_settings_max_attempts: int
    hidden_settings_multi_fault_probability: float
    installation_request_probability: float
    current_call_contactable_probability: float
    phone_collection_second_attempt_probability: float
    phone_collection_third_attempt_probability: float
    phone_collection_invalid_short_probability: float
    phone_collection_invalid_long_probability: float
    phone_collection_invalid_pattern_probability: float
    phone_collection_invalid_digit_mismatch_probability: float
    service_known_address_probability: float
    service_known_address_matches_probability: float
    address_collection_followup_probability: float
    address_segmented_reply_probability: float
    address_segment_rounds_weights: dict[str, float]
    address_segment_strategy_weights: dict[str, float]
    address_input_omit_province_city_suffix_probability: float
    address_confirmation_direct_correction_probability: float
    user_reply_off_topic_probability: float
    user_reply_off_topic_target_weights: dict[str, float]
    user_reply_off_topic_rounds_weights: dict[str, float]
    user_address_nonstandard_probability: float
    user_address_nonstandard_style_weights: dict[str, float] = field(
        default_factory=lambda: dict(DEFAULT_USER_ADDRESS_NONSTANDARD_STYLE_WEIGHTS)
    )
    address_known_mismatch_start_level_weights: dict[str, float] = field(
        default_factory=lambda: dict(DEFAULT_ADDRESS_KNOWN_MISMATCH_START_LEVEL_WEIGHTS)
    )
    address_known_mismatch_rewrite_end_level_weights: dict[str, float] = field(
        default_factory=lambda: dict(DEFAULT_ADDRESS_KNOWN_MISMATCH_REWRITE_END_LEVEL_WEIGHTS)
    )


def load_model_request_profiles() -> dict[str, dict[str, object]]:
    profiles = {
        model_name: dict(profile)
        for model_name, profile in DEFAULT_MODEL_REQUEST_PROFILES.items()
    }
    raw = os.getenv("MODEL_REQUEST_PROFILES", "").strip()
    if not raw:
        return profiles

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError("MODEL_REQUEST_PROFILES must be valid JSON.") from exc

    if not isinstance(parsed, dict):
        raise ValueError("MODEL_REQUEST_PROFILES must be a JSON object.")

    for model_name, profile in parsed.items():
        if not isinstance(profile, dict):
            raise ValueError("Each MODEL_REQUEST_PROFILES entry must be a JSON object.")
        merged = dict(profiles.get(model_name, {}))
        merged.update(profile)
        profiles[str(model_name)] = merged

    return profiles


def _load_weight_map(
    env_name: str,
    default: dict[str, float],
) -> dict[str, float]:
    raw = os.getenv(env_name, "").strip()
    if not raw:
        return dict(default)

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{env_name} must be valid JSON.") from exc

    if not isinstance(parsed, dict):
        raise ValueError(f"{env_name} must be a JSON object.")

    merged = dict(default)
    for key, value in parsed.items():
        merged[str(key)] = float(value)
    return merged


def load_config() -> AppConfig:
    _refresh_env_from_file()
    default_model = os.getenv("OPENAI_MODEL", "gpt-4o").strip()
    model_defaults = LLMS.get(default_model, {})
    api_key = os.getenv("OPENAI_API_KEY", model_defaults.get("api_key", "")).strip()
    if not api_key:
        raise ValueError("Missing OPENAI_API_KEY. Set it in environment variables or .env.")

    base_url = os.getenv("OPENAI_BASE_URL", model_defaults.get("base_url", "")).strip()
    if not base_url:
        raise ValueError("Missing OPENAI_BASE_URL. Set it in environment variables or .env.")

    user = os.getenv("OPENAI_USER", model_defaults.get("user", "")).strip()

    return AppConfig(
        openai_base_url=base_url,
        openai_api_key=api_key,
        user=user,
        default_model=default_model,
        user_agent_model=os.getenv("USER_AGENT_MODEL", default_model).strip(),
        service_agent_model=os.getenv("SERVICE_AGENT_MODEL", default_model).strip(),
        default_temperature=float(os.getenv("DEFAULT_TEMPERATURE", "0.7")),
        service_ok_prefix_probability=float(os.getenv("SERVICE_OK_PREFIX_PROBABILITY", "0.7")),
        second_round_include_issue_probability=float(
            os.getenv("SECOND_ROUND_INCLUDE_ISSUE_PROBABILITY", "0.4")
        ),
        max_rounds=int(os.getenv("MAX_ROUNDS", "20")),
        max_concurrency=max(1, int(os.getenv("MAX_CONCURRENCY", "5"))),
        request_timeout=float(os.getenv("REQUEST_TIMEOUT", "90")),
        data_dir=ROOT_DIR / "data",
        output_dir=ROOT_DIR / "outputs",
        hidden_settings_store=ROOT_DIR / "data" / "hidden_settings_history.jsonl",
        hidden_settings_similarity_threshold=float(
            os.getenv("HIDDEN_SETTINGS_SIMILARITY_THRESHOLD", "0.82")
        ),
        hidden_settings_duplicate_threshold=float(
            os.getenv("HIDDEN_SETTINGS_DUPLICATE_THRESHOLD", "0.5")
        ),
        hidden_settings_max_attempts=int(os.getenv("HIDDEN_SETTINGS_MAX_ATTEMPTS", "6")),
        hidden_settings_multi_fault_probability=float(
            os.getenv("HIDDEN_SETTINGS_MULTI_FAULT_PROBABILITY", "0.1")
        ),
        installation_request_probability=float(
            os.getenv("INSTALLATION_REQUEST_PROBABILITY", "0.5")
        ),
        current_call_contactable_probability=float(
            os.getenv("CURRENT_CALL_CONTACTABLE_PROBABILITY", "0.5")
        ),
        phone_collection_second_attempt_probability=float(
            os.getenv("PHONE_COLLECTION_SECOND_ATTEMPT_PROBABILITY", "0.35")
        ),
        phone_collection_third_attempt_probability=float(
            os.getenv("PHONE_COLLECTION_THIRD_ATTEMPT_PROBABILITY", "0.2")
        ),
        phone_collection_invalid_short_probability=float(
            os.getenv("PHONE_COLLECTION_INVALID_SHORT_PROBABILITY", "0.34")
        ),
        phone_collection_invalid_long_probability=float(
            os.getenv("PHONE_COLLECTION_INVALID_LONG_PROBABILITY", "0.33")
        ),
        phone_collection_invalid_pattern_probability=float(
            os.getenv("PHONE_COLLECTION_INVALID_PATTERN_PROBABILITY", "0.33")
        ),
        phone_collection_invalid_digit_mismatch_probability=float(
            os.getenv("PHONE_COLLECTION_INVALID_DIGIT_MISMATCH_PROBABILITY", "0.33")
        ),
        service_known_address_probability=float(
            os.getenv("SERVICE_KNOWN_ADDRESS_PROBABILITY", "0.2")
        ),
        service_known_address_matches_probability=float(
            os.getenv("SERVICE_KNOWN_ADDRESS_MATCHES_PROBABILITY", "0.7")
        ),
        address_collection_followup_probability=float(
            os.getenv("ADDRESS_COLLECTION_FOLLOWUP_PROBABILITY", "0.35")
        ),
        address_segmented_reply_probability=float(
            os.getenv(
                "ADDRESS_SEGMENTED_REPLY_PROBABILITY",
                os.getenv("ADDRESS_COLLECTION_FOLLOWUP_PROBABILITY", "0.35"),
            )
        ),
        address_segment_rounds_weights=_load_weight_map(
            "ADDRESS_SEGMENT_ROUNDS_WEIGHTS",
            DEFAULT_ADDRESS_SEGMENT_ROUNDS_WEIGHTS,
        ),
        address_segment_strategy_weights=_load_weight_map(
            "ADDRESS_SEGMENT_MERGE_STRATEGY_WEIGHTS",
            DEFAULT_ADDRESS_SEGMENT_STRATEGY_WEIGHTS,
        ),
        address_input_omit_province_city_suffix_probability=float(
            os.getenv("ADDRESS_INPUT_OMIT_PROVINCE_CITY_SUFFIX_PROBABILITY", "0.0")
        ),
        address_confirmation_direct_correction_probability=float(
            os.getenv("ADDRESS_CONFIRMATION_DIRECT_CORRECTION_PROBABILITY", "0.5")
        ),
        user_reply_off_topic_probability=float(
            os.getenv("USER_REPLY_OFF_TOPIC_PROBABILITY", "0.18")
        ),
        user_reply_off_topic_target_weights=_load_weight_map(
            "USER_REPLY_OFF_TOPIC_TARGET_WEIGHTS",
            DEFAULT_USER_REPLY_OFF_TOPIC_TARGET_WEIGHTS,
        ),
        user_reply_off_topic_rounds_weights=_load_weight_map(
            "USER_REPLY_OFF_TOPIC_ROUNDS_WEIGHTS",
            DEFAULT_USER_REPLY_OFF_TOPIC_ROUNDS_WEIGHTS,
        ),
        user_address_nonstandard_probability=float(
            os.getenv("USER_ADDRESS_NONSTANDARD_PROBABILITY", "0.28")
        ),
        user_address_nonstandard_style_weights=_load_weight_map(
            "USER_ADDRESS_NONSTANDARD_STYLE_WEIGHTS",
            DEFAULT_USER_ADDRESS_NONSTANDARD_STYLE_WEIGHTS,
        ),
        address_known_mismatch_start_level_weights=_load_weight_map(
            "ADDRESS_KNOWN_MISMATCH_START_LEVEL_WEIGHTS",
            DEFAULT_ADDRESS_KNOWN_MISMATCH_START_LEVEL_WEIGHTS,
        ),
        address_known_mismatch_rewrite_end_level_weights=_load_weight_map(
            "ADDRESS_KNOWN_MISMATCH_REWRITE_END_LEVEL_WEIGHTS",
            DEFAULT_ADDRESS_KNOWN_MISMATCH_REWRITE_END_LEVEL_WEIGHTS,
        ),
    )
