import asyncio
import base64

import pytest


@pytest.mark.asyncio
async def test_screenshot(browser_env, local_server):
    driver = browser_env["driver"]
    session_id = browser_env["session_id"]
    
    tabs = await driver.enumerate_tabs(session_id)
    tab_id = tabs[0]["id"]
    
    # Load page and wait for it to be ready
    await driver.execute_js(session_id, tab_id, f"window.location.href = '{local_server}/index.html';")
    for _ in range(50):
        resp = await driver.execute_js(session_id, tab_id, "return document.readyState;")
        if resp.get("result") == "complete":
            break
        await asyncio.sleep(0.1)
    
    screenshot = await driver.browser_screenshot(session_id, tab_id)
    
    assert screenshot["mime_type"] == "image/png"
    assert screenshot["width"] > 0
    assert screenshot["height"] > 0
    assert len(screenshot["base64"]) > 0
    
    # verify it's valid base64
    base64.b64decode(screenshot["base64"])
