import sys
import asyncio
import subprocess
import shutil
import tempfile
from pathlib import Path

from config import load_config
from providers.factory import create_provider
from tools import ToolRegistry
from agent import Agent
from memory.storage import MemoryStore
from memory.privacy import PrivacyFilter
from memory.service import MemoryService
from tools.browser import setup_browser_tools
from tools.registry import set_main_loop

from browser.transport import BrowserTransport
from browser.driver import BrowserDriver
from browser.session import BrowserSessionManager, Session
from browser.cdp import CDPClient
from browser.observer import BrowserObserver
from datetime import datetime

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

async def async_start_browser_repl(db_path: str, skills_dir: str, managed: bool = False):
    set_main_loop(asyncio.get_running_loop())
    ws_port = 18765
    http_port = 18766

    transport = BrowserTransport(ws_port=ws_port, http_port=http_port)
    session_id = "default"
    transport.register_session(session_id)
    
    # Start transport servers
    try:
        await transport.start_ws_server()
        await transport.start_http_server()
    except Exception as e:
        print(f"Error starting transport: {e}")
        return

    connected = False
    
    if not managed:
        # Wait to see if extension connects on its own
        print("Waiting for extension connection...")
        for _ in range(10):
            if transport.is_connected(session_id):
                connected = True
                break
            await asyncio.sleep(0.2)

    proc = None
    user_data_dir = None
    if not connected:
        print("Launching browser...")
        chrome_path = find_chrome()
        if not chrome_path:
            print("Chrome not found. Cannot launch browser.")
            await transport.stop()
            return

        root_dir = Path(__file__).parent.parent
        extension_dir = root_dir / "extension"

        config = load_config()
        if managed:
            user_data_dir = str(Path(config.data_dir) / "browser" / "profile")
            # Clear it to ensure fresh session
            shutil.rmtree(user_data_dir, ignore_errors=True)
            Path(user_data_dir).mkdir(parents=True, exist_ok=True)
        else:
            user_data_dir = tempfile.mkdtemp()
            
        cmd = [
            chrome_path,
            f"--load-extension={extension_dir}",
            f"--user-data-dir={user_data_dir}",
            "--no-first-run",
            "--no-default-browser-check",
            "--remote-debugging-port=9222",
            "http://127.0.0.1:18766/poll?session_id=default"
        ]

        proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        for _ in range(150):
            if transport.is_connected(session_id):
                connected = True
                break
            await asyncio.sleep(0.1)

    if not connected:
        print("Failed to connect to browser extension.")
        if proc:
            proc.terminate()
        await transport.stop()
        return

    print("Browser extension connected.")
    
    session_manager = BrowserSessionManager()
    driver = BrowserDriver(transport=transport, session_manager=session_manager)
    cdp = CDPClient(transport)
    observer = BrowserObserver(transport=transport, cdp=cdp)
    
    print("Listing tabs...")
    try:
        tabs = await driver.enumerate_tabs(session_id)
        if tabs:
            tab_id = tabs[0]["id"]
            url = tabs[0].get("url", "")
            title = tabs[0].get("title", "")
            print(f"Selecting active tab: {tab_id} ({title})")
            sess = Session(
                session_id=session_id,
                tab_id=str(tab_id),
                url=url,
                title=title,
                active=True,
                connected=True,
                last_seen=datetime.now(),
                connection_type="ws"
            )
            session_manager.set_session(sess)
        else:
            print("No tabs found.")
    except Exception as e:
        print(f"Error listing tabs: {e}")

    setup_browser_tools(driver, session_manager, observer, cdp)
    
    print("Entering browser-agent mode...")

    # Now run the REPL
    config = load_config()
    try:
        provider = create_provider(config)
    except ValueError as e:
        print(f"Error: {e}")
        return

    tools = ToolRegistry()
    memory_store = MemoryStore(db_path, skills_dir=skills_dir)
    memory_svc = MemoryService(memory_store, PrivacyFilter())

    agent = Agent(provider, tools, config.default_model, config.max_agent_steps, memory_service=memory_svc)

    print("Browser Agent started. Type /quit to exit.")
    try:
        while True:
            # We must use asyncio for input if we want transport to run in background?
            # Actually input() is blocking. A blocking input will pause the asyncio event loop!
            # We need to run input() in an executor.
            try:
                user_in = await asyncio.to_thread(input, "> ")
            except (EOFError, KeyboardInterrupt):
                print()
                break

            if user_in.strip() == "/quit":
                break

            context = memory_svc.get_context_for(user_in)
            sys_prompt = "You are a helpful Browser AI Agent with access to browser tools."
            if context:
                sys_prompt += "\n" + context

            # agent.run is synchronous? If it is, it will block asyncio loop.
            # We should wrap it in to_thread, or if it has async tools...
            # Wait, Pygent tools are async but Agent is synchronous? Let's check Agent.run
            messages = await asyncio.to_thread(agent.run, sys_prompt, user_in)
            for msg in messages:
                if msg.role == "assistant" and msg.content:
                    print(f"AI: {msg.content}")

            memory_svc.add(f"User observation: {user_in}")
    finally:
        memory_store.close()
        await transport.stop()
        if proc:
            proc.terminate()
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                proc.kill()
        if user_data_dir and not managed:
            shutil.rmtree(user_data_dir, ignore_errors=True)

def handle_browser(db_path: str, skills_dir: str, managed: bool = False):
    try:
        asyncio.run(async_start_browser_repl(db_path, skills_dir, managed))
    except KeyboardInterrupt:
        pass
