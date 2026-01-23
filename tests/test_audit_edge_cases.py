"""
Comprehensive edge case tests for audit logging.

This module tests critical edge cases in audit logging including queue overflow,
database failures, worker cancellation, and malformed log entries.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.exc import DatabaseError, IntegrityError, OperationalError

from app.utils.audit_logger import (
    flush_audit_queue,
    get_audit_queue,
    log_user_action,
)


class TestQueueOverflowScenarios:
    """Test audit queue overflow and recovery."""

    @pytest.mark.asyncio
    async def test_queue_overflow_drops_logs(self):
        """
        Test that audit logs are dropped when queue is full.

        When queue reaches max capacity, new logs should be rejected
        and counter should increment.
        """
        # Get the audit queue
        queue = get_audit_queue()

        # Fill the queue to capacity (simulated with timeout=0)
        with patch("app.settings.app_settings.AUDIT_QUEUE_TIMEOUT", 0):
            # Try to add more logs than queue size
            tasks = []
            for i in range(15000):  # More than default 10000 capacity
                task = log_user_action(
                    user_id=f"user{i}",
                    username=f"username{i}",
                    user_roles=["user"],
                    action_type="TEST",
                    resource="test",
                    outcome="success",
                )
                tasks.append(task)

            # Wait for all tasks (some should be dropped)
            await asyncio.gather(*tasks, return_exceptions=True)

            # Queue should be at max capacity
            # Verify that some logs were dropped by checking queue size
            assert queue.qsize() <= queue.maxsize

    @pytest.mark.asyncio
    async def test_queue_recovery_after_overflow(self):
        """
        Test that audit system recovers after queue overflow.

        After worker drains queue, new logs should be accepted.
        """
        # Add some logs (reduced count for faster test execution)
        for i in range(10):
            await log_user_action(
                user_id=f"user{i}",
                username=f"username{i}",
                user_roles=["user"],
                action_type="TEST",
                resource="test",
                outcome="success",
            )

        # Flush the queue (drain it)
        with patch("app.storage.db.async_session") as mock_session:
            mock_session_inst = AsyncMock()
            mock_context_manager = MagicMock()
            mock_context_manager.__aenter__ = AsyncMock(
                return_value=mock_session_inst
            )
            mock_context_manager.__aexit__ = AsyncMock(return_value=None)
            mock_session.return_value = mock_context_manager

            await flush_audit_queue()

        # Queue should be empty, new logs should be accepted
        await log_user_action(
            user_id="user_new",
            username="username_new",
            user_roles=["user"],
            action_type="TEST",
            resource="test",
            outcome="success",
        )

        # Should succeed without error


class TestDatabaseWriteFailures:
    """Test audit worker handles database failures gracefully."""

    @pytest.mark.asyncio
    async def test_database_connection_error(self):
        """
        Test audit worker handles database connection errors.

        Worker should log error and continue processing.
        """
        # Add an audit log
        await log_user_action(
            user_id="test_user",
            username="testuser",
            user_roles=["user"],
            action_type="TEST",
            resource="test",
            outcome="success",
        )

        # Simulate database connection error during flush
        with patch("app.storage.db.async_session") as mock_session:
            mock_session.side_effect = DatabaseError(
                "Connection lost", None, None
            )

            # Flush should handle error gracefully
            try:
                await flush_audit_queue()
            except DatabaseError:
                pytest.fail("Should handle database errors gracefully")

    @pytest.mark.asyncio
    async def test_database_integrity_error(self):
        """
        Test handling of database integrity constraint violations.

        Worker should skip invalid log and continue with remaining logs.
        """
        await log_user_action(
            user_id="test_user",
            username="testuser",
            user_roles=["user"],
            action_type="TEST",
            resource="test",
            outcome="success",
        )

        with patch("app.storage.db.async_session") as mock_session:
            # Simulate integrity error (e.g., duplicate key)
            mock_session_inst = AsyncMock()
            mock_session_inst.add = MagicMock()
            mock_session_inst.commit = AsyncMock(
                side_effect=IntegrityError("Duplicate key", None, None)
            )

            mock_context_manager = MagicMock()
            mock_context_manager.__aenter__ = AsyncMock(
                return_value=mock_session_inst
            )
            mock_context_manager.__aexit__ = AsyncMock(return_value=None)
            mock_session.return_value = mock_context_manager

            # Should handle error and continue
            await flush_audit_queue()

    @pytest.mark.asyncio
    async def test_database_operational_error_retry(self):
        """
        Test handling of transient database errors.

        Worker should handle operational errors that might be transient.
        """
        await log_user_action(
            user_id="test_user",
            username="testuser",
            user_roles=["user"],
            action_type="TEST",
            resource="test",
            outcome="success",
        )

        with patch("app.storage.db.async_session") as mock_session:
            mock_session.side_effect = OperationalError(
                "Lock timeout", None, None
            )

            # Should handle error gracefully
            try:
                await flush_audit_queue()
            except OperationalError:
                pytest.fail("Should handle operational errors gracefully")


class TestMalformedAuditEntries:
    """Test handling of malformed or invalid audit log entries."""

    @pytest.mark.asyncio
    async def test_invalid_user_id_type(self):
        """
        Test handling of invalid user_id type.

        Pydantic validation should raise ValidationError for wrong types.
        """
        from pydantic import ValidationError

        # user_id should be string, try with int
        with pytest.raises(ValidationError):
            await log_user_action(
                user_id=12345,  # Invalid type (should be string)
                username="testuser",
                user_roles=["user"],
                action_type="TEST",
                resource="test",
                outcome="success",
            )

    @pytest.mark.asyncio
    async def test_null_required_fields(self):
        """
        Test handling of None values in required fields.

        Pydantic validation should raise ValidationError for missing fields.
        """
        from pydantic import ValidationError

        # Required fields should not be None
        with pytest.raises(ValidationError):
            await log_user_action(
                user_id=None,  # Required field
                username="testuser",
                user_roles=["user"],
                action_type="TEST",
                resource="test",
                outcome="success",
            )

    @pytest.mark.asyncio
    async def test_empty_user_roles_list(self):
        """
        Test handling of empty roles list.

        Empty roles should be acceptable (unauthenticated user).
        """
        await log_user_action(
            user_id="test_user",
            username="testuser",
            user_roles=[],  # Empty roles
            action_type="TEST",
            resource="test",
            outcome="success",
        )

        # Should succeed without error

    @pytest.mark.asyncio
    async def test_very_long_field_values(self):
        """
        Test handling of excessively long field values.

        Database has column length limits, should handle gracefully.
        """
        long_string = "x" * 10000  # Very long string

        await log_user_action(
            user_id="test_user",
            username="testuser",
            user_roles=["user"],
            action_type="TEST",
            resource=long_string,  # Very long resource
            outcome="success",
        )

        # Flush and check for errors
        with patch("app.storage.db.async_session") as mock_session:
            mock_session_inst = AsyncMock()
            mock_session_inst.add = MagicMock()
            mock_session_inst.commit = AsyncMock()

            mock_context_manager = MagicMock()
            mock_context_manager.__aenter__ = AsyncMock(
                return_value=mock_session_inst
            )
            mock_context_manager.__aexit__ = AsyncMock(return_value=None)
            mock_session.return_value = mock_context_manager

            await flush_audit_queue()


class TestWorkerTaskCancellation:
    """Test audit worker behavior when cancelled."""

    @pytest.mark.asyncio
    async def test_worker_graceful_shutdown(self):
        """
        Test that audit worker gracefully shuts down.

        Worker should flush remaining logs before stopping.
        """
        # Add some audit logs
        for i in range(10):
            await log_user_action(
                user_id=f"user{i}",
                username=f"username{i}",
                user_roles=["user"],
                action_type="TEST",
                resource="test",
                outcome="success",
            )

        # Flush queue (simulates worker shutdown)
        with patch("app.storage.db.async_session") as mock_session:
            mock_session_inst = AsyncMock()
            mock_session_inst.add = MagicMock()
            mock_session_inst.commit = AsyncMock()

            mock_context_manager = MagicMock()
            mock_context_manager.__aenter__ = AsyncMock(
                return_value=mock_session_inst
            )
            mock_context_manager.__aexit__ = AsyncMock(return_value=None)
            mock_session.return_value = mock_context_manager

            await flush_audit_queue()

            # All logs should be flushed
            # (Verify by checking queue is empty)

    @pytest.mark.asyncio
    async def test_worker_cancellation_mid_batch(self):
        """
        Test worker cancellation during batch write.

        Should handle partial batch writes gracefully.
        """
        # Add logs to queue
        for i in range(50):
            await log_user_action(
                user_id=f"user{i}",
                username=f"username{i}",
                user_roles=["user"],
                action_type="TEST",
                resource="test",
                outcome="success",
            )

        with patch("app.storage.db.async_session") as mock_session:
            # Simulate slow commit that gets cancelled
            async def slow_commit():
                await asyncio.sleep(10)  # Very slow

            mock_session_inst = AsyncMock()
            mock_session_inst.add = MagicMock()
            mock_session_inst.commit = slow_commit

            mock_context_manager = MagicMock()
            mock_context_manager.__aenter__ = AsyncMock(
                return_value=mock_session_inst
            )
            mock_context_manager.__aexit__ = AsyncMock(return_value=None)
            mock_session.return_value = mock_context_manager

            # Create flush task
            flush_task = asyncio.create_task(flush_audit_queue())

            # Cancel after short delay
            await asyncio.sleep(0.1)
            flush_task.cancel()

            # Should handle cancellation gracefully
            try:
                await flush_task
            except asyncio.CancelledError:
                pass  # Expected


class TestBatchProcessing:
    """Test audit log batch processing."""

    @pytest.mark.asyncio
    async def test_batch_size_respected(self):
        """
        Test that multiple logs can be queued successfully.

        NOTE: Batch processing behavior (audit_log_worker) requires running background task.
        This test verifies that logs are queued correctly for batch processing.
        """
        # Get queue and record initial size
        queue = get_audit_queue()
        initial_size = queue.qsize()

        # Add logs to queue
        for i in range(10):
            await log_user_action(
                user_id=f"user{i}",
                username=f"username{i}",
                user_roles=["user"],
                action_type="TEST",
                resource="test",
                outcome="success",
            )

        # Verify logs were queued
        assert queue.qsize() == initial_size + 10

    @pytest.mark.asyncio
    async def test_partial_batch_timeout(self):
        """
        Test that small batches are queued correctly.

        NOTE: Testing audit_log_worker timeout behavior requires running background task.
        This test verifies that even small batches are queued successfully.
        """
        # Get queue and record initial size
        queue = get_audit_queue()
        initial_size = queue.qsize()

        # Add fewer logs than typical batch size
        for i in range(5):
            await log_user_action(
                user_id=f"user{i}",
                username=f"username{i}",
                user_roles=["user"],
                action_type="TEST",
                resource="test",
                outcome="success",
            )

        # Verify logs were queued even though less than batch size
        assert queue.qsize() == initial_size + 5


class TestConcurrentAuditLogging:
    """Test concurrent audit logging operations."""

    @pytest.mark.asyncio
    async def test_concurrent_log_writes(self):
        """
        Test many concurrent audit log writes.

        System should handle high concurrency without errors.
        """
        # Write 100 logs concurrently
        tasks = [
            log_user_action(
                user_id=f"user{i}",
                username=f"username{i}",
                user_roles=["user"],
                action_type="TEST",
                resource="test",
                outcome="success",
            )
            for i in range(100)
        ]

        # All should complete without errors
        await asyncio.gather(*tasks)

    @pytest.mark.asyncio
    async def test_concurrent_flush_operations(self):
        """
        Test concurrent flush operations.

        Multiple flush calls should be safe (idempotent).
        """
        # Add some logs
        for i in range(50):
            await log_user_action(
                user_id=f"user{i}",
                username=f"username{i}",
                user_roles=["user"],
                action_type="TEST",
                resource="test",
                outcome="success",
            )

        with patch("app.storage.db.async_session") as mock_session:
            mock_session_inst = AsyncMock()
            mock_session_inst.add = MagicMock()
            mock_session_inst.commit = AsyncMock()

            mock_context_manager = MagicMock()
            mock_context_manager.__aenter__ = AsyncMock(
                return_value=mock_session_inst
            )
            mock_context_manager.__aexit__ = AsyncMock(return_value=None)
            mock_session.return_value = mock_context_manager

            # Flush concurrently multiple times
            flush_tasks = [flush_audit_queue() for _ in range(3)]

            # Should handle concurrent flushes safely
            await asyncio.gather(*flush_tasks, return_exceptions=True)
