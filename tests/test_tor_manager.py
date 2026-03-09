"""Tests for Tor manager."""

import pytest
import socket
from unittest.mock import Mock, patch, MagicMock
from puppets.tor_manager import TorInstance, get_free_port, find_tor_executable
from puppets.exceptions import TorLaunchError


class TestGetFreePort:
    """Test get_free_port function."""

    def test_get_free_port_returns_integer(self):
        """Test that get_free_port returns an integer."""
        port = get_free_port()
        assert isinstance(port, int)

    def test_get_free_port_in_valid_range(self):
        """Test that port is in valid range."""
        port = get_free_port()
        assert 1024 <= port <= 65535

    def test_get_free_port_returns_different_ports(self):
        """Test that multiple calls return different ports."""
        ports = [get_free_port() for _ in range(10)]
        assert len(set(ports)) == 10  # All unique


class TestFindTorExecutable:
    """Test find_tor_executable function."""

    @patch('puppets.tor_manager.shutil.which')
    def test_finds_tor_in_path(self, mock_which):
        """Test that tor is found in PATH."""
        mock_which.return_value = "/usr/bin/tor"
        result = find_tor_executable()
        assert result == "/usr/bin/tor"

    @patch('puppets.tor_manager.shutil.which')
    @patch('puppets.tor_manager.os.path.isfile')
    @patch('puppets.tor_manager.os.access')
    def test_finds_tor_in_common_paths(self, mock_access, mock_isfile, mock_which):
        """Test that tor is found in common paths when not in PATH."""
        mock_which.return_value = None
        mock_isfile.return_value = True
        mock_access.return_value = True
        
        result = find_tor_executable()
        assert result in ["/usr/sbin/tor", "/usr/bin/tor", "/usr/local/bin/tor"]

    @patch('puppets.tor_manager.shutil.which')
    @patch('puppets.tor_manager.os.path.isfile', return_value=False)
    def test_raises_error_when_tor_not_found(self, mock_isfile, mock_which):
        """Test that error is raised when tor is not found."""
        mock_which.return_value = None
        
        with pytest.raises(TorLaunchError) as exc_info:
            find_tor_executable()
        
        assert "Tor executable not found" in str(exc_info.value)


class TestTorInstance:
    """Test TorInstance class."""

    def test_tor_instance_initialization(self):
        """Test TorInstance initializes with default values."""
        instance = TorInstance()
        assert instance.process is None
        assert instance.socks_port == 0
        assert instance.control_port == 0

    def test_tor_instance_custom_timeout(self):
        """Test TorInstance accepts custom timeout."""
        instance = TorInstance(timeout=60)
        assert instance._timeout == 60

    @patch('puppets.tor_manager.process.launch_tor_with_config')
    @patch('puppets.tor_manager.find_tor_executable')
    def test_tor_instance_start(self, mock_find_tor, mock_launch):
        """Test TorInstance.start() launches Tor."""
        mock_find_tor.return_value = "/usr/bin/tor"
        mock_process = Mock()
        mock_launch.return_value = mock_process
        
        instance = TorInstance()
        process, socks_port, control_port = instance.start()
        
        assert process is mock_process
        assert socks_port > 0
        assert control_port > 0
        assert socks_port != control_port

    def test_tor_instance_stop(self):
        """Test TorInstance.stop() terminates process."""
        instance = TorInstance()
        mock_process = Mock()
        instance.process = mock_process
        
        instance.stop()
        
        mock_process.terminate.assert_called_once()
        assert instance.process is None

    def test_tor_instance_context_manager(self):
        """Test TorInstance as context manager."""
        with patch('puppets.tor_manager.process.launch_tor_with_config') as mock_launch:
            with patch('puppets.tor_manager.find_tor_executable') as mock_find:
                mock_find.return_value = "/usr/bin/tor"
                mock_process = Mock()
                mock_launch.return_value = mock_process
                
                with TorInstance() as instance:
                    assert instance.process is not None
                
                mock_process.terminate.assert_called_once()