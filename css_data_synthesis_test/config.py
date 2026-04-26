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

MODEL_ENV_PREFIXES = {
    "gpt-4o": "OPENAI_GPT_4O",
    "qwen3-32b": "OPENAI_QWEN3_32B",
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
    "gpt-4o": {
        "include_enable_thinking": False,
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
    "5": 0.05,
}
DEFAULT_ADDRESS_SEGMENT_2_STRATEGY_WEIGHTS = {
    "province_city_district_locality__detail": 0.6,
    "province_city_district__locality_detail": 0.4,
}
DEFAULT_ADDRESS_SEGMENT_3_STRATEGY_WEIGHTS = {
    "province_city_district__locality__detail": 0.5454545454545454,
    "province_city__district_locality__detail": 0.2727272727272727,
    "province_city__district__locality_detail": 0.18181818181818182,
}
DEFAULT_ADDRESS_SEGMENT_4_STRATEGY_WEIGHTS = {
    "province_city__district__locality__detail": 1.0,
}
DEFAULT_ADDRESS_SEGMENT_5_STRATEGY_WEIGHTS = {
    "province__city__district__locality__detail": 1.0,
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
DEFAULT_PRODUCT_ROUTING_ENTRY_WEIGHTS = {
    "brand_series": 0.35,
    "model": 0.05,
    "unknown": 0.60,
}
DEFAULT_PRODUCT_ROUTING_BRAND_SERIES_WEIGHTS = {
    "colmo": 0.23,
    "cooling_or_little_swan": 0.15,
    "home_series": 0.40,
    "lieyan": 0.22,
}
DEFAULT_PRODUCT_ROUTING_USAGE_SCENE_WEIGHTS = {
    "family": 0.56,
    "villa_apartment_barber": 0.20,
    "other_unknown": 0.24,
}
DEFAULT_PRODUCT_ROUTING_PURCHASE_OR_PROPERTY_WEIGHTS = {
    "self_buy": 0.65,
    "unknown": 0.10,
    "property_bundle": 0.25,
}
DEFAULT_PRODUCT_ROUTING_PROPERTY_YEAR_WEIGHTS = {
    "before_2021": 0.60,
    "after_2021": 0.40,
}
DEFAULT_PRODUCT_ROUTING_HISTORY_CONFIRMATION_WEIGHTS = {
    "yes": 0.68,
    "no_unknown": 0.32,
}
DEFAULT_AUTO_MODE_IVR_PRODUCT_KIND_WEIGHTS = {
    "air_energy": 0.7,
    "water_heater": 0.3,
}
DEFAULT_AUTO_MODE_WATER_HEATER_OPENING_REPLY_WEIGHTS = {
    "confirm": 0.45,
    "change_brand": 0.15,
    "change_product_type": 0.15,
    "change_request": 0.15,
    "change_brand_request": 0.10,
}
DEFAULT_AUTO_MODE_HISTORY_DEVICE_BRAND_WEIGHTS = {
    "美的": 0.25,
    "COLMO": 0.20,
    "真暖": 0.10,
    "真省": 0.10,
    "雪焰": 0.08,
    "暖家": 0.08,
    "煤改电": 0.07,
    "真享": 0.07,
    "烈焰": 0.05,
}
DEFAULT_AUTO_MODE_HISTORY_DEVICE_CATEGORY_WEIGHTS = {
    "家用空气能热水机": 0.75,
    "空气能热水机": 0.25,
}
SERVICE_QUERY_PREFIX_CHOICES = ("好的", "嗯嗯", "了解了", "")


def _load_bool(env_name: str, default: bool) -> bool:
    raw = os.getenv(env_name, "").strip().lower()
    if not raw:
        return default
    if raw in {"1", "true", "yes", "on"}:
        return True
    if raw in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"{env_name} must be a boolean-like value.")


@dataclass(frozen=True)
class AppConfig:
    openai_base_url: str
    openai_api_key: str
    user: str
    default_model: str
    user_agent_model: str
    service_agent_model: str
    model_endpoints: dict[str, dict[str, str]]
    default_temperature: float
    service_ok_prefix_probability: float
    service_query_prefix_weights: dict[str, float]
    second_round_include_issue_probability: float
    max_rounds: int
    max_concurrency: int
    request_timeout: float
    data_dir: Path
    output_dir: Path
    hidden_settings_store: Path | None
    utterance_reference_library_path: Path
    utterance_reference_sample_probability: float
    product_routing_enabled: bool
    product_routing_apply_probability: float
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
    address_segment_2_strategy_weights: dict[str, float]
    address_segment_3_strategy_weights: dict[str, float]
    address_segment_4_strategy_weights: dict[str, float]
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
    address_segment_5_strategy_weights: dict[str, float] = field(
        default_factory=lambda: dict(DEFAULT_ADDRESS_SEGMENT_5_STRATEGY_WEIGHTS)
    )
    product_routing_entry_weights: dict[str, float] = field(
        default_factory=lambda: dict(DEFAULT_PRODUCT_ROUTING_ENTRY_WEIGHTS)
    )
    product_routing_brand_series_weights: dict[str, float] = field(
        default_factory=lambda: dict(DEFAULT_PRODUCT_ROUTING_BRAND_SERIES_WEIGHTS)
    )
    product_routing_usage_scene_weights: dict[str, float] = field(
        default_factory=lambda: dict(DEFAULT_PRODUCT_ROUTING_USAGE_SCENE_WEIGHTS)
    )
    product_routing_purchase_or_property_weights: dict[str, float] = field(
        default_factory=lambda: dict(DEFAULT_PRODUCT_ROUTING_PURCHASE_OR_PROPERTY_WEIGHTS)
    )
    product_routing_property_year_weights: dict[str, float] = field(
        default_factory=lambda: dict(DEFAULT_PRODUCT_ROUTING_PROPERTY_YEAR_WEIGHTS)
    )
    product_routing_history_confirmation_weights: dict[str, float] = field(
        default_factory=lambda: dict(DEFAULT_PRODUCT_ROUTING_HISTORY_CONFIRMATION_WEIGHTS)
    )
    auto_mode_ivr_product_kind_weights: dict[str, float] = field(
        default_factory=lambda: dict(DEFAULT_AUTO_MODE_IVR_PRODUCT_KIND_WEIGHTS)
    )
    auto_mode_water_heater_opening_reply_weights: dict[str, float] = field(
        default_factory=lambda: dict(DEFAULT_AUTO_MODE_WATER_HEATER_OPENING_REPLY_WEIGHTS)
    )
    auto_mode_history_device_probability: float = 0.35
    auto_mode_history_device_brand_weights: dict[str, float] = field(
        default_factory=lambda: dict(DEFAULT_AUTO_MODE_HISTORY_DEVICE_BRAND_WEIGHTS)
    )
    auto_mode_history_device_category_weights: dict[str, float] = field(
        default_factory=lambda: dict(DEFAULT_AUTO_MODE_HISTORY_DEVICE_CATEGORY_WEIGHTS)
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


def _load_model_endpoints() -> dict[str, dict[str, str]]:
    endpoints: dict[str, dict[str, str]] = {}
    for fallback_model, prefix in MODEL_ENV_PREFIXES.items():
        model_name = os.getenv(f"{prefix}_MODEL", fallback_model).strip() or fallback_model
        base_url = os.getenv(f"{prefix}_BASE_URL", "").strip()
        api_key = os.getenv(f"{prefix}_API_KEY", "").strip()
        user = os.getenv(f"{prefix}_USER", "").strip()
        if base_url or api_key or user:
            endpoints[model_name] = {
                "base_url": base_url,
                "api_key": api_key,
                "user": user,
            }

    legacy_model = os.getenv("OPENAI_MODEL", "").strip()
    legacy_base_url = os.getenv("OPENAI_BASE_URL", "").strip()
    legacy_api_key = os.getenv("OPENAI_API_KEY", "").strip()
    legacy_user = os.getenv("OPENAI_USER", "").strip()
    if legacy_model and (legacy_base_url or legacy_api_key or legacy_user):
        endpoints.setdefault(
            legacy_model,
            {
                "base_url": legacy_base_url,
                "api_key": legacy_api_key,
                "user": legacy_user,
            },
        )

    return endpoints


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


def _load_optional_weight_map(env_name: str) -> dict[str, float] | None:
    raw = os.getenv(env_name, "").strip()
    if not raw:
        return None

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{env_name} must be valid JSON.") from exc

    if not isinstance(parsed, dict):
        raise ValueError(f"{env_name} must be a JSON object.")

    return {str(key): float(value) for key, value in parsed.items()}


def _load_service_query_prefix_weights(ok_prefix_probability: float) -> dict[str, float]:
    raw = os.getenv("SERVICE_QUERY_PREFIX_WEIGHTS", "").strip()
    if not raw:
        probability = max(0.0, min(1.0, float(ok_prefix_probability)))
        return {
            "好的": probability,
            "嗯嗯": 0.0,
            "了解了": 0.0,
            "": 1.0 - probability,
        }

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError("SERVICE_QUERY_PREFIX_WEIGHTS must be valid JSON.") from exc

    if not isinstance(parsed, dict):
        raise ValueError("SERVICE_QUERY_PREFIX_WEIGHTS must be a JSON object.")

    weights = {prefix: 0.0 for prefix in SERVICE_QUERY_PREFIX_CHOICES}
    for key, value in parsed.items():
        prefix = str(key)
        if prefix not in weights:
            allowed = "、".join(f'"{item}"' for item in SERVICE_QUERY_PREFIX_CHOICES)
            raise ValueError(f"SERVICE_QUERY_PREFIX_WEIGHTS only supports prefixes: {allowed}.")
        weights[prefix] = max(0.0, float(value))
    if sum(weights.values()) <= 0:
        raise ValueError("SERVICE_QUERY_PREFIX_WEIGHTS must contain at least one positive weight.")
    return weights


def _load_segment_strategy_weights(
    *,
    env_name: str,
    default: dict[str, float],
    legacy_values: dict[str, float] | None = None,
) -> dict[str, float]:
    override_values = _load_optional_weight_map(env_name)
    if override_values:
        total = sum(max(0.0, float(value)) for value in override_values.values())
        if abs(total - 1.0) > 1e-6:
            raise ValueError(f"{env_name} must sum to 1.0 within its segment choices.")
        return {str(key): float(value) for key, value in override_values.items()}

    if legacy_values:
        filtered_legacy_values = {
            key: float(value)
            for key, value in legacy_values.items()
            if key in default
        }
        total = sum(max(0.0, float(value)) for value in filtered_legacy_values.values())
        if total > 0:
            return {
                key: max(0.0, float(value)) / total
                for key, value in filtered_legacy_values.items()
            }

    return dict(default)


def load_config() -> AppConfig:
    _refresh_env_from_file()
    default_model = os.getenv("OPENAI_DEFAULT_MODEL", os.getenv("OPENAI_MODEL", "gpt-4o")).strip()
    model_endpoints = _load_model_endpoints()
    model_defaults = model_endpoints.get(default_model, {})
    api_key = (
        model_defaults.get("api_key", "")
        or os.getenv("OPENAI_API_KEY", "")
    ).strip()
    if not api_key:
        raise ValueError(
            f"Missing API key for {default_model}. Set {MODEL_ENV_PREFIXES.get(default_model, 'OPENAI')}_API_KEY."
        )

    base_url = (
        model_defaults.get("base_url", "")
        or os.getenv("OPENAI_BASE_URL", "")
    ).strip()
    if not base_url:
        raise ValueError(
            f"Missing base URL for {default_model}. Set {MODEL_ENV_PREFIXES.get(default_model, 'OPENAI')}_BASE_URL."
        )

    user = (
        model_defaults.get("user", "")
        or os.getenv("OPENAI_USER", "")
    ).strip()
    legacy_segment_strategy_weights = _load_optional_weight_map(
        "ADDRESS_SEGMENT_MERGE_STRATEGY_WEIGHTS"
    )

    service_ok_prefix_probability = float(os.getenv("SERVICE_OK_PREFIX_PROBABILITY", "0.7"))

    return AppConfig(
        openai_base_url=base_url,
        openai_api_key=api_key,
        user=user,
        default_model=default_model,
        user_agent_model=os.getenv("USER_AGENT_MODEL", default_model).strip() or default_model,
        service_agent_model=os.getenv("SERVICE_AGENT_MODEL", default_model).strip() or default_model,
        model_endpoints=model_endpoints,
        default_temperature=float(os.getenv("DEFAULT_TEMPERATURE", "1.0")),
        service_ok_prefix_probability=service_ok_prefix_probability,
        service_query_prefix_weights=_load_service_query_prefix_weights(service_ok_prefix_probability),
        second_round_include_issue_probability=float(
            os.getenv("SECOND_ROUND_INCLUDE_ISSUE_PROBABILITY", "0.4")
        ),
        max_rounds=int(os.getenv("MAX_ROUNDS", "20")),
        max_concurrency=max(1, int(os.getenv("MAX_CONCURRENCY", "5"))),
        request_timeout=float(os.getenv("REQUEST_TIMEOUT", "90")),
        data_dir=ROOT_DIR / "data",
        output_dir=ROOT_DIR / "outputs",
        hidden_settings_store=ROOT_DIR / "data" / "hidden_settings_history.jsonl",
        utterance_reference_library_path=ROOT_DIR / "data" / "utterance_reference_library.json",
        utterance_reference_sample_probability=float(
            os.getenv("UTTERANCE_REFERENCE_SAMPLE_PROBABILITY", "0.9")
        ),
        product_routing_enabled=_load_bool("PRODUCT_ROUTING_ENABLED", True),
        product_routing_apply_probability=float(
            os.getenv("PRODUCT_ROUTING_APPLY_PROBABILITY", "1.0")
        ),
        product_routing_entry_weights=_load_weight_map(
            "PRODUCT_ROUTING_ENTRY_WEIGHTS",
            DEFAULT_PRODUCT_ROUTING_ENTRY_WEIGHTS,
        ),
        product_routing_brand_series_weights=_load_weight_map(
            "PRODUCT_ROUTING_BRAND_SERIES_WEIGHTS",
            DEFAULT_PRODUCT_ROUTING_BRAND_SERIES_WEIGHTS,
        ),
        product_routing_usage_scene_weights=_load_weight_map(
            "PRODUCT_ROUTING_USAGE_SCENE_WEIGHTS",
            DEFAULT_PRODUCT_ROUTING_USAGE_SCENE_WEIGHTS,
        ),
        product_routing_purchase_or_property_weights=_load_weight_map(
            "PRODUCT_ROUTING_PURCHASE_OR_PROPERTY_WEIGHTS",
            DEFAULT_PRODUCT_ROUTING_PURCHASE_OR_PROPERTY_WEIGHTS,
        ),
        product_routing_property_year_weights=_load_weight_map(
            "PRODUCT_ROUTING_PROPERTY_YEAR_WEIGHTS",
            DEFAULT_PRODUCT_ROUTING_PROPERTY_YEAR_WEIGHTS,
        ),
        product_routing_history_confirmation_weights=_load_weight_map(
            "PRODUCT_ROUTING_HISTORY_CONFIRMATION_WEIGHTS",
            DEFAULT_PRODUCT_ROUTING_HISTORY_CONFIRMATION_WEIGHTS,
        ),
        auto_mode_ivr_product_kind_weights=_load_weight_map(
            "AUTO_MODE_IVR_PRODUCT_KIND_WEIGHTS",
            DEFAULT_AUTO_MODE_IVR_PRODUCT_KIND_WEIGHTS,
        ),
        auto_mode_water_heater_opening_reply_weights=_load_weight_map(
            "AUTO_MODE_WATER_HEATER_OPENING_REPLY_WEIGHTS",
            DEFAULT_AUTO_MODE_WATER_HEATER_OPENING_REPLY_WEIGHTS,
        ),
        auto_mode_history_device_probability=float(
            os.getenv("AUTO_MODE_HISTORY_DEVICE_PROBABILITY", "0.35")
        ),
        auto_mode_history_device_brand_weights=_load_weight_map(
            "AUTO_MODE_HISTORY_DEVICE_BRAND_WEIGHTS",
            DEFAULT_AUTO_MODE_HISTORY_DEVICE_BRAND_WEIGHTS,
        ),
        auto_mode_history_device_category_weights=_load_weight_map(
            "AUTO_MODE_HISTORY_DEVICE_CATEGORY_WEIGHTS",
            DEFAULT_AUTO_MODE_HISTORY_DEVICE_CATEGORY_WEIGHTS,
        ),
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
        address_segment_2_strategy_weights=_load_segment_strategy_weights(
            env_name="ADDRESS_SEGMENT_2_STRATEGY_WEIGHTS",
            default=DEFAULT_ADDRESS_SEGMENT_2_STRATEGY_WEIGHTS,
            legacy_values=legacy_segment_strategy_weights,
        ),
        address_segment_3_strategy_weights=_load_segment_strategy_weights(
            env_name="ADDRESS_SEGMENT_3_STRATEGY_WEIGHTS",
            default=DEFAULT_ADDRESS_SEGMENT_3_STRATEGY_WEIGHTS,
            legacy_values=legacy_segment_strategy_weights,
        ),
        address_segment_4_strategy_weights=_load_segment_strategy_weights(
            env_name="ADDRESS_SEGMENT_4_STRATEGY_WEIGHTS",
            default=DEFAULT_ADDRESS_SEGMENT_4_STRATEGY_WEIGHTS,
            legacy_values=legacy_segment_strategy_weights,
        ),
        address_segment_5_strategy_weights=_load_segment_strategy_weights(
            env_name="ADDRESS_SEGMENT_5_STRATEGY_WEIGHTS",
            default=DEFAULT_ADDRESS_SEGMENT_5_STRATEGY_WEIGHTS,
            legacy_values=legacy_segment_strategy_weights,
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
