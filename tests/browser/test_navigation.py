import pytest
import asyncio

@pytest.mark.asyncio
async def test_navigation(browser_env, local_server):
    driver = browser_env["driver"]
    session_id = browser_env["session_id"]
    
    tabs = await driver.enumerate_tabs(session_id)
    tab_id = tabs[0]["id"]
    
    res = await driver.execute_js(session_id, tab_id, f"window.location.href = '{local_server}/page2.html';")
    
    for _ in range(20):
        tabs = await driver.enumerate_tabs(session_id)
        if any("page2.html" in t["url"] for t in tabs):
            break
        await asyncio.sleep(0.1)
    
    assert any("page2.html" in t["url"] for t in tabs)
