from __future__ import annotations

import json
from typing import Any

import httpx

from css_data_synthesis_test.config import AppConfig, load_model_request_profiles


def extract_json_object(text: str) -> dict[str, Any]:
    text = (text or "").strip()
    if not text:
        raise ValueError("Model returned empty content.")

    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError(f"Could not locate JSON object in: {text}")

    parsed = json.loads(text[start : end + 1])
    if not isinstance(parsed, dict):
        raise ValueError("Parsed JSON is not an object.")
    return parsed


class OpenAIChatClient:
    def __init__(self, config: AppConfig):
        self.config = config

    @staticmethod
    def _is_qwen_family_model(model: str) -> bool:
        return model.strip().lower().startswith("qwen")

    @staticmethod
    def _requires_qwen_model_path(model: str) -> bool:
        return model.strip().lower().startswith("qwen3-")

    @staticmethod
    def _summarize_response_body(response: httpx.Response, *, limit: int = 300) -> str:
        body = response.text.strip()
        if not body:
            return "<empty body>"
        compact = " ".join(body.split())
        if len(compact) <= limit:
            return compact
        return f"{compact[:limit]}..."

    def _build_headers(self, model: str) -> dict[str, str]:
        endpoint = self._endpoint_for_model(model)
        headers = {
            "Aimp-Biz-Id": model,
            "Authorization": f"Bearer {endpoint['api_key']}",
            "Content-Type": "application/json",
        }
        if endpoint["user"]:
            headers["AIGC-USER"] = endpoint["user"]
        return headers

    def _endpoint_for_model(self, model: str) -> dict[str, str]:
        endpoint = dict(self.config.model_endpoints.get(model, {}))
        base_url = str(endpoint.get("base_url") or self.config.openai_base_url).strip()
        api_key = str(endpoint.get("api_key") or self.config.openai_api_key).strip()
        user = str(endpoint.get("user") or self.config.user).strip()
        if not base_url:
            raise RuntimeError(f"Missing base URL for model {model}.")
        if not api_key:
            raise RuntimeError(f"Missing API key for model {model}.")
        return {"base_url": base_url, "api_key": api_key, "user": user}

    def _build_payload(
        self,
        *,
        model: str,
        messages: list[dict[str, str]],
        temperature: float | None,
        max_tokens: int | None,
        enable_thinking: bool = False,
        additional_payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        profile = self._request_profile_for_model(model)
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
        }

        resolved_temperature = self.config.default_temperature if temperature is None else temperature
        if profile["include_temperature"] and resolved_temperature is not None:
            payload[str(profile["temperature_param"])] = resolved_temperature

        if profile["include_max_tokens"] and max_tokens is not None:
            payload[str(profile["max_tokens_param"])] = max_tokens

        if profile["include_enable_thinking"] and enable_thinking:
            payload[str(profile["enable_thinking_param"])] = True

        extra_body = profile.get("extra_body", {})
        if isinstance(extra_body, dict):
            payload.update(extra_body)

        if self._is_qwen_family_model(model):
            chat_template_kwargs = payload.get("chat_template_kwargs", {})
            if not isinstance(chat_template_kwargs, dict):
                chat_template_kwargs = {}
            chat_template_kwargs.setdefault("enable_thinking", enable_thinking)
            payload["chat_template_kwargs"] = chat_template_kwargs
            payload.setdefault("stream", False)

            if self._requires_qwen_model_path(model):
                payload["model"] = f"/model/{model}"

        if isinstance(additional_payload, dict):
            payload.update(additional_payload)

        return payload

    @staticmethod
    def _request_profile_for_model(model: str) -> dict[str, Any]:
        profiles = load_model_request_profiles()
        profile: dict[str, Any] = dict(profiles.get("default", {}))
        profile.update(profiles.get(model, {}))
        profile.setdefault("include_temperature", True)
        profile.setdefault("include_max_tokens", True)
        profile.setdefault("temperature_param", "temperature")
        profile.setdefault("max_tokens_param", "max_tokens")
        profile.setdefault("include_enable_thinking", True)
        profile.setdefault("enable_thinking_param", "enable_thinking")
        if model.strip().lower().startswith("qwen"):
            profile["include_enable_thinking"] = False
        return profile

    @classmethod
    def _parse_event_stream_payload(cls, body: str) -> dict[str, Any]:
        events: list[dict[str, Any]] = []
        for raw_line in body.splitlines():
            line = raw_line.strip()
            if not line or not line.startswith("data:"):
                continue
            event_text = line[5:].strip()
            if not event_text or event_text == "[DONE]":
                continue
            try:
                event = json.loads(event_text)
            except json.JSONDecodeError:
                continue
            if isinstance(event, dict):
                events.append(event)

        if not events:
            raise ValueError("No JSON event payloads found in stream response.")

        for event in reversed(events):
            choices = event.get("choices")
            if (
                isinstance(choices, list)
                and choices
                and isinstance(choices[0], dict)
                and isinstance(choices[0].get("message"), dict)
            ):
                return event

        aggregated_choices: dict[int, dict[str, Any]] = {}
        usage: Any = None
        last_event = events[-1]

        for event in events:
            if event.get("usage") is not None:
                usage = event.get("usage")

            choices = event.get("choices")
            if not isinstance(choices, list):
                continue

            for choice in choices:
                if not isinstance(choice, dict):
                    continue
                index = int(choice.get("index", 0))
                aggregate = aggregated_choices.setdefault(
                    index,
                    {
                        "index": index,
                        "message": {
                            "role": "assistant",
                            "content": "",
                            "reasoning_content": None,
                            "tool_calls": None,
                        },
                        "logprobs": None,
                        "finish_reason": None,
                        "matched_stop": None,
                    },
                )

                message = aggregate["message"]
                delta = choice.get("delta")
                if isinstance(delta, dict):
                    role = delta.get("role")
                    if isinstance(role, str) and role:
                        message["role"] = role

                    content = delta.get("content")
                    if isinstance(content, str):
                        message["content"] += content

                    reasoning_content = delta.get("reasoning_content")
                    if isinstance(reasoning_content, str):
                        existing_reasoning = message.get("reasoning_content")
                        if isinstance(existing_reasoning, str):
                            message["reasoning_content"] = existing_reasoning + reasoning_content
                        else:
                            message["reasoning_content"] = reasoning_content

                    tool_calls = delta.get("tool_calls")
                    if tool_calls is not None:
                        message["tool_calls"] = tool_calls

                if choice.get("finish_reason") is not None:
                    aggregate["finish_reason"] = choice.get("finish_reason")
                if choice.get("matched_stop") is not None:
                    aggregate["matched_stop"] = choice.get("matched_stop")
                if choice.get("logprobs") is not None:
                    aggregate["logprobs"] = choice.get("logprobs")

        if not aggregated_choices:
            raise ValueError("No usable choices found in stream response.")

        return {
            "id": last_event.get("id"),
            "object": "chat.completion",
            "created": last_event.get("created"),
            "model": last_event.get("model"),
            "choices": [aggregated_choices[index] for index in sorted(aggregated_choices)],
            "usage": usage,
        }

    @staticmethod
    def _extract_message_content(payload: dict[str, Any]) -> str:
        choices = payload.get("choices")
        if not isinstance(choices, list) or not choices:
            raise ValueError(f"Model response missing choices: {payload}")

        message = choices[0].get("message")
        if not isinstance(message, dict):
            raise ValueError(f"Model response missing message: {payload}")

        content = message.get("content")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            text_parts: list[str] = []
            for item in content:
                if not isinstance(item, dict):
                    continue
                if item.get("type") == "text" and isinstance(item.get("text"), str):
                    text_parts.append(item["text"])
                    continue
                if isinstance(item.get("content"), str):
                    text_parts.append(item["content"])
            return "".join(text_parts).replace(" ", "")
        return ""

    def _send_request(
        self,
        *,
        base_url: str,
        headers: dict[str, str],
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        with httpx.Client(timeout=self.config.request_timeout) as client:
            response = client.post(base_url, json=payload, headers=headers)
        return self._parse_response(response)

    async def _send_request_async(
        self,
        *,
        base_url: str,
        headers: dict[str, str],
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=self.config.request_timeout) as client:
            response = await client.post(base_url, json=payload, headers=headers)
        return self._parse_response(response)

    def _parse_response(self, response: httpx.Response) -> dict[str, Any]:
        if response.status_code >= 400:
            raise RuntimeError(
                f"Model request failed with status {response.status_code}: "
                f"{self._summarize_response_body(response)}"
            )
        content_type = response.headers.get("content-type", "<missing>")
        if "text/event-stream" in content_type.lower():
            try:
                return self._parse_event_stream_payload(response.text)
            except ValueError as exc:
                raise RuntimeError(
                    "Model response event stream could not be parsed: "
                    f"{self._summarize_response_body(response)}"
                ) from exc
        try:
            payload = response.json()
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                "Model response was not valid JSON "
                f"(status {response.status_code}, content-type {content_type}): "
                f"{self._summarize_response_body(response)}"
            ) from exc

        if not isinstance(payload, dict):
            raise RuntimeError(
                "Model response JSON root must be an object, "
                f"got {type(payload).__name__}: {self._summarize_response_body(response)}"
            )
        return payload

    def complete(
        self,
        *,
        model: str,
        messages: list[dict[str, str]],
        temperature: float | None = None,
        max_tokens: int | None = None,
        enable_thinking: bool = False,
        additional_payload: dict[str, Any] | None = None,
    ) -> str:
        payload = self._build_payload(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            enable_thinking=enable_thinking,
            additional_payload=additional_payload,
        )
        endpoint = self._endpoint_for_model(model)
        response = self._send_request(
            base_url=endpoint["base_url"],
            headers=self._build_headers(model),
            payload=payload,
        )
        return self._extract_message_content(response)

    def complete_json(
        self,
        *,
        model: str,
        messages: list[dict[str, str]],
        temperature: float | None = None,
        max_tokens: int | None = None,
        enable_thinking: bool = False,
        additional_payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        text = self.complete(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            enable_thinking=enable_thinking,
            additional_payload=additional_payload,
        )
        try:
            return extract_json_object(text)
        except ValueError:
            retry_messages = messages + [
                {
                    "role": "user",
                    "content": "上一次输出不是合法 JSON。请仅返回一个 JSON 对象，不要附带解释。",
                }
            ]
            retry_text = self.complete(
                model=model,
                messages=retry_messages,
                temperature=temperature,
                max_tokens=max_tokens,
                enable_thinking=enable_thinking,
                additional_payload=additional_payload,
            )
            return extract_json_object(retry_text)

    async def complete_async(
        self,
        *,
        model: str,
        messages: list[dict[str, str]],
        temperature: float | None = None,
        max_tokens: int | None = None,
        enable_thinking: bool = False,
        additional_payload: dict[str, Any] | None = None,
    ) -> str:
        payload = self._build_payload(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            enable_thinking=enable_thinking,
            additional_payload=additional_payload,
        )
        endpoint = self._endpoint_for_model(model)
        response = await self._send_request_async(
            base_url=endpoint["base_url"],
            headers=self._build_headers(model),
            payload=payload,
        )
        return self._extract_message_content(response)

    async def complete_json_async(
        self,
        *,
        model: str,
        messages: list[dict[str, str]],
        temperature: float | None = None,
        max_tokens: int | None = None,
        enable_thinking: bool = False,
        additional_payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        text = await self.complete_async(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            enable_thinking=enable_thinking,
            additional_payload=additional_payload,
        )
        try:
            return extract_json_object(text)
        except ValueError:
            retry_messages = messages + [
                {
                    "role": "user",
                    "content": "上一次输出不是合法 JSON。请仅返回一个 JSON 对象，不要附带解释。",
                }
            ]
            retry_text = await self.complete_async(
                model=model,
                messages=retry_messages,
                temperature=temperature,
                max_tokens=max_tokens,
                enable_thinking=enable_thinking,
                additional_payload=additional_payload,
            )
            return extract_json_object(retry_text)
