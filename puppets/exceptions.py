"""Custom exceptions for puppets."""


class PuppetsError(Exception):
    """Base exception for all puppets errors."""

    pass


class TorLaunchError(PuppetsError):
    """Raised when Tor fails to launch."""

    pass


class TorConnectionError(PuppetsError):
    """Raised when connection to Tor fails."""

    pass


class BrowserError(PuppetsError):
    """Raised when browser operations fail."""

    pass


class ChromeNotFoundError(PuppetsError):
    """Raised when Chrome/Chromium is not found."""

    pass
