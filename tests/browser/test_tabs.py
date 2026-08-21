import pytest
import asyncio

@pytest.mark.asyncio
async def test_enumerate_tabs(browser_env, local_server):
    driver = browser_env["driver"]
    session_id = browser_env["session_id"]
    
    tabs = await driver.enumerate_tabs(session_id)
    assert len(tabs) >= 1
    
    # Open local server page
    await driver.execute_js(session_id, tabs[0]["id"], f"window.location.href = '{local_server}/index.html';")
    await asyncio.sleep(1)  # wait for load
    
    tabs = await driver.enumerate_tabs(session_id)
    assert any("index.html" in t["url"] for t in tabs)
