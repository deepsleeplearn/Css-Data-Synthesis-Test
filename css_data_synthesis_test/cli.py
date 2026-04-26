from __future__ import annotations

import asyncio
import argparse
import hashlib
import json
from dataclasses import replace
from pathlib import Path
from typing import Any, Iterable

from css_data_synthesis_test.config import load_config
from css_data_synthesis_test.exporter import write_json, write_jsonl, write_sqlite
from css_data_synthesis_test.hidden_settings_tool import HiddenSettingsTool
from css_data_synthesis_test.llm import OpenAIChatClient
from css_data_synthesis_test.agents import ServiceAgent
from css_data_synthesis_test.manual_test import (
    _sanitize_manual_user_text,
    default_manual_test_output_path,
    load_manual_test_scenario,
    run_manual_test_session,
)
from css_data_synthesis_test.orchestrator import DialogueOrchestrator
from css_data_synthesis_test.product_routing import ensure_product_routing_plan
from css_data_synthesis_test.scenario_factory import ScenarioFactory


DEFAULT_SCENARIO_FILE = Path("data/seed_scenarios.json")
DEFAULT_JSONL_OUTPUT = Path("outputs/dialogues.jsonl")
DEFAULT_JSON_OUTPUT = Path("outputs/dialogues.json")
DEFAULT_HIDDEN_SETTINGS_OUTPUT = Path("outputs/generated_hidden_scenarios.json")
DEFAULT_SQLITE_OUTPUT = Path("outputs/generated_dialogues.sqlite3")
MANUAL_CONTACT_PHONE_PREFIXES = (
    "130",
    "131",
    "132",
    "133",
    "134",
    "135",
    "136",
    "137",
    "138",
    "139",
    "145",
    "146",
    "147",
    "148",
    "149",
    "150",
    "151",
    "152",
    "153",
    "155",
    "156",
    "157",
    "158",
    "159",
    "166",
    "167",
    "170",
    "171",
    "172",
    "173",
    "175",
    "176",
    "177",
    "178",
    "180",
    "181",
    "182",
    "183",
    "184",
    "185",
    "186",
    "187",
    "188",
    "189",
    "191",
    "193",
    "195",
    "196",
    "198",
    "199",
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="多智能体家电客服对话数据生成器")
    subparsers = parser.add_subparsers(dest="command", required=True)

    generate_parser = subparsers.add_parser("generate", help="批量生成对话数据")
    generate_parser.add_argument(
        "--scenario-file",
        type=Path,
        default=DEFAULT_SCENARIO_FILE,
        help="场景配置 JSON 文件路径",
    )
    generate_parser.add_argument(
        "--count",
        type=int,
        default=None,
        help="需要生成的样本数，默认使用场景文件内全部样本",
    )
    generate_parser.add_argument(
        "--jsonl-output",
        type=Path,
        default=DEFAULT_JSONL_OUTPUT,
        help="JSONL 输出路径",
    )
    generate_parser.add_argument(
        "--json-output",
        type=Path,
        default=DEFAULT_JSON_OUTPUT,
        help="JSON 输出路径",
    )
    generate_parser.add_argument(
        "--write-output",
        action="store_true",
        help="显式启用文件输出；默认只在终端打印结果，不写入 outputs/ 或 data/",
    )
    generate_parser.add_argument(
        "--auto-hidden-settings",
        action="store_true",
        help="调用隐藏设定生成 TOOL，自动为 user_agent 生成并持久化隐藏设定",
    )
    generate_parser.add_argument(
        "--show-dialogue",
        action="store_true",
        help="生成对话时在终端打印每轮交互过程",
    )
    generate_parser.add_argument(
        "--show-persona",
        action="store_true",
        help="配合 --show-dialogue 使用，在终端额外打印初始用户画像与说话方式",
    )
    generate_parser.add_argument(
        "--concurrency",
        type=int,
        default=None,
        help="异步并发生成的任务数，默认使用配置中的 MAX_CONCURRENCY",
    )
    generate_parser.add_argument(
        "--persist-to-db",
        "-p",
        action="store_true",
        help="将生成的对话持久化到 SQLite 数据库（需配合 --write-output 使用）",
    )
    generate_parser.add_argument(
        "--db-output",
        type=Path,
        default=DEFAULT_SQLITE_OUTPUT,
        help=f"SQLite 输出路径，默认 {DEFAULT_SQLITE_OUTPUT}",
    )

    hidden_parser = subparsers.add_parser("generate-hidden-settings", help="仅生成隐藏设定")
    hidden_parser.add_argument(
        "--scenario-file",
        type=Path,
        default=DEFAULT_SCENARIO_FILE,
        help="场景配置 JSON 文件路径",
    )
    hidden_parser.add_argument(
        "--count",
        type=int,
        default=None,
        help="需要生成的场景数，默认使用场景文件内全部样本",
    )
    hidden_parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_HIDDEN_SETTINGS_OUTPUT,
        help="带隐藏设定的场景输出路径",
    )
    hidden_parser.add_argument(
        "--write-output",
        action="store_true",
        help="显式启用文件输出；默认只在终端打印结果，不写入 outputs/ 或 data/",
    )
    hidden_parser.add_argument(
        "--concurrency",
        type=int,
        default=None,
        help="异步并发生成的任务数，默认使用配置中的 MAX_CONCURRENCY",
    )

    interactive_parser = subparsers.add_parser(
        "interactive-test",
        help="手工输入用户话术，与现有客服状态机交互测试",
    )
    interactive_parser.add_argument(
        "--scenario-file",
        type=Path,
        default=DEFAULT_SCENARIO_FILE,
        help="场景配置 JSON 文件路径",
    )
    interactive_parser.add_argument(
        "--scenario-id",
        type=str,
        default="",
        help="指定要测试的 scenario_id，优先级高于 scenario-index",
    )
    interactive_parser.add_argument(
        "--scenario-index",
        type=int,
        default=0,
        help="指定要测试的场景下标，默认取第 1 个",
    )
    interactive_parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="测试结果 JSON 输出路径；需配合 --write-output 使用",
    )
    interactive_parser.add_argument(
        "--max-rounds",
        type=int,
        default=None,
        help="最大交互轮数，默认使用场景里的 max_turns",
    )
    interactive_parser.add_argument(
        "--auto-hidden-settings",
        action="store_true",
        help="先调用隐藏设定生成 TOOL，再进入手工交互测试",
    )
    interactive_parser.add_argument(
        "--write-output",
        action="store_true",
        help="显式启用文件输出；默认只在终端打印结果，不写入 outputs/ 或 data/",
    )
    interactive_parser.add_argument(
        "--show-address-state",
        action="store_true",
        help="手工测试时在地址采集/确认环节额外打印地址运行状态",
    )
    interactive_parser.add_argument(
        "--hide-address-state",
        action="store_true",
        help="手工测试时关闭地址采集/确认环节的地址运行状态打印",
    )
    interactive_parser.add_argument(
        "--show-final-slots",
        action="store_true",
        help="手工测试结束后在终端打印最终收集到的槽位信息",
    )

    return parser


def run_generate(args: argparse.Namespace) -> None:
    asyncio.run(run_generate_async(args))


async def run_generate_async(args: argparse.Namespace) -> None:
    config = _load_cli_config(write_output=args.write_output)
    factory = ScenarioFactory(
        installation_request_probability=config.installation_request_probability,
    )
    scenarios = factory.load_from_file(args.scenario_file)
    scenarios = factory.expand_to_count(scenarios, args.count)

    orchestrator = DialogueOrchestrator(
        config,
        auto_generate_hidden_settings=args.auto_hidden_settings,
        show_dialogue_progress=args.show_dialogue,
        show_persona_profile=args.show_persona,
    )
    concurrency = max(1, args.concurrency or config.max_concurrency)
    samples = await orchestrator.generate_dialogues_async(scenarios, concurrency=concurrency)

    if args.write_output:
        write_jsonl(samples, args.jsonl_output)
        write_json(samples, args.json_output)
        if args.persist_to_db:
            written = write_sqlite(samples, args.db_output)

    completed = sum(1 for sample in samples if sample.status == "completed")
    incomplete = sum(1 for sample in samples if sample.status == "incomplete")
    transferred = sum(1 for sample in samples if sample.status == "transferred")
    print(f"Generated {len(samples)} dialogues.")
    print(f"  completed:   {completed}")
    print(f"  incomplete:  {incomplete}")
    print(f"  transferred: {transferred}")
    if args.auto_hidden_settings:
        _print_utterance_reference_summary(
            sample.scenario for sample in samples
        )
    if args.write_output:
        print(f"JSONL output: {args.jsonl_output}")
        print(f"JSON output:  {args.json_output}")
        if args.persist_to_db:
            print(f"SQLite output: {args.db_output} ({written} records written)")
    else:
        print("File output disabled. Use --write-output to persist JSONL/JSON files.")
        if args.persist_to_db:
            print("Note: --persist-to-db has no effect without --write-output.")


def run_generate_hidden_settings(args: argparse.Namespace) -> None:
    asyncio.run(run_generate_hidden_settings_async(args))


async def run_generate_hidden_settings_async(args: argparse.Namespace) -> None:
    config = _load_cli_config(write_output=args.write_output)
    factory = ScenarioFactory(
        installation_request_probability=config.installation_request_probability,
    )
    scenarios = factory.load_from_file(args.scenario_file)
    scenarios = factory.expand_to_count(scenarios, args.count)

    tool = HiddenSettingsTool(OpenAIChatClient(config), config)
    concurrency = max(1, args.concurrency or config.max_concurrency)
    semaphore = asyncio.Semaphore(concurrency)

    async def generate_single(scenario):
        async with semaphore:
            generated = await tool.generate_for_scenario_async(
                scenario,
                use_utterance_reference=True,
            )
            return generated.to_dict()

    hydrated = list(await asyncio.gather(*(generate_single(scenario) for scenario in scenarios)))

    if args.write_output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(hydrated, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    print(f"Generated hidden settings for {len(hydrated)} scenarios.")
    _print_utterance_reference_summary(hydrated)
    if args.write_output:
        print(f"Output: {args.output}")
        print(f"History store: {config.hidden_settings_store}")
    else:
        print("File output disabled. Use --write-output to persist generated scenarios or history.")


def run_interactive_test(args: argparse.Namespace) -> None:
    config = _load_cli_config(write_output=args.write_output)
    scenario = load_manual_test_scenario(
        args.scenario_file,
        scenario_id=args.scenario_id,
        scenario_index=args.scenario_index,
    )
    if args.auto_hidden_settings:
        tool = HiddenSettingsTool(OpenAIChatClient(config), config)
        scenario = tool.generate_for_scenario(
            scenario,
            use_utterance_reference=True,
        )
    elif _manual_test_requires_generated_hidden_settings(scenario):
        scenario = _hydrate_manual_test_scenario_locally(scenario)
    scenario = _configure_manual_test_known_address(scenario)
    scenario.hidden_context["interactive_test_freeform"] = True
    scenario.hidden_context.update(
        {
            "product_routing_entry_weights": dict(config.product_routing_entry_weights),
            "product_routing_brand_series_weights": dict(config.product_routing_brand_series_weights),
            "product_routing_usage_scene_weights": dict(config.product_routing_usage_scene_weights),
            "product_routing_purchase_or_property_weights": dict(
                config.product_routing_purchase_or_property_weights
            ),
            "product_routing_property_year_weights": dict(config.product_routing_property_year_weights),
            "product_routing_history_confirmation_weights": dict(
                config.product_routing_history_confirmation_weights
            ),
        }
    )
    ensure_product_routing_plan(
        scenario.hidden_context,
        enabled=config.product_routing_enabled,
        apply_probability=config.product_routing_apply_probability,
        model_hint=scenario.product.model,
    )
    service_agent = ServiceAgent(
        OpenAIChatClient(config),
        model=config.service_agent_model,
        temperature=config.default_temperature,
        ok_prefix_probability=config.service_ok_prefix_probability,
        query_prefix_weights=config.service_query_prefix_weights,
        product_routing_enabled=config.product_routing_enabled,
        product_routing_apply_probability=config.product_routing_apply_probability,
    )

    output_path = None
    if args.write_output:
        output_path = args.output or default_manual_test_output_path(scenario.scenario_id)
    resolved_max_rounds = _resolve_interactive_max_rounds(
        args_max_rounds=args.max_rounds,
        scenario_max_turns=scenario.max_turns,
        config_max_rounds=config.max_rounds,
    )
    run_manual_test_session(
        scenario,
        output_path=output_path,
        max_rounds=resolved_max_rounds,
        ok_prefix_probability=config.service_ok_prefix_probability,
        policy=service_agent.policy,
        show_address_state=bool(args.show_address_state) and not bool(args.hide_address_state),
        show_final_slots=bool(args.show_final_slots),
    )


def _load_cli_config(*, write_output: bool):
    config = load_config()
    if write_output:
        return config
    return replace(config, hidden_settings_store=None)


def _utterance_reference_summary_line(scenario_payload: dict) -> str:
    scenario_id = str(scenario_payload.get("scenario_id", "")).strip() or "<unknown>"
    hidden_context = scenario_payload.get("hidden_context", {})
    if not isinstance(hidden_context, dict):
        hidden_context = {}
    source = str(hidden_context.get("utterance_reference_source", "model")).strip() or "model"
    if source != "library":
        return f"- {scenario_id}: 未参考话术库，直接走模型生成"

    intent = str(hidden_context.get("utterance_reference_intent", "")).strip()
    category = str(hidden_context.get("utterance_reference_category", "")).strip()
    summary = str(hidden_context.get("utterance_reference_summary", "")).strip()
    original = str(hidden_context.get("utterance_reference_original", "")).strip()
    details = " / ".join(part for part in (intent, category, summary) if part)
    if original:
        return f"- {scenario_id}: 参考话术库 -> {details} | 原话: {original}"
    return f"- {scenario_id}: 参考话术库 -> {details}"


def _print_utterance_reference_summary(scenarios: Iterable[Any]) -> None:
    payloads = [scenario for scenario in scenarios]
    if not payloads:
        return
    print("话术参考使用情况:")
    for scenario_payload in payloads:
        if hasattr(scenario_payload, "to_dict"):
            scenario_payload = scenario_payload.to_dict()
        print(_utterance_reference_summary_line(dict(scenario_payload)))


def _validate_output_flags(parser: argparse.ArgumentParser, args: argparse.Namespace) -> None:
    if getattr(args, "write_output", False):
        return
    if args.command == "generate":
        if args.jsonl_output != DEFAULT_JSONL_OUTPUT or args.json_output != DEFAULT_JSON_OUTPUT:
            parser.error("--jsonl-output/--json-output 需要配合 --write-output 使用。")
        if args.db_output != DEFAULT_SQLITE_OUTPUT:
            parser.error("--db-output 需要配合 --write-output 使用。")
    elif args.command == "generate-hidden-settings":
        if args.output != DEFAULT_HIDDEN_SETTINGS_OUTPUT:
            parser.error("--output 需要配合 --write-output 使用。")
    elif args.command == "interactive-test" and args.output is not None:
        parser.error("--output 需要配合 --write-output 使用。")


def _resolve_interactive_max_rounds(
    *,
    args_max_rounds: int | None,
    scenario_max_turns: int | None,
    config_max_rounds: int,
) -> int:
    if args_max_rounds:
        return int(args_max_rounds)
    if scenario_max_turns:
        return int(scenario_max_turns)
    return int(config_max_rounds)


def _manual_test_requires_generated_hidden_settings(scenario) -> bool:
    unknown_markers = {"", "未知", "unknown", "n/a", "na", "null", "none"}

    def has_known_value(value: str) -> bool:
        return str(value or "").strip().lower() not in unknown_markers

    customer = scenario.customer
    request = scenario.request
    required_customer_values = (
        customer.full_name,
        customer.surname,
        customer.phone,
        customer.address,
        customer.persona,
        customer.speech_style,
    )
    required_request_values = (
        request.issue,
        request.desired_resolution,
        request.availability,
    )
    if not all(has_known_value(value) for value in required_customer_values + required_request_values):
        return True
    if not has_known_value(str(scenario.hidden_context.get("current_call_contactable", ""))):
        return True
    return False


def _configure_manual_test_known_address(
    scenario,
    *,
    input_func=input,
    print_func=print,
):
    raw = input_func(
        "如需让客服直接核对已知地址，请输入完整地址；直接回车则按未知地址走询问流程: "
    )
    known_address = _sanitize_manual_user_text(raw)
    hidden_context = dict(scenario.hidden_context)

    if not known_address:
        hidden_context.update(
            {
                "service_known_address": False,
                "service_known_address_value": "",
                "service_known_address_matches_actual": False,
            }
        )
        print_func("未设置已知地址，客服将按询问流程采集地址。")
        return scenario.with_generated_hidden_settings(
            customer=scenario.customer,
            request=scenario.request,
            hidden_context=hidden_context,
        )

    hidden_context.update(
        {
            "service_known_address": True,
            "service_known_address_value": known_address,
            "service_known_address_matches_actual": True,
            "address_input_round_1": known_address,
            "address_input_round_2": known_address,
            "address_input_round_3": known_address,
            "address_input_round_4": known_address,
            "address_input_rounds": [known_address],
        }
    )
    print_func(f"已设置已知地址，客服将优先核对: {known_address}")
    return scenario.with_generated_hidden_settings(
        customer=replace(scenario.customer, address=known_address),
        request=scenario.request,
        hidden_context=hidden_context,
    )


def _hydrate_manual_test_scenario_locally(scenario):
    mock_contact_phone = _mock_manual_contact_phone(scenario.scenario_id)
    hidden_context = dict(scenario.hidden_context)
    hidden_context.update(
        {
            "current_call_contactable": True,
            "contact_phone_owner": "本人当前来电",
            "contact_phone_owner_spoken_label": "我这个号码",
            "contact_phone": mock_contact_phone,
            "phone_input_attempts_required": 0,
            "phone_input_round_1": "",
            "phone_input_round_2": "",
            "phone_input_round_3": "",
            "service_known_address": False,
            "service_known_address_value": "",
            "service_known_address_matches_actual": False,
            "address_input_round_1": "",
            "address_input_round_2": "",
            "address_input_round_3": "",
            "address_input_round_4": "",
            "address_input_rounds": [],
            "gender": hidden_context.get("gender", ""),
            "second_round_reply_strategy": hidden_context.get("second_round_reply_strategy", "confirm_only"),
        }
    )

    return scenario.with_generated_hidden_settings(
        customer=scenario.customer,
        request=scenario.request,
        hidden_context=hidden_context,
    )


def _mock_manual_contact_phone(seed_text: str) -> str:
    normalized_seed = str(seed_text or "").strip() or "manual_test_default"
    digest = hashlib.sha256(normalized_seed.encode("utf-8")).digest()
    prefix = MANUAL_CONTACT_PHONE_PREFIXES[int.from_bytes(digest[:2], "big") % len(MANUAL_CONTACT_PHONE_PREFIXES)]
    suffix = str(int.from_bytes(digest[2:8], "big") % 100000000).zfill(8)
    return f"{prefix}{suffix}"


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    _validate_output_flags(parser, args)

    if args.command == "generate":
        run_generate(args)
    elif args.command == "generate-hidden-settings":
        run_generate_hidden_settings(args)
    elif args.command == "interactive-test":
        run_interactive_test(args)


if __name__ == "__main__":
    main()
