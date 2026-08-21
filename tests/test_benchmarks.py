"""Tests for the browser benchmark framework."""

from __future__ import annotations

import json

import pytest

from benchmarks.metrics import BenchmarkMetrics, MetricsCollector
from benchmarks.runner import BenchmarkReport, BenchmarkResult, BenchmarkRunner
from benchmarks.tasks import (
    BENCHMARK_TASKS,
    BenchmarkTask,
    TaskCategory,
    TaskDifficulty,
    filter_tasks,
    get_task,
)

# ======================================================================
# Task definitions
# ======================================================================


class TestBenchmarkTasks:
    """Tests for the benchmark task definitions."""

    def test_all_tasks_defined(self):
        assert len(BENCHMARK_TASKS) == 21

    def test_task_ids_unique(self):
        ids = [t.task_id for t in BENCHMARK_TASKS]
        assert len(ids) == len(set(ids))

    def test_expected_task_ids(self):
        expected = {
            "open_url",
            "search_page",
            "click_button",
            "fill_form",
            "submit_form",
            "open_new_tab",
            "switch_tabs",
            "download_file",
            "upload_file",
            "handle_spa",
            "handle_iframe",
            "handle_shadow_dom",
            "use_cdp",
            "recover_from_js_failure",
            "self_evolution_a",
            "self_evolution_b",
            "env_package_missing",
            "env_extension_missing",
            "env_driver_stopped",
            "env_port_unavailable",
            "env_browser_closed",
        }
        actual = {t.task_id for t in BENCHMARK_TASKS}
        assert actual == expected


    def test_get_task_found(self):
        task = get_task("open_url")
        assert task.name == "Open URL"

    def test_get_task_not_found(self):
        with pytest.raises(KeyError, match="no_such_task"):
            get_task("no_such_task")

    def test_filter_by_category(self):
        nav = filter_tasks(category=TaskCategory.NAVIGATION)
        assert all(t.category == TaskCategory.NAVIGATION for t in nav)
        assert len(nav) >= 1

    def test_filter_by_difficulty(self):
        easy = filter_tasks(difficulty=TaskDifficulty.EASY)
        assert all(t.difficulty == TaskDifficulty.EASY for t in easy)

    def test_filter_by_tags(self):
        results = filter_tasks(tags={"form"})
        assert all("form" in t.tags for t in results)
        assert len(results) >= 1

    def test_filter_combined(self):
        results = filter_tasks(
            category=TaskCategory.FORM, difficulty=TaskDifficulty.MEDIUM
        )
        assert all(
            t.category == TaskCategory.FORM and t.difficulty == TaskDifficulty.MEDIUM
            for t in results
        )

    def test_all_tasks_have_expected_outcome(self):
        for t in BENCHMARK_TASKS:
            assert "success" in t.expected_outcome

    def test_matches_filter_no_criteria(self):
        task = BENCHMARK_TASKS[0]
        assert task.matches_filter() is True

    def test_has_executor_false_by_default(self):
        task = BENCHMARK_TASKS[0]
        assert task.has_executor is False


# ======================================================================
# Metrics
# ======================================================================


class TestBenchmarkMetrics:
    """Tests for metrics data and collector."""

    def test_metrics_defaults(self):
        m = BenchmarkMetrics()
        assert m.success is False
        assert m.turn_count == 0
        assert m.tool_calls == 0
        assert m.elapsed_seconds == 0.0
        assert m.recovery_count == 0

    def test_metrics_as_dict(self):
        m = BenchmarkMetrics(success=True, turn_count=3, tool_calls=5,
                             elapsed_seconds=1.2345, recovery_count=1)
        d = m.as_dict()
        assert d["success"] is True
        assert d["turn_count"] == 3
        assert d["tool_calls"] == 5
        assert d["elapsed_seconds"] == 1.2345
        assert d["recovery_count"] == 1

    def test_collector_lifecycle(self):
        c = MetricsCollector()
        assert c.is_running is False
        assert c.elapsed == 0.0

        c.start()
        assert c.is_running is True

        c.record_turn()
        c.record_turn()
        c.record_tool_call(3)
        c.record_recovery()

        c.stop(success=True)
        assert c.is_running is False

        m = c.finalise()
        assert m.success is True
        assert m.turn_count == 2
        assert m.tool_calls == 3
        assert m.recovery_count == 1
        assert m.elapsed_seconds > 0.0

    def test_collector_finalise_before_stop(self):
        c = MetricsCollector()
        c.start()
        c.record_turn()
        # finalise without calling stop — should still work
        m = c.finalise()
        assert m.success is False
        assert m.turn_count == 1
        assert m.elapsed_seconds >= 0.0

    def test_collector_tool_call_default_count(self):
        c = MetricsCollector()
        c.record_tool_call()
        m = c.finalise()
        assert m.tool_calls == 1


# ======================================================================
# Runner – dry-run mode
# ======================================================================


class TestBenchmarkRunnerDryRun:
    """Tests for the benchmark runner in dry-run mode (no live browser)."""

    @pytest.mark.asyncio
    async def test_dry_run_all_tasks(self):
        runner = BenchmarkRunner(live=False)
        report = await runner.run()
        assert report.total == 21
        # In dry-run with no override all tasks fail
        assert report.passed == 0
        assert report.failed == 21

    @pytest.mark.asyncio
    async def test_dry_run_simulated_pass(self):
        runner = BenchmarkRunner(live=False, dry_run_result=True)
        report = await runner.run()
        assert report.passed == 21
        assert report.success_rate == 1.0

    @pytest.mark.asyncio
    async def test_dry_run_simulated_fail(self):
        runner = BenchmarkRunner(live=False, dry_run_result=False)
        report = await runner.run()
        assert report.passed == 0
        assert report.success_rate == 0.0
        for r in report.results:
            assert r.error == "dry-run: simulated failure"

    @pytest.mark.asyncio
    async def test_dry_run_with_category_filter(self):
        runner = BenchmarkRunner(
            live=False, category=TaskCategory.FORM, dry_run_result=True
        )
        report = await runner.run()
        assert report.total == 2  # fill_form + submit_form
        assert all(r.task.category == TaskCategory.FORM for r in report.results)

    @pytest.mark.asyncio
    async def test_dry_run_with_difficulty_filter(self):
        runner = BenchmarkRunner(
            live=False, difficulty=TaskDifficulty.EASY, dry_run_result=True
        )
        report = await runner.run()
        assert report.total >= 1
        assert all(
            r.task.difficulty == TaskDifficulty.EASY for r in report.results
        )

    @pytest.mark.asyncio
    async def test_dry_run_with_tag_filter(self):
        runner = BenchmarkRunner(
            live=False, tags={"cdp"}, dry_run_result=True
        )
        report = await runner.run()
        assert report.total == 1
        assert report.results[0].task.task_id == "use_cdp"

    @pytest.mark.asyncio
    async def test_dry_run_metrics_populated(self):
        runner = BenchmarkRunner(live=False, dry_run_result=True)
        report = await runner.run()
        for r in report.results:
            assert r.metrics.turn_count == 1
            assert r.metrics.tool_calls == 1
            assert r.metrics.elapsed_seconds >= 0.0

    @pytest.mark.asyncio
    async def test_custom_task_list(self):
        subset = BENCHMARK_TASKS[:3]
        runner = BenchmarkRunner(tasks=subset, live=False, dry_run_result=True)
        report = await runner.run()
        assert report.total == 3


# ======================================================================
# Runner – live mode with mock executor
# ======================================================================


class TestBenchmarkRunnerLive:
    """Tests for the runner with mock executors (no real browser)."""

    @staticmethod
    def _make_task_with_executor(
        success: bool = True,
        turns: int = 2,
        tools: int = 4,
        recoveries: int = 0,
        skill_created: bool = False,
        skill_reused: bool = False,
        successful_path: list[str] = None,
        detected: bool = False,
        repaired: bool = False,
        verified: bool = False,
        remembered: bool = False,
        task_id: str = "mock_task",
    ) -> BenchmarkTask:
        async def executor(**kwargs):
            return {
                "success": success,
                "turn_count": turns,
                "tool_calls": tools,
                "recovery_count": recoveries,
                "skill_created": skill_created,
                "skill_reused": skill_reused,
                "successful_path": successful_path or [],
                "detected": detected,
                "repaired": repaired,
                "verified": verified,
                "remembered": remembered,
            }

        return BenchmarkTask(
            task_id=task_id,
            name="Mock Task",
            description="A mock task for testing.",
            category=TaskCategory.NAVIGATION,
            difficulty=TaskDifficulty.EASY,
            expected_outcome={"success": True},
            executor=executor,
        )

    @pytest.mark.asyncio
    async def test_live_executor_success(self):
        task = self._make_task_with_executor(success=True, turns=3, tools=5)
        runner = BenchmarkRunner(tasks=[task], live=True)
        report = await runner.run()

        assert report.total == 1
        r = report.results[0]
        assert r.passed is True
        assert r.metrics.turn_count == 3
        assert r.metrics.tool_calls == 5
        assert r.metrics.elapsed_seconds > 0.0

    @pytest.mark.asyncio
    async def test_live_executor_failure(self):
        task = self._make_task_with_executor(success=False)
        runner = BenchmarkRunner(tasks=[task], live=True)
        report = await runner.run()

        assert report.results[0].passed is False

    @pytest.mark.asyncio
    async def test_live_executor_exception(self):
        async def bad_executor(**kwargs):
            raise RuntimeError("browser crashed")

        task = BenchmarkTask(
            task_id="crash_task",
            name="Crash Task",
            description="Task that raises.",
            category=TaskCategory.RECOVERY,
            difficulty=TaskDifficulty.HARD,
            executor=bad_executor,
        )
        runner = BenchmarkRunner(tasks=[task], live=True)
        report = await runner.run()

        r = report.results[0]
        assert r.passed is False
        assert r.error == "browser crashed"

    @pytest.mark.asyncio
    async def test_live_with_recovery(self):
        task = self._make_task_with_executor(
            success=True, turns=4, tools=8, recoveries=2
        )
        runner = BenchmarkRunner(tasks=[task], live=True)
        report = await runner.run()

        r = report.results[0]
        assert r.metrics.recovery_count == 2

    @pytest.mark.asyncio
    async def test_live_with_skills(self):
        task = self._make_task_with_executor(
            success=True, turns=4, tools=8, skill_created=True, skill_reused=True,
            successful_path=["click_button", "fill_form"]
        )
        runner = BenchmarkRunner(tasks=[task], live=True)
        report = await runner.run()

        r = report.results[0]
        assert r.metrics.skill_created is True
        assert r.metrics.skill_reused is True
        assert r.metrics.successful_path == ["click_button", "fill_form"]

    @pytest.mark.asyncio
    async def test_validate_evolution(self):
        task_a = self._make_task_with_executor(
            task_id="self_evolution_a",
            success=True, turns=4, recoveries=2,
            skill_created=True, successful_path=["step1", "step2"]
        )
        task_b = self._make_task_with_executor(
            task_id="self_evolution_b",
            success=True, turns=2, recoveries=0,
            skill_reused=True
        )
        runner = BenchmarkRunner(tasks=[task_a, task_b], live=True)
        report = await runner.run()
        
        errors = report.validate_evolution()
        assert not errors, f"Expected no evolution errors, got: {errors}"
        
    @pytest.mark.asyncio
    async def test_validate_evolution_fails(self):
        task_a = self._make_task_with_executor(
            task_id="self_evolution_a",
            success=True, turns=2, recoveries=1,
            skill_created=True, successful_path=["step1"]
        )
        task_b = self._make_task_with_executor(
            task_id="self_evolution_b",
            success=True, turns=4, recoveries=2,  # worse performance
            skill_reused=False  # failed to reuse
        )
        runner = BenchmarkRunner(tasks=[task_a, task_b], live=True)
        report = await runner.run()
        
        errors = report.validate_evolution()
        assert len(errors) == 3
        assert "Task B did not use fewer turns" in errors[0]
        assert "Task B did not have fewer failures/recoveries" in errors[1]
        assert "Task B did not record a reused skill" in errors[2]

    @pytest.mark.asyncio
    async def test_validate_environment_evolution_success(self):
        task_1 = self._make_task_with_executor(
            task_id="env_package_missing",
            success=True,
            detected=True,
            repaired=True,
            verified=True,
            remembered=True
        )
        runner = BenchmarkRunner(tasks=[task_1], live=True)
        report = await runner.run()
        
        errors = report.validate_environment_evolution()
        assert not errors, f"Expected no errors, got: {errors}"

    @pytest.mark.asyncio
    async def test_validate_environment_evolution_fails(self):
        task_1 = self._make_task_with_executor(
            task_id="env_package_missing",
            success=True,
            detected=True,
            repaired=False,
            verified=True,
            remembered=False
        )
        runner = BenchmarkRunner(tasks=[task_1], live=True)
        report = await runner.run()
        
        errors = report.validate_environment_evolution()
        assert len(errors) == 2
        assert "Task env_package_missing did not record 'repaired'" in errors[0]
        assert "Task env_package_missing did not record 'remembered'" in errors[1]

# ======================================================================
# Report
# ======================================================================


class TestBenchmarkReport:
    """Tests for report aggregation and serialisation."""

    @staticmethod
    def _sample_report() -> BenchmarkReport:
        results = []
        for i, task in enumerate(BENCHMARK_TASKS[:4]):
            m = BenchmarkMetrics(
                success=(i % 2 == 0),
                turn_count=i + 1,
                tool_calls=i * 2,
                elapsed_seconds=0.1 * (i + 1),
                recovery_count=0 if i < 2 else 1,
            )
            results.append(BenchmarkResult(task=task, metrics=m))
        return BenchmarkReport(results=results, wall_clock_seconds=1.5)

    def test_aggregate_totals(self):
        report = self._sample_report()
        assert report.total == 4
        assert report.passed == 2
        assert report.failed == 2

    def test_success_rate(self):
        report = self._sample_report()
        assert report.success_rate == 0.5

    def test_total_turns(self):
        report = self._sample_report()
        # 1 + 2 + 3 + 4 = 10
        assert report.total_turns == 10

    def test_total_tool_calls(self):
        report = self._sample_report()
        # 0 + 2 + 4 + 6 = 12
        assert report.total_tool_calls == 12

    def test_total_recoveries(self):
        report = self._sample_report()
        assert report.total_recoveries == 2

    def test_avg_elapsed(self):
        report = self._sample_report()
        expected = (0.1 + 0.2 + 0.3 + 0.4) / 4
        assert abs(report.avg_elapsed - expected) < 1e-6

    def test_to_json_roundtrip(self):
        report = self._sample_report()
        data = json.loads(report.to_json())
        assert data["summary"]["total"] == 4
        assert len(data["results"]) == 4

    def test_save_to_file(self, tmp_path):
        report = self._sample_report()
        out = report.save(tmp_path / "report.json")
        assert out.exists()
        data = json.loads(out.read_text())
        assert data["summary"]["success_rate"] == 0.5

    def test_summary_text(self):
        report = self._sample_report()
        text = report.summary_text()
        assert "BROWSER BENCHMARK REPORT" in text
        assert "PASS" in text
        assert "FAIL" in text

    def test_by_category(self):
        report = self._sample_report()
        groups = report.by_category()
        assert isinstance(groups, dict)
        assert len(groups) >= 1

    def test_empty_report(self):
        report = BenchmarkReport()
        assert report.total == 0
        assert report.success_rate == 0.0
        assert report.avg_elapsed == 0.0

    def test_result_as_dict(self):
        task = BENCHMARK_TASKS[0]
        m = BenchmarkMetrics(success=True, turn_count=1)
        r = BenchmarkResult(task=task, metrics=m)
        d = r.as_dict()
        assert d["task_id"] == "open_url"
        assert d["passed"] is True
        assert "metrics" in d
