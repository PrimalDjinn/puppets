"""Tests for custom exceptions."""

import pytest
from puppets.exceptions import (
    PuppetsError,
    TorLaunchError,
    TorConnectionError,
    BrowserError,
    ChromeNotFoundError,
)


class TestExceptions:
    """Test custom exception hierarchy."""

    def test_puppets_error_base(self):
        """Test that PuppetsError is the base exception."""
        with pytest.raises(PuppetsError):
            raise PuppetsError("Test error")

    def test_tor_launch_error(self):
        """Test TorLaunchError inherits from PuppetsError."""
        with pytest.raises(PuppetsError):
            raise TorLaunchError("Tor failed to launch")

    def test_tor_connection_error(self):
        """Test TorConnectionError inherits from PuppetsError."""
        with pytest.raises(PuppetsError):
            raise TorConnectionError("Cannot connect to Tor")

    def test_browser_error(self):
        """Test BrowserError inherits from PuppetsError."""
        with pytest.raises(PuppetsError):
            raise BrowserError("Browser failed")

    def test_chrome_not_found_error(self):
        """Test ChromeNotFoundError inherits from PuppetsError."""
        with pytest.raises(PuppetsError):
            raise ChromeNotFoundError("Chrome not found")

    def test_exception_chaining(self):
        """Test that exceptions can be chained."""
        original = ValueError("Original error")
        with pytest.raises(PuppetsError) as exc_info:
            raise TorLaunchError("Wrapped error") from original

        assert exc_info.value.__cause__ is original

    def test_exception_message(self):
        """Test exception messages are preserved."""
        msg = "Detailed error message"
        with pytest.raises(PuppetsError) as exc_info:
            raise PuppetsError(msg)

        assert str(exc_info.value) == msg
