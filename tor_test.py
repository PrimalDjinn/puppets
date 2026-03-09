import undetected_chromedriver as webdriver
import time
import socket
import shutil
import logging
import subprocess
import re

import requests
from stem.control import Controller
from stem import Signal
from stem import process
from selenium.common.exceptions import WebDriverException

logging.basicConfig(level=logging.INFO)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_free_port() -> int:
    """Return an unused TCP port number on localhost."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


def _is_port_open(host: str, port: int, timeout: float = 1.0) -> bool:
    """Return True if *host:port* is accepting TCP connections."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(timeout)
        try:
            s.connect((host, port))
            return True
        except Exception:
            return False


def _chrome_major_version() -> int | None:
    """Detect the installed Chrome/Chromium major version, or None."""
    for binary in ("google-chrome", "chromium-browser", "chromium"):
        try:
            out = subprocess.check_output([binary, "--version"],
                                          stderr=subprocess.DEVNULL)
            m = re.search(r"(\d+)", out.decode())
            if m:
                return int(m.group(1))
        except Exception:
            continue
    return None


# ---------------------------------------------------------------------------
# Tor management
# ---------------------------------------------------------------------------

def launch_tor(timeout: int = 120):
    """Start a Tor process on free ports and return *(process, socks_port, control_port)*."""
    socks_port = get_free_port()
    control_port = get_free_port()

    tor_cmd = shutil.which("tor") or "/usr/sbin/tor"
    logging.info("starting tor  socks_port=%s  control_port=%s  binary=%s",
                 socks_port, control_port, tor_cmd)

    try:
        tor_proc = process.launch_tor_with_config(
            tor_cmd=tor_cmd,
            config={
                "SocksPort": str(socks_port),
                "ControlPort": str(control_port),
                "CookieAuthentication": "1",
            },
            timeout=timeout,
            init_msg_handler=lambda msg: logging.debug("tor: %s", msg),
            take_ownership=True,
        )
    except OSError as exc:
        logging.error("could not start tor: %s", exc)
        raise

    return tor_proc, socks_port, control_port


def new_identity(control_port: int):
    """Signal Tor for a new identity and wait for the circuit to rebuild."""
    with Controller.from_port(port=control_port) as controller:
        controller.authenticate()
        controller.signal(Signal.NEWNYM)
    time.sleep(3)


def check_tor_proxy(socks_port: int) -> str:
    """Make a quick HTTP request through Tor and return the exit IP."""
    proxies = {
        "http":  f"socks5h://127.0.0.1:{socks_port}",
        "https": f"socks5h://127.0.0.1:{socks_port}",
    }
    resp = requests.get("http://www.icanhazip.com", proxies=proxies, timeout=15)
    resp.raise_for_status()
    return resp.text.strip()


def wait_for_tor(socks_port: int, timeout: int = 60) -> str:
    """Block until the Tor proxy has a working circuit, then return the IP."""
    start = time.time()
    while True:
        try:
            return check_tor_proxy(socks_port)
        except Exception:
            if time.time() - start > timeout:
                raise RuntimeError("timed out waiting for Tor circuit")
            time.sleep(1)


# ---------------------------------------------------------------------------
# Browser
# ---------------------------------------------------------------------------

def browse_through_tor(socks_port: int):
    """Launch an undetected Chrome instance routed through Tor and return the driver."""
    if not _is_port_open("127.0.0.1", socks_port):
        raise RuntimeError(f"nothing listening on socks port {socks_port}")

    try:
        ip = wait_for_tor(socks_port, timeout=30)
        logging.debug("tor proxy answered – current ip %s", ip)
    except Exception as exc:
        logging.warning("tor proxy sanity check failed: %s", exc)

    PROXY = f"socks5://127.0.0.1:{socks_port}"
    version_main = _chrome_major_version()

    for attempt in range(3):
        opts = webdriver.ChromeOptions()
        opts.add_argument(f"--proxy-server={PROXY}")

        driver = (webdriver.Chrome(options=opts, version_main=version_main)
                  if version_main
                  else webdriver.Chrome(options=opts))
        try:
            driver.get("http://www.icanhazip.com")
            time.sleep(5)
            return driver
        except WebDriverException as exc:
            logging.warning("browser attempt %s failed: %s", attempt + 1, exc)
            driver.quit()
            if attempt < 2:
                time.sleep(3)
            else:
                raise

    raise RuntimeError("unable to start browser with working tor proxy")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    tor_proc, socks_port, control_port = launch_tor()

    try:
        # --- first request ---
        driver = browse_through_tor(socks_port)
        logging.info("first request done")
        driver.quit()

        # --- rotate identity ---
        new_identity(control_port)
        logging.info("new identity requested")

        ip = wait_for_tor(socks_port, timeout=30)
        logging.info("tor ready after NEWNYM – new ip %s", ip)

        # --- second request ---
        driver = browse_through_tor(socks_port)
        logging.info("second request done")
        time.sleep(5)
    finally:
        tor_proc.terminate()
        try:
            driver.quit()
        except Exception:
            pass

