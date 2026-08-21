"""Context compression for older conversation history.

Compresses older messages to reduce token usage while preserving:
- Recent messages (last N)
- Active task facts / checkpoint content
- Current skill references
- Important state (errors, goals)

Compresses:
- Thinking blocks (removed entirely)
- Tool results (truncated to summary)
- Old browser observations (stripped to essentials)
- Old conversation (summarised)
"""

from __future__ import annotations

import re
from typing import List, Optional

from models import Message

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

# Number of recent messages to keep verbatim (not compressed).
DEFAULT_KEEP_RECENT = 6

# Maximum character length for a compressed tool result.
MAX_TOOL_RESULT_LEN = 300

# Maximum character length for a compressed assistant message.
MAX_ASSISTANT_CONTENT_LEN = 400

# Marker prepended to content that was compressed.
COMPRESSED_MARKER = "[compressed] "

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_THINKING_RE = re.compile(
    r"<thinking>.*?</thinking>", re.DOTALL | re.IGNORECASE
)

_BROWSER_OBSERVATION_RE = re.compile(
    r"(Screenshot|DOM snapshot|Page HTML|Visible text|Browser observation)[:\s].*",
    re.DOTALL | re.IGNORECASE,
)


def _strip_thinking(text: str) -> str:
    """Remove ``<thinking>…</thinking>`` blocks."""
    return _THINKING_RE.sub("", text).strip()


def _truncate(text: str, limit: int) -> str:
    """Truncate *text* to *limit* characters, appending '…' when trimmed."""
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "…"


def _compress_tool_result(content: str) -> str:
    """Compress a tool-role message body.

    * Strips thinking blocks.
    * Strips verbose browser observations.
    * Truncates the remainder.
    """
    text = _strip_thinking(content)
    text = _BROWSER_OBSERVATION_RE.sub("[browser observation removed]", text)
    return COMPRESSED_MARKER + _truncate(text, MAX_TOOL_RESULT_LEN)


def _compress_assistant(content: str) -> str:
    """Compress an assistant-role message body.

    * Strips thinking blocks.
    * Truncates long output.
    """
    text = _strip_thinking(content)
    return COMPRESSED_MARKER + _truncate(text, MAX_ASSISTANT_CONTENT_LEN)


def _compress_browser_state(content: str) -> str:
    """Compress old browser state / observation in user or system messages."""
    text = _BROWSER_OBSERVATION_RE.sub("[browser observation removed]", content)
    text = _strip_thinking(text)
    return COMPRESSED_MARKER + _truncate(text, MAX_ASSISTANT_CONTENT_LEN)


def _is_important(msg: Message) -> bool:
    """Return ``True`` if a message should never be compressed.

    Protected messages:
    * System messages (they carry rules, checkpoints, skills, env facts).
    * Messages that look like checkpoint or skill references.
    * Error/failure notices that inform future decisions.
    """
    if msg.role == "system":
        return True
    c = (msg.content or "").lower()
    important_keywords = [
        "checkpoint",
        "current goal",
        "current task",
        "active skill",
        "error",
        "failure",
        "important",
        "constraint",
    ]
    return any(kw in c for kw in important_keywords)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def compress_history(
    messages: List[Message],
    *,
    keep_recent: int = DEFAULT_KEEP_RECENT,
    max_tool_result_len: int = MAX_TOOL_RESULT_LEN,
    max_assistant_content_len: int = MAX_ASSISTANT_CONTENT_LEN,
) -> List[Message]:
    """Return a compressed copy of *messages*.

    The last *keep_recent* messages are always returned verbatim.
    Older messages are selectively compressed:

    * **System** messages are kept as-is (they carry rules, skills, facts).
    * **Tool** messages have their content truncated / browser observations
      stripped.
    * **Assistant** messages have thinking blocks removed and content
      truncated.
    * **User** messages with large browser observations are trimmed.
    * Messages flagged as *important* (errors, checkpoints, goals) are kept
      intact regardless of age.

    Parameters
    ----------
    messages:
        Full conversation history.
    keep_recent:
        Number of trailing messages to preserve verbatim.
    max_tool_result_len:
        Max chars for a compressed tool result.
    max_assistant_content_len:
        Max chars for a compressed assistant message.

    Returns
    -------
    List[Message]
        A new list with the same length as *messages*, where older entries
        may have had their ``.content`` replaced with a compressed version.
    """
    if not messages:
        return []

    n = len(messages)
    boundary = max(0, n - keep_recent)

    result: List[Message] = []
    for idx, msg in enumerate(messages):
        # Recent window – keep verbatim.
        if idx >= boundary:
            result.append(msg.model_copy())
            continue

        # Important messages – keep verbatim regardless of age.
        if _is_important(msg):
            result.append(msg.model_copy())
            continue

        # --- Compress older messages ---
        compressed = msg.model_copy()
        content = compressed.content or ""

        def _compress_tool(text: str) -> str:
            text = _strip_thinking(text)
            text = _BROWSER_OBSERVATION_RE.sub("[browser observation removed]", text)
            return COMPRESSED_MARKER + _truncate(text, max_tool_result_len)

        def _compress_asst(text: str) -> str:
            text = _strip_thinking(text)
            return COMPRESSED_MARKER + _truncate(text, max_assistant_content_len)

        def _compress_browser(text: str) -> str:
            text = _BROWSER_OBSERVATION_RE.sub("[browser observation removed]", text)
            text = _strip_thinking(text)
            return COMPRESSED_MARKER + _truncate(text, max_assistant_content_len)

        if msg.role == "tool":
            compressed.content = _compress_tool(content)
        elif msg.role == "assistant":
            # Keep tool_calls intact – only compress the text body.
            if content:
                compressed.content = _compress_asst(content)
        elif msg.role == "user":
            # Large user messages with browser observations.
            if len(content) > max_assistant_content_len:
                compressed.content = _compress_browser(content)

        result.append(compressed)

    return result
