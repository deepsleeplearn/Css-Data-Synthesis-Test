from __future__ import annotations

import unittest

from multi_agent_data_synthesis.agents import ServiceAgent, UserAgent
from multi_agent_data_synthesis.schemas import DialogueTurn, Scenario
from multi_agent_data_synthesis.service_policy import ServiceRuntimeState


def build_scenario() -> Scenario:
    return Scenario.from_dict(
        {
            "scenario_id": "agent_case_001",
            "product": {
                "brand": "美的",
                "category": "空气能热水器",
                "model": "KF-01",
                "purchase_channel": "京东",
            },
            "customer": {
                "full_name": "张三",
                "surname": "张",
                "phone": "13800000001",
                "address": "上海市浦东新区测试路1号",
                "persona": "普通用户",
                "speech_style": "简洁",
            },
            "request": {
                "request_type": "fault",
                "issue": "启动后显示E4，热水不出来",
                "desired_resolution": "尽快安排维修",
                "availability": "明天下午",
            },
            "required_slots": ["issue_description", "request_type"],
            "max_turns": 12,
        }
    )


class FailingClient:
    def complete_json(self, **kwargs):
        raise AssertionError("LLM should not be called for satisfaction rating.")

    async def complete_json_async(self, **kwargs):
        raise AssertionError("LLM should not be called for satisfaction rating.")


class ReplyClient:
    def __init__(self, reply: str):
        self.reply = reply

    def complete_json(self, **kwargs):
        return {
            "reply": self.reply,
            "call_complete": False,
        }

    async def complete_json_async(self, **kwargs):
        return {
            "reply": self.reply,
            "call_complete": False,
        }


class RecordingAddressClient:
    def __init__(self):
        self.calls: list[dict] = []

    def complete_json(self, **kwargs):
        self.calls.append(kwargs)
        return {
            "address_candidate": "新开镇柴桥村四组25号",
            "granularity": "locality_with_detail",
        }

    async def complete_json_async(self, **kwargs):
        raise AssertionError("Async path is not used in ServiceAgent.")


class RecordingRoutingClient:
    def __init__(self):
        self.calls: list[dict] = []

    def complete_json(self, **kwargs):
        self.calls.append(kwargs)
        user_content = str(kwargs.get("messages", [{}, {}])[-1].get("content", ""))
        if "当前 prompt_key：usage_purpose" in user_content:
            return {
                "prompt_key": "usage_purpose",
                "answer_key": "purpose.water",
            }
        if "当前 prompt_key：capacity_or_hp" in user_content:
            return {
                "prompt_key": "capacity_or_hp",
                "answer_key": "capacity.below_threshold",
            }
        if "当前 prompt_key：purchase_or_property" in user_content:
            return {
                "prompt_key": "purchase_or_property",
                "answer_key": "purchase.property_bundle",
            }
        raise AssertionError("Unexpected model fallback call.")

    async def complete_json_async(self, **kwargs):
        raise AssertionError("Async path is not used in ServiceAgent.")


class RecordingConfirmationClient:
    def __init__(self):
        self.calls: list[dict] = []

    def complete_json(self, **kwargs):
        self.calls.append(kwargs)
        user_content = str(kwargs.get("messages", [{}, {}])[-1].get("content", ""))
        if "当前 prompt_kind：address_confirmation" in user_content:
            if "就按你刚核对那个地址" not in user_content:
                raise AssertionError("Unexpected confirmation user content.")
            return {
                "prompt_kind": "address_confirmation",
                "intent": "yes",
            }
        raise AssertionError("Unexpected model fallback call.")

    async def complete_json_async(self, **kwargs):
        raise AssertionError("Async path is not used in ServiceAgent.")


class RecordingOpeningClient:
    def __init__(self):
        self.calls: list[dict] = []

    def complete_json(self, **kwargs):
        self.calls.append(kwargs)
        user_content = str(kwargs.get("messages", [{}, {}])[-1].get("content", ""))
        if "[1]用户: 可不么" not in user_content:
            raise AssertionError("Unexpected opening user content.")
        return {"intent": "yes"}

    async def complete_json_async(self, **kwargs):
        raise AssertionError("Async path is not used in ServiceAgent.")


class UserAgentTests(unittest.IsolatedAsyncioTestCase):
    def test_respond_forces_numeric_satisfaction_rating(self):
        agent = UserAgent(
            FailingClient(),
            model="qwen3-32b",
            temperature=0.7,
            second_round_include_issue_probability=0.5,
        )

        result = agent.respond(
            scenario=build_scenario(),
            transcript=[
                DialogueTurn(
                    speaker="service",
                    text="还需要麻烦您对本次通话服务打分，1、非常满意，2、较满意，3、一般，4、较不满，5、非常不满",
                    round_index=9,
                )
            ],
            round_index=10,
        )

        self.assertIn(result["reply"], {"1", "2"})
        self.assertTrue(result["call_complete"])

    def test_respond_removes_ellipsis_for_asr_style(self):
        agent = UserAgent(
            ReplyClient("嗯……是我这个号码..."),
            model="qwen3-32b",
            temperature=0.7,
            second_round_include_issue_probability=0.5,
        )

        result = agent.respond(
            scenario=build_scenario(),
            transcript=[
                DialogueTurn(
                    speaker="service",
                    text="请问您当前这个来电号码能联系到您吗？",
                    round_index=5,
                )
            ],
            round_index=6,
        )

        self.assertEqual(result["reply"], "嗯，是我这个号码")

    def test_respond_strips_repeated_issue_detail_during_contactability_prompt(self):
        agent = UserAgent(
            ReplyClient("能联系，就是这个号码，热水器还是忽冷忽热。"),
            model="qwen3-32b",
            temperature=0.7,
            second_round_include_issue_probability=0.5,
        )

        result = agent.respond(
            scenario=build_scenario(),
            transcript=[
                DialogueTurn(
                    speaker="service",
                    text="请问您当前这个来电号码能联系到您吗？",
                    round_index=5,
                )
            ],
            round_index=6,
        )

        self.assertEqual(result["reply"], "能联系，就是这个号码。")

    def test_respond_trims_address_chatter_and_keeps_address_core(self):
        agent = UserAgent(
            ReplyClient("新寺村一组，嗯……我家就在村口那家小卖部旁边，你懂的，红绿灯往南走不多远就到了。"),
            model="qwen3-32b",
            temperature=0.7,
            second_round_include_issue_probability=0.5,
        )

        result = agent.respond(
            scenario=build_scenario(),
            transcript=[
                DialogueTurn(
                    speaker="service",
                    text="好的，请您提供一下详细的地址，具体到门牌号。",
                    round_index=7,
                )
            ],
            round_index=8,
        )

        self.assertEqual(result["reply"], "新寺村一组。")

    def test_respond_keeps_only_one_capacity_dimension(self):
        scenario = build_scenario()
        scenario.hidden_context["product_routing_plan"] = {
            "enabled": True,
            "result": "家用 + 可直接确认机型",
            "trace": ["capacity.below_threshold"],
            "summary": "capacity.below_threshold -> 家用 + 可直接确认机型",
            "steps": [
                {
                    "prompt_key": "capacity_or_hp",
                    "prompt": "请问机器是多少升的，或者多少匹数的呢？",
                    "answer_key": "capacity.below_threshold",
                    "answer_value": "750升以下",
                    "answer_instruction": "自然表达机器容量较小。",
                }
            ],
        }
        agent = UserAgent(
            ReplyClient("750升以下，3匹以下的吧。"),
            model="qwen3-32b",
            temperature=0.7,
            second_round_include_issue_probability=0.5,
        )

        result = agent.respond(
            scenario=scenario,
            transcript=[
                DialogueTurn(
                    speaker="service",
                    text="请问机器是多少升的，或者多少匹数的呢？",
                    round_index=4,
                )
            ],
            round_index=5,
        )

        self.assertIn("750升以下", result["reply"])
        self.assertNotIn("匹", result["reply"])

    async def test_respond_async_forces_numeric_satisfaction_rating(self):
        agent = UserAgent(
            FailingClient(),
            model="qwen3-32b",
            temperature=0.7,
            second_round_include_issue_probability=0.5,
        )

        result = await agent.respond_async(
            scenario=build_scenario(),
            transcript=[
                DialogueTurn(
                    speaker="service",
                    text="温馨提示，产品首次安装免费，但辅材及改造环境等可能涉及收费，具体以安装人员现场勘查为准。 还需要麻烦您对本次通话服务打分，1、非常满意，2、较满意，3、一般，4、较不满，5、非常不满",
                    round_index=9,
                )
            ],
            round_index=10,
        )

        self.assertIn(result["reply"], {"1", "2"})
        self.assertTrue(result["call_complete"])


class ServiceAgentTests(unittest.TestCase):
    def test_service_agent_uses_model_fallback_for_address_correction(self):
        client = RecordingAddressClient()
        agent = ServiceAgent(
            client,
            model="qwen3-32b",
            temperature=0.7,
            ok_prefix_probability=0.0,
        )
        scenario_data = build_scenario().to_dict()
        scenario_data["request"]["request_type"] = "installation"
        scenario_data["customer"]["address"] = "湖南省岳阳市岳阳县新开镇柴桥村四组25号"
        scenario_data["hidden_context"] = {
            "service_known_address": True,
            "service_known_address_value": "湖南省岳阳市岳阳县新开镇滨江花园四组25号",
            "service_known_address_matches_actual": False,
            "product_arrived": "yes",
            "current_call_contactable": True,
            "contact_phone_owner": "本人当前来电",
        }
        scenario = Scenario.from_dict(scenario_data)
        state = ServiceRuntimeState(expected_address_confirmation=True)

        result = agent.respond(
            scenario=scenario,
            transcript=[
                DialogueTurn(
                    speaker="service",
                    text="好的，您的地址是湖南省岳阳市岳阳县新开镇滨江花园四组25号，对吗？",
                    round_index=5,
                ),
                DialogueTurn(
                    speaker="user",
                    text="不对，前面小区说错了，我说的是老家那个地址。",
                    round_index=6,
                ),
            ],
            collected_slots={
                "issue_description": "想约安装。",
                "surname": "陈",
                "phone": "13800138001",
                "address": "",
                "product_model": "",
                "request_type": "installation",
                "phone_contactable": "yes",
                "phone_contact_owner": "本人当前来电",
                "phone_collection_attempts": "0",
                "product_arrived": "yes",
            },
            runtime_state=state,
        )

        self.assertEqual(len(client.calls), 1)
        self.assertEqual(
            result["reply"],
            "跟您确认一下，地址是湖南省岳阳市岳阳县新开镇柴桥村四组25号，对吗？",
        )

    def test_service_agent_prefers_rule_before_product_routing_model_fallback(self):
        client = RecordingRoutingClient()
        agent = ServiceAgent(
            client,
            model="qwen3-32b",
            temperature=0.7,
            ok_prefix_probability=0.0,
        )
        scenario = build_scenario()
        scenario.hidden_context = {
            "current_call_contactable": True,
            "contact_phone_owner": "本人当前来电",
            "contact_phone": "13800000001",
            "product_routing_plan": {
                "enabled": True,
                "result": "家用 + 可直接确认机型",
                "trace": ["purchase.self_buy"],
                "summary": "purchase.self_buy -> 家用 + 可直接确认机型",
                "steps": [
                    {
                        "prompt_key": "purchase_or_property",
                        "prompt": "请问是您自己购买的，还是楼盘配套赠送的呢？",
                        "answer_key": "purchase.self_buy",
                        "answer_value": "自己购买",
                        "answer_instruction": "自然表达机器是自己购买的。",
                    }
                ],
            },
        }
        state = ServiceRuntimeState(
            expected_product_routing_response=True,
            product_routing_step_index=0,
            product_routing_observed_trace=["entry.unknown", "purpose.unknown", "scene.yes"],
        )

        result = agent.respond(
            scenario=scenario,
            transcript=[
                DialogueTurn(
                    speaker="service",
                    text="请问是您自己购买的，还是楼盘配套赠送的呢？",
                    round_index=5,
                ),
                DialogueTurn(
                    speaker="user",
                    text="房子交付时候就有",
                    round_index=6,
                ),
            ],
            collected_slots={
                "issue_description": "",
                "request_type": "",
            },
            runtime_state=state,
        )

        self.assertEqual(result["reply"], "请问是21年之前的楼盘，还是之后的呢？")
        self.assertEqual(len(client.calls), 0)

    def test_service_agent_uses_model_fallback_for_usage_purpose_when_rule_cannot_match(self):
        client = RecordingRoutingClient()
        agent = ServiceAgent(
            client,
            model="qwen3-32b",
            temperature=0.7,
            ok_prefix_probability=0.0,
        )
        scenario = build_scenario()
        scenario.hidden_context = {
            "current_call_contactable": True,
            "contact_phone_owner": "本人当前来电",
            "contact_phone": "13800000001",
            "product_routing_plan": {
                "enabled": True,
                "result": "家用 + 可直接确认机型",
                "trace": ["purpose.unknown"],
                "summary": "purpose.unknown -> 家用 + 可直接确认机型",
                "steps": [
                    {
                        "prompt_key": "usage_purpose",
                        "prompt": "请问是生活用水加采暖使用，还是单独生活用水，或者单独采暖的呢？",
                        "answer_key": "purpose.unknown",
                        "answer_value": "不清楚用途",
                        "answer_instruction": "自然表达自己不清楚机器用途。",
                    }
                ],
            },
        }
        state = ServiceRuntimeState(
            expected_product_routing_response=True,
            product_routing_step_index=0,
            product_routing_observed_trace=["entry.unknown"],
        )

        result = agent.respond(
            scenario=scenario,
            transcript=[
                DialogueTurn(
                    speaker="service",
                    text="请问是生活用水加采暖使用，还是单独生活用水，或者单独采暖的呢？",
                    round_index=4,
                ),
                DialogueTurn(
                    speaker="user",
                    text="平时就那个日常用的",
                    round_index=5,
                ),
            ],
            collected_slots={
                "issue_description": "",
                "request_type": "",
            },
            runtime_state=state,
        )

        self.assertEqual(result["reply"], "请问机器是多少升的，或者多少匹数的呢？")
        self.assertTrue(result["used_model_intent_inference"])
        self.assertEqual(len(client.calls), 1)

    def test_service_agent_maps_cross_threshold_capacity_range_to_unknown_without_model_fallback(self):
        client = RecordingRoutingClient()
        agent = ServiceAgent(
            client,
            model="qwen3-32b",
            temperature=0.7,
            ok_prefix_probability=0.0,
        )
        scenario = build_scenario()
        scenario.hidden_context = {
            "current_call_contactable": True,
            "contact_phone_owner": "本人当前来电",
            "contact_phone": "13800000001",
            "product_routing_plan": {
                "enabled": True,
                "result": "家用 + 可直接确认机型",
                "trace": ["capacity.unknown"],
                "summary": "capacity.unknown -> 家用 + 可直接确认机型",
                "steps": [
                    {
                        "prompt_key": "capacity_or_hp",
                        "prompt": "请问机器是多少升的，或者多少匹数的呢？",
                        "answer_key": "capacity.unknown",
                        "answer_value": "不清楚容量或匹数",
                        "answer_instruction": "自然表达自己不清楚容量或匹数。",
                    }
                ],
            },
        }
        state = ServiceRuntimeState(
            expected_product_routing_response=True,
            product_routing_step_index=0,
            product_routing_observed_trace=["entry.unknown", "purpose.water"],
        )

        result = agent.respond(
            scenario=scenario,
            transcript=[
                DialogueTurn(
                    speaker="service",
                    text="请问机器是多少升的，或者多少匹数的呢？",
                    round_index=5,
                ),
                DialogueTurn(
                    speaker="user",
                    text="七八百升吧",
                    round_index=6,
                ),
            ],
            collected_slots={
                "issue_description": "",
                "request_type": "",
            },
            runtime_state=state,
        )

        self.assertEqual(result["reply"], "请问是在家庭、别墅、公寓或理发店使用的吗？")
        self.assertFalse(result["used_model_intent_inference"])
        self.assertEqual(len(client.calls), 0)

    def test_service_agent_handles_colloquial_capacity_range_without_model_fallback(self):
        client = RecordingRoutingClient()
        agent = ServiceAgent(
            client,
            model="qwen3-32b",
            temperature=0.7,
            ok_prefix_probability=0.0,
        )
        scenario = build_scenario()
        scenario.hidden_context = {
            "current_call_contactable": True,
            "contact_phone_owner": "本人当前来电",
            "contact_phone": "13800000001",
            "product_routing_plan": {
                "enabled": True,
                "result": "家用 + 可直接确认机型",
                "trace": ["capacity.unknown"],
                "summary": "capacity.unknown -> 家用 + 可直接确认机型",
                "steps": [
                    {
                        "prompt_key": "capacity_or_hp",
                        "prompt": "请问机器是多少升的，或者多少匹数的呢？",
                        "answer_key": "capacity.unknown",
                        "answer_value": "不清楚容量或匹数",
                        "answer_instruction": "自然表达自己不清楚容量或匹数。",
                    }
                ],
            },
        }
        state = ServiceRuntimeState(
            expected_product_routing_response=True,
            product_routing_step_index=0,
            product_routing_observed_trace=["entry.unknown", "purpose.water"],
        )

        result = agent.respond(
            scenario=scenario,
            transcript=[
                DialogueTurn(
                    speaker="service",
                    text="请问机器是多少升的，或者多少匹数的呢？",
                    round_index=5,
                ),
                DialogueTurn(
                    speaker="user",
                    text="五六百升吧好像",
                    round_index=6,
                ),
            ],
            collected_slots={
                "issue_description": "",
                "request_type": "",
            },
            runtime_state=state,
        )

        self.assertEqual(result["reply"], "请问是您自己购买的，还是楼盘配套赠送的呢？")
        self.assertFalse(result["used_model_intent_inference"])
        self.assertEqual(len(client.calls), 0)

    def test_product_routing_model_prompt_contains_property_bundle_disambiguation(self):
        client = RecordingRoutingClient()
        agent = ServiceAgent(
            client,
            model="qwen3-32b",
            temperature=0.7,
            ok_prefix_probability=0.0,
        )

        agent._infer_product_routing_intent_with_model(
            prompt_key="purchase_or_property",
            user_text="当时好像房子自己就有",
            user_round_index=6,
        )

        system_prompt = str(client.calls[0]["messages"][0]["content"])
        self.assertIn("房子自己就有", system_prompt)
        self.assertIn("purchase.property_bundle", system_prompt)

    def test_product_routing_model_prompt_contains_capacity_disambiguation(self):
        client = RecordingRoutingClient()
        agent = ServiceAgent(
            client,
            model="qwen3-32b",
            temperature=0.7,
            ok_prefix_probability=0.0,
        )

        agent._infer_product_routing_intent_with_model(
            prompt_key="capacity_or_hp",
            user_text="七八百升吧",
            user_round_index=6,
        )

        system_prompt = str(client.calls[0]["messages"][0]["content"])
        self.assertIn("五六百升", system_prompt)
        self.assertIn("七八百升", system_prompt)
        self.assertIn("answer_key 必须属于当前 prompt_key", system_prompt)
        self.assertIn("三四匹", system_prompt)

    def test_service_agent_uses_model_fallback_for_opening_intent(self):
        client = RecordingOpeningClient()
        agent = ServiceAgent(
            client,
            model="qwen3-32b",
            temperature=0.7,
            ok_prefix_probability=0.0,
        )
        scenario = build_scenario()
        state = ServiceRuntimeState()

        result = agent.respond(
            scenario=scenario,
            transcript=[
                DialogueTurn(
                    speaker="service",
                    text="您好，很高兴为您服务，请问是美的空气能热水器需要维修吗？",
                    round_index=1,
                ),
                DialogueTurn(
                    speaker="user",
                    text="可不么",
                    round_index=1,
                ),
            ],
            collected_slots={
                "issue_description": "",
                "request_type": "",
            },
            runtime_state=state,
        )

        self.assertEqual(result["reply"], "请问您的空气能是什么具体品牌或系列呢？")
        self.assertTrue(result["used_model_intent_inference"])
        self.assertEqual(len(client.calls), 1)

    def test_service_agent_uses_model_fallback_for_confirmation_intent(self):
        client = RecordingConfirmationClient()
        agent = ServiceAgent(
            client,
            model="qwen3-32b",
            temperature=0.7,
            ok_prefix_probability=0.0,
        )
        scenario = build_scenario()
        scenario_data = scenario.to_dict()
        scenario_data["request"]["request_type"] = "installation"
        scenario = Scenario.from_dict(scenario_data)
        state = ServiceRuntimeState(
            expected_address_confirmation=True,
            pending_address_confirmation="上海市浦东新区测试路1号",
        )

        result = agent.respond(
            scenario=scenario,
            transcript=[
                DialogueTurn(
                    speaker="service",
                    text="跟您确认一下，地址是上海市浦东新区测试路1号，对吗？",
                    round_index=5,
                ),
                DialogueTurn(
                    speaker="user",
                    text="就按你刚核对那个地址",
                    round_index=6,
                ),
            ],
            collected_slots={
                "issue_description": "想约安装。",
                "surname": "张",
                "phone": "13800000001",
                "address": "",
                "product_model": "",
                "request_type": "installation",
                "phone_contactable": "yes",
                "phone_contact_owner": "本人当前来电",
                "phone_collection_attempts": "0",
                "product_arrived": "yes",
            },
            runtime_state=state,
        )

        self.assertEqual(result["slot_updates"]["address"], "上海市浦东新区测试路1号")
        self.assertEqual(len(client.calls), 1)
