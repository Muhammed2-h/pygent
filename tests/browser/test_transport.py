import pytest
import asyncio
from browser.models import ExtensionRequest

@pytest.mark.asyncio
async def test_transport_connection(browser_env):
    transport = browser_env["transport"]
    session_id = browser_env["session_id"]
    
    assert transport.is_connected(session_id)

@pytest.mark.asyncio
async def test_transport_message_flow(browser_env):
    transport = browser_env["transport"]
    session_id = browser_env["session_id"]
    
    # Send a simple command like enumerate_tabs just to test the transport flow directly
    req = ExtensionRequest(cmd="enumerate_tabs", payload={})
    msg_id = await transport.send_command(session_id, req)
    
    resp = await transport.receive_result(session_id, msg_id, timeout=5.0)
    assert resp.ok
    assert isinstance(resp.data, list)
    
    transport.acknowledge(session_id, msg_id)
