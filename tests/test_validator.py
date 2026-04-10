from __future__ import annotations

import unittest

from multi_agent_data_synthesis.schemas import DialogueSample, DialogueTurn
from multi_agent_data_synthesis.validator import validate_dialogue


class ValidatorTests(unittest.TestCase):
    def test_accepts_user_first_dialogue(self):
        sample = DialogueSample(
            scenario_id="case_000",
            status="completed",
            rounds_used=2,
            transcript=[
                DialogueTurn(speaker="user", text="美的空气能热水器需要维修", round_index=1),
                DialogueTurn(speaker="service", text="好的，请问空气能热水器现在是出现了什么问题？", round_index=1),
            ],
            collected_slots={},
            missing_slots=[],
            scenario={},
            validation={},
        )

        validation = validate_dialogue(sample)

        self.assertTrue(validation["passed"])

    def test_accepts_service_first_dialogue(self):
        sample = DialogueSample(
            scenario_id="case_001",
            status="completed",
            rounds_used=2,
            transcript=[
                DialogueTurn(speaker="service", text="您好，很高兴为您服务，请问是美的空气能热水器需要维修吗？", round_index=1),
                DialogueTurn(speaker="user", text="对，热水器加热很慢。", round_index=1),
                DialogueTurn(speaker="service", text="好的，请问您贵姓", round_index=2),
                DialogueTurn(speaker="user", text="我姓张。", round_index=2),
            ],
            collected_slots={"surname": "张"},
            missing_slots=[],
            scenario={},
            validation={},
        )

        validation = validate_dialogue(sample)

        self.assertTrue(validation["passed"])

    def test_accepts_chinese_speaker_labels(self):
        sample = DialogueSample(
            scenario_id="case_002",
            status="completed",
            rounds_used=2,
            transcript=[
                DialogueTurn(speaker="客服", text="您好，很高兴为您服务。", round_index=1),
                DialogueTurn(speaker="用户", text="对，需要报修。", round_index=1),
            ],
            collected_slots={},
            missing_slots=[],
            scenario={},
            validation={},
        )

        validation = validate_dialogue(sample)

        self.assertTrue(validation["passed"])

    def test_rejects_issue_repetition_after_address_confirmation(self):
        sample = DialogueSample(
            scenario_id="case_003",
            status="completed",
            rounds_used=8,
            transcript=[
                DialogueTurn(speaker="service", text="跟您确认一下，地址是山东省济南市历下区泉城路218号贵和购物中心公寓楼12层1203室，对吗？", round_index=7),
                DialogueTurn(speaker="user", text="对，是的，现在热水器显示E4故障代码，没法加热水。", round_index=8),
            ],
            collected_slots={"address": "山东省济南市历下区泉城路218号贵和购物中心公寓楼12层1203室"},
            missing_slots=[],
            scenario={},
            validation={},
        )

        validation = validate_dialogue(sample)

        self.assertFalse(validation["passed"])
        self.assertIn("user introduced unrelated or repeated details after address confirmation at round 8", validation["issues"])

    def test_rejects_address_repetition_during_closing_ack(self):
        sample = DialogueSample(
            scenario_id="case_004",
            status="completed",
            rounds_used=9,
            transcript=[
                DialogueTurn(speaker="service", text="好的，您的工单已受理成功，明天上午10点前会有专人与您确认服务时间。", round_index=8),
                DialogueTurn(speaker="user", text="山东省济南市历下区泉城路218号贵和购物中心公寓楼12层1203室。", round_index=9),
            ],
            collected_slots={"address": "山东省济南市历下区泉城路218号贵和购物中心公寓楼12层1203室"},
            missing_slots=[],
            scenario={},
            validation={},
        )

        validation = validate_dialogue(sample)

        self.assertFalse(validation["passed"])
        self.assertIn("user repeated prior details during closing acknowledgement at round 9", validation["issues"])

    def test_rejects_repeated_off_topic_surname_collection(self):
        sample = DialogueSample(
            scenario_id="case_005",
            status="completed",
            rounds_used=8,
            transcript=[
                DialogueTurn(speaker="service", text="好的，请问您贵姓", round_index=3),
                DialogueTurn(speaker="user", text="对，到货了，但是还没安装。", round_index=3),
                DialogueTurn(speaker="service", text="好的，请问您贵姓", round_index=4),
                DialogueTurn(speaker="user", text="对，到货了，但是还没安装。", round_index=4),
                DialogueTurn(speaker="service", text="好的，请问您贵姓", round_index=5),
                DialogueTurn(speaker="user", text="啊，对，就是我这边买了一个美的空气能热水机，还没装。", round_index=5),
            ],
            collected_slots={},
            missing_slots=["surname"],
            scenario={},
            validation={},
        )

        validation = validate_dialogue(sample)

        self.assertFalse(validation["passed"])
        self.assertIn("user repeated the same off-topic reply during surname collection at round 4", validation["issues"])
        self.assertIn("user still did not answer surname after 3 prompts at round 5", validation["issues"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
