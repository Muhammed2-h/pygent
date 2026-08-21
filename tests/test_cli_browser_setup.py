from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cli.browser_setup import check_port, find_chrome, run_diagnostics


def test_find_chrome():
    res = find_chrome()
    assert isinstance(res, str)

def test_check_port():
    res = check_port(18765)
    assert isinstance(res, bool)

@pytest.mark.asyncio
@patch('cli.browser_setup.Path.exists')
@patch('cli.browser_setup.find_chrome')
@patch('cli.browser_setup.check_port')
@patch('cli.browser_setup.subprocess.Popen')
@patch('cli.browser_setup.BrowserTransport')
@patch('cli.browser_setup.BrowserDriver')
async def test_run_diagnostics(mock_driver, mock_transport, mock_popen, mock_check_port, mock_find_chrome, mock_path_exists, capsys):
    mock_find_chrome.return_value = "/usr/bin/chromium"
    mock_path_exists.return_value = True
    mock_check_port.return_value = True
    
    mock_transport_instance = MagicMock()
    mock_transport_instance.start_ws_server = AsyncMock()
    mock_transport_instance.start_http_server = AsyncMock()
    mock_transport_instance.stop = AsyncMock()
    mock_transport_instance.is_connected.return_value = True
    mock_transport.return_value = mock_transport_instance
    
    mock_driver_instance = MagicMock()
    mock_driver.return_value = mock_driver_instance
    
    async def mock_enumerate_tabs(session_id):
        return [{"id": 1, "url": "http://example.com"}]
        
    async def mock_execute_js(session_id, tab_id, script):
        return {"result": 2}
        
    mock_driver_instance.enumerate_tabs = mock_enumerate_tabs
    mock_driver_instance.execute_js = mock_execute_js
    
    await run_diagnostics()
    
    captured = capsys.readouterr()
    assert "Browser Setup Diagnostics" in captured.out
    assert "Extension connects: WebSocket connected" in captured.out
    assert "Tabs are visible: Found 1 tabs" in captured.out
    assert "JavaScript execution works" in captured.out

