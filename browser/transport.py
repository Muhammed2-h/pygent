import asyncio
import json
import logging
import uuid
from typing import Any, Dict, List, Optional, Set
from aiohttp import web, WSMsgType

logger = logging.getLogger(__name__)

class BrowserTransport:
    """Transport layer for browser communication."""
    
    def __init__(self, host: str = "127.0.0.1", ws_port: int = 18765, http_port: int = 18766):
        self.host = host
        self.ws_port = ws_port
        self.http_port = http_port
        
        self.sessions: Set[str] = set()
        
        self._pending_commands: Dict[str, List[Dict[str, Any]]] = {}
        self._command_events: Dict[str, asyncio.Event] = {}
        
        self._result_queues: Dict[str, asyncio.Queue] = {}
        self._http_sent_ids: Dict[str, Set[str]] = {}
        
        self._active_ws: Dict[str, web.WebSocketResponse] = {}
        self._tasks: Set[asyncio.Task] = set()
        
        self._ws_app = web.Application()
        self._ws_app.router.add_get('/ws', self._ws_handler)
        self._ws_runner: Optional[web.AppRunner] = None
        
        self._http_app = web.Application(middlewares=[self._cors_middleware])
        self._http_app.router.add_get('/poll', self._http_poll_handler)
        self._http_app.router.add_post('/result', self._http_result_handler)
        self._http_runner: Optional[web.AppRunner] = None

    @web.middleware
    async def _cors_middleware(self, request: web.Request, handler) -> web.Response:
        # For HTTP endpoints
        response = await handler(request)
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        return response

    async def start_ws_server(self):
        self._ws_runner = web.AppRunner(self._ws_app)
        await self._ws_runner.setup()
        site = web.TCPSite(self._ws_runner, self.host, self.ws_port)
        await site.start()
        logger.info(f"WebSocket server started on {self.host}:{self.ws_port}")

    async def start_http_server(self):
        self._http_runner = web.AppRunner(self._http_app)
        await self._http_runner.setup()
        site = web.TCPSite(self._http_runner, self.host, self.http_port)
        await site.start()
        logger.info(f"HTTP fallback server started on {self.host}:{self.http_port}")
        
    async def stop(self):
        for task in list(self._tasks):
            task.cancel()
        if self._ws_runner:
            await self._ws_runner.cleanup()
        if self._http_runner:
            await self._http_runner.cleanup()

    def register_session(self, session_id: str):
        self.sessions.add(session_id)
        if session_id not in self._pending_commands:
            self._pending_commands[session_id] = []
        if session_id not in self._command_events:
            self._command_events[session_id] = asyncio.Event()
        if session_id not in self._result_queues:
            self._result_queues[session_id] = asyncio.Queue()
        if session_id not in self._http_sent_ids:
            self._http_sent_ids[session_id] = set()

    def unregister_session(self, session_id: str):
        self.sessions.discard(session_id)
        if session_id in self._pending_commands:
            del self._pending_commands[session_id]
        if session_id in self._command_events:
            del self._command_events[session_id]
        if session_id in self._result_queues:
            del self._result_queues[session_id]
        if session_id in self._http_sent_ids:
            del self._http_sent_ids[session_id]
        if session_id in self._active_ws:
            ws = self._active_ws.pop(session_id)
            task = asyncio.create_task(ws.close())
            self._tasks.add(task)
            task.add_done_callback(self._tasks.discard)

    async def send_command(self, session_id: str, command: Dict[str, Any]) -> str:
        if session_id not in self.sessions:
            raise ValueError(f"Unknown session {session_id}")
            
        message_id = str(uuid.uuid4())
        cmd_wrapper = {"message_id": message_id, "command": command}
        self._pending_commands[session_id].append(cmd_wrapper)
        
        self._command_events[session_id].set()
        return message_id

    async def receive_result(self, session_id: str, timeout: Optional[float] = None) -> Dict[str, Any]:
        if session_id not in self.sessions:
            raise ValueError(f"Unknown session {session_id}")
        
        if timeout is not None:
            return await asyncio.wait_for(self._result_queues[session_id].get(), timeout)
        else:
            return await self._result_queues[session_id].get()

    def acknowledge(self, session_id: str, message_id: str):
        """Acknowledge a received message."""
        if session_id in self._pending_commands:
            self._pending_commands[session_id] = [
                cmd for cmd in self._pending_commands[session_id]
                if cmd["message_id"] != message_id
            ]

    async def _ws_handler(self, request: web.Request):
        origin = request.headers.get("Origin")
        if origin:
            allowed = ["http://127.0.0.1", "http://localhost", "https://127.0.0.1", "https://localhost"]
            if not origin.startswith("chrome-extension://") and \
               not origin.startswith("moz-extension://") and \
               not origin.startswith("safari-extension://") and \
               not any(origin.startswith(a) for a in allowed):
                logger.warning(f"Rejecting WS connection from forbidden Origin: {origin}")
                return web.Response(status=403, text="Forbidden")

        session_id = request.query.get("session_id")
        if not session_id or session_id not in self.sessions:
            return web.Response(status=401, text="Invalid or missing session_id")
            
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        
        self._active_ws[session_id] = ws
        
        async def send_loop():
            sent_ids = set()
            try:
                while True:
                    pending = self._pending_commands.get(session_id, [])
                    to_send = [cmd for cmd in pending if cmd["message_id"] not in sent_ids]
                    
                    if to_send:
                        for cmd in to_send:
                            await ws.send_json(cmd)
                            sent_ids.add(cmd["message_id"])
                    else:
                        self._command_events[session_id].clear()
                        # Double-check after clearing the event to avoid race condition
                        pending = self._pending_commands.get(session_id, [])
                        to_send = [cmd for cmd in pending if cmd["message_id"] not in sent_ids]
                        if not to_send:
                            await self._command_events[session_id].wait()
            except asyncio.CancelledError:
                pass
            except Exception as e:
                logger.error(f"Error sending to WS: {e}")

        send_task = asyncio.create_task(send_loop())
        self._tasks.add(send_task)
        send_task.add_done_callback(self._tasks.discard)
        
        try:
            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
                    try:
                        data = json.loads(msg.data)
                        await self._result_queues[session_id].put(data)
                    except Exception as e:
                        logger.error(f"Failed to parse WS message: {e}")
                elif msg.type == WSMsgType.ERROR:
                    logger.error(f"WS connection closed with exception {ws.exception()}")
        finally:
            send_task.cancel()
            if self._active_ws.get(session_id) == ws:
                del self._active_ws[session_id]
            
        return ws

    async def _http_poll_handler(self, request: web.Request):
        """Long poll endpoint for commands."""
        if request.method == 'OPTIONS':
            return web.Response(status=200)
            
        session_id = request.query.get("session_id")
        if not session_id or session_id not in self.sessions:
            return web.Response(status=401, text="Invalid or missing session_id")
            
        pending = self._pending_commands.get(session_id, [])
        unsent = [cmd for cmd in pending if cmd["message_id"] not in self._http_sent_ids[session_id]]
        
        if not unsent:
            self._command_events[session_id].clear()
            # Double check
            pending = self._pending_commands.get(session_id, [])
            unsent = [cmd for cmd in pending if cmd["message_id"] not in self._http_sent_ids[session_id]]
            if not unsent:
                try:
                    await asyncio.wait_for(self._command_events[session_id].wait(), timeout=30.0)
                except asyncio.TimeoutError:
                    return web.json_response({})
            pending = self._pending_commands.get(session_id, [])
            unsent = [cmd for cmd in pending if cmd["message_id"] not in self._http_sent_ids[session_id]]
            
        if unsent:
            cmd = unsent[0]
            msg_id = cmd["message_id"]
            self._http_sent_ids[session_id].add(msg_id)
            
            async def timeout_unacked():
                await asyncio.sleep(30.0)
                if session_id in self._http_sent_ids and msg_id in self._http_sent_ids[session_id]:
                    # Check if still pending
                    if session_id in self._pending_commands and any(c["message_id"] == msg_id for c in self._pending_commands[session_id]):
                        self._http_sent_ids[session_id].remove(msg_id)
                        if session_id in self._command_events:
                            self._command_events[session_id].set()

            task = asyncio.create_task(timeout_unacked())
            self._tasks.add(task)
            task.add_done_callback(self._tasks.discard)
            
            return web.json_response(cmd)
            
        return web.json_response({})

    async def _http_result_handler(self, request: web.Request):
        """Endpoint to submit results."""
        if request.method == 'OPTIONS':
            return web.Response(status=200)
            
        session_id = request.query.get("session_id")
        if not session_id or session_id not in self.sessions:
            return web.Response(status=401, text="Invalid or missing session_id")
            
        try:
            data = await request.json()
            await self._result_queues[session_id].put(data)
            return web.json_response({"status": "ok"})
        except Exception as e:
            logger.error(f"Failed to parse HTTP result: {e}")
            return web.Response(status=400, text="Invalid JSON")
