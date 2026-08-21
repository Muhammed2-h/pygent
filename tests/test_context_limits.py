from core.compression import compress_history
from core.context import ContextBuilder
from models import Message


def test_context_limits_long_conversation():
    builder = ContextBuilder()
    
    # 1. Long conversation
    history = []
    for i in range(100):
        history.append(Message(role="user", content=f"User msg {i} " * 100))
        history.append(Message(role="assistant", content=f"<thinking>Thought {i}</thinking> Assistant msg {i} " * 100))
        
    context = builder.build_context(
        system_prompt="System prompt",
        user_input="User input",
        history=history,
        max_history=10 # ContextBuilder truncates to 10
    )
    
    compressed = compress_history(context, keep_recent=2, max_assistant_content_len=100)
    
    # Check length
    total_len = sum(len(m.content or "") for m in compressed)
    # 1 system + 10 history + 1 user = 12 messages.
    # Out of 10 history, 8 are compressed (keep_recent=2 applies to the end of the history? Wait, keep_recent applies to the whole context list)
    assert total_len < 6000, f"Total length is {total_len}, should be bounded"

def test_context_limits_large_browser_state():
    builder = ContextBuilder()
    
    # 2. Large browser state
    large_dom = "<div>" * 5000 + "Hello" + "</div>" * 5000
    browser_state = {"current_url": "https://example.com", "dom": large_dom, "tabs": ["tab"] * 100}
    
    context = builder.build_context(
        system_prompt="System prompt",
        user_input="User input",
        browser_state=browser_state
    )
    
    total_len = sum(len(m.content or "") for m in context)
    # Wait, ContextBuilder dumps the whole browser state into the system message. It does NOT compress it.
    # I will assert it is bounded, which will fail if ContextBuilder doesn't truncate it.
    assert total_len < 10000, f"Total length is {total_len}, browser state should be bounded"

def test_context_limits_large_tool_result():
    builder = ContextBuilder()
    
    # 3. Large tool result
    history = [
        Message(role="tool", content="Tool result output " * 10000, tool_call_id="call_1")
    ]
    
    context = builder.build_context(
        system_prompt="System",
        user_input="Input",
        history=history
    )
    
    compressed = compress_history(context, keep_recent=0, max_tool_result_len=300)
    
    total_len = sum(len(m.content or "") for m in compressed)
    assert total_len < 2000, f"Total length is {total_len}, tool result should be bounded"

def test_context_limits_large_skill_repository():
    class MockMemoryService:
        def get_relevant_skills(self, query):
            # Return skills with massive content
            return [
                {"name": f"skill_{i}", "content": "Skill content " * 1000, "prerequisites": "none"}
                for i in range(10) # many skills
            ]
            
    builder = ContextBuilder(memory_service=MockMemoryService())
    
    context = builder.build_context(
        system_prompt="System",
        user_input="Input"
    )
    
    total_len = sum(len(m.content or "") for m in context)
    assert total_len < 5000, f"Total length is {total_len}, skills should be bounded"

def test_context_limits_repeated_tool_calls():
    builder = ContextBuilder()
    
    # 5. Repeated tool calls
    history = []
    for i in range(50):
        history.append(Message(
            role="assistant", 
            content=f"Calling tool {i}",
            tool_calls=[{"name": "test_tool", "arguments": {"arg": "long_argument_" * 100}, "id": f"call_{i}"}]
        ))
        history.append(Message(
            role="tool", 
            content="Result " * 100, 
            tool_call_id=f"call_{i}"
        ))
        
    context = builder.build_context(
        system_prompt="System",
        user_input="Input",
        history=history,
        max_history=10
    )
    
    compressed = compress_history(context, keep_recent=0, max_assistant_content_len=100, max_tool_result_len=100)
    
    total_len = sum(len(m.content or "") for m in compressed)
    assert total_len < 3000, f"Total length is {total_len}, repeated tool calls should be bounded"
