import pytest
import asyncio

@pytest.mark.asyncio
async def test_execute_js(browser_env, local_server):
    driver = browser_env["driver"]
    session_id = browser_env["session_id"]
    
    tabs = await driver.enumerate_tabs(session_id)
    tab_id = tabs[0]["id"]
    
    res = await driver.execute_js(session_id, tab_id, "return 1 + 2;")
    assert res["result"] == 3
    
    # test error extraction
    with pytest.raises(RuntimeError):
        await driver.execute_js(session_id, tab_id, "throw new Error('Test JS error');")
