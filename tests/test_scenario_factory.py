from __future__ import annotations

import random
import unittest

from css_data_synthesis_test.scenario_factory import ScenarioFactory
from css_data_synthesis_test.schemas import Scenario


def build_scenarios() -> list[Scenario]:
    return [
        Scenario.from_dict(
            {
                "scenario_id": "fault_seed",
                "product": {
                    "brand": "美的",
                    "category": "空气能热水器",
                    "model": "F-1",
                    "purchase_channel": "京东",
                },
                "customer": {
                    "full_name": "张三",
                    "surname": "张",
                    "phone": "13800000001",
                    "address": "上海市浦东新区1号",
                    "persona": "普通用户",
                    "speech_style": "简洁",
                },
                "request": {
                    "request_type": "fault",
                    "issue": "不加热",
                    "desired_resolution": "安排维修",
                    "availability": "周末",
                },
                "required_slots": ["issue_description", "surname", "phone", "address", "request_type"],
            }
        ),
        Scenario.from_dict(
            {
                "scenario_id": "installation_seed",
                "product": {
                    "brand": "美的",
                    "category": "空气能热水机",
                    "model": "I-1",
                    "purchase_channel": "天猫",
                },
                "customer": {
                    "full_name": "李四",
                    "surname": "李",
                    "phone": "13800000002",
                    "address": "杭州市余杭区2号",
                    "persona": "普通用户",
                    "speech_style": "简洁",
                },
                "request": {
                    "request_type": "installation",
                    "issue": "预约安装",
                    "desired_resolution": "安排安装",
                    "availability": "周末",
                },
                "required_slots": ["issue_description", "surname", "phone", "address", "request_type"],
            }
        ),
    ]


class ScenarioFactoryTests(unittest.TestCase):
    def test_load_hydrates_random_call_start_time(self):
        factory = ScenarioFactory(rng=random.Random(0))
        scenarios = build_scenarios()

        hydrated = factory.expand_to_count(scenarios, 2)

        self.assertEqual(len(hydrated), 2)
        self.assertRegex(hydrated[0].call_start_time, r"^\d{2}:\d{2}:\d{2}$")
        self.assertRegex(hydrated[1].call_start_time, r"^\d{2}:\d{2}:\d{2}$")
        self.assertNotEqual(hydrated[0].call_start_time, "")
        self.assertNotEqual(hydrated[1].call_start_time, "")
        self.assertNotEqual(hydrated[0].call_start_time, hydrated[1].call_start_time)

    def test_preserves_explicit_call_start_time(self):
        factory = ScenarioFactory(rng=random.Random(0))
        scenario_data = build_scenarios()[0].to_dict()
        scenario_data["call_start_time"] = "20:06:02"

        hydrated = factory.expand_to_count([Scenario.from_dict(scenario_data)], 1)

        self.assertEqual(hydrated[0].call_start_time, "20:06:02")

    def test_expand_can_force_fault_probability(self):
        factory = ScenarioFactory(installation_request_probability=0.0, rng=random.Random(0))
        expanded = factory.expand_to_count(build_scenarios(), 6)

        self.assertEqual(len(expanded), 6)
        self.assertTrue(all(s.request.request_type == "fault" for s in expanded))
        self.assertTrue(all(s.call_start_time for s in expanded))

    def test_expand_can_force_installation_probability(self):
        factory = ScenarioFactory(installation_request_probability=1.0, rng=random.Random(0))
        expanded = factory.expand_to_count(build_scenarios(), 6)

        self.assertEqual(len(expanded), 6)
        self.assertTrue(all(s.request.request_type == "installation" for s in expanded))
        self.assertTrue(all(s.call_start_time for s in expanded))


if __name__ == "__main__":
    unittest.main(verbosity=2)
