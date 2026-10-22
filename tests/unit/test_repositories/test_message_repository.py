"""Characterization tests for MessageRepository.

These tests capture the current behavior of the MessageRepository class
to ensure behavior preservation during refactoring.
"""
import pytest
from datetime import date
from unittest.mock import MagicMock

from src.repositories.message_repository import MessageRepository
from src.db.models import Message


@pytest.fixture
def mock_db():
    """Create mock database for testing."""
    return MagicMock()


@pytest.fixture
def repository(mock_db):
    """Create MessageRepository with mock database."""
    return MessageRepository(mock_db)


class TestMessageRepositoryInitialization:
    """Test MessageRepository initialization behavior."""

    def test_init_stores_db_reference(self, mock_db):
        """MessageRepository stores database reference."""
        repo = MessageRepository(mock_db)
        assert repo.db is mock_db

    def test_init_accepts_any_db_like_object(self):
        """MessageRepository accepts any object as db."""
        mock_db = MagicMock()
        repo = MessageRepository(mock_db)
        assert repo.db is mock_db


class TestMessageRepositoryCreate:
    """Test MessageRepository create method."""

    def test_create_calls_add_messages_with_single_message(self, repository, mock_db):
        """Create calls add_messages with formatted message data."""
        mock_db.add_messages.return_value = 1

        result = repository.create(
            room_id=1,
            sender="User",
            content="Hello",
            message_date=date(2024, 2, 10),
            message_time="10:30",
        )

        # Verify add_messages was called with correct structure
        mock_db.add_messages.assert_called_once()
        call_args = mock_db.add_messages.call_args
        assert call_args[0][0] == 1  # room_id
        messages = call_args[0][1]
        assert len(messages) == 1
        assert messages[0]["sender"] == "User"
        assert messages[0]["content"] == "Hello"
        assert messages[0]["date"] == date(2024, 2, 10)
        assert messages[0]["time"] == "10:30"

    def test_create_returns_message_object(self, repository, mock_db):
        """Create returns Message object with provided data."""
        mock_db.add_messages.return_value = 1

        result = repository.create(
            room_id=1,
            sender="User",
            content="Hello",
            message_date=date(2024, 2, 10),
        )

        assert isinstance(result, Message)
        assert result.room_id == 1
        assert result.sender == "User"
        assert result.content == "Hello"
        assert result.message_date == date(2024, 2, 10)

    def test_create_without_time_passes_none(self, repository, mock_db):
        """Create handles missing message_time."""
        mock_db.add_messages.return_value = 1

        result = repository.create(
            room_id=1,
            sender="User",
            content="Hello",
            message_date=date(2024, 2, 10),
            message_time=None,
        )

        call_args = mock_db.add_messages.call_args
        messages = call_args[0][1]
        assert messages[0]["time"] is None

    def test_create_ignores_extra_kwargs(self, repository, mock_db):
        """Create ignores extra kwargs not in signature."""
        mock_db.add_messages.return_value = 1

        result = repository.create(
            room_id=1,
            sender="User",
            content="Hello",
            message_date=date(2024, 2, 10),
            extra_field="ignored",
        )

        # Should not raise error


class TestMessageRepositoryGetById:
    """Test MessageRepository get_by_id method."""

    def test_get_by_id_returns_none(self, repository):
        """get_by_id returns None (not implemented)."""
        result = repository.get_by_id(1)
        assert result is None

    def test_get_by_id_does_not_call_db(self, repository, mock_db):
        """get_by_id does not make database call."""
        repository.get_by_id(1)
        mock_db.assert_not_called()


class TestMessageRepositoryGetAll:
    """Test MessageRepository get_all method."""

    def test_get_all_returns_empty_list(self, repository):
        """get_all returns empty list (use get_messages_by_room)."""
        result = repository.get_all()
        assert result == []
        assert isinstance(result, list)


class TestMessageRepositoryGetMessagesByRoom:
    """Test MessageRepository get_messages_by_room method."""

    def test_get_messages_by_room_calls_db(self, repository, mock_db):
        """get_messages_by_room delegates to database."""
        mock_db.get_messages_by_room.return_value = []

        result = repository.get_messages_by_room(room_id=1)

        mock_db.get_messages_by_room.assert_called_once_with(1, None, None)

    def test_get_messages_by_room_with_date_filters(self, repository, mock_db):
        """get_messages_by_room passes date filters to database."""
        mock_db.get_messages_by_room.return_value = []

        result = repository.get_messages_by_room(
            room_id=1,
            start_date=date(2024, 2, 1),
            end_date=date(2024, 2, 28),
        )

        mock_db.get_messages_by_room.assert_called_once_with(
            1, date(2024, 2, 1), date(2024, 2, 28)
        )

    def test_get_messages_by_room_returns_db_result(self, repository, mock_db):
        """get_messages_by_room returns database result unchanged."""
        mock_messages = [MagicMock(), MagicMock()]
        mock_db.get_messages_by_room.return_value = mock_messages

        result = repository.get_messages_by_room(room_id=1)

        assert result is mock_messages


class TestMessageRepositoryUpdate:
    """Test MessageRepository update method."""

    def test_update_returns_none(self, repository):
        """update returns None (not implemented)."""
        result = repository.update(1, content="New content")
        assert result is None


class TestMessageRepositoryDelete:
    """Test MessageRepository delete method."""

    def test_delete_returns_false(self, repository):
        """delete returns False (not implemented)."""
        result = repository.delete(1)
        assert result is False


class TestMessageRepositoryAddMessages:
    """Test MessageRepository add_messages method."""

    def test_add_messages_delegates_to_db(self, repository, mock_db):
        """add_messages delegates to database add_messages."""
        mock_db.add_messages.return_value = 5

        messages = [
            {"sender": "User1", "content": "Hi", "date": date(2024, 2, 10)},
            {"sender": "User2", "content": "Hello", "date": date(2024, 2, 10)},
        ]

        result = repository.add_messages(room_id=1, messages=messages)

        mock_db.add_messages.assert_called_once_with(1, messages)
        assert result == 5

    def test_add_messages_with_empty_list(self, repository, mock_db):
        """add_messages handles empty message list."""
        mock_db.add_messages.return_value = 0

        result = repository.add_messages(room_id=1, messages=[])

        mock_db.add_messages.assert_called_once_with(1, [])
        assert result == 0


class TestMessageRepositoryGetCountByRoom:
    """Test MessageRepository get_count_by_room method."""

    def test_get_count_by_room_delegates_to_db(self, repository, mock_db):
        """get_count_by_room delegates to database."""
        mock_db.get_message_count_by_room.return_value = 100

        result = repository.get_count_by_room(room_id=1)

        mock_db.get_message_count_by_room.assert_called_once_with(1)
        assert result == 100

    def test_get_count_by_room_returns_zero_for_empty_room(self, repository, mock_db):
        """get_count_by_room returns 0 for room with no messages."""
        mock_db.get_message_count_by_room.return_value = 0

        result = repository.get_count_by_room(room_id=999)

        assert result == 0


class TestMessageRepositoryGetCountByDate:
    """Test MessageRepository get_count_by_date method."""

    def test_get_count_by_date_delegates_to_db(self, repository, mock_db):
        """get_count_by_date delegates to database."""
        mock_db.get_message_count_by_date.return_value = 25

        result = repository.get_count_by_date(
            room_id=1, target_date=date(2024, 2, 10)
        )

        mock_db.get_message_count_by_date.assert_called_once_with(
            1, date(2024, 2, 10)
        )
        assert result == 25


class TestMessageRepositoryGetUniqueSenders:
    """Test MessageRepository get_unique_senders method."""

    def test_get_unique_senders_delegates_to_db(self, repository, mock_db):
        """get_unique_senders delegates to database."""
        mock_db.get_unique_senders.return_value = ["Alice", "Bob", "Charlie"]

        result = repository.get_unique_senders(room_id=1)

        mock_db.get_unique_senders.assert_called_once_with(1)
        assert result == ["Alice", "Bob", "Charlie"]

    def test_get_unique_senders_returns_empty_list(self, repository, mock_db):
        """get_unique_senders returns empty list for room with no messages."""
        mock_db.get_unique_senders.return_value = []

        result = repository.get_unique_senders(room_id=999)

        assert result == []
