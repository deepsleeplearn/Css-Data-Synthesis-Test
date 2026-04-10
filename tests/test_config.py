from __future__ import annotations

import os
import unittest
from unittest.mock import patch

import multi_agent_data_synthesis.config as config_module
from multi_agent_data_synthesis.config import load_config


class ConfigTests(unittest.TestCase):
    def test_load_config_prefers_explicit_env_values(self):
        with patch.object(config_module, "load_dotenv", return_value=True):
            with patch.dict(
                os.environ,
                {
                    "OPENAI_MODEL": "gpt-4o",
                    "OPENAI_BASE_URL": "https://example.com/v1/chat/completions",
                    "OPENAI_API_KEY": "env-api-key",
                    "OPENAI_USER": "env-user",
                    "USER_AGENT_MODEL": "user-model",
                    "SERVICE_AGENT_MODEL": "service-model",
                    "SECOND_ROUND_INCLUDE_ISSUE_PROBABILITY": "0.9",
                    "ADDRESS_SEGMENTED_REPLY_PROBABILITY": "0.8",
                    "ADDRESS_SEGMENT_ROUNDS_WEIGHTS": '{"2": 0.1, "3": 0.9, "4": 0.0}',
                    "ADDRESS_SEGMENT_MERGE_STRATEGY_WEIGHTS": '{"province_city_district__locality__detail": 1.0}',
                    "ADDRESS_KNOWN_MISMATCH_REWRITE_END_LEVEL_WEIGHTS": '{"building": 0.3, "room": 0.7}',
                    "USER_REPLY_OFF_TOPIC_TARGET_WEIGHTS": '{"address_collection": 0.6, "surname_collection": 0.4}',
                    "USER_REPLY_OFF_TOPIC_ROUNDS_WEIGHTS": '{"1": 0.7, "2": 0.3}',
                    "MAX_CONCURRENCY": "3",
                },
                clear=False,
            ):
                config = load_config()

        self.assertEqual(config.openai_base_url, "https://example.com/v1/chat/completions")
        self.assertEqual(config.openai_api_key, "env-api-key")
        self.assertEqual(config.user, "env-user")
        self.assertEqual(config.user_agent_model, "user-model")
        self.assertEqual(config.service_agent_model, "service-model")
        self.assertEqual(config.second_round_include_issue_probability, 0.9)
        self.assertEqual(config.address_segmented_reply_probability, 0.8)
        self.assertEqual(config.address_segment_rounds_weights["3"], 0.9)
        self.assertEqual(
            config.address_segment_strategy_weights["province_city_district__locality__detail"],
            1.0,
        )
        self.assertEqual(config.address_known_mismatch_rewrite_end_level_weights["room"], 0.7)
        self.assertEqual(config.user_reply_off_topic_target_weights["address_collection"], 0.6)
        self.assertEqual(config.user_reply_off_topic_rounds_weights["2"], 0.3)
        self.assertEqual(config.max_concurrency, 3)

    def test_load_config_allows_custom_model_when_env_is_complete(self):
        with patch.object(config_module, "load_dotenv", return_value=True):
            with patch.dict(
                os.environ,
                {
                    "OPENAI_MODEL": "custom-model",
                    "OPENAI_BASE_URL": "https://example.com/custom",
                    "OPENAI_API_KEY": "custom-key",
                    "OPENAI_USER": "custom-user",
                },
                clear=False,
            ):
                config = load_config()

        self.assertEqual(config.default_model, "custom-model")
        self.assertEqual(config.openai_base_url, "https://example.com/custom")
        self.assertEqual(config.openai_api_key, "custom-key")
        self.assertEqual(config.user, "custom-user")

    def test_load_config_refreshes_request_settings_from_dotenv_file(self):
        def fake_load_dotenv(path, override=False):
            self.assertEqual(path, config_module.ENV_PATH)
            self.assertTrue(override)
            os.environ["OPENAI_MODEL"] = "dotenv-model"
            os.environ["OPENAI_BASE_URL"] = "https://example.com/from-dotenv"
            os.environ["OPENAI_API_KEY"] = "dotenv-api-key"
            os.environ["OPENAI_USER"] = "dotenv-user"
            os.environ["USER_AGENT_MODEL"] = "dotenv-user-model"
            os.environ["SERVICE_AGENT_MODEL"] = "dotenv-service-model"
            return True

        with patch.dict(
            os.environ,
            {
                "OPENAI_MODEL": "env-model",
                "OPENAI_BASE_URL": "https://example.com/from-env",
                "OPENAI_API_KEY": "env-api-key",
                "OPENAI_USER": "env-user",
                "USER_AGENT_MODEL": "env-user-model",
                "SERVICE_AGENT_MODEL": "env-service-model",
            },
            clear=False,
        ):
            with patch.object(config_module, "load_dotenv", side_effect=fake_load_dotenv):
                config = load_config()

        self.assertEqual(config.default_model, "dotenv-model")
        self.assertEqual(config.openai_base_url, "https://example.com/from-dotenv")
        self.assertEqual(config.openai_api_key, "dotenv-api-key")
        self.assertEqual(config.user, "dotenv-user")
        self.assertEqual(config.user_agent_model, "dotenv-user-model")
        self.assertEqual(config.service_agent_model, "dotenv-service-model")


if __name__ == "__main__":
    unittest.main(verbosity=2)
