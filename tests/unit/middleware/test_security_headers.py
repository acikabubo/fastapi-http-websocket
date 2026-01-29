"""
Tests for security headers middleware.

This module tests the SecurityHeadersMiddleware to ensure all security
headers are properly set on HTTP responses.
"""

import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient

from app.middlewares.security_headers import SecurityHeadersMiddleware


@pytest.fixture
def app():
    """Create a minimal FastAPI app with security headers middleware."""
    app = FastAPI()
    app.add_middleware(SecurityHeadersMiddleware)

    @app.get("/test")
    def test_endpoint():
        return {"message": "test"}

    return app


@pytest.fixture
def client(app):
    """Create a test client for the app."""
    return TestClient(app)


class TestSecurityHeaders:
    """Test that security headers are correctly set on responses."""

    def test_x_frame_options_header(self, client):
        """Test that X-Frame-Options header is set to DENY."""
        response = client.get("/test")
        assert response.headers["X-Frame-Options"] == "DENY"

    def test_x_content_type_options_header(self, client):
        """Test that X-Content-Type-Options header is set to nosniff."""
        response = client.get("/test")
        assert response.headers["X-Content-Type-Options"] == "nosniff"

    def test_x_xss_protection_header(self, client):
        """Test that X-XSS-Protection header is set."""
        response = client.get("/test")
        assert response.headers["X-XSS-Protection"] == "1; mode=block"

    def test_strict_transport_security_header(self, client):
        """Test that Strict-Transport-Security header is set."""
        response = client.get("/test")
        assert response.headers["Strict-Transport-Security"] == (
            "max-age=31536000; includeSubDomains"
        )

    def test_referrer_policy_header(self, client):
        """Test that Referrer-Policy header is set."""
        response = client.get("/test")
        assert (
            response.headers["Referrer-Policy"]
            == "strict-origin-when-cross-origin"
        )

    def test_permissions_policy_header(self, client):
        """Test that Permissions-Policy header is set."""
        response = client.get("/test")
        assert response.headers["Permissions-Policy"] == (
            "geolocation=(), microphone=(), camera=()"
        )

    def test_content_security_policy_header_exists(self, client):
        """Test that Content-Security-Policy header is present."""
        response = client.get("/test")
        assert "Content-Security-Policy" in response.headers

    def test_csp_default_src_directive(self, client):
        """Test that CSP default-src directive is set to 'self'."""
        response = client.get("/test")
        csp = response.headers["Content-Security-Policy"]
        assert "default-src 'self'" in csp

    def test_csp_script_src_directive(self, client):
        """Test that CSP script-src directive is set to 'self' only."""
        response = client.get("/test")
        csp = response.headers["Content-Security-Policy"]
        assert "script-src 'self'" in csp

    def test_csp_style_src_directive(self, client):
        """Test that CSP style-src allows inline styles for API docs."""
        response = client.get("/test")
        csp = response.headers["Content-Security-Policy"]
        assert "style-src 'self' 'unsafe-inline'" in csp

    def test_csp_img_src_directive(self, client):
        """Test that CSP img-src allows self and data URIs."""
        response = client.get("/test")
        csp = response.headers["Content-Security-Policy"]
        assert "img-src 'self' data:" in csp

    def test_csp_font_src_directive(self, client):
        """Test that CSP font-src is set to 'self' only."""
        response = client.get("/test")
        csp = response.headers["Content-Security-Policy"]
        assert "font-src 'self'" in csp

    def test_csp_connect_src_directive(self, client):
        """Test that CSP connect-src allows WebSocket connections."""
        response = client.get("/test")
        csp = response.headers["Content-Security-Policy"]
        assert "connect-src 'self' ws: wss:" in csp

    def test_csp_frame_ancestors_directive(self, client):
        """Test that CSP frame-ancestors prevents framing."""
        response = client.get("/test")
        csp = response.headers["Content-Security-Policy"]
        assert "frame-ancestors 'none'" in csp

    def test_csp_base_uri_directive(self, client):
        """Test that CSP base-uri is restricted to same origin."""
        response = client.get("/test")
        csp = response.headers["Content-Security-Policy"]
        assert "base-uri 'self'" in csp

    def test_csp_form_action_directive(self, client):
        """Test that CSP form-action is restricted to same origin."""
        response = client.get("/test")
        csp = response.headers["Content-Security-Policy"]
        assert "form-action 'self'" in csp

    def test_csp_upgrade_insecure_requests(self, client):
        """Test that CSP includes upgrade-insecure-requests directive."""
        response = client.get("/test")
        csp = response.headers["Content-Security-Policy"]
        assert "upgrade-insecure-requests" in csp

    def test_all_security_headers_present(self, client):
        """Test that all expected security headers are present."""
        response = client.get("/test")

        expected_headers = [
            "X-Frame-Options",
            "X-Content-Type-Options",
            "X-XSS-Protection",
            "Strict-Transport-Security",
            "Referrer-Policy",
            "Permissions-Policy",
            "Content-Security-Policy",
        ]

        for header in expected_headers:
            assert header in response.headers, (
                f"Missing security header: {header}"
            )

    def test_security_headers_on_different_endpoints(self, client):
        """Test that security headers are set on different endpoints."""
        # Since /test is defined in the fixture, test it
        response = client.get("/test")
        assert "Content-Security-Policy" in response.headers

        # Test 404 response also has headers
        response = client.get("/nonexistent")
        assert "Content-Security-Policy" in response.headers

    def test_csp_prevents_inline_scripts(self, client):
        """Test that CSP policy disallows inline scripts."""
        response = client.get("/test")
        csp = response.headers["Content-Security-Policy"]

        # Ensure 'unsafe-inline' is NOT in script-src
        # (it is allowed in style-src for API docs, but not in script-src)
        script_src_part = [
            part for part in csp.split(";") if "script-src" in part
        ][0]
        assert "'unsafe-inline'" not in script_src_part

    def test_csp_format_is_valid(self, client):
        """Test that CSP header has valid format with semicolons."""
        response = client.get("/test")
        csp = response.headers["Content-Security-Policy"]

        # CSP directives should be separated by semicolons
        directives = csp.split(";")
        assert len(directives) > 5, "CSP should have multiple directives"

        # Each directive should have a name and value
        for directive in directives:
            directive = directive.strip()
            if directive:  # Skip empty strings
                assert (
                    " " in directive
                    or directive == "upgrade-insecure-requests"
                ), f"Invalid directive format: {directive}"
