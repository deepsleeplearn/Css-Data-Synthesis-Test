from __future__ import annotations

import asyncio
import argparse
import json
from pathlib import Path

from multi_agent_data_synthesis.config import load_config
from multi_agent_data_synthesis.exporter import write_json, write_jsonl
from multi_agent_data_synthesis.hidden_settings_tool import HiddenSettingsTool
from multi_agent_data_synthesis.llm import OpenAIChatClient
from multi_agent_data_synthesis.orchestrator import DialogueOrchestrator
from multi_agent_data_synthesis.scenario_factory import ScenarioFactory


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="多智能体家电客服对话数据生成器")
    subparsers = parser.add_subparsers(dest="command", required=True)

    generate_parser = subparsers.add_parser("generate", help="批量生成对话数据")
    generate_parser.add_argument(
        "--scenario-file",
        type=Path,
        default=Path("data/seed_scenarios.json"),
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
        default=Path("outputs/dialogues.jsonl"),
        help="JSONL 输出路径",
    )
    generate_parser.add_argument(
        "--json-output",
        type=Path,
        default=Path("outputs/dialogues.json"),
        help="JSON 输出路径",
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
        default=Path("data/seed_scenarios.json"),
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
        default=Path("outputs/generated_hidden_scenarios.json"),
        help="带隐藏设定的场景输出路径",
    )
    hidden_parser.add_argument(
        "--concurrency",
        type=int,
        default=None,
        help="异步并发生成的任务数，默认使用配置中的 MAX_CONCURRENCY",
    )

    return parser


def run_generate(args: argparse.Namespace) -> None:
    asyncio.run(run_generate_async(args))


async def run_generate_async(args: argparse.Namespace) -> None:
    config = load_config()
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

    write_jsonl(samples, args.jsonl_output)
    write_json(samples, args.json_output)

    completed = sum(1 for sample in samples if sample.status == "completed")
    print(f"Generated {len(samples)} dialogues.")
    print(f"Completed dialogues: {completed}")
    print(f"JSONL output: {args.jsonl_output}")
    print(f"JSON output: {args.json_output}")


def run_generate_hidden_settings(args: argparse.Namespace) -> None:
    asyncio.run(run_generate_hidden_settings_async(args))


async def run_generate_hidden_settings_async(args: argparse.Namespace) -> None:
    config = load_config()
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

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(hydrated, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Generated hidden settings for {len(hydrated)} scenarios.")
    print(f"Output: {args.output}")
    print(f"History store: {config.hidden_settings_store}")


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "generate":
        run_generate(args)
    elif args.command == "generate-hidden-settings":
        run_generate_hidden_settings(args)


if __name__ == "__main__":
    main()
