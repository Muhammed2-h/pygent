"""
Benchmark runner and reporting.

The runner iterates over benchmark tasks, optionally executing them
against a live browser (when an executor is attached and ``--live``
is requested), and produces a structured report.
"""

from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional, Sequence

from .metrics import BenchmarkMetrics, MetricsCollector
from .tasks import (
    BENCHMARK_TASKS,
    BenchmarkTask,
    TaskCategory,
    TaskDifficulty,
    filter_tasks,
)


@dataclass
class BenchmarkResult:
    """Result of running a single benchmark task."""

    task: BenchmarkTask
    metrics: BenchmarkMetrics
    error: Optional[str] = None
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        return self.metrics.success and self.error is None

    def as_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task.task_id,
            "task_name": self.task.name,
            "category": self.task.category.value,
            "difficulty": self.task.difficulty.value,
            "passed": self.passed,
            "error": self.error,
            "metrics": self.metrics.as_dict(),
            **self.extra,
        }


@dataclass
class BenchmarkReport:
    """Aggregate report over all executed benchmark tasks."""

    results: list[BenchmarkResult] = field(default_factory=list)
    wall_clock_seconds: float = 0.0

    # ------------------------------------------------------------------
    # Aggregate helpers
    # ------------------------------------------------------------------

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def passed(self) -> int:
        return sum(1 for r in self.results if r.passed)

    @property
    def failed(self) -> int:
        return self.total - self.passed

    @property
    def success_rate(self) -> float:
        return self.passed / self.total if self.total else 0.0

    @property
    def total_turns(self) -> int:
        return sum(r.metrics.turn_count for r in self.results)

    @property
    def total_tool_calls(self) -> int:
        return sum(r.metrics.tool_calls for r in self.results)

    @property
    def total_recoveries(self) -> int:
        return sum(r.metrics.recovery_count for r in self.results)

    @property
    def avg_elapsed(self) -> float:
        if not self.results:
            return 0.0
        return sum(r.metrics.elapsed_seconds for r in self.results) / len(self.results)

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def as_dict(self) -> dict[str, Any]:
        return {
            "summary": {
                "total": self.total,
                "passed": self.passed,
                "failed": self.failed,
                "success_rate": round(self.success_rate, 4),
                "total_turns": self.total_turns,
                "total_tool_calls": self.total_tool_calls,
                "total_recoveries": self.total_recoveries,
                "avg_elapsed_seconds": round(self.avg_elapsed, 4),
                "wall_clock_seconds": round(self.wall_clock_seconds, 4),
            },
            "results": [r.as_dict() for r in self.results],
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.as_dict(), indent=indent)

    def save(self, path: str | Path) -> Path:
        """Write the JSON report to *path* and return the resolved ``Path``."""
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(self.to_json())
        return p

    # ------------------------------------------------------------------
    # Human-readable summary
    # ------------------------------------------------------------------

    def summary_text(self) -> str:
        lines = [
            "=" * 60,
            "  BROWSER BENCHMARK REPORT",
            "=" * 60,
            f"  Tasks run:       {self.total}",
            f"  Passed:          {self.passed}",
            f"  Failed:          {self.failed}",
            f"  Success rate:    {self.success_rate:.1%}",
            f"  Total turns:     {self.total_turns}",
            f"  Total tool calls:{self.total_tool_calls}",
            f"  Total recoveries:{self.total_recoveries}",
            f"  Avg elapsed:     {self.avg_elapsed:.3f}s",
            f"  Wall clock:      {self.wall_clock_seconds:.3f}s",
            "-" * 60,
        ]
        for r in self.results:
            status = "PASS" if r.passed else "FAIL"
            lines.append(
                f"  [{status}] {r.task.name:<28} "
                f"turns={r.metrics.turn_count} "
                f"tools={r.metrics.tool_calls} "
                f"time={r.metrics.elapsed_seconds:.3f}s "
                f"recov={r.metrics.recovery_count}"
            )
            if r.error:
                lines.append(f"         error: {r.error}")
        lines.append("=" * 60)
        return "\n".join(lines)

    def by_category(self) -> dict[str, list[BenchmarkResult]]:
        """Group results by task category."""
        groups: dict[str, list[BenchmarkResult]] = {}
        for r in self.results:
            groups.setdefault(r.task.category.value, []).append(r)
        return groups


class BenchmarkRunner:
    """Execute benchmark tasks and collect results.

    Parameters
    ----------
    tasks : sequence of BenchmarkTask, optional
        Tasks to run.  Defaults to :data:`BENCHMARK_TASKS`.
    live : bool
        When ``True``, tasks that have an ``executor`` will be invoked
        against a live browser.  When ``False`` (default), each task is
        recorded as *skipped* (success=False, error="dry-run") unless a
        ``dry_run_result`` override is supplied.
    dry_run_result : bool | None
        If set, override dry-run outcomes: ``True`` marks all non-live
        tasks as passed, ``False`` marks them as failed.
    """

    def __init__(
        self,
        tasks: Optional[Sequence[BenchmarkTask]] = None,
        *,
        live: bool = False,
        dry_run_result: Optional[bool] = None,
        category: Optional[TaskCategory] = None,
        difficulty: Optional[TaskDifficulty] = None,
        tags: Optional[set[str]] = None,
    ) -> None:
        base = list(tasks) if tasks is not None else list(BENCHMARK_TASKS)
        self.tasks = [
            t
            for t in base
            if t.matches_filter(category=category, difficulty=difficulty, tags=tags)
        ]
        self.live = live
        self.dry_run_result = dry_run_result

    # ------------------------------------------------------------------
    # Running
    # ------------------------------------------------------------------

    async def run(self, **executor_kwargs: Any) -> BenchmarkReport:
        """Execute all selected tasks and return a :class:`BenchmarkReport`."""
        report = BenchmarkReport()
        wall_start = time.monotonic()

        for task in self.tasks:
            result = await self._run_one(task, **executor_kwargs)
            report.results.append(result)

        report.wall_clock_seconds = time.monotonic() - wall_start
        return report

    async def _run_one(
        self, task: BenchmarkTask, **executor_kwargs: Any
    ) -> BenchmarkResult:
        collector = MetricsCollector()

        if self.live and task.has_executor:
            return await self._run_live(task, collector, **executor_kwargs)

        # Dry-run mode: simulate the result
        return self._run_dry(task, collector)

    async def _run_live(
        self,
        task: BenchmarkTask,
        collector: MetricsCollector,
        **executor_kwargs: Any,
    ) -> BenchmarkResult:
        """Run a task with its live executor."""
        assert task.executor is not None
        collector.start()
        try:
            result_dict = await task.executor(**executor_kwargs)
            success = bool(result_dict.get("success", False))
            turn_count = result_dict.get("turn_count", 1)
            tool_calls = result_dict.get("tool_calls", 1)
            recovery_count = result_dict.get("recovery_count", 0)

            for _ in range(turn_count):
                collector.record_turn()
            collector.record_tool_call(tool_calls)
            for _ in range(recovery_count):
                collector.record_recovery()

            collector.stop(success=success)
            return BenchmarkResult(
                task=task,
                metrics=collector.finalise(),
                extra=result_dict,
            )
        except Exception as exc:
            collector.stop(success=False)
            return BenchmarkResult(
                task=task,
                metrics=collector.finalise(),
                error=str(exc),
            )

    def _run_dry(
        self, task: BenchmarkTask, collector: MetricsCollector
    ) -> BenchmarkResult:
        """Produce a dry-run result without executing against a browser."""
        collector.start()

        if self.dry_run_result is not None:
            success = self.dry_run_result
            error = None if success else "dry-run: simulated failure"
        else:
            success = False
            error = "dry-run: no live executor"

        collector.record_turn()
        collector.record_tool_call(1)
        collector.stop(success=success)

        return BenchmarkResult(
            task=task,
            metrics=collector.finalise(),
            error=error,
        )
