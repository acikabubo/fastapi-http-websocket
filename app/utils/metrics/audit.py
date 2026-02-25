"""
Prometheus metrics for audit logging monitoring.

This module defines metrics for tracking audit log creation, queue status,
batch processing, and dropped logs.
"""

from fastapi_telemetry import (
    get_or_create_counter,
    get_or_create_gauge,
    get_or_create_histogram,
)

# Audit Logging Metrics
audit_logs_total = get_or_create_counter(
    "audit_logs_total",
    "Total audit log entries created",
    ["outcome"],  # success, error, permission_denied
)

audit_log_creation_duration_seconds = get_or_create_histogram(
    "audit_log_creation_duration_seconds",
    "Audit log creation duration in seconds",
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5),
)

audit_log_errors_total = get_or_create_counter(
    "audit_log_errors_total",
    "Total audit log creation errors",
    ["error_type"],
)

audit_queue_size = get_or_create_gauge(
    "audit_queue_size",
    "Number of audit logs waiting to be written to database",
    [],
)

audit_logs_written_total = get_or_create_counter(
    "audit_logs_written_total",
    "Total number of audit logs written to database",
    [],
)

audit_logs_dropped_total = get_or_create_counter(
    "audit_logs_dropped_total",
    "Total number of audit logs dropped due to queue full",
    [],
)

audit_batch_size = get_or_create_histogram(
    "audit_batch_size",
    "Size of audit log batches written to database",
    buckets=(1, 10, 25, 50, 100, 250, 500),
)

__all__ = [
    "audit_logs_total",
    "audit_log_creation_duration_seconds",
    "audit_log_errors_total",
    "audit_queue_size",
    "audit_logs_written_total",
    "audit_logs_dropped_total",
    "audit_batch_size",
]
