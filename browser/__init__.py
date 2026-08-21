"""
Browser Subsystem Package.

This package provides a comprehensive, structured browser engine for the agent.
It contains modules for driving the browser, handling sessions, state, transport, and CDP.
"""

from .cdp import CDPClient
from .driver import BrowserDriver
from .observer import BrowserObserver
from .session import BrowserSessionManager, Session
from .state import BrowserState
from .transport import BrowserTransport

__all__ = [
    "BrowserDriver",
    "BrowserObserver",
    "BrowserSessionManager",
    "BrowserState",
    "BrowserTransport",
    "CDPClient",
    "Session",
]
