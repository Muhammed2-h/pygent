"""
Browser Session Module.

Manages individual browser contexts/sessions and tabs.
"""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class Session:
    """Represents a browser session state."""
    session_id: str
    tab_id: str
    url: str
    title: str
    active: bool
    connected: bool
    last_seen: datetime
    connection_type: str


class BrowserSessionManager:
    """Manages browser sessions."""
    
    def __init__(self):
        self._sessions: dict[str, Session] = {}
        self._active_tab_id: str | None = None
        
    def list_sessions(self) -> list[Session]:
        """List all current browser sessions."""
        return list(self._sessions.values())
        
    def find_session(self, **kwargs) -> list[Session]:
        """Find sessions matching the provided keyword arguments."""
        result = []
        for session in self._sessions.values():
            match = True
            for k, v in kwargs.items():
                if not hasattr(session, k) or getattr(session, k) != v:
                    match = False
                    break
            if match:
                result.append(session)
        return result
        
    def get_session(self, session_id: str) -> Session | None:
        """Get a session by its session_id."""
        return self._sessions.get(session_id)
        
    def set_session(self, session: Session) -> None:
        """
        Add or update a session. 
        If the session is active, updates the explicit active tab and deactivates others.
        """
        if session.active:
            # Enforce single active tab explicitly
            for s in self._sessions.values():
                if s is not session:
                    s.active = False
            self._active_tab_id = session.tab_id
        else:
            # If the session being updated to inactive is the currently active tab
            if self._active_tab_id == session.tab_id:
                self._active_tab_id = None
                    
        self._sessions[session.session_id] = session

    def remove_session(self, session_id: str) -> bool:
        """Remove a session by its session_id."""
        session = self._sessions.pop(session_id, None)
        if session and session.tab_id == self._active_tab_id:
            # Explicitly unset active tab if the active session is removed
            self._active_tab_id = None
        return session is not None

    @property
    def active_tab_id(self) -> str | None:
        """Get the ID of the explicitly active tab."""
        return self._active_tab_id
