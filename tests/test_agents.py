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
