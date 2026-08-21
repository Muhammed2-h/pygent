import pytest
import asyncio
from unittest.mock import patch, AsyncMock, MagicMock
from cli.browser_repl import async_start_browser_repl

@pytest.mark.asyncio
async def test_browser_repl_tool_execution(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr("os.path.expanduser", lambda p: str(tmp_path) if "~" in p else p)
    
    # Mock input to return one message then /quit
    input_calls = ["do something in browser", "/quit"]
    def mock_input(prompt=""):
        if input_calls:
            return input_calls.pop(0)
        return "/quit"
    
    monkeypatch.setattr("builtins.input", mock_input)
    
    from models import Message, ToolCall
    
    class MockResponse:
        def __init__(self, msg):
            self.messages = [msg]

    class MockProvider:
        def __init__(self):
            self.calls = 0
            
        def complete(self, messages, model, tools):
            self.calls += 1
            if self.calls == 1:
                # Return a tool call to browser_execute_js
                tc = ToolCall(id="call_123", name="browser_execute_js", arguments={"session_id": "default", "tab_id": 1, "script": "return 1;"})
                return MockResponse(Message(role="assistant", content=None, tool_calls=[tc]))
            elif self.calls == 2:
                # Final answer
                return MockResponse(Message(role="assistant", content="Tool executed!"))
            return MockResponse(Message(role="assistant", content="Done"))

    def mock_create_provider(config):
        return MockProvider()
        
    monkeypatch.setattr("cli.browser_repl.create_provider", mock_create_provider)
    
    # We want to mock transport so it connects immediately
    with patch("cli.browser_repl.BrowserTransport") as mock_transport_cls:
        mock_transport = MagicMock()
        mock_transport.start_ws_server = AsyncMock()
        mock_transport.start_http_server = AsyncMock()
        mock_transport.stop = AsyncMock()
        mock_transport.is_connected = MagicMock(return_value=True)
        mock_transport_cls.return_value = mock_transport
        
        with patch("cli.browser_repl.BrowserDriver") as mock_driver_cls:
            mock_driver = MagicMock()
            mock_driver.enumerate_tabs = AsyncMock(return_value=[{"id": 1, "url": "about:blank", "title": "Blank"}])
            mock_driver.execute_js = AsyncMock(return_value={"result": 1})
            mock_driver_cls.return_value = mock_driver
            
            with patch("cli.browser_repl.CDPClient"), patch("cli.browser_repl.BrowserObserver"):
                await async_start_browser_repl(str(tmp_path / "mem.db"), str(tmp_path / "skills"))
                
                # Check that execute_js was called by the agent through the registry
                assert mock_driver.execute_js.call_count == 1
