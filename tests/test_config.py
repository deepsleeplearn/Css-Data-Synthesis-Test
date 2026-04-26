from __future__ import annotations

import os
import unittest
from unittest.mock import patch

import css_data_synthesis_test.config as config_module
from css_data_synthesis_test.config import load_config


class ConfigTests(unittest.TestCase):
    def test_load_config_prefers_explicit_env_values(self):
        with patch.object(config_module, "load_dotenv", return_value=True):
            with patch.dict(
                os.environ,
                {
                    "OPENAI_DEFAULT_MODEL": "gpt-4o",
                    "OPENAI_GPT_4O_MODEL": "gpt-4o",
                    "OPENAI_GPT_4O_BASE_URL": "https://example.com/v1/chat/completions",
                    "OPENAI_GPT_4O_API_KEY": "env-api-key",
                    "OPENAI_GPT_4O_USER": "env-user",
                    "OPENAI_QWEN3_32B_MODEL": "qwen3-32b",
                    "OPENAI_QWEN3_32B_BASE_URL": "https://example.com/qwen",
                    "OPENAI_QWEN3_32B_API_KEY": "qwen-key",
                    "OPENAI_QWEN3_32B_USER": "qwen-user",
                    "USER_AGENT_MODEL": "user-model",
                    "SERVICE_AGENT_MODEL": "service-model",
                    "PRODUCT_ROUTING_ENABLED": "false",
                    "PRODUCT_ROUTING_APPLY_PROBABILITY": "0.25",
                    "AUTO_MODE_IVR_PRODUCT_KIND_WEIGHTS": '{"air_energy": 0.2, "water_heater": 0.8}',
                    "AUTO_MODE_WATER_HEATER_OPENING_REPLY_WEIGHTS": '{"confirm": 0.1, "change_request": 0.9}',
                    "AUTO_MODE_HISTORY_DEVICE_PROBABILITY": "0.75",
                    "AUTO_MODE_HISTORY_DEVICE_BRAND_WEIGHTS": '{"美的": 0.6, "烈焰": 0.4}',
                    "AUTO_MODE_HISTORY_DEVICE_CATEGORY_WEIGHTS": '{"家用空气能热水机": 0.2, "空气能热水机": 0.8}',
                    "SECOND_ROUND_INCLUDE_ISSUE_PROBABILITY": "0.9",
                    "SERVICE_QUERY_PREFIX_WEIGHTS": '{"好的": 0.2, "嗯嗯": 0.3, "了解了": 0.4, "": 0.1}',
                    "ADDRESS_SEGMENTED_REPLY_PROBABILITY": "0.8",
                    "ADDRESS_SEGMENT_ROUNDS_WEIGHTS": '{"2": 0.1, "3": 0.9, "4": 0.0}',
                    "ADDRESS_SEGMENT_3_STRATEGY_WEIGHTS": '{"province_city_district__locality__detail": 1.0}',
                    "ADDRESS_SEGMENT_2_STRATEGY_WEIGHTS": '{"province_city_district_locality__detail": 0.7, "province_city_district__locality_detail": 0.3}',
                    "ADDRESS_SEGMENT_4_STRATEGY_WEIGHTS": '{"province_city__district__locality__detail": 1.0}',
                    "ADDRESS_SEGMENT_5_STRATEGY_WEIGHTS": '{"province__city__district__locality__detail": 1.0}',
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
        self.assertEqual(config.model_endpoints["qwen3-32b"]["base_url"], "https://example.com/qwen")
        self.assertEqual(config.model_endpoints["qwen3-32b"]["api_key"], "qwen-key")
        self.assertEqual(config.user_agent_model, "user-model")
        self.assertEqual(config.service_agent_model, "service-model")
        self.assertFalse(config.product_routing_enabled)
        self.assertEqual(config.product_routing_apply_probability, 0.25)
        self.assertEqual(config.auto_mode_ivr_product_kind_weights["water_heater"], 0.8)
        self.assertEqual(config.auto_mode_water_heater_opening_reply_weights["change_request"], 0.9)
        self.assertEqual(config.auto_mode_history_device_probability, 0.75)
        self.assertEqual(config.auto_mode_history_device_brand_weights["烈焰"], 0.4)
        self.assertEqual(config.auto_mode_history_device_category_weights["空气能热水机"], 0.8)
        self.assertEqual(config.second_round_include_issue_probability, 0.9)
        self.assertEqual(config.service_query_prefix_weights["嗯嗯"], 0.3)
        self.assertEqual(config.service_query_prefix_weights[""], 0.1)
        self.assertEqual(config.address_segmented_reply_probability, 0.8)
        self.assertEqual(config.address_segment_rounds_weights["3"], 0.9)
        self.assertEqual(
            config.address_segment_3_strategy_weights["province_city_district__locality__detail"],
            1.0,
        )
        self.assertEqual(
            config.address_segment_2_strategy_weights["province_city_district_locality__detail"],
            0.7,
        )
        self.assertEqual(
            config.address_segment_4_strategy_weights["province_city__district__locality__detail"],
            1.0,
        )
        self.assertEqual(
            config.address_segment_5_strategy_weights["province__city__district__locality__detail"],
            1.0,
        )
        self.assertEqual(config.address_known_mismatch_rewrite_end_level_weights["room"], 0.7)
        self.assertEqual(config.user_reply_off_topic_target_weights["address_collection"], 0.6)
        self.assertEqual(config.user_reply_off_topic_rounds_weights["2"], 0.3)
        self.assertEqual(config.max_concurrency, 3)

    def test_load_config_keeps_legacy_segment_strategy_env_as_fallback(self):
        with patch.object(config_module, "load_dotenv", return_value=True):
            with patch.dict(
                os.environ,
                {
                    "OPENAI_DEFAULT_MODEL": "gpt-4o",
                    "OPENAI_GPT_4O_MODEL": "gpt-4o",
                    "OPENAI_GPT_4O_BASE_URL": "https://example.com/v1/chat/completions",
                    "OPENAI_GPT_4O_API_KEY": "env-api-key",
                    "ADDRESS_SEGMENT_MERGE_STRATEGY_WEIGHTS": '{"province_city_district__locality__detail": 0.9, "province_city_district__locality_detail": 0.8, "province_city__district__locality__detail": 0.7}',
                    "ADDRESS_SEGMENT_2_STRATEGY_WEIGHTS": "",
                    "ADDRESS_SEGMENT_3_STRATEGY_WEIGHTS": "",
                    "ADDRESS_SEGMENT_4_STRATEGY_WEIGHTS": "",
                    "ADDRESS_SEGMENT_5_STRATEGY_WEIGHTS": "",
                },
                clear=False,
            ):
                config = load_config()

        self.assertEqual(
            config.address_segment_3_strategy_weights["province_city_district__locality__detail"],
            1.0,
        )
        self.assertEqual(
            config.address_segment_2_strategy_weights["province_city_district__locality_detail"],
            1.0,
        )
        self.assertEqual(
            config.address_segment_4_strategy_weights["province_city__district__locality__detail"],
            1.0,
        )

    def test_load_config_rejects_segment_strategy_distribution_that_does_not_sum_to_one(self):
        with patch.object(config_module, "load_dotenv", return_value=True):
            with patch.dict(
                os.environ,
                {
                    "OPENAI_DEFAULT_MODEL": "gpt-4o",
                    "OPENAI_GPT_4O_MODEL": "gpt-4o",
                    "OPENAI_GPT_4O_BASE_URL": "https://example.com/v1/chat/completions",
                    "OPENAI_GPT_4O_API_KEY": "env-api-key",
                    "ADDRESS_SEGMENT_2_STRATEGY_WEIGHTS": '{"province_city_district_locality__detail": 0.7, "province_city_district__locality_detail": 0.4}',
                },
                clear=False,
            ):
                with self.assertRaisesRegex(ValueError, "ADDRESS_SEGMENT_2_STRATEGY_WEIGHTS must sum to 1.0"):
                    load_config()

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
                clear=True,
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
            os.environ.pop("OPENAI_DEFAULT_MODEL", None)
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
            clear=True,
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
