import pytest
import asyncio
from browser.observer import BrowserObserver

@pytest.mark.asyncio
async def test_observer_scan(browser_env, local_server):
    transport = browser_env["transport"]
    driver = browser_env["driver"]
    session_id = browser_env["session_id"]
    
    tabs = await driver.enumerate_tabs(session_id)
    tab_id = tabs[0]["id"]
    
    # load test page
    await driver.execute_js(session_id, tab_id, f"window.location.href = '{local_server}/index.html';")
    
    observer = BrowserObserver(transport)
    scan_res = None
    for _ in range(30):
        scan_res = await observer.scan(session_id, tab_id)
        if scan_res and scan_res.get("interactive_elements"):
            break
        await asyncio.sleep(0.2)
        
    assert scan_res is not None
    assert "interactive_elements" in scan_res
    assert isinstance(scan_res["interactive_elements"], list)
    assert any(el.get("tag", "").lower() == "button" for el in scan_res["interactive_elements"])
