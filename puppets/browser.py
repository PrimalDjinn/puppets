"""Browser management using undetected-chromedriver."""

import subprocess
import re
import logging
import platform
import shutil
import os
import time
import threading
import tempfile
from typing import Optional, List

import undetected_chromedriver as uc
from puppets.exceptions import BrowserError, ChromeNotFoundError

logger = logging.getLogger(__name__)

_uc_patch_lock = threading.Lock()
_browser_start_serial_lock = threading.Lock()


def _read_chrome_version_from_registry() -> Optional[int]:
    r"""Try to read the version string from the Windows registry.

    Chrome keeps its version in two possible locations depending on whether
    it's installed for the current user or all users.  We look under both
    hive **HKCU** and **HKLM** at
    ``Software\Google\Chrome\BLBeacon``.

    Returns the major version number if found, otherwise ``None``.
    """
    try:
        import winreg
    except ImportError:  # not on Windows
        return None

    for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):  # type: ignore
        try:
            key = winreg.OpenKey(hive, r"Software\Google\Chrome\BLBeacon")  # type: ignore
            version_str, _ = winreg.QueryValueEx(key, "version")  # type: ignore
            m = re.search(r"(\d+)", version_str)
            if m:
                return int(m.group(1))
        except Exception:
            continue
    return None


def detect_chrome_version() -> Optional[int]:
    """Detect the installed Chrome/Chromium major version.

    On Linux/macOS this invokes various ``chrome``/``chromium`` binaries with
    ``--version``.  On Windows the implementation does the same _and_ falls
    back to querying the registry if the binary lookup fails.

    Returns:
        Major version number, or None if not detected.
    """
    # Build a list of possible Chrome/Chromium executables depending on platform.
    chrome_commands: List[str]
    system = platform.system()
    if system == "Windows":
        # on Windows we can look for the command in PATH or common install locations
        chrome_commands = [
            "chrome",
            "chrome.exe",
            # default installation paths
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files\Chromium\Application\chrome.exe",
        ]
    else:
        chrome_commands = [
            "google-chrome",
            "google-chrome-stable",
            "chromium",
            "chromium-browser",
        ]

    for chrome_cmd in chrome_commands:
        # if the executable isn't available, skip early to avoid noisy logs
        if not os.path.isabs(chrome_cmd):
            # command name; check PATH
            if shutil.which(chrome_cmd) is None:
                continue
        else:
            # absolute path; ensure it exists
            if not os.path.exists(chrome_cmd):
                continue

        version: int | None = None
        try:
            out = subprocess.check_output(
                [chrome_cmd, "--version"], stderr=subprocess.DEVNULL
            )
            text = out.decode()
            # some Windows builds (when Chrome is already running) output
            # "Opening in existing browser session." which contains no version
            # number at all; in that case fall through to the registry lookup
            m = re.search(r"(\d+)", text)
            if m:
                version = int(m.group(1))
                logger.debug("detected %s version %s", chrome_cmd, version)
                return version
        except FileNotFoundError:
            # binary disappeared between which check and invocation
            continue
        except Exception as e:
            logger.debug("failed to get version from %s: %s", chrome_cmd, e)
            continue

    # registry fallback is only meaningful on Windows
    if system == "Windows":
        version = _read_chrome_version_from_registry()
        if version:
            logger.debug("detected chrome version %s via registry", version)
            return version

    return None


class Browser:
    """Manages a Chrome/Chromium browser instance.

    Attributes:
        driver: The Selenium WebDriver instance.
    """

    def __init__(
        self,
        socks_port: Optional[int] = None,
        headless: bool = False,
        flags: Optional[List[str]] = None,
        start_timeout: int | float = 30,
    ):
        """Initialize a new browser.

        Args:
            socks_port: The Tor SOCKS proxy port, or None for direct transport.
            headless: Whether to run browser in headless mode.
            flags: Optional list of Chrome flags to add.
            start_timeout: Seconds to wait for the browser to launch before
                raising an error (default 30s).  This guards against
                undetected-chromedriver hanging indefinitely.
        """
        self.driver: Optional[uc.Chrome] = None
        self.socks_port = socks_port
        self.headless = headless
        self.flags = flags or []
        self._version_main: Optional[int] = None
        self.start_timeout = start_timeout
        self._temp_dir: Optional[str] = None

    def _build_options(self):
        opts = uc.ChromeOptions()
        if self.socks_port:
            proxy = f"socks5://127.0.0.1:{self.socks_port}"
            opts.add_argument(f"--proxy-server={proxy}")
            opts.add_argument(
                "--host-resolver-rules=MAP * ~NOTFOUND , EXCLUDE 127.0.0.1"
            )
            opts.add_argument("--proxy-bypass-list=<-loopback>")

        if self.headless:
            opts.add_argument("--headless=new")

        for flag in self.flags:
            opts.add_argument(flag)

        return opts

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
                "  - Google Chrome: https://www.google.com/chrome/ (Windows/Mac/Linux)\n"
                "  - Chromium: sudo apt install chromium-browser (Debian/Ubuntu)\n"
                "  - brew install chromium (macOS)\n"
                "On Windows the installer is available from the Chrome website above.\n"
                "The browser is required for this script to work."
            )

        opts = self._build_options()

        logger.debug(
            "Starting Chrome with options: socks_port=%s, headless=%s, flags=%s, "
            "version_main=%s, timeout=%s",
            self.socks_port,
            self.headless,
            self.flags,
            self._version_main,
            self.start_timeout,
        )

        with _browser_start_serial_lock:
            # Entire Chrome startup is locked to serialize binary copying and process launch.
            # This completely avoids resource thrashing and parallel file access collisions.

            # Ensure the default undetected_chromedriver binary is downloaded/patched
            # under a global lock to prevent parallel download/write conflicts.
            orig_path = None
            try:
                with _uc_patch_lock:
                    patcher = uc.Patcher()
                    orig_path = patcher.executable_path
                    if not orig_path or not os.path.exists(orig_path):
                        patcher.auto()
                        orig_path = patcher.executable_path
            except Exception as e:
                logger.debug("Could not resolve or patch base undetected_chromedriver binary: %s", e)

            # Copy the executable to a unique per-session path to avoid sharing/disk conflicts
            custom_driver_path = None
            if orig_path and os.path.exists(orig_path):
                try:
                    self._temp_dir = tempfile.mkdtemp(prefix="puypets_")
                    custom_driver_path = os.path.join(self._temp_dir, "chromedriver")
                    shutil.copy2(orig_path, custom_driver_path)
                    os.chmod(custom_driver_path, 0o755)
                    logger.debug("Isolated chromedriver binary created: %s", custom_driver_path)
                except Exception as e:
                    logger.warning("Failed to create isolated chromedriver copy, using default: %s", e)
                    if self._temp_dir and os.path.exists(self._temp_dir):
                        shutil.rmtree(self._temp_dir, ignore_errors=True)
                        self._temp_dir = None

            # Attempt to start Chrome; wrap in a timeout so we don't hang indefinitely
            # (undetected-chromedriver may block while downloading a matching driver,
            # or if the handshake with the browser never completes).  Using a thread
            # executor allows us to enforce a wall‑clock timeout.
            import concurrent.futures

            def _launch():
                if custom_driver_path:
                    if self._version_main:
                        return uc.Chrome(
                            options=opts,
                            version_main=self._version_main,
                            driver_executable_path=custom_driver_path,
                        )
                    else:
                        return uc.Chrome(
                            options=opts,
                            driver_executable_path=custom_driver_path,
                        )
                else:
                    if self._version_main:
                        return uc.Chrome(options=opts, version_main=self._version_main)
                    else:
                        return uc.Chrome(options=opts)

            start_time = time.time()
            timeout = int(getattr(self, "start_timeout", 99))
            try:
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(_launch)
                    # allow callers to override timeout by passing start_timeout attr
                    self.driver = future.result(timeout=timeout)
            except concurrent.futures.TimeoutError as exc:
                raise BrowserError(
                    f"Timed out after {timeout} seconds while starting Chrome/ChromeDriver"
                ) from exc
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
            finally:
                elapsed = time.time() - start_time
                logger.debug(f"uc.Chrome() returned after {elapsed:.1f}s")

        return self.driver

    def stop(self) -> None:
        """Stop the browser."""
        if self.driver:
            try:
                self.driver.quit()
            except Exception:
                pass
            self.driver = None

        if hasattr(self, "_temp_dir") and self._temp_dir and os.path.exists(self._temp_dir):
            try:
                shutil.rmtree(self._temp_dir, ignore_errors=True)
            except Exception:
                pass
            self._temp_dir = None

    def __repr__(self) -> str:
        status = "running" if self.driver else "stopped"
        return (
            f"Browser(socks_port={self.socks_port}, "
            f"headless={self.headless}, status={status!r})"
        )

    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()
        return False
