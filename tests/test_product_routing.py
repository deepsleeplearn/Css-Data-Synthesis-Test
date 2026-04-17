from __future__ import annotations

import random
import unittest

from multi_agent_data_synthesis.address_utils import extract_address_components
from multi_agent_data_synthesis.agents import ServiceAgent, UserAgent
from multi_agent_data_synthesis.product_routing import (
    PROMPT_BRAND_OR_SERIES,
    PROMPT_USAGE_SCENE,
    PROMPT_USAGE_PURPOSE,
    ROUTING_RESULT_BUILDING,
    ROUTING_RESULT_HOME,
    build_product_routing_plan,
    infer_product_routing_answer_key,
)
from multi_agent_data_synthesis.prompts import build_user_agent_messages
from multi_agent_data_synthesis.schemas import DialogueTurn, Scenario
from multi_agent_data_synthesis.service_policy import ServiceDialoguePolicy, ServiceRuntimeState


def build_scenario_with_routing(plan: dict | None = None) -> Scenario:
    hidden_context = {
        "current_call_contactable": True,
        "contact_phone_owner": "本人当前来电",
        "contact_phone": "13800138001",
    }
    if plan is not None:
        hidden_context["product_routing_plan"] = plan
        hidden_context["product_routing_result"] = plan.get("result", "")
        hidden_context["product_routing_trace"] = plan.get("trace", [])
        hidden_context["product_routing_summary"] = plan.get("summary", "")

    return Scenario.from_dict(
        {
            "scenario_id": "routing_case_001",
            "product": {
                "brand": "美的",
                "category": "空气能热水器",
                "model": "KF66/200L-MI(E4)",
                "purchase_channel": "京东官方旗舰店",
            },
            "customer": {
                "full_name": "张三",
                "surname": "张",
                "phone": "13800138001",
                "address": "上海市浦东新区锦绣路1888弄6号1202室",
                "persona": "普通家用用户",
                "speech_style": "简短直接",
            },
            "request": {
                "request_type": "fault",
                "issue": "最近热水不稳定，想报修",
                "desired_resolution": "安排售后上门",
                "availability": "周末白天",
            },
            "hidden_context": hidden_context,
            "required_slots": [
                "issue_description",
                "surname",
                "phone",
                "address",
                "request_type",
            ],
            "max_turns": 20,
        }
    )


class RecordingClient:
    def __init__(self, reply: str):
        self.reply = reply
        self.calls: list[dict] = []

    def complete_json(self, **kwargs):
        self.calls.append(kwargs)
        return {"reply": self.reply, "call_complete": False}

    async def complete_json_async(self, **kwargs):
        self.calls.append(kwargs)
        return {"reply": self.reply, "call_complete": False}


class ProductRoutingPlanTests(unittest.TestCase):
    def test_build_product_routing_plan_returns_enabled_plan(self):
        plan = build_product_routing_plan(
            rng=random.Random(3),
            model_hint="KF66/200L-MI(E4)",
        )

        self.assertTrue(plan["enabled"])
        self.assertGreaterEqual(len(plan["steps"]), 1)
        self.assertEqual(plan["steps"][0]["prompt"], PROMPT_BRAND_OR_SERIES)
        self.assertTrue(plan["result"])
        self.assertIn(plan["result"], plan["summary"])

    def test_extract_address_components_handles_suffixless_city_and_district(self):
        components = extract_address_components("甘肃白银平川区")

        self.assertEqual(components.province, "甘肃")
        self.assertEqual(components.city, "白银市")
        self.assertEqual(components.district, "平川区")

    def test_extract_address_components_does_not_infer_fake_city_from_district_only_prefix(self):
        components = extract_address_components("七里河区雁南路福源佳园小区4号楼2单元")

        self.assertEqual(components.city, "")
        self.assertEqual(components.district, "七里河区")

    def test_extract_address_components_handles_autonomous_region_prefix(self):
        components = extract_address_components("广西壮族自治区来宾市武宣县通挽镇石坡村第五组17号")

        self.assertEqual(components.province, "广西")
        self.assertEqual(components.city, "来宾市")
        self.assertEqual(components.district, "武宣县")
        self.assertEqual(components.town, "通挽镇")
        self.assertEqual(components.community, "石坡村")

    def test_infer_product_routing_answer_key_maps_unknown_usage_purpose_to_unknown_branch(self):
        answer_key = infer_product_routing_answer_key("usage_purpose", "啊这个我也不知道啊")

        self.assertEqual(answer_key, "purpose.unknown")

    def test_infer_product_routing_answer_key_maps_colloquial_water_usage_to_water_branch(self):
        answer_key = infer_product_routing_answer_key("usage_purpose", "单独生活的")

        self.assertEqual(answer_key, "purpose.water")

    def test_infer_product_routing_answer_key_maps_bare_scene_negative_to_no_branch(self):
        answer_key = infer_product_routing_answer_key("usage_scene", "不是")

        self.assertEqual(answer_key, "scene.no")

    def test_infer_product_routing_answer_key_maps_bare_scene_affirmative_to_yes_branch(self):
        answer_key = infer_product_routing_answer_key("usage_scene", "是的")

        self.assertEqual(answer_key, "scene.yes")

    def test_infer_product_routing_answer_key_maps_chinese_capacity_range_below_threshold(self):
        answer_key = infer_product_routing_answer_key("capacity_or_hp", "五六百升吧好像")

        self.assertEqual(answer_key, "capacity.below_threshold")

    def test_infer_product_routing_answer_key_maps_cross_threshold_liter_range_to_unknown(self):
        answer_key = infer_product_routing_answer_key("capacity_or_hp", "七八百升吧")

        self.assertEqual(answer_key, "capacity.unknown")

    def test_infer_product_routing_answer_key_maps_cross_threshold_hp_range_to_unknown(self):
        answer_key = infer_product_routing_answer_key("capacity_or_hp", "三四匹吧")

        self.assertEqual(answer_key, "capacity.unknown")

    def test_infer_product_routing_answer_key_maps_house_purchase_gift_to_property_bundle(self):
        answer_key = infer_product_routing_answer_key("purchase_or_property", "当时买房送的吧")

        self.assertEqual(answer_key, "purchase.property_bundle")

    def test_infer_product_routing_answer_key_maps_short_purchase_reply_to_self_buy(self):
        answer_key = infer_product_routing_answer_key("purchase_or_property", "买的")

        self.assertEqual(answer_key, "purchase.self_buy")

    def test_infer_product_routing_answer_key_maps_short_gift_reply_to_property_bundle(self):
        answer_key = infer_product_routing_answer_key("purchase_or_property", "送的")

        self.assertEqual(answer_key, "purchase.property_bundle")

    def test_infer_product_routing_answer_key_maps_baigei_reply_to_property_bundle(self):
        answer_key = infer_product_routing_answer_key("purchase_or_property", "白给的")

        self.assertEqual(answer_key, "purchase.property_bundle")

    def test_infer_product_routing_answer_key_maps_house_builtin_to_property_bundle(self):
        answer_key = infer_product_routing_answer_key("purchase_or_property", "买房当时自带的")

        self.assertEqual(answer_key, "purchase.property_bundle")

    def test_infer_product_routing_answer_key_maps_house_already_had_it_to_property_bundle(self):
        answer_key = infer_product_routing_answer_key("purchase_or_property", "当时好像房子自己就有")

        self.assertEqual(answer_key, "purchase.property_bundle")

    def test_infer_product_routing_answer_key_maps_specific_two_digit_property_year(self):
        answer_key = infer_product_routing_answer_key("property_year", "19年的楼盘")

        self.assertEqual(answer_key, "property_year.before_2021")

    def test_infer_product_routing_answer_key_maps_specific_four_digit_property_year(self):
        answer_key = infer_product_routing_answer_key("property_year", "2018年交付的")

        self.assertEqual(answer_key, "property_year.before_2021")

    def test_infer_product_routing_answer_key_maps_specific_post_2021_property_year(self):
        answer_key = infer_product_routing_answer_key("property_year", "22年的")

        self.assertEqual(answer_key, "property_year.after_2021")

    def test_infer_product_routing_answer_key_maps_unknown_property_year(self):
        answer_key = infer_product_routing_answer_key("property_year", "这个时间太久了，我有点忘记了")

        self.assertEqual(answer_key, "property_year.unknown")


class ProductRoutingServicePolicyTests(unittest.TestCase):
    def test_service_policy_inserts_routing_between_opening_and_fault_question(self):
        plan = {
            "enabled": True,
            "result": ROUTING_RESULT_BUILDING,
            "trace": ["entry.unknown", "purpose.both"],
            "summary": "entry.unknown -> purpose.both -> 楼宇 + 可直接确认机型",
            "steps": [
                {
                    "prompt_key": "brand_or_series",
                    "prompt": PROMPT_BRAND_OR_SERIES,
                    "answer_key": "entry.unknown",
                    "answer_value": "不知道品牌或系列",
                    "answer_instruction": "自然表达自己不知道品牌或系列，或暂时提供不了。",
                },
                {
                    "prompt_key": "usage_purpose",
                    "prompt": PROMPT_USAGE_PURPOSE,
                    "answer_key": "purpose.both",
                    "answer_value": "生活用水和采暖都有",
                    "answer_instruction": "自然表达机器同时用于生活用水和采暖。",
                },
            ],
        }
        scenario = build_scenario_with_routing(plan)
        policy = ServiceDialoguePolicy(ok_prefix_probability=0.0, rng=random.Random(0))
        state = ServiceRuntimeState()
        collected_slots = {
            "issue_description": "",
            "surname": "",
            "phone": "",
            "address": "",
            "request_type": "",
            "phone_contactable": "",
            "phone_contact_owner": "",
            "phone_collection_attempts": "",
            "product_arrived": "",
        }

        opening_followup = policy.respond(
            scenario=scenario,
            transcript=[
                DialogueTurn(
                    speaker="service",
                    text="您好，很高兴为您服务，请问是美的空气能热水器需要维修吗？",
                    round_index=1,
                ),
                DialogueTurn(
                    speaker="user",
                    text="对，是要维修。",
                    round_index=2,
                ),
            ],
            collected_slots=collected_slots,
            runtime_state=state,
        )
        collected_slots.update(opening_followup.slot_updates)
        self.assertEqual(opening_followup.reply, PROMPT_BRAND_OR_SERIES)
        self.assertTrue(state.expected_product_routing_response)

        routing_step_2 = policy.respond(
            scenario=scenario,
            transcript=[
                DialogueTurn(
                    speaker="service",
                    text="您好，很高兴为您服务，请问是美的空气能热水器需要维修吗？",
                    round_index=1,
                ),
                DialogueTurn(speaker="user", text="对，是要维修。", round_index=2),
                DialogueTurn(speaker="service", text=PROMPT_BRAND_OR_SERIES, round_index=2),
                DialogueTurn(speaker="user", text="这个我不太清楚。", round_index=3),
            ],
            collected_slots=collected_slots,
            runtime_state=state,
        )
        self.assertEqual(routing_step_2.reply, PROMPT_USAGE_PURPOSE)
        self.assertEqual(state.product_routing_step_index, 0)
        self.assertEqual(state.product_routing_observed_trace, ["entry.unknown"])

        post_routing = policy.respond(
            scenario=scenario,
            transcript=[
                DialogueTurn(
                    speaker="service",
                    text="您好，很高兴为您服务，请问是美的空气能热水器需要维修吗？",
                    round_index=1,
                ),
                DialogueTurn(speaker="user", text="对，是要维修。", round_index=2),
                DialogueTurn(speaker="service", text=PROMPT_BRAND_OR_SERIES, round_index=2),
                DialogueTurn(speaker="user", text="这个我不太清楚。", round_index=3),
                DialogueTurn(speaker="service", text=PROMPT_USAGE_PURPOSE, round_index=3),
                DialogueTurn(speaker="user", text="生活用水和采暖都有。", round_index=4),
            ],
            collected_slots=collected_slots,
            runtime_state=state,
        )
        self.assertEqual(post_routing.reply, "请问空气能热水器现在是出现了什么问题？")
        self.assertEqual(post_routing.slot_updates["product_routing_result"], ROUTING_RESULT_BUILDING)
        self.assertTrue(state.product_routing_completed)

    def test_service_policy_prepends_fault_ack_before_first_routing_question(self):
        plan = {
            "enabled": True,
            "result": ROUTING_RESULT_BUILDING,
            "trace": ["entry.unknown", "purpose.heating"],
            "summary": "entry.unknown -> purpose.heating -> 楼宇 + 可直接确认机型",
            "steps": [
                {
                    "prompt_key": "brand_or_series",
                    "prompt": PROMPT_BRAND_OR_SERIES,
                    "answer_key": "entry.unknown",
                    "answer_value": "不知道品牌或系列",
                    "answer_instruction": "自然表达自己不知道品牌或系列，或暂时提供不了。",
                }
            ],
        }
        scenario = build_scenario_with_routing(plan)
        policy = ServiceDialoguePolicy(ok_prefix_probability=0.0, rng=random.Random(0))
        state = ServiceRuntimeState()

        result = policy.respond(
            scenario=scenario,
            transcript=[
                DialogueTurn(
                    speaker="service",
                    text="您好，很高兴为您服务，请问是美的空气能热水器需要维修吗？",
                    round_index=1,
                ),
                DialogueTurn(
                    speaker="user",
                    text="对，是的，我家热水器加热太慢了，晚上水不够热。",
                    round_index=2,
                ),
            ],
            collected_slots={
                "issue_description": "",
                "surname": "",
                "phone": "",
                "address": "",
                "request_type": "",
                "phone_contactable": "",
                "phone_contact_owner": "",
                "phone_collection_attempts": "",
                "product_arrived": "",
            },
            runtime_state=state,
        )

        self.assertEqual(
            result.reply,
            "非常抱歉，给您添麻烦了，我这就安排是否上门维修，请问您的空气能是什么具体品牌或系列呢？",
        )

    def test_service_policy_reroutes_unknown_usage_purpose_to_usage_scene(self):
        plan = {
            "enabled": True,
            "result": ROUTING_RESULT_BUILDING,
            "trace": ["entry.unknown", "purpose.water", "capacity.below_threshold"],
            "summary": "entry.unknown -> purpose.water -> capacity.below_threshold -> 楼宇 + 可直接确认机型",
            "steps": [
                {
                    "prompt_key": "brand_or_series",
                    "prompt": PROMPT_BRAND_OR_SERIES,
                    "answer_key": "entry.unknown",
                    "answer_value": "不知道品牌或系列",
                    "answer_instruction": "自然表达自己不知道品牌或系列，或暂时提供不了。",
                },
                {
                    "prompt_key": "usage_purpose",
                    "prompt": PROMPT_USAGE_PURPOSE,
                    "answer_key": "purpose.water",
                    "answer_value": "单独生活用水",
                    "answer_instruction": "自然表达机器是单独生活用水/洗澡热水用途。",
                },
                {
                    "prompt_key": "capacity_or_hp",
                    "prompt": "请问机器是多少升的，或者多少匹数的呢？",
                    "answer_key": "capacity.below_threshold",
                    "answer_value": "750升以下",
                    "answer_instruction": "自然表达机器容量较小。",
                },
            ],
        }
        scenario = build_scenario_with_routing(plan)
        policy = ServiceDialoguePolicy(ok_prefix_probability=0.0, rng=random.Random(0))
        state = ServiceRuntimeState(product_routing_observed_trace=["entry.unknown"])
        state.expected_product_routing_response = True
        state.product_routing_step_index = 1

        result = policy.respond(
            scenario=scenario,
            transcript=[
                DialogueTurn(speaker="service", text=PROMPT_USAGE_PURPOSE, round_index=3),
                DialogueTurn(speaker="user", text="啊这个我也不知道啊", round_index=4),
            ],
            collected_slots={
                "issue_description": "",
                "surname": "",
                "phone": "",
                "address": "",
                "request_type": "",
                "phone_contactable": "",
                "phone_contact_owner": "",
                "phone_collection_attempts": "",
                "product_arrived": "",
            },
            runtime_state=state,
        )

        self.assertEqual(result.reply, PROMPT_USAGE_SCENE)
        self.assertEqual(state.product_routing_observed_trace, ["entry.unknown", "purpose.unknown"])
        self.assertEqual(
            scenario.hidden_context["product_routing_trace"],
            ["entry.unknown", "purpose.unknown"],
        )

    def test_service_policy_stops_at_building_when_unknown_purpose_then_bare_scene_negative(self):
        plan = {
            "enabled": True,
            "result": ROUTING_RESULT_BUILDING,
            "trace": ["entry.unknown", "purpose.unknown", "scene.no"],
            "summary": "entry.unknown -> purpose.unknown -> scene.no -> 楼宇 + 可直接确认机型",
            "steps": [
                {
                    "prompt_key": "usage_scene",
                    "prompt": PROMPT_USAGE_SCENE,
                    "answer_key": "scene.no",
                    "answer_value": "不是家庭/别墅/公寓/理发店使用",
                    "answer_instruction": "自然表达这不是用户本人居住或单体经营空间内的使用场景，不算这里的“公寓”。不要为了回答问题刻意复述提示语里的分类解释。",
                }
            ],
        }
        scenario = build_scenario_with_routing(plan)
        policy = ServiceDialoguePolicy(ok_prefix_probability=0.0, rng=random.Random(0))
        state = ServiceRuntimeState(
            expected_product_routing_response=True,
            product_routing_step_index=0,
            product_routing_observed_trace=["entry.unknown", "purpose.unknown"],
        )

        result = policy.respond(
            scenario=scenario,
            transcript=[
                DialogueTurn(speaker="service", text=PROMPT_USAGE_SCENE, round_index=5),
                DialogueTurn(speaker="user", text="不是", round_index=6),
            ],
            collected_slots={
                "issue_description": "",
                "surname": "",
                "phone": "",
                "address": "",
                "request_type": "",
                "phone_contactable": "",
                "phone_contact_owner": "",
                "phone_collection_attempts": "",
                "product_arrived": "",
            },
            runtime_state=state,
        )

        self.assertEqual(result.reply, "请问空气能热水器现在是出现了什么问题？")
        self.assertEqual(result.slot_updates["product_routing_result"], ROUTING_RESULT_BUILDING)
        self.assertEqual(
            state.product_routing_observed_trace,
            ["entry.unknown", "purpose.unknown", "scene.no"],
        )
        self.assertTrue(state.product_routing_completed)

    def test_service_policy_stops_at_building_when_property_year_is_unknown(self):
        plan = {
            "enabled": True,
            "result": ROUTING_RESULT_BUILDING,
            "trace": ["property_year.unknown"],
            "summary": "property_year.unknown -> 楼宇 + 可直接确认机型",
            "steps": [
                {
                    "prompt_key": "property_year",
                    "prompt": "请问是21年之前的楼盘，还是之后的呢？",
                    "answer_key": "property_year.unknown",
                    "answer_value": "不清楚楼盘年份",
                    "answer_instruction": "自然表达自己不清楚楼盘属于 2021 年之前还是之后，也没有提供可辅助判断的大概时间点。",
                }
            ],
        }
        scenario = build_scenario_with_routing(plan)
        policy = ServiceDialoguePolicy(ok_prefix_probability=0.0, rng=random.Random(0))
        state = ServiceRuntimeState(
            expected_product_routing_response=True,
            product_routing_step_index=0,
            product_routing_observed_trace=["entry.unknown", "purpose.unknown", "scene.yes", "purchase.property_bundle"],
        )

        result = policy.respond(
            scenario=scenario,
            transcript=[
                DialogueTurn(speaker="service", text="请问是21年之前的楼盘，还是之后的呢？", round_index=6),
                DialogueTurn(speaker="user", text="忘记了", round_index=7),
            ],
            collected_slots={
                "issue_description": "",
                "surname": "",
                "phone": "",
                "address": "",
                "request_type": "",
                "phone_contactable": "",
                "phone_contact_owner": "",
                "phone_collection_attempts": "",
                "product_arrived": "",
            },
            runtime_state=state,
        )

        self.assertEqual(result.reply, "请问空气能热水器现在是出现了什么问题？")
        self.assertEqual(result.slot_updates["product_routing_result"], ROUTING_RESULT_BUILDING)
        self.assertEqual(
            state.product_routing_observed_trace,
            ["entry.unknown", "purpose.unknown", "scene.yes", "purchase.property_bundle", "property_year.unknown"],
        )
        self.assertTrue(state.product_routing_completed)

    def test_user_prompt_disambiguates_apartment_from_building_public_area(self):
        plan = {
            "enabled": True,
            "result": ROUTING_RESULT_BUILDING,
            "trace": ["scene.no"],
            "summary": "scene.no -> 楼宇 + 可直接确认机型",
            "steps": [
                {
                    "prompt_key": "usage_scene",
                    "prompt": "请问是在家庭、别墅、公寓或理发店使用的吗？",
                    "answer_key": "scene.no",
                    "answer_value": "不是家庭/别墅/公寓/理发店使用",
                    "answer_instruction": "自然表达这不是用户本人居住或单体经营空间内的使用场景，不算这里的“公寓”。不要为了回答问题刻意复述提示语里的分类解释。",
                }
            ],
        }
        scenario = build_scenario_with_routing(plan)
        prompt_messages = build_user_agent_messages(
            scenario,
            transcript=[
                DialogueTurn(
                    speaker="service",
                    text="请问是在家庭、别墅、公寓或理发店使用的吗？",
                    round_index=4,
                )
            ],
            round_index=5,
            second_round_reply_strategy="confirm_only",
        )

        self.assertIn("它只指用户自己居住的公寓住房", prompt_messages[1]["content"])
        self.assertNotIn("小区楼宇", prompt_messages[1]["content"])

    def test_user_prompt_for_unknown_routing_answer_prefers_direct_uncertainty_expression(self):
        plan = {
            "enabled": True,
            "result": ROUTING_RESULT_HOME,
            "trace": ["purpose.unknown"],
            "summary": "purpose.unknown -> 家用 + 可直接确认机型",
            "steps": [
                {
                    "prompt_key": "usage_purpose",
                    "prompt": PROMPT_USAGE_PURPOSE,
                    "answer_key": "purpose.unknown",
                    "answer_value": "不清楚用途",
                    "answer_instruction": "优先用一小句直接表达自己不清楚机器用途；不要先猜生活用水还是采暖再反复改口。",
                }
            ],
        }
        scenario = build_scenario_with_routing(plan)
        prompt_messages = build_user_agent_messages(
            scenario,
            transcript=[
                DialogueTurn(
                    speaker="service",
                    text=PROMPT_USAGE_PURPOSE,
                    round_index=4,
                )
            ],
            round_index=5,
            second_round_reply_strategy="confirm_only",
        )

        self.assertIn("优先一两句直接表达不知道、不确定、记不清就够了", prompt_messages[1]["content"])
        self.assertIn("不要先猜一个答案再否定", prompt_messages[1]["content"])
        self.assertIn("不要为了显得自然而故意说得很长", prompt_messages[1]["content"])


class ProductRoutingUserAgentTests(unittest.IsolatedAsyncioTestCase):
    def test_user_agent_prompt_contains_routing_instruction_and_llm_generates_reply(self):
        plan = {
            "enabled": True,
            "result": ROUTING_RESULT_BUILDING,
            "trace": ["entry.unknown"],
            "summary": "entry.unknown -> 楼宇 + 可直接确认机型",
            "steps": [
                {
                    "prompt_key": "brand_or_series",
                    "prompt": PROMPT_BRAND_OR_SERIES,
                    "answer_key": "entry.unknown",
                    "answer_value": "不知道品牌或系列",
                    "answer_instruction": "自然表达自己不知道品牌或系列，或暂时提供不了。",
                }
            ],
        }
        scenario = build_scenario_with_routing(plan)
        client = RecordingClient("品牌系列我一下子真说不上来。")
        agent = UserAgent(
            client,
            model="test-model",
            temperature=0.7,
            second_round_include_issue_probability=0.5,
        )

        prompt_messages = build_user_agent_messages(
            scenario,
            transcript=[
                DialogueTurn(
                    speaker="service",
                    text=PROMPT_BRAND_OR_SERIES,
                    round_index=2,
                )
            ],
            round_index=3,
            second_round_reply_strategy="confirm_only",
        )
        self.assertIn("产品归属中间路由约束", prompt_messages[1]["content"])
        self.assertIn("自然表达自己不知道品牌或系列", prompt_messages[1]["content"])

        result = agent.respond(
            scenario=scenario,
            transcript=[
                DialogueTurn(
                    speaker="service",
                    text=PROMPT_BRAND_OR_SERIES,
                    round_index=2,
                )
            ],
            round_index=3,
        )

        self.assertEqual(result["reply"], "品牌系列我一下子真说不上来。")
        self.assertFalse(result["call_complete"])
        self.assertEqual(len(client.calls), 1)


class ProductRoutingServiceAgentFallbackTests(unittest.TestCase):
    def test_service_agent_can_attach_routing_plan_when_missing(self):
        scenario = build_scenario_with_routing(None)
        agent = ServiceAgent(
            RecordingClient("忽略"),
            model="test-model",
            temperature=0.7,
            ok_prefix_probability=0.0,
            product_routing_enabled=True,
            product_routing_apply_probability=1.0,
        )
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
                    text="对，是要维修。",
                    round_index=2,
                ),
            ],
            collected_slots={
                "issue_description": "",
                "surname": "",
                "phone": "",
                "address": "",
                "request_type": "",
                "phone_contactable": "",
                "phone_contact_owner": "",
                "phone_collection_attempts": "",
                "product_arrived": "",
            },
            runtime_state=state,
        )

        self.assertEqual(result["reply"], PROMPT_BRAND_OR_SERIES)
        self.assertIn("product_routing_plan", scenario.hidden_context)


if __name__ == "__main__":
    unittest.main(verbosity=2)
