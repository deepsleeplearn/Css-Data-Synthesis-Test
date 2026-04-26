from __future__ import annotations

import random
import unittest

from css_data_synthesis_test.address_utils import extract_address_components
from css_data_synthesis_test.agents import ServiceAgent, UserAgent
from css_data_synthesis_test.product_routing import (
    PROMPT_BRAND_OR_SERIES,
    PROMPT_PURCHASE_OR_PROPERTY,
    PROMPT_USAGE_SCENE,
    PROMPT_USAGE_PURPOSE,
    ROUTING_RESULT_BUILDING,
    ROUTING_RESULT_HOME,
    build_product_routing_plan,
    current_product_routing_step,
    infer_model_lookup_answer_key,
    infer_product_routing_answer_key,
    next_product_routing_steps_from_observed_trace,
)
from css_data_synthesis_test.prompts import build_user_agent_messages
from css_data_synthesis_test.schemas import DialogueTurn, Scenario
from css_data_synthesis_test.service_policy import ServiceDialoguePolicy, ServiceRuntimeState


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

    def test_build_product_routing_plan_uses_manual_history_device_prompt(self):
        plan = build_product_routing_plan(
            rng=random.Random(3),
            hidden_context={
                "product_routing_has_history_device": True,
                "air_energy_history_device": {
                    "brand": "COLMO",
                    "category": "家用空气能热水机",
                    "purchase_date": "2024-05-12",
                },
                "product_routing_entry_weights": {"brand_series": 0.0, "model": 0.0, "unknown": 1.0},
                "product_routing_usage_scene_weights": {
                    "family": 1.0,
                    "villa_apartment_barber": 0.0,
                    "other_unknown": 0.0,
                },
                "product_routing_history_confirmation_weights": {"yes": 1.0, "no_unknown": 0.0},
            },
        )

        prompts = [step["prompt"] for step in plan["steps"]]
        self.assertIn("这边看到您2024年5月有购买一台COLMO家用空气能热水机，请问是这台吗？", prompts)

    def test_next_steps_preserve_initial_preview_plan_after_runtime_truncation(self):
        plan = {
            "enabled": True,
            "result": ROUTING_RESULT_BUILDING,
            "trace": [
                "entry.unknown",
                "scene.family",
                "history_device.no_unknown",
                "purchase.property_bundle",
                "property_year.after_2021",
            ],
            "summary": (
                "entry.unknown -> scene.family -> history_device.no_unknown -> "
                "purchase.property_bundle -> property_year.after_2021 -> 楼宇 + 可直接确认机型"
            ),
            "steps": [
                {
                    "prompt_key": "brand_or_series",
                    "prompt": PROMPT_BRAND_OR_SERIES,
                    "answer_key": "entry.unknown",
                    "answer_value": "不知道品牌或系列",
                    "answer_instruction": "自然表达自己不知道品牌或系列。",
                },
                {
                    "prompt_key": "usage_scene",
                    "prompt": PROMPT_USAGE_SCENE,
                    "answer_key": "scene.family",
                    "answer_value": "家庭使用",
                    "answer_instruction": "自然表达空气能是在家庭场所使用。",
                },
                {
                    "prompt_key": "history_device_confirmation",
                    "prompt": "这边看到您2024年5月有购买一台COLMO家用空气能热水机，请问是这台吗？",
                    "answer_key": "history_device.no_unknown",
                    "answer_value": "不是或不清楚查询到的设备",
                    "answer_instruction": "自然表达不是查询到的那台设备。",
                },
                {
                    "prompt_key": "purchase_or_property",
                    "prompt": PROMPT_PURCHASE_OR_PROPERTY,
                    "answer_key": "purchase.property_bundle",
                    "answer_value": "楼盘配套赠送",
                    "answer_instruction": "自然表达机器是楼盘配套赠送的。",
                },
                {
                    "prompt_key": "property_year",
                    "prompt": "请问是21年之前的楼盘，还是之后的呢？",
                    "answer_key": "property_year.after_2021",
                    "answer_value": "21年之后的楼盘",
                    "answer_instruction": "自然表达楼盘属于 2021 年之后。",
                },
            ],
        }
        hidden_context = {
            "product_routing_initial_plan": plan,
            "product_routing_plan": {
                "enabled": True,
                "result": "",
                "trace": ["entry.unknown"],
                "summary": "entry.unknown",
                "steps": [plan["steps"][1]],
            },
            "air_energy_history_device": {"brand": "COLMO"},
        }

        next_steps, result = next_product_routing_steps_from_observed_trace(
            ["entry.unknown"],
            hidden_context=hidden_context,
        )
        self.assertEqual(result, "")
        self.assertEqual(next_steps[0]["answer_key"], "scene.family")

        next_steps, result = next_product_routing_steps_from_observed_trace(
            ["entry.unknown", "scene.family"],
            hidden_context=hidden_context,
        )
        self.assertEqual(result, "")
        self.assertEqual(next_steps[0]["answer_key"], "history_device.no_unknown")

        next_steps, result = next_product_routing_steps_from_observed_trace(
            ["entry.unknown", "scene.family", "history_device.no_unknown"],
            hidden_context=hidden_context,
        )
        self.assertEqual(result, "")
        self.assertEqual(next_steps[0]["answer_key"], "purchase.property_bundle")

        next_steps, result = next_product_routing_steps_from_observed_trace(
            [
                "entry.unknown",
                "scene.family",
                "history_device.no_unknown",
                "purchase.property_bundle",
            ],
            hidden_context=hidden_context,
        )
        self.assertEqual(result, "")
        self.assertEqual(next_steps[0]["answer_key"], "property_year.after_2021")

    def test_current_product_routing_step_matches_fault_ack_prefixed_prompt(self):
        plan = {
            "enabled": True,
            "result": ROUTING_RESULT_BUILDING,
            "trace": ["entry.unknown", "scene.villa_apartment_barber"],
            "summary": "entry.unknown -> scene.villa_apartment_barber -> 楼宇 + 可直接确认机型",
            "steps": [
                {
                    "prompt_key": "brand_or_series",
                    "prompt": PROMPT_BRAND_OR_SERIES,
                    "answer_key": "entry.unknown",
                    "answer_value": "不知道品牌或系列",
                    "answer_instruction": "自然表达自己不知道品牌或系列。",
                }
            ],
        }
        step = current_product_routing_step(
            [
                DialogueTurn(
                    speaker="service",
                    text=f"非常抱歉，给您添麻烦了，我帮您安排售后处理，{PROMPT_BRAND_OR_SERIES}",
                    round_index=3,
                )
            ],
            {"product_routing_plan": plan},
        )

        self.assertIsNotNone(step)
        self.assertEqual(step["answer_key"], "entry.unknown")

    def test_extract_address_components_handles_suffixless_city_and_district(self):
        components = extract_address_components("甘肃白银平川区")

        self.assertEqual(components.province, "甘肃省")
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

    def test_infer_product_routing_answer_key_maps_generic_midea_brand_to_unknown_entry_branch(self):
        answer_key = infer_product_routing_answer_key("brand_or_series", "应该是美的吧")

        self.assertEqual(answer_key, "entry.unknown")

    def test_infer_product_routing_answer_key_maps_only_knows_midea_brand_to_unknown_entry_branch(self):
        answer_key = infer_product_routing_answer_key("brand_or_series", "我就知道是美的的啊")

        self.assertEqual(answer_key, "entry.unknown")

    def test_infer_product_routing_answer_key_maps_colmo_homophones(self):
        for user_text in ("科慕的", "可木的", "科目的", "扣摸的"):
            with self.subTest(user_text=user_text):
                answer_key = infer_product_routing_answer_key("brand_or_series", user_text)

                self.assertEqual(answer_key, "brand_series.colmo")

    def test_infer_product_routing_answer_key_maps_lieyan_homophones(self):
        for user_text in ("莲叶的", "莲炎的", "列焰的", "连叶的"):
            with self.subTest(user_text=user_text):
                answer_key = infer_product_routing_answer_key("brand_or_series", user_text)

                self.assertEqual(answer_key, "brand_series.lieyan")

    def test_infer_product_routing_answer_key_maps_other_series_homophones(self):
        cases = {
            "库风的": "brand_series.cooling_or_little_swan",
            "小天娥": "brand_series.cooling_or_little_swan",
            "真神系列": "brand_series.home_series",
            "真想的": "brand_series.home_series",
            "雪燕": "brand_series.home_series",
            "暖佳": "brand_series.home_series",
        }
        for user_text, expected in cases.items():
            with self.subTest(user_text=user_text):
                answer_key = infer_product_routing_answer_key("brand_or_series", user_text)

                self.assertEqual(answer_key, expected)

    def test_infer_product_routing_answer_key_maps_zhensheng_series_to_home_series(self):
        answer_key = infer_product_routing_answer_key("brand_or_series", "买的时候,店家说叫什么真省")

        self.assertEqual(answer_key, "brand_series.home_series")

    def test_infer_product_routing_answer_key_maps_colloquial_zhensheng_reply_to_home_series(self):
        answer_key = infer_product_routing_answer_key("brand_or_series", "那个真省的好像")

        self.assertEqual(answer_key, "brand_series.home_series")

    def test_infer_product_routing_answer_key_maps_colloquial_water_usage_to_water_branch(self):
        answer_key = infer_product_routing_answer_key("usage_purpose", "单独生活的")

        self.assertEqual(answer_key, "purpose.water")

    def test_infer_product_routing_answer_key_maps_negated_heating_with_bathing_to_water_branch(self):
        answer_key = infer_product_routing_answer_key("usage_purpose", "我们家好像就用它来洗澡，应该没采暖功能")

        self.assertEqual(answer_key, "purpose.water")

    def test_infer_product_routing_answer_key_maps_bare_scene_negative_to_no_branch(self):
        answer_key = infer_product_routing_answer_key("usage_scene", "不是")

        self.assertEqual(answer_key, "scene.other_unknown")

    def test_infer_product_routing_answer_key_maps_bare_scene_affirmative_to_yes_branch(self):
        answer_key = infer_product_routing_answer_key("usage_scene", "是的")

        self.assertEqual(answer_key, "scene.other_unknown")

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

    def test_next_product_routing_steps_routes_model_entry_to_usage_scene_question(self):
        next_steps, result = next_product_routing_steps_from_observed_trace(
            ["entry.model"],
            model_hint="KF66/200L-MI(E4)",
        )

        self.assertEqual(result, "")
        self.assertEqual(len(next_steps), 1)
        self.assertEqual(next_steps[0]["prompt_key"], "usage_scene")
        self.assertEqual(next_steps[0]["prompt"], PROMPT_USAGE_SCENE)

    def test_next_product_routing_steps_routes_villa_apartment_barber_scene_to_building(self):
        next_steps, result = next_product_routing_steps_from_observed_trace(
            ["entry.model", "scene.villa_apartment_barber"],
            model_hint="KF66/200L-MI(E4)",
        )

        self.assertEqual(next_steps, [])
        self.assertEqual(result, ROUTING_RESULT_BUILDING)

    def test_infer_model_lookup_answer_key_defaults_known_homeish_model_to_unknown(self):
        answer_key = infer_model_lookup_answer_key("KF66/200L-MI(E4)")

        self.assertEqual(answer_key, "model_lookup.unknown")

    def test_infer_model_lookup_answer_key_maps_large_capacity_model_to_building(self):
        answer_key = infer_model_lookup_answer_key("KF110/500L-D")

        self.assertEqual(answer_key, "model_lookup.building")


class ProductRoutingServicePolicyTests(unittest.TestCase):
    def test_service_policy_routes_zhensheng_series_to_home_without_handoff(self):
        plan = {
            "enabled": True,
            "result": ROUTING_RESULT_HOME,
            "trace": ["brand_series.home_series"],
            "summary": "brand_series.home_series -> 家用 + 可直接确认机型",
            "steps": [
                {
                    "prompt_key": "brand_or_series",
                    "prompt": PROMPT_BRAND_OR_SERIES,
                    "answer_key": "entry.unknown",
                    "answer_value": "真省",
                    "answer_instruction": "自然表达副品牌/系列是真省。",
                }
            ],
        }
        scenario = build_scenario_with_routing(plan)
        policy = ServiceDialoguePolicy(ok_prefix_probability=0.0)
        state = ServiceRuntimeState(
            expected_product_routing_response=True,
            product_routing_step_index=0,
            product_routing_observed_trace=[],
        )

        result = policy.respond(
            scenario=scenario,
            transcript=[
                DialogueTurn(speaker="service", text=PROMPT_BRAND_OR_SERIES, round_index=2),
                DialogueTurn(speaker="user", text="买的时候,店家说叫什么真省", round_index=3),
            ],
            collected_slots={
                "issue_description": "热水不稳定",
                "surname": "",
                "phone": "",
                "address": "",
                "request_type": "fault",
                "phone_contactable": "",
                "phone_contact_owner": "",
                "phone_collection_attempts": "",
                "product_arrived": "",
                "product_routing_result": "",
            },
            runtime_state=state,
        )

        self.assertEqual(result.reply, "请问您贵姓？")
        self.assertEqual(result.close_status, "")
        self.assertEqual(result.close_reason, "")
        self.assertEqual(result.slot_updates["product_routing_result"], ROUTING_RESULT_HOME)
        self.assertEqual(state.product_routing_observed_trace, ["brand_series.home_series"])

    def test_service_policy_routes_colloquial_zhensheng_reply_to_home_without_handoff(self):
        plan = {
            "enabled": True,
            "result": ROUTING_RESULT_HOME,
            "trace": ["brand_series.home_series"],
            "summary": "brand_series.home_series -> 家用 + 可直接确认机型",
            "steps": [
                {
                    "prompt_key": "brand_or_series",
                    "prompt": PROMPT_BRAND_OR_SERIES,
                    "answer_key": "entry.unknown",
                    "answer_value": "真省",
                    "answer_instruction": "自然表达副品牌/系列是真省。",
                }
            ],
        }
        scenario = build_scenario_with_routing(plan)
        policy = ServiceDialoguePolicy(ok_prefix_probability=0.0)
        state = ServiceRuntimeState(
            expected_product_routing_response=True,
            product_routing_step_index=0,
            product_routing_observed_trace=[],
        )

        result = policy.respond(
            scenario=scenario,
            transcript=[
                DialogueTurn(speaker="service", text=PROMPT_BRAND_OR_SERIES, round_index=2),
                DialogueTurn(speaker="user", text="那个真省的好像", round_index=3),
            ],
            collected_slots={
                "issue_description": "热水不稳定",
                "surname": "",
                "phone": "",
                "address": "",
                "request_type": "fault",
                "phone_contactable": "",
                "phone_contact_owner": "",
                "phone_collection_attempts": "",
                "product_arrived": "",
                "product_routing_result": "",
            },
            runtime_state=state,
        )

        self.assertEqual(result.reply, "请问您贵姓？")
        self.assertEqual(result.close_status, "")
        self.assertEqual(result.close_reason, "")
        self.assertEqual(result.slot_updates["product_routing_result"], ROUTING_RESULT_HOME)
        self.assertEqual(state.product_routing_observed_trace, ["brand_series.home_series"])

    def test_service_policy_resets_hidden_plan_trace_before_brand_answer_and_then_records_actual_answer(self):
        plan = {
            "enabled": True,
            "result": ROUTING_RESULT_HOME,
            "trace": ["brand_series.colmo"],
            "summary": "brand_series.colmo -> 家用 + 可直接确认机型",
            "steps": [
                {
                    "prompt_key": "brand_or_series",
                    "prompt": PROMPT_BRAND_OR_SERIES,
                    "answer_key": "brand_series.colmo",
                    "answer_value": "COLMO",
                    "answer_instruction": "自然表达品牌或系列是 COLMO。",
                }
            ],
        }
        scenario = build_scenario_with_routing(plan)
        policy = ServiceDialoguePolicy(ok_prefix_probability=0.0)
        state = ServiceRuntimeState()

        opening_result = policy.respond(
            scenario=scenario,
            transcript=[
                DialogueTurn(
                    speaker="service",
                    text="您好，很高兴为您服务，请问是美的空气能热水器需要维修吗？",
                    round_index=1,
                ),
                DialogueTurn(
                    speaker="user",
                    text="是的",
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
                "product_routing_result": "",
            },
            runtime_state=state,
        )

        self.assertEqual(opening_result.reply, PROMPT_BRAND_OR_SERIES)
        self.assertEqual(state.product_routing_observed_trace, [])
        self.assertEqual(scenario.hidden_context["product_routing_trace"], [])
        self.assertEqual(scenario.hidden_context["product_routing_plan"]["trace"], [])

        answer_result = policy.respond(
            scenario=scenario,
            transcript=[
                DialogueTurn(speaker="service", text=PROMPT_BRAND_OR_SERIES, round_index=2),
                DialogueTurn(speaker="user", text="那个真省的好像", round_index=3),
            ],
            collected_slots={
                "issue_description": "热水不稳定",
                "surname": "",
                "phone": "",
                "address": "",
                "request_type": "fault",
                "phone_contactable": "",
                "phone_contact_owner": "",
                "phone_collection_attempts": "",
                "product_arrived": "",
                "product_routing_result": "",
            },
            runtime_state=ServiceRuntimeState(
                expected_product_routing_response=True,
                product_routing_step_index=0,
                product_routing_observed_trace=[],
            ),
        )

        self.assertEqual(answer_result.reply, "请问您贵姓？")
        self.assertEqual(scenario.hidden_context["product_routing_trace"], ["brand_series.home_series"])
        self.assertEqual(scenario.hidden_context["product_routing_plan"]["trace"], ["brand_series.home_series"])

    def test_service_policy_ignores_legacy_model_lookup_trace_after_user_provides_model(self):
        plan = {
            "enabled": True,
            "result": ROUTING_RESULT_HOME,
            "trace": ["entry.model", "scene.family", "purchase.self_buy"],
            "summary": "entry.model -> scene.family -> purchase.self_buy -> 家用 + 可直接确认机型",
            "steps": [
                {
                    "prompt_key": "brand_or_series",
                    "prompt": PROMPT_BRAND_OR_SERIES,
                    "answer_key": "entry.model",
                    "answer_value": "KF66/200L-MI(E4)",
                    "answer_instruction": "自然提供一个具体型号，不要说自己不知道。",
                    "post_answer_trace": ["model_lookup.unknown"],
                }
            ],
        }
        scenario = build_scenario_with_routing(plan)
        policy = ServiceDialoguePolicy(ok_prefix_probability=0.0, rng=random.Random(0))
        state = ServiceRuntimeState(
            expected_product_routing_response=True,
            product_routing_step_index=0,
            product_routing_observed_trace=[],
        )

        result = policy.respond(
            scenario=scenario,
            transcript=[
                DialogueTurn(
                    speaker="service",
                    text=PROMPT_BRAND_OR_SERIES,
                    round_index=2,
                ),
                DialogueTurn(
                    speaker="user",
                    text="型号是KF66/200L-MI(E4)",
                    round_index=3,
                ),
            ],
            collected_slots={
                "issue_description": "热水不稳定",
                "surname": "",
                "phone": "",
                "address": "",
                "request_type": "fault",
                "phone_contactable": "",
                "phone_contact_owner": "",
                "phone_collection_attempts": "",
                "product_arrived": "",
            },
            runtime_state=state,
        )

        self.assertEqual(result.reply, PROMPT_USAGE_SCENE)
        self.assertEqual(
            state.product_routing_observed_trace,
            ["entry.model"],
        )
        self.assertTrue(state.expected_product_routing_response)

    def test_service_policy_does_not_append_fallback_model_lookup_trace_when_step_has_no_post_trace(self):
        plan = {
            "enabled": True,
            "result": ROUTING_RESULT_HOME,
            "trace": ["entry.model", "scene.family", "purchase.self_buy"],
            "summary": "entry.model -> scene.family -> purchase.self_buy -> 家用 + 可直接确认机型",
            "steps": [
                {
                    "prompt_key": "brand_or_series",
                    "prompt": PROMPT_BRAND_OR_SERIES,
                    "answer_key": "entry.model",
                    "answer_value": "KF66/200L-MI(E4)",
                    "answer_instruction": "自然提供一个具体型号，不要说自己不知道。",
                }
            ],
        }
        scenario = build_scenario_with_routing(plan)
        policy = ServiceDialoguePolicy(ok_prefix_probability=0.0, rng=random.Random(0))
        state = ServiceRuntimeState(
            expected_product_routing_response=True,
            product_routing_step_index=0,
            product_routing_observed_trace=[],
        )

        result = policy.respond(
            scenario=scenario,
            transcript=[
                DialogueTurn(speaker="service", text=PROMPT_BRAND_OR_SERIES, round_index=2),
                DialogueTurn(speaker="user", text="型号是KF66/200L-MI(E4)", round_index=3),
            ],
            collected_slots={
                "issue_description": "热水不稳定",
                "surname": "",
                "phone": "",
                "address": "",
                "request_type": "fault",
                "phone_contactable": "",
                "phone_contact_owner": "",
                "phone_collection_attempts": "",
                "product_arrived": "",
                "product_routing_result": "",
            },
            runtime_state=state,
        )

        self.assertEqual(result.reply, PROMPT_USAGE_SCENE)
        self.assertEqual(state.product_routing_observed_trace, ["entry.model"])

    def test_service_policy_inserts_routing_between_opening_and_fault_question(self):
        plan = {
            "enabled": True,
            "result": ROUTING_RESULT_BUILDING,
            "trace": ["entry.unknown", "scene.villa_apartment_barber"],
            "summary": "entry.unknown -> scene.villa_apartment_barber -> 楼宇 + 可直接确认机型",
            "steps": [
                {
                    "prompt_key": "brand_or_series",
                    "prompt": PROMPT_BRAND_OR_SERIES,
                    "answer_key": "entry.unknown",
                    "answer_value": "不知道品牌或系列",
                    "answer_instruction": "自然表达自己不知道品牌或系列，或暂时提供不了。",
                },
                {
                    "prompt_key": "usage_scene",
                    "prompt": PROMPT_USAGE_SCENE,
                    "answer_key": "scene.villa_apartment_barber",
                    "answer_value": "理发店使用",
                    "answer_instruction": "自然表达空气能是在别墅、公寓或理发店中的一个场所使用。",
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
        self.assertEqual(routing_step_2.reply, PROMPT_USAGE_SCENE)
        self.assertEqual(state.product_routing_step_index, 0)
        self.assertEqual(state.product_routing_observed_trace, ["entry.unknown"])
        self.assertEqual(
            scenario.hidden_context["product_routing_plan"]["steps"][0]["answer_key"],
            "scene.villa_apartment_barber",
        )

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
                DialogueTurn(speaker="service", text=PROMPT_USAGE_SCENE, round_index=3),
                DialogueTurn(speaker="user", text="理发店使用。", round_index=4),
            ],
            collected_slots=collected_slots,
            runtime_state=state,
        )
        self.assertEqual(post_routing.reply, "请问空气能热水器现在是出现了什么问题？")
        self.assertEqual(post_routing.slot_updates["product_routing_result"], ROUTING_RESULT_BUILDING)
        self.assertTrue(state.product_routing_completed)

    def test_service_policy_preserves_planned_family_scene_after_unknown_entry(self):
        plan = {
            "enabled": True,
            "result": ROUTING_RESULT_HOME,
            "trace": ["entry.unknown", "scene.family", "purchase.self_buy"],
            "summary": "entry.unknown -> scene.family -> purchase.self_buy -> 家用 + 可直接确认机型",
            "steps": [
                {
                    "prompt_key": "brand_or_series",
                    "prompt": PROMPT_BRAND_OR_SERIES,
                    "answer_key": "entry.unknown",
                    "answer_value": "不知道品牌或系列",
                    "answer_instruction": "自然表达自己不知道品牌或系列，或暂时提供不了。",
                },
                {
                    "prompt_key": "usage_scene",
                    "prompt": PROMPT_USAGE_SCENE,
                    "answer_key": "scene.family",
                    "answer_value": "家庭使用",
                    "answer_instruction": "自然表达空气能是在家庭场所使用。",
                },
                {
                    "prompt_key": "purchase_or_property",
                    "prompt": PROMPT_PURCHASE_OR_PROPERTY,
                    "answer_key": "purchase.self_buy",
                    "answer_value": "自己购买",
                    "answer_instruction": "自然表达机器是自己购买的。",
                },
            ],
        }
        scenario = build_scenario_with_routing(plan)
        policy = ServiceDialoguePolicy(ok_prefix_probability=0.0, rng=random.Random(0))
        state = ServiceRuntimeState(expected_product_routing_response=True)
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

        usage_scene_step = policy.respond(
            scenario=scenario,
            transcript=[
                DialogueTurn(speaker="service", text=PROMPT_BRAND_OR_SERIES, round_index=3),
                DialogueTurn(speaker="user", text="只知道是美的的。", round_index=4),
            ],
            collected_slots=collected_slots,
            runtime_state=state,
        )

        self.assertEqual(usage_scene_step.reply, PROMPT_USAGE_SCENE)
        self.assertEqual(
            scenario.hidden_context["product_routing_plan"]["steps"][0]["answer_key"],
            "scene.family",
        )

        purchase_step = policy.respond(
            scenario=scenario,
            transcript=[
                DialogueTurn(speaker="service", text=PROMPT_BRAND_OR_SERIES, round_index=3),
                DialogueTurn(speaker="user", text="只知道是美的的。", round_index=4),
                DialogueTurn(speaker="service", text=PROMPT_USAGE_SCENE, round_index=4),
                DialogueTurn(speaker="user", text="家里用的。", round_index=5),
            ],
            collected_slots=collected_slots,
            runtime_state=state,
        )

        self.assertEqual(purchase_step.reply, PROMPT_PURCHASE_OR_PROPERTY)
        self.assertEqual(
            scenario.hidden_context["product_routing_plan"]["steps"][0]["answer_key"],
            "purchase.self_buy",
        )

    def test_service_policy_history_device_denial_continues_to_planned_purchase_step(self):
        plan = {
            "enabled": True,
            "result": ROUTING_RESULT_HOME,
            "trace": [
                "entry.unknown",
                "scene.family",
                "history_device.no_unknown",
                "purchase.property_bundle",
                "property_year.before_2021",
            ],
            "summary": (
                "entry.unknown -> scene.family -> history_device.no_unknown -> "
                "purchase.property_bundle -> property_year.before_2021 -> 家用 + 可直接确认机型"
            ),
            "steps": [
                {
                    "prompt_key": "brand_or_series",
                    "prompt": PROMPT_BRAND_OR_SERIES,
                    "answer_key": "entry.unknown",
                    "answer_value": "不知道品牌或系列",
                    "answer_instruction": "自然表达自己不知道品牌或系列。",
                },
                {
                    "prompt_key": "usage_scene",
                    "prompt": PROMPT_USAGE_SCENE,
                    "answer_key": "scene.family",
                    "answer_value": "家庭使用",
                    "answer_instruction": "自然表达空气能是在家庭场所使用。",
                },
                {
                    "prompt_key": "history_device_confirmation",
                    "prompt": "这边看到您2025年5月有购买一台煤改电家用空气能热水机，请问是这台吗？",
                    "answer_key": "history_device.no_unknown",
                    "answer_value": "不是或不清楚查询到的设备",
                    "answer_instruction": "自然表达不是查询到的那台设备。",
                },
                {
                    "prompt_key": "purchase_or_property",
                    "prompt": PROMPT_PURCHASE_OR_PROPERTY,
                    "answer_key": "purchase.property_bundle",
                    "answer_value": "楼盘配套赠送",
                    "answer_instruction": "自然表达机器是楼盘配套赠送的。",
                },
            ],
        }
        scenario = build_scenario_with_routing(plan)
        scenario.hidden_context["product_routing_initial_plan"] = plan
        scenario.hidden_context["product_routing_plan"] = {
            **plan,
            "trace": ["entry.unknown", "scene.family"],
            "steps": plan["steps"][2:],
            "summary": "entry.unknown -> scene.family",
            "result": "",
        }
        scenario.hidden_context["air_energy_history_device"] = {"brand": "煤改电"}
        policy = ServiceDialoguePolicy(ok_prefix_probability=0.0, rng=random.Random(0))
        state = ServiceRuntimeState(
            expected_product_routing_response=True,
            product_routing_observed_trace=["entry.unknown", "scene.family"],
        )

        result = policy.respond(
            scenario=scenario,
            transcript=[
                DialogueTurn(
                    speaker="service",
                    text="这边看到您2025年5月有购买一台煤改电家用空气能热水机，请问是这台吗？",
                    round_index=5,
                ),
                DialogueTurn(speaker="user", text="呃，不是这台。", round_index=6),
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

        self.assertEqual(result.reply, PROMPT_PURCHASE_OR_PROPERTY)
        self.assertEqual(
            state.product_routing_observed_trace,
            ["entry.unknown", "scene.family", "history_device.no_unknown"],
        )
        self.assertEqual(
            scenario.hidden_context["product_routing_plan"]["steps"][0]["answer_key"],
            "purchase.property_bundle",
        )

    def test_service_policy_history_device_confirmation_prefers_model_intent(self):
        def fake_routing_inference(*, prompt_key: str, user_text: str, user_round_index: int):
            self.assertEqual(prompt_key, "history_device_confirmation")
            self.assertEqual(user_text, "呃，不是这台。")
            return {
                "prompt_key": "history_device_confirmation",
                "answer_key": "history_device.no_unknown",
            }

        plan = {
            "enabled": True,
            "result": ROUTING_RESULT_HOME,
            "trace": [
                "entry.unknown",
                "scene.family",
                "history_device.no_unknown",
                "purchase.self_buy",
            ],
            "summary": (
                "entry.unknown -> scene.family -> history_device.no_unknown -> "
                "purchase.self_buy -> 家用 + 可直接确认机型"
            ),
            "steps": [
                {
                    "prompt_key": "brand_or_series",
                    "prompt": PROMPT_BRAND_OR_SERIES,
                    "answer_key": "entry.unknown",
                    "answer_value": "不知道品牌或系列",
                    "answer_instruction": "自然表达自己不知道品牌或系列。",
                },
                {
                    "prompt_key": "usage_scene",
                    "prompt": PROMPT_USAGE_SCENE,
                    "answer_key": "scene.family",
                    "answer_value": "家庭使用",
                    "answer_instruction": "自然表达空气能是在家庭场所使用。",
                },
                {
                    "prompt_key": "history_device_confirmation",
                    "prompt": "这边看到您2025年5月有购买一台煤改电家用空气能热水机，请问是这台吗？",
                    "answer_key": "history_device.no_unknown",
                    "answer_value": "不是或不清楚查询到的设备",
                    "answer_instruction": "自然表达不是查询到的那台设备。",
                },
                {
                    "prompt_key": "purchase_or_property",
                    "prompt": PROMPT_PURCHASE_OR_PROPERTY,
                    "answer_key": "purchase.self_buy",
                    "answer_value": "自己购买",
                    "answer_instruction": "自然表达机器是自己购买的。",
                },
            ],
        }
        scenario = build_scenario_with_routing(plan)
        scenario.hidden_context["product_routing_initial_plan"] = plan
        scenario.hidden_context["product_routing_plan"] = {
            **plan,
            "trace": ["entry.unknown", "scene.family"],
            "steps": plan["steps"][2:],
            "summary": "entry.unknown -> scene.family",
            "result": "",
        }
        policy = ServiceDialoguePolicy(
            ok_prefix_probability=0.0,
            rng=random.Random(0),
            product_routing_intent_inference_callback=fake_routing_inference,
        )
        state = ServiceRuntimeState(
            expected_product_routing_response=True,
            product_routing_observed_trace=["entry.unknown", "scene.family"],
        )

        result = policy.respond(
            scenario=scenario,
            transcript=[
                DialogueTurn(
                    speaker="service",
                    text="这边看到您2025年5月有购买一台煤改电家用空气能热水机，请问是这台吗？",
                    round_index=5,
                ),
                DialogueTurn(speaker="user", text="呃，不是这台。", round_index=6),
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

        self.assertEqual(result.reply, PROMPT_PURCHASE_OR_PROPERTY)
        self.assertTrue(policy.last_used_model_intent_inference)
        self.assertEqual(
            state.product_routing_observed_trace,
            ["entry.unknown", "scene.family", "history_device.no_unknown"],
        )

    def test_service_policy_history_device_affirmation_uses_model_yes_intent(self):
        def fake_routing_inference(*, prompt_key: str, user_text: str, user_round_index: int):
            self.assertEqual(prompt_key, "history_device_confirmation")
            self.assertEqual(user_text, "啊，对对对，买了五六年了。")
            return {
                "prompt_key": "history_device_confirmation",
                "answer_key": "history_device.yes",
            }

        plan = {
            "enabled": True,
            "result": ROUTING_RESULT_HOME,
            "trace": ["entry.unknown", "scene.family", "history_device.yes"],
            "summary": "entry.unknown -> scene.family -> history_device.yes -> 家用 + 可直接确认机型",
            "steps": [
                {
                    "prompt_key": "history_device_confirmation",
                    "prompt": "这边看到您2019年4月有购买一台美的家用空气能热水机，请问是这台吗？",
                    "answer_key": "history_device.yes",
                    "answer_value": "是查询到的这台设备",
                    "answer_instruction": "自然确认就是查询到的历史设备。",
                },
            ],
        }
        scenario = build_scenario_with_routing(plan)
        scenario.hidden_context["product_routing_initial_plan"] = plan
        scenario.hidden_context["product_routing_plan"] = {
            **plan,
            "trace": ["entry.unknown", "scene.family"],
            "steps": plan["steps"],
            "summary": "entry.unknown -> scene.family",
            "result": "",
        }
        policy = ServiceDialoguePolicy(
            ok_prefix_probability=0.0,
            rng=random.Random(0),
            product_routing_intent_inference_callback=fake_routing_inference,
        )
        state = ServiceRuntimeState(
            expected_product_routing_response=True,
            product_routing_observed_trace=["entry.unknown", "scene.family"],
        )

        result = policy.respond(
            scenario=scenario,
            transcript=[
                DialogueTurn(
                    speaker="service",
                    text="这边看到您2019年4月有购买一台美的家用空气能热水机，请问是这台吗？",
                    round_index=5,
                ),
                DialogueTurn(speaker="user", text="啊，对对对，买了五六年了。", round_index=6),
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

        self.assertNotEqual(result.reply, PROMPT_PURCHASE_OR_PROPERTY)
        self.assertEqual(result.reply, "请问空气能热水器现在是出现了什么问题？")
        self.assertTrue(policy.last_used_model_intent_inference)
        self.assertEqual(
            state.product_routing_observed_trace,
            ["entry.unknown", "scene.family", "history_device.yes"],
        )

    def test_service_policy_treats_generic_midea_brand_as_unknown_entry(self):
        plan = {
            "enabled": True,
            "result": ROUTING_RESULT_BUILDING,
            "trace": ["entry.unknown", "scene.other_unknown"],
            "summary": "entry.unknown -> scene.other_unknown -> 楼宇 + 可直接确认机型",
            "steps": [
                {
                    "prompt_key": "brand_or_series",
                    "prompt": PROMPT_BRAND_OR_SERIES,
                    "answer_key": "entry.unknown",
                    "answer_value": "不知道品牌或系列",
                    "answer_instruction": "自然表达自己不知道品牌或系列、暂时提供不了，或者只知道是美的。",
                },
                {
                    "prompt_key": "usage_scene",
                    "prompt": PROMPT_USAGE_SCENE,
                    "answer_key": "scene.other_unknown",
                    "answer_value": "不清楚具体使用场所",
                    "answer_instruction": "自然表达空气能是在其他地方使用，或者自己不清楚具体场所。",
                },
            ],
        }
        scenario = build_scenario_with_routing(plan)
        policy = ServiceDialoguePolicy(ok_prefix_probability=0.0, rng=random.Random(0))
        state = ServiceRuntimeState(
            expected_product_routing_response=True,
            product_routing_step_index=0,
        )

        result = policy.respond(
            scenario=scenario,
            transcript=[
                DialogueTurn(speaker="service", text=PROMPT_BRAND_OR_SERIES, round_index=2),
                DialogueTurn(speaker="user", text="美的", round_index=3),
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
        self.assertEqual(state.product_routing_observed_trace, ["entry.unknown"])
        self.assertTrue(state.expected_product_routing_response)

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
            "非常抱歉，给您添麻烦了，我帮您安排售后处理，请问您的空气能具体是什么品牌或系列的呢？",
        )

    def test_service_policy_routes_unknown_usage_scene_to_building(self):
        plan = {
            "enabled": True,
            "result": ROUTING_RESULT_BUILDING,
            "trace": ["entry.unknown", "scene.other_unknown"],
            "summary": "entry.unknown -> scene.other_unknown -> 楼宇 + 可直接确认机型",
            "steps": [
                {
                    "prompt_key": "brand_or_series",
                    "prompt": PROMPT_BRAND_OR_SERIES,
                    "answer_key": "entry.unknown",
                    "answer_value": "不知道品牌或系列",
                    "answer_instruction": "自然表达自己不知道品牌或系列，或暂时提供不了。",
                },
                {
                    "prompt_key": "usage_scene",
                    "prompt": PROMPT_USAGE_SCENE,
                    "answer_key": "scene.other_unknown",
                    "answer_value": "不清楚具体使用场所",
                    "answer_instruction": "自然表达空气能是在其他地方使用，或者自己不清楚具体场所。",
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
                DialogueTurn(speaker="service", text=PROMPT_USAGE_SCENE, round_index=3),
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

        self.assertEqual(result.reply, "请问空气能热水器现在是出现了什么问题？")
        self.assertEqual(state.product_routing_observed_trace, ["entry.unknown", "scene.other_unknown"])
        self.assertEqual(
            scenario.hidden_context["product_routing_trace"],
            ["entry.unknown", "scene.other_unknown"],
        )

    def test_service_policy_stops_at_building_when_bare_scene_negative(self):
        plan = {
            "enabled": True,
            "result": ROUTING_RESULT_BUILDING,
            "trace": ["entry.unknown", "scene.other_unknown"],
            "summary": "entry.unknown -> scene.other_unknown -> 楼宇 + 可直接确认机型",
            "steps": [
                {
                    "prompt_key": "usage_scene",
                    "prompt": PROMPT_USAGE_SCENE,
                    "answer_key": "scene.other_unknown",
                    "answer_value": "不清楚具体使用场所",
                    "answer_instruction": "自然表达空气能是在其他地方使用，或者自己不清楚具体场所。",
                }
            ],
        }
        scenario = build_scenario_with_routing(plan)
        policy = ServiceDialoguePolicy(ok_prefix_probability=0.0, rng=random.Random(0))
        state = ServiceRuntimeState(
            expected_product_routing_response=True,
            product_routing_step_index=0,
            product_routing_observed_trace=["entry.unknown"],
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
            ["entry.unknown", "scene.other_unknown"],
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
            product_routing_observed_trace=["entry.unknown", "scene.family", "purchase.property_bundle"],
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
            ["entry.unknown", "scene.family", "purchase.property_bundle", "property_year.unknown"],
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
