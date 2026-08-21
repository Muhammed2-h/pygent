"""
Browser Benchmark Framework.

Provides a benchmark runner and task definitions for measuring
browser agent performance across common browser automation scenarios.
"""

from .metrics import BenchmarkMetrics, MetricsCollector
from .runner import BenchmarkReport, BenchmarkResult, BenchmarkRunner
from .tasks import BENCHMARK_TASKS, BenchmarkTask

__all__ = [
    "BENCHMARK_TASKS",
    "BenchmarkMetrics",
    "BenchmarkReport",
    "BenchmarkResult",
    "BenchmarkRunner",
    "BenchmarkTask",
    "MetricsCollector",
]
