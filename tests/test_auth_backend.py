"""
Comprehensive tests for AuthBackend.authenticate() method.

This module tests the authentication integration including:
- Token caching integration (cache hits/misses)
- Prometheus metrics tracking
- WebSocket authentication success scenarios
- Edge cases (missing/malformed tokens)
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.auth import AuthBackend
from app.exceptions import AuthenticationError
from tests.mocks.auth_mocks import create_mock_keycloak_manager


class TestAuthBackendTokenCaching:
    """Test token caching integration in authenticate() method."""

    @pytest.mark.asyncio
    async def test_cache_hit_skips_token_decode(self, mock_user_data):
        """Test that cache hit skips Keycloak token decoding."""
        auth_backend = AuthBackend()

        request = MagicMock()
        request.scope = {"type": "http"}
        request.url.path = "/api/test"
        request.headers.get.return_value = "Bearer cached_token"

        mock_kc_manager = create_mock_keycloak_manager()

        with patch("app.auth.keycloak_manager", mock_kc_manager):
            # Mock cache hit - returns user data from cache
            with patch(
                "app.utils.token_cache.get_cached_token_claims",
                new_callable=AsyncMock,
                return_value=mock_user_data,
            ):
                # Mock cache_token_claims to verify it's NOT called
                with patch(
                    "app.utils.token_cache.cache_token_claims",
                    new_callable=AsyncMock,
                ) as mock_cache:
                    result = await auth_backend.authenticate(request)

                    # Should return successful authentication
                    assert result is not None
                    credentials, user = result
                    assert (
                        user.username == mock_user_data["preferred_username"]
                    )

                    # Token decode should NOT be called (cache hit)
                    mock_kc_manager.openid.a_decode_token.assert_not_called()

                    # Cache write should NOT be called (already cached)
                    mock_cache.assert_not_called()

    @pytest.mark.asyncio
    async def test_cache_miss_decodes_and_caches_token(self, mock_user_data):
        """Test that cache miss triggers decode and caches result."""
        auth_backend = AuthBackend()

        request = MagicMock()
        request.scope = {"type": "http"}
        request.url.path = "/api/test"
        request.headers.get.return_value = "Bearer uncached_token"

        mock_kc_manager = create_mock_keycloak_manager()
        mock_kc_manager.openid.a_decode_token = AsyncMock(
            return_value=mock_user_data
        )

        with patch("app.auth.app_settings.DEBUG_AUTH", False):
            with patch("app.auth.keycloak_manager", mock_kc_manager):
                # Mock cache miss - returns None
                with patch(
                    "app.utils.token_cache.get_cached_token_claims",
                    new_callable=AsyncMock,
                    return_value=None,
                ):
                    # Mock cache_token_claims to verify it's called
                    with patch(
                        "app.utils.token_cache.cache_token_claims",
                        new_callable=AsyncMock,
                    ) as mock_cache:
                        result = await auth_backend.authenticate(request)

                        # Should return successful authentication
                        assert result is not None
                        credentials, user = result
                        assert (
                            user.username
                            == mock_user_data["preferred_username"]
                        )

                        # Token decode SHOULD be called (cache miss)
                        mock_kc_manager.openid.a_decode_token.assert_called_once_with(
                            "uncached_token"
                        )

                        # Cache write SHOULD be called with decoded data
                        mock_cache.assert_called_once_with(
                            "uncached_token", mock_user_data
                        )


class TestAuthBackendMetrics:
    """Test Prometheus metrics tracking in authenticate() method."""

    @pytest.mark.asyncio
    async def test_successful_auth_tracks_metrics(self, mock_user_data):
        """Test that successful authentication tracks all metrics."""
        auth_backend = AuthBackend()

        request = MagicMock()
        request.scope = {"type": "http"}
        request.url.path = "/api/test"
        request.headers.get.return_value = "Bearer valid_token"

        mock_kc_manager = create_mock_keycloak_manager()
        mock_kc_manager.openid.a_decode_token = AsyncMock(
            return_value=mock_user_data
        )

        with patch("app.auth.keycloak_manager", mock_kc_manager):
            with patch(
                "app.utils.token_cache.get_cached_token_claims",
                new_callable=AsyncMock,
                return_value=None,
            ):
                with patch(
                    "app.utils.token_cache.cache_token_claims",
                    new_callable=AsyncMock,
                ):
                    # Mock metrics
                    with patch(
                        "app.utils.metrics.keycloak_token_validation_total"
                    ) as mock_validation:
                        with patch(
                            "app.utils.metrics.auth_backend_requests_total"
                        ) as mock_backend:
                            with patch(
                                "app.utils.metrics.keycloak_operation_duration_seconds"
                            ) as mock_duration:
                                await auth_backend.authenticate(request)

                                # Verify token validation metric
                                mock_validation.labels.assert_called_with(
                                    status="valid", reason="success"
                                )
                                mock_validation.labels().inc.assert_called_once()

                                # Verify auth backend metric
                                mock_backend.labels.assert_called_with(
                                    type="http", outcome="success"
                                )
                                mock_backend.labels().inc.assert_called_once()

                                # Verify duration metric
                                mock_duration.labels.assert_called_with(
                                    operation="validate_token"
                                )
                                mock_duration.labels().observe.assert_called_once()

    @pytest.mark.asyncio
    async def test_websocket_auth_tracks_websocket_metrics(
        self, mock_user_data
    ):
        """Test that WebSocket auth tracks type='websocket' in metrics."""
        auth_backend = AuthBackend()

        request = MagicMock()
        request.scope = {
            "type": "websocket",
            "query_string": b"Authorization=Bearer%20ws_token",
        }

        mock_kc_manager = create_mock_keycloak_manager()
        mock_kc_manager.openid.a_decode_token = AsyncMock(
            return_value=mock_user_data
        )

        with patch("app.auth.keycloak_manager", mock_kc_manager):
            with patch(
                "app.utils.token_cache.get_cached_token_claims",
                new_callable=AsyncMock,
                return_value=None,
            ):
                with patch(
                    "app.utils.token_cache.cache_token_claims",
                    new_callable=AsyncMock,
                ):
                    with patch(
                        "app.utils.metrics.auth_backend_requests_total"
                    ) as mock_backend:
                        with patch(
                            "app.utils.metrics.keycloak_token_validation_total"
                        ):
                            with patch(
                                "app.utils.metrics.keycloak_operation_duration_seconds"
                            ):
                                await auth_backend.authenticate(request)

                                # Verify WebSocket type in metric
                                mock_backend.labels.assert_called_with(
                                    type="websocket", outcome="success"
                                )

    @pytest.mark.asyncio
    async def test_expired_token_tracks_denied_metrics(self):
        """Test that expired token tracks denied outcome metrics."""
        from jwcrypto.jwt import JWTExpired

        auth_backend = AuthBackend()

        request = MagicMock()
        request.scope = {"type": "http"}
        request.url.path = "/api/test"
        request.headers.get.return_value = "Bearer expired_token"

        mock_kc_manager = create_mock_keycloak_manager()
        mock_kc_manager.openid.a_decode_token = AsyncMock(
            side_effect=JWTExpired("Token expired")
        )

        with patch("app.auth.keycloak_manager", mock_kc_manager):
            with patch(
                "app.utils.token_cache.get_cached_token_claims",
                new_callable=AsyncMock,
                return_value=None,
            ):
                with patch(
                    "app.utils.metrics.keycloak_token_validation_total"
                ) as mock_validation:
                    with patch(
                        "app.utils.metrics.auth_backend_requests_total"
                    ) as mock_backend:
                        with patch(
                            "app.utils.metrics.keycloak_operation_duration_seconds"
                        ) as mock_duration:
                            with pytest.raises(AuthenticationError):
                                await auth_backend.authenticate(request)

                            # Verify expired token metric
                            mock_validation.labels.assert_called_with(
                                status="expired", reason="token_expired"
                            )

                            # Verify denied outcome metric
                            mock_backend.labels.assert_called_with(
                                type="http", outcome="denied"
                            )

                            # Verify duration still tracked
                            mock_duration.labels.assert_called_with(
                                operation="validate_token"
                            )


class TestAuthBackendWebSocketSuccess:
    """Test successful WebSocket authentication scenarios."""

    @pytest.mark.asyncio
    async def test_websocket_auth_with_query_param(self, mock_user_data):
        """Test WebSocket authentication with token in query parameter."""
        auth_backend = AuthBackend()

        request = MagicMock()
        request.scope = {
            "type": "websocket",
            "query_string": b"Authorization=Bearer%20ws_valid_token",
        }

        mock_kc_manager = create_mock_keycloak_manager()
        mock_kc_manager.openid.a_decode_token = AsyncMock(
            return_value=mock_user_data
        )

        with patch("app.auth.app_settings.DEBUG_AUTH", False):
            with patch("app.auth.keycloak_manager", mock_kc_manager):
                with patch(
                    "app.utils.token_cache.get_cached_token_claims",
                    new_callable=AsyncMock,
                    return_value=None,
                ):
                    with patch(
                        "app.utils.token_cache.cache_token_claims",
                        new_callable=AsyncMock,
                    ):
                        result = await auth_backend.authenticate(request)

                        # Should return successful authentication
                        assert result is not None
                        credentials, user = result
                        assert (
                            user.username
                            == mock_user_data["preferred_username"]
                        )
                        assert user.id == mock_user_data["sub"]

                        # Token should be extracted from query param
                        mock_kc_manager.openid.a_decode_token.assert_called_once_with(
                            "ws_valid_token"
                        )

    @pytest.mark.asyncio
    async def test_websocket_auth_url_encoded_token(self, mock_user_data):
        """Test WebSocket authentication handles URL-encoded tokens."""
        auth_backend = AuthBackend()

        # Token with special characters that need URL encoding
        request = MagicMock()
        request.scope = {
            "type": "websocket",
            "query_string": b"Authorization=Bearer%20token%2Bwith%2Bplus",
        }

        mock_kc_manager = create_mock_keycloak_manager()
        mock_kc_manager.openid.a_decode_token = AsyncMock(
            return_value=mock_user_data
        )

        with patch("app.auth.app_settings.DEBUG_AUTH", False):
            with patch("app.auth.keycloak_manager", mock_kc_manager):
                with patch(
                    "app.utils.token_cache.get_cached_token_claims",
                    new_callable=AsyncMock,
                    return_value=None,
                ):
                    with patch(
                        "app.utils.token_cache.cache_token_claims",
                        new_callable=AsyncMock,
                    ):
                        result = await auth_backend.authenticate(request)

                        assert result is not None
                        # Token should be properly decoded
                        mock_kc_manager.openid.a_decode_token.assert_called_once_with(
                            "token+with+plus"
                        )


class TestAuthBackendEdgeCases:
    """Test edge cases in authentication."""

    @pytest.mark.asyncio
    async def test_missing_authorization_header(self):
        """Test authentication with missing Authorization header."""
        from keycloak.exceptions import KeycloakAuthenticationError

        auth_backend = AuthBackend()

        request = MagicMock()
        request.scope = {"type": "http"}
        request.url.path = "/api/test"
        request.headers.get.return_value = ""  # No Authorization header

        mock_kc_manager = create_mock_keycloak_manager()
        # Empty token should cause authentication error
        mock_kc_manager.openid.a_decode_token = AsyncMock(
            side_effect=KeycloakAuthenticationError("Invalid token")
        )

        with patch("app.auth.keycloak_manager", mock_kc_manager):
            with patch(
                "app.utils.token_cache.get_cached_token_claims",
                new_callable=AsyncMock,
                return_value=None,
            ):
                with pytest.raises(AuthenticationError) as exc_info:
                    await auth_backend.authenticate(request)

                assert "invalid_credentials" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_malformed_authorization_header_no_bearer(self):
        """Test authentication with malformed header (missing Bearer prefix)."""
        from keycloak.exceptions import KeycloakAuthenticationError

        auth_backend = AuthBackend()

        request = MagicMock()
        request.scope = {"type": "http"}
        request.url.path = "/api/test"
        request.headers.get.return_value = "just_token_no_bearer"

        mock_kc_manager = create_mock_keycloak_manager()
        # get_authorization_scheme_param returns empty string for malformed header
        mock_kc_manager.openid.a_decode_token = AsyncMock(
            side_effect=KeycloakAuthenticationError("Invalid token")
        )

        with patch("app.auth.keycloak_manager", mock_kc_manager):
            with patch(
                "app.utils.token_cache.get_cached_token_claims",
                new_callable=AsyncMock,
                return_value=None,
            ):
                with pytest.raises(AuthenticationError) as exc_info:
                    await auth_backend.authenticate(request)

                assert "invalid_credentials" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_websocket_missing_authorization_query_param(self):
        """Test WebSocket authentication with missing Authorization query param."""
        from keycloak.exceptions import KeycloakAuthenticationError

        auth_backend = AuthBackend()

        request = MagicMock()
        request.scope = {
            "type": "websocket",
            "query_string": b"other_param=value",  # No Authorization
        }

        mock_kc_manager = create_mock_keycloak_manager()
        mock_kc_manager.openid.a_decode_token = AsyncMock(
            side_effect=KeycloakAuthenticationError("Invalid token")
        )

        with patch("app.auth.keycloak_manager", mock_kc_manager):
            with patch(
                "app.utils.token_cache.get_cached_token_claims",
                new_callable=AsyncMock,
                return_value=None,
            ):
                with pytest.raises(AuthenticationError) as exc_info:
                    await auth_backend.authenticate(request)

                assert "invalid_credentials" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_empty_query_string_websocket(self):
        """Test WebSocket authentication with empty query string."""
        from keycloak.exceptions import KeycloakAuthenticationError

        auth_backend = AuthBackend()

        request = MagicMock()
        request.scope = {"type": "websocket", "query_string": b""}

        mock_kc_manager = create_mock_keycloak_manager()
        mock_kc_manager.openid.a_decode_token = AsyncMock(
            side_effect=KeycloakAuthenticationError("Invalid token")
        )

        with patch("app.auth.keycloak_manager", mock_kc_manager):
            with patch(
                "app.utils.token_cache.get_cached_token_claims",
                new_callable=AsyncMock,
                return_value=None,
            ):
                with pytest.raises(AuthenticationError) as exc_info:
                    await auth_backend.authenticate(request)

                assert "invalid_credentials" in exc_info.value.message


class TestAuthBackendRequestTypeDifferentiation:
    """Test that HTTP and WebSocket requests are properly differentiated."""

    @pytest.mark.asyncio
    async def test_http_request_type_in_metrics(self, mock_user_data):
        """Test that HTTP requests set request_type='http'."""
        auth_backend = AuthBackend()

        request = MagicMock()
        request.scope = {"type": "http"}
        request.url.path = "/api/test"
        request.headers.get.return_value = "Bearer token"

        mock_kc_manager = create_mock_keycloak_manager()
        mock_kc_manager.openid.a_decode_token = AsyncMock(
            return_value=mock_user_data
        )

        with patch("app.auth.keycloak_manager", mock_kc_manager):
            with patch(
                "app.utils.token_cache.get_cached_token_claims",
                new_callable=AsyncMock,
                return_value=None,
            ):
                with patch(
                    "app.utils.token_cache.cache_token_claims",
                    new_callable=AsyncMock,
                ):
                    with patch(
                        "app.utils.metrics.auth_backend_requests_total"
                    ) as mock_metric:
                        with patch(
                            "app.utils.metrics.keycloak_token_validation_total"
                        ):
                            with patch(
                                "app.utils.metrics.keycloak_operation_duration_seconds"
                            ):
                                await auth_backend.authenticate(request)

                                # Verify HTTP type
                                mock_metric.labels.assert_called_with(
                                    type="http", outcome="success"
                                )

    @pytest.mark.asyncio
    async def test_websocket_request_type_in_metrics(self, mock_user_data):
        """Test that WebSocket requests set request_type='websocket'."""
        auth_backend = AuthBackend()

        request = MagicMock()
        request.scope = {
            "type": "websocket",
            "query_string": b"Authorization=Bearer%20token",
        }

        mock_kc_manager = create_mock_keycloak_manager()
        mock_kc_manager.openid.a_decode_token = AsyncMock(
            return_value=mock_user_data
        )

        with patch("app.auth.keycloak_manager", mock_kc_manager):
            with patch(
                "app.utils.token_cache.get_cached_token_claims",
                new_callable=AsyncMock,
                return_value=None,
            ):
                with patch(
                    "app.utils.token_cache.cache_token_claims",
                    new_callable=AsyncMock,
                ):
                    with patch(
                        "app.utils.metrics.auth_backend_requests_total"
                    ) as mock_metric:
                        with patch(
                            "app.utils.metrics.keycloak_token_validation_total"
                        ):
                            with patch(
                                "app.utils.metrics.keycloak_operation_duration_seconds"
                            ):
                                await auth_backend.authenticate(request)

                                # Verify WebSocket type
                                mock_metric.labels.assert_called_with(
                                    type="websocket", outcome="success"
                                )
