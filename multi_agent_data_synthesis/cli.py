from __future__ import annotations

import asyncio
import argparse
import json
import random
from dataclasses import replace
from pathlib import Path

from multi_agent_data_synthesis.config import load_config
from multi_agent_data_synthesis.exporter import write_json, write_jsonl
from multi_agent_data_synthesis.hidden_settings_tool import HiddenSettingsTool
from multi_agent_data_synthesis.llm import OpenAIChatClient
from multi_agent_data_synthesis.agents import ServiceAgent
from multi_agent_data_synthesis.manual_test import (
    default_manual_test_output_path,
    load_manual_test_scenario,
    run_manual_test_session,
)
from multi_agent_data_synthesis.orchestrator import DialogueOrchestrator
from multi_agent_data_synthesis.product_routing import ensure_product_routing_plan
from multi_agent_data_synthesis.scenario_factory import ScenarioFactory
from multi_agent_data_synthesis.schemas import CustomerProfile, ServiceRequest


DEFAULT_SCENARIO_FILE = Path("data/seed_scenarios.json")
DEFAULT_JSONL_OUTPUT = Path("outputs/dialogues.jsonl")
DEFAULT_JSON_OUTPUT = Path("outputs/dialogues.json")
DEFAULT_HIDDEN_SETTINGS_OUTPUT = Path("outputs/generated_hidden_scenarios.json")


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

    completed = sum(1 for sample in samples if sample.status == "completed")
    print(f"Generated {len(samples)} dialogues.")
    print(f"Completed dialogues: {completed}")
    if args.write_output:
        print(f"JSONL output: {args.jsonl_output}")
        print(f"JSON output: {args.json_output}")
    else:
        print("File output disabled. Use --write-output to persist JSONL/JSON files.")


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
            generated = await tool.generate_for_scenario_async(scenario)
            return generated.to_dict()

    hydrated = list(await asyncio.gather(*(generate_single(scenario) for scenario in scenarios)))

    if args.write_output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(hydrated, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    print(f"Generated hidden settings for {len(hydrated)} scenarios.")
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
        scenario = tool.generate_for_scenario(scenario)
    elif _manual_test_requires_generated_hidden_settings(scenario):
        scenario = _hydrate_manual_test_scenario_locally(scenario)
    scenario.hidden_context["interactive_test_freeform"] = True
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
        product_routing_enabled=config.product_routing_enabled,
        product_routing_apply_probability=config.product_routing_apply_probability,
    )

    output_path = None
    if args.write_output:
        output_path = args.output or default_manual_test_output_path(scenario.scenario_id)
    run_manual_test_session(
        scenario,
        output_path=output_path,
        max_rounds=args.max_rounds,
        ok_prefix_probability=config.service_ok_prefix_probability,
        policy=service_agent.policy,
    )


def _load_cli_config(*, write_output: bool):
    config = load_config()
    if write_output:
        return config
    return replace(config, hidden_settings_store=None)


def _validate_output_flags(parser: argparse.ArgumentParser, args: argparse.Namespace) -> None:
    if getattr(args, "write_output", False):
        return
    if args.command == "generate":
        if args.jsonl_output != DEFAULT_JSONL_OUTPUT or args.json_output != DEFAULT_JSON_OUTPUT:
            parser.error("--jsonl-output/--json-output 需要配合 --write-output 使用。")
    elif args.command == "generate-hidden-settings":
        if args.output != DEFAULT_HIDDEN_SETTINGS_OUTPUT:
            parser.error("--output 需要配合 --write-output 使用。")
    elif args.command == "interactive-test" and args.output is not None:
        parser.error("--output 需要配合 --write-output 使用。")


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


def _hydrate_manual_test_scenario_locally(scenario):
    seed = sum((index + 1) * ord(char) for index, char in enumerate(scenario.scenario_id))
    rng = random.Random(seed)

    customer_options = (
        {
            "full_name": "张丽",
            "surname": "张",
            "phone": "13800138001",
            "address": "上海市浦东新区锦绣路1888弄6号1202室",
            "persona": "上班族，表达比较直接，倾向按客服流程一步步确认。",
            "speech_style": "说话简短清楚，偶尔带一点口头语。",
        },
        {
            "full_name": "王强",
            "surname": "王",
            "phone": "13900139002",
            "address": "杭州市余杭区五常大道666号3幢1单元802室",
            "persona": "家用用户，希望尽快把问题登记清楚，不喜欢反复确认。",
            "speech_style": "说话偏口语化，确认信息时比较利索。",
        },
        {
            "full_name": "郭建国",
            "surname": "郭",
            "phone": "13773341553",
            "address": "江苏省扬州市宝应县安宜镇宝应碧桂园3幢5层502室",
            "persona": "普通家庭用户，比较配合客服，但不希望流程拖太久。",
            "speech_style": "表达自然，必要时会补半句说明。",
        },
    )
    request_type = scenario.request.request_type
    customer_seed = customer_options[rng.randrange(len(customer_options))]

    if request_type == "installation":
        request_seed = {
            "issue": "新买的空气能热水机已经送到家了，想约师傅上门安装。",
            "desired_resolution": "先把安装工单登记好，等后续联系确认时间。",
            "availability": "这周六上午或者周日下午都可以。",
            "product_arrived": "yes",
        }
    else:
        request_seed = {
            "issue": "最近空气能热水器加热比较慢，洗澡时水温还有点忽冷忽热，想报修。",
            "desired_resolution": "尽快安排售后上门检查机器问题。",
            "availability": "工作日晚上七点后或者周末白天都可以。",
            "product_arrived": "",
        }

    hidden_context = dict(scenario.hidden_context)
    hidden_context.update(
        {
            "current_call_contactable": True,
            "contact_phone_owner": "本人当前来电",
            "contact_phone_owner_spoken_label": "我这个号码",
            "contact_phone": customer_seed["phone"],
            "phone_input_attempts_required": 0,
            "phone_input_round_1": f"{customer_seed['phone']}#",
            "phone_input_round_2": f"{customer_seed['phone']}#",
            "phone_input_round_3": f"{customer_seed['phone']}#",
            "service_known_address": False,
            "service_known_address_value": "",
            "service_known_address_matches_actual": False,
            "address_input_round_1": customer_seed["address"],
            "address_input_round_2": customer_seed["address"],
            "address_input_round_3": customer_seed["address"],
            "address_input_round_4": customer_seed["address"],
            "address_input_rounds": [customer_seed["address"]],
            "gender": hidden_context.get("gender", "男"),
            "second_round_reply_strategy": hidden_context.get("second_round_reply_strategy", "confirm_only"),
        }
    )
    if request_seed["product_arrived"]:
        hidden_context["product_arrived"] = request_seed["product_arrived"]

    return scenario.with_generated_hidden_settings(
        customer=CustomerProfile(**customer_seed),
        request=ServiceRequest(
            request_type=request_type,
            issue=request_seed["issue"],
            desired_resolution=request_seed["desired_resolution"],
            availability=request_seed["availability"],
        ),
        hidden_context=hidden_context,
    )


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
