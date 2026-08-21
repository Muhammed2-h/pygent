"""
Benchmark task definitions.

Each task is a data structure describing a browser automation scenario,
the fixture page it targets, the expected outcome, and an optional
callable that executes the task against a live browser.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Awaitable, Optional


class TaskCategory(str, Enum):
    """High-level category for grouping benchmark tasks."""

    NAVIGATION = "navigation"
    INTERACTION = "interaction"
    FORM = "form"
    TAB_MANAGEMENT = "tab_management"
    FILE_IO = "file_io"
    ADVANCED_DOM = "advanced_dom"
    CDP = "cdp"
    RECOVERY = "recovery"
    EVOLUTION = "evolution"


class TaskDifficulty(str, Enum):
    """Relative difficulty rating."""

    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


# Type alias for the optional live-execution callable.
# Signature: (driver, session_id, base_url) -> dict with at least {"success": bool}
TaskExecutor = Callable[..., Awaitable[dict[str, Any]]]


@dataclass(frozen=True)
class BenchmarkTask:
    """A single benchmark task definition.

    Parameters
    ----------
    task_id : str
        Unique identifier, e.g. ``"open_url"``.
    name : str
        Human-readable name shown in reports.
    description : str
        Longer explanation of what the task tests.
    category : TaskCategory
        Grouping category.
    difficulty : TaskDifficulty
        Relative difficulty.
    fixture_page : str | None
        Fixture HTML page from ``tests/browser/pages/`` used by this task.
        ``None`` when the task does not need a fixture page.
    expected_outcome : dict[str, Any]
        A dict describing the expected result for verification.
        Must at minimum contain ``{"success": True}``.
    tags : tuple[str, ...]
        Free-form tags for filtering.
    executor : TaskExecutor | None
        Optional async callable that performs the task against a live browser.
    """

    task_id: str
    name: str
    description: str
    category: TaskCategory
    difficulty: TaskDifficulty
    fixture_page: Optional[str] = None
    expected_outcome: dict[str, Any] = field(default_factory=lambda: {"success": True})
    tags: tuple[str, ...] = ()
    executor: Optional[TaskExecutor] = None

    # ------------------------------------------------------------------
    # Convenience helpers
    # ------------------------------------------------------------------

    @property
    def has_executor(self) -> bool:
        """Return ``True`` if a live executor is attached."""
        return self.executor is not None

    def matches_filter(
        self,
        *,
        category: Optional[TaskCategory] = None,
        difficulty: Optional[TaskDifficulty] = None,
        tags: Optional[set[str]] = None,
    ) -> bool:
        """Return ``True`` if the task matches **all** supplied filters."""
        if category is not None and self.category != category:
            return False
        if difficulty is not None and self.difficulty != difficulty:
            return False
        if tags is not None and not tags.issubset(set(self.tags)):
            return False
        return True


# ======================================================================
# Pre-defined benchmark tasks
# ======================================================================

BENCHMARK_TASKS: list[BenchmarkTask] = [
    BenchmarkTask(
        task_id="open_url",
        name="Open URL",
        description="Navigate to a given URL and verify the page loads.",
        category=TaskCategory.NAVIGATION,
        difficulty=TaskDifficulty.EASY,
        fixture_page="basic.html",
        expected_outcome={"success": True, "title": "Basic Test Page"},
        tags=("navigation", "basic"),
    ),
    BenchmarkTask(
        task_id="search_page",
        name="Search page",
        description="Search/scan the current page for specific text content.",
        category=TaskCategory.NAVIGATION,
        difficulty=TaskDifficulty.EASY,
        fixture_page="basic.html",
        expected_outcome={"success": True, "found_text": "Nested content inside a div."},
        tags=("navigation", "search"),
    ),
    BenchmarkTask(
        task_id="click_button",
        name="Click button",
        description="Click a button element and verify the DOM updates.",
        category=TaskCategory.INTERACTION,
        difficulty=TaskDifficulty.EASY,
        fixture_page="basic.html",
        expected_outcome={"success": True, "status_text": "Button clicked!"},
        tags=("interaction", "click"),
    ),
    BenchmarkTask(
        task_id="fill_form",
        name="Fill form",
        description="Fill in form fields (text, select, checkbox, radio).",
        category=TaskCategory.FORM,
        difficulty=TaskDifficulty.MEDIUM,
        fixture_page="form.html",
        expected_outcome={"success": True, "fields_filled": True},
        tags=("form", "input"),
    ),
    BenchmarkTask(
        task_id="submit_form",
        name="Submit form",
        description="Submit a form and verify the result message appears.",
        category=TaskCategory.FORM,
        difficulty=TaskDifficulty.MEDIUM,
        fixture_page="form.html",
        expected_outcome={"success": True, "submitted": True},
        tags=("form", "submit"),
    ),
    BenchmarkTask(
        task_id="open_new_tab",
        name="Open new tab",
        description="Open a URL in a new tab and verify it exists.",
        category=TaskCategory.TAB_MANAGEMENT,
        difficulty=TaskDifficulty.MEDIUM,
        fixture_page="navigation.html",
        expected_outcome={"success": True, "tab_count_increased": True},
        tags=("tabs", "open"),
    ),
    BenchmarkTask(
        task_id="switch_tabs",
        name="Switch tabs",
        description="Switch between browser tabs and verify active tab.",
        category=TaskCategory.TAB_MANAGEMENT,
        difficulty=TaskDifficulty.MEDIUM,
        fixture_page="navigation.html",
        expected_outcome={"success": True, "active_tab_changed": True},
        tags=("tabs", "switch"),
    ),
    BenchmarkTask(
        task_id="download_file",
        name="Download file",
        description="Trigger a file download and verify the file was received.",
        category=TaskCategory.FILE_IO,
        difficulty=TaskDifficulty.HARD,
        fixture_page="download.html",
        expected_outcome={"success": True, "file_downloaded": True},
        tags=("file", "download"),
    ),
    BenchmarkTask(
        task_id="upload_file",
        name="Upload file",
        description="Upload a file via a file-input element.",
        category=TaskCategory.FILE_IO,
        difficulty=TaskDifficulty.HARD,
        fixture_page="form.html",
        expected_outcome={"success": True, "file_uploaded": True},
        tags=("file", "upload"),
    ),
    BenchmarkTask(
        task_id="handle_spa",
        name="Handle SPA",
        description="Navigate within a single-page application using dynamic routing.",
        category=TaskCategory.ADVANCED_DOM,
        difficulty=TaskDifficulty.HARD,
        fixture_page="dynamic.html",
        expected_outcome={"success": True, "route_changed": True},
        tags=("spa", "dynamic"),
    ),
    BenchmarkTask(
        task_id="handle_iframe",
        name="Handle iframe",
        description="Interact with content inside an iframe.",
        category=TaskCategory.ADVANCED_DOM,
        difficulty=TaskDifficulty.HARD,
        fixture_page="iframe.html",
        expected_outcome={"success": True, "iframe_accessed": True},
        tags=("iframe", "advanced"),
    ),
    BenchmarkTask(
        task_id="handle_shadow_dom",
        name="Handle Shadow DOM",
        description="Access and interact with elements inside a Shadow DOM.",
        category=TaskCategory.ADVANCED_DOM,
        difficulty=TaskDifficulty.HARD,
        fixture_page="shadow.html",
        expected_outcome={"success": True, "shadow_element_found": True},
        tags=("shadow_dom", "advanced"),
    ),
    BenchmarkTask(
        task_id="use_cdp",
        name="Use CDP",
        description="Use the Chrome DevTools Protocol to interact with the page.",
        category=TaskCategory.CDP,
        difficulty=TaskDifficulty.HARD,
        fixture_page="basic.html",
        expected_outcome={"success": True, "cdp_command_executed": True},
        tags=("cdp", "devtools"),
    ),
    BenchmarkTask(
        task_id="recover_from_js_failure",
        name="Recover from JS failure",
        description="Detect and recover from a JavaScript error on the page.",
        category=TaskCategory.RECOVERY,
        difficulty=TaskDifficulty.HARD,
        fixture_page="dynamic.html",
        expected_outcome={"success": True, "recovered": True},
        tags=("recovery", "error"),
    ),
    BenchmarkTask(
        task_id="self_evolution_a",
        name="Self-Evolution (Task A)",
        description="Perform unknown browser workflow. Record skill creation.",
        category=TaskCategory.EVOLUTION,
        difficulty=TaskDifficulty.HARD,
        fixture_page="form.html",
        expected_outcome={"success": True, "skill_created": True},
        tags=("evolution", "learning"),
    ),
    BenchmarkTask(
        task_id="self_evolution_b",
        name="Self-Evolution (Task B)",
        description="Repeat related workflow. Expect skill reuse, fewer turns and failures.",
        category=TaskCategory.EVOLUTION,
        difficulty=TaskDifficulty.HARD,
        fixture_page="form.html",
        expected_outcome={"success": True, "skill_reused": True},
        tags=("evolution", "reuse"),
    ),
]


def get_task(task_id: str) -> BenchmarkTask:
    """Look up a benchmark task by *task_id*.

    Raises ``KeyError`` if not found.
    """
    for t in BENCHMARK_TASKS:
        if t.task_id == task_id:
            return t
    raise KeyError(f"Unknown benchmark task: {task_id!r}")


def filter_tasks(
    *,
    category: Optional[TaskCategory] = None,
    difficulty: Optional[TaskDifficulty] = None,
    tags: Optional[set[str]] = None,
) -> list[BenchmarkTask]:
    """Return the subset of ``BENCHMARK_TASKS`` matching all supplied filters."""
    return [
        t
        for t in BENCHMARK_TASKS
        if t.matches_filter(category=category, difficulty=difficulty, tags=tags)
    ]
