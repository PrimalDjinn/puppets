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
import queue
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


def detect_chromedriver_version(driver_path: str) -> Optional[int]:
    """Detect the ChromeDriver major version for an executable path."""
    try:
        out = subprocess.check_output(
            [driver_path, "--version"], stderr=subprocess.DEVNULL, timeout=10
        )
    except Exception as exc:
        logger.debug("failed to get ChromeDriver version from %s: %s", driver_path, exc)
        return None

    m = re.search(r"ChromeDriver\s+(\d+)", out.decode(errors="replace"))
    if not m:
        return None
    return int(m.group(1))


def resolve_chromedriver_executable(version_main: int) -> str:
    """Resolve a ChromeDriver executable compatible with the browser version."""
    override_path = os.environ.get("PUPPETS_CHROMEDRIVER_PATH")
    if override_path:
        if not os.path.exists(override_path):
            raise BrowserError(
                "PUPPETS_CHROMEDRIVER_PATH points to a missing file: "
                f"{override_path}"
            )
        override_version = detect_chromedriver_version(override_path)
        if override_version is not None and override_version != version_main:
            raise BrowserError(
                "PUPPETS_CHROMEDRIVER_PATH points to ChromeDriver "
                f"{override_version}, but Chrome is {version_main}: {override_path}"
            )
        return override_path

    patcher = uc.Patcher(version_main=version_main)
    executable_path = patcher.executable_path
    if executable_path and os.path.exists(executable_path):
        driver_version = detect_chromedriver_version(executable_path)
        if driver_version == version_main:
            return executable_path
        logger.info(
            "Refreshing ChromeDriver cache: found version %s, need %s",
            driver_version or "unknown",
            version_main,
        )

    patcher.auto(version_main=version_main)
    executable_path = patcher.executable_path
    if not executable_path or not os.path.exists(executable_path):
        raise BrowserError(
            "undetected-chromedriver did not provide a ChromeDriver executable "
            f"for Chrome {version_main}"
        )
    return executable_path


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
                "  - Chromium: sudo apt install chromium (Debian/Ubuntu)\n"
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

            # Resolve/download the ChromeDriver binary under a global lock to
            # prevent parallel download/write conflicts.
            orig_path = None
            try:
                with _uc_patch_lock:
                    orig_path = resolve_chromedriver_executable(self._version_main)
            except BrowserError:
                raise
            except Exception as e:
                logger.debug(
                    "Could not resolve compatible undetected_chromedriver binary: %s",
                    e,
                )

            # Copy the executable to a unique per-session path to avoid sharing/disk conflicts
            custom_driver_path = None
            if orig_path and os.path.exists(orig_path):
                try:
                    self._temp_dir = tempfile.mkdtemp(prefix="puypets_")
                    custom_driver_path = os.path.join(
                        self._temp_dir, os.path.basename(orig_path)
                    )
                    shutil.copy2(orig_path, custom_driver_path)
                    os.chmod(custom_driver_path, 0o755)
                    logger.debug(
                        "Isolated chromedriver binary created: %s", custom_driver_path
                    )
                except Exception as e:
                    logger.warning(
                        "Failed to create isolated chromedriver copy, using default: %s",
                        e,
                    )
                    if self._temp_dir and os.path.exists(self._temp_dir):
                        shutil.rmtree(self._temp_dir, ignore_errors=True)
                        self._temp_dir = None

            # Attempt to start Chrome; wrap in a daemon thread so a stuck
            # ChromeDriver handshake cannot pin the caller indefinitely.
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
            result_queue: queue.Queue[tuple[str, object]] = queue.Queue(maxsize=1)
            timed_out = threading.Event()

            def _launch_worker():
                try:
                    driver = _launch()
                except Exception as exc:
                    if not timed_out.is_set():
                        result_queue.put(("error", exc))
                    return

                if timed_out.is_set():
                    try:
                        driver.quit()
                    except Exception:
                        pass
                    return

                result_queue.put(("driver", driver))

            launch_thread = threading.Thread(
                target=_launch_worker,
                name="puypets-chrome-launch",
                daemon=True,
            )
            try:
                launch_thread.start()
                status, payload = result_queue.get(timeout=timeout)
                if status == "error":
                    if isinstance(payload, Exception):
                        raise payload
                    raise RuntimeError(payload)
                self.driver = payload  # type: ignore[assignment]
            except queue.Empty as exc:
                timed_out.set()
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
                        "Try refreshing the driver cache, upgrading "
                        "undetected-chromedriver, or setting "
                        "PUPPETS_CHROMEDRIVER_PATH to a matching ChromeDriver."
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

        if (
            hasattr(self, "_temp_dir")
            and self._temp_dir
            and os.path.exists(self._temp_dir)
        ):
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
