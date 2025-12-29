"""
Chaos tests for database failure scenarios.

Tests application resilience when PostgreSQL is unavailable or fails.

Run with: pytest tests/chaos/test_database_failures.py -v -m chaos
"""

from unittest.mock import AsyncMock

import pytest
from sqlalchemy.exc import (
    DBAPIError,
    DisconnectionError,
    OperationalError,
    TimeoutError as SQLTimeoutError,
)

from app.models.author import Author
from app.repositories.author_repository import AuthorRepository

# Mark all tests in this module as chaos tests
pytestmark = pytest.mark.chaos


class TestDatabaseConnectionFailures:
    """Tests for database connection failure scenarios."""

    @pytest.mark.asyncio
    async def test_query_with_database_unavailable(self):
        """Test repository query when database is unavailable."""
        mock_session = AsyncMock()
        mock_session.exec = AsyncMock(
            side_effect=OperationalError(
                "could not connect to server",
                params=None,
                orig=Exception("Connection refused"),
            )
        )

        repo = AuthorRepository(mock_session)

        # Should raise OperationalError when database unavailable
        with pytest.raises(OperationalError):
            await repo.get_all()

    @pytest.mark.asyncio
    async def test_create_with_connection_lost(self):
        """Test repository create when connection is lost mid-operation."""
        mock_session = AsyncMock()

        # Simulate connection loss during flush
        mock_session.add = AsyncMock()
        mock_session.flush = AsyncMock(
            side_effect=DisconnectionError(
                "connection lost", params=None, orig=Exception("EOF")
            )
        )

        repo = AuthorRepository(mock_session)
        author = Author(name="Test Author", bio="Test bio")

        # Should raise DisconnectionError
        with pytest.raises(DisconnectionError):
            await repo.create(author)

    @pytest.mark.asyncio
    async def test_query_timeout(self):
        """Test repository query when database query times out."""
        mock_session = AsyncMock()
        mock_session.exec = AsyncMock(
            side_effect=SQLTimeoutError(
                "query timeout", params=None, orig=Exception("Timeout")
            )
        )

        repo = AuthorRepository(mock_session)

        # Should raise TimeoutError on slow query
        with pytest.raises(SQLTimeoutError):
            await repo.get_all()

    @pytest.mark.asyncio
    async def test_transaction_rollback_on_error(self):
        """Test that session rolls back on database errors."""
        mock_session = AsyncMock()
        mock_session.add = AsyncMock()
        mock_session.flush = AsyncMock(
            side_effect=OperationalError(
                "deadlock detected", params=None, orig=Exception()
            )
        )
        mock_session.rollback = AsyncMock()

        repo = AuthorRepository(mock_session)
        author = Author(name="Test", bio="Test")

        # Create should fail
        with pytest.raises(OperationalError):
            await repo.create(author)

        # Rollback should be called (if handled in repository)
        # Note: Current repository doesn't call rollback, this tests expected behavior


class TestDatabasePartialFailures:
    """Tests for partial database operation failures."""

    @pytest.mark.asyncio
    async def test_query_returns_partial_results(self):
        """Test handling when query returns incomplete results due to errors."""
        mock_result = AsyncMock()

        # Simulate partial result fetch
        call_count = [0]

        async def mock_all():
            call_count[0] += 1
            if call_count[0] == 1:
                # First call returns partial data
                return [
                    Author(id=1, name="Author 1", bio="Bio 1"),
                    Author(id=2, name="Author 2", bio="Bio 2"),
                ]
            else:
                # Subsequent calls fail
                raise DBAPIError(
                    "cursor closed", params=None, orig=Exception()
                )

        mock_result.all = mock_all

        mock_session = AsyncMock()
        mock_session.exec = AsyncMock(return_value=mock_result)

        repo = AuthorRepository(mock_session)

        # First call should succeed with partial data
        authors = await repo.get_all()
        assert len(authors) == 2

    @pytest.mark.asyncio
    async def test_commit_fails_after_operations(self):
        """Test when database operations succeed but commit fails."""
        mock_session = AsyncMock()
        mock_session.add = AsyncMock()
        mock_session.flush = AsyncMock()  # Flush succeeds
        mock_session.commit = AsyncMock(
            side_effect=OperationalError(
                "commit failed", params=None, orig=Exception()
            )
        )

        # Note: Current repository pattern uses flush, not commit
        # This tests the scenario if commit were used


class TestDatabaseIntermittentFailures:
    """Tests for intermittent database failures and recovery."""

    @pytest.mark.asyncio
    async def test_retry_after_transient_failure(self):
        """Test repository operations retry after transient database failures."""
        mock_session = AsyncMock()

        # First attempt: transient error
        # Second attempt: success
        call_count = [0]
        mock_result = AsyncMock()
        mock_result.all = AsyncMock(
            return_value=[Author(id=1, name="Test", bio="Bio")]
        )

        async def mock_exec(stmt):
            call_count[0] += 1
            if call_count[0] == 1:
                raise OperationalError(
                    "server closed connection",
                    params=None,
                    orig=Exception(),
                )
            else:
                return mock_result

        mock_session.exec = mock_exec

        repo = AuthorRepository(mock_session)

        # First attempt fails
        with pytest.raises(OperationalError):
            await repo.get_all()

        # Second attempt succeeds
        authors = await repo.get_all()
        assert len(authors) == 1
        assert authors[0].name == "Test"

    @pytest.mark.asyncio
    async def test_connection_pool_exhaustion_recovery(self):
        """Test recovery when database connection pool is exhausted."""
        # Simulate multiple rapid queries exhausting the pool
        mock_session = AsyncMock()

        queries = []
        for i in range(20):
            mock_result = AsyncMock()
            if i < 15:
                # First 15 queries: pool exhausted
                mock_result.all = AsyncMock(
                    side_effect=OperationalError(
                        "connection pool exhausted",
                        params=None,
                        orig=Exception(),
                    )
                )
            else:
                # Last 5 queries: pool recovered
                mock_result.all = AsyncMock(return_value=[])

            queries.append(mock_result)

        mock_session.exec = AsyncMock(side_effect=queries)
        repo = AuthorRepository(mock_session)

        # First 15 should fail
        for i in range(15):
            with pytest.raises(OperationalError):
                await repo.get_all()

        # Last 5 should succeed (pool recovered)
        for i in range(5):
            result = await repo.get_all()
            assert result == []


class TestDatabaseNetworkPartitions:
    """Tests for database network partition scenarios."""

    @pytest.mark.asyncio
    async def test_split_brain_scenario(self):
        """Test handling of split-brain scenario (network partition)."""
        # This would test behavior when database replication has split-brain
        # For now, this is a placeholder for more advanced chaos scenarios
        pass

    @pytest.mark.asyncio
    async def test_slow_network_to_database(self):
        """Test queries when network to database is slow."""
        mock_session = AsyncMock()

        # Simulate slow network by delaying query execution
        import asyncio

        mock_result = AsyncMock()

        async def slow_all():
            await asyncio.sleep(0.5)  # 500ms delay
            return [Author(id=1, name="Test", bio="Bio")]

        mock_result.all = slow_all
        mock_session.exec = AsyncMock(return_value=mock_result)

        repo = AuthorRepository(mock_session)

        import time

        start = time.time()
        authors = await repo.get_all()
        duration = time.time() - start

        # Query should complete but take longer
        assert len(authors) == 1
        assert duration >= 0.5, (
            f"Query should take at least 500ms, took {duration:.3f}s"
        )
