"""
Browser Benchmark Framework.

Provides a benchmark runner and task definitions for measuring
browser agent performance across common browser automation scenarios.
"""

from .tasks import BenchmarkTask, BENCHMARK_TASKS
from .metrics import BenchmarkMetrics, MetricsCollector
from .runner import BenchmarkRunner, BenchmarkResult, BenchmarkReport

__all__ = [
    "BenchmarkTask",
    "BENCHMARK_TASKS",
    "BenchmarkMetrics",
    "MetricsCollector",
    "BenchmarkRunner",
    "BenchmarkResult",
    "BenchmarkReport",
]
