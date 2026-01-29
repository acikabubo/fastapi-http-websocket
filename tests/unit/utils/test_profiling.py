"""
Tests for profiling utilities.

This module tests profiling manager functionality and profiling context
management.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.utils.profiling import (
    ProfilingManager,
    get_profiling_status,
    is_profiling_enabled,
    profile_context,
)


class TestProfilingManager:
    """Tests for ProfilingManager class."""

    def test_init_with_profiling_enabled_and_scalene_available(self):
        """Test initialization when profiling is enabled and scalene is installed."""
        with (
            patch("app.utils.profiling.app_settings") as mock_settings,
            patch("app.utils.profiling.HAS_SCALENE", True),
            patch("app.utils.profiling.Path.mkdir") as mock_mkdir,
        ):
            mock_settings.PROFILING_ENABLED = True
            mock_settings.PROFILING_OUTPUT_DIR = "profiling_reports"
            mock_settings.PROFILING_INTERVAL_SECONDS = 30

            manager = ProfilingManager()

            assert manager.enabled is True
            assert manager.output_dir == Path("profiling_reports")
            assert manager.interval_seconds == 30
            mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)

    def test_init_with_profiling_disabled(self):
        """Test initialization when profiling is disabled."""
        with (
            patch("app.utils.profiling.app_settings") as mock_settings,
            patch("app.utils.profiling.HAS_SCALENE", True),
        ):
            mock_settings.PROFILING_ENABLED = False
            mock_settings.PROFILING_OUTPUT_DIR = "profiling_reports"
            mock_settings.PROFILING_INTERVAL_SECONDS = 30

            manager = ProfilingManager()

            assert manager.enabled is False

    def test_init_with_scalene_not_installed(self):
        """Test initialization when scalene is not installed."""
        with (
            patch("app.utils.profiling.app_settings") as mock_settings,
            patch("app.utils.profiling.HAS_SCALENE", False),
            patch("app.utils.profiling.logger") as mock_logger,
        ):
            mock_settings.PROFILING_ENABLED = True
            mock_settings.PROFILING_OUTPUT_DIR = "profiling_reports"
            mock_settings.PROFILING_INTERVAL_SECONDS = 30

            manager = ProfilingManager()

            # Should disable profiling if scalene not available
            assert manager.enabled is False

            # Should log warning
            mock_logger.warning.assert_called_once()
            warning_msg = mock_logger.warning.call_args[0][0]
            assert "scalene is not installed" in warning_msg

    def test_get_report_path_default(self):
        """Test report path generation with default endpoint name."""
        with (
            patch("app.utils.profiling.app_settings") as mock_settings,
            patch("app.utils.profiling.HAS_SCALENE", True),
            patch("app.utils.profiling.datetime") as mock_datetime,
        ):
            mock_settings.PROFILING_ENABLED = True
            mock_settings.PROFILING_OUTPUT_DIR = "profiling_reports"
            mock_settings.PROFILING_INTERVAL_SECONDS = 30

            # Mock datetime.now().strftime()
            mock_now = MagicMock()
            mock_now.strftime.return_value = "20250123_143000"
            mock_datetime.now.return_value = mock_now

            manager = ProfilingManager()
            report_path = manager.get_report_path()

            expected_path = (
                Path("profiling_reports")
                / "websocket_profile_20250123_143000.html"
            )
            assert report_path == expected_path

    def test_get_report_path_custom_endpoint(self):
        """Test report path generation with custom endpoint name."""
        with (
            patch("app.utils.profiling.app_settings") as mock_settings,
            patch("app.utils.profiling.HAS_SCALENE", True),
            patch("app.utils.profiling.datetime") as mock_datetime,
        ):
            mock_settings.PROFILING_ENABLED = True
            mock_settings.PROFILING_OUTPUT_DIR = "profiling_reports"
            mock_settings.PROFILING_INTERVAL_SECONDS = 30

            mock_now = MagicMock()
            mock_now.strftime.return_value = "20250123_143000"
            mock_datetime.now.return_value = mock_now

            manager = ProfilingManager()
            report_path = manager.get_report_path("custom_endpoint")

            expected_path = (
                Path("profiling_reports")
                / "custom_endpoint_profile_20250123_143000.html"
            )
            assert report_path == expected_path

    def test_start_profiling_when_enabled(self):
        """Test starting profiling when enabled."""
        with (
            patch("app.utils.profiling.app_settings") as mock_settings,
            patch("app.utils.profiling.HAS_SCALENE", True),
            patch("app.utils.profiling.logger") as mock_logger,
        ):
            mock_settings.PROFILING_ENABLED = True
            mock_settings.PROFILING_OUTPUT_DIR = "profiling_reports"
            mock_settings.PROFILING_INTERVAL_SECONDS = 30

            manager = ProfilingManager()
            manager.start_profiling()

            # Should log info message
            mock_logger.info.assert_called()
            info_msg = [call[0][0] for call in mock_logger.info.call_args_list]
            assert any("Profiling started" in msg for msg in info_msg)

    def test_start_profiling_when_disabled(self):
        """Test starting profiling when disabled (should do nothing)."""
        with (
            patch("app.utils.profiling.app_settings") as mock_settings,
            patch("app.utils.profiling.HAS_SCALENE", True),
            patch("app.utils.profiling.logger") as mock_logger,
        ):
            mock_settings.PROFILING_ENABLED = False
            mock_settings.PROFILING_OUTPUT_DIR = "profiling_reports"
            mock_settings.PROFILING_INTERVAL_SECONDS = 30

            manager = ProfilingManager()
            manager.start_profiling()

            # Should not log anything about starting
            info_calls = [
                call[0][0] for call in mock_logger.info.call_args_list
            ]
            assert not any("Profiling started" in msg for msg in info_calls)

    def test_stop_profiling_when_enabled(self):
        """Test stopping profiling when enabled."""
        with (
            patch("app.utils.profiling.app_settings") as mock_settings,
            patch("app.utils.profiling.HAS_SCALENE", True),
            patch("app.utils.profiling.logger") as mock_logger,
        ):
            mock_settings.PROFILING_ENABLED = True
            mock_settings.PROFILING_OUTPUT_DIR = "profiling_reports"
            mock_settings.PROFILING_INTERVAL_SECONDS = 30

            manager = ProfilingManager()
            manager.stop_profiling()

            # Should log info message
            mock_logger.info.assert_called()
            info_msg = [call[0][0] for call in mock_logger.info.call_args_list]
            assert any("Profiling stopped" in msg for msg in info_msg)

    def test_stop_profiling_when_disabled(self):
        """Test stopping profiling when disabled (should do nothing)."""
        with (
            patch("app.utils.profiling.app_settings") as mock_settings,
            patch("app.utils.profiling.HAS_SCALENE", True),
            patch("app.utils.profiling.logger") as mock_logger,
        ):
            mock_settings.PROFILING_ENABLED = False
            mock_settings.PROFILING_OUTPUT_DIR = "profiling_reports"
            mock_settings.PROFILING_INTERVAL_SECONDS = 30

            manager = ProfilingManager()
            manager.stop_profiling()

            # Should not log anything about stopping
            info_calls = [
                call[0][0] for call in mock_logger.info.call_args_list
            ]
            assert not any("Profiling stopped" in msg for msg in info_calls)


class TestProfileContext:
    """Tests for profile_context async context manager."""

    @pytest.mark.asyncio
    async def test_profile_context_when_enabled(self):
        """Test profile context when profiling is enabled."""
        with (
            patch("app.utils.profiling.profiling_manager") as mock_manager,
            patch("app.utils.profiling.logger") as mock_logger,
        ):
            mock_manager.enabled = True

            async with profile_context("test_operation"):
                pass

            # Should log start and finish
            assert mock_logger.debug.call_count == 2
            debug_calls = [
                call[0][0] for call in mock_logger.debug.call_args_list
            ]
            assert any(
                "Profiling started: test_operation" in msg
                for msg in debug_calls
            )
            assert any(
                "Profiling finished: test_operation" in msg
                for msg in debug_calls
            )

    @pytest.mark.asyncio
    async def test_profile_context_when_disabled(self):
        """Test profile context when profiling is disabled."""
        with (
            patch("app.utils.profiling.profiling_manager") as mock_manager,
            patch("app.utils.profiling.logger") as mock_logger,
        ):
            mock_manager.enabled = False

            async with profile_context("test_operation"):
                pass

            # Should not log anything
            mock_logger.debug.assert_not_called()

    @pytest.mark.asyncio
    async def test_profile_context_measures_duration(self):
        """Test that profile context measures operation duration."""
        import asyncio

        with (
            patch("app.utils.profiling.profiling_manager") as mock_manager,
            patch("app.utils.profiling.logger") as mock_logger,
        ):
            mock_manager.enabled = True

            async with profile_context("slow_operation"):
                await asyncio.sleep(0.1)  # 100ms delay

            # Check that duration is logged
            debug_calls = [
                call[0][0] for call in mock_logger.debug.call_args_list
            ]
            finish_msg = [msg for msg in debug_calls if "finished" in msg][0]
            # Should show duration in seconds
            assert "took" in finish_msg
            assert "s" in finish_msg


class TestGetProfilingStatus:
    """Tests for get_profiling_status function."""

    def test_get_profiling_status_enabled(self):
        """Test profiling status when enabled."""
        with (
            patch("app.utils.profiling.profiling_manager") as mock_manager,
            patch("app.utils.profiling.HAS_SCALENE", True),
        ):
            mock_manager.enabled = True
            mock_manager.output_dir = Path("profiling_reports")
            mock_manager.interval_seconds = 30

            status = get_profiling_status()

            assert status["enabled"] is True
            assert status["scalene_installed"] is True
            assert status["output_directory"] == "profiling_reports"
            assert status["interval_seconds"] == 30
            assert "python_version" in status
            assert "command" in status
            assert "view_command" in status
            assert "makefile_commands" in status

    def test_get_profiling_status_disabled(self):
        """Test profiling status when disabled."""
        with (
            patch("app.utils.profiling.profiling_manager") as mock_manager,
            patch("app.utils.profiling.HAS_SCALENE", False),
        ):
            mock_manager.enabled = False
            mock_manager.output_dir = Path("profiling_reports")
            mock_manager.interval_seconds = 30

            status = get_profiling_status()

            assert status["enabled"] is False
            assert status["scalene_installed"] is False


class TestIsProfilingEnabled:
    """Tests for is_profiling_enabled function."""

    def test_is_profiling_enabled_true(self):
        """Test is_profiling_enabled returns True when enabled."""
        with patch("app.utils.profiling.profiling_manager") as mock_manager:
            mock_manager.enabled = True

            result = is_profiling_enabled()

            assert result is True

    def test_is_profiling_enabled_false(self):
        """Test is_profiling_enabled returns False when disabled."""
        with patch("app.utils.profiling.profiling_manager") as mock_manager:
            mock_manager.enabled = False

            result = is_profiling_enabled()

            assert result is False
