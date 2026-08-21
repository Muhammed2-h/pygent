import pytest
import asyncio
from browser.models import ExtensionRequest

@pytest.mark.asyncio
async def test_recovery_transport_disconnect(browser_env):
    transport = browser_env["transport"]
    # We can't really crash chrome easily without tearing down the whole test session, 
    # but we can test that sending a command to an invalid session/tab handles it gracefully
    
    req = ExtensionRequest(cmd="execute", payload={"tabId": 999999, "script": "return 1;"})
    msg_id = await transport.send_command("default", req)
    
    resp = await transport.receive_result("default", msg_id, timeout=2.0)
    # The extension will fail to execute script on invalid tab
    assert resp.ok is False
    assert "No tab with id" in resp.error or "Missing" in resp.error or "not" in resp.error.lower()
