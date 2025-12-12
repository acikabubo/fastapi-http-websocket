"""
Tests for UnixTimestampField custom SQLModel field.

These tests verify that datetime values are correctly stored as Unix timestamps
(BIGINT) in the database while maintaining datetime objects in Python code.
"""

import pytest
from datetime import datetime, timezone, timedelta
from typing import Optional

from sqlmodel import Field, SQLModel, create_engine, Session, select
from sqlmodel.pool import StaticPool

from app.fields.unix_timestamp import (
    UnixTimestampField,
    UnixTimestampType,
)


# Test model using UnixTimestampField
class Event(SQLModel, table=True):
    """Test model with Unix timestamp fields."""

    __tablename__ = "test_events"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=255)

    # Unix timestamp fields
    created_at: datetime = UnixTimestampField(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    updated_at: Optional[datetime] = UnixTimestampField(
        default=None, nullable=True
    )

    scheduled_at: Optional[datetime] = UnixTimestampField(
        default=None, nullable=True, index=True
    )


@pytest.fixture
def engine():
    """Create in-memory SQLite engine for testing."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    return engine


@pytest.fixture
def session(engine):
    """Create database session for testing."""
    with Session(engine) as session:
        yield session


class TestUnixTimestampType:
    """Test UnixTimestampType TypeDecorator."""

    def test_process_bind_param_with_datetime(self):
        """Test converting datetime to Unix timestamp."""
        field_type = UnixTimestampType()
        dt = datetime(2025, 12, 12, 10, 30, 0, tzinfo=timezone.utc)

        result = field_type.process_bind_param(dt, None)

        assert isinstance(result, int)
        assert result == int(dt.timestamp())

    def test_process_bind_param_with_none(self):
        """Test that None is preserved."""
        field_type = UnixTimestampType()

        result = field_type.process_bind_param(None, None)

        assert result is None

    def test_process_bind_param_naive_datetime(self):
        """Test that naive datetime is treated as UTC."""
        field_type = UnixTimestampType()
        naive_dt = datetime(2025, 12, 12, 10, 30, 0)

        result = field_type.process_bind_param(naive_dt, None)

        # Should be same as UTC datetime
        utc_dt = datetime(2025, 12, 12, 10, 30, 0, tzinfo=timezone.utc)
        assert result == int(utc_dt.timestamp())

    def test_process_result_value_with_timestamp(self):
        """Test converting Unix timestamp to datetime."""
        field_type = UnixTimestampType()
        timestamp = 1765535400  # 2025-12-12 10:30:00 UTC

        result = field_type.process_result_value(timestamp, None)

        assert isinstance(result, datetime)
        assert result.tzinfo == timezone.utc
        assert result.year == 2025
        assert result.month == 12
        assert result.day == 12
        assert result.hour == 10
        assert result.minute == 30

    def test_process_result_value_with_none(self):
        """Test that None is preserved."""
        field_type = UnixTimestampType()

        result = field_type.process_result_value(None, None)

        assert result is None


class TestUnixTimestampFieldStorage:
    """Test storage and retrieval of Unix timestamp fields."""

    def test_create_event_with_default_timestamp(self, session):
        """Test creating event with default created_at timestamp."""
        before = datetime.now(timezone.utc).replace(microsecond=0)
        event = Event(name="Test Event")

        session.add(event)
        session.commit()
        session.refresh(event)

        after = datetime.now(timezone.utc).replace(microsecond=0)

        assert isinstance(event.created_at, datetime)
        assert event.created_at.tzinfo == timezone.utc
        # Unix timestamp has second precision, so microseconds should be 0
        assert event.created_at.microsecond == 0
        assert before <= event.created_at <= after

    def test_create_event_with_explicit_timestamp(self, session):
        """Test creating event with explicit timestamp."""
        specific_time = datetime(
            2025, 12, 12, 10, 30, 0, tzinfo=timezone.utc
        )

        event = Event(name="Test Event", created_at=specific_time)

        session.add(event)
        session.commit()
        session.refresh(event)

        assert isinstance(event.created_at, datetime)
        assert event.created_at == specific_time

    def test_nullable_timestamp_field(self, session):
        """Test that nullable timestamp fields work correctly."""
        event = Event(name="Test Event", updated_at=None)

        session.add(event)
        session.commit()
        session.refresh(event)

        assert event.updated_at is None

    def test_update_timestamp_field(self, session):
        """Test updating a timestamp field."""
        event = Event(name="Test Event")
        session.add(event)
        session.commit()

        # Update the timestamp
        new_time = datetime.now(timezone.utc)
        event.updated_at = new_time
        session.commit()
        session.refresh(event)

        assert event.updated_at is not None
        assert isinstance(event.updated_at, datetime)
        # Allow small difference due to precision
        assert abs((event.updated_at - new_time).total_seconds()) < 1

    def test_scheduled_timestamp_with_future_date(self, session):
        """Test storing future timestamp."""
        future_time = datetime.now(timezone.utc) + timedelta(days=7)

        event = Event(name="Future Event", scheduled_at=future_time)

        session.add(event)
        session.commit()
        session.refresh(event)

        assert isinstance(event.scheduled_at, datetime)
        assert event.scheduled_at.tzinfo == timezone.utc
        # Allow small difference due to precision
        assert abs((event.scheduled_at - future_time).total_seconds()) < 1


class TestUnixTimestampFieldQuerying:
    """Test querying with Unix timestamp fields."""

    def test_filter_by_exact_timestamp(self, session):
        """Test filtering events by exact timestamp."""
        specific_time = datetime(
            2025, 12, 12, 10, 30, 0, tzinfo=timezone.utc
        )

        event1 = Event(name="Event 1", created_at=specific_time)
        event2 = Event(
            name="Event 2",
            created_at=specific_time + timedelta(hours=1),
        )

        session.add_all([event1, event2])
        session.commit()

        # Query by exact time
        result = session.exec(
            select(Event).where(Event.created_at == specific_time)
        ).all()

        assert len(result) == 1
        assert result[0].name == "Event 1"

    def test_filter_by_date_range(self, session):
        """Test filtering events by date range."""
        base_time = datetime(2025, 12, 12, 0, 0, 0, tzinfo=timezone.utc)

        event1 = Event(
            name="Event 1", created_at=base_time + timedelta(hours=1)
        )
        event2 = Event(
            name="Event 2", created_at=base_time + timedelta(hours=5)
        )
        event3 = Event(
            name="Event 3", created_at=base_time + timedelta(hours=10)
        )

        session.add_all([event1, event2, event3])
        session.commit()

        # Query events between 2 and 8 hours
        from_time = base_time + timedelta(hours=2)
        to_time = base_time + timedelta(hours=8)

        result = session.exec(
            select(Event)
            .where(Event.created_at >= from_time)
            .where(Event.created_at <= to_time)
        ).all()

        assert len(result) == 1
        assert result[0].name == "Event 2"

    def test_filter_greater_than(self, session):
        """Test filtering events after a specific time."""
        base_time = datetime.now(timezone.utc)

        event1 = Event(name="Past Event", created_at=base_time)
        event2 = Event(
            name="Future Event",
            created_at=base_time + timedelta(days=1),
        )

        session.add_all([event1, event2])
        session.commit()

        # Query future events
        result = session.exec(
            select(Event).where(Event.created_at > base_time)
        ).all()

        assert len(result) == 1
        assert result[0].name == "Future Event"

    def test_order_by_timestamp(self, session):
        """Test ordering events by timestamp."""
        base_time = datetime(2025, 12, 12, 0, 0, 0, tzinfo=timezone.utc)

        event1 = Event(
            name="Event C", created_at=base_time + timedelta(hours=5)
        )
        event2 = Event(
            name="Event A", created_at=base_time + timedelta(hours=1)
        )
        event3 = Event(
            name="Event B", created_at=base_time + timedelta(hours=3)
        )

        session.add_all([event1, event2, event3])
        session.commit()

        # Query ordered by created_at
        result = session.exec(
            select(Event).order_by(Event.created_at)
        ).all()

        assert len(result) == 3
        assert result[0].name == "Event A"
        assert result[1].name == "Event B"
        assert result[2].name == "Event C"

    def test_filter_null_timestamps(self, session):
        """Test filtering for NULL and non-NULL timestamps."""
        event1 = Event(name="Event 1", updated_at=None)
        event2 = Event(
            name="Event 2",
            updated_at=datetime.now(timezone.utc),
        )

        session.add_all([event1, event2])
        session.commit()

        # Query events with NULL updated_at
        null_result = session.exec(
            select(Event).where(Event.updated_at.is_(None))
        ).all()

        assert len(null_result) == 1
        assert null_result[0].name == "Event 1"

        # Query events with non-NULL updated_at
        not_null_result = session.exec(
            select(Event).where(Event.updated_at.isnot(None))
        ).all()

        assert len(not_null_result) == 1
        assert not_null_result[0].name == "Event 2"


class TestUnixTimestampFieldEdgeCases:
    """Test edge cases for Unix timestamp fields."""

    def test_epoch_timestamp(self, session):
        """Test storing Unix epoch (timestamp 0)."""
        epoch = datetime(1970, 1, 1, 0, 0, 0, tzinfo=timezone.utc)

        event = Event(name="Epoch Event", created_at=epoch)

        session.add(event)
        session.commit()
        session.refresh(event)

        assert event.created_at == epoch

    def test_year_2038_problem(self, session):
        """Test timestamps beyond 2038 (32-bit signed int limit)."""
        # January 19, 2038, 03:14:08 UTC (32-bit limit + 1 second)
        beyond_2038 = datetime(2038, 1, 19, 3, 14, 8, tzinfo=timezone.utc)

        event = Event(name="Future Event", created_at=beyond_2038)

        session.add(event)
        session.commit()
        session.refresh(event)

        assert isinstance(event.created_at, datetime)
        # Allow small difference due to precision
        assert abs((event.created_at - beyond_2038).total_seconds()) < 1

    def test_very_far_future(self, session):
        """Test timestamps far in the future."""
        far_future = datetime(2100, 1, 1, 0, 0, 0, tzinfo=timezone.utc)

        event = Event(name="Far Future Event", created_at=far_future)

        session.add(event)
        session.commit()
        session.refresh(event)

        assert isinstance(event.created_at, datetime)
        assert event.created_at.year == 2100

    def test_microseconds_precision(self, session):
        """Test that microseconds are truncated (seconds precision only)."""
        time_with_microseconds = datetime(
            2025, 12, 12, 10, 30, 0, 123456, tzinfo=timezone.utc
        )

        event = Event(name="Precise Event", created_at=time_with_microseconds)

        session.add(event)
        session.commit()
        session.refresh(event)

        # Unix timestamp only has second precision
        # Microseconds should be lost
        assert event.created_at.microsecond == 0
        assert event.created_at.second == time_with_microseconds.second
