
import pytest

from browser.session import Session


@pytest.mark.asyncio
async def test_session_manager(browser_env):
    # browser_env provides driver which has driver.session_manager
    # But driver might not have session_manager populated in conftest.
    # We can test browser_env's transport sessions
    transport = browser_env["transport"]
    
    assert "default" in transport.sessions
    
    # We can also instantiate a new BrowserSessionManager if needed, but it's a standalone class.
    from datetime import datetime

    from browser.session import BrowserSessionManager
    
    manager = BrowserSessionManager()
    sess = Session(
        session_id="test1",
        tab_id="tab1",
        url="http://test.com",
        title="Test",
        active=True,
        connected=True,
        last_seen=datetime.now(),
        connection_type="ws"
    )
    
    manager.set_session(sess)
    assert manager.get_session("test1") == sess
    assert manager.active_tab_id == "tab1"
    
    manager.remove_session("test1")
    assert manager.get_session("test1") is None
    assert manager.active_tab_id is None
