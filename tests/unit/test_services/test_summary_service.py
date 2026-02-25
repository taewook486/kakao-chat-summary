"""Characterization tests for SummaryService.

These tests capture the current behavior of the SummaryService class
to ensure behavior preservation during refactoring.
"""
import pytest
from datetime import date, timedelta
from unittest.mock import MagicMock, patch

from src.services.summary_service import SummaryService


@pytest.fixture
def mock_repos():
    """Create mock repositories for testing."""
    chat_room_repo = MagicMock()
    message_repo = MagicMock()
    summary_repo = MagicMock()
    sync_log_repo = MagicMock()
    return chat_room_repo, message_repo, summary_repo, sync_log_repo


class TestSummaryServiceInitialization:
    """Test SummaryService initialization behavior."""

    def test_init_with_required_repos(self, mock_repos):
        """SummaryService initializes with required repositories."""
        chat_room_repo, message_repo, summary_repo, sync_log_repo = mock_repos

        service = SummaryService(
            chat_room_repo=chat_room_repo,
            message_repo=message_repo,
            summary_repo=summary_repo,
            sync_log_repo=sync_log_repo,
        )

        assert service.chat_room_repo is chat_room_repo
        assert service.message_repo is message_repo
        assert service.summary_repo is summary_repo
        assert service.sync_log_repo is sync_log_repo

    def test_init_creates_default_file_storage(self, mock_repos):
        """SummaryService creates default FileStorage if not provided."""
        chat_room_repo, message_repo, summary_repo, sync_log_repo = mock_repos

        service = SummaryService(
            chat_room_repo=chat_room_repo,
            message_repo=message_repo,
            summary_repo=summary_repo,
            sync_log_repo=sync_log_repo,
        )

        assert service.file_storage is not None

    def test_init_accepts_custom_file_storage(self, mock_repos):
        """SummaryService accepts custom FileStorage instance."""
        chat_room_repo, message_repo, summary_repo, sync_log_repo = mock_repos
        custom_storage = MagicMock()

        service = SummaryService(
            chat_room_repo=chat_room_repo,
            message_repo=message_repo,
            summary_repo=summary_repo,
            sync_log_repo=sync_log_repo,
            file_storage=custom_storage,
        )

        assert service.file_storage is custom_storage

    def test_init_creates_chat_processor(self, mock_repos):
        """SummaryService creates ChatProcessor instance."""
        chat_room_repo, message_repo, summary_repo, sync_log_repo = mock_repos

        service = SummaryService(
            chat_room_repo=chat_room_repo,
            message_repo=message_repo,
            summary_repo=summary_repo,
            sync_log_repo=sync_log_repo,
        )

        assert service.processor is not None


class TestGenerateSummaryForDate:
    """Test SummaryService generate_summary_for_date method."""

    def test_returns_error_when_room_not_found(self, mock_repos):
        """Returns error when room doesn't exist."""
        chat_room_repo, message_repo, summary_repo, sync_log_repo = mock_repos
        chat_room_repo.get_by_id.return_value = None

        service = SummaryService(
            chat_room_repo=chat_room_repo,
            message_repo=message_repo,
            summary_repo=summary_repo,
            sync_log_repo=sync_log_repo,
        )

        result = service.generate_summary_for_date(
            room_id=999, target_date=date(2024, 2, 10)
        )

        assert result["success"] is False
        assert "Room not found" in result["error"]

    def test_returns_error_when_no_messages(self, mock_repos):
        """Returns error when no messages found for date."""
        chat_room_repo, message_repo, summary_repo, sync_log_repo = mock_repos

        mock_room = MagicMock()
        mock_room.name = "TestRoom"
        chat_room_repo.get_by_id.return_value = mock_room
        message_repo.get_messages_by_room.return_value = []

        service = SummaryService(
            chat_room_repo=chat_room_repo,
            message_repo=message_repo,
            summary_repo=summary_repo,
            sync_log_repo=sync_log_repo,
        )

        result = service.generate_summary_for_date(
            room_id=1, target_date=date(2024, 2, 10)
        )

        assert result["success"] is False
        assert "No messages found" in result["error"]

    def test_skips_when_summary_exists_and_skip_enabled(self, mock_repos):
        """Skips generation when summary exists and skip_existing is True."""
        chat_room_repo, message_repo, summary_repo, sync_log_repo = mock_repos

        mock_room = MagicMock()
        mock_room.name = "TestRoom"
        chat_room_repo.get_by_id.return_value = mock_room

        # Create existing summary
        mock_summary = MagicMock()
        mock_summary.summary_date = date(2024, 2, 10)
        mock_summary.id = 42
        mock_summary.content = "Existing summary"
        summary_repo.get_summaries_by_room.return_value = [mock_summary]

        service = SummaryService(
            chat_room_repo=chat_room_repo,
            message_repo=message_repo,
            summary_repo=summary_repo,
            sync_log_repo=sync_log_repo,
        )

        result = service.generate_summary_for_date(
            room_id=1, target_date=date(2024, 2, 10), skip_existing=True
        )

        assert result["success"] is True
        assert result["skipped"] is True
        assert result["summary_id"] == 42

    def test_generates_summary_when_skip_disabled(self, mock_repos):
        """Generates summary even when exists if skip_existing is False."""
        chat_room_repo, message_repo, summary_repo, sync_log_repo = mock_repos

        mock_room = MagicMock()
        mock_room.name = "TestRoom"
        chat_room_repo.get_by_id.return_value = mock_room

        # Create existing summary
        mock_summary = MagicMock()
        mock_summary.summary_date = date(2024, 2, 10)
        summary_repo.get_summaries_by_room.return_value = [mock_summary]

        # Create mock messages
        mock_message = MagicMock()
        mock_message.sender = "User"
        mock_message.content = "Hello"
        mock_message.message_date = date(2024, 2, 10)
        mock_message.message_time = MagicMock()
        message_repo.get_messages_by_room.return_value = [mock_message]

        # Mock LLM client
        with patch('src.services.summary_service.LLMClient') as mock_llm_class:
            mock_llm = MagicMock()
            mock_llm.summarize.return_value = {
                "success": True,
                "content": "Generated summary content that is long enough to pass validation."
            }
            mock_llm_class.return_value = mock_llm

            # Mock summary creation
            mock_new_summary = MagicMock()
            mock_new_summary.id = 100
            summary_repo.create.return_value = mock_new_summary

            service = SummaryService(
                chat_room_repo=chat_room_repo,
                message_repo=message_repo,
                summary_repo=summary_repo,
                sync_log_repo=sync_log_repo,
            )

            # Mock processor.process_chat (ChatProcessor is used for formatting)
            mock_processor = MagicMock()
            mock_processor.process_chat.return_value = "Formatted chat text"
            service.processor = mock_processor

            # Mock file_storage.save_daily_summary
            with patch.object(service, 'file_storage') as mock_storage:
                mock_storage.save_daily_summary = MagicMock()

                result = service.generate_summary_for_date(
                    room_id=1, target_date=date(2024, 2, 10), skip_existing=False
                )

        assert result["success"] is True
        assert result["skipped"] is False


class TestValidateSummaryContent:
    """Test SummaryService _validate_summary_content method."""

    def test_rejects_empty_content(self, mock_repos):
        """Rejects empty summary content."""
        chat_room_repo, message_repo, summary_repo, sync_log_repo = mock_repos

        service = SummaryService(
            chat_room_repo=chat_room_repo,
            message_repo=message_repo,
            summary_repo=summary_repo,
            sync_log_repo=sync_log_repo,
        )

        result = service._validate_summary_content("")

        assert result["valid"] is False
        assert "Empty" in result["reason"]

    def test_rejects_whitespace_only_content(self, mock_repos):
        """Rejects whitespace-only content."""
        chat_room_repo, message_repo, summary_repo, sync_log_repo = mock_repos

        service = SummaryService(
            chat_room_repo=chat_room_repo,
            message_repo=message_repo,
            summary_repo=summary_repo,
            sync_log_repo=sync_log_repo,
        )

        result = service._validate_summary_content("   \n\t  ")

        assert result["valid"] is False

    def test_rejects_too_short_content(self, mock_repos):
        """Rejects content shorter than minimum length."""
        chat_room_repo, message_repo, summary_repo, sync_log_repo = mock_repos

        service = SummaryService(
            chat_room_repo=chat_room_repo,
            message_repo=message_repo,
            summary_repo=summary_repo,
            sync_log_repo=sync_log_repo,
        )

        result = service._validate_summary_content("Too short")

        assert result["valid"] is False
        assert "short" in result["reason"].lower()

    def test_rejects_truncated_content(self, mock_repos):
        """Rejects content that appears truncated."""
        chat_room_repo, message_repo, summary_repo, sync_log_repo = mock_repos

        service = SummaryService(
            chat_room_repo=chat_room_repo,
            message_repo=message_repo,
            summary_repo=summary_repo,
            sync_log_repo=sync_log_repo,
        )

        result = service._validate_summary_content(
            "This summary is incomplete... and needs more content here."
        )

        assert result["valid"] is False
        assert "truncated" in result["reason"].lower()

    def test_accepts_valid_content(self, mock_repos):
        """Accepts valid summary content."""
        chat_room_repo, message_repo, summary_repo, sync_log_repo = mock_repos

        service = SummaryService(
            chat_room_repo=chat_room_repo,
            message_repo=message_repo,
            summary_repo=summary_repo,
            sync_log_repo=sync_log_repo,
        )

        result = service._validate_summary_content(
            "This is a valid summary with enough content to pass validation checks."
        )

        assert result["valid"] is True
        assert result["reason"] is None


class TestGetSummariesByRoom:
    """Test SummaryService get_summaries_by_room method."""

    def test_returns_summaries_from_repository(self, mock_repos):
        """Returns summaries from repository."""
        chat_room_repo, message_repo, summary_repo, sync_log_repo = mock_repos

        mock_summary = MagicMock()
        summary_repo.get_summaries_by_room.return_value = [mock_summary]

        service = SummaryService(
            chat_room_repo=chat_room_repo,
            message_repo=message_repo,
            summary_repo=summary_repo,
            sync_log_repo=sync_log_repo,
        )

        result = service.get_summaries_by_room(room_id=1)

        summary_repo.get_summaries_by_room.assert_called_once_with(1, None)
        assert len(result) == 1

    def test_filters_by_summary_type(self, mock_repos):
        """Filters summaries by type."""
        chat_room_repo, message_repo, summary_repo, sync_log_repo = mock_repos

        service = SummaryService(
            chat_room_repo=chat_room_repo,
            message_repo=message_repo,
            summary_repo=summary_repo,
            sync_log_repo=sync_log_repo,
        )

        service.get_summaries_by_room(room_id=1, summary_type="weekly")

        summary_repo.get_summaries_by_room.assert_called_once_with(1, "weekly")


class TestGetDatesNeedingSummary:
    """Test SummaryService get_dates_needing_summary method."""

    def test_returns_dates_without_summaries(self, mock_repos):
        """Returns dates that have messages but no summaries."""
        chat_room_repo, message_repo, summary_repo, sync_log_repo = mock_repos

        # Create mock messages with dates
        mock_msg1 = MagicMock()
        mock_msg1.message_date = date(2024, 2, 10)
        mock_msg2 = MagicMock()
        mock_msg2.message_date = date(2024, 2, 11)
        message_repo.get_messages_by_room.return_value = [mock_msg1, mock_msg2]

        # Create existing summary for one date
        mock_summary = MagicMock()
        mock_summary.summary_date = date(2024, 2, 10)
        summary_repo.get_summaries_by_room.return_value = [mock_summary]

        service = SummaryService(
            chat_room_repo=chat_room_repo,
            message_repo=message_repo,
            summary_repo=summary_repo,
            sync_log_repo=sync_log_repo,
        )

        result = service.get_dates_needing_summary(room_id=1)

        # Only 2024-02-11 should need summary
        assert len(result) == 1
        assert date(2024, 2, 11) in result

    def test_returns_empty_list_when_all_summarized(self, mock_repos):
        """Returns empty list when all dates have summaries."""
        chat_room_repo, message_repo, summary_repo, sync_log_repo = mock_repos

        # Create mock message
        mock_msg = MagicMock()
        mock_msg.message_date = date(2024, 2, 10)
        message_repo.get_messages_by_room.return_value = [mock_msg]

        # Create summary for same date
        mock_summary = MagicMock()
        mock_summary.summary_date = date(2024, 2, 10)
        summary_repo.get_summaries_by_room.return_value = [mock_summary]

        service = SummaryService(
            chat_room_repo=chat_room_repo,
            message_repo=message_repo,
            summary_repo=summary_repo,
            sync_log_repo=sync_log_repo,
        )

        result = service.get_dates_needing_summary(room_id=1)

        assert result == []

    def test_returns_all_dates_when_no_summaries(self, mock_repos):
        """Returns all message dates when no summaries exist."""
        chat_room_repo, message_repo, summary_repo, sync_log_repo = mock_repos

        # Create mock messages
        mock_msg1 = MagicMock()
        mock_msg1.message_date = date(2024, 2, 10)
        mock_msg2 = MagicMock()
        mock_msg2.message_date = date(2024, 2, 11)
        message_repo.get_messages_by_room.return_value = [mock_msg1, mock_msg2]

        # No existing summaries
        summary_repo.get_summaries_by_room.return_value = []

        service = SummaryService(
            chat_room_repo=chat_room_repo,
            message_repo=message_repo,
            summary_repo=summary_repo,
            sync_log_repo=sync_log_repo,
        )

        result = service.get_dates_needing_summary(room_id=1)

        assert len(result) == 2
        assert date(2024, 2, 10) in result
        assert date(2024, 2, 11) in result


class TestGenerateSummariesForDateRange:
    """Test SummaryService generate_summaries_for_date_range method."""

    def test_generates_summaries_for_each_date(self, mock_repos):
        """Generates summaries for each date in range."""
        chat_room_repo, message_repo, summary_repo, sync_log_repo = mock_repos

        mock_room = MagicMock()
        mock_room.name = "TestRoom"
        chat_room_repo.get_by_id.return_value = mock_room

        # Mock messages for all dates
        mock_msg = MagicMock()
        mock_msg.sender = "User"
        mock_msg.content = "Test"
        mock_msg.message_date = date(2024, 2, 10)
        mock_msg.message_time = MagicMock()
        message_repo.get_messages_by_room.return_value = [mock_msg]

        # No existing summaries
        summary_repo.get_summaries_by_room.return_value = []

        service = SummaryService(
            chat_room_repo=chat_room_repo,
            message_repo=message_repo,
            summary_repo=summary_repo,
            sync_log_repo=sync_log_repo,
        )

        # Mock generate_summary_for_date to return success
        with patch.object(
            service, 'generate_summary_for_date'
        ) as mock_generate:
            mock_generate.return_value = {
                "success": True,
                "summary_id": 1,
                "content": "Summary",
            }

            results = service.generate_summaries_for_date_range(
                room_id=1,
                start_date=date(2024, 2, 10),
                end_date=date(2024, 2, 12),
            )

        # Should have 3 results (10th, 11th, 12th)
        assert len(results) == 3
        for result in results:
            assert result["success"] is True

    def test_handles_generation_failures(self, mock_repos):
        """Handles failures during generation gracefully."""
        chat_room_repo, message_repo, summary_repo, sync_log_repo = mock_repos

        service = SummaryService(
            chat_room_repo=chat_room_repo,
            message_repo=message_repo,
            summary_repo=summary_repo,
            sync_log_repo=sync_log_repo,
        )

        # Mock generate_summary_for_date to return failure
        with patch.object(
            service, 'generate_summary_for_date'
        ) as mock_generate:
            mock_generate.return_value = {
                "success": False,
                "error": "LLM error",
            }

            results = service.generate_summaries_for_date_range(
                room_id=1,
                start_date=date(2024, 2, 10),
                end_date=date(2024, 2, 10),
            )

        assert len(results) == 1
        assert results[0]["success"] is False
