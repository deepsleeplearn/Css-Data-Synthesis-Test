"""
按自定义策略删除 outputs/ 目录下 SQLite 数据库中的记录。

===============================================================================
命令行参数总览
===============================================================================

基本形式：
    python review_db/delete_records.py --target <db> [全局开关] <策略> [策略参数]

全局参数：
    --target {reviews,generated,rewrite}
                                   （必填，必须写在策略名之前）指定要操作的数据库：
                                     - reviews   → outputs/frontend_manual_test.sqlite3
                                                   表 manual_test_reviews
                                                   主键列 session_id，时间列 reviewed_at
                                     - generated → outputs/generated_dialogues.sqlite3
                                                   表 generated_dialogues
                                                   主键列 dialogue_id，时间列 generated_at
                                     - rewrite   → outputs/frontend_rewrite_review.sqlite3
                                                   表 rewrite_reviews
                                                   主键列 record_id，时间列 reviewed_at
    --dry-run                      仅统计将会删除的行数，不实际执行 DELETE。
                                   可写在策略名之前或之后。
                                   建议任何一次新策略第一次运行都先带此开关试一遍。
    --yes                          跳过交互式二次确认；`all` 策略强制需要此开关。
                                   可写在策略名之前或之后。
    -h, --help                     打印帮助。

子命令 / 策略（必须提供其中之一）：

1) by-id          按主键精确删除（session_id / dialogue_id / record_id）
   用法：  by-id <id> [<id> ...]
   示例：  by-id abcd-1234
           by-id sess-1 sess-2 sess-3
   说明：  接受 1 个或多个 id，用空格分隔；命中为 0 时直接跳过。

2) recent         删除"最近 N 段时间"内产生的记录（时间列落在 [now - Δ, now]）
   用法：  recent [--days D] [--hours H] [--minutes M]
   示例：  recent --hours 2          # 删除最近 2 小时的记录
           recent --days 1 --hours 6 # 组合；等价于最近 30 小时
   说明：  --days/--hours/--minutes 至少一个为正；generated 以 UTC 计算，
           reviews/rewrite 以本地展示时间 `YYYY-MM-DD HH:MM:SS` 计算。

3) older-than     删除"N 段时间之前"的历史记录（时间列 <= now - Δ）
   用法：  older-than [--days D] [--hours H] [--minutes M]
   示例：  older-than --days 30      # 清理 30 天前的存档
   说明：  参数语义同 recent；与 recent 互为补集。

4) before         删除某个"绝对时间点"之前的记录（时间列 <= --time）
   用法：  before --time <TIME>
   示例：  before --time 2026-03-01 08:00:00
           before --time 2026-03-01T00:00:00
   说明：  reviews/rewrite 使用 `YYYY-MM-DD HH:MM:SS`；generated 兼容旧 ISO。

5) after          删除某个"绝对时间点"之后的记录（时间列 >= --time）
   用法：  after --time <TIME>
   示例：  after --time 2026-04-18 09:00:00

6) all            清空整张表（无 WHERE）
   用法：  all
   示例：  --yes all
   说明：  必须同时带 --yes；否则直接报错退出，避免误操作。

===============================================================================
典型调用示例
===============================================================================

    # 预览：reviews 库中 30 天前的记录有多少条（不真删）
    python review_db/delete_records.py --target reviews --dry-run older-than --days 30

    # 按 session_id 删除一条（带交互式确认）
    python review_db/delete_records.py --target reviews by-id 6d237d90-053a-4ffa-8e6e-993a11b4032b

    # 批量删除多个 dialogue_id，跳过确认
    python review_db/delete_records.py --target generated --yes by-id d-001 d-002 d-003

    # 清理一天内生成的对话（--yes 可写在任意位置）
    python review_db/delete_records.py --target generated recent --hours 24 --yes

    # 删除某个绝对时刻之前的所有评审
    python review_db/delete_records.py --target reviews before --time "2026-03-01 08:00:00"

    # 删除某个改写评审 record_id
    python review_db/delete_records.py --target rewrite by-id auto-20260423115442-bd58b00f

    # 清空整张表（需显式 --yes）
    python review_db/delete_records.py --target reviews --yes all

===============================================================================
拓展方式（新增删除策略）
===============================================================================

    新增一个继承 `DeletionStrategy` 的类，实现 `build_where(table)` 返回
    `(where_sql, params)`；用 `@register_strategy("<name>")` 注册一个工厂
    函数，把 argparse 解析结果转成策略实例；最后在 `build_parser` 里挂一个
    子命令即可。主执行流程不需要改动。

    示例（假设要新增"按状态删除"）：

        class ByStatusStrategy(DeletionStrategy):
            def __init__(self, status: str) -> None:
                self.status = status
            def build_where(self, table):
                return "status = ?", [self.status]

        @register_strategy("by-status")
        def _factory_by_status(args):
            return ByStatusStrategy(args.status)

        # 在 build_parser 中：
        p = sub.add_parser("by-status", parents=[common], help="按 status 列删除")
        p.add_argument("--status", required=True)
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable


# ── 目标数据库（表 + 主键 + 时间列）─────────────────────────────────────────

@dataclass(frozen=True)
class TargetTable:
    name: str
    db_path: Path
    table: str
    id_column: str
    time_column: str
    time_style: str = "iso"


OUTPUTS_DIR = Path(__file__).resolve().parent.parent / "outputs"

TARGETS: dict[str, TargetTable] = {
    "reviews": TargetTable(
        name="reviews",
        db_path=OUTPUTS_DIR / "frontend_manual_test.sqlite3",
        table="manual_test_reviews",
        id_column="session_id",
        time_column="reviewed_at",
        time_style="display",
    ),
    "generated": TargetTable(
        name="generated",
        db_path=OUTPUTS_DIR / "generated_dialogues.sqlite3",
        table="generated_dialogues",
        id_column="dialogue_id",
        time_column="generated_at",
        time_style="iso",
    ),
    "rewrite": TargetTable(
        name="rewrite",
        db_path=OUTPUTS_DIR / "frontend_rewrite_review.sqlite3",
        table="rewrite_reviews",
        id_column="record_id",
        time_column="reviewed_at",
        time_style="display",
    ),
}


# ── 策略基类与注册器 ────────────────────────────────────────────────────────

class DeletionStrategy(ABC):
    """
    每个策略只需返回 WHERE 片段（不含 WHERE 关键字）以及对应的参数列表。
    返回空字符串表示无条件（例如 `all` 策略）。
    """

    @abstractmethod
    def build_where(self, table: TargetTable) -> tuple[str, list[Any]]:
        ...

    def describe(self) -> str:
        return self.__class__.__name__


StrategyFactory = Callable[[argparse.Namespace], DeletionStrategy]
_REGISTRY: dict[str, StrategyFactory] = {}


def register_strategy(name: str) -> Callable[[StrategyFactory], StrategyFactory]:
    def decorator(factory: StrategyFactory) -> StrategyFactory:
        if name in _REGISTRY:
            raise ValueError(f"策略已注册: {name}")
        _REGISTRY[name] = factory
        return factory
    return decorator


# ── 内置策略实现 ────────────────────────────────────────────────────────────

class ByIdStrategy(DeletionStrategy):
    def __init__(self, ids: list[str]) -> None:
        cleaned = [i.strip() for i in ids if i and i.strip()]
        if not cleaned:
            raise ValueError("必须至少提供一个 id")
        self.ids = cleaned

    def build_where(self, table: TargetTable) -> tuple[str, list[Any]]:
        placeholders = ",".join("?" for _ in self.ids)
        return f"{table.id_column} IN ({placeholders})", list(self.ids)

    def describe(self) -> str:
        preview = self.ids[:3]
        suffix = "..." if len(self.ids) > 3 else ""
        return f"by-id ({len(self.ids)} 个: {preview}{suffix})"


class TimeRangeStrategy(DeletionStrategy):
    """通用时间区间策略：time_column 位于 [lower, upper] 之间（任一侧可空）。"""

    def __init__(self, lower: str | None, upper: str | None, label: str) -> None:
        if lower is None and upper is None:
            raise ValueError("lower 与 upper 不能同时为空")
        self.lower = lower
        self.upper = upper
        self.label = label

    def build_where(self, table: TargetTable) -> tuple[str, list[Any]]:
        clauses: list[str] = []
        params: list[Any] = []
        if self.lower is not None:
            clauses.append(f"{table.time_column} >= ?")
            params.append(self.lower)
        if self.upper is not None:
            clauses.append(f"{table.time_column} <= ?")
            params.append(self.upper)
        return " AND ".join(clauses), params

    def describe(self) -> str:
        return self.label


class AllStrategy(DeletionStrategy):
    def build_where(self, table: TargetTable) -> tuple[str, list[Any]]:
        return "", []

    def describe(self) -> str:
        return "all (清空整表)"


# ── 策略工厂（将 argparse 结果转换为策略实例）──────────────────────────────

def _parse_duration(args: argparse.Namespace) -> timedelta:
    total_seconds = (
        args.days * 86400
        + args.hours * 3600
        + args.minutes * 60
    )
    if total_seconds <= 0:
        raise ValueError("时间长度必须为正数（请设置 --days/--hours/--minutes 至少一个）")
    return timedelta(seconds=total_seconds)


DISPLAY_TIMEZONE = timezone(timedelta(hours=8))
DISPLAY_TIME_FORMAT = "%Y-%m-%d %H:%M:%S"


def _target_cutoff_text(table: TargetTable, duration: timedelta) -> str:
    if table.time_style == "display":
        return (datetime.now(DISPLAY_TIMEZONE) - duration).strftime(DISPLAY_TIME_FORMAT)
    return (datetime.now(timezone.utc).replace(tzinfo=None) - duration).isoformat(timespec="seconds")


def _normalize_absolute_time_for_target(table: TargetTable, value: str) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        raise ValueError("时间不能为空")
    if table.time_style == "display":
        try:
            return datetime.fromisoformat(normalized.replace("Z", "+00:00")).astimezone(DISPLAY_TIMEZONE).strftime(
                DISPLAY_TIME_FORMAT
            )
        except ValueError:
            try:
                return datetime.strptime(normalized, DISPLAY_TIME_FORMAT).strftime(DISPLAY_TIME_FORMAT)
            except ValueError as exc:
                raise ValueError("reviews 库时间格式必须为 YYYY-MM-DD HH:MM:SS，或可被 fromisoformat 解析") from exc
    return normalized


@register_strategy("by-id")
def _factory_by_id(args: argparse.Namespace) -> DeletionStrategy:
    return ByIdStrategy(args.ids)


@register_strategy("recent")
def _factory_recent(args: argparse.Namespace) -> DeletionStrategy:
    duration = _parse_duration(args)
    cutoff = _target_cutoff_text(TARGETS[args.target], duration)
    return TimeRangeStrategy(lower=cutoff, upper=None, label=f"recent (>= {cutoff})")


@register_strategy("older-than")
def _factory_older_than(args: argparse.Namespace) -> DeletionStrategy:
    duration = _parse_duration(args)
    cutoff = _target_cutoff_text(TARGETS[args.target], duration)
    return TimeRangeStrategy(lower=None, upper=cutoff, label=f"older-than (<= {cutoff})")


@register_strategy("before")
def _factory_before(args: argparse.Namespace) -> DeletionStrategy:
    normalized = _normalize_absolute_time_for_target(TARGETS[args.target], args.time)
    return TimeRangeStrategy(lower=None, upper=normalized, label=f"before ({normalized})")


@register_strategy("after")
def _factory_after(args: argparse.Namespace) -> DeletionStrategy:
    normalized = _normalize_absolute_time_for_target(TARGETS[args.target], args.time)
    return TimeRangeStrategy(lower=normalized, upper=None, label=f"after ({normalized})")


@register_strategy("all")
def _factory_all(args: argparse.Namespace) -> DeletionStrategy:
    if not args.yes:
        raise ValueError("`all` 策略需要显式传入 --yes 以确认清空整张表")
    return AllStrategy()


# ── 执行器 ─────────────────────────────────────────────────────────────────

def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table,),
    ).fetchone()
    return row is not None


def execute_deletion(
    target: TargetTable,
    strategy: DeletionStrategy,
    *,
    dry_run: bool,
) -> int:
    if not target.db_path.exists():
        raise FileNotFoundError(f"SQLite 文件不存在: {target.db_path}")

    where_sql, params = strategy.build_where(target)

    with sqlite3.connect(target.db_path) as conn:
        if not _table_exists(conn, target.table):
            raise ValueError(f"表不存在: {target.table}")

        count_query = f"SELECT COUNT(*) FROM {target.table}"
        delete_query = f"DELETE FROM {target.table}"
        if where_sql:
            count_query += f" WHERE {where_sql}"
            delete_query += f" WHERE {where_sql}"

        affected = int(conn.execute(count_query, params).fetchone()[0])
        if dry_run:
            return affected

        conn.execute(delete_query, params)
        conn.commit()
        return affected


# ── CLI ────────────────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    # --dry-run / --yes 抽到 common parent，让它们既能写在策略名前，也能写在后面。
    # --target 只放在顶层（必填），避免子 parser 的默认 None 覆盖顶层解析结果。
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument(
        "--dry-run",
        action="store_true",
        help="只统计将删除的行数，不实际执行 DELETE",
    )
    common.add_argument(
        "--yes",
        action="store_true",
        help="跳过二次确认；`all` 策略强制要求此开关",
    )

    parser = argparse.ArgumentParser(
        description="按策略删除 outputs/ 下 SQLite 数据库中的记录",
        parents=[common],
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--target",
        choices=sorted(TARGETS.keys()),
        required=True,
        help="目标数据库：reviews / generated / rewrite（必须写在策略名之前）",
    )

    sub = parser.add_subparsers(dest="strategy", required=True, metavar="<strategy>")

    p_id = sub.add_parser("by-id", parents=[common], help="按主键删除：session_id / dialogue_id / record_id")
    p_id.add_argument("ids", nargs="+", help="一个或多个 id（空格分隔）")

    for name, help_text in (
        ("recent", "删除最近 N 段时间内产生的记录"),
        ("older-than", "删除 N 段时间之前产生的记录"),
    ):
        p = sub.add_parser(name, parents=[common], help=help_text)
        p.add_argument("--days", type=int, default=0, help="天数（默认 0）")
        p.add_argument("--hours", type=int, default=0, help="小时数（默认 0）")
        p.add_argument("--minutes", type=int, default=0, help="分钟数（默认 0）")

    p_before = sub.add_parser("before", parents=[common], help="删除某个绝对时间之前的记录")
    p_before.add_argument("--time", required=True, help="reviews/rewrite 用 YYYY-MM-DD HH:MM:SS；generated 可用 ISO")

    p_after = sub.add_parser("after", parents=[common], help="删除某个绝对时间之后的记录")
    p_after.add_argument("--time", required=True, help="reviews/rewrite 用 YYYY-MM-DD HH:MM:SS；generated 可用 ISO")

    sub.add_parser("all", parents=[common], help="清空整张表（需配合 --yes）")

    return parser


def _confirm(prompt: str) -> bool:
    try:
        answer = input(f"{prompt} [y/N]: ").strip().lower()
    except EOFError:
        return False
    return answer in {"y", "yes"}


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    target = TARGETS[args.target]

    factory = _REGISTRY.get(args.strategy)
    if factory is None:
        print(f"未知策略: {args.strategy}", file=sys.stderr)
        return 2

    try:
        strategy = factory(args)
    except ValueError as exc:
        print(f"参数错误: {exc}", file=sys.stderr)
        return 2

    try:
        to_delete = execute_deletion(target, strategy, dry_run=True)
    except (FileNotFoundError, ValueError) as exc:
        print(f"执行失败: {exc}", file=sys.stderr)
        return 1

    print(
        f"[目标] {target.name}  表={target.table}  库={target.db_path}\n"
        f"[策略] {strategy.describe()}\n"
        f"[待删除] {to_delete} 行"
    )

    if args.dry_run:
        print("[dry-run] 未执行真实删除")
        return 0
    if to_delete == 0:
        print("无匹配记录，跳过删除")
        return 0
    if not args.yes and not _confirm("确认执行删除？"):
        print("已取消")
        return 0

    deleted = execute_deletion(target, strategy, dry_run=False)
    print(f"[完成] 已删除 {deleted} 行")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
