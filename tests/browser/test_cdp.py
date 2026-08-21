
import pytest

from browser.cdp import CDPClient


@pytest.mark.asyncio
async def test_cdp_evaluate(browser_env):
    transport = browser_env["transport"]
    driver = browser_env["driver"]
    session_id = browser_env["session_id"]
    
    tabs = await driver.enumerate_tabs(session_id)
    tab_id = tabs[0]["id"]
    
    cdp = CDPClient(transport)
    await cdp.attach(session_id, tab_id)
    
    res = await cdp.runtime_evaluate(session_id, tab_id, "5 + 7")
    assert "result" in res
    assert res["result"]["value"] == 12
    
    await cdp.detach(session_id, tab_id)
