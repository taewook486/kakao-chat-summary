"""
Unit tests for Database class methods.

Tests cover:
- Session management and context managers
- ChatRoom CRUD operations
- Message operations and queries
- Summary operations
- SyncLog operations
- URL operations
- Statistics and aggregation queries
- Error handling and edge cases
"""

import pytest
from datetime import date, time, datetime
from pathlib import Path

from src.db.database import Database, get_db, reset_db
from src.db.models import ChatRoom, Message, Summary, SyncLog, URL


class TestDatabaseSessionManagement:
    """Test database session management."""

    def test_get_session_context_manager(self, db_session):
        """Test that get_session works as a context manager."""
        from sqlalchemy import text
        with db_session.get_session() as session:
            # Session should be active
            assert session is not None
            # Can execute queries
            result = session.execute(text("SELECT 1")).scalar()
            assert result == 1

    def test_get_session_commits_on_success(self, db_session):
        """Test that session commits on successful block."""
        room = db_session.create_room("Test Room")
        # Changes should be committed - room object is returned with id
        assert room is not None
        assert room.id is not None
        assert room.name == "Test Room"
        # Verify it can be retrieved
        retrieved = db_session.get_room_by_id(room.id)
        assert retrieved is not None
        assert retrieved.name == "Test Room"

    def test_get_session_rolls_back_on_error(self, db_session):
        """Test that session rolls back on exception."""
        try:
            with db_session.get_session() as session:
                room = ChatRoom(name="Temp Room")
                session.add(room)
                session.flush()
                # Raise exception to trigger rollback
                raise ValueError("Test error")
        except ValueError:
            pass

        # Room should not exist due to rollback
        rooms = db_session.get_all_rooms()
        assert len(rooms) == 0


class TestDatabaseChatRoomOperations:
    """Test ChatRoom CRUD operations."""

    def test_create_room_with_file_path(self, db_session):
        """Test creating a room with file path."""
        room = db_session.create_room("Test Room", "/path/to/file.txt")
        assert room.id is not None
        assert room.name == "Test Room"
        assert room.file_path == "/path/to/file.txt"

    def test_create_room_without_file_path(self, db_session):
        """Test creating a room without file path."""
        room = db_session.create_room("Test Room")
        assert room.id is not None
        assert room.name == "Test Room"
        assert room.file_path is None

    def test_get_room_by_id_found(self, db_session):
        """Test getting a room by existing ID."""
        created = db_session.create_room("Test Room")
        room = db_session.get_room_by_id(created.id)
        assert room is not None
        assert room.id == created.id
        assert room.name == "Test Room"

    def test_get_room_by_id_not_found(self, db_session):
        """Test getting a room by non-existent ID."""
        room = db_session.get_room_by_id(99999)
        assert room is None

    def test_get_room_by_name_found(self, db_session):
        """Test getting a room by existing name."""
        db_session.create_room("Test Room")
        room = db_session.get_room_by_name("Test Room")
        assert room is not None
        assert room.name == "Test Room"

    def test_get_room_by_name_not_found(self, db_session):
        """Test getting a room by non-existent name."""
        room = db_session.get_room_by_name("Nonexistent Room")
        assert room is None

    def test_get_all_rooms_empty(self, db_session):
        """Test getting all rooms when database is empty."""
        rooms = db_session.get_all_rooms()
        assert len(rooms) == 0

    def test_get_all_rooms_single(self, db_session):
        """Test getting all rooms with one room."""
        db_session.create_room("Test Room")
        rooms = db_session.get_all_rooms()
        assert len(rooms) == 1
        assert rooms[0].name == "Test Room"

    def test_get_all_rooms_multiple_sorted(self, db_session):
        """Test getting all rooms sorted by message count."""
        room1 = db_session.create_room("Room 1")
        room2 = db_session.create_room("Room 2")

        # Add messages to Room 1
        db_session.add_messages(room1.id, [
            {"sender": "A", "date": date(2024, 1, 1), "time": time(10, 0), "content": "Msg 1"}
        ])

        # Add multiple messages to Room 2
        db_session.add_messages(room2.id, [
            {"sender": "A", "date": date(2024, 1, 1), "time": time(10, 0), "content": "Msg 1"},
            {"sender": "B", "date": date(2024, 1, 1), "time": time(10, 1), "content": "Msg 2"}
        ])

        rooms = db_session.get_all_rooms()
        assert len(rooms) == 2
        # Room 2 should be first (more messages)
        assert rooms[0].name == "Room 2"
        assert rooms[1].name == "Room 1"

    def test_update_room_sync_time(self, db_session):
        """Test updating room sync time."""
        from datetime import datetime
        from unittest.mock import patch

        room = db_session.create_room("Test Room")

        # Mock datetime.now() to ensure time difference
        fixed_time = datetime(2024, 1, 1, 12, 0, 0)
        with patch('src.db.database.datetime') as mock_dt:
            mock_dt.now.return_value = fixed_time
            db_session.update_room_sync_time(room.id)

        updated_room = db_session.get_room_by_id(room.id)
        assert updated_room.last_sync_at == fixed_time

    def test_delete_room_existing(self, db_session):
        """Test deleting an existing room."""
        room = db_session.create_room("Test Room")
        room_id = room.id

        # Add messages
        db_session.add_messages(room_id, [
            {"sender": "A", "date": date(2024, 1, 1), "time": time(10, 0), "content": "Msg 1"}
        ])

        # Delete room
        db_session.delete_room(room_id)

        # Room should be gone
        room = db_session.get_room_by_id(room_id)
        assert room is None

        # Messages should also be deleted (cascade)
        messages = db_session.get_messages_by_room(room_id)
        assert len(messages) == 0

    def test_delete_room_nonexistent(self, db_session):
        """Test deleting a non-existent room (should not raise)."""
        # Should not raise exception
        db_session.delete_room(99999)


class TestDatabaseMessageOperations:
    """Test Message operations."""

    def test_add_messages_empty_list(self, db_session):
        """Test adding empty message list."""
        room = db_session.create_room("Test Room")
        count = db_session.add_messages(room.id, [])
        assert count == 0

    def test_add_messages_single(self, db_session):
        """Test adding a single message."""
        room = db_session.create_room("Test Room")
        messages = [
            {"sender": "Alice", "date": date(2024, 1, 1), "time": time(10, 0), "content": "Hello"}
        ]
        count = db_session.add_messages(room.id, messages)
        assert count == 1

        messages = db_session.get_messages_by_room(room.id)
        assert len(messages) == 1
        assert messages[0].sender == "Alice"

    def test_add_messages_multiple(self, db_session):
        """Test adding multiple messages."""
        room = db_session.create_room("Test Room")
        messages = [
            {"sender": "Alice", "date": date(2024, 1, 1), "time": time(10, 0), "content": "Hello"},
            {"sender": "Bob", "date": date(2024, 1, 1), "time": time(10, 1), "content": "Hi"},
        ]
        count = db_session.add_messages(room.id, messages)
        assert count == 2

    def test_add_messages_duplicates_ignored(self, db_session):
        """Test that duplicate messages are ignored."""
        room = db_session.create_room("Test Room")
        messages = [
            {"sender": "Alice", "date": date(2024, 1, 1), "time": time(10, 0), "content": "Hello"}
        ]

        # Add same messages twice
        count1 = db_session.add_messages(room.id, messages)
        count2 = db_session.add_messages(room.id, messages)

        assert count1 == 1
        assert count2 == 0  # Duplicate ignored

    def test_add_messages_without_time(self, db_session):
        """Test adding messages without time field."""
        room = db_session.create_room("Test Room")
        messages = [
            {"sender": "Alice", "date": date(2024, 1, 1), "content": "Hello"}
        ]
        count = db_session.add_messages(room.id, messages)
        assert count == 1

    def test_add_messages_without_content(self, db_session):
        """Test adding messages without content field."""
        room = db_session.create_room("Test Room")
        messages = [
            {"sender": "Alice", "date": date(2024, 1, 1), "time": time(10, 0)}
        ]
        count = db_session.add_messages(room.id, messages)
        assert count == 1

    def test_add_messages_batch_size(self, db_session):
        """Test adding messages with custom batch size."""
        room = db_session.create_room("Test Room")
        # Use smaller batch to avoid timeout
        messages = [
            {"sender": f"User{i}", "date": date(2024, 1, 1), "time": time(10, i % 60), "content": f"Msg {i}"}
            for i in range(20)
        ]
        # Small batch size
        count = db_session.add_messages(room.id, messages, batch_size=5)
        assert count == 20

    def test_get_messages_by_room_all(self, db_session):
        """Test getting all messages for a room."""
        room = db_session.create_room("Test Room")
        db_session.add_messages(room.id, [
            {"sender": "A", "date": date(2024, 1, 1), "time": time(10, 0), "content": "Msg 1"},
            {"sender": "B", "date": date(2024, 1, 2), "time": time(10, 0), "content": "Msg 2"},
        ])

        messages = db_session.get_messages_by_room(room.id)
        assert len(messages) == 2

    def test_get_messages_by_room_with_date_range(self, db_session):
        """Test getting messages within date range."""
        room = db_session.create_room("Test Room")
        db_session.add_messages(room.id, [
            {"sender": "A", "date": date(2024, 1, 1), "time": time(10, 0), "content": "Msg 1"},
            {"sender": "B", "date": date(2024, 1, 5), "time": time(10, 0), "content": "Msg 2"},
            {"sender": "C", "date": date(2024, 1, 10), "time": time(10, 0), "content": "Msg 3"},
        ])

        messages = db_session.get_messages_by_room(
            room.id,
            start_date=date(2024, 1, 3),
            end_date=date(2024, 1, 7)
        )
        assert len(messages) == 1
        assert messages[0].sender == "B"

    def test_get_message_count_by_room(self, db_session):
        """Test getting message count for a room."""
        room = db_session.create_room("Test Room")
        db_session.add_messages(room.id, [
            {"sender": "A", "date": date(2024, 1, 1), "time": time(10, 0), "content": "Msg 1"},
            {"sender": "B", "date": date(2024, 1, 2), "time": time(10, 0), "content": "Msg 2"},
        ])

        count = db_session.get_message_count_by_room(room.id)
        assert count == 2

    def test_get_message_count_by_date(self, db_session):
        """Test getting message count for specific date."""
        room = db_session.create_room("Test Room")
        db_session.add_messages(room.id, [
            {"sender": "A", "date": date(2024, 1, 1), "time": time(10, 0), "content": "Msg 1"},
            {"sender": "B", "date": date(2024, 1, 1), "time": time(11, 0), "content": "Msg 2"},
            {"sender": "C", "date": date(2024, 1, 2), "time": time(10, 0), "content": "Msg 3"},
        ])

        count = db_session.get_message_count_by_date(room.id, date(2024, 1, 1))
        assert count == 2

    def test_get_unique_senders(self, db_session):
        """Test getting unique senders for a room."""
        room = db_session.create_room("Test Room")
        db_session.add_messages(room.id, [
            {"sender": "Alice", "date": date(2024, 1, 1), "time": time(10, 0), "content": "Msg 1"},
            {"sender": "Bob", "date": date(2024, 1, 1), "time": time(10, 1), "content": "Msg 2"},
            {"sender": "Alice", "date": date(2024, 1, 1), "time": time(10, 2), "content": "Msg 3"},
        ])

        senders = db_session.get_unique_senders(room.id)
        assert len(senders) == 2
        assert "Alice" in senders
        assert "Bob" in senders


class TestDatabaseSummaryOperations:
    """Test Summary operations."""

    def test_add_summary(self, db_session):
        """Test adding a summary."""
        room = db_session.create_room("Test Room")
        summary = db_session.add_summary(
            room.id,
            date(2024, 1, 1),
            "daily",
            "# Test Summary\n\nContent here",
            llm_provider="test"
        )
        assert summary.id is not None
        assert summary.summary_date == date(2024, 1, 1)
        assert summary.summary_type == "daily"

    def test_get_summary_by_id(self, db_session):
        """Test getting summary by ID."""
        room = db_session.create_room("Test Room")
        created = db_session.add_summary(
            room.id,
            date(2024, 1, 1),
            "daily",
            "# Test Summary",
            llm_provider="test"
        )

        summary = db_session.get_summary_by_id(created.id)
        assert summary is not None
        assert summary.id == created.id

    def test_get_summaries_by_room(self, db_session):
        """Test getting summaries for a room."""
        room = db_session.create_room("Test Room")
        db_session.add_summary(room.id, date(2024, 1, 2), "daily", "# Summary 2")
        db_session.add_summary(room.id, date(2024, 1, 1), "daily", "# Summary 1")

        summaries = db_session.get_summaries_by_room(room.id)
        assert len(summaries) == 2
        # Should be sorted by date descending
        assert summaries[0].summary_date == date(2024, 1, 2)
        assert summaries[1].summary_date == date(2024, 1, 1)

    def test_get_summaries_by_room_with_type(self, db_session):
        """Test getting summaries filtered by type."""
        room = db_session.create_room("Test Room")
        db_session.add_summary(room.id, date(2024, 1, 1), "daily", "# Daily")
        db_session.add_summary(room.id, date(2024, 1, 1), "weekly", "# Weekly")

        summaries = db_session.get_summaries_by_room(room.id, summary_type="daily")
        assert len(summaries) == 1
        assert summaries[0].summary_type == "daily"

    def test_delete_summary(self, db_session):
        """Test deleting a summary."""
        room = db_session.create_room("Test Room")
        db_session.add_summary(room.id, date(2024, 1, 1), "daily", "# Summary")

        deleted = db_session.delete_summary(room.id, date(2024, 1, 1))
        assert deleted is True

        summaries = db_session.get_summaries_by_room(room.id)
        assert len(summaries) == 0

    def test_delete_summary_nonexistent(self, db_session):
        """Test deleting non-existent summary."""
        room = db_session.create_room("Test Room")
        deleted = db_session.delete_summary(room.id, date(2024, 1, 1))
        assert deleted is False


class TestDatabaseSyncLogOperations:
    """Test SyncLog operations."""

    def test_add_sync_log(self, db_session):
        """Test adding a sync log."""
        room = db_session.create_room("Test Room")
        log_id = db_session.add_sync_log(
            room.id,
            "success",
            message_count=100,
            new_message_count=50
        )
        assert log_id > 0

    def test_add_sync_log_with_error(self, db_session):
        """Test adding sync log with error message."""
        room = db_session.create_room("Test Room")
        log_id = db_session.add_sync_log(
            room.id,
            "error",
            error_message="Connection failed"
        )
        assert log_id > 0

    def test_get_sync_logs_by_room(self, db_session):
        """Test getting sync logs for a room."""
        room = db_session.create_room("Test Room")
        db_session.add_sync_log(room.id, "success", message_count=100)
        db_session.add_sync_log(room.id, "success", message_count=200)

        logs = db_session.get_sync_logs_by_room(room.id, limit=10)
        assert len(logs) == 2
        # Logs are sorted by synced_at descending
        # When timestamps are equal, order is by insertion order (first added = last in result)
        # Second log (200) was added last, so it should be first (most recent)
        assert logs[0].message_count == 200
        assert logs[1].message_count == 100

    def test_get_sync_logs_limit(self, db_session):
        """Test sync log limit parameter."""
        room = db_session.create_room("Test Room")
        for i in range(5):
            db_session.add_sync_log(room.id, "success", message_count=i)

        logs = db_session.get_sync_logs_by_room(room.id, limit=3)
        assert len(logs) == 3


class TestDatabaseURLOperations:
    """Test URL operations."""

    def test_add_url(self, db_session):
        """Test adding a URL."""
        room = db_session.create_room("Test Room")
        url_id = db_session.add_url(
            room.id,
            "https://example.com",
            descriptions=["Example site"]
        )
        assert url_id > 0

    def test_add_url_updates_existing(self, db_session):
        """Test that adding existing URL updates descriptions."""
        room = db_session.create_room("Test Room")
        db_session.add_url(room.id, "https://example.com", ["Desc 1"])
        db_session.add_url(room.id, "https://example.com", ["Desc 2"])

        urls = db_session.get_urls_by_room(room.id)
        assert len(urls) == 1
        # Descriptions should be merged
        assert "Desc 1" in urls["https://example.com"]
        assert "Desc 2" in urls["https://example.com"]

    def test_add_url_without_descriptions(self, db_session):
        """Test adding URL without descriptions."""
        room = db_session.create_room("Test Room")
        url_id = db_session.add_url(room.id, "https://example.com")
        assert url_id > 0

    def test_add_urls_batch(self, db_session):
        """Test adding multiple URLs at once."""
        room = db_session.create_room("Test Room")
        urls = {
            "https://example1.com": ["Site 1"],
            "https://example2.com": ["Site 2"],
        }
        count = db_session.add_urls_batch(room.id, urls)
        assert count == 2

    def test_get_urls_by_room(self, db_session):
        """Test getting URLs for a room."""
        room = db_session.create_room("Test Room")
        db_session.add_url(room.id, "https://example.com", ["Example"])

        urls = db_session.get_urls_by_room(room.id)
        assert len(urls) == 1
        assert "https://example.com" in urls

    def test_get_url_count_by_room(self, db_session):
        """Test getting URL count for a room."""
        room = db_session.create_room("Test Room")
        db_session.add_url(room.id, "https://example1.com", ["Site 1"])
        db_session.add_url(room.id, "https://example2.com", ["Site 2"])

        count = db_session.get_url_count_by_room(room.id)
        assert count == 2

    def test_clear_urls_by_room(self, db_session):
        """Test clearing all URLs for a room."""
        room = db_session.create_room("Test Room")
        db_session.add_url(room.id, "https://example.com", ["Example"])

        count = db_session.clear_urls_by_room(room.id)
        assert count == 1

        urls = db_session.get_urls_by_room(room.id)
        assert len(urls) == 0


class TestDatabaseStatistics:
    """Test statistics and aggregation queries."""

    def test_get_room_stats_existing(self, db_session):
        """Test getting statistics for existing room."""
        room = db_session.create_room("Test Room")
        db_session.add_messages(room.id, [
            {"sender": "Alice", "date": date(2024, 1, 1), "time": time(10, 0), "content": "Msg 1"},
            {"sender": "Bob", "date": date(2024, 1, 5), "time": time(10, 0), "content": "Msg 2"},
        ])

        stats = db_session.get_room_stats(room.id)
        assert stats['room_name'] == "Test Room"
        assert stats['total_messages'] == 2
        assert stats['unique_senders'] == 2
        assert stats['first_date'] == date(2024, 1, 1)
        assert stats['last_date'] == date(2024, 1, 5)

    def test_get_room_stats_nonexistent(self, db_session):
        """Test getting statistics for non-existent room."""
        stats = db_session.get_room_stats(99999)
        assert stats == {}


class TestDatabaseSingleton:
    """Test Database singleton pattern."""

    def test_get_db_returns_same_instance(self, temp_db):
        """Test that get_db returns same instance for same path."""
        db1 = get_db(str(temp_db))
        db2 = get_db(str(temp_db))
        assert db1 is db2

    def test_get_db_force_new(self, temp_db):
        """Test force_new parameter creates new instance."""
        db1 = get_db(str(temp_db))
        db2 = get_db(str(temp_db), force_new=True)
        assert db1 is not db2

    def test_get_db_different_paths(self, temp_db):
        """Test that different paths create different instances."""
        db1 = get_db(str(temp_db))
        db2 = get_db(str(temp_db) + "_other")
        assert db1 is not db2

    def test_reset_db(self, temp_db):
        """Test reset_db clears singleton."""
        db1 = get_db(str(temp_db))
        reset_db()
        db2 = get_db(str(temp_db))
        assert db1 is not db2
