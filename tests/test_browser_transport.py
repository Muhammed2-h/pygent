import asyncio
import pytest
from aiohttp import ClientSession, WSMsgType
from browser.transport import BrowserTransport
from browser.models import ExtensionRequest

import pytest_asyncio

@pytest_asyncio.fixture
async def transport():
    t = BrowserTransport(ws_port=18765, http_port=18766)
    await t.start_ws_server()
    await t.start_http_server()
    yield t
    await t.stop()

@pytest.mark.asyncio
async def test_register_unregister_session(transport):
    transport.register_session("sess1")
    assert "sess1" in transport.sessions
    
    transport.unregister_session("sess1")
    assert "sess1" not in transport.sessions

@pytest.mark.asyncio
async def test_ws_communication_and_ack(transport):
    transport.register_session("sess1")
    
    message_id_event = asyncio.Event()
    received_message_id = None
    
    async def client_task():
        nonlocal received_message_id
        async with ClientSession() as session:
            async with session.ws_connect('http://127.0.0.1:18765/ws?session_id=sess1') as ws:
                # Wait for command
                msg = await ws.receive()
                assert msg.type == WSMsgType.TEXT
                data = msg.json()
                
                assert "id" in data
                assert data["cmd"] == "test"
                received_message_id = data["id"]
                message_id_event.set()
                
                # Send result
                await ws.send_json({"id": data["id"], "ok": True, "data": {"res": "ok"}})
                
    task = asyncio.create_task(client_task())
    
    # Wait a bit for connection
    await asyncio.sleep(0.1)
    
    req = ExtensionRequest(cmd="test")
    msg_id = await transport.send_command("sess1", req)
    
    # Wait for the client to receive it
    await asyncio.wait_for(message_id_event.wait(), timeout=1.0)
    assert received_message_id == msg_id
    
    # It should still be in pending since not acked
    assert len(transport._pending_commands["sess1"]) == 1
    
    # Acknowledge
    transport.acknowledge("sess1", msg_id)
    assert len(transport._pending_commands["sess1"]) == 0
    
    result = await transport.receive_result("sess1", msg_id=msg_id, timeout=1.0)
    assert result.id == msg_id
    assert result.ok is True
    assert result.data == {"res": "ok"}
    
    await task

@pytest.mark.asyncio
async def test_http_long_poll_and_ack(transport):
    transport.register_session("sess2")
    
    msg_id_event = asyncio.Event()
    received_msg_id = None
    
    async def client_task():
        nonlocal received_msg_id
        async with ClientSession() as session:
            # Long poll for command
            async with session.get('http://127.0.0.1:18766/poll?session_id=sess2') as resp:
                assert resp.status == 200
                data = await resp.json()
                assert "id" in data
                assert data["cmd"] == "test_http"
                received_msg_id = data["id"]
                msg_id_event.set()
                
            # Send result
            async with session.post('http://127.0.0.1:18766/result?session_id=sess2', json={"id": data["id"], "ok": True, "data": {"res": "ok_http"}}) as resp:
                assert resp.status == 200
                
    task = asyncio.create_task(client_task())
    
    # Send command (will queue and then be picked up by poll)
    req = ExtensionRequest(cmd="test_http")
    msg_id = await transport.send_command("sess2", req)
    
    await asyncio.wait_for(msg_id_event.wait(), timeout=1.0)
    assert received_msg_id == msg_id
    
    # Still pending
    assert len(transport._pending_commands["sess2"]) == 1
    transport.acknowledge("sess2", msg_id)
    assert len(transport._pending_commands["sess2"]) == 0
    
    result = await transport.receive_result("sess2", msg_id=msg_id, timeout=1.0)
    assert result.id == msg_id
    assert result.ok is True
    assert result.data == {"res": "ok_http"}
    
    await task

@pytest.mark.asyncio
async def test_invalid_session(transport):
    async with ClientSession() as session:
        async with session.get('http://127.0.0.1:18766/poll?session_id=invalid') as resp:
            assert resp.status == 401
