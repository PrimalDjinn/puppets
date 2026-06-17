"""Tests for browser module."""

import pytest
import platform
import shutil
import os
import time
import threading
from unittest.mock import Mock, patch, MagicMock
from puppets.browser import (
    Browser,
    detect_chrome_version,
    detect_chromedriver_version,
    resolve_chromedriver_executable,
)
from puppets.exceptions import ChromeNotFoundError, BrowserError


class TestDetectChromeVersion:
    """Test detect_chrome_version function."""

    @patch("puppets.browser.subprocess.check_output")
    def test_detects_google_chrome(self, mock_check_output, monkeypatch):
        """Test detection of Google Chrome (non-Windows)."""
        monkeypatch.setattr(platform, "system", lambda: "Linux")
        monkeypatch.setattr(shutil, "which", lambda cmd: cmd)
        mock_check_output.return_value = b"Google Chrome 120.0.6099.109"
        version = detect_chrome_version()
        assert version == 120

    @patch("puppets.browser.subprocess.check_output")
    def test_detects_chromium(self, mock_check_output, monkeypatch):
        """Test detection of Chromium (non-Windows)."""
        monkeypatch.setattr(platform, "system", lambda: "Linux")
        monkeypatch.setattr(shutil, "which", lambda cmd: cmd)
        # First call raises FileNotFoundError, second returns chromium
        mock_check_output.side_effect = [
            FileNotFoundError(),
            b"Chromium 119.0.6045.124",
        ]
        version = detect_chrome_version()
        assert version == 119

    @patch("puppets.browser.subprocess.check_output")
    def test_returns_none_when_no_chrome(self, mock_check_output, monkeypatch):
        """Test returns None when no Chrome is found (non-Windows)."""
        monkeypatch.setattr(platform, "system", lambda: "Linux")
        monkeypatch.setattr(shutil, "which", lambda cmd: None)
        mock_check_output.side_effect = FileNotFoundError()
        version = detect_chrome_version()
        assert version is None

    @patch("puppets.browser.subprocess.check_output")
    def test_detects_chrome_on_windows(self, mock_check_output, monkeypatch):
        """Ensure detection works when running on Windows via binary lookup."""
        monkeypatch.setattr(platform, "system", lambda: "Windows")
        # ensure which resolves so the loop tries the command
        monkeypatch.setattr(shutil, "which", lambda cmd: cmd)
        mock_check_output.return_value = b"Google Chrome 120.0.6099.109"
        version = detect_chrome_version()
        assert version == 120

    @patch("puppets.browser.subprocess.check_output")
    def test_windows_running_chrome_uses_registry(self, mock_check_output, monkeypatch):
        """If invoking the binary returns the "opening" message, fallback to registry."""
        monkeypatch.setattr(platform, "system", lambda: "Windows")
        monkeypatch.setattr(shutil, "which", lambda cmd: cmd)
        # binary output that lacks a version number
        mock_check_output.return_value = b"Opening in existing browser session."
        # mock registry function to return version
        monkeypatch.setattr(
            "puppets.browser._read_chrome_version_from_registry",
            lambda: 123,
        )
        version = detect_chrome_version()
        assert version == 123

    def test_registry_lookup_only(self, monkeypatch):
        """Registry reader returns value even if no executables are present."""
        monkeypatch.setattr(platform, "system", lambda: "Windows")
        monkeypatch.setattr(shutil, "which", lambda cmd: None)
        # ensure absolute path check fails as well
        monkeypatch.setattr(os.path, "exists", lambda p: False)
        monkeypatch.setattr(
            "puppets.browser._read_chrome_version_from_registry",
            lambda: 88,
        )
        version = detect_chrome_version()
        assert version == 88

    @patch("puppets.browser.subprocess.check_output")
    def test_windows_no_chrome(self, mock_check_output, monkeypatch):
        """Return None on Windows when no browser is installed."""
        monkeypatch.setattr(platform, "system", lambda: "Windows")
        monkeypatch.setattr(shutil, "which", lambda cmd: None)
        monkeypatch.setattr(
            "puppets.browser._read_chrome_version_from_registry",
            lambda: None,
        )
        mock_check_output.side_effect = FileNotFoundError()
        version = detect_chrome_version()
        assert version is None


class TestResolveChromeDriverExecutable:
    """Test ChromeDriver resolution."""

    @patch("puppets.browser.subprocess.check_output")
    def test_detects_chromedriver_version(self, mock_check_output):
        """ChromeDriver --version output should parse to a major version."""
        mock_check_output.return_value = b"ChromeDriver 149.0.7827.116"

        assert detect_chromedriver_version(r"C:\drivers\chromedriver.exe") == 149

    @patch("puppets.browser.uc.Patcher")
    def test_reuses_cached_driver_when_major_version_matches(self, mock_patcher_class):
        """Resolver should keep a cached driver that already matches Chrome."""
        mock_patcher = Mock()
        mock_patcher.executable_path = r"C:\drivers\undetected_chromedriver.exe"
        mock_patcher_class.return_value = mock_patcher

        with patch("puppets.browser.os.path.exists", return_value=True):
            with patch("puppets.browser.detect_chromedriver_version", return_value=149):
                path = resolve_chromedriver_executable(149)

        assert path == r"C:\drivers\undetected_chromedriver.exe"
        mock_patcher_class.assert_called_once_with(version_main=149)
        mock_patcher.auto.assert_not_called()

    @patch("puppets.browser.uc.Patcher")
    def test_refreshes_cached_driver_when_major_version_differs(
        self, mock_patcher_class
    ):
        """Resolver should refresh the cache when Chrome has auto-updated."""
        mock_patcher = Mock()
        mock_patcher.executable_path = r"C:\drivers\undetected_chromedriver.exe"
        mock_patcher_class.return_value = mock_patcher

        with patch("puppets.browser.os.path.exists", return_value=True):
            with patch("puppets.browser.detect_chromedriver_version", return_value=145):
                path = resolve_chromedriver_executable(149)

        assert path == r"C:\drivers\undetected_chromedriver.exe"
        mock_patcher_class.assert_called_once_with(version_main=149)
        mock_patcher.auto.assert_called_once_with(version_main=149)

    def test_respects_explicit_driver_path(self, monkeypatch):
        """Users can pin a known-good driver path explicitly."""
        driver_path = r"C:\drivers\chromedriver.exe"
        monkeypatch.setenv("PUPPETS_CHROMEDRIVER_PATH", driver_path)

        with patch("puppets.browser.os.path.exists", return_value=True):
            with patch("puppets.browser.detect_chromedriver_version", return_value=149):
                assert resolve_chromedriver_executable(149) == driver_path

    def test_rejects_explicit_driver_path_for_wrong_major(self, monkeypatch):
        """Pinned drivers should fail fast if they do not match Chrome."""
        driver_path = r"C:\drivers\chromedriver.exe"
        monkeypatch.setenv("PUPPETS_CHROMEDRIVER_PATH", driver_path)

        with patch("puppets.browser.os.path.exists", return_value=True):
            with patch("puppets.browser.detect_chromedriver_version", return_value=145):
                with pytest.raises(BrowserError):
                    resolve_chromedriver_executable(149)


class TestBrowser:
    """Test Browser class."""

    def test_browser_initialization(self):
        """Test Browser initializes with correct values."""
        browser = Browser(socks_port=9050)
        assert browser.socks_port == 9050
        assert browser.driver is None

    def test_browser_start_timeout_attribute(self):
        """Constructor should set the start_timeout attribute."""
        browser = Browser(socks_port=9050, start_timeout=5)
        assert browser.start_timeout == 5

    def test_browser_headless_option(self):
        """Test Browser accepts headless option."""
        browser = Browser(socks_port=9050, headless=True)
        assert browser.headless is True

    @patch("puppets.browser.detect_chrome_version")
    def test_browser_raises_when_no_chrome(self, mock_detect):
        """Test Browser raises ChromeNotFoundError when no Chrome."""
        mock_detect.return_value = None

        browser = Browser(socks_port=9050)

        with pytest.raises(ChromeNotFoundError):
            browser.start()

    @patch("puppets.browser.resolve_chromedriver_executable", return_value="driver")
    @patch("puppets.browser.uc.Chrome")
    @patch("puppets.browser.detect_chrome_version")
    def test_browser_start(self, mock_detect, mock_chrome, mock_resolve):
        """Test Browser.start() creates driver."""
        mock_detect.return_value = 120
        mock_driver = Mock()
        mock_chrome.return_value = mock_driver

        browser = Browser(socks_port=9050)
        driver = browser.start()

        assert driver is mock_driver
        assert browser.driver is mock_driver

    @patch("puppets.browser.resolve_chromedriver_executable", return_value="driver")
    @patch("puppets.browser.uc.Chrome")
    @patch("puppets.browser.detect_chrome_version")
    def test_browser_start_timeout(self, mock_detect, mock_chrome, mock_resolve):
        """Timeout while launching should raise BrowserError."""
        mock_detect.return_value = 120

        def slow_launch(*args, **kwargs):
            import time

            time.sleep(0.1)
            return Mock()

        mock_chrome.side_effect = slow_launch

        browser = Browser(socks_port=9050, start_timeout=0.01)
        with pytest.raises(BrowserError):
            browser.start()

    @patch("puppets.browser.resolve_chromedriver_executable", return_value="driver")
    @patch("puppets.browser.uc.Chrome")
    @patch("puppets.browser.detect_chrome_version")
    def test_browser_start_timeout_does_not_wait_for_stuck_launcher(
        self, mock_detect, mock_chrome, mock_resolve
    ):
        """A stuck Chrome launch should not pin Browser.start() after timeout."""
        mock_detect.return_value = 120
        never_return = threading.Event()
        mock_chrome.side_effect = lambda *args, **kwargs: never_return.wait()

        browser = Browser(socks_port=9050, start_timeout=0.01)
        started_at = time.perf_counter()
        with pytest.raises(BrowserError):
            browser.start()

        assert time.perf_counter() - started_at < 0.5

    def test_browser_stop(self):
        """Test Browser.stop() quits driver."""
        browser = Browser(socks_port=9050)
        mock_driver = Mock()
        browser.driver = mock_driver

        browser.stop()

        mock_driver.quit.assert_called_once()
        assert browser.driver is None

    @patch("puppets.browser.resolve_chromedriver_executable", return_value="driver")
    @patch("puppets.browser.uc.Chrome")
    @patch("puppets.browser.detect_chrome_version")
    def test_browser_context_manager(self, mock_detect, mock_chrome, mock_resolve):
        """Test Browser as context manager."""
        mock_detect.return_value = 120
        mock_driver = Mock()
        mock_chrome.return_value = mock_driver

        with Browser(socks_port=9050) as browser:
            assert browser.driver is not None

        mock_driver.quit.assert_called_once()
