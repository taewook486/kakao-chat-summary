"""Characterization tests for SummaryRepository.

These tests capture the current behavior of the SummaryRepository class
to ensure behavior preservation during refactoring.
"""
import pytest
from datetime import date
from unittest.mock import MagicMock

from src.repositories.summary_repository import SummaryRepository
from src.db.models import Summary


@pytest.fixture
def mock_db():
    """Create mock database for testing."""
    return MagicMock()


@pytest.fixture
def repository(mock_db):
    """Create SummaryRepository with mock database."""
    return SummaryRepository(mock_db)


class TestSummaryRepositoryInitialization:
    """Test SummaryRepository initialization behavior."""

    def test_init_stores_db_reference(self, mock_db):
        """SummaryRepository stores database reference."""
        repo = SummaryRepository(mock_db)
        assert repo.db is mock_db


class TestSummaryRepositoryCreate:
    """Test SummaryRepository create method."""

    def test_create_calls_db_add_summary(self, repository, mock_db):
        """Create delegates to database add_summary."""
        mock_summary = MagicMock()
        mock_db.add_summary.return_value = mock_summary

        result = repository.create(
            room_id=1,
            summary_date=date(2024, 2, 10),
            summary_type="daily",
            content="Summary content here",
            llm_provider="glm",
        )

        mock_db.add_summary.assert_called_once_with(
            room_id=1,
            summary_date=date(2024, 2, 10),
            summary_type="daily",
            content="Summary content here",
            llm_provider="glm",
        )
        assert result is mock_summary

    def test_create_without_llm_provider(self, repository, mock_db):
        """Create handles missing llm_provider."""
        mock_summary = MagicMock()
        mock_db.add_summary.return_value = mock_summary

        result = repository.create(
            room_id=1,
            summary_date=date(2024, 2, 10),
            summary_type="daily",
            content="Summary content",
        )

        mock_db.add_summary.assert_called_once_with(
            room_id=1,
            summary_date=date(2024, 2, 10),
            summary_type="daily",
            content="Summary content",
            llm_provider=None,
        )

    def test_create_with_extra_kwargs(self, repository, mock_db):
        """Create ignores extra kwargs (not passed to db)."""
        mock_summary = MagicMock()
        mock_db.add_summary.return_value = mock_summary

        result = repository.create(
            room_id=1,
            summary_date=date(2024, 2, 10),
            summary_type="daily",
            content="Summary content",
            extra_field="ignored",
        )

        # Should not raise error


class TestSummaryRepositoryGetById:
    """Test SummaryRepository get_by_id method."""

    def test_get_by_id_calls_db(self, repository, mock_db):
        """get_by_id delegates to database."""
        mock_summary = MagicMock()
        mock_db.get_summary_by_id.return_value = mock_summary

        result = repository.get_by_id(42)

        mock_db.get_summary_by_id.assert_called_once_with(42)
        assert result is mock_summary

    def test_get_by_id_returns_none_for_not_found(self, repository, mock_db):
        """get_by_id returns None when summary not found."""
        mock_db.get_summary_by_id.return_value = None

        result = repository.get_by_id(999)

        assert result is None


class TestSummaryRepositoryGetAll:
    """Test SummaryRepository get_all method."""

    def test_get_all_returns_empty_list(self, repository):
        """get_all returns empty list (use get_summaries_by_room)."""
        result = repository.get_all()
        assert result == []
        assert isinstance(result, list)


class TestSummaryRepositoryGetSummariesByRoom:
    """Test SummaryRepository get_summaries_by_room method."""

    def test_get_summaries_by_room_calls_db(self, repository, mock_db):
        """get_summaries_by_room delegates to database."""
        mock_db.get_summaries_by_room.return_value = []

        result = repository.get_summaries_by_room(room_id=1)

        mock_db.get_summaries_by_room.assert_called_once_with(1, None)

    def test_get_summaries_by_room_with_type_filter(self, repository, mock_db):
        """get_summaries_by_room passes type filter to database."""
        mock_db.get_summaries_by_room.return_value = []

        result = repository.get_summaries_by_room(room_id=1, summary_type="weekly")

        mock_db.get_summaries_by_room.assert_called_once_with(1, "weekly")

    def test_get_summaries_by_room_returns_db_result(self, repository, mock_db):
        """get_summaries_by_room returns database result unchanged."""
        mock_summaries = [MagicMock(), MagicMock()]
        mock_db.get_summaries_by_room.return_value = mock_summaries

        result = repository.get_summaries_by_room(room_id=1)

        assert result is mock_summaries


class TestSummaryRepositoryGetByRoom:
    """Test SummaryRepository get_by_room alias method."""

    def test_get_by_room_calls_get_summaries_by_room(self, repository, mock_db):
        """get_by_room is an alias for get_summaries_by_room."""
        mock_summaries = [MagicMock()]
        mock_db.get_summaries_by_room.return_value = mock_summaries

        result = repository.get_by_room(room_id=1, summary_type="daily")

        mock_db.get_summaries_by_room.assert_called_once_with(1, "daily")
        assert result is mock_summaries


class TestSummaryRepositoryUpdate:
    """Test SummaryRepository update method."""

    def test_update_returns_none(self, repository):
        """update returns None (not implemented)."""
        result = repository.update(1, content="New content")
        assert result is None


class TestSummaryRepositoryDelete:
    """Test SummaryRepository delete method."""

    def test_delete_returns_false(self, repository):
        """delete returns False (use delete_by_date instead)."""
        result = repository.delete(1)
        assert result is False


class TestSummaryRepositoryDeleteByDate:
    """Test SummaryRepository delete_by_date method."""

    def test_delete_by_date_calls_db(self, repository, mock_db):
        """delete_by_date delegates to database."""
        mock_db.delete_summary.return_value = True

        result = repository.delete_by_date(
            room_id=1, summary_date=date(2024, 2, 10)
        )

        mock_db.delete_summary.assert_called_once_with(1, date(2024, 2, 10))
        assert result is True

    def test_delete_by_date_returns_false_when_not_found(self, repository, mock_db):
        """delete_by_date returns False when summary not found."""
        mock_db.delete_summary.return_value = False

        result = repository.delete_by_date(
            room_id=999, summary_date=date(2024, 2, 10)
        )

        assert result is False
