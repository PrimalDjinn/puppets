"""
Puppets - Automate Chrome through the Tor network with Python

A library for running browser sessions through Tor with support for:
- Single session with fresh Tor instance
- Multiple parallel sessions
- Identity rotation (new IP on demand)
- Headless mode support

Usage:
    from puppets import Session, SessionManager

    # Single session
    session = Session()
    result = session.run()

    # Multiple parallel sessions
    manager = SessionManager(max_workers=10)
    results = manager.run_sessions(num_sessions=50)
"""

from puppets.session import Session
from puppets.session_manager import SessionManager
from puppets.exceptions import (
    PuppetsError,
    TorLaunchError,
    TorConnectionError,
    BrowserError,
    ChromeNotFoundError,
)

__version__ = "1.0.0"
__all__ = [
    "Session",
    "SessionManager",
    "PuppetsError",
    "TorLaunchError",
    "TorConnectionError",
    "BrowserError",
    "ChromeNotFoundError",
]
