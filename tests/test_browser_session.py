"""Tests for the browser session manager."""

import pytest
from datetime import datetime, timezone
from browser.session import BrowserSessionManager, Session

def create_session(session_id: str, tab_id: str, active: bool = False, url: str = "http://example.com") -> Session:
    return Session(
        session_id=session_id,
        tab_id=tab_id,
        url=url,
        title="Example Title",
        active=active,
        connected=True,
        last_seen=datetime.now(timezone.utc),
        connection_type="cdp"
    )

def test_session_creation():
    manager = BrowserSessionManager()
    assert manager.list_sessions() == []
    assert manager.active_tab_id is None

def test_set_and_get_session():
    manager = BrowserSessionManager()
    session = create_session("s1", "t1")
    manager.set_session(session)
    
    assert manager.get_session("s1") == session
    assert len(manager.list_sessions()) == 1
    assert manager.active_tab_id is None

def test_active_session_management():
    manager = BrowserSessionManager()
    session1 = create_session("s1", "t1", active=True)
    manager.set_session(session1)
    
    assert manager.active_tab_id == "t1"
    assert manager.get_session("s1").active is True
    
    # Add another active session, should deactivate the first one
    session2 = create_session("s2", "t2", active=True)
    manager.set_session(session2)
    
    assert manager.active_tab_id == "t2"
    assert manager.get_session("s2").active is True
    assert manager.get_session("s1").active is False
    
    # Update s2 to be inactive
    session2.active = False
    manager.set_session(session2)
    assert manager.active_tab_id is None
    assert manager.get_session("s2").active is False

def test_find_session():
    manager = BrowserSessionManager()
    s1 = create_session("s1", "t1", url="http://a.com")
    s2 = create_session("s2", "t2", url="http://b.com")
    s3 = create_session("s3", "t3", url="http://a.com")
    manager.set_session(s1)
    manager.set_session(s2)
    manager.set_session(s3)
    
    found = manager.find_session(url="http://a.com")
    assert len(found) == 2
    assert s1 in found
    assert s3 in found
    
    found_tab = manager.find_session(tab_id="t2")
    assert len(found_tab) == 1
    assert found_tab[0] == s2
    
    found_none = manager.find_session(url="http://c.com")
    assert len(found_none) == 0

def test_remove_session():
    manager = BrowserSessionManager()
    s1 = create_session("s1", "t1", active=True)
    manager.set_session(s1)
    
    assert manager.active_tab_id == "t1"
    
    # Remove active session
    removed = manager.remove_session("s1")
    assert removed is True
    assert manager.get_session("s1") is None
    assert manager.active_tab_id is None
    
    # Remove non-existent session
    removed_none = manager.remove_session("s999")
    assert removed_none is False
