"""Characterization tests for SummaryWorker.

These tests capture the current behavior of the SummaryWorker class
to ensure behavior preservation during refactoring.
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch, PropertyMock
from pathlib import Path

from src.workers.summary_worker import SummaryWorker


class TestSummaryWorkerInitialization:
    """Test SummaryWorker initialization behavior."""

    def test_init_with_required_params(self, qapp):
        """SummaryWorker initializes with room_id and summary_type."""
        worker = SummaryWorker(room_id=1, summary_type="today")

        assert worker.room_id == 1
        assert worker.summary_type == "today"

    def test_init_with_optional_params(self, qapp):
        """SummaryWorker accepts optional parameters."""
        worker = SummaryWorker(
            room_id=1,
            summary_type="yesterday",
            file_path="/path/to/chat.txt",
            room_name="Test Room",
            skip_existing=False,
            llm_provider="openai"
        )

        assert worker.file_path == "/path/to/chat.txt"
        assert worker.room_name == "Test Room"
        assert worker.skip_existing is False
        assert worker.llm_provider == "openai"

    def test_default_values(self, qapp):
        """SummaryWorker uses default values for optional params."""
        worker = SummaryWorker(room_id=1, summary_type="all")

        assert worker.file_path is None
        assert worker.room_name == "Unknown"
        assert worker.skip_existing is True
        assert worker.llm_provider == "glm"

    def test_signals_defined(self, qapp):
        """SummaryWorker has required signals."""
        worker = SummaryWorker(room_id=1, summary_type="today")

        assert hasattr(worker, 'progress')
        assert hasattr(worker, 'finished')
        assert hasattr(worker.progress, 'connect')
        assert hasattr(worker.finished, 'connect')


class TestSummaryWorkerGetDatesToProcess:
    """Test SummaryWorker _get_dates_to_process method."""

    def test_get_dates_pending_type(self, qapp):
        """_get_dates_to_process returns pending dates for 'pending' type."""
        worker = SummaryWorker(room_id=1, summary_type="pending", room_name="Test")

        messages_by_date = {
            "2024-02-10": ["msg1"],
            "2024-02-11": ["msg2"],
            "2024-02-12": ["msg3"],
        }

        with patch.object(worker, 'storage') as mock_storage:
            mock_storage.get_dates_needing_summary.return_value = {
                "2024-02-10": "new",
                "2024-02-11": "needs_update"
            }

            dates, skipped = worker._get_dates_to_process(messages_by_date)

        assert len(dates) == 2
        assert "2024-02-10" in dates
        assert "2024-02-11" in dates
        assert skipped == 1  # 2024-02-12 was skipped

    def test_get_dates_today_type(self, qapp):
        """_get_dates_to_process filters for today's date."""
        worker = SummaryWorker(room_id=1, summary_type="today", room_name="Test")

        today = datetime.now().strftime("%Y-%m-%d")
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

        messages_by_date = {
            yesterday: ["msg1"],
            today: ["msg2"],
        }

        with patch.object(worker, 'storage') as mock_storage:
            mock_storage.get_summarized_dates.return_value = set()

            dates, skipped = worker._get_dates_to_process(messages_by_date)

        assert len(dates) == 1
        assert today in dates

    def test_get_dates_yesterday_type(self, qapp):
        """_get_dates_to_process filters for dates >= yesterday (includes today)."""
        worker = SummaryWorker(room_id=1, summary_type="yesterday", room_name="Test")

        today = datetime.now().strftime("%Y-%m-%d")
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

        messages_by_date = {
            yesterday: ["msg1"],
            today: ["msg2"],
        }

        with patch.object(worker, 'storage') as mock_storage:
            mock_storage.get_summarized_dates.return_value = set()

            dates, skipped = worker._get_dates_to_process(messages_by_date)

        # Current implementation uses >= start_date, so includes both today and yesterday
        assert len(dates) == 2
        assert yesterday in dates
        assert today in dates

    def test_get_dates_skip_existing_true(self, qapp):
        """_get_dates_to_process skips already summarized dates."""
        worker = SummaryWorker(
            room_id=1,
            summary_type="all",
            room_name="Test",
            skip_existing=True
        )

        messages_by_date = {
            "2024-02-10": ["msg1"],
            "2024-02-11": ["msg2"],
        }

        with patch.object(worker, 'storage') as mock_storage:
            mock_storage.get_summarized_dates.return_value = {"2024-02-10"}

            dates, skipped = worker._get_dates_to_process(messages_by_date)

        assert len(dates) == 1
        assert "2024-02-11" in dates
        assert skipped == 1

    def test_get_dates_skip_existing_false(self, qapp):
        """_get_dates_to_process includes all dates when skip_existing is False."""
        worker = SummaryWorker(
            room_id=1,
            summary_type="all",
            room_name="Test",
            skip_existing=False
        )

        messages_by_date = {
            "2024-02-10": ["msg1"],
            "2024-02-11": ["msg2"],
        }

        with patch.object(worker, 'storage') as mock_storage:
            mock_storage.get_summarized_dates.return_value = {"2024-02-10"}

            dates, skipped = worker._get_dates_to_process(messages_by_date)

        assert len(dates) == 2
        assert skipped == 0


class TestSummaryWorkerCombineSummaries:
    """Test SummaryWorker _combine_summaries method."""

    def test_combine_single_summary(self, qapp):
        """_combine_summaries combines status with single summary."""
        worker = SummaryWorker(room_id=1, summary_type="today")

        result = worker._combine_summaries(
            "Summarized: 1 day",
            ["## Date: 2024-02-10\n\nSummary content"]
        )

        assert "Summarized: 1 day" in result
        assert "## Date: 2024-02-10" in result
        assert "---" in result

    def test_combine_multiple_summaries(self, qapp):
        """_combine_summaries combines status with multiple summaries."""
        worker = SummaryWorker(room_id=1, summary_type="all")

        result = worker._combine_summaries(
            "Summarized: 2 days",
            [
                "## Date: 2024-02-10\n\nFirst summary",
                "## Date: 2024-02-11\n\nSecond summary"
            ]
        )

        assert "Summarized: 2 days" in result
        assert "## Date: 2024-02-10" in result
        assert "## Date: 2024-02-11" in result
        # Should have separators between summaries
        assert result.count("---") >= 2


class TestSummaryWorkerSaveSummaryToDb:
    """Test SummaryWorker _save_summary_to_db method."""

    def test_save_summary_creates_db_entry(self, qapp):
        """_save_summary_to_db creates database entry."""
        worker = SummaryWorker(room_id=42, summary_type="today")

        with patch.object(worker, '_create_worker_db') as mock_create_db:
            mock_db = MagicMock()
            mock_create_db.return_value = mock_db

            worker._save_summary_to_db("2024-02-10", "Summary content", "glm")

        mock_db.delete_summary.assert_called_once()
        mock_db.add_summary.assert_called_once()
        # add_summary is called with positional args: (room_id, summary_date, summary_type, content, llm_provider)
        call_args = mock_db.add_summary.call_args[0]
        assert call_args[0] == 42  # room_id
        assert call_args[3] == "Summary content"  # content
        assert call_args[4] == "glm"  # llm_provider

    def test_save_summary_disposes_db(self, qapp):
        """_save_summary_to_db disposes database after use."""
        worker = SummaryWorker(room_id=1, summary_type="today")

        with patch.object(worker, '_create_worker_db') as mock_create_db:
            mock_db = MagicMock()
            mock_db.engine.dispose = MagicMock()
            mock_create_db.return_value = mock_db

            worker._save_summary_to_db("2024-02-10", "Summary", "glm")

        mock_db.engine.dispose.assert_called_once()

    def test_save_summary_handles_db_error(self, qapp):
        """_save_summary_to_db handles database errors gracefully."""
        worker = SummaryWorker(room_id=1, summary_type="today")

        with patch.object(worker, '_create_worker_db') as mock_create_db:
            mock_db = MagicMock()
            mock_db.add_summary.side_effect = Exception("DB error")
            mock_create_db.return_value = mock_db

            # Should not raise
            worker._save_summary_to_db("2024-02-10", "Summary", "glm")


class TestSummaryWorkerRunBehavior:
    """Test SummaryWorker run method behavior (characterization tests)."""

    def test_run_emits_finished_when_no_data(self, qapp):
        """run emits finished when no chat data available."""
        worker = SummaryWorker(room_id=1, summary_type="today", room_name="Test")

        finished_emissions = []
        worker.finished.connect(lambda s, m: finished_emissions.append((s, m)))

        # Patch get_storage to return mock storage
        with patch('file_storage.get_storage') as mock_get_storage:
            mock_storage = MagicMock()
            mock_storage.load_all_originals.return_value = {}
            mock_storage.get_summarized_dates.return_value = set()
            mock_get_storage.return_value = mock_storage

            worker.run()

        assert len(finished_emissions) == 1
        success, message = finished_emissions[0]
        assert success is False
        assert "No chat data" in message

    def test_run_skips_all_already_summarized(self, qapp):
        """run emits success when all dates already summarized."""
        worker = SummaryWorker(
            room_id=1,
            summary_type="all",
            room_name="Test",
            skip_existing=True
        )

        finished_emissions = []
        worker.finished.connect(lambda s, m: finished_emissions.append((s, m)))

        # Patch get_storage to return mock storage
        with patch('file_storage.get_storage') as mock_get_storage:
            mock_storage = MagicMock()
            mock_storage.load_all_originals.return_value = {
                "2024-02-10": ["msg1"]
            }
            mock_storage.get_summarized_dates.return_value = {"2024-02-10"}
            mock_get_storage.return_value = mock_storage

            worker.run()

        assert len(finished_emissions) == 1
        success, message = finished_emissions[0]
        assert success is True
        assert "already summarized" in message

    def test_run_handles_cancellation(self, qapp):
        """run handles cancellation during processing."""
        worker = SummaryWorker(room_id=1, summary_type="all", room_name="Test")

        progress_emissions = []
        worker.progress.connect(lambda p, m: progress_emissions.append((p, m)))

        finished_emissions = []
        worker.finished.connect(lambda s, m: finished_emissions.append((s, m)))

        # Cancel before running
        worker.cancel()

        # Patch get_storage to return mock storage
        with patch('file_storage.get_storage') as mock_get_storage:
            mock_storage = MagicMock()
            mock_storage.load_all_originals.return_value = {
                "2024-02-10": ["msg1"]
            }
            mock_storage.get_summarized_dates.return_value = set()
            mock_storage.get_dates_needing_summary.return_value = {
                "2024-02-10": "new"
            }
            mock_get_storage.return_value = mock_storage

            # Patch config in full_config module where it's imported from
            with patch('full_config.config') as mock_config:
                mock_provider_info = MagicMock()
                mock_provider_info.name = "Test LLM"
                mock_config.get_provider_info.return_value = mock_provider_info

                worker.run()

        # Should emit finished (cancelled state)
        assert len(finished_emissions) == 1


class TestSummaryWorkerDateRange:
    """Test SummaryWorker date range handling for different summary types."""

    def test_two_days_range(self, qapp):
        """_get_dates_to_process handles 2days type correctly."""
        worker = SummaryWorker(room_id=1, summary_type="2days", room_name="Test")

        today = datetime.now().strftime("%Y-%m-%d")
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        day_before = (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d")

        messages_by_date = {
            day_before: ["msg1"],
            yesterday: ["msg2"],
            today: ["msg3"],
        }

        with patch.object(worker, 'storage') as mock_storage:
            mock_storage.get_summarized_dates.return_value = set()

            dates, skipped = worker._get_dates_to_process(messages_by_date)

        # Should include day_before and all dates after
        assert len(dates) >= 1
        assert day_before in dates

    def test_empty_messages_returns_empty(self, qapp):
        """_get_dates_to_process returns empty when no messages."""
        worker = SummaryWorker(room_id=1, summary_type="all", room_name="Test")

        with patch.object(worker, 'storage') as mock_storage:
            mock_storage.get_summarized_dates.return_value = set()

            dates, skipped = worker._get_dates_to_process({})

        assert len(dates) == 0
        assert skipped == 0
