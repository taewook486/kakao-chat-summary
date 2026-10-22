"""Characterization tests for URLService.

These tests capture the current behavior of the URLService class
to ensure behavior preservation during refactoring.
"""
import pytest
from datetime import date
from unittest.mock import MagicMock, patch
from pathlib import Path

from src.services.url_service import URLService


class TestURLServiceInitialization:
    """Test URLService initialization behavior."""

    def test_init_with_required_repositories(self):
        """URLService initializes with required repositories."""
        chat_room_repo = MagicMock()
        url_repo = MagicMock()
        summary_repo = MagicMock()

        service = URLService(
            chat_room_repo=chat_room_repo,
            url_repo=url_repo,
            summary_repo=summary_repo,
        )

        assert service.chat_room_repo is chat_room_repo
        assert service.url_repo is url_repo
        assert service.summary_repo is summary_repo

    def test_init_creates_default_file_storage(self):
        """URLService creates default FileStorage if not provided."""
        chat_room_repo = MagicMock()
        url_repo = MagicMock()
        summary_repo = MagicMock()

        service = URLService(
            chat_room_repo=chat_room_repo,
            url_repo=url_repo,
            summary_repo=summary_repo,
        )

        assert service.file_storage is not None

    def test_init_accepts_custom_file_storage(self):
        """URLService accepts custom FileStorage instance."""
        chat_room_repo = MagicMock()
        url_repo = MagicMock()
        summary_repo = MagicMock()
        custom_storage = MagicMock()

        service = URLService(
            chat_room_repo=chat_room_repo,
            url_repo=url_repo,
            summary_repo=summary_repo,
            file_storage=custom_storage,
        )

        assert service.file_storage is custom_storage


class TestExtractURLsFromSummary:
    """Test URLService extract_urls_from_summary method."""

    def test_returns_empty_dict_when_room_not_found(self):
        """Returns empty dict when room doesn't exist."""
        chat_room_repo = MagicMock()
        chat_room_repo.get_by_id.return_value = None
        url_repo = MagicMock()
        summary_repo = MagicMock()

        service = URLService(
            chat_room_repo=chat_room_repo,
            url_repo=url_repo,
            summary_repo=summary_repo,
        )

        result = service.extract_urls_from_summary(room_id=999, summary_date=date(2024, 2, 10))

        assert result == {}
        chat_room_repo.get_by_id.assert_called_once_with(999)

    def test_returns_empty_dict_when_summary_not_found(self):
        """Returns empty dict when summary for date doesn't exist."""
        chat_room_repo = MagicMock()
        mock_room = MagicMock()
        mock_room.id = 1
        chat_room_repo.get_by_id.return_value = mock_room

        url_repo = MagicMock()
        summary_repo = MagicMock()
        summary_repo.get_summaries_by_room.return_value = []

        service = URLService(
            chat_room_repo=chat_room_repo,
            url_repo=url_repo,
            summary_repo=summary_repo,
        )

        result = service.extract_urls_from_summary(room_id=1, summary_date=date(2024, 2, 10))

        assert result == {}

    def test_returns_empty_dict_when_summary_has_no_content(self):
        """Returns empty dict when summary content is empty."""
        chat_room_repo = MagicMock()
        mock_room = MagicMock()
        mock_room.id = 1
        chat_room_repo.get_by_id.return_value = mock_room

        url_repo = MagicMock()

        # Create summary with empty content
        mock_summary = MagicMock()
        mock_summary.summary_date = date(2024, 2, 10)
        mock_summary.content = ""

        summary_repo = MagicMock()
        summary_repo.get_summaries_by_room.return_value = [mock_summary]

        service = URLService(
            chat_room_repo=chat_room_repo,
            url_repo=url_repo,
            summary_repo=summary_repo,
        )

        result = service.extract_urls_from_summary(room_id=1, summary_date=date(2024, 2, 10))

        assert result == {}

    def test_extracts_and_stores_urls_from_summary(self):
        """Extracts URLs, normalizes, deduplicates, and stores them."""
        chat_room_repo = MagicMock()
        mock_room = MagicMock()
        mock_room.id = 1
        mock_room.name = "TestRoom"
        chat_room_repo.get_by_id.return_value = mock_room

        url_repo = MagicMock()
        url_repo.add_urls_batch.return_value = 3

        # Create summary with content containing URLs
        mock_summary = MagicMock()
        mock_summary.summary_date = date(2024, 2, 10)
        mock_summary.content = """
        # Summary
        Check out https://example.com/article
        Also see http://test.com/page
        """

        summary_repo = MagicMock()
        summary_repo.get_summaries_by_room.return_value = [mock_summary]

        service = URLService(
            chat_room_repo=chat_room_repo,
            url_repo=url_repo,
            summary_repo=summary_repo,
        )

        with patch('src.services.url_service.extract_urls_from_text') as mock_extract:
            mock_extract.return_value = {
                "https://example.com/article": ["Article description"],
                "http://test.com/page": ["Page description"],
            }

            with patch('src.services.url_service.normalize_url') as mock_normalize:
                mock_normalize.side_effect = lambda x: x  # Return as-is

                with patch('src.services.url_service.deduplicate_urls') as mock_dedup:
                    mock_dedup.return_value = {
                        "https://example.com/article": ["Article description"],
                        "http://test.com/page": ["Page description"],
                    }

                    with patch.object(service, '_save_url_lists_to_file'):
                        result = service.extract_urls_from_summary(
                            room_id=1, summary_date=date(2024, 2, 10)
                        )

        # Verify URLs were stored in database
        url_repo.add_urls_batch.assert_called_once()
        assert result is not None


class TestExtractURLsFromAllSummaries:
    """Test URLService extract_urls_from_all_summaries method."""

    def test_returns_empty_dict_when_no_summaries(self):
        """Returns empty dict when room has no summaries."""
        chat_room_repo = MagicMock()
        url_repo = MagicMock()
        summary_repo = MagicMock()
        summary_repo.get_summaries_by_room.return_value = []

        service = URLService(
            chat_room_repo=chat_room_repo,
            url_repo=url_repo,
            summary_repo=summary_repo,
        )

        result = service.extract_urls_from_all_summaries(room_id=1)

        assert result == {}

    def test_extracts_urls_from_all_summaries_and_merges(self):
        """Extracts URLs from multiple summaries and merges them."""
        chat_room_repo = MagicMock()
        mock_room = MagicMock()
        mock_room.id = 1
        mock_room.name = "TestRoom"
        chat_room_repo.get_by_id.return_value = mock_room

        url_repo = MagicMock()
        url_repo.add_urls_batch.return_value = 2

        # Create multiple summaries
        mock_summary1 = MagicMock()
        mock_summary1.content = "Content with https://example.com/1"
        mock_summary1.summary_date = date(2024, 2, 10)

        mock_summary2 = MagicMock()
        mock_summary2.content = "Content with https://example.com/2"
        mock_summary2.summary_date = date(2024, 2, 11)

        summary_repo = MagicMock()
        summary_repo.get_summaries_by_room.return_value = [mock_summary1, mock_summary2]

        service = URLService(
            chat_room_repo=chat_room_repo,
            url_repo=url_repo,
            summary_repo=summary_repo,
        )

        with patch('src.services.url_service.extract_urls_from_text') as mock_extract:
            # Return different URLs for each summary
            mock_extract.side_effect = [
                {"https://example.com/1": ["First URL"]},
                {"https://example.com/2": ["Second URL"]},
            ]

            with patch('src.services.url_service.normalize_url') as mock_normalize:
                mock_normalize.side_effect = lambda x: x

                with patch('src.services.url_service.deduplicate_urls') as mock_dedup:
                    mock_dedup.return_value = {
                        "https://example.com/1": ["First URL"],
                        "https://example.com/2": ["Second URL"],
                    }

                    with patch.object(service, '_save_url_lists_to_file'):
                        result = service.extract_urls_from_all_summaries(room_id=1)

        # Verify URLs were cleared and re-added
        url_repo.clear_urls_by_room.assert_called_once_with(1)
        url_repo.add_urls_batch.assert_called_once()
        assert result is not None


class TestGetURLsByRoom:
    """Test URLService get_urls_by_room method."""

    def test_returns_urls_from_repository(self):
        """Returns URLs from repository for given room."""
        chat_room_repo = MagicMock()
        url_repo = MagicMock()
        url_repo.get_urls_by_room.return_value = {
            "https://example.com": ["Description"],
        }
        summary_repo = MagicMock()

        service = URLService(
            chat_room_repo=chat_room_repo,
            url_repo=url_repo,
            summary_repo=summary_repo,
        )

        result = service.get_urls_by_room(room_id=1)

        url_repo.get_urls_by_room.assert_called_once_with(1)
        assert result == {"https://example.com": ["Description"]}

    def test_returns_empty_dict_when_no_urls(self):
        """Returns empty dict when room has no URLs."""
        chat_room_repo = MagicMock()
        url_repo = MagicMock()
        url_repo.get_urls_by_room.return_value = {}
        summary_repo = MagicMock()

        service = URLService(
            chat_room_repo=chat_room_repo,
            url_repo=url_repo,
            summary_repo=summary_repo,
        )

        result = service.get_urls_by_room(room_id=1)

        assert result == {}


class TestSyncURLsFromFile:
    """Test URLService sync_urls_from_file method."""

    def test_returns_zero_when_room_not_found(self):
        """Returns 0 when room doesn't exist."""
        chat_room_repo = MagicMock()
        chat_room_repo.get_by_id.return_value = None
        url_repo = MagicMock()
        summary_repo = MagicMock()

        service = URLService(
            chat_room_repo=chat_room_repo,
            url_repo=url_repo,
            summary_repo=summary_repo,
        )

        result = service.sync_urls_from_file(room_id=999)

        assert result == 0

    def test_syncs_urls_from_all_list_types(self):
        """Syncs URLs from recent, weekly, and all list files."""
        chat_room_repo = MagicMock()
        mock_room = MagicMock()
        mock_room.id = 1
        mock_room.name = "TestRoom"
        chat_room_repo.get_by_id.return_value = mock_room

        url_repo = MagicMock()
        url_repo.add_urls_batch.return_value = 3

        summary_repo = MagicMock()

        # Mock file storage to return URLs from different lists
        file_storage = MagicMock()
        file_storage.load_url_list.side_effect = [
            {"https://example.com/1": ["Recent URL"]},  # recent
            {"https://example.com/2": ["Weekly URL"]},  # weekly
            {"https://example.com/3": ["All URL"]},     # all
        ]

        service = URLService(
            chat_room_repo=chat_room_repo,
            url_repo=url_repo,
            summary_repo=summary_repo,
            file_storage=file_storage,
        )

        with patch('src.services.url_service.normalize_url') as mock_normalize:
            mock_normalize.side_effect = lambda x: x

            with patch('src.services.url_service.deduplicate_urls') as mock_dedup:
                mock_dedup.return_value = {
                    "https://example.com/1": ["Recent URL"],
                    "https://example.com/2": ["Weekly URL"],
                    "https://example.com/3": ["All URL"],
                }

                result = service.sync_urls_from_file(room_id=1)

        # Verify URLs were loaded from all three list types
        assert file_storage.load_url_list.call_count == 3
        url_repo.clear_urls_by_room.assert_called_once_with(1)
        url_repo.add_urls_batch.assert_called_once()
        assert result == 3

    def test_returns_zero_when_no_urls_in_files(self):
        """Returns 0 when no URLs are found in files."""
        chat_room_repo = MagicMock()
        mock_room = MagicMock()
        mock_room.id = 1
        mock_room.name = "TestRoom"
        chat_room_repo.get_by_id.return_value = mock_room

        url_repo = MagicMock()
        summary_repo = MagicMock()

        # Mock file storage to return no URLs
        file_storage = MagicMock()
        file_storage.load_url_list.return_value = None

        service = URLService(
            chat_room_repo=chat_room_repo,
            url_repo=url_repo,
            summary_repo=summary_repo,
            file_storage=file_storage,
        )

        result = service.sync_urls_from_file(room_id=1)

        assert result == 0


class TestGetURLCount:
    """Test URLService get_url_count method."""

    def test_returns_count_from_repository(self):
        """Returns URL count from repository."""
        chat_room_repo = MagicMock()
        url_repo = MagicMock()
        url_repo.get_count_by_room.return_value = 42
        summary_repo = MagicMock()

        service = URLService(
            chat_room_repo=chat_room_repo,
            url_repo=url_repo,
            summary_repo=summary_repo,
        )

        result = service.get_url_count(room_id=1)

        url_repo.get_count_by_room.assert_called_once_with(1)
        assert result == 42

    def test_returns_zero_when_no_urls(self):
        """Returns 0 when room has no URLs."""
        chat_room_repo = MagicMock()
        url_repo = MagicMock()
        url_repo.get_count_by_room.return_value = 0
        summary_repo = MagicMock()

        service = URLService(
            chat_room_repo=chat_room_repo,
            url_repo=url_repo,
            summary_repo=summary_repo,
        )

        result = service.get_url_count(room_id=1)

        assert result == 0


class TestSaveURLListsToFile:
    """Test URLService _save_url_lists_to_file method."""

    def test_creates_directory_and_saves_files(self, temp_dir):
        """Creates directory structure and saves URL files."""
        chat_room_repo = MagicMock()
        url_repo = MagicMock()
        summary_repo = MagicMock()

        file_storage = MagicMock()
        file_storage.url_dir = temp_dir
        file_storage._sanitize_name = lambda x: x

        service = URLService(
            chat_room_repo=chat_room_repo,
            url_repo=url_repo,
            summary_repo=summary_repo,
            file_storage=file_storage,
        )

        urls = {
            "https://example.com": ["Example description"],
        }

        with patch('src.services.url_service.save_urls_to_file') as mock_save:
            service._save_url_lists_to_file("TestRoom", urls)

        # Should save to three files (recent, weekly, all)
        assert mock_save.call_count == 3
