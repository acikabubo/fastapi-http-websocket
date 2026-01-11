"""
Tests for IP address utilities.

This module tests IP extraction and spoofing protection functionality.
"""

from unittest.mock import MagicMock, patch

from starlette.requests import Request

from {{cookiecutter.module_name}}.utils.ip_utils import get_client_ip, is_trusted_proxy


class TestIsTrustedProxy:
    """Tests for is_trusted_proxy function."""

    def test_empty_trusted_proxies_list(self):
        """Test returns False when TRUSTED_PROXIES is empty."""
        with patch("{{cookiecutter.module_name}}.utils.ip_utils.app_settings") as mock_settings:
            mock_settings.TRUSTED_PROXIES = []

            result = is_trusted_proxy("192.168.1.1")

        assert result is False

    def test_single_ip_match(self):
        """Test matching against single IP address."""
        with patch("{{cookiecutter.module_name}}.utils.ip_utils.app_settings") as mock_settings:
            mock_settings.TRUSTED_PROXIES = ["192.168.1.100"]

            assert is_trusted_proxy("192.168.1.100") is True
            assert is_trusted_proxy("192.168.1.101") is False

    def test_cidr_network_match(self):
        """Test matching against CIDR network."""
        with patch("{{cookiecutter.module_name}}.utils.ip_utils.app_settings") as mock_settings:
            mock_settings.TRUSTED_PROXIES = ["192.168.1.0/24"]

            assert is_trusted_proxy("192.168.1.1") is True
            assert is_trusted_proxy("192.168.1.254") is True
            assert is_trusted_proxy("192.168.2.1") is False

    def test_multiple_proxies(self):
        """Test matching against multiple proxies."""
        with patch("{{cookiecutter.module_name}}.utils.ip_utils.app_settings") as mock_settings:
            mock_settings.TRUSTED_PROXIES = [
                "10.0.0.0/8",
                "172.16.0.0/12",
                "192.168.1.100",
            ]

            assert is_trusted_proxy("10.0.1.1") is True
            assert is_trusted_proxy("172.16.0.1") is True
            assert is_trusted_proxy("192.168.1.100") is True
            assert is_trusted_proxy("1.2.3.4") is False

    def test_invalid_ip_address(self):
        """Test handling of invalid IP address."""
        with patch("{{cookiecutter.module_name}}.utils.ip_utils.app_settings") as mock_settings:
            mock_settings.TRUSTED_PROXIES = ["192.168.1.0/24"]

            result = is_trusted_proxy("invalid-ip")

        assert result is False

    def test_invalid_proxy_in_list(self):
        """Test handling of invalid proxy in TRUSTED_PROXIES."""
        with (
            patch("{{cookiecutter.module_name}}.utils.ip_utils.app_settings") as mock_settings,
            patch("{{cookiecutter.module_name}}.utils.ip_utils.logger") as mock_logger,
        ):
            mock_settings.TRUSTED_PROXIES = [
                "192.168.1.0/24",
                "invalid-proxy",
                "10.0.0.1",
            ]

            # Should match valid proxy despite invalid one in list
            assert is_trusted_proxy("10.0.0.1") is True

            # Should warn about invalid proxy
            mock_logger.warning.assert_called()

    def test_ipv6_address(self):
        """Test IPv6 address matching."""
        with patch("{{cookiecutter.module_name}}.utils.ip_utils.app_settings") as mock_settings:
            mock_settings.TRUSTED_PROXIES = [
                "2001:db8::/32",
                "::1",
            ]

            assert is_trusted_proxy("2001:db8::1") is True
            assert is_trusted_proxy("::1") is True
            assert is_trusted_proxy("2001:db9::1") is False


class TestGetClientIp:
    """Tests for get_client_ip function."""

    def test_get_ip_without_forwarded_header(self):
        """Test getting IP when no X-Forwarded-For header."""
        request = MagicMock(spec=Request)
        request.client = MagicMock()
        request.client.host = "192.168.1.100"
        request.headers = {}

        ip = get_client_ip(request)

        assert ip == "192.168.1.100"

    def test_get_ip_from_trusted_proxy(self):
        """Test getting IP from X-Forwarded-For when from trusted proxy."""
        request = MagicMock(spec=Request)
        request.client = MagicMock()
        request.client.host = "10.0.0.1"  # Trusted proxy
        request.headers = {"X-Forwarded-For": "203.0.113.1"}

        with patch("{{cookiecutter.module_name}}.utils.ip_utils.app_settings") as mock_settings:
            mock_settings.TRUSTED_PROXIES = ["10.0.0.0/8"]

            ip = get_client_ip(request)

        assert ip == "203.0.113.1"

    def test_get_ip_ignores_untrusted_proxy(self):
        """Test ignoring X-Forwarded-For from untrusted proxy."""
        request = MagicMock(spec=Request)
        request.client = MagicMock()
        request.client.host = "1.2.3.4"  # Untrusted proxy
        request.headers = {"X-Forwarded-For": "203.0.113.1"}

        with (
            patch("{{cookiecutter.module_name}}.utils.ip_utils.app_settings") as mock_settings,
            patch("{{cookiecutter.module_name}}.utils.ip_utils.logger") as mock_logger,
        ):
            mock_settings.TRUSTED_PROXIES = ["10.0.0.0/8"]

            ip = get_client_ip(request)

        assert ip == "1.2.3.4"  # Should return proxy IP, not forwarded IP
        mock_logger.warning.assert_called()

    def test_get_ip_from_multiple_forwarded(self):
        """Test extracting first IP from chain of proxies."""
        request = MagicMock(spec=Request)
        request.client = MagicMock()
        request.client.host = "10.0.0.1"  # Trusted proxy
        request.headers = {
            "X-Forwarded-For": "203.0.113.1, 10.0.0.2, 10.0.0.3"
        }

        with patch("{{cookiecutter.module_name}}.utils.ip_utils.app_settings") as mock_settings:
            mock_settings.TRUSTED_PROXIES = ["10.0.0.0/8"]

            ip = get_client_ip(request)

        # Should extract first IP (original client)
        assert ip == "203.0.113.1"

    def test_get_ip_with_whitespace_in_forwarded(self):
        """Test handling whitespace in X-Forwarded-For."""
        request = MagicMock(spec=Request)
        request.client = MagicMock()
        request.client.host = "10.0.0.1"  # Trusted proxy
        request.headers = {"X-Forwarded-For": "  203.0.113.1  , 10.0.0.2"}

        with patch("{{cookiecutter.module_name}}.utils.ip_utils.app_settings") as mock_settings:
            mock_settings.TRUSTED_PROXIES = ["10.0.0.0/8"]

            ip = get_client_ip(request)

        # Should strip whitespace
        assert ip == "203.0.113.1"

    def test_get_ip_no_client(self):
        """Test handling request with no client attribute."""
        request = MagicMock(spec=Request)
        request.client = None
        request.headers = {}

        ip = get_client_ip(request)

        assert ip == "unknown"

    def test_get_ip_with_proper_header_casing(self):
        """Test X-Forwarded-For header with proper casing."""
        request = MagicMock(spec=Request)
        request.client = MagicMock()
        request.client.host = "10.0.0.1"  # Trusted proxy
        # Use standard header casing (Starlette normalizes headers)
        request.headers = {"X-Forwarded-For": "203.0.113.1"}

        with patch("{{cookiecutter.module_name}}.utils.ip_utils.app_settings") as mock_settings:
            mock_settings.TRUSTED_PROXIES = ["10.0.0.0/8"]

            ip = get_client_ip(request)

        assert ip == "203.0.113.1"

    def test_get_ip_logs_trusted_proxy_usage(self):
        """Test that using X-Forwarded-For from trusted proxy is logged."""
        request = MagicMock(spec=Request)
        request.client = MagicMock()
        request.client.host = "10.0.0.1"  # Trusted proxy
        request.headers = {"X-Forwarded-For": "203.0.113.1"}

        with (
            patch("{{cookiecutter.module_name}}.utils.ip_utils.app_settings") as mock_settings,
            patch("{{cookiecutter.module_name}}.utils.ip_utils.logger") as mock_logger,
        ):
            mock_settings.TRUSTED_PROXIES = ["10.0.0.0/8"]

            get_client_ip(request)

        # Should log debug message about using X-Forwarded-For
        mock_logger.debug.assert_called()
        debug_msg = mock_logger.debug.call_args[0][0]
        assert "X-Forwarded-For" in debug_msg
        assert "203.0.113.1" in debug_msg
