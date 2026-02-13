"""Tests for exception self-conversion methods."""

from uuid import uuid4

from app.api.ws.constants import PkgID, RSPCode
from app.exceptions import (
    AppException,
    AuthenticationError,
    AuthorizationError,
    ConflictError,
    DatabaseError,
    NotFoundError,
    RateLimitError,
    RedisError,
    ValidationError,
)
from app.schemas.errors import (
    ErrorCode,
    HTTPErrorResponse,
    WebSocketErrorResponse,
)


class TestHTTPConversion:
    """Test exception to_http_response() method."""

    def test_validation_error_to_http(self):
        """Test ValidationError converts to HTTP response."""
        ex = ValidationError("Invalid input")
        response = ex.to_http_response()

        assert isinstance(response, HTTPErrorResponse)
        assert response.error.code == ErrorCode.VALIDATION_ERROR
        assert response.error.msg == "Invalid input"
        assert response.error.details is None

    def test_not_found_error_to_http(self):
        """Test NotFoundError converts to HTTP response."""
        ex = NotFoundError("Author not found")
        response = ex.to_http_response()

        assert isinstance(response, HTTPErrorResponse)
        assert response.error.code == ErrorCode.NOT_FOUND
        assert response.error.msg == "Author not found"
        assert response.error.details is None

    def test_database_error_to_http(self):
        """Test DatabaseError converts to HTTP response."""
        ex = DatabaseError("Connection failed")
        response = ex.to_http_response()

        assert response.error.code == ErrorCode.DATABASE_ERROR
        assert response.error.msg == "Connection failed"

    def test_authentication_error_to_http(self):
        """Test AuthenticationError converts to HTTP response."""
        ex = AuthenticationError("Token expired")
        response = ex.to_http_response()

        assert response.error.code == ErrorCode.AUTHENTICATION_FAILED
        assert response.error.msg == "Token expired"

    def test_authorization_error_to_http(self):
        """Test AuthorizationError converts to HTTP response."""
        ex = AuthorizationError("Missing permissions")
        response = ex.to_http_response()

        assert response.error.code == ErrorCode.PERMISSION_DENIED
        assert response.error.msg == "Missing permissions"

    def test_rate_limit_error_to_http(self):
        """Test RateLimitError converts to HTTP response."""
        ex = RateLimitError("Too many requests")
        response = ex.to_http_response()

        assert response.error.code == ErrorCode.RATE_LIMIT_EXCEEDED
        assert response.error.msg == "Too many requests"

    def test_redis_error_to_http(self):
        """Test RedisError converts to HTTP response."""
        ex = RedisError("Cache unavailable")
        response = ex.to_http_response()

        assert response.error.code == ErrorCode.REDIS_ERROR
        assert response.error.msg == "Cache unavailable"

    def test_conflict_error_to_http(self):
        """Test ConflictError converts to HTTP response."""
        ex = ConflictError("Duplicate entry")
        response = ex.to_http_response()

        assert response.error.code == ErrorCode.CONFLICT
        assert response.error.msg == "Duplicate entry"

    def test_to_http_with_details(self):
        """Test conversion with optional details."""
        ex = ValidationError("Name too short")
        response = ex.to_http_response(
            details={"field": "name", "min_length": 3}
        )

        assert response.error.code == ErrorCode.VALIDATION_ERROR
        assert response.error.msg == "Name too short"
        assert response.error.details == {"field": "name", "min_length": 3}

    def test_base_exception_to_http(self):
        """Test base AppException converts with default error code."""
        ex = AppException("Generic error")
        response = ex.to_http_response()

        assert response.error.code == ErrorCode.INTERNAL_ERROR
        assert response.error.msg == "Generic error"


class TestWebSocketConversion:
    """Test exception to_ws_response() method."""

    def test_validation_error_to_ws(self):
        """Test ValidationError converts to WebSocket response."""
        ex = ValidationError("Invalid data")
        pkg_id = PkgID.GET_AUTHORS
        req_id = str(uuid4())

        response = ex.to_ws_response(pkg_id, req_id)

        assert isinstance(response, WebSocketErrorResponse)
        assert response.pkg_id == pkg_id
        assert str(response.req_id) == req_id
        assert response.status_code == RSPCode.INVALID_DATA
        assert response.data["code"] == ErrorCode.VALIDATION_ERROR
        assert response.data["msg"] == "Invalid data"
        assert response.data["details"] is None

    def test_not_found_error_to_ws(self):
        """Test NotFoundError converts to WebSocket response."""
        ex = NotFoundError("Resource not found")
        pkg_id = PkgID.CREATE_AUTHOR
        req_id = str(uuid4())

        response = ex.to_ws_response(pkg_id, req_id)

        assert response.pkg_id == pkg_id
        assert str(response.req_id) == req_id
        assert response.status_code == RSPCode.ERROR
        assert response.data["code"] == ErrorCode.NOT_FOUND
        assert response.data["msg"] == "Resource not found"

    def test_authentication_error_to_ws(self):
        """Test AuthenticationError converts to WebSocket response."""
        ex = AuthenticationError("Token expired")
        pkg_id = PkgID.GET_AUTHORS
        req_id = str(uuid4())

        response = ex.to_ws_response(pkg_id, req_id)

        assert response.status_code == RSPCode.PERMISSION_DENIED
        assert response.data["code"] == ErrorCode.AUTHENTICATION_FAILED
        assert response.data["msg"] == "Token expired"

    def test_authorization_error_to_ws(self):
        """Test AuthorizationError converts to WebSocket response."""
        ex = AuthorizationError("Insufficient privileges")
        pkg_id = PkgID.CREATE_AUTHOR
        req_id = str(uuid4())

        response = ex.to_ws_response(pkg_id, req_id)

        assert response.status_code == RSPCode.PERMISSION_DENIED
        assert response.data["code"] == ErrorCode.PERMISSION_DENIED
        assert response.data["msg"] == "Insufficient privileges"

    def test_conflict_error_to_ws(self):
        """Test ConflictError converts to WebSocket response."""
        ex = ConflictError("Duplicate name")
        pkg_id = PkgID.GET_PAGINATED_AUTHORS
        req_id = str(uuid4())

        response = ex.to_ws_response(pkg_id, req_id)

        assert response.status_code == RSPCode.INVALID_DATA
        assert response.data["code"] == ErrorCode.CONFLICT
        assert response.data["msg"] == "Duplicate name"

    def test_to_ws_with_details(self):
        """Test WebSocket conversion with optional details."""
        ex = ValidationError("Validation failed")
        pkg_id = PkgID.GET_AUTHORS
        req_id = str(uuid4())
        details = {"fields": ["name", "email"], "reason": "required"}

        response = ex.to_ws_response(pkg_id, req_id, details=details)

        assert response.data["code"] == ErrorCode.VALIDATION_ERROR
        assert response.data["msg"] == "Validation failed"
        assert response.data["details"] == details

    def test_base_exception_to_ws(self):
        """Test base AppException converts with default values."""
        ex = AppException("Generic error")
        pkg_id = PkgID.UNREGISTERED_HANDLER
        req_id = str(uuid4())

        response = ex.to_ws_response(pkg_id, req_id)

        assert response.status_code == RSPCode.ERROR
        assert response.data["code"] == ErrorCode.INTERNAL_ERROR
        assert response.data["msg"] == "Generic error"


class TestErrorCodeMapping:
    """Test error_code class attribute on all exceptions."""

    def test_all_exceptions_have_error_code(self):
        """Verify all exception types have error_code defined."""
        assert AppException.error_code == ErrorCode.INTERNAL_ERROR
        assert ValidationError.error_code == ErrorCode.VALIDATION_ERROR
        assert NotFoundError.error_code == ErrorCode.NOT_FOUND
        assert DatabaseError.error_code == ErrorCode.DATABASE_ERROR
        assert (
            AuthenticationError.error_code == ErrorCode.AUTHENTICATION_FAILED
        )
        assert AuthorizationError.error_code == ErrorCode.PERMISSION_DENIED
        assert RateLimitError.error_code == ErrorCode.RATE_LIMIT_EXCEEDED
        assert RedisError.error_code == ErrorCode.REDIS_ERROR
        assert ConflictError.error_code == ErrorCode.CONFLICT

    def test_error_code_consistency_with_http_status(self):
        """Verify error codes are consistent with HTTP status codes."""
        # 4xx errors
        assert ValidationError.http_status == 400
        assert ValidationError.error_code == ErrorCode.VALIDATION_ERROR

        assert AuthenticationError.http_status == 401
        assert (
            AuthenticationError.error_code == ErrorCode.AUTHENTICATION_FAILED
        )

        assert AuthorizationError.http_status == 403
        assert AuthorizationError.error_code == ErrorCode.PERMISSION_DENIED

        assert NotFoundError.http_status == 404
        assert NotFoundError.error_code == ErrorCode.NOT_FOUND

        assert ConflictError.http_status == 409
        assert ConflictError.error_code == ErrorCode.CONFLICT

        assert RateLimitError.http_status == 429
        assert RateLimitError.error_code == ErrorCode.RATE_LIMIT_EXCEEDED

        # 5xx errors
        assert DatabaseError.http_status == 500
        assert DatabaseError.error_code == ErrorCode.DATABASE_ERROR

        assert RedisError.http_status == 500
        assert RedisError.error_code == ErrorCode.REDIS_ERROR

    def test_error_code_consistency_with_ws_status(self):
        """Verify error codes are consistent with WebSocket status codes."""
        assert ValidationError.ws_status == RSPCode.INVALID_DATA
        assert ConflictError.ws_status == RSPCode.INVALID_DATA

        assert AuthenticationError.ws_status == RSPCode.PERMISSION_DENIED
        assert AuthorizationError.ws_status == RSPCode.PERMISSION_DENIED

        assert NotFoundError.ws_status == RSPCode.ERROR
        assert DatabaseError.ws_status == RSPCode.ERROR
        assert RedisError.ws_status == RSPCode.ERROR
        assert RateLimitError.ws_status == RSPCode.ERROR


class TestExceptionAttributes:
    """Test exception attributes are properly set."""

    def test_exception_message_attribute(self):
        """Verify exception message is stored correctly."""
        message = "Test error message"
        ex = ValidationError(message)

        assert ex.message == message
        assert str(ex) == message

    def test_exception_http_status_attribute(self):
        """Verify HTTP status codes are set correctly."""
        assert ValidationError("test").http_status == 400
        assert NotFoundError("test").http_status == 404
        assert AuthenticationError("test").http_status == 401
        assert AuthorizationError("test").http_status == 403
        assert ConflictError("test").http_status == 409
        assert RateLimitError("test").http_status == 429
        assert DatabaseError("test").http_status == 500
        assert RedisError("test").http_status == 500

    def test_exception_ws_status_attribute(self):
        """Verify WebSocket status codes are set correctly."""
        assert ValidationError("test").ws_status == RSPCode.INVALID_DATA
        assert NotFoundError("test").ws_status == RSPCode.ERROR
        assert (
            AuthenticationError("test").ws_status == RSPCode.PERMISSION_DENIED
        )
        assert (
            AuthorizationError("test").ws_status == RSPCode.PERMISSION_DENIED
        )
        assert ConflictError("test").ws_status == RSPCode.INVALID_DATA
        assert RateLimitError("test").ws_status == RSPCode.ERROR
        assert DatabaseError("test").ws_status == RSPCode.ERROR
        assert RedisError("test").ws_status == RSPCode.ERROR
