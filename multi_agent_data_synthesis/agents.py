from __future__ import annotations

from typing import Any

from multi_agent_data_synthesis.dialogue_plans import resolve_second_round_reply_strategy
from multi_agent_data_synthesis.llm import OpenAIChatClient
from multi_agent_data_synthesis.prompts import build_user_agent_messages
from multi_agent_data_synthesis.schemas import DialogueTurn, Scenario, SERVICE_SPEAKER
from multi_agent_data_synthesis.service_policy import (
    ServiceDialoguePolicy,
    ServiceRuntimeState,
)


class UserAgent:
    def __init__(
        self,
        client: OpenAIChatClient,
        model: str,
        temperature: float,
        second_round_include_issue_probability: float,
    ):
        self.client = client
        self.model = model
        self.temperature = temperature
        self.second_round_include_issue_probability = second_round_include_issue_probability

    @staticmethod
    def _last_service_text(transcript: list[DialogueTurn]) -> str:
        for turn in reversed(transcript):
            if turn.speaker == SERVICE_SPEAKER:
                return turn.text
        return ""

    @staticmethod
    def _forced_satisfaction_rating(scenario: Scenario, round_index: int) -> str:
        basis = f"{scenario.scenario_id}:{round_index}"
        return "1" if sum(ord(char) for char in basis) % 2 == 0 else "2"

    def respond(
        self,
        *,
        scenario: Scenario,
        transcript: list[DialogueTurn],
        round_index: int,
    ) -> dict[str, Any]:
        if ServiceDialoguePolicy.is_satisfaction_prompt(self._last_service_text(transcript)):
            return {
                "reply": self._forced_satisfaction_rating(scenario, round_index),
                "call_complete": True,
            }
        second_round_reply_strategy = resolve_second_round_reply_strategy(
            scenario_id=scenario.scenario_id,
            hidden_context=scenario.hidden_context,
            include_issue_probability=self.second_round_include_issue_probability,
        )
        payload = self.client.complete_json(
            model=self.model,
            messages=build_user_agent_messages(
                scenario,
                transcript,
                round_index,
                second_round_reply_strategy=second_round_reply_strategy,
            ),
            temperature=self.temperature,
        )
        return {
            "reply": str(payload.get("reply", "")).strip(),
            "call_complete": bool(payload.get("call_complete", False)),
        }

    async def respond_async(
        self,
        *,
        scenario: Scenario,
        transcript: list[DialogueTurn],
        round_index: int,
    ) -> dict[str, Any]:
        if ServiceDialoguePolicy.is_satisfaction_prompt(self._last_service_text(transcript)):
            return {
                "reply": self._forced_satisfaction_rating(scenario, round_index),
                "call_complete": True,
            }
        second_round_reply_strategy = resolve_second_round_reply_strategy(
            scenario_id=scenario.scenario_id,
            hidden_context=scenario.hidden_context,
            include_issue_probability=self.second_round_include_issue_probability,
        )
        payload = await self.client.complete_json_async(
            model=self.model,
            messages=build_user_agent_messages(
                scenario,
                transcript,
                round_index,
                second_round_reply_strategy=second_round_reply_strategy,
            ),
            temperature=self.temperature,
        )
        return {
            "reply": str(payload.get("reply", "")).strip(),
            "call_complete": bool(payload.get("call_complete", False)),
        }


class ServiceAgent:
    def __init__(
        self,
        client: OpenAIChatClient,
        model: str,
        temperature: float,
        ok_prefix_probability: float = 1.0,
    ):
        self.client = client
        self.model = model
        self.temperature = temperature
        self.policy = ServiceDialoguePolicy(
            ok_prefix_probability=ok_prefix_probability,
            address_inference_callback=self._infer_address_candidate_with_model,
        )

    def _infer_address_candidate_with_model(
        self,
        *,
        user_text: str,
        confirmation_address: str,
        partial_address_candidate: str,
        last_address_followup_prompt: str,
    ) -> dict[str, Any]:
        system_prompt = """你是家电客服对话里的地址识别助手。

任务：
1. 只提取用户这一轮明确说出的地址内容。
2. 去掉抱怨、路线说明、上门提醒、停车说明等非地址信息。
3. 不要脑补用户没说出的省、市、区、镇、村、小区、门牌号。
4. 如果这一轮没有明确说出可用地址，就返回空字符串。

输出 JSON：
{
  "address_candidate": "提取后的地址片段，没有就返回空字符串",
  "granularity": "none|admin_region|locality|detail|locality_with_detail|complete"
}
"""
        user_prompt = f"""请基于下面信息识别本轮用户明确说出的地址。

上一轮客服话术：
{last_address_followup_prompt or '无'}

客服正在核对或上下文中的地址：
{confirmation_address or '无'}

当前已积累的地址片段：
{partial_address_candidate or '无'}

用户本轮原话：
{user_text}

只返回 JSON。"""
        payload = self.client.complete_json(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.0,
        )
        return {
            "address_candidate": str(payload.get("address_candidate", "")).strip(),
            "granularity": str(payload.get("granularity", "")).strip(),
        }

    def respond(
        self,
        *,
        scenario: Scenario,
        transcript: list[DialogueTurn],
        collected_slots: dict[str, str],
        runtime_state: ServiceRuntimeState,
    ) -> dict[str, Any]:
        result = self.policy.respond(
            scenario=scenario,
            transcript=transcript,
            collected_slots=collected_slots,
            runtime_state=runtime_state,
        )
        return {
            "reply": result.reply,
            "slot_updates": result.slot_updates,
            "is_ready_to_close": result.is_ready_to_close,
        }

    def build_initial_user_utterance(self, scenario: Scenario) -> str:
        return self.policy.build_initial_user_utterance(scenario)
