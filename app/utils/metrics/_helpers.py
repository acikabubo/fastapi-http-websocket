"""
Helper functions for Prometheus metric registration.

These functions prevent duplicate registration errors during development
with --reload by retrieving existing metrics from the registry if they
already exist.
"""

from prometheus_client import REGISTRY, Counter, Gauge, Histogram


def _get_or_create_counter(
    name: str, doc: str, labels: list[str] | None = None
) -> Counter:
    """
    Get existing counter or create new one.

    Prevents duplicate registration errors during development with --reload.

    Args:
        name: Metric name.
        doc: Metric documentation.
        labels: Optional list of label names.

    Returns:
        Counter instance.
    """
    try:
        return Counter(name, doc, labels or [])
    except ValueError:
        # Metric already exists, retrieve it from registry
        return REGISTRY._names_to_collectors[name]


def _get_or_create_gauge(
    name: str, doc: str, labels: list[str] | None = None
) -> Gauge:
    """
    Get existing gauge or create new one.

    Prevents duplicate registration errors during development with --reload.

    Args:
        name: Metric name.
        doc: Metric documentation.
        labels: Optional list of label names.

    Returns:
        Gauge instance.
    """
    try:
        return Gauge(name, doc, labels or [])
    except ValueError:
        # Metric already exists, retrieve it from registry
        return REGISTRY._names_to_collectors[name]


def _get_or_create_histogram(
    name: str,
    doc: str,
    labels: list[str] | None = None,
    buckets: list[float] | tuple[float, ...] | tuple[int, ...] | None = None,
) -> Histogram:
    """
    Get existing histogram or create new one.

    Prevents duplicate registration errors during development with --reload.

    Args:
        name: Metric name.
        doc: Metric documentation.
        labels: Optional list of label names.
        buckets: Optional histogram buckets.

    Returns:
        Histogram instance.
    """
    try:
        if buckets:
            return Histogram(name, doc, labels or [], buckets=buckets)
        return Histogram(name, doc, labels or [])
    except ValueError:
        # Metric already exists, retrieve it from registry
        return REGISTRY._names_to_collectors[name]
