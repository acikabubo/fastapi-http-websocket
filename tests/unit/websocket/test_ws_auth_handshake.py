"""
Tests for first-message WebSocket authentication handshake.

Covers on_connect (origin check + pre-auth setup), on_first_message
(token validation flow), _post_auth_setup (connection registration),
and dispatch (auth gate before message loop).
"""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from starlette.authentication import UnauthenticatedUser
from starlette.websockets import WebSocket

from app.api.ws.websocket import PackageAuthWebSocketEndpoint


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_endpoint() -> PackageAuthWebSocketEndpoint:
    """Create a bare endpoint instance without going through ASGI dispatch."""
    scope = {
        "type": "websocket",
        "headers": [],
        "query_string": b"",
        "path": "/web",
    }
    receive = AsyncMock()
    send = AsyncMock()
    endpoint = PackageAuthWebSocketEndpoint(scope, receive, send)
    endpoint.user = UnauthenticatedUser()
    return endpoint


def make_ws(
    *, headers: dict | None = None, query_params: dict | None = None
) -> MagicMock:
    """Return a mock WebSocket with sensible defaults."""
    ws = MagicMock(spec=WebSocket)
    ws.headers = headers or {}
    ws.query_params = query_params or {}
    ws.send_text = AsyncMock()
    ws.close = AsyncMock()
    ws.receive = AsyncMock()
    return ws


def _auth_frame(token: str = "Bearer valid-token") -> dict:
    return {
        "type": "websocket.receive",
        "text": json.dumps({"type": "auth", "token": token}),
    }


# ---------------------------------------------------------------------------
# on_connect
# ---------------------------------------------------------------------------


class TestOnConnect:
    @pytest.mark.asyncio
    async def test_rejects_disallowed_origin(self) -> None:
        endpoint = make_endpoint()
        ws = make_ws(headers={"origin": "https://evil.example.com"})

        with (
            patch("app.api.ws.websocket.app_settings") as mock_settings,
            patch("app.api.ws.websocket.MetricsCollector"),
        ):
            mock_settings.ALLOWED_WS_ORIGINS = ["https://allowed.example.com"]
            await endpoint.on_connect(ws)

        ws.close.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_accepts_allowed_origin(self) -> None:
        endpoint = make_endpoint()
        ws = make_ws(headers={"origin": "https://allowed.example.com"})

        with (
            patch("app.api.ws.websocket.app_settings") as mock_settings,
            patch(
                "app.api.ws.websocket.get_auth_redis_connection",
                new_callable=AsyncMock,
            ) as mock_redis,
            patch(
                "app.api.ws.websocket.WebSocketEndpoint.on_connect",
                new_callable=AsyncMock,
            ),
        ):
            mock_settings.ALLOWED_WS_ORIGINS = ["https://allowed.example.com"]
            mock_redis.return_value = MagicMock()
            await endpoint.on_connect(ws)

        ws.close.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_user_set_to_unauthenticated_after_connect(self) -> None:
        endpoint = make_endpoint()
        ws = make_ws()

        with (
            patch("app.api.ws.websocket.app_settings") as mock_settings,
            patch(
                "app.api.ws.websocket.get_auth_redis_connection",
                new_callable=AsyncMock,
            ) as mock_redis,
            patch(
                "app.api.ws.websocket.WebSocketEndpoint.on_connect",
                new_callable=AsyncMock,
            ),
        ):
            mock_settings.ALLOWED_WS_ORIGINS = ["*"]
            mock_redis.return_value = MagicMock()
            await endpoint.on_connect(ws)

        assert isinstance(endpoint.user, UnauthenticatedUser)

    @pytest.mark.asyncio
    async def test_wildcard_origin_allows_all(self) -> None:
        endpoint = make_endpoint()
        ws = make_ws(headers={"origin": "https://any.example.com"})

        with (
            patch("app.api.ws.websocket.app_settings") as mock_settings,
            patch(
                "app.api.ws.websocket.get_auth_redis_connection",
                new_callable=AsyncMock,
            ) as mock_redis,
            patch(
                "app.api.ws.websocket.WebSocketEndpoint.on_connect",
                new_callable=AsyncMock,
            ),
        ):
            mock_settings.ALLOWED_WS_ORIGINS = ["*"]
            mock_redis.return_value = MagicMock()
            await endpoint.on_connect(ws)

        ws.close.assert_not_awaited()


# ---------------------------------------------------------------------------
# on_first_message
# ---------------------------------------------------------------------------


class TestOnFirstMessage:
    @pytest.mark.asyncio
    async def test_timeout_closes_with_4002(self) -> None:
        endpoint = make_endpoint()
        ws = make_ws()
        ws.receive = AsyncMock(side_effect=asyncio.TimeoutError)

        with (
            patch("app.api.ws.websocket.MetricsCollector"),
            patch("asyncio.wait_for", side_effect=asyncio.TimeoutError),
        ):
            result = await endpoint.on_first_message(ws)

        assert result is False
        ws.close.assert_awaited_once_with(code=endpoint.WS_4002_AUTH_TIMEOUT)

    @pytest.mark.asyncio
    async def test_disconnect_during_auth_returns_false(self) -> None:
        endpoint = make_endpoint()
        ws = make_ws()
        ws.receive = AsyncMock(return_value={"type": "websocket.disconnect"})

        with patch(
            "asyncio.wait_for",
            new=AsyncMock(return_value={"type": "websocket.disconnect"}),
        ):
            result = await endpoint.on_first_message(ws)

        assert result is False
        ws.close.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_non_text_frame_closes_with_4001(self) -> None:
        endpoint = make_endpoint()
        ws = make_ws()
        binary_frame = {"type": "websocket.receive", "bytes": b"\x00\x01"}

        with (
            patch(
                "asyncio.wait_for", new=AsyncMock(return_value=binary_frame)
            ),
            patch("app.api.ws.websocket.MetricsCollector"),
        ):
            result = await endpoint.on_first_message(ws)

        assert result is False
        ws.close.assert_awaited_once_with(code=endpoint.WS_4001_UNAUTHORIZED)

    @pytest.mark.asyncio
    async def test_invalid_json_closes_with_4001(self) -> None:
        endpoint = make_endpoint()
        ws = make_ws()
        bad_frame = {"type": "websocket.receive", "text": "not-json{{{"}

        with (
            patch("asyncio.wait_for", new=AsyncMock(return_value=bad_frame)),
            patch("app.api.ws.websocket.MetricsCollector"),
        ):
            result = await endpoint.on_first_message(ws)

        assert result is False
        ws.close.assert_awaited_once_with(code=endpoint.WS_4001_UNAUTHORIZED)

    @pytest.mark.asyncio
    async def test_wrong_frame_type_closes_with_4001(self) -> None:
        endpoint = make_endpoint()
        ws = make_ws()
        wrong_type = {
            "type": "websocket.receive",
            "text": json.dumps({"type": "ping"}),
        }

        with (
            patch("asyncio.wait_for", new=AsyncMock(return_value=wrong_type)),
            patch("app.api.ws.websocket.MetricsCollector"),
        ):
            result = await endpoint.on_first_message(ws)

        assert result is False
        ws.close.assert_awaited_once_with(code=endpoint.WS_4001_UNAUTHORIZED)

    @pytest.mark.asyncio
    async def test_missing_token_closes_with_4001(self) -> None:
        endpoint = make_endpoint()
        ws = make_ws()
        no_token = {
            "type": "websocket.receive",
            "text": json.dumps({"type": "auth"}),
        }

        with (
            patch("asyncio.wait_for", new=AsyncMock(return_value=no_token)),
            patch("app.api.ws.websocket.MetricsCollector"),
        ):
            result = await endpoint.on_first_message(ws)

        assert result is False
        ws.close.assert_awaited_once_with(code=endpoint.WS_4001_UNAUTHORIZED)

    @pytest.mark.asyncio
    async def test_non_bearer_scheme_closes_with_4001(self) -> None:
        endpoint = make_endpoint()
        ws = make_ws()
        basic_auth = {
            "type": "websocket.receive",
            "text": json.dumps(
                {"type": "auth", "token": "Basic dXNlcjpwYXNz"}
            ),
        }

        with (
            patch("asyncio.wait_for", new=AsyncMock(return_value=basic_auth)),
            patch("app.api.ws.websocket.MetricsCollector"),
        ):
            result = await endpoint.on_first_message(ws)

        assert result is False
        ws.close.assert_awaited_once_with(code=endpoint.WS_4001_UNAUTHORIZED)

    @pytest.mark.asyncio
    async def test_expired_token_closes_with_4001(self) -> None:
        from jwcrypto.jwt import JWTExpired

        endpoint = make_endpoint()
        ws = make_ws()

        with (
            patch(
                "asyncio.wait_for", new=AsyncMock(return_value=_auth_frame())
            ),
            patch("app.api.ws.websocket.MetricsCollector"),
            patch("app.api.ws.websocket.keycloak_manager") as mock_kc,
        ):
            mock_kc.decode_token = AsyncMock(side_effect=JWTExpired)
            result = await endpoint.on_first_message(ws)

        assert result is False
        ws.close.assert_awaited_once_with(code=endpoint.WS_4001_UNAUTHORIZED)

    @pytest.mark.asyncio
    async def test_valid_token_calls_post_auth_setup(self) -> None:
        endpoint = make_endpoint()
        ws = make_ws()
        user_info = {
            "sub": "user-1",
            "preferred_username": "alice",
            "exp": 9999999999,
            "realm_access": {"roles": []},
        }

        with (
            patch(
                "asyncio.wait_for", new=AsyncMock(return_value=_auth_frame())
            ),
            patch("app.api.ws.websocket.MetricsCollector"),
            patch("app.api.ws.websocket.keycloak_manager") as mock_kc,
            patch.object(
                endpoint, "_post_auth_setup", new=AsyncMock(return_value=True)
            ) as mock_setup,
        ):
            mock_kc.decode_token = AsyncMock(return_value=user_info)
            result = await endpoint.on_first_message(ws)

        assert result is True
        mock_setup.assert_awaited_once_with(ws)


# ---------------------------------------------------------------------------
# _post_auth_setup
# ---------------------------------------------------------------------------


class TestPostAuthSetup:
    def _make_user(self):
        from fastapi_keycloak_rbac.models import UserModel

        return UserModel(
            sub="user-1",
            preferred_username="alice",
            exp=9999999999,
        )

    @pytest.mark.asyncio
    async def test_connection_limit_exceeded_closes_and_returns_false(
        self,
    ) -> None:
        endpoint = make_endpoint()
        endpoint.r = MagicMock()
        endpoint.user = self._make_user()
        ws = make_ws()

        with (
            patch("app.api.ws.websocket.connection_limiter") as mock_limiter,
            patch("app.api.ws.websocket.MetricsCollector"),
            patch("app.api.ws.websocket.set_log_context"),
        ):
            mock_limiter.add_connection = AsyncMock(return_value=False)
            result = await endpoint._post_auth_setup(ws)

        assert result is False
        ws.close.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_success_sends_auth_ok_and_returns_true(self) -> None:
        endpoint = make_endpoint()
        endpoint.r = MagicMock()
        endpoint.r.add_kc_user_session = AsyncMock()
        endpoint.user = self._make_user()
        ws = make_ws()

        with (
            patch("app.api.ws.websocket.connection_limiter") as mock_limiter,
            patch("app.api.ws.websocket.connection_manager"),
            patch("app.api.ws.websocket.MetricsCollector"),
            patch("app.api.ws.websocket.set_log_context"),
            patch("app.api.ws.websocket.app_settings") as mock_settings,
        ):
            mock_limiter.add_connection = AsyncMock(return_value=True)
            mock_limiter.remove_connection = AsyncMock()
            mock_settings.USER_SESSION_REDIS_KEY_PREFIX = "session:"
            result = await endpoint._post_auth_setup(ws)

        assert result is True
        ws.send_text.assert_awaited_once_with(json.dumps({"type": "auth_ok"}))
