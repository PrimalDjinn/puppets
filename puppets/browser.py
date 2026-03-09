"""Browser management using undetected-chromedriver."""

import subprocess
import re
import logging
from typing import Optional

import undetected_chromedriver as uc
from puppets.exceptions import BrowserError, ChromeNotFoundError

logger = logging.getLogger(__name__)


def detect_chrome_version() -> Optional[int]:
    """Detect the installed Chrome/Chromium major version.

    Returns:
        Major version number, or None if not detected.
    """
    chrome_commands = [
        "google-chrome",
        "google-chrome-stable",
        "chromium",
        "chromium-browser",
    ]

    for chrome_cmd in chrome_commands:
        try:
            out = subprocess.check_output(
                [chrome_cmd, "--version"], stderr=subprocess.DEVNULL
            )
            m = re.search(r"(\d+)", out.decode())
            if m:
                version = int(m.group(1))
                logger.debug("detected %s version %s", chrome_cmd, version)
                return version
        except FileNotFoundError:
            continue
        except Exception as e:
            logger.debug("failed to get version from %s: %s", chrome_cmd, e)
            continue

    return None


class Browser:
    """Manages a Chrome/Chromium browser instance.

    Attributes:
        driver: The Selenium WebDriver instance.
    """

    def __init__(self, socks_port: int, headless: bool = False):
        """Initialize a new browser.

        Args:
            socks_port: The Tor SOCKS proxy port.
            headless: Whether to run browser in headless mode.
        """
        self.driver: Optional[uc.Chrome] = None
        self.socks_port = socks_port
        self.headless = headless
        self._version_main: Optional[int] = None

    def start(self) -> uc.Chrome:
        """Start the browser with Tor proxy.

        Returns:
            The WebDriver instance.

        Raises:
            ChromeNotFoundError: If no Chrome is installed.
            BrowserError: If browser fails to start.
        """
        # Detect Chrome version
        self._version_main = detect_chrome_version()

        if self._version_main is None:
            raise ChromeNotFoundError(
                "No Chrome/Chromium browser found. Please install one of:\n"
                "  - Google Chrome: https://www.google.com/chrome/\n"
                "  - Chromium: sudo apt install chromium-browser (Debian/Ubuntu)\n"
                "  - Or: brew install chromium (macOS)\n"
                "The browser is required for this script to work."
            )

        # Configure proxy
        # Chrome's --proxy-server flag only accepts socks5://, not socks5h://.
        # Chrome routes DNS through the SOCKS5 proxy automatically.
        PROXY = f"socks5://127.0.0.1:{self.socks_port}"

        opts = uc.ChromeOptions()
        opts.add_argument(f"--proxy-server={PROXY}")
        opts.add_argument("--host-resolver-rules=MAP * ~NOTFOUND , EXCLUDE 127.0.0.1")
        opts.add_argument("--proxy-bypass-list=<-loopback>")

        if self.headless:
            opts.add_argument("--headless=new")

        try:
            if self._version_main:
                self.driver = uc.Chrome(options=opts, version_main=self._version_main)
            else:
                self.driver = uc.Chrome(options=opts)
        except Exception as exc:
            error_msg = str(exc).lower()
            if "chromedriver" in error_msg or "chrome" in error_msg:
                raise BrowserError(
                    f"Failed to start Chrome/ChromeDriver: {exc}\n"
                    "This may be caused by:\n"
                    "  - ChromeDriver version mismatch with your Chrome version\n"
                    "  - Missing Chrome browser installation\n"
                    "  - Permission issues running Chrome/ChromeDriver\n"
                    "Try updating Chrome and reinstalling undetected-chromedriver:\n"
                    "  pip install --upgrade undetected-chromedriver"
                ) from exc
            raise

        return self.driver

    def stop(self) -> None:
        """Stop the browser."""
        if self.driver:
            try:
                self.driver.quit()
            except Exception:
                pass
            self.driver = None

    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()
        return False
