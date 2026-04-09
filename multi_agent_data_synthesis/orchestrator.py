from __future__ import annotations

import asyncio

from multi_agent_data_synthesis.agents import ServiceAgent, UserAgent
from multi_agent_data_synthesis.config import AppConfig
from multi_agent_data_synthesis.hidden_settings_tool import HiddenSettingsTool
from multi_agent_data_synthesis.llm import OpenAIChatClient
from multi_agent_data_synthesis.schemas import (
    DialogueSample,
    DialogueTurn,
    Scenario,
    SERVICE_SPEAKER,
    USER_SPEAKER,
    display_speaker,
    effective_required_slots,
)
from multi_agent_data_synthesis.service_policy import ServiceRuntimeState
from multi_agent_data_synthesis.validator import validate_dialogue


class DialogueOrchestrator:
    def __init__(
        self,
        config: AppConfig,
        auto_generate_hidden_settings: bool = False,
        show_dialogue_progress: bool = False,
        show_persona_profile: bool = False,
    ):
        self.config = config
        self.client = OpenAIChatClient(config)
        self.auto_generate_hidden_settings = auto_generate_hidden_settings
        self.show_dialogue_progress = show_dialogue_progress
        self.show_persona_profile = show_persona_profile
        self._print_lock = asyncio.Lock()
        self.hidden_settings_tool = HiddenSettingsTool(self.client, config)
        self.user_agent = UserAgent(
            self.client,
            model=config.user_agent_model,
            temperature=config.default_temperature,
            second_round_include_issue_probability=config.second_round_include_issue_probability,
        )
        self.service_agent = ServiceAgent(
            self.client,
            model=config.service_agent_model,
            temperature=config.default_temperature,
            ok_prefix_probability=config.service_ok_prefix_probability,
        )

    def generate_dialogue(self, scenario: Scenario) -> DialogueSample:
        return asyncio.run(self.generate_dialogue_async(scenario))

    async def generate_dialogue_async(self, scenario: Scenario) -> DialogueSample:
        if self.auto_generate_hidden_settings:
            scenario = await self.hidden_settings_tool.generate_for_scenario_async(scenario)
        if self.show_dialogue_progress:
            await self._print_dialogue_header_async(scenario)
        transcript: list[DialogueTurn] = []
        required_slots = effective_required_slots(scenario)
        collected_slots = {slot: "" for slot in required_slots}
        collected_slots.setdefault("phone_contactable", "")
        collected_slots.setdefault("phone_contact_owner", "")
        collected_slots.setdefault("phone_collection_attempts", "")
        collected_slots.setdefault("product_arrived", "")
        ready_to_close = False
        rounds_limit = scenario.max_turns or self.config.max_rounds
        runtime_state = ServiceRuntimeState()

        initial_user_utterance = self.service_agent.build_initial_user_utterance(scenario)
        transcript.append(
            DialogueTurn(
                speaker=USER_SPEAKER,
                text=initial_user_utterance,
                round_index=1,
            )
        )
        if self.show_dialogue_progress:
            await self._print_turn_async(USER_SPEAKER, 1, initial_user_utterance)

        opening_action = self.service_agent.respond(
            scenario=scenario,
            transcript=transcript,
            collected_slots=collected_slots,
            runtime_state=runtime_state,
        )
        transcript.append(
            DialogueTurn(
                speaker=SERVICE_SPEAKER,
                text=opening_action["reply"],
                round_index=1,
            )
        )
        if self.show_dialogue_progress:
            await self._print_turn_async(SERVICE_SPEAKER, 1, opening_action["reply"])

        self._merge_slots(collected_slots, opening_action["slot_updates"], required_slots)
        self._merge_slots(
            collected_slots,
            opening_action["slot_updates"],
            ["phone_contactable", "phone_contact_owner", "phone_collection_attempts", "product_arrived"],
        )

        ready_to_close = opening_action["is_ready_to_close"]
        if not (ready_to_close and self._all_required_slots_filled(collected_slots, required_slots)):
            for round_index in range(2, rounds_limit + 1):
                user_action = await self.user_agent.respond_async(
                    scenario=scenario,
                    transcript=transcript,
                    round_index=round_index,
                )
                transcript.append(
                    DialogueTurn(
                        speaker=USER_SPEAKER,
                        text=user_action["reply"],
                        round_index=round_index,
                    )
                )
                if self.show_dialogue_progress:
                    await self._print_turn_async(USER_SPEAKER, round_index, user_action["reply"])

                service_action = self.service_agent.respond(
                    scenario=scenario,
                    transcript=transcript,
                    collected_slots=collected_slots,
                    runtime_state=runtime_state,
                )
                self._merge_slots(collected_slots, service_action["slot_updates"], required_slots)
                self._merge_slots(
                    collected_slots,
                    service_action["slot_updates"],
                    ["phone_contactable", "phone_contact_owner", "phone_collection_attempts", "product_arrived"],
                )
                transcript.append(
                    DialogueTurn(
                        speaker=SERVICE_SPEAKER,
                        text=service_action["reply"],
                        round_index=round_index,
                    )
                )
                if self.show_dialogue_progress and service_action["reply"]:
                    await self._print_turn_async(
                        SERVICE_SPEAKER,
                        round_index,
                        service_action["reply"],
                    )

                ready_to_close = service_action["is_ready_to_close"]
                if ready_to_close and self._all_required_slots_filled(collected_slots, required_slots):
                    break

        missing_slots = [
            slot for slot in required_slots if not collected_slots.get(slot, "").strip()
        ]
        status = "completed" if ready_to_close and not missing_slots else "incomplete"

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
        if self.show_dialogue_progress:
            await self._print_dialogue_footer_async(sample)
        return sample

    async def generate_dialogues_async(
        self,
        scenarios: list[Scenario],
        concurrency: int,
    ) -> list[DialogueSample]:
        semaphore = asyncio.Semaphore(max(1, concurrency))

        async def run_single(scenario: Scenario) -> DialogueSample:
            async with semaphore:
                return await self.generate_dialogue_async(scenario)

        return list(await asyncio.gather(*(run_single(scenario) for scenario in scenarios)))

    @staticmethod
    def _merge_slots(
        collected_slots: dict[str, str],
        slot_updates: dict[str, str],
        required_slots: list[str],
    ) -> None:
        for slot, value in slot_updates.items():
            if slot in required_slots and value.strip():
                collected_slots[slot] = value.strip()

    @staticmethod
    def _all_required_slots_filled(
        collected_slots: dict[str, str],
        required_slots: list[str],
    ) -> bool:
        return all(collected_slots.get(slot, "").strip() for slot in required_slots)

    @staticmethod
    def _print_dialogue_header(scenario: Scenario, show_persona_profile: bool = False) -> None:
        print(f"\n=== Scenario: {scenario.scenario_id} ===")
        print(
            f"Product: {scenario.product.brand} {scenario.product.category} {scenario.product.model}"
        )
        print(f"Request Type: {scenario.request.request_type}")
        print(f"Call Start Time: {scenario.call_start_time or 'N/A'}")
        if show_persona_profile:
            print(f"Persona: {scenario.customer.persona or 'N/A'}")
            print(f"Speech Style: {scenario.customer.speech_style or 'N/A'}")

    @staticmethod
    def _print_turn(speaker: str, round_index: int, text: str) -> None:
        print(f"[{round_index}] {display_speaker(speaker)}: {text}")

    @staticmethod
    def _print_dialogue_footer(sample: DialogueSample) -> None:
        print(f"Status: {sample.status}")
        print(f"Collected Slots: {sample.collected_slots}")
        if sample.missing_slots:
            print(f"Missing Slots: {sample.missing_slots}")
        print("=== End Scenario ===")

    async def _print_dialogue_header_async(self, scenario: Scenario) -> None:
        async with self._print_lock:
            self._print_dialogue_header(scenario, show_persona_profile=self.show_persona_profile)

    async def _print_turn_async(self, speaker: str, round_index: int, text: str) -> None:
        async with self._print_lock:
            self._print_turn(speaker, round_index, text)

    async def _print_dialogue_footer_async(self, sample: DialogueSample) -> None:
        async with self._print_lock:
            self._print_dialogue_footer(sample)
