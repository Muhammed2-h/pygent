import asyncio
import pytest
from aiohttp import ClientSession, WSMsgType
from browser.transport import BrowserTransport

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
async def test_ws_communication(transport):
    transport.register_session("sess1")
    
    async def client_task():
        async with ClientSession() as session:
            async with session.ws_connect('http://127.0.0.1:18765/ws?session_id=sess1') as ws:
                # Wait for command
                msg = await ws.receive()
                assert msg.type == WSMsgType.TEXT
                assert msg.json() == {"cmd": "test"}
                
                # Send result
                await ws.send_json({"res": "ok"})
                
    task = asyncio.create_task(client_task())
    
    # Wait a bit for connection
    await asyncio.sleep(0.1)
    
    await transport.send_command("sess1", {"cmd": "test"})
    
    result = await transport.receive_result("sess1", timeout=1.0)
    assert result == {"res": "ok"}
    
    await task

@pytest.mark.asyncio
async def test_http_long_poll(transport):
    transport.register_session("sess2")
    
    async def client_task():
        async with ClientSession() as session:
            # Long poll for command
            async with session.get('http://127.0.0.1:18766/poll?session_id=sess2') as resp:
                assert resp.status == 200
                data = await resp.json()
                assert data == {"cmd": "test_http"}
                
            # Send result
            async with session.post('http://127.0.0.1:18766/result?session_id=sess2', json={"res": "ok_http"}) as resp:
                assert resp.status == 200
                
    task = asyncio.create_task(client_task())
    
    # Send command (will queue and then be picked up by poll)
    await transport.send_command("sess2", {"cmd": "test_http"})
    
    result = await transport.receive_result("sess2", timeout=1.0)
    assert result == {"res": "ok_http"}
    
    await task

@pytest.mark.asyncio
async def test_invalid_session(transport):
    async with ClientSession() as session:
        async with session.get('http://127.0.0.1:18766/poll?session_id=invalid') as resp:
            assert resp.status == 401
