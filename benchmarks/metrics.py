"""
Metrics collection for benchmark runs.

Tracks the five metrics called out in the task brief:
    * success rate
    * turn count
    * tool calls
    * time (seconds)
    * recovery count
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class BenchmarkMetrics:
    """Immutable snapshot of metrics for a single task run."""

    success: bool = False
    turn_count: int = 0
    tool_calls: int = 0
    elapsed_seconds: float = 0.0
    recovery_count: int = 0
    skill_created: bool = False
    skill_reused: bool = False
    successful_path: list[str] = field(default_factory=list)

    # ------------------------------------------------------------------
    # Derived / computed helpers
    # ------------------------------------------------------------------

    def as_dict(self) -> dict:
        """Return a plain dict suitable for serialisation."""
        return {
            "success": self.success,
            "turn_count": self.turn_count,
            "tool_calls": self.tool_calls,
            "elapsed_seconds": round(self.elapsed_seconds, 4),
            "recovery_count": self.recovery_count,
            "skill_created": self.skill_created,
            "skill_reused": self.skill_reused,
            "successful_path": list(self.successful_path),
        }


class MetricsCollector:
    """Mutable collector used *during* a task run.

    Call :pymeth:`start` before the task and :pymeth:`stop` after.
    Intermediate events (turns, tool-calls, recoveries) are recorded via
    the corresponding ``record_*`` helpers.

    When done, call :pymeth:`finalise` to obtain an immutable
    :class:`BenchmarkMetrics` snapshot.
    """

    def __init__(self) -> None:
        self._start_time: Optional[float] = None
        self._end_time: Optional[float] = None
        self._turn_count: int = 0
        self._tool_calls: int = 0
        self._recovery_count: int = 0
        self._success: bool = False
        self._skill_created: bool = False
        self._skill_reused: bool = False
        self._successful_path: list[str] = []

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Mark the beginning of a task run."""
        self._start_time = time.monotonic()
        self._end_time = None

    def stop(self, *, success: bool) -> None:
        """Mark the end of a task run."""
        self._end_time = time.monotonic()
        self._success = success

    # ------------------------------------------------------------------
    # Event recording
    # ------------------------------------------------------------------

    def record_turn(self) -> None:
        """Record one agent turn (LLM round-trip)."""
        self._turn_count += 1

    def record_tool_call(self, count: int = 1) -> None:
        """Record one or more tool calls."""
        self._tool_calls += count

    def record_recovery(self) -> None:
        """Record a recovery event (error handled)."""
        self._recovery_count += 1

    def record_skill_created(self) -> None:
        """Record that a skill was created during the task."""
        self._skill_created = True

    def record_skill_reused(self) -> None:
        """Record that a skill was reused during the task."""
        self._skill_reused = True

    def record_successful_path(self, path: list[str]) -> None:
        """Record the successful sequence of actions/tools used."""
        self._successful_path.extend(path)

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def is_running(self) -> bool:
        return self._start_time is not None and self._end_time is None

    @property
    def elapsed(self) -> float:
        if self._start_time is None:
            return 0.0
        end = self._end_time if self._end_time is not None else time.monotonic()
        return end - self._start_time

    # ------------------------------------------------------------------
    # Finalisation
    # ------------------------------------------------------------------

    def finalise(self) -> BenchmarkMetrics:
        """Return an immutable metrics snapshot.

        Can be called even if ``stop()`` has not been called yet (in which
        case elapsed time is computed up to *now*).
        """
        return BenchmarkMetrics(
            success=self._success,
            turn_count=self._turn_count,
            tool_calls=self._tool_calls,
            elapsed_seconds=self.elapsed,
            recovery_count=self._recovery_count,
            skill_created=self._skill_created,
            skill_reused=self._skill_reused,
            successful_path=list(self._successful_path),
        )
