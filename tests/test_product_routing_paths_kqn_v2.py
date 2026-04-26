from __future__ import annotations

import re
import unittest
from pathlib import Path
from typing import Any

from css_data_synthesis_test.product_routing import (
    ROUTING_RESULT_BUILDING,
    ROUTING_RESULT_DIRECT,
    ROUTING_RESULT_HOME,
    ROUTING_RESULT_HUMAN,
    next_product_routing_steps_from_observed_trace,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent
PATHS_MD = PROJECT_ROOT / "adds" / "product_routing_paths_kqn_v2.md"
PATH_LINE_PATTERN = re.compile(r"^- `(?P<path_id>P\d{3})`: (?P<path>.+)$")

SEGMENT_TO_ANSWER_KEY_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"^品牌=COLMO$"), "brand_series.colmo"),
    (re.compile(r"^品牌=(酷风|小天鹅)$"), "brand_series.cooling_or_little_swan"),
    (re.compile(r"^系列=(真暖|真省|雪焰|暖家|煤改电|真享)$"), "brand_series.home_series"),
    (re.compile(r"^系列=烈焰$"), "brand_series.lieyan"),
    (re.compile(r"^(不清楚/提供不了|只知道是美的)$"), "entry.unknown"),
    (re.compile(r"^提供型号$"), "entry.model"),
    (re.compile(r"^家庭使用$"), "scene.family"),
    (re.compile(r"^(别墅使用|公寓使用|理发店使用)$"), "scene.villa_apartment_barber"),
    (re.compile(r"^(其他场所|不清楚使用场所)$"), "scene.other_unknown"),
    (re.compile(r"^用户确认是查询到的设备$"), "history_device.yes"),
    (re.compile(r"^用户否定/不清楚$"), "history_device.no_unknown"),
    (re.compile(r"^自己购买$"), "purchase.self_buy"),
    (re.compile(r"^不知道是否自己购买$"), "purchase.unknown"),
    (re.compile(r"^楼盘配套$"), "purchase.property_bundle"),
    (re.compile(r"^21年之前$"), "property_year.before_2021"),
    (re.compile(r"^21年之后$"), "property_year.after_2021"),
    (re.compile(r"^楼盘年份不清楚$"), "property_year.unknown"),
]

RESULT_MAPPING = {
    "家用+可直接确认机型": ROUTING_RESULT_HOME,
    "楼宇+可直接确认机型": ROUTING_RESULT_BUILDING,
    "转人工": ROUTING_RESULT_HUMAN,
    "可直接确认归属与机型": ROUTING_RESULT_DIRECT,
}

ANSWER_KEY_TO_PROMPT_KEY = {
    "entry.unknown": "brand_or_series",
    "entry.model": "brand_or_series",
    "brand_series.colmo": "brand_or_series",
    "brand_series.cooling_or_little_swan": "brand_or_series",
    "brand_series.home_series": "brand_or_series",
    "brand_series.lieyan": "brand_or_series",
    "scene.family": "usage_scene",
    "scene.villa_apartment_barber": "usage_scene",
    "scene.other_unknown": "usage_scene",
    "history_device.yes": "history_device_confirmation",
    "history_device.no_unknown": "history_device_confirmation",
    "purchase.self_buy": "purchase_or_property",
    "purchase.unknown": "purchase_or_property",
    "purchase.property_bundle": "purchase_or_property",
    "property_year.before_2021": "property_year",
    "property_year.after_2021": "property_year",
    "property_year.unknown": "property_year",
}

CONTEXT_SEGMENTS = {
    "有空气能历史设备": {"air_energy_history_device": {"source": "path_test"}},
    "无空气能历史设备": {},
}


def _normalize_result_label(label: str) -> str:
    return re.sub(r"\s+", "", str(label or "").strip())


def _segment_to_answer_key(segment: str) -> str:
    normalized = str(segment or "").strip()
    for pattern, answer_key in SEGMENT_TO_ANSWER_KEY_PATTERNS:
        if pattern.fullmatch(normalized):
            return answer_key
    raise AssertionError(f"未覆盖的路径片段: {normalized}")


def _hidden_context_from_segments(segments: list[str]) -> dict[str, Any]:
    hidden_context: dict[str, Any] = {}
    for segment in segments:
        if segment in CONTEXT_SEGMENTS:
            hidden_context = dict(CONTEXT_SEGMENTS[segment])
    return hidden_context


def _parse_paths_from_markdown() -> list[dict[str, object]]:
    cases: list[dict[str, object]] = []
    for raw_line in PATHS_MD.read_text(encoding="utf-8").splitlines():
        matched = PATH_LINE_PATTERN.match(raw_line.strip())
        if not matched:
            continue
        path_id = matched.group("path_id")
        raw_path = matched.group("path")
        segments = [segment.strip() for segment in raw_path.split("->")]
        if len(segments) < 2:
            raise AssertionError(f"{path_id} 路径定义无效: {raw_path}")
        if segments[0] != "询问品牌或系列":
            raise AssertionError(f"{path_id} 起始片段不是“询问品牌或系列”: {raw_path}")

        result_label = _normalize_result_label(segments[-1])
        expected_result = RESULT_MAPPING.get(result_label)
        if expected_result is None:
            raise AssertionError(f"{path_id} 终点状态未覆盖: {segments[-1]}")

        decision_segments = [
            segment for segment in segments[1:-1] if segment not in CONTEXT_SEGMENTS
        ]
        trace = [_segment_to_answer_key(segment) for segment in decision_segments]
        cases.append(
            {
                "path_id": path_id,
                "raw_path": raw_path,
                "trace": trace,
                "hidden_context": _hidden_context_from_segments(segments),
                "expected_result": expected_result,
            }
        )
    return cases


class ProductRoutingPathsKqnV2Tests(unittest.TestCase):
    def test_markdown_contains_all_58_declared_paths(self):
        cases = _parse_paths_from_markdown()

        self.assertEqual(len(cases), 58)

    def test_all_58_paths_resolve_to_expected_terminal_result(self):
        for case in _parse_paths_from_markdown():
            trace = list(case["trace"])
            hidden_context = dict(case["hidden_context"])
            expected_result = str(case["expected_result"])

            with self.subTest(path_id=case["path_id"], raw_path=case["raw_path"]):
                next_steps, result = next_product_routing_steps_from_observed_trace(
                    trace,
                    hidden_context=hidden_context,
                )
                self.assertEqual(result, expected_result)
                self.assertEqual(next_steps, [])

    def test_all_58_paths_follow_expected_prompt_progression(self):
        for case in _parse_paths_from_markdown():
            trace = list(case["trace"])
            hidden_context = dict(case["hidden_context"])
            if len(trace) < 2:
                continue

            with self.subTest(path_id=case["path_id"], raw_path=case["raw_path"]):
                for index in range(1, len(trace)):
                    next_answer_key = trace[index]
                    prefix = trace[:index]
                    next_steps, result = next_product_routing_steps_from_observed_trace(
                        prefix,
                        hidden_context=hidden_context,
                    )
                    expected_prompt_key = ANSWER_KEY_TO_PROMPT_KEY[next_answer_key]
                    self.assertEqual(result, "", msg=f"prefix={prefix}")
                    self.assertGreaterEqual(len(next_steps), 1, msg=f"prefix={prefix}")
                    self.assertEqual(next_steps[0]["prompt_key"], expected_prompt_key, msg=f"prefix={prefix}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
