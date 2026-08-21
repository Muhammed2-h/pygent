import pytest
import pytest_asyncio
import asyncio
import os
import signal
import socket
import sys
import shutil
import subprocess
from pathlib import Path
import tempfile
import threading
from http.server import SimpleHTTPRequestHandler
import socketserver

from browser.transport import BrowserTransport
from browser.driver import BrowserDriver
from browser.cdp import CDPClient

def find_chrome() -> str:
    candidates = [
        "google-chrome",
        "google-chrome-stable",
        "chromium",
        "chromium-browser",
        "chrome"
    ]
    if sys.platform == "darwin":
        candidates.append("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")

    for candidate in candidates:
        if Path(candidate).is_absolute() and Path(candidate).exists():
            return candidate
        path = shutil.which(candidate)
        if path:
            return path
    return ""

class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

@pytest.fixture(scope="session")
def local_server():
    temp_dir = tempfile.mkdtemp()
    
    # Create some test files
    (Path(temp_dir) / "index.html").write_text("<html><body><h1>Test Page</h1><button id='btn'>Click me</button></body></html>")
    (Path(temp_dir) / "page2.html").write_text("<html><body><h1>Page 2</h1></body></html>")
    
    class TCPServer(socketserver.TCPServer):
        allow_reuse_address = True
        
    handler = lambda *args, **kwargs: QuietHandler(*args, directory=temp_dir, **kwargs)
    
    port = 8000
    while True:
        try:
            httpd = TCPServer(("127.0.0.1", port), handler)
            break
        except OSError:
            port += 1
            
    server_thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    server_thread.start()
    
    yield f"http://127.0.0.1:{port}"
    
    httpd.shutdown()
    httpd.server_close()
    shutil.rmtree(temp_dir, ignore_errors=True)


def _get_free_port():
    """Bind to port 0 to let the OS pick a free port, then release it."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        return s.getsockname()[1]


@pytest_asyncio.fixture
async def browser_env():
    chrome_path = find_chrome()
    if not chrome_path:
        pytest.skip("Chrome not found")

    ws_port = _get_free_port()
    http_port = _get_free_port()
    
    root_dir = Path(__file__).parent.parent.parent
    orig_extension_dir = root_dir / "extension"
    if not orig_extension_dir.exists():
        pytest.skip("Extension not found")
        
    temp_ext_dir = Path(tempfile.mkdtemp())
    shutil.copytree(orig_extension_dir, temp_ext_dir, dirs_exist_ok=True)
    
    bg_js = temp_ext_dir / "background.js"
    content = bg_js.read_text()
    content = content.replace("ws://127.0.0.1:18765/ws?session_id=default", f"ws://127.0.0.1:{ws_port}/ws?session_id=default")
    bg_js.write_text(content)
        
    transport = BrowserTransport(ws_port=ws_port, http_port=http_port)
    session_id = "default"
    transport.register_session(session_id)
    
    await transport.start_ws_server()
    await transport.start_http_server()
    
    user_data_dir = tempfile.mkdtemp()
    driver = BrowserDriver(transport=transport)
    
    cmd = [
        chrome_path,
        f"--load-extension={temp_ext_dir}",
        f"--user-data-dir={user_data_dir}",
        "--no-first-run",
        "--no-default-browser-check",
        "--remote-debugging-port=0"
    ]
    
    xvfb = shutil.which("xvfb-run")
    if xvfb:
        cmd = [xvfb, "-a"] + cmd
    else:
        cmd.extend(["--headless=new", "--disable-gpu"])
        
    cmd.append(f"http://127.0.0.1:{http_port}/poll?session_id={session_id}")
    
    log_dir = Path(tempfile.mkdtemp())
    log_out = open(log_dir / "chrome_out.log", "w")
    log_err = open(log_dir / "chrome_err.log", "w")
    proc = None
    try:
        proc = subprocess.Popen(cmd, stdout=log_out, stderr=log_err, start_new_session=True)
        
        connected = False
        for _ in range(600):
            if transport.is_connected(session_id):
                connected = True
                break
            await asyncio.sleep(0.1)
            
        if not connected:
            pytest.fail("Browser did not connect")
            
        env = {
            "transport": transport,
            "driver": driver,
            "session_id": session_id,
            "proc": proc,
            "http_port": http_port
        }
        
        yield env
    finally:
        if proc is not None:
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            except Exception:
                proc.kill()

        log_out.close()
        log_err.close()
        shutil.rmtree(user_data_dir, ignore_errors=True)
        shutil.rmtree(temp_ext_dir, ignore_errors=True)
        shutil.rmtree(log_dir, ignore_errors=True)
        await transport.stop()
