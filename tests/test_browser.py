"""Tests for the browser subsystem."""

from browser import (
    BrowserDriver,
    BrowserObserver,
    BrowserSessionManager,
    BrowserState,
    BrowserTransport,
    CDPClient,
)


def test_browser_imports():
    """Test that all major browser components can be imported and instantiated."""
    driver = BrowserDriver()
    transport = BrowserTransport()
    manager = BrowserSessionManager()
    observer = BrowserObserver()
    state = BrowserState()
    cdp = CDPClient()

    assert driver is not None
    assert transport is not None
    assert manager is not None
    assert observer is not None
    assert state is not None
    assert cdp is not None
