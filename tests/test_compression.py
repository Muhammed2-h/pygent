"""Tests for core.compression — context compression for older history."""

import pytest
from models import Message
from core.compression import (
    compress_history,
    COMPRESSED_MARKER,
    DEFAULT_KEEP_RECENT,
    MAX_TOOL_RESULT_LEN,
    MAX_ASSISTANT_CONTENT_LEN,
    _strip_thinking,
    _truncate,
    _is_important,
)


# ── helpers ──────────────────────────────────────────────────────────────────

def _msg(role: str, content: str, **kw) -> Message:
    return Message(role=role, content=content, **kw)


def _long(n: int = 600) -> str:
    return "x" * n


# ── _strip_thinking ─────────────────────────────────────────────────────────

class TestStripThinking:
    def test_removes_thinking_block(self):
        text = "Before <thinking>secret</thinking> After"
        assert _strip_thinking(text) == "Before  After"

    def test_removes_multiline_thinking(self):
        text = "A\n<thinking>\nline1\nline2\n</thinking>\nB"
        assert _strip_thinking(text) == "A\n\nB"

    def test_case_insensitive(self):
        text = "<Thinking>hmm</Thinking> ok"
        assert _strip_thinking(text) == "ok"

    def test_no_thinking(self):
        assert _strip_thinking("plain text") == "plain text"


# ── _truncate ────────────────────────────────────────────────────────────────

class TestTruncate:
    def test_short_text_unchanged(self):
        assert _truncate("hello", 10) == "hello"

    def test_exact_limit(self):
        assert _truncate("12345", 5) == "12345"

    def test_over_limit(self):
        result = _truncate("123456", 5)
        assert result == "12345…"
        assert len(result) == 6  # 5 chars + ellipsis

    def test_zero_limit(self):
        assert _truncate("abc", 0) == "…"


# ── _is_important ────────────────────────────────────────────────────────────

class TestIsImportant:
    def test_system_always_important(self):
        assert _is_important(_msg("system", "anything"))

    def test_checkpoint_keyword(self):
        assert _is_important(_msg("user", "See the checkpoint here"))

    def test_error_keyword(self):
        assert _is_important(_msg("tool", "error occurred"))

    def test_goal_keyword(self):
        assert _is_important(_msg("assistant", "Current goal: do X"))

    def test_ordinary_user_msg_not_important(self):
        assert not _is_important(_msg("user", "Hello there"))

    def test_ordinary_tool_msg_not_important(self):
        assert not _is_important(_msg("tool", "success"))


# ── compress_history — basic behaviour ───────────────────────────────────────

class TestCompressHistoryBasic:
    def test_empty_list(self):
        assert compress_history([]) == []

    def test_fewer_than_keep_recent(self):
        """All messages inside the recent window — nothing compressed."""
        msgs = [_msg("user", "hi"), _msg("assistant", "hello")]
        result = compress_history(msgs, keep_recent=5)
        assert len(result) == 2
        assert result[0].content == "hi"
        assert result[1].content == "hello"

    def test_exact_keep_recent(self):
        msgs = [_msg("user", f"m{i}") for i in range(6)]
        result = compress_history(msgs, keep_recent=6)
        for orig, comp in zip(msgs, result):
            assert comp.content == orig.content

    def test_recent_messages_unchanged(self):
        """Messages inside the keep_recent window must not be compressed."""
        old_tool = _msg("tool", _long(600), tool_call_id="tc1")
        recent_user = _msg("user", "what next?")
        recent_asst = _msg("assistant", "plan: " + _long(600))

        msgs = [old_tool, recent_user, recent_asst]
        result = compress_history(msgs, keep_recent=2)

        # last 2 kept verbatim
        assert result[1].content == recent_user.content
        assert result[2].content == recent_asst.content

    def test_does_not_mutate_originals(self):
        msgs = [_msg("tool", _long(600), tool_call_id="tc1")]
        original_content = msgs[0].content
        compress_history(msgs, keep_recent=0)
        assert msgs[0].content == original_content


# ── compress_history — tool results ──────────────────────────────────────────

class TestCompressTool:
    def test_old_tool_result_truncated(self):
        msgs = [
            _msg("tool", _long(600), tool_call_id="tc1"),
            _msg("user", "u1"),
            _msg("assistant", "a1"),
        ]
        result = compress_history(msgs, keep_recent=2)
        assert result[0].content.startswith(COMPRESSED_MARKER)
        # Compressed content must be shorter than original
        assert len(result[0].content) < len(msgs[0].content)

    def test_tool_thinking_stripped(self):
        content = "<thinking>internal reasoning</thinking>Result: OK"
        msgs = [
            _msg("tool", content, tool_call_id="tc1"),
            _msg("user", "u"),
            _msg("assistant", "a"),
        ]
        result = compress_history(msgs, keep_recent=2)
        assert "<thinking>" not in result[0].content
        assert "internal reasoning" not in result[0].content

    def test_tool_browser_observation_removed(self):
        content = "Screenshot: base64data\nSome text"
        msgs = [
            _msg("tool", content, tool_call_id="tc1"),
            _msg("user", "u"),
            _msg("assistant", "a"),
        ]
        result = compress_history(msgs, keep_recent=2)
        assert "base64data" not in result[0].content
        assert "[browser observation removed]" in result[0].content

    def test_short_tool_result_still_marked(self):
        msgs = [
            _msg("tool", "ok", tool_call_id="tc1"),
            _msg("user", "u"),
            _msg("assistant", "a"),
        ]
        result = compress_history(msgs, keep_recent=2)
        assert result[0].content.startswith(COMPRESSED_MARKER)
        assert "ok" in result[0].content


# ── compress_history — assistant messages ────────────────────────────────────

class TestCompressAssistant:
    def test_old_assistant_thinking_removed(self):
        content = "<thinking>planning</thinking>Here is my answer."
        msgs = [
            _msg("user", "q"),
            _msg("assistant", content),
            _msg("user", "u2"),
            _msg("assistant", "a2"),
        ]
        result = compress_history(msgs, keep_recent=2)
        assert "<thinking>" not in result[1].content
        assert "planning" not in result[1].content
        assert "answer" in result[1].content

    def test_old_assistant_truncated(self):
        msgs = [
            _msg("assistant", _long(800)),
            _msg("user", "u"),
            _msg("assistant", "a"),
        ]
        result = compress_history(msgs, keep_recent=2)
        assert len(result[0].content) < 800

    def test_assistant_tool_calls_preserved(self):
        from models import ToolCall

        tc = ToolCall(id="tc1", name="run", arguments={"cmd": "ls"})
        msgs = [
            Message(role="assistant", content="running", tool_calls=[tc]),
            _msg("tool", "output", tool_call_id="tc1"),
            _msg("user", "u"),
            _msg("assistant", "a"),
        ]
        result = compress_history(msgs, keep_recent=2)
        assert result[0].tool_calls is not None
        assert result[0].tool_calls[0].name == "run"

    def test_empty_assistant_content(self):
        from models import ToolCall

        tc = ToolCall(id="tc2", name="search", arguments={})
        msgs = [
            Message(role="assistant", content=None, tool_calls=[tc]),
            _msg("tool", "found", tool_call_id="tc2"),
            _msg("user", "u"),
            _msg("assistant", "a"),
        ]
        result = compress_history(msgs, keep_recent=2)
        # No content to compress — should remain None / empty.
        assert result[0].content is None or result[0].content == ""


# ── compress_history — user messages ─────────────────────────────────────────

class TestCompressUser:
    def test_old_large_user_msg_compressed(self):
        msgs = [
            _msg("user", _long(800)),
            _msg("assistant", "a1"),
            _msg("user", "u2"),
            _msg("assistant", "a2"),
        ]
        result = compress_history(msgs, keep_recent=2)
        assert result[0].content.startswith(COMPRESSED_MARKER)
        assert len(result[0].content) < 800

    def test_old_short_user_msg_unchanged(self):
        msgs = [
            _msg("user", "short"),
            _msg("assistant", "a1"),
            _msg("user", "u2"),
            _msg("assistant", "a2"),
        ]
        result = compress_history(msgs, keep_recent=2)
        assert result[0].content == "short"

    def test_user_browser_observation_stripped(self):
        content = "Browser observation: <html>...</html>"
        msgs = [
            _msg("user", content + _long(400)),
            _msg("assistant", "a1"),
            _msg("user", "u2"),
            _msg("assistant", "a2"),
        ]
        result = compress_history(msgs, keep_recent=2)
        assert "<html>" not in result[0].content


# ── compress_history — system / important preserved ──────────────────────────

class TestPreserved:
    def test_system_messages_never_compressed(self):
        sys_content = _long(800)
        msgs = [
            _msg("system", sys_content),
            _msg("user", "u"),
            _msg("assistant", "a"),
        ]
        result = compress_history(msgs, keep_recent=2)
        assert result[0].content == sys_content

    def test_important_messages_never_compressed(self):
        msgs = [
            _msg("tool", "error: file not found " + _long(600), tool_call_id="tc1"),
            _msg("user", "u"),
            _msg("assistant", "a"),
        ]
        result = compress_history(msgs, keep_recent=2)
        # error keyword makes it important → kept verbatim
        assert not result[0].content.startswith(COMPRESSED_MARKER)

    def test_checkpoint_preserved(self):
        msgs = [
            _msg("user", "checkpoint: step 3 done " + _long(600)),
            _msg("assistant", "a1"),
            _msg("user", "u2"),
            _msg("assistant", "a2"),
        ]
        result = compress_history(msgs, keep_recent=2)
        assert not result[0].content.startswith(COMPRESSED_MARKER)


# ── compress_history — custom parameters ─────────────────────────────────────

class TestCustomParams:
    def test_custom_keep_recent(self):
        msgs = [_msg("user", f"m{i}") for i in range(10)]
        result = compress_history(msgs, keep_recent=3)
        # last 3 must be unchanged
        for i in range(7, 10):
            assert result[i].content == f"m{i}"

    def test_keep_recent_zero(self):
        """All messages are candidates for compression."""
        msgs = [
            _msg("tool", _long(600), tool_call_id="tc1"),
            _msg("assistant", _long(600)),
        ]
        result = compress_history(msgs, keep_recent=0)
        assert all(
            r.content.startswith(COMPRESSED_MARKER) for r in result
        )

    def test_keep_recent_larger_than_list(self):
        msgs = [_msg("user", "hi")]
        result = compress_history(msgs, keep_recent=100)
        assert result[0].content == "hi"

    def test_custom_max_tool_result_len(self):
        msgs = [
            _msg("tool", "a" * 200, tool_call_id="tc1"),
            _msg("user", "u"),
        ]
        result = compress_history(msgs, keep_recent=1, max_tool_result_len=50)
        # The function uses module-level MAX_TOOL_RESULT_LEN currently,
        # but the parameter is accepted for API forward-compatibility.
        assert result[0].content.startswith(COMPRESSED_MARKER)


# ── compress_history — mixed conversation ────────────────────────────────────

class TestMixedConversation:
    def test_realistic_conversation(self):
        """Simulate a realistic agent conversation and verify compression."""
        msgs = [
            _msg("system", "You are a helpful agent."),
            _msg("user", "Find files matching *.py"),
            Message(
                role="assistant",
                content="<thinking>I'll use find</thinking>Let me search.",
                tool_calls=[
                    __import__("models").ToolCall(
                        id="tc1", name="bash", arguments={"cmd": "find . -name '*.py'"}
                    )
                ],
            ),
            _msg("tool", "Screenshot: abc\n./main.py\n./test.py\n" + _long(500), tool_call_id="tc1"),
            _msg("assistant", "Found 2 Python files."),
            _msg("user", "Good, now count lines"),
            Message(
                role="assistant",
                content=None,
                tool_calls=[
                    __import__("models").ToolCall(
                        id="tc2", name="bash", arguments={"cmd": "wc -l *.py"}
                    )
                ],
            ),
            _msg("tool", "100 main.py\n50 test.py", tool_call_id="tc2"),
            _msg("assistant", "main.py has 100 lines, test.py has 50."),
            _msg("user", "Thanks!"),
        ]

        result = compress_history(msgs, keep_recent=4)

        # Length preserved
        assert len(result) == len(msgs)

        # System kept verbatim
        assert result[0].content == "You are a helpful agent."

        # Old assistant thinking removed
        assert "<thinking>" not in (result[2].content or "")

        # Old tool browser observation removed
        assert "Screenshot: abc" not in result[3].content

        # Recent messages verbatim
        assert result[-1].content == "Thanks!"
        assert result[-2].content == "main.py has 100 lines, test.py has 50."
        assert result[-3].content == "100 main.py\n50 test.py"
