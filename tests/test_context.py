import pytest
from models import Message
from core.context import ContextBuilder
from browser.state import BrowserState

class MockPromptBuilder:
    def build(self):
        return "mocked system rules"

class MockMemoryService:
    def get_environment_facts(self, query):
        return [{"content": "Ubuntu 22.04"}, {"content": "Python 3.12"}]
        
    def get_relevant_skills(self, query):
        return [{"name": "grep_search", "content": "Use grep to search files"}]

def test_context_builder_basic():
    builder = ContextBuilder()
    context = builder.build_context("System Agent.", "Hello", max_history=10)
    
    assert len(context) == 2
    assert context[0].role == "system"
    assert context[0].content == "System Agent."
    assert context[1].role == "user"
    assert context[1].content == "Hello"

def test_context_builder_with_all_components():
    builder = ContextBuilder(
        prompt_builder=MockPromptBuilder(),
        memory_service=MockMemoryService(),
        browser_state=BrowserState(current_url="https://example.com")
    )
    
    history = [
        Message(role="user", content="prev user"),
        Message(role="assistant", content="prev asst")
    ]
    
    context = builder.build_context(
        system_prompt="Base System.",
        user_input="Current query",
        checkpoint="My checkpoint",
        history=history,
        max_history=5
    )
    
    assert len(context) == 4 # 1 system, 2 history, 1 current user
    
    sys_content = context[0].content
    assert context[0].role == "system"
    assert "Base System." in sys_content
    assert "mocked system rules" in sys_content
    assert "Environment Facts:" in sys_content
    assert "- Ubuntu 22.04" in sys_content
    assert "Top Skills:" in sys_content
    assert "- grep_search: Use grep to search files" in sys_content
    assert "Working Checkpoint:\nMy checkpoint" in sys_content
    assert "Recent Browser State:" in sys_content
    assert "https://example.com" in sys_content
    
    assert context[1].content == "prev user"
    assert context[2].content == "prev asst"
    assert context[3].content == "Current query"

def test_context_builder_max_history():
    builder = ContextBuilder()
    
    history = [
        Message(role="user", content="msg1"),
        Message(role="assistant", content="msg2"),
        Message(role="user", content="msg3"),
        Message(role="assistant", content="msg4"),
    ]
    
    context = builder.build_context(
        system_prompt="sys",
        user_input="user",
        history=history,
        max_history=2
    )
    
    # 1 system + 2 history + 1 user
    assert len(context) == 4
    assert context[1].content == "msg3"
    assert context[2].content == "msg4"

def test_context_builder_backward_compat():
    builder = ContextBuilder()
    messages = builder.build("Sys prompt", "User query")
    assert len(messages) == 2
    assert messages[0].content == "Sys prompt"
    assert messages[1].content == "User query"
