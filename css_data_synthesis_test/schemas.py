from __future__ import annotations

from dataclasses import asdict, dataclass, field, replace
from typing import Any

DEFAULT_PRODUCT_CATEGORY = "空气能热水机"
SERVICE_SPEAKER = "service"
USER_SPEAKER = "user"
SPEAKER_DISPLAY_NAMES = {
    SERVICE_SPEAKER: "客服",
    USER_SPEAKER: "用户",
}
SPEAKER_ALIASES = {
    SERVICE_SPEAKER: SERVICE_SPEAKER,
    "客服": SERVICE_SPEAKER,
    USER_SPEAKER: USER_SPEAKER,
    "用户": USER_SPEAKER,
}

SLOT_DESCRIPTIONS = {
    "issue_description": "用户对故障或安装诉求的具体描述",
    "surname": "用户姓氏",
    "phone": "联系电话",
    "address": "详细上门地址",
    "product_model": "家电型号",
    "request_type": "诉求类型，通常为 fault 或 installation",
    "purchase_channel": "购买渠道",
    "availability": "用户可预约的上门时间",
    "phone_contactable": "当前来电号码是否可联系到用户",
    "phone_contact_owner": "登记号码归属，如本人、爱人、朋友等",
    "phone_collection_attempts": "拨号盘录入联系方式的尝试次数",
    "product_arrived": "安装场景下产品是否已到货",
    "product_routing_result": "产品归属识别结果，如家用、楼宇或转人工",
}

SUPPLEMENTARY_COLLECTED_SLOTS = (
    "phone_contactable",
    "phone_contact_owner",
    "phone_collection_attempts",
    "product_arrived",
    "product_routing_result",
)


def normalize_speaker(speaker: str) -> str:
    normalized = str(speaker or "").strip()
    return SPEAKER_ALIASES.get(normalized, normalized)


def display_speaker(speaker: str) -> str:
    return SPEAKER_DISPLAY_NAMES.get(normalize_speaker(speaker), str(speaker or "").strip())


@dataclass
class ProductProfile:
    brand: str
    model: str
    category: str = DEFAULT_PRODUCT_CATEGORY
    purchase_channel: str = ""


@dataclass
class CustomerProfile:
    full_name: str
    surname: str
    phone: str
    address: str
    persona: str
    speech_style: str = ""


@dataclass
class ServiceRequest:
    request_type: str
    issue: str
    desired_resolution: str
    availability: str = ""


@dataclass
class Scenario:
    scenario_id: str
    product: ProductProfile
    customer: CustomerProfile
    request: ServiceRequest
    call_start_time: str = ""
    hidden_context: dict[str, Any] = field(default_factory=dict)
    required_slots: list[str] = field(default_factory=list)
    max_turns: int = 20
    tags: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Scenario":
        product_data = dict(data["product"])
        if not str(product_data.get("category", "")).strip():
            product_data["category"] = DEFAULT_PRODUCT_CATEGORY
        scenario = cls(
            scenario_id=data["scenario_id"],
            product=ProductProfile(**product_data),
            customer=CustomerProfile(**data["customer"]),
            request=ServiceRequest(**data["request"]),
            call_start_time=str(data.get("call_start_time", "")).strip(),
            hidden_context=dict(data.get("hidden_context", {})),
            required_slots=list(data.get("required_slots", [])),
            max_turns=int(data.get("max_turns", 20)),
            tags=list(data.get("tags", [])),
        )
        scenario.validate_domain()
        return scenario

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def clone_with_id(self, scenario_id: str) -> "Scenario":
        return replace(self, scenario_id=scenario_id)

    def with_call_start_time(self, call_start_time: str) -> "Scenario":
        return replace(self, call_start_time=call_start_time)

    def with_generated_hidden_settings(
        self,
        *,
        customer: CustomerProfile,
        request: ServiceRequest,
        hidden_context: dict[str, Any],
    ) -> "Scenario":
        return replace(
            self,
            customer=customer,
            request=request,
            hidden_context=hidden_context,
        )

    def validate_domain(self) -> None:
        if str(self.product.brand).strip() != "美的":
            raise ValueError("Only 美的 product scenarios are supported.")
        if not str(self.product.category).strip():
            raise ValueError(
                "Product category must not be empty."
            )


@dataclass
class DialogueTurn:
    speaker: str
    text: str
    round_index: int
    model_intent_inference_used: bool = False
    previous_user_intent_model_inference_used: bool | None = None
    post_display_lines: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @property
    def effective_model_intent_inference_used(self) -> bool:
        if (
            normalize_speaker(self.speaker) == SERVICE_SPEAKER
            and self.previous_user_intent_model_inference_used is not None
        ):
            return bool(self.previous_user_intent_model_inference_used)
        return bool(self.model_intent_inference_used)

    def to_display_dict(self) -> dict[str, Any]:
        round_label = str(self.round_index)
        effective_used = self.effective_model_intent_inference_used
        if normalize_speaker(self.speaker) == SERVICE_SPEAKER and effective_used:
            round_label = f"{round_label}*"
        return {
            "display_kind": "turn",
            "speaker": display_speaker(self.speaker),
            "text": self.text,
            "round_index": self.round_index,
            "round_label": round_label,
            "model_intent_inference_used": effective_used,
            "previous_user_intent_model_inference_used": (
                effective_used if normalize_speaker(self.speaker) == SERVICE_SPEAKER else None
            ),
            "post_display_lines": list(self.post_display_lines),
        }


def build_display_transcript(transcript: list[DialogueTurn]) -> list[dict[str, Any]]:
    display_transcript: list[dict[str, Any]] = []
    for turn in transcript:
        display_turn = turn.to_display_dict()
        post_display_lines = list(display_turn.pop("post_display_lines", []))
        display_transcript.append(display_turn)
        for line in post_display_lines:
            display_transcript.append(
                {
                    "display_kind": "function_call",
                    "speaker": "",
                    "text": str(line),
                    "round_index": turn.round_index,
                    "round_label": "",
                    "model_intent_inference_used": False,
                    "previous_user_intent_model_inference_used": None,
                }
            )
    return display_transcript


@dataclass
class DialogueSample:
    scenario_id: str
    status: str
    rounds_used: int
    transcript: list[DialogueTurn]
    collected_slots: dict[str, str]
    missing_slots: list[str]
    scenario: dict[str, Any]
    validation: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        display_transcript = build_display_transcript(self.transcript)
        data["transcript"] = display_transcript
        data["dialogue_process"] = display_transcript
        data["dialogue_text"] = "\n".join(
            (
                turn["text"]
                if turn.get("display_kind") == "function_call"
                else f"[{turn['round_label']}] {turn['speaker']}: {turn['text']}"
            )
            for turn in display_transcript
        )
        data["related_info"] = {
            "product": data["scenario"]["product"],
            "customer": data["scenario"]["customer"],
            "request": data["scenario"]["request"],
            "hidden_context": data["scenario"].get("hidden_context", {}),
            "required_slots": data["scenario"].get("required_slots", []),
            "collected_slots": data["collected_slots"],
            "missing_slots": data["missing_slots"],
            "status": data["status"],
            "validation": data["validation"],
        }
        return data


def effective_required_slots(scenario: Scenario) -> list[str]:
    skip_slots: set[str] = set()
    if scenario.request.request_type == "fault":
        skip_slots.update({"product_model", "availability", "purchase_channel"})
    if scenario.request.request_type == "installation":
        skip_slots.update({"product_model", "availability", "purchase_channel"})
    return [slot for slot in scenario.required_slots if slot not in skip_slots]
