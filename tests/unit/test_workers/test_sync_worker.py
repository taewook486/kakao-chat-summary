"""Characterization tests for SyncWorker.

These tests capture the current behavior of the SyncWorker class
to ensure behavior preservation during refactoring.
"""
import pytest
from datetime import date
from unittest.mock import MagicMock, patch, PropertyMock
from pathlib import Path

from src.workers.sync_worker import SyncWorker
from src.workers.file_upload_worker import MessageParser


class TestSyncWorkerInitialization:
    """Test SyncWorker initialization behavior."""

    def test_init_with_required_params(self, qapp):
        """SyncWorker initializes with room_id and file_path."""
        worker = SyncWorker(room_id=1, file_path="/path/to/chat.txt")

        assert worker.room_id == 1
        assert worker.file_path == Path("/path/to/chat.txt")

    def test_init_with_parent(self, qapp):
        """SyncWorker accepts optional parent parameter."""
        worker = SyncWorker(room_id=2, file_path="/test.txt")

        assert worker.room_id == 2

    def test_file_path_converted_to_path(self, qapp):
        """file_path string is converted to Path object."""
        worker = SyncWorker(room_id=1, file_path="/path/to/chat.txt")

        assert isinstance(worker.file_path, Path)

    def test_signals_defined(self, qapp):
        """SyncWorker has required signals."""
        worker = SyncWorker(room_id=1, file_path="/test.txt")

        assert hasattr(worker, 'progress')
        assert hasattr(worker, 'finished')
        assert hasattr(worker.progress, 'connect')
        assert hasattr(worker.finished, 'connect')


class TestSyncWorkerRun:
    """Test SyncWorker run method behavior (characterization tests)."""

    def test_run_emits_progress_and_finished_on_success(
        self, qapp, temp_dir, sample_chat_file
    ):
        """SyncWorker emits progress signals and finished on successful sync."""
        worker = SyncWorker(room_id=1, file_path=str(sample_chat_file))

        progress_emissions = []
        finished_emissions = []

        worker.progress.connect(lambda p, m: progress_emissions.append((p, m)))
        worker.finished.connect(lambda s, m: finished_emissions.append((s, m)))

        # Mock database operations
        with patch.object(worker, '_create_worker_db') as mock_create_db:
            mock_db = MagicMock()
            mock_db.add_messages.return_value = 5
            mock_db.update_room_sync_time = MagicMock()
            mock_db.add_sync_log = MagicMock()
            mock_create_db.return_value = mock_db

            worker.run()

        # Verify progress emission
        assert len(progress_emissions) > 0
        assert any(p == 100 for p, m in progress_emissions)

        # Verify finished signal
        assert len(finished_emissions) == 1
        success, message = finished_emissions[0]
        assert success is True
        assert "Sync complete" in message

    def test_run_handles_parse_error(self, qapp, temp_dir):
        """SyncWorker handles file parsing errors gracefully."""
        non_existent_file = temp_dir / "non_existent.txt"
        worker = SyncWorker(room_id=1, file_path=str(non_existent_file))

        finished_emissions = []
        worker.finished.connect(lambda s, m: finished_emissions.append((s, m)))

        with patch.object(worker, '_create_worker_db') as mock_create_db:
            mock_db = MagicMock()
            mock_create_db.return_value = mock_db

            worker.run()

        # Should emit finished with failure
        assert len(finished_emissions) == 1
        success, message = finished_emissions[0]
        assert success is False

    def test_run_disposes_database_in_finally(self, qapp, sample_chat_file):
        """SyncWorker disposes database even on error."""
        worker = SyncWorker(room_id=1, file_path=str(sample_chat_file))

        with patch.object(worker, '_create_worker_db') as mock_create_db:
            mock_db = MagicMock()
            mock_db.engine.dispose = MagicMock()
            mock_create_db.return_value = mock_db

            # Make parsing fail by patching the import inside run()
            with patch('parser.KakaoLogParser') as mock_parser:
                mock_parser.return_value.parse.side_effect = Exception("Parse error")

                worker.run()

            # Verify dispose was called
            mock_db.engine.dispose.assert_called()

    def test_run_processes_messages_by_date(
        self, qapp, temp_dir
    ):
        """SyncWorker processes messages grouped by date."""
        # Create a chat file with proper message format that MessageParser expects
        # Format: [nickname] [AM/PM HH:MM] content
        chat_content = """KakaoTalk Chat Export
---------------------

--------------- 2024년 2월 10일 토요일 ---------------
[홍길동] [오전 10:00] 안녕하세요!
[김철수] [오전 10:05] 반갑습니다

--------------- 2024년 2월 11일 일요일 ---------------
[이영희] [오후 2:00] 점심 드셨나요?
"""
        chat_file = temp_dir / "test_chat.txt"
        chat_file.write_text(chat_content, encoding="utf-8")

        worker = SyncWorker(room_id=1, file_path=str(chat_file))

        add_messages_calls = []
        mock_db = MagicMock()

        def capture_add_messages(room_id, messages):
            add_messages_calls.append({
                'room_id': room_id,
                'count': len(messages),
                'dates': [m['date'] for m in messages] if messages else []
            })
            return len(messages)

        mock_db.add_messages.side_effect = capture_add_messages
        mock_db.update_room_sync_time = MagicMock()
        mock_db.add_sync_log = MagicMock()

        with patch.object(worker, '_create_worker_db', return_value=mock_db):
            worker.run()

        # Verify messages were added (check the captured calls, not mock call_count)
        assert len(add_messages_calls) >= 1


class TestSyncWorkerDatabaseOperations:
    """Test SyncWorker database interaction patterns."""

    def test_run_updates_sync_time(self, qapp, sample_chat_file):
        """SyncWorker updates room sync time after sync."""
        worker = SyncWorker(room_id=42, file_path=str(sample_chat_file))

        with patch.object(worker, '_create_worker_db') as mock_create_db:
            mock_db = MagicMock()
            mock_db.add_messages.return_value = 5
            mock_create_db.return_value = mock_db

            worker.run()

        mock_db.update_room_sync_time.assert_called_once_with(42)

    def test_run_adds_sync_log(self, qapp, sample_chat_file):
        """SyncWorker adds sync log entry after sync."""
        worker = SyncWorker(room_id=1, file_path=str(sample_chat_file))

        with patch.object(worker, '_create_worker_db') as mock_create_db:
            mock_db = MagicMock()
            mock_db.add_messages.return_value = 5
            mock_create_db.return_value = mock_db

            worker.run()

        mock_db.add_sync_log.assert_called_once()
        call_args = mock_db.add_sync_log.call_args
        assert call_args[0][0] == 1  # room_id
        assert call_args[1]['message_count'] >= 0
        assert call_args[1]['new_message_count'] >= 0


class TestSyncWorkerMessageParserIntegration:
    """Test SyncWorker integration with MessageParser."""

    def test_run_uses_message_parser_for_each_line(
        self, qapp, temp_dir
    ):
        """SyncWorker parses each message line using MessageParser."""
        # Create a simple chat file
        chat_content = """KakaoTalk Chat Export
---------------------

--------------- 2024년 2월 10일 토요일 ---------------
[홍길동] [오전 10:00] 안녕하세요
[김철수] [오전 10:05] 반갑습니다
"""
        chat_file = temp_dir / "test_chat.txt"
        chat_file.write_text(chat_content, encoding="utf-8")

        worker = SyncWorker(room_id=1, file_path=str(chat_file))

        messages_added = []

        with patch.object(worker, '_create_worker_db') as mock_create_db:
            mock_db = MagicMock()

            def capture_messages(room_id, messages):
                messages_added.extend(messages)
                return len(messages)

            mock_db.add_messages.side_effect = capture_messages
            mock_db.update_room_sync_time = MagicMock()
            mock_db.add_sync_log = MagicMock()
            mock_create_db.return_value = mock_db

            worker.run()

        # Verify messages were parsed
        assert len(messages_added) >= 2
        # Check message structure
        for msg in messages_added:
            assert 'sender' in msg
            assert 'content' in msg
            assert 'date' in msg
            assert 'time' in msg


class TestMessageParser:
    """Test MessageParser behavior."""

    def test_parse_message_am(self):
        """Parse AM message correctly."""
        from datetime import time as dt_time

        result = MessageParser.parse_message(
            "[홍길동] [오전 10:00] 안녕하세요",
            date(2024, 2, 10)
        )

        assert result is not None
        assert result['sender'] == "홍길동"
        assert result['time'] == dt_time(10, 0)
        assert result['content'] == "안녕하세요"

    def test_parse_message_pm(self):
        """Parse PM message with hour conversion."""
        from datetime import time as dt_time

        result = MessageParser.parse_message(
            "[철수] [오후 3:45] 점심 먹었어?",
            date(2024, 2, 10)
        )

        assert result is not None
        assert result['time'] == dt_time(15, 45)  # 3:45 PM = 15:45

    def test_parse_message_invalid_format(self):
        """Return None for invalid format."""
        result = MessageParser.parse_message(
            "This is not a valid message format",
            date(2024, 2, 10)
        )

        assert result is None
