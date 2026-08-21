import pytest
import asyncio

@pytest.mark.asyncio
async def test_navigation(browser_env, local_server):
    driver = browser_env["driver"]
    session_id = browser_env["session_id"]
    
    tabs = await driver.enumerate_tabs(session_id)
    tab_id = tabs[0]["id"]
    
    res = await driver.execute_js(session_id, tab_id, f"window.location.href = '{local_server}/page2.html';")
    assert res["navigated"] is True
    
    await asyncio.sleep(1)
    tabs = await driver.enumerate_tabs(session_id)
    assert any("page2.html" in t["url"] for t in tabs)
