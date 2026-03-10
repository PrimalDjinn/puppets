"""Single session management."""

import time
import uuid
import socket
import logging
from typing import Optional, Dict, Any, Callable, List

import requests

from puppets.tor_manager import TorInstance
from puppets.browser import Browser
from puppets.exceptions import TorConnectionError, BrowserError

logger = logging.getLogger(__name__)

IP_CHECK_URL = "https://api.ipify.org"


def is_port_open(host: str, port: int, timeout: float = 1.0) -> bool:
    """Check if a port is accepting connections."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    try:
        s.connect((host, port))
        return True
    except Exception:
        return False
    finally:
        s.close()


def check_tor_proxy(socks_port: int, url: str = IP_CHECK_URL) -> str:
    """Verify Tor proxy is working and return the IP."""
    proxies = {
        "http": f"socks5h://127.0.0.1:{socks_port}",
        "https": f"socks5h://127.0.0.1:{socks_port}",
    }
    try:
        resp = requests.get(url, proxies=proxies, timeout=15)
        resp.raise_for_status()
        return resp.text.strip()
    except requests.exceptions.ConnectionError as exc:
        raise TorConnectionError(
            f"Cannot connect to Tor SOCKS proxy at localhost:{socks_port}"
        ) from exc
    except requests.exceptions.Timeout as exc:
        raise TorConnectionError("Request timed out through Tor proxy") from exc
    except requests.exceptions.RequestException as exc:
        raise TorConnectionError(
            f"HTTP request failed through Tor proxy: {exc}"
        ) from exc


def wait_for_tor(socks_port: int, timeout: int = 60) -> str:
    """Wait for Tor proxy to be ready."""
    start = time.time()
    last_error = None

    while True:
        try:
            return check_tor_proxy(socks_port)
        except Exception as e:
            last_error = e
            if time.time() - start > timeout:
                raise TorConnectionError(
                    f"timed out waiting for Tor circuit (last error: {last_error})"
                ) from last_error
            time.sleep(1)


class Session:
    """A single browser session with its own Tor instance.

    This is the main class for running a single session. Each session
    gets its own fresh Tor instance, ensuring a unique IP address.

    Attributes:
        session_id: Unique identifier for this session.
        tor_instance: The Tor instance for this session.
        browser: The browser instance.
        ip: The current IP address (after Tor connection).
    """

    def __init__(
        self,
        session_id: Optional[str] = None,
        headless: bool = False,
        tor_timeout: int = 120,
        flags: Optional[List[str]] = None,
    ):
        """Initialize a new session.

        Args:
            session_id: Optional custom session ID. Auto-generated if not provided.
            headless: Whether to run browser in headless mode.
            tor_timeout: Seconds to wait for Tor to start.
            flags: Optional list of Chrome flags to pass to the browser.
        """
        self.session_id = session_id or str(uuid.uuid4())[:8]
        self.headless = headless
        self.tor_timeout = tor_timeout
        self.flags = flags or []

        self.tor_instance: Optional[TorInstance] = None
        self.browser: Optional[Browser] = None
        self.ip: Optional[str] = None
        self._driver = None

    @property
    def driver(self):
        """Get the Selenium WebDriver instance.

        Returns:
            The WebDriver instance, or None if the session hasn't been started.
        """
        return self._driver

    def __repr__(self) -> str:
        status = "started" if self._driver else "idle"
        return (
            f"Session(id={self.session_id!r}, ip={self.ip!r}, "
            f"headless={self.headless}, status={status!r})"
        )

    def start(self) -> None:
        """Start the session (Tor + browser).

        This starts Tor and the browser but does NOT navigate to any URL.
        Use this when you want full control over the driver for DOM manipulation.

        After calling start(), you can use self.driver to:
        - Navigate to URLs
        - Find and click elements
        - Fill forms
        - Execute JavaScript
        - Take screenshots
        - Any other Selenium operations

        Raises:
            TorConnectionError: If Tor fails to start or connect.
            BrowserError: If browser fails to start.
        """
        # Start Tor
        logger.info(f"[{self.session_id}] Starting Tor instance...")
        self.tor_instance = TorInstance(timeout=self.tor_timeout)
        self.tor_instance.start()

        # Verify Tor is working
        logger.info(f"[{self.session_id}] Verifying Tor connection...")
        self.ip = wait_for_tor(self.tor_instance.socks_port)
        logger.info(f"[{self.session_id}] Tor ready with IP: {self.ip}")

        # Start browser
        logger.info(f"[{self.session_id}] Starting browser...")
        self.browser = Browser(
            socks_port=self.tor_instance.socks_port, headless=self.headless, flags=self.flags
        )
        self._driver = self.browser.start()
        logger.info(f"[{self.session_id}] Browser ready")

    def navigate(self, url: str) -> None:
        """Navigate to a URL.

        Args:
            url: The URL to navigate to.

        Raises:
            RuntimeError: If the session has not been started.
        """
        if not self._driver:
            raise RuntimeError("Session not started. Call start() first.")
        self._driver.get(url)

    def run(
        self,
        url: str = IP_CHECK_URL,
        action_callback: Optional[Callable[[Any], None]] = None,
    ) -> Dict[str, Any]:
        """Run a complete session.

        This will:
        1. Start a fresh Tor instance
        2. Verify Tor is working
        3. Start the browser
        4. Navigate to the URL
        5. Optionally execute custom actions via callback

        Args:
            url: URL to navigate to after browser starts.
            action_callback: Optional callback function that receives the WebDriver
                           instance for custom browser actions.

        Returns:
            Dictionary with session results:
                - session_id: The session ID
                - ip: The IP address through Tor
                - socks_port: The Tor SOCKS port used
                - success: Whether the session completed successfully
                - error: Error message (only present on failure)
        """
        result: Dict[str, Any] = {
            "session_id": self.session_id,
            "ip": None,
            "socks_port": None,
            "success": False,
        }

        try:
            # Start Tor
            logger.info(f"[{self.session_id}] Starting Tor instance...")
            self.tor_instance = TorInstance(timeout=self.tor_timeout)
            self.tor_instance.start()
            result["socks_port"] = self.tor_instance.socks_port

            # Verify Tor is working
            logger.info(f"[{self.session_id}] Verifying Tor connection...")
            self.ip = wait_for_tor(self.tor_instance.socks_port)
            result["ip"] = self.ip
            logger.info(f"[{self.session_id}] Tor ready with IP: {self.ip}")

            # Start browser
            logger.info(f"[{self.session_id}] Starting browser...")
            self.browser = Browser(
                socks_port=self.tor_instance.socks_port, headless=self.headless, flags=self.flags
            )
            self._driver = self.browser.start()
            if self._driver is None:
                raise BrowserError("Browser started but returned no driver")

            # Navigate to URL
            logger.info(f"[{self.session_id}] Navigating to {url}...")
            self._driver.get(url)
            time.sleep(2)  # Brief pause for initial page load

            # Execute custom actions if provided
            if action_callback:
                logger.info(f"[{self.session_id}] Executing custom actions...")
                action_callback(self._driver)

            result["success"] = True
            logger.info(f"[{self.session_id}] Session completed successfully")

        except Exception as exc:
            result["error"] = str(exc)
            logger.error(f"[{self.session_id}] Session failed: {exc}")

        finally:
            self.cleanup()

        return result

    def cleanup(self) -> None:
        """Clean up all resources."""
        if self.browser:
            try:
                self.browser.stop()
            except Exception:
                pass
            self.browser = None

        if self.tor_instance:
            try:
                self.tor_instance.stop()
            except Exception:
                pass
            self.tor_instance = None

        self._driver = None

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.cleanup()
        return False
