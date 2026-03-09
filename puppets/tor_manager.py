"""Tor instance management."""

import os
import socket
import shutil
import logging
from typing import Tuple, Optional, Any

from stem import process
from stem.control import Controller
from stem import Signal

from puppets.exceptions import TorLaunchError, TorConnectionError

logger = logging.getLogger(__name__)


def get_free_port() -> int:
    """Return an unused TCP port number on localhost."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


def find_tor_executable() -> str:
    """Find the Tor executable on the system.

    Returns:
        Path to the Tor executable.

    Raises:
        TorLaunchError: If Tor is not found.
    """
    tor_cmd = shutil.which("tor")

    if tor_cmd is None:
        # Try common installation paths
        common_tor_paths = [
            "/usr/sbin/tor",
            "/usr/bin/tor",
            "/usr/local/bin/tor",
            "/opt/tor/bin/tor",
            "/run/current-system/profile/bin/tor",
        ]
        for path in common_tor_paths:
            if os.path.isfile(path) and os.access(path, os.X_OK):
                tor_cmd = path
                break

    if tor_cmd is None:
        raise TorLaunchError(
            "Tor executable not found. Please install Tor:\n"
            "  - Debian/Ubuntu: sudo apt install tor\n"
            "  - macOS: brew install tor\n"
            "  - Or verify Tor is in your PATH with: which tor"
        )

    logger.debug("using tor executable: %s", tor_cmd)
    return tor_cmd


class TorInstance:
    """Manages a single Tor instance.

    Attributes:
        process: The Tor subprocess.
        socks_port: The SOCKS port number.
        control_port: The control port number.
    """

    def __init__(self, timeout: int = 120):
        """Initialize a new Tor instance.

        Args:
            timeout: Seconds to wait for Tor to start.
        """
        self.process: Optional[Any] = None
        self.socks_port: int = 0
        self.control_port: int = 0
        self._timeout = timeout
        self._controller: Optional[Controller] = None

    def start(self) -> Tuple[Any, int, int]:
        """Start a new Tor instance.

        Returns:
            Tuple of (process, socks_port, control_port).

        Raises:
            TorLaunchError: If Tor fails to start.
        """
        self.socks_port = get_free_port()
        self.control_port = get_free_port()

        logger.info(
            "starting tor attached to socks port %s control port %s",
            self.socks_port,
            self.control_port,
        )

        tor_cmd = find_tor_executable()

        def _init_msg(msg: str) -> None:
            logger.debug("tor: %s", msg)

        try:
            self.process = process.launch_tor_with_config(
                tor_cmd=tor_cmd,
                config={
                    "SocksPort": str(self.socks_port),
                    "ControlPort": str(self.control_port),
                    "CookieAuthentication": "1",
                },
                timeout=self._timeout,
                init_msg_handler=_init_msg,
                take_ownership=True,
            )
        except OSError as exc:
            raise TorLaunchError(
                f"Failed to start Tor process: {exc}\n"
                "This may be caused by:\n"
                "  - Tor executable not found or not executable\n"
                "  - Port already in use (another Tor instance running?)\n"
                "  - Permission denied to run Tor\n"
                f"Tor command attempted: {tor_cmd}\n"
                "Try running 'tor' manually to see any error messages."
            ) from exc
        except Exception as exc:
            raise TorLaunchError(
                f"Unexpected error starting Tor: {exc}\n"
                "Please check that Tor is properly installed and configured."
            ) from exc

        return self.process, self.socks_port, self.control_port

    def new_identity(self) -> None:
        """Request a new Tor identity (new IP).

        Raises:
            TorConnectionError: If authentication or signal fails.
        """
        try:
            self._controller = Controller.from_port(port=str(self.control_port))
            self._controller.authenticate()
            self._controller.signal(Signal.NEWNYM)  # type: ignore
        except Exception as exc:
            raise TorConnectionError(
                f"Failed to request new Tor identity: {exc}"
            ) from exc
        finally:
            if self._controller:
                self._controller.close()
                self._controller = None

    def stop(self) -> None:
        """Stop the Tor instance."""
        if self.process:
            self.process.terminate()
            self.process = None

        if self._controller:
            try:
                self._controller.close()
            except Exception:
                pass
            self._controller = None

    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()
        return False
