"""Tests for browser module."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from puppets.browser import Browser, detect_chrome_version
from puppets.exceptions import ChromeNotFoundError, BrowserError


class TestDetectChromeVersion:
    """Test detect_chrome_version function."""

    @patch('puppets.browser.subprocess.check_output')
    def test_detects_google_chrome(self, mock_check_output):
        """Test detection of Google Chrome."""
        mock_check_output.return_value = b"Google Chrome 120.0.6099.109"
        version = detect_chrome_version()
        assert version == 120

    @patch('puppets.browser.subprocess.check_output')
    def test_detects_chromium(self, mock_check_output):
        """Test detection of Chromium."""
        # First call raises FileNotFoundError, second returns chromium
        mock_check_output.side_effect = [
            FileNotFoundError(),
            b"Chromium 119.0.6045.124"
        ]
        version = detect_chrome_version()
        assert version == 119

    @patch('puppets.browser.subprocess.check_output')
    def test_returns_none_when_no_chrome(self, mock_check_output):
        """Test returns None when no Chrome is found."""
        mock_check_output.side_effect = FileNotFoundError()
        version = detect_chrome_version()
        assert version is None


class TestBrowser:
    """Test Browser class."""

    def test_browser_initialization(self):
        """Test Browser initializes with correct values."""
        browser = Browser(socks_port=9050)
        assert browser.socks_port == 9050
        assert browser.driver is None

    def test_browser_headless_option(self):
        """Test Browser accepts headless option."""
        browser = Browser(socks_port=9050, headless=True)
        assert browser.headless is True

    @patch('puppets.browser.detect_chrome_version')
    def test_browser_raises_when_no_chrome(self, mock_detect):
        """Test Browser raises ChromeNotFoundError when no Chrome."""
        mock_detect.return_value = None
        
        browser = Browser(socks_port=9050)
        
        with pytest.raises(ChromeNotFoundError):
            browser.start()

    @patch('puppets.browser.uc.Chrome')
    @patch('puppets.browser.detect_chrome_version')
    def test_browser_start(self, mock_detect, mock_chrome):
        """Test Browser.start() creates driver."""
        mock_detect.return_value = 120
        mock_driver = Mock()
        mock_chrome.return_value = mock_driver
        
        browser = Browser(socks_port=9050)
        driver = browser.start()
        
        assert driver is mock_driver
        assert browser.driver is mock_driver

    def test_browser_stop(self):
        """Test Browser.stop() quits driver."""
        browser = Browser(socks_port=9050)
        mock_driver = Mock()
        browser.driver = mock_driver
        
        browser.stop()
        
        mock_driver.quit.assert_called_once()
        assert browser.driver is None

    @patch('puppets.browser.uc.Chrome')
    @patch('puppets.browser.detect_chrome_version')
    def test_browser_context_manager(self, mock_detect, mock_chrome):
        """Test Browser as context manager."""
        mock_detect.return_value = 120
        mock_driver = Mock()
        mock_chrome.return_value = mock_driver
        
        with Browser(socks_port=9050) as browser:
            assert browser.driver is not None
        
        mock_driver.quit.assert_called_once()