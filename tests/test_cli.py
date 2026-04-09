from __future__ import annotations

import io
import unittest
from contextlib import redirect_stdout

from multi_agent_data_synthesis.cli import build_parser
from multi_agent_data_synthesis.orchestrator import DialogueOrchestrator
from tests.test_orchestrator import build_scenario


class CliTests(unittest.TestCase):
    def test_generate_parser_accepts_show_persona_flag(self):
        parser = build_parser()

        args = parser.parse_args(
            [
                "generate",
                "--count",
                "1",
                "--show-dialogue",
                "--show-persona",
            ]
        )

        self.assertTrue(args.show_dialogue)
        self.assertTrue(args.show_persona)

    def test_dialogue_header_can_include_persona_profile(self):
        buffer = io.StringIO()

        with redirect_stdout(buffer):
            DialogueOrchestrator._print_dialogue_header(
                build_scenario(),
                show_persona_profile=True,
            )

        output = buffer.getvalue()
        self.assertIn("Persona: 普通用户", output)
        self.assertIn("Speech Style: 简洁", output)


if __name__ == "__main__":
    unittest.main(verbosity=2)
