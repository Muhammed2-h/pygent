import asyncio
import socket
import sys
import shutil
import subprocess
from pathlib import Path

from browser.transport import BrowserTransport
from browser.driver import BrowserDriver
import uuid
import tempfile

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

def check_port(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("127.0.0.1", port))
            return True
        except OSError:
            return False

async def run_diagnostics():
    print("Browser Setup Diagnostics:")
    print("==========================")
    
    # 1. Chrome exists
    chrome_path = find_chrome()
    if chrome_path:
        print(f"✅ Chrome exists: {chrome_path}")
    else:
        print("❌ Chrome exists: Not found")
        
    # 2. Extension exists
    root_dir = Path(__file__).parent.parent
    extension_dir = root_dir / "extension"
    manifest_path = extension_dir / "manifest.json"
    if manifest_path.exists():
        print(f"✅ Extension exists: {extension_dir}")
    else:
        print(f"❌ Extension exists: Not found at {extension_dir}")
        
    # 3. Bridge ports available
    ws_port = 18765
    http_port = 18766
    ws_ok = check_port(ws_port)
    http_ok = check_port(http_port)
    if ws_ok and http_ok:
        print(f"✅ Bridge ports available: WS({ws_port}), HTTP({http_port})")
    else:
        print(f"❌ Bridge ports available: WS={ws_ok}, HTTP={http_ok}")
        
    if not (chrome_path and manifest_path.exists() and ws_ok and http_ok):
        print("\nPrerequisites failed. Skipping further tests.")
        return
        
    # 4. Driver starts
    transport = BrowserTransport(ws_port=ws_port, http_port=http_port)
    session_id = "default"
    transport.register_session(session_id)
    
    try:
        await transport.start_ws_server()
        await transport.start_http_server()
        print("✅ Driver starts: Transport servers running")
    except Exception as e:
        print(f"❌ Driver starts: {e}")
        return
        
    user_data_dir = tempfile.mkdtemp()
    driver = BrowserDriver(transport=transport)
    
    cmd = [
        chrome_path,
        f"--load-extension={extension_dir}",
        f"--user-data-dir={user_data_dir}",
        "--no-first-run",
        "--no-default-browser-check",
        "--remote-debugging-port=9222"
    ]
    
    xvfb = shutil.which("xvfb-run")
    if xvfb:
        cmd = [xvfb, "-a"] + cmd
    else:
        cmd.append("--headless=new")
        cmd.append("--disable-gpu")
        
    cmd.append("http://127.0.0.1:18766/poll?session_id=default")
    
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    connected = False
    for _ in range(50):
        if session_id in transport._active_ws:
            connected = True
            break
        await asyncio.sleep(0.1)
        
    if connected:
        print("✅ Extension connects: WebSocket connected")
    else:
        print("❌ Extension connects: Timeout waiting for WebSocket")
        
    tabs = []
    if connected:
        try:
            tabs = await driver._enumerate_tabs(session_id)
            if tabs:
                print(f"✅ Tabs are visible: Found {len(tabs)} tabs")
            else:
                print("❌ Tabs are visible: 0 tabs found")
        except Exception as e:
            print(f"❌ Tabs are visible: {e}")
            
    if connected and tabs:
        try:
            tab_id = tabs[0]["id"]
            res = await driver.execute_js(session_id, tab_id, "return 1 + 1;")
            if res.get("result") == 2:
                print("✅ JavaScript execution works")
            else:
                print(f"❌ JavaScript execution works: {res}")
        except Exception as e:
            print(f"❌ JavaScript execution works: {e}")
            
    proc.terminate()
    try:
        proc.wait(timeout=3)
    except subprocess.TimeoutExpired:
        proc.kill()
        
    shutil.rmtree(user_data_dir, ignore_errors=True)
    await transport.stop()

def handle_browser_setup():
    asyncio.run(run_diagnostics())
