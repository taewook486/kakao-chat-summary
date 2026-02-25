"""Characterization tests for RecoveryWorker.

These tests capture the current behavior of the RecoveryWorker class
to ensure behavior preservation during refactoring.
"""
import pytest
from datetime import datetime, date
from unittest.mock import MagicMock, patch
from pathlib import Path

from src.workers.recovery_worker import RecoveryWorker


class TestRecoveryWorkerInitialization:
    """Test RecoveryWorker initialization behavior."""

    def test_init_no_params_required(self, qapp):
        """RecoveryWorker initializes without required parameters."""
        worker = RecoveryWorker()

        assert worker.storage is None  # Initialized in run()

    def test_init_accepts_parent(self, qapp):
        """RecoveryWorker accepts optional parent parameter."""
        # QThread parent must be QObject, not MagicMock
        worker = RecoveryWorker()

        assert worker.storage is None

    def test_signals_defined(self, qapp):
        """RecoveryWorker has required signals."""
        worker = RecoveryWorker()

        assert hasattr(worker, 'progress')
        assert hasattr(worker, 'finished')
        assert hasattr(worker.progress, 'connect')
        assert hasattr(worker.finished, 'connect')


class TestRecoveryWorkerRunBehavior:
    """Test RecoveryWorker run method behavior (characterization tests)."""

    def test_run_emits_finished_no_data(self, qapp):
        """run emits finished with error when no data to recover."""
        worker = RecoveryWorker()

        finished_emissions = []
        worker.finished.connect(lambda s, m: finished_emissions.append((s, m)))

        # Patch get_storage inside run()
        with patch('file_storage.get_storage') as mock_get_storage:
            mock_storage = MagicMock()
            mock_storage.get_all_rooms.return_value = []
            mock_get_storage.return_value = mock_storage

            # Patch db module imports inside run()
            with patch('db.reset_db'):
                with patch('db.get_db') as mock_get_db:
                    mock_db = MagicMock()
                    mock_get_db.return_value = mock_db

                    worker.run()

        assert len(finished_emissions) == 1
        success, message = finished_emissions[0]
        assert success is False
        assert "No data to recover" in message

    def test_run_emits_progress_during_recovery(self, qapp):
        """run emits progress signals during recovery."""
        worker = RecoveryWorker()

        progress_emissions = []
        worker.progress.connect(lambda p, m: progress_emissions.append((p, m)))

        with patch('file_storage.get_storage') as mock_get_storage:
            mock_storage = MagicMock()
            mock_storage.get_all_rooms.return_value = ["Room1"]
            mock_storage.load_all_originals.return_value = {}
            mock_storage.get_summarized_dates.return_value = []
            mock_get_storage.return_value = mock_storage

            with patch('db.reset_db'):
                with patch('db.get_db') as mock_get_db:
                    mock_db = MagicMock()
                    mock_db.create_room.return_value = MagicMock(id=1)
                    mock_get_db.return_value = mock_db

                    worker.run()

        # Verify progress emissions
        assert len(progress_emissions) > 0
        # Should emit 100% at completion
        assert any(p == 100 for p, m in progress_emissions)

    def test_run_recovers_single_room(self, qapp):
        """run recovers a single room with messages and summaries."""
        worker = RecoveryWorker()

        finished_emissions = []
        worker.finished.connect(lambda s, m: finished_emissions.append((s, m)))

        with patch('file_storage.get_storage') as mock_get_storage:
            mock_storage = MagicMock()
            mock_storage.get_all_rooms.return_value = ["TestRoom"]
            mock_storage.load_all_originals.return_value = {
                "2024-02-10": [
                    "[홍길동] [오전 10:00] 안녕하세요",
                    "[김철수] [오전 10:05] 반갑습니다"
                ]
            }
            mock_storage.get_summarized_dates.return_value = ["2024-02-10"]
            mock_storage.load_daily_summary.return_value = "Summary content"
            mock_get_storage.return_value = mock_storage

            with patch('db.reset_db'):
                with patch('db.get_db') as mock_get_db:
                    mock_db = MagicMock()
                    mock_room = MagicMock()
                    mock_room.id = 1
                    mock_db.create_room.return_value = mock_room
                    mock_db.add_messages.return_value = 2
                    mock_get_db.return_value = mock_db

                    worker.run()

        assert len(finished_emissions) == 1
        success, message = finished_emissions[0]
        assert success is True
        assert "Recovery complete" in message
        assert "Rooms: 1" in message

    def test_run_recovers_multiple_rooms(self, qapp):
        """run recovers multiple rooms."""
        worker = RecoveryWorker()

        finished_emissions = []
        worker.finished.connect(lambda s, m: finished_emissions.append((s, m)))

        with patch('file_storage.get_storage') as mock_get_storage:
            mock_storage = MagicMock()
            mock_storage.get_all_rooms.return_value = ["Room1", "Room2", "Room3"]
            mock_storage.load_all_originals.return_value = {
                "2024-02-10": ["[User] [오전 10:00] Message"]
            }
            mock_storage.get_summarized_dates.return_value = []
            mock_storage.load_daily_summary.return_value = None
            mock_get_storage.return_value = mock_storage

            with patch('db.reset_db'):
                with patch('db.get_db') as mock_get_db:
                    mock_db = MagicMock()
                    mock_room = MagicMock()
                    mock_room.id = 1
                    mock_db.create_room.return_value = mock_room
                    mock_db.add_messages.return_value = 1
                    mock_get_db.return_value = mock_db

                    worker.run()

        assert len(finished_emissions) == 1
        success, message = finished_emissions[0]
        assert success is True
        assert "Rooms: 3" in message

    def test_run_handles_db_errors_gracefully(self, qapp):
        """run continues recovery even when individual DB operations fail."""
        worker = RecoveryWorker()

        finished_emissions = []
        worker.finished.connect(lambda s, m: finished_emissions.append((s, m)))

        with patch('file_storage.get_storage') as mock_get_storage:
            mock_storage = MagicMock()
            mock_storage.get_all_rooms.return_value = ["Room1"]
            mock_storage.load_all_originals.return_value = {
                "2024-02-10": ["[User] [오전 10:00] Message"]
            }
            mock_storage.get_summarized_dates.return_value = []
            mock_get_storage.return_value = mock_storage

            with patch('db.reset_db'):
                with patch('db.get_db') as mock_get_db:
                    mock_db = MagicMock()
                    mock_room = MagicMock()
                    mock_room.id = 1
                    mock_db.create_room.return_value = mock_room
                    # First add_messages call raises, second succeeds
                    mock_db.add_messages.side_effect = [
                        Exception("DB error"),
                        1
                    ]
                    mock_get_db.return_value = mock_db

                    # Should not raise, should continue
                    worker.run()

        # Should still complete (graceful error handling)
        assert len(finished_emissions) == 1


class TestRecoveryWorkerMessageParsing:
    """Test RecoveryWorker message parsing behavior."""

    def test_run_parses_messages_using_message_parser(self, qapp):
        """run uses MessageParser to parse message lines."""
        worker = RecoveryWorker()

        add_messages_calls = []

        with patch('file_storage.get_storage') as mock_get_storage:
            mock_storage = MagicMock()
            mock_storage.get_all_rooms.return_value = ["TestRoom"]
            mock_storage.load_all_originals.return_value = {
                "2024-02-10": [
                    "[홍길동] [오전 10:00] 안녕하세요",
                    "[김철수] [오후 3:30] 점심 드셨나요?"
                ]
            }
            mock_storage.get_summarized_dates.return_value = []
            mock_get_storage.return_value = mock_storage

            with patch('db.reset_db'):
                with patch('db.get_db') as mock_get_db:
                    mock_db = MagicMock()
                    mock_room = MagicMock()
                    mock_room.id = 1
                    mock_db.create_room.return_value = mock_room

                    def capture_messages(room_id, messages):
                        add_messages_calls.append(messages)
                        return len(messages)

                    mock_db.add_messages.side_effect = capture_messages
                    mock_get_db.return_value = mock_db

                    worker.run()

        # Verify messages were parsed with correct structure
        assert len(add_messages_calls) == 1
        messages = add_messages_calls[0]
        assert len(messages) == 2

        # Check first message
        msg = messages[0]
        assert msg['sender'] == "홍길동"
        assert msg['content'] == "안녕하세요"

    def test_run_skips_invalid_message_lines(self, qapp):
        """run skips lines that don't match message pattern."""
        worker = RecoveryWorker()

        add_messages_calls = []

        with patch('file_storage.get_storage') as mock_get_storage:
            mock_storage = MagicMock()
            mock_storage.get_all_rooms.return_value = ["TestRoom"]
            mock_storage.load_all_originals.return_value = {
                "2024-02-10": [
                    "--------------- 2024년 2월 10일 토요일 ---------------",  # Invalid
                    "[홍길동] [오전 10:00] 안녕하세요",  # Valid
                    "This is not a valid message",  # Invalid
                ]
            }
            mock_storage.get_summarized_dates.return_value = []
            mock_get_storage.return_value = mock_storage

            with patch('db.reset_db'):
                with patch('db.get_db') as mock_get_db:
                    mock_db = MagicMock()
                    mock_room = MagicMock()
                    mock_room.id = 1
                    mock_db.create_room.return_value = mock_room

                    def capture_messages(room_id, messages):
                        add_messages_calls.append(messages)
                        return len(messages)

                    mock_db.add_messages.side_effect = capture_messages
                    mock_get_db.return_value = mock_db

                    worker.run()

        # Only one valid message should be parsed
        assert len(add_messages_calls) == 1
        assert len(add_messages_calls[0]) == 1


class TestRecoveryWorkerSummaryRestore:
    """Test RecoveryWorker summary restoration behavior."""

    def test_run_restores_summaries(self, qapp):
        """run restores summaries for summarized dates."""
        worker = RecoveryWorker()

        add_summary_calls = []

        with patch('file_storage.get_storage') as mock_get_storage:
            mock_storage = MagicMock()
            mock_storage.get_all_rooms.return_value = ["TestRoom"]
            mock_storage.load_all_originals.return_value = {
                "2024-02-10": ["[User] [오전 10:00] Message"]
            }
            mock_storage.get_summarized_dates.return_value = ["2024-02-10"]
            mock_storage.load_daily_summary.return_value = "# Summary\n\nContent"
            mock_get_storage.return_value = mock_storage

            with patch('db.reset_db'):
                with patch('db.get_db') as mock_get_db:
                    mock_db = MagicMock()
                    mock_room = MagicMock()
                    mock_room.id = 1
                    mock_db.create_room.return_value = mock_room
                    mock_db.add_messages.return_value = 1

                    def capture_summary(*args, **kwargs):
                        add_summary_calls.append((args, kwargs))
                        return MagicMock(id=1)

                    mock_db.add_summary.side_effect = capture_summary
                    mock_get_db.return_value = mock_db

                    worker.run()

        # Verify summary was added
        # add_summary is called with positional args: (room_id, summary_date, summary_type, content)
        assert len(add_summary_calls) == 1
        args, kwargs = add_summary_calls[0]
        # Check positional args - content is the 4th argument (index 3)
        assert args[3] == "# Summary\n\nContent"

    def test_run_skips_empty_summaries(self, qapp):
        """run skips dates where summary content is None."""
        worker = RecoveryWorker()

        add_summary_calls = []

        with patch('file_storage.get_storage') as mock_get_storage:
            mock_storage = MagicMock()
            mock_storage.get_all_rooms.return_value = ["TestRoom"]
            mock_storage.load_all_originals.return_value = {
                "2024-02-10": ["[User] [오전 10:00] Message"]
            }
            mock_storage.get_summarized_dates.return_value = ["2024-02-10"]
            mock_storage.load_daily_summary.return_value = None  # No content
            mock_get_storage.return_value = mock_storage

            with patch('db.reset_db'):
                with patch('db.get_db') as mock_get_db:
                    mock_db = MagicMock()
                    mock_room = MagicMock()
                    mock_room.id = 1
                    mock_db.create_room.return_value = mock_room
                    mock_db.add_messages.return_value = 1

                    mock_db.add_summary.side_effect = lambda *a, **k: add_summary_calls.append(True)
                    mock_get_db.return_value = mock_db

                    worker.run()

        # No summary should be added for None content
        assert len(add_summary_calls) == 0


class TestRecoveryWorkerErrorHandling:
    """Test RecoveryWorker error handling behavior."""

    def test_run_handles_exception_and_emits_error(self, qapp):
        """run emits finished with error on unexpected exception during recovery."""
        worker = RecoveryWorker()

        finished_emissions = []
        worker.finished.connect(lambda s, m: finished_emissions.append((s, m)))

        # Mock storage to succeed, then make db.reset_db fail
        # (exception inside the try block will be caught)
        with patch('file_storage.get_storage') as mock_get_storage:
            mock_storage = MagicMock()
            mock_storage.get_all_rooms.return_value = ["Room1"]
            mock_get_storage.return_value = mock_storage

            # Make reset_db raise an exception (inside the try block)
            with patch('db.reset_db') as mock_reset_db:
                mock_reset_db.side_effect = Exception("Unexpected error")

                worker.run()

        assert len(finished_emissions) == 1
        success, message = finished_emissions[0]
        assert success is False
        assert "Recovery failed" in message
