import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock

from browser.driver import BrowserDriver
from browser.models import ExtensionResponse

@pytest.mark.asyncio
async def test_browser_screenshot():
    mock_transport = AsyncMock()
    
    async def mock_send_command(session_id, req):
        return f"msg_{req.payload.get('method', 'unknown')}"
        
    async def mock_receive_result(session_id, msg_id, timeout):
        if "Runtime.evaluate" in msg_id:
            return ExtensionResponse(
                id=msg_id,
                ok=True,
                data={
                    "result": {
                        "type": "object",
                        "value": {
                            "width": 1024,
                            "height": 768
                        }
                    }
                }
            )
        elif "Page.captureScreenshot" in msg_id:
            return ExtensionResponse(
                id=msg_id,
                ok=True,
                data={
                    "data": "base64encodedstring"
                }
            )
        return ExtensionResponse(id=msg_id, ok=True, data={})

    mock_transport.send_command.side_effect = mock_send_command
    mock_transport.receive_result.side_effect = mock_receive_result
    
    # We need to mock acknowledge if it's called
    mock_transport.acknowledge = MagicMock()
    
    driver = BrowserDriver(transport=mock_transport)
    
    result = await driver.browser_screenshot("session1", 42)
    
    assert result["base64"] == "base64encodedstring"
    assert result["mime_type"] == "image/png"
    assert result["width"] == 1024
    assert result["height"] == 768
    
    assert mock_transport.send_command.call_count == 2
    assert mock_transport.receive_result.call_count == 2

@pytest.mark.asyncio
async def test_browser_screenshot_default_dimensions():
    mock_transport = AsyncMock()
    
    async def mock_send_command(session_id, req):
        return f"msg_{req.payload.get('method', 'unknown')}"
        
    async def mock_receive_result(session_id, msg_id, timeout):
        if "Runtime.evaluate" in msg_id:
            # Simulate failure to get dimensions (e.g. exception)
            return ExtensionResponse(
                id=msg_id,
                ok=True,
                data={
                    "exceptionDetails": {"text": "Error"}
                }
            )
        elif "Page.captureScreenshot" in msg_id:
            return ExtensionResponse(
                id=msg_id,
                ok=True,
                data={
                    "data": "base64encodedstring2"
                }
            )
        return ExtensionResponse(id=msg_id, ok=True, data={})

    mock_transport.send_command.side_effect = mock_send_command
    mock_transport.receive_result.side_effect = mock_receive_result
    mock_transport.acknowledge = MagicMock()
    
    driver = BrowserDriver(transport=mock_transport)
    
    result = await driver.browser_screenshot("session1", 42)
    
    assert result["base64"] == "base64encodedstring2"
    assert result["mime_type"] == "image/png"
    assert result["width"] == 800  # Default
    assert result["height"] == 600 # Default
