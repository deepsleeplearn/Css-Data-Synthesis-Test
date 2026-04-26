from __future__ import annotations

import os
import unittest
from pathlib import Path
from unittest.mock import patch

import httpx

from css_data_synthesis_test.config import AppConfig
from css_data_synthesis_test.llm import OpenAIChatClient


def build_config() -> AppConfig:
    root = Path("/tmp/multi-agent-data-synthesis-tests")
    return AppConfig(
        openai_base_url="https://aimpapi.midea.com/t-aigc/mip-chat-app/openai/standard/v1/chat/completions",
        openai_api_key="test-api-key",
        user="test-user",
        default_model="gpt-4o",
        user_agent_model="gpt-4o",
        service_agent_model="gpt-4o",
        model_endpoints={
            "gpt-4o": {
                "base_url": "https://aimpapi.midea.com/t-aigc/mip-chat-app/openai/standard/v1/chat/completions",
                "api_key": "test-api-key",
                "user": "test-user",
            },
            "qwen3-32b": {
                "base_url": "https://aimpapi.midea.com/t-aigc/aimp-qwen3-32b/v1/chat/completions",
                "api_key": "qwen-api-key",
                "user": "qwen-user",
            },
        },
        default_temperature=0.7,
        service_ok_prefix_probability=0.7,
        service_query_prefix_weights={"好的": 0.7, "嗯嗯": 0.0, "了解了": 0.0, "": 0.3},
        second_round_include_issue_probability=0.5,
        max_rounds=20,
        max_concurrency=5,
        request_timeout=30,
        data_dir=root,
        output_dir=root,
        hidden_settings_store=root / "hidden_settings_history.jsonl",
        utterance_reference_library_path=root / "utterance_reference_library.json",
        utterance_reference_sample_probability=0.9,
        product_routing_enabled=True,
        product_routing_apply_probability=1.0,
        hidden_settings_similarity_threshold=0.82,
        hidden_settings_duplicate_threshold=0.5,
        hidden_settings_max_attempts=3,
        hidden_settings_multi_fault_probability=0.1,
        installation_request_probability=0.5,
        current_call_contactable_probability=0.75,
        phone_collection_second_attempt_probability=0.35,
        phone_collection_third_attempt_probability=0.2,
        phone_collection_invalid_short_probability=0.34,
        phone_collection_invalid_long_probability=0.33,
        phone_collection_invalid_pattern_probability=0.33,
        phone_collection_invalid_digit_mismatch_probability=0.33,
        service_known_address_probability=0.2,
        service_known_address_matches_probability=0.8,
        address_collection_followup_probability=0.35,
        address_segmented_reply_probability=0.35,
        address_segment_rounds_weights={"2": 0.45, "3": 0.35, "4": 0.20},
        address_segment_2_strategy_weights={
            "province_city_district_locality__detail": 0.6,
            "province_city_district__locality_detail": 0.4,
        },
        address_segment_3_strategy_weights={
            "province_city_district__locality__detail": 0.5454545454545454,
            "province_city__district_locality__detail": 0.2727272727272727,
            "province_city__district__locality_detail": 0.18181818181818182,
        },
        address_segment_4_strategy_weights={
            "province_city__district__locality__detail": 1.0,
        },
        address_input_omit_province_city_suffix_probability=0.0,
        address_confirmation_direct_correction_probability=0.5,
        user_reply_off_topic_probability=0.18,
        user_reply_off_topic_target_weights={
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
        },
        user_reply_off_topic_rounds_weights={"1": 0.85, "2": 0.12, "3": 0.03},
        user_address_nonstandard_probability=0.28,
        user_address_nonstandard_style_weights={
            "house_number_only": 0.45,
            "rural_group_number": 0.25,
            "landmark_poi": 0.30,
        },
        address_known_mismatch_start_level_weights={
            "province": 0.05,
            "city": 0.10,
            "district": 0.15,
            "locality": 0.25,
            "building": 0.15,
            "unit": 0.10,
            "floor": 0.05,
            "room": 0.15,
        },
        address_known_mismatch_rewrite_end_level_weights={
            "province": 0.05,
            "city": 0.08,
            "district": 0.10,
            "locality": 0.14,
            "building": 0.16,
            "unit": 0.16,
            "floor": 0.11,
            "room": 0.20,
        },
    )


class RecordingChatClient(OpenAIChatClient):
    def __init__(self, responses: list[dict]):
        super().__init__(build_config())
        self.responses = responses
        self.sent_requests: list[dict] = []

    def _send_request(self, *, base_url: str, headers: dict[str, str], payload: dict[str, object]) -> dict:
        self.sent_requests.append({"base_url": base_url, "headers": headers, "payload": payload})
        if not self.responses:
            raise AssertionError("No prepared sync response available.")
        return self.responses.pop(0)

    async def _send_request_async(self, *, base_url: str, headers: dict[str, str], payload: dict[str, object]) -> dict:
        self.sent_requests.append({"base_url": base_url, "headers": headers, "payload": payload})
        if not self.responses:
            raise AssertionError("No prepared async response available.")
        return self.responses.pop(0)


class OpenAIChatClientTests(unittest.TestCase):
    def test_parse_response_accepts_event_stream_chunks(self):
        client = OpenAIChatClient(build_config())
        response = httpx.Response(
            200,
            text=(
                'data: {"id":"evt-1","object":"chat.completion.chunk","created":1,'
                '"model":"qwen3-32b","choices":[{"index":0,"delta":{"role":"assistant","content":"你"},'
                '"logprobs":null,"finish_reason":null,"matched_stop":null}],"usage":null}\n\n'
                'data: {"id":"evt-1","object":"chat.completion.chunk","created":1,'
                '"model":"qwen3-32b","choices":[{"index":0,"delta":{"content":"好"},'
                '"logprobs":null,"finish_reason":"stop","matched_stop":151645}],"usage":{"prompt_tokens":1,"completion_tokens":2,"total_tokens":3}}\n\n'
                "data: [DONE]\n"
            ),
            headers={"content-type": "text/event-stream; charset=utf-8"},
        )

        payload = client._parse_response(response)

        self.assertEqual(payload["object"], "chat.completion")
        self.assertEqual(payload["choices"][0]["message"]["content"], "你好")
        self.assertEqual(payload["choices"][0]["finish_reason"], "stop")
        self.assertEqual(payload["usage"]["total_tokens"], 3)

    def test_parse_response_raises_clear_error_for_non_json_success_body(self):
        client = OpenAIChatClient(build_config())
        response = httpx.Response(
            200,
            text="",
            headers={"content-type": "text/plain; charset=utf-8"},
        )

        with self.assertRaisesRegex(RuntimeError, "Model response was not valid JSON"):
            client._parse_response(response)

    def test_parse_response_raises_clear_error_for_non_object_json(self):
        client = OpenAIChatClient(build_config())
        response = httpx.Response(
            200,
            json=[{"content": "not-an-object-root"}],
            headers={"content-type": "application/json"},
        )

        with self.assertRaisesRegex(RuntimeError, "JSON root must be an object"):
            client._parse_response(response)

    def test_complete_builds_gpt4o_compatible_aimp_headers_and_payload(self):
        client = RecordingChatClient(
            [
                {
                    "choices": [
                        {
                            "message": {
                                "content": "模型输出",
                            }
                        }
                    ]
                }
            ]
        )

        result = client.complete(
            model="gpt-4o",
            messages=[{"role": "user", "content": "你好"}],
            temperature=0.4,
            max_tokens=256,
            enable_thinking=True,
        )

        self.assertEqual(result, "模型输出")
        self.assertEqual(len(client.sent_requests), 1)
        request = client.sent_requests[0]
        self.assertEqual(request["headers"]["Aimp-Biz-Id"], "gpt-4o")
        self.assertEqual(request["headers"]["AIGC-USER"], "test-user")
        self.assertEqual(request["headers"]["Authorization"], "Bearer test-api-key")
        self.assertEqual(
            request["payload"],
            {
                "model": "gpt-4o",
                "messages": [{"role": "user", "content": "你好"}],
                "temperature": 0.4,
                "max_tokens": 256,
            },
        )

    def test_complete_supports_additional_payload_for_gpt4o(self):
        client = RecordingChatClient(
            [
                {
                    "choices": [
                        {
                            "message": {
                                "content": "模型输出",
                            }
                        }
                    ]
                }
            ]
        )

        client.complete(
            model="gpt-4o",
            messages=[{"role": "user", "content": "你好"}],
            temperature=0.4,
            additional_payload={"top_p": 0.7, "presence_penalty": 0.2},
        )

        request = client.sent_requests[0]
        self.assertEqual(
            request["payload"],
            {
                "model": "gpt-4o",
                "messages": [{"role": "user", "content": "你好"}],
                "temperature": 0.4,
                "top_p": 0.7,
                "presence_penalty": 0.2,
            },
        )

    def test_qwen3_complete_builds_non_stream_payload(self):
        client = RecordingChatClient(
            [
                {
                    "choices": [
                        {
                            "message": {
                                "content": "模型输出",
                            }
                        }
                    ]
                }
            ]
        )

        client.complete(
            model="qwen3-32b",
            messages=[{"role": "user", "content": "你好"}],
            temperature=0.4,
            max_tokens=256,
            enable_thinking=True,
        )

        request = client.sent_requests[0]
        self.assertEqual(
            request["payload"],
            {
                "model": "/model/qwen3-32b",
                "messages": [{"role": "user", "content": "你好"}],
                "temperature": 0.4,
                "max_tokens": 256,
                "chat_template_kwargs": {"enable_thinking": True},
                "stream": False,
            },
        )

    def test_complete_json_retries_after_invalid_json(self):
        client = RecordingChatClient(
            [
                {
                    "choices": [
                        {
                            "message": {
                                "content": "这不是 JSON",
                            }
                        }
                    ]
                },
                {
                    "choices": [
                        {
                            "message": {
                                "content": '{"reply":"已修正","call_complete":false}',
                            }
                        }
                    ]
                },
            ]
        )

        payload = client.complete_json(
            model="gpt-4o",
            messages=[{"role": "user", "content": "返回 JSON"}],
        )

        self.assertEqual(payload["reply"], "已修正")
        self.assertEqual(len(client.sent_requests), 2)
        retry_messages = client.sent_requests[1]["payload"]["messages"]
        self.assertEqual(retry_messages[-1]["role"], "user")
        self.assertIn("请仅返回一个 JSON 对象", retry_messages[-1]["content"])

    def test_complete_supports_list_content(self):
        client = RecordingChatClient(
            [
                {
                    "choices": [
                        {
                            "message": {
                                "content": [
                                    {"type": "text", "text": "第一段"},
                                    {"type": "text", "text": "第二段"},
                                ]
                            }
                        }
                    ]
                }
            ]
        )

        result = client.complete(
            model="gpt-4o",
            messages=[{"role": "user", "content": "你好"}],
        )

        self.assertEqual(result, "第一段第二段")

    def test_gpt_5_3_chat_omits_temperature_and_max_tokens_by_default(self):
        client = RecordingChatClient(
            [
                {
                    "choices": [
                        {
                            "message": {
                                "content": "模型输出",
                            }
                        }
                    ]
                }
            ]
        )

        client.complete(
            model="gpt-5.3-chat",
            messages=[{"role": "user", "content": "你好"}],
            temperature=0.4,
            max_tokens=256,
            enable_thinking=True,
        )

        request = client.sent_requests[0]
        self.assertEqual(
            request["payload"],
            {
                "model": "gpt-5.3-chat",
                "messages": [{"role": "user", "content": "你好"}],
                "enable_thinking": True,
            },
        )

    def test_model_request_profiles_can_override_param_names(self):
        client = RecordingChatClient(
            [
                {
                    "choices": [
                        {
                            "message": {
                                "content": "模型输出",
                            }
                        }
                    ]
                }
            ]
        )

        with patch.dict(
            os.environ,
            {
                "MODEL_REQUEST_PROFILES": (
                    '{"default":{"include_max_tokens":false},'
                    '"custom-model":{"include_temperature":false,'
                    '"include_max_tokens":true,'
                    '"max_tokens_param":"max_completion_tokens",'
                    '"include_enable_thinking":false,'
                    '"extra_body":{"reasoning_effort":"medium"}}}'
                )
            },
            clear=False,
        ):
            client.complete(
                model="custom-model",
                messages=[{"role": "user", "content": "你好"}],
                temperature=0.2,
                max_tokens=128,
                enable_thinking=True,
            )

        request = client.sent_requests[0]
        self.assertEqual(
            request["payload"],
            {
                "model": "custom-model",
                "messages": [{"role": "user", "content": "你好"}],
                "max_completion_tokens": 128,
                "reasoning_effort": "medium",
            },
        )


class OpenAIChatClientAsyncTests(unittest.IsolatedAsyncioTestCase):
    async def test_complete_json_async_retries_after_invalid_json(self):
        client = RecordingChatClient(
            [
                {
                    "choices": [
                        {
                            "message": {
                                "content": "still not json",
                            }
                        }
                    ]
                },
                {
                    "choices": [
                        {
                            "message": {
                                "content": '{"reply":"异步成功","call_complete":true}',
                            }
                        }
                    ]
                },
            ]
        )

        payload = await client.complete_json_async(
            model="gpt-4o",
            messages=[{"role": "user", "content": "异步返回 JSON"}],
        )

        self.assertEqual(payload["reply"], "异步成功")
        self.assertTrue(payload["call_complete"])
        self.assertEqual(len(client.sent_requests), 2)
