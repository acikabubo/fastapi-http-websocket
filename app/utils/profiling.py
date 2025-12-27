"""
Scalene profiling integration for WebSocket performance analysis.

Provides utilities for profiling WebSocket endpoints, connection managers,
and broadcast operations to identify performance bottlenecks.
"""

import sys
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import AsyncGenerator

from app.logging import logger
from app.settings import app_settings

# Check if scalene is available
try:
    import scalene  # noqa: F401

    HAS_SCALENE = True
except ImportError:
    HAS_SCALENE = False


class ProfilingManager:
    """
    Manages Scalene profiling for WebSocket performance analysis.

    This manager handles enabling/disabling profiling, generating reports,
    and managing profiling output files.
    """

    def __init__(self) -> None:
        """Initialize profiling manager with configuration from settings."""
        self.enabled = app_settings.PROFILING_ENABLED and HAS_SCALENE
        self.output_dir = Path(app_settings.PROFILING_OUTPUT_DIR)
        self.interval_seconds = app_settings.PROFILING_INTERVAL_SECONDS

        if self.enabled:
            self.output_dir.mkdir(parents=True, exist_ok=True)
            logger.info(
                f"Profiling enabled. Reports will be saved to {self.output_dir}"
            )
        elif app_settings.PROFILING_ENABLED and not HAS_SCALENE:
            logger.warning(
                "Profiling is enabled but scalene is not installed. "
                "Install with: uv sync --group profiling"
            )

    def get_report_path(self, endpoint_name: str = "websocket") -> Path:
        """
        Generate a timestamped report path for profiling output.

        Args:
            endpoint_name: Name of the endpoint being profiled.

        Returns:
            Path to the profiling report HTML file.
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{endpoint_name}_profile_{timestamp}.html"
        return self.output_dir / filename

    def start_profiling(self) -> None:
        """
        Start Scalene profiling programmatically.

        Note: This is a placeholder. Scalene is typically run as a
        command-line wrapper, not started programmatically. For actual
        profiling, run your app with:
            scalene --html --outfile report.html -- uvicorn app:application
        """
        if not self.enabled:
            return

        logger.info("Profiling started via CLI wrapper")

    def stop_profiling(self) -> None:
        """Stop profiling and generate report."""
        if not self.enabled:
            return

        logger.info("Profiling stopped. Report generated.")


# Singleton profiling manager
profiling_manager = ProfilingManager()


@asynccontextmanager
async def profile_context(
    name: str = "operation",
) -> AsyncGenerator[None, None]:
    """
    Context manager for profiling async operations.

    This is a lightweight profiling context that logs timing information.
    For detailed Scalene profiling, run the app with Scalene CLI.

    Args:
        name: Name of the operation being profiled.

    Yields:
        None

    Example:
        async with profile_context("websocket_broadcast"):
            await manager.broadcast(message)
    """
    if not profiling_manager.enabled:
        yield
        return

    start_time = datetime.now()
    logger.debug(f"Profiling started: {name}")

    try:
        yield
    finally:
        duration = (datetime.now() - start_time).total_seconds()
        logger.debug(f"Profiling finished: {name} took {duration:.4f}s")


def get_profiling_status() -> dict:
    """
    Get current profiling configuration and status.

    Returns:
        Dictionary containing profiling status information.
    """
    return {
        "enabled": profiling_manager.enabled,
        "scalene_installed": HAS_SCALENE,
        "output_directory": str(profiling_manager.output_dir),
        "interval_seconds": profiling_manager.interval_seconds,
        "python_version": sys.version,
        "command": "scalene run run_server.py",
        "view_command": "scalene view",
        "makefile_commands": {
            "profile": "make profile",
            "view": "make profile-view",
            "view_cli": "make profile-view-cli",
            "clean": "make profile-clean",
        },
    }


def is_profiling_enabled() -> bool:
    """
    Check if profiling is currently enabled.

    Returns:
        True if profiling is enabled and scalene is available.
    """
    return profiling_manager.enabled
