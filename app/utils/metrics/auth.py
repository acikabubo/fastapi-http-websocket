"""
Prometheus metrics for authentication and authorization monitoring.

This module defines metrics for tracking authentication attempts,
token validations, Keycloak operations, and token caching.
"""

from fastapi_telemetry import (
    get_or_create_counter,
    get_or_create_histogram,
)

# Authentication Metrics
auth_attempts_total = get_or_create_counter(
    "auth_attempts_total",
    "Total authentication attempts",
    ["status"],  # success, failure, expired
)

auth_token_validations_total = get_or_create_counter(
    "auth_token_validations_total",
    "Total token validation attempts",
    ["status"],  # valid, invalid, expired
)

# Keycloak Authentication Metrics
keycloak_auth_attempts_total = get_or_create_counter(
    "keycloak_auth_attempts_total",
    "Total Keycloak authentication attempts",
    [
        "status",
        "method",
    ],  # status: success/failure/error, method: token/password
)

keycloak_token_validation_total = get_or_create_counter(
    "keycloak_token_validation_total",
    "Total JWT token validation attempts",
    [
        "status",
        "reason",
    ],  # status: valid/invalid/expired/error, reason: expired/malformed/etc
)

keycloak_operation_duration_seconds = get_or_create_histogram(
    "keycloak_operation_duration_seconds",
    "Keycloak operation duration in seconds",
    ["operation"],  # operation: login/validate_token/refresh_token
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
)

auth_backend_requests_total = get_or_create_counter(
    "auth_backend_requests_total",
    "Total authentication backend requests",
    # Labels: type (http/websocket), outcome (success/error/denied)
    ["type", "outcome"],
)

# Token Cache Metrics
token_cache_hits_total = get_or_create_counter(
    "token_cache_hits_total",
    "Total JWT token cache hits",
)

token_cache_misses_total = get_or_create_counter(
    "token_cache_misses_total",
    "Total JWT token cache misses",
)

__all__ = [
    "auth_attempts_total",
    "auth_token_validations_total",
    "keycloak_auth_attempts_total",
    "keycloak_token_validation_total",
    "keycloak_operation_duration_seconds",
    "auth_backend_requests_total",
    "token_cache_hits_total",
    "token_cache_misses_total",
]
