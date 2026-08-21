import pytest
import asyncio
from unittest.mock import patch, AsyncMock, MagicMock
from cli.browser_repl import async_start_browser_repl

@pytest.mark.asyncio
async def test_browser_repl_managed(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr("os.path.expanduser", lambda p: str(tmp_path) if "~" in p else p)
    
    # Mock input to return /quit immediately
    def mock_input(prompt=""):
        return "/quit"
    
    monkeypatch.setattr("builtins.input", mock_input)
    
    def mock_create_provider(config):
        class MockProvider:
            def complete(self, messages, model, tools):
                from models import Message
                return type('MockResponse', (), {'messages': [Message(role="assistant", content="Done")]})()
        return MockProvider()
        
    monkeypatch.setattr("cli.browser_repl.create_provider", mock_create_provider)
    
    # We want to mock transport
    with patch("cli.browser_repl.BrowserTransport") as mock_transport_cls:
        mock_transport = MagicMock()
        mock_transport.start_ws_server = AsyncMock()
        mock_transport.start_http_server = AsyncMock()
        mock_transport.stop = AsyncMock()
        
        # Make is_connected return True eventually to break out of the 150 wait loop
        is_conn_mock = MagicMock(side_effect=[False, False, True, True, True, True, True, True, True])
        mock_transport.is_connected = is_conn_mock
        mock_transport_cls.return_value = mock_transport
        
        with patch("cli.browser_repl.subprocess.Popen") as mock_popen, \
             patch("cli.browser_repl.shutil.rmtree") as mock_rmtree, \
             patch("cli.browser_repl.Path.mkdir") as mock_mkdir:
             
            mock_proc = MagicMock()
            mock_proc.terminate = MagicMock()
            mock_proc.wait = MagicMock()
            mock_popen.return_value = mock_proc
            
            with patch("cli.browser_repl.BrowserDriver") as mock_driver_cls:
                mock_driver = MagicMock()
                mock_driver.enumerate_tabs = AsyncMock(return_value=[{"id": 1, "url": "about:blank", "title": "Blank"}])
                mock_driver_cls.return_value = mock_driver
                
                with patch("cli.browser_repl.CDPClient"), patch("cli.browser_repl.BrowserObserver"):
                    await async_start_browser_repl(str(tmp_path / "mem.db"), str(tmp_path / "skills"), managed=True)
                    
                    # Verify Popen was called (browser launched)
                    assert mock_popen.called
                    cmd_args = mock_popen.call_args[0][0]
                    assert any("--user-data-dir=" in arg and "browser/profile" in arg for arg in cmd_args)
                    
                    # Verify rmtree was called (clear profile)
                    assert mock_rmtree.called
                    # But NOT on exit!
                    # Wait, is rmtree called on exit? No, we suppressed it for managed.
                    # Wait, rmtree is called at the start to ensure fresh session.
                    assert mock_rmtree.call_count == 1
                    
                    # Verify input was called (actually we mocked it)
