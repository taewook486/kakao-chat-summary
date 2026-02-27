"""Characterization tests for FileService.

These tests capture the current behavior of the FileService class
to ensure behavior preservation during refactoring.
"""
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.services.file_service import FileService


@pytest.fixture
def mock_chat_room_repo():
    """Create mock chat room repository."""
    return MagicMock()


@pytest.fixture
def mock_file_storage():
    """Create mock file storage."""
    return MagicMock()


class TestFileServiceInitialization:
    """Test FileService initialization behavior."""

    def test_init_with_required_repo(self, mock_chat_room_repo):
        """FileService initializes with required repository."""
        service = FileService(chat_room_repo=mock_chat_room_repo)

        assert service.chat_room_repo is mock_chat_room_repo
        assert service.file_storage is not None
        assert service.parser is not None

    def test_init_creates_default_file_storage(self, mock_chat_room_repo):
        """FileService creates default FileStorage if not provided."""
        service = FileService(chat_room_repo=mock_chat_room_repo)

        assert service.file_storage is not None

    def test_init_accepts_custom_file_storage(
        self, mock_chat_room_repo, mock_file_storage
    ):
        """FileService accepts custom FileStorage instance."""
        service = FileService(
            chat_room_repo=mock_chat_room_repo,
            file_storage=mock_file_storage,
        )

        assert service.file_storage is mock_file_storage

    def test_init_creates_kakao_log_parser(self, mock_chat_room_repo):
        """FileService creates KakaoLogParser instance."""
        service = FileService(chat_room_repo=mock_chat_room_repo)

        assert service.parser is not None


class TestValidateChatFile:
    """Test FileService validate_chat_file method."""

    def test_returns_invalid_when_file_not_exists(
        self, mock_chat_room_repo, temp_dir
    ):
        """Returns invalid when file does not exist."""
        service = FileService(chat_room_repo=mock_chat_room_repo)

        result = service.validate_chat_file(str(temp_dir / "nonexistent.txt"))

        assert result["valid"] is False
        assert "does not exist" in result["reason"]
        assert result["date_count"] == 0

    def test_returns_invalid_when_no_date_headers(
        self, mock_chat_room_repo, temp_dir
    ):
        """Returns invalid when file has no date headers."""
        # Create a file without date headers
        invalid_file = temp_dir / "invalid.txt"
        invalid_file.write_text("Some random content without date headers")

        service = FileService(chat_room_repo=mock_chat_room_repo)

        result = service.validate_chat_file(str(invalid_file))

        assert result["valid"] is False
        assert "No valid date headers" in result["reason"]
        assert result["date_count"] == 0

    def test_returns_valid_for_valid_chat_file(
        self, mock_chat_room_repo, sample_chat_file
    ):
        """Returns valid for a properly formatted chat file."""
        service = FileService(chat_room_repo=mock_chat_room_repo)

        result = service.validate_chat_file(str(sample_chat_file))

        assert result["valid"] is True
        assert result["reason"] is None
        assert result["date_count"] > 0

    def test_returns_invalid_on_parser_exception(
        self, mock_chat_room_repo, temp_dir
    ):
        """Returns invalid when parser raises exception."""
        service = FileService(chat_room_repo=mock_chat_room_repo)

        # Create a valid file but mock parser to raise
        test_file = temp_dir / "test.txt"
        test_file.write_text("content")

        with patch.object(service, 'parser') as mock_parser:
            mock_parser.parse.side_effect = Exception("Parser error")

            result = service.validate_chat_file(str(test_file))

        assert result["valid"] is False
        assert "Error parsing file" in result["reason"]
        assert result["date_count"] == 0


class TestGetAvailableDatesForRoom:
    """Test FileService get_available_dates_for_room method."""

    def test_returns_dates_from_file_storage(
        self, mock_chat_room_repo, mock_file_storage
    ):
        """Returns available dates from file storage."""
        mock_file_storage.get_available_dates.return_value = [
            "2024-02-10", "2024-02-11"
        ]

        service = FileService(
            chat_room_repo=mock_chat_room_repo,
            file_storage=mock_file_storage,
        )

        result = service.get_available_dates_for_room("TestRoom")

        mock_file_storage.get_available_dates.assert_called_once_with("TestRoom")
        assert result == ["2024-02-10", "2024-02-11"]

    def test_returns_empty_list_when_no_dates(
        self, mock_chat_room_repo, mock_file_storage
    ):
        """Returns empty list when no dates available."""
        mock_file_storage.get_available_dates.return_value = []

        service = FileService(
            chat_room_repo=mock_chat_room_repo,
            file_storage=mock_file_storage,
        )

        result = service.get_available_dates_for_room("EmptyRoom")

        assert result == []


class TestGetChatContentForDate:
    """Test FileService get_chat_content_for_date method."""

    def test_returns_chat_content_from_storage(
        self, mock_chat_room_repo, mock_file_storage
    ):
        """Returns chat content from file storage."""
        expected_content = ["[User] [10:00] Hello", "[Bot] [10:01] Hi"]
        mock_file_storage.load_daily_original.return_value = expected_content

        service = FileService(
            chat_room_repo=mock_chat_room_repo,
            file_storage=mock_file_storage,
        )

        result = service.get_chat_content_for_date("TestRoom", "2024-02-10")

        mock_file_storage.load_daily_original.assert_called_once_with(
            "TestRoom", "2024-02-10"
        )
        assert result == expected_content

    def test_returns_none_when_content_not_found(
        self, mock_chat_room_repo, mock_file_storage
    ):
        """Returns None when content not found."""
        mock_file_storage.load_daily_original.return_value = None

        service = FileService(
            chat_room_repo=mock_chat_room_repo,
            file_storage=mock_file_storage,
        )

        result = service.get_chat_content_for_date("TestRoom", "2024-02-10")

        assert result is None


class TestGetSummaryContentForDate:
    """Test FileService get_summary_content_for_date method."""

    def test_returns_summary_content_from_storage(
        self, mock_chat_room_repo, mock_file_storage
    ):
        """Returns summary content from file storage."""
        expected_summary = "# Summary\n\nKey points..."
        mock_file_storage.load_daily_summary.return_value = expected_summary

        service = FileService(
            chat_room_repo=mock_chat_room_repo,
            file_storage=mock_file_storage,
        )

        result = service.get_summary_content_for_date("TestRoom", "2024-02-10")

        mock_file_storage.load_daily_summary.assert_called_once_with(
            "TestRoom", "2024-02-10"
        )
        assert result == expected_summary

    def test_returns_none_when_summary_not_found(
        self, mock_chat_room_repo, mock_file_storage
    ):
        """Returns None when summary not found."""
        mock_file_storage.load_daily_summary.return_value = None

        service = FileService(
            chat_room_repo=mock_chat_room_repo,
            file_storage=mock_file_storage,
        )

        result = service.get_summary_content_for_date("TestRoom", "2024-02-10")

        assert result is None


class TestCheckSummaryExists:
    """Test FileService check_summary_exists method."""

    def test_returns_true_when_summary_exists(
        self, mock_chat_room_repo, mock_file_storage
    ):
        """Returns True when summary exists."""
        mock_file_storage.get_summarized_dates.return_value = ["2024-02-10", "2024-02-11"]

        service = FileService(
            chat_room_repo=mock_chat_room_repo,
            file_storage=mock_file_storage,
        )

        result = service.check_summary_exists("TestRoom", "2024-02-10")

        mock_file_storage.get_summarized_dates.assert_called_once_with("TestRoom")
        assert result is True

    def test_returns_false_when_summary_not_exists(
        self, mock_chat_room_repo, mock_file_storage
    ):
        """Returns False when summary does not exist."""
        mock_file_storage.get_summarized_dates.return_value = ["2024-02-10"]

        service = FileService(
            chat_room_repo=mock_chat_room_repo,
            file_storage=mock_file_storage,
        )

        result = service.check_summary_exists("TestRoom", "2024-02-11")

        assert result is False

    def test_returns_false_when_no_summaries(
        self, mock_chat_room_repo, mock_file_storage
    ):
        """Returns False when no summaries exist for room."""
        mock_file_storage.get_summarized_dates.return_value = []

        service = FileService(
            chat_room_repo=mock_chat_room_repo,
            file_storage=mock_file_storage,
        )

        result = service.check_summary_exists("TestRoom", "2024-02-10")

        assert result is False


class TestGetDatesNeedingSummary:
    """Test FileService get_dates_needing_summary method."""

    def test_returns_dates_from_file_storage(
        self, mock_chat_room_repo, mock_file_storage
    ):
        """Returns dates needing summary from file storage."""
        expected = {
            "2024-02-10": "new",
            "2024-02-11": "needs_update",
        }
        mock_file_storage.get_dates_needing_summary.return_value = expected

        service = FileService(
            chat_room_repo=mock_chat_room_repo,
            file_storage=mock_file_storage,
        )

        result = service.get_dates_needing_summary("TestRoom")

        mock_file_storage.get_dates_needing_summary.assert_called_once_with("TestRoom")
        assert result == expected

    def test_returns_empty_dict_when_all_summarized(
        self, mock_chat_room_repo, mock_file_storage
    ):
        """Returns empty dict when all dates have summaries."""
        mock_file_storage.get_dates_needing_summary.return_value = {}

        service = FileService(
            chat_room_repo=mock_chat_room_repo,
            file_storage=mock_file_storage,
        )

        result = service.get_dates_needing_summary("TestRoom")

        assert result == {}


class TestDeleteSummary:
    """Test FileService delete_summary method."""

    def test_deletes_summary_through_storage(
        self, mock_chat_room_repo, mock_file_storage
    ):
        """Deletes summary through file storage."""
        mock_file_storage.delete_daily_summary.return_value = True

        service = FileService(
            chat_room_repo=mock_chat_room_repo,
            file_storage=mock_file_storage,
        )

        result = service.delete_summary("TestRoom", "2024-02-10")

        mock_file_storage.delete_daily_summary.assert_called_once_with(
            "TestRoom", "2024-02-10"
        )
        assert result is True

    def test_returns_false_when_deletion_fails(
        self, mock_chat_room_repo, mock_file_storage
    ):
        """Returns False when deletion fails."""
        mock_file_storage.delete_daily_summary.return_value = False

        service = FileService(
            chat_room_repo=mock_chat_room_repo,
            file_storage=mock_file_storage,
        )

        result = service.delete_summary("TestRoom", "2024-02-10")

        assert result is False


class TestGetFileSizeInfo:
    """Test FileService get_file_size_info method."""

    def test_returns_size_info_from_storage(
        self, mock_chat_room_repo, mock_file_storage
    ):
        """Returns file size information from storage."""
        mock_file_storage.get_original_file_size.return_value = 1024
        mock_file_storage.get_summary_file_size.return_value = 512

        service = FileService(
            chat_room_repo=mock_chat_room_repo,
            file_storage=mock_file_storage,
        )

        result = service.get_file_size_info("TestRoom", "2024-02-10")

        mock_file_storage.get_original_file_size.assert_called_once_with(
            "TestRoom", "2024-02-10"
        )
        mock_file_storage.get_summary_file_size.assert_called_once_with(
            "TestRoom", "2024-02-10"
        )

        assert result["original_size"] == 1024
        assert result["summary_size"] == 512
        assert result["total_size"] == 1536

    def test_returns_zero_sizes_when_files_not_found(
        self, mock_chat_room_repo, mock_file_storage
    ):
        """Returns zero sizes when files not found."""
        mock_file_storage.get_original_file_size.return_value = 0
        mock_file_storage.get_summary_file_size.return_value = 0

        service = FileService(
            chat_room_repo=mock_chat_room_repo,
            file_storage=mock_file_storage,
        )

        result = service.get_file_size_info("TestRoom", "2024-02-10")

        assert result["original_size"] == 0
        assert result["summary_size"] == 0
        assert result["total_size"] == 0

    def test_calculates_total_correctly(
        self, mock_chat_room_repo, mock_file_storage
    ):
        """Calculates total size correctly."""
        mock_file_storage.get_original_file_size.return_value = 2048
        mock_file_storage.get_summary_file_size.return_value = 1024

        service = FileService(
            chat_room_repo=mock_chat_room_repo,
            file_storage=mock_file_storage,
        )

        result = service.get_file_size_info("TestRoom", "2024-02-10")

        assert result["total_size"] == 3072
