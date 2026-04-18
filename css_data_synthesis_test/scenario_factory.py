from __future__ import annotations

import json
import random
from pathlib import Path

from css_data_synthesis_test.schemas import Scenario


class ScenarioFactory:
    def __init__(
        self,
        installation_request_probability: float = 0.5,
        rng: random.Random | None = None,
    ):
        self.installation_request_probability = max(0.0, min(1.0, installation_request_probability))
        self.rng = rng or random.Random()

    def load_from_file(self, path: Path) -> list[Scenario]:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, list):
            raise ValueError("Scenario file must contain a JSON array.")
        scenarios = [self._hydrate_call_start_time(Scenario.from_dict(item)) for item in raw]
        if not scenarios:
            raise ValueError("Scenario file is empty.")
        return scenarios

    def expand_to_count(self, scenarios: list[Scenario], count: int | None) -> list[Scenario]:
        if count is None or count <= len(scenarios):
            selected = scenarios if count is None else scenarios[:count]
            return [self._hydrate_call_start_time(scenario) for scenario in selected]

        faults = [scenario for scenario in scenarios if scenario.request.request_type == "fault"]
        installations = [scenario for scenario in scenarios if scenario.request.request_type == "installation"]
        if faults and installations:
            return self._expand_with_request_type_sampling(
                faults=faults,
                installations=installations,
                count=count,
            )

        expanded: list[Scenario] = []
        for index in range(count):
            base = scenarios[index % len(scenarios)]
            cloned = base.clone_with_id(f"{base.scenario_id}_sample_{index + 1:04d}")
            expanded.append(self._hydrate_call_start_time(cloned))
        return expanded

    def _expand_with_request_type_sampling(
        self,
        *,
        faults: list[Scenario],
        installations: list[Scenario],
        count: int,
    ) -> list[Scenario]:
        expanded: list[Scenario] = []
        fault_index = 0
        installation_index = 0

        for index in range(count):
            pick_installation = self.rng.random() < self.installation_request_probability
            if pick_installation:
                base = installations[installation_index % len(installations)]
                installation_index += 1
            else:
                base = faults[fault_index % len(faults)]
                fault_index += 1
            cloned = base.clone_with_id(f"{base.scenario_id}_sample_{index + 1:04d}")
            expanded.append(self._hydrate_call_start_time(cloned))

        return expanded

    def _hydrate_call_start_time(self, scenario: Scenario) -> Scenario:
        if scenario.call_start_time:
            return scenario
        return scenario.with_call_start_time(self._generate_call_start_time())

    def _generate_call_start_time(self) -> str:
        seconds = self.rng.randint(0, 86399)
        hour, remainder = divmod(seconds, 3600)
        minute, second = divmod(remainder, 60)
        return f"{hour:02d}:{minute:02d}:{second:02d}"
