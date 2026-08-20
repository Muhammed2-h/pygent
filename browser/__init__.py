"""
Browser Subsystem Package.

This package provides a comprehensive, structured browser engine for the agent.
It contains modules for driving the browser, handling sessions, state, transport, and CDP.
"""

from .driver import BrowserDriver
from .transport import BrowserTransport
from .session import BrowserSession
from .observer import BrowserObserver
from .state import BrowserState
from .cdp import CDPClient

__all__ = [
    "BrowserDriver",
    "BrowserTransport",
    "BrowserSession",
    "BrowserObserver",
    "BrowserState",
    "CDPClient",
]
