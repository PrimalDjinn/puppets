"""Tests for session module."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from puppets.session import Session, is_port_open, check_tor_proxy, wait_for_tor
from puppets.exceptions import TorConnectionError


class TestIsPortOpen:
    """Test is_port_open function."""

    def test_is_port_open_returns_bool(self):
        """Test is_port_open returns boolean."""
        result = is_port_open("127.0.0.1", 9999, timeout=0.1)
        assert isinstance(result, bool)

    def test_is_port_open_closed_port(self):
        """Test returns False for closed port."""
        result = is_port_open("127.0.0.1", 1, timeout=0.1)
        assert result is False


class TestCheckTorProxy:
    """Test check_tor_proxy function."""

    @patch('puppets.session.requests.get')
    def test_check_tor_proxy_success(self, mock_get):
        """Test successful proxy check."""
        mock_response = Mock()
        mock_response.text.strip.return_value = "1.2.3.4"
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        result = check_tor_proxy(9050)
        
        assert result == "1.2.3.4"

    @patch('puppets.session.requests.get')
    def test_check_tor_proxy_connection_error(self, mock_get):
        """Test connection error handling."""
        import requests
        mock_get.side_effect = requests.exceptions.ConnectionError()
        
        with pytest.raises(TorConnectionError):
            check_tor_proxy(9050)

    @patch('puppets.session.requests.get')
    def test_check_tor_proxy_timeout(self, mock_get):
        """Test timeout error handling."""
        import requests
        mock_get.side_effect = requests.exceptions.Timeout()
        
        with pytest.raises(TorConnectionError):
            check_tor_proxy(9050)


class TestWaitForTor:
    """Test wait_for_tor function."""

    @patch('puppets.session.check_tor_proxy')
    def test_wait_for_tor_success(self, mock_check):
        """Test successful wait."""
        mock_check.return_value = "1.2.3.4"
        
        result = wait_for_tor(9050, timeout=5)
        
        assert result == "1.2.3.4"

    @patch('puppets.session.check_tor_proxy')
    def test_wait_for_tor_timeout(self, mock_check):
        """Test timeout handling."""
        mock_check.side_effect = Exception("Connection refused")
        
        with pytest.raises(TorConnectionError) as exc_info:
            wait_for_tor(9050, timeout=1)
        
        assert "timed out" in str(exc_info.value).lower()


class TestSession:
    """Test Session class."""

    def test_session_initialization(self):
        """Test Session initializes with default values."""
        session = Session()
        assert session.session_id is not None
        assert session.headless is False
        assert session.tor_instance is None
        assert session.browser is None

    def test_session_custom_id(self):
        """Test Session accepts custom ID."""
        session = Session(session_id="test_123", headless=True)
        assert session.session_id == "test_123"

    def test_session_headless_option(self):
        """Test Session accepts headless option."""
        session = Session(headless=True)
        assert session.headless is True

    @patch('puppets.session.TorInstance')
    @patch('puppets.session.Browser')
    def test_session_run(self, mock_browser_class, mock_tor_class):
        """Test Session.run() executes successfully."""
        # Mock Tor
        mock_tor = Mock()
        mock_tor.socks_port = 9050
        mock_tor.start = Mock()
        mock_tor_class.return_value = mock_tor

        # Mock browser
        mock_browser = Mock()
        mock_browser.start = Mock()
        mock_browser_class.return_value = mock_browser

        # Mock wait_for_tor
        with patch('puppets.session.wait_for_tor', return_value="1.2.3.4"):
            session = Session(headless=True)
            result = session.run("https://example.com")
            
            assert result['success'] is True
            assert result['ip'] == "1.2.3.4"
            assert result['socks_port'] == 9050

    def test_session_cleanup(self):
        """Test Session.cleanup() releases resources."""
        session = Session()
        
        mock_tor = Mock()
        mock_browser = Mock()
        
        session.tor_instance = mock_tor
        session.browser = mock_browser
        
        session.cleanup()
        
        mock_tor.stop.assert_called_once()
        mock_browser.stop.assert_called_once()
        assert session.tor_instance is None
        assert session.browser is None

    @patch('puppets.tor_manager.TorInstance')
    def test_session_context_manager(self, mock_tor_class):
        """Test Session as context manager."""
        mock_tor = Mock()
        mock_tor.socks_port = 9050
        mock_tor.start = Mock()
        mock_tor_class.return_value = mock_tor

        with patch('puppets.session.wait_for_tor', return_value="1.2.3.4"):
            with patch('puppets.browser.Browser') as mock_browser_class:
                mock_browser = Mock()
                mock_browser.start = Mock()
                mock_browser_class.return_value = mock_browser
                
                with Session(headless=True) as session:
                    session.tor_instance = mock_tor
                    assert session.tor_instance is not None
                
                mock_tor.stop.assert_called_once()