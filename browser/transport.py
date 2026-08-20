import asyncio
import json
import logging
from typing import Any, Dict, Optional, Set
from aiohttp import web, WSMsgType

logger = logging.getLogger(__name__)

class BrowserTransport:
    """Transport layer for browser communication."""
    
    def __init__(self, host: str = "127.0.0.1", ws_port: int = 18765, http_port: int = 18766):
        self.host = host
        self.ws_port = ws_port
        self.http_port = http_port
        
        self.sessions: Set[str] = set()
        
        self._command_queues: Dict[str, asyncio.Queue] = {}
        self._result_queues: Dict[str, asyncio.Queue] = {}
        
        self._active_ws: Dict[str, web.WebSocketResponse] = {}
        
        self._ws_app = web.Application()
        self._ws_app.router.add_get('/ws', self._ws_handler)
        self._ws_runner: Optional[web.AppRunner] = None
        
        self._http_app = web.Application(middlewares=[self._cors_middleware])
        self._http_app.router.add_get('/poll', self._http_poll_handler)
        self._http_app.router.add_post('/result', self._http_result_handler)
        self._http_runner: Optional[web.AppRunner] = None

    @web.middleware
    async def _cors_middleware(self, request: web.Request, handler) -> web.Response:
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
        if self._ws_runner:
            await self._ws_runner.cleanup()
        if self._http_runner:
            await self._http_runner.cleanup()

    def register_session(self, session_id: str):
        self.sessions.add(session_id)
        if session_id not in self._command_queues:
            self._command_queues[session_id] = asyncio.Queue()
        if session_id not in self._result_queues:
            self._result_queues[session_id] = asyncio.Queue()

    def unregister_session(self, session_id: str):
        self.sessions.discard(session_id)
        if session_id in self._command_queues:
            del self._command_queues[session_id]
        if session_id in self._result_queues:
            del self._result_queues[session_id]
        if session_id in self._active_ws:
            ws = self._active_ws.pop(session_id)
            asyncio.create_task(ws.close())

    async def send_command(self, session_id: str, command: Dict[str, Any]):
        if session_id not in self.sessions:
            raise ValueError(f"Unknown session {session_id}")
            
        # If WS is active, send immediately. Otherwise queue it for long-poll or reconnecting WS
        ws = self._active_ws.get(session_id)
        if ws and not ws.closed:
            try:
                await ws.send_json(command)
                return
            except Exception as e:
                logger.error(f"Error sending command over WS: {e}")
                
        await self._command_queues[session_id].put(command)

    async def receive_result(self, session_id: str, timeout: Optional[float] = None) -> Dict[str, Any]:
        if session_id not in self.sessions:
            raise ValueError(f"Unknown session {session_id}")
        
        if timeout is not None:
            return await asyncio.wait_for(self._result_queues[session_id].get(), timeout)
        else:
            return await self._result_queues[session_id].get()

    def acknowledge(self, session_id: str, message_id: str):
        """Acknowledge a received message."""
        logger.debug(f"Session {session_id} acknowledged message {message_id}")

    async def _ws_handler(self, request: web.Request):
        session_id = request.query.get("session_id")
        if not session_id or session_id not in self.sessions:
            return web.Response(status=401, text="Invalid or missing session_id")
            
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        
        self._active_ws[session_id] = ws
        
        # Drain queue of pending commands
        while not self._command_queues[session_id].empty():
            cmd = self._command_queues[session_id].get_nowait()
            await ws.send_json(cmd)
            
        async for msg in ws:
            if msg.type == WSMsgType.TEXT:
                try:
                    data = json.loads(msg.data)
                    await self._result_queues[session_id].put(data)
                except Exception as e:
                    logger.error(f"Failed to parse WS message: {e}")
            elif msg.type == WSMsgType.ERROR:
                logger.error(f"WS connection closed with exception {ws.exception()}")
                
        if self._active_ws.get(session_id) == ws:
            del self._active_ws[session_id]
            
        return ws

    async def _http_poll_handler(self, request: web.Request):
        """Long poll endpoint for commands."""
        # Handle OPTIONS for CORS
        if request.method == 'OPTIONS':
            return web.Response(status=200)
            
        session_id = request.query.get("session_id")
        if not session_id or session_id not in self.sessions:
            return web.Response(status=401, text="Invalid or missing session_id")
            
        try:
            cmd = await asyncio.wait_for(self._command_queues[session_id].get(), timeout=30.0)
            return web.json_response(cmd)
        except asyncio.TimeoutError:
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
