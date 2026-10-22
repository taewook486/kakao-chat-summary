"""Characterization tests for FileUploadWorker.

These tests capture the current behavior of the FileUploadWorker class
to ensure behavior preservation during refactoring.
"""
import pytest
from datetime import date
from unittest.mock import MagicMock, patch
from pathlib import Path

from src.workers.file_upload_worker import FileUploadWorker, MessageParser


class TestFileUploadWorkerInitialization:
    """Test FileUploadWorker initialization behavior."""

    def test_init_with_required_params(self, qapp):
        """FileUploadWorker initializes with file_path."""
        worker = FileUploadWorker(file_path="C:/path/to/chat.txt")

        assert worker.file_path == Path("C:/path/to/chat.txt")
        assert worker.room_name is None

    def test_init_with_room_name(self, qapp):
        """FileUploadWorker accepts optional room_name."""
        worker = FileUploadWorker(
            file_path="C:/path/to/chat.txt",
            room_name="My Chat Room"
        )

        assert worker.room_name == "My Chat Room"

    def test_file_path_converted_to_path(self, qapp):
        """file_path string is converted to Path object."""
        worker = FileUploadWorker(file_path="C:/path/to/chat.txt")

        assert isinstance(worker.file_path, Path)

    def test_storage_initialized_as_none(self, qapp):
        """storage is initialized as None (set in run())."""
        worker = FileUploadWorker(file_path="C:/test.txt")

        assert worker.storage is None

    def test_signals_defined(self, qapp):
        """FileUploadWorker has required signals."""
        worker = FileUploadWorker(file_path="C:/test.txt")

        assert hasattr(worker, 'progress')
        assert hasattr(worker, 'finished')
        assert hasattr(worker.progress, 'connect')
        assert hasattr(worker.finished, 'connect')

    def test_finished_signal_includes_room_id(self, qapp):
        """finished signal includes room_id parameter."""
        worker = FileUploadWorker(file_path="C:/test.txt")

        # Signal should accept 3 arguments (success, message, room_id)
        emissions = []

        def capture(success, message, room_id):
            emissions.append((success, message, room_id))

        worker.finished.connect(capture)
        worker.finished.emit(True, "Test", 42)

        assert len(emissions) == 1
        assert emissions[0] == (True, "Test", 42)


class TestFileUploadWorkerExtractRoomName:
    """Test FileUploadWorker _extract_room_name method."""

    def test_extract_from_kakao_talk_format(self, qapp, temp_dir):
        """Extract room name from KakaoTalk_YYYYMMDD_HHMM_SS_NNN_group format."""
        file_path = temp_dir / "MyRoom_KakaoTalk_20260211_1254_06_432_group.txt"
        worker = FileUploadWorker(file_path=str(file_path))

        name = worker._extract_room_name()

        assert name == "MyRoom"

    def test_extract_from_kakao_talk_prefix_only(self, qapp, temp_dir):
        """Extract returns default when only KakaoTalk_ prefix exists."""
        file_path = temp_dir / "KakaoTalk_20260211_1254_06_432_group.txt"
        worker = FileUploadWorker(file_path=str(file_path))

        name = worker._extract_room_name()

        assert name == "KakaoTalk Chat"

    def test_extract_from_simple_filename(self, qapp, temp_dir):
        """Extract returns stem for simple filenames."""
        file_path = temp_dir / "MyChat.txt"
        worker = FileUploadWorker(file_path=str(file_path))

        name = worker._extract_room_name()

        assert name == "MyChat"

    def test_extract_handles_no_extension(self, qapp, temp_dir):
        """Extract handles files without extension."""
        file_path = temp_dir / "SimpleChat"
        worker = FileUploadWorker(file_path=str(file_path))

        name = worker._extract_room_name()

        assert name == "SimpleChat"


class TestFileUploadWorkerGetOrCreateRoom:
    """Test FileUploadWorker _get_or_create_room method."""

    def test_get_existing_room(self, qapp):
        """_get_or_create_room returns existing room if found."""
        worker = FileUploadWorker(file_path="C:/test.txt")

        mock_db = MagicMock()
        existing_room = MagicMock()
        existing_room.id = 42
        mock_db.get_room_by_name.return_value = existing_room

        room = worker._get_or_create_room("Existing Room", mock_db)

        assert room.id == 42
        mock_db.get_room_by_name.assert_called_once_with("Existing Room")
        mock_db.create_room.assert_not_called()

    def test_create_new_room(self, qapp):
        """_get_or_create_room creates new room if not found."""
        worker = FileUploadWorker(file_path="C:/path/to/chat.txt")

        mock_db = MagicMock()
        mock_db.get_room_by_name.return_value = None
        new_room = MagicMock()
        new_room.id = 1
        mock_db.create_room.return_value = new_room

        room = worker._get_or_create_room("New Room", mock_db)

        assert room.id == 1
        # Verify room_name and file_path were passed (Windows paths)
        mock_db.create_room.assert_called_once()
        call_args = mock_db.create_room.call_args[0]
        assert call_args[0] == "New Room"


class TestFileUploadWorkerRunBehavior:
    """Test FileUploadWorker run method behavior (characterization tests)."""

    def test_run_emits_progress_signals(self, qapp, sample_chat_file):
        """run emits progress signals during upload."""
        worker = FileUploadWorker(file_path=str(sample_chat_file))

        progress_emissions = []
        worker.progress.connect(lambda p, m: progress_emissions.append((p, m)))

        with patch.object(worker, '_create_worker_db') as mock_create_db:
            mock_db = MagicMock()
            mock_room = MagicMock()
            mock_room.id = 1
            mock_db.get_room_by_name.return_value = None
            mock_db.create_room.return_value = mock_room
            mock_db.add_messages.return_value = 5
            mock_db.update_room_sync_time = MagicMock()
            mock_db.add_sync_log = MagicMock()
            mock_create_db.return_value = mock_db

            worker.run()

        # Verify multiple progress emissions
        assert len(progress_emissions) > 0
        # Should emit 100% at completion
        assert any(p == 100 for p, m in progress_emissions)

    def test_run_emits_finished_on_success(self, qapp, sample_chat_file):
        """run emits finished signal with success on completion."""
        worker = FileUploadWorker(file_path=str(sample_chat_file))

        finished_emissions = []
        worker.finished.connect(lambda s, m, r: finished_emissions.append((s, m, r)))

        with patch.object(worker, '_create_worker_db') as mock_create_db:
            mock_db = MagicMock()
            mock_room = MagicMock()
            mock_room.id = 42
            mock_db.get_room_by_name.return_value = None
            mock_db.create_room.return_value = mock_room
            mock_db.add_messages.return_value = 5
            mock_db.update_room_sync_time = MagicMock()
            mock_db.add_sync_log = MagicMock()
            mock_create_db.return_value = mock_db

            worker.run()

        assert len(finished_emissions) == 1
        success, message, room_id = finished_emissions[0]
        assert success is True
        assert room_id == 42
        assert "File:" in message

    def test_run_emits_finished_on_error(self, qapp, temp_dir):
        """run emits finished signal with error on failure."""
        non_existent = temp_dir / "nonexistent.txt"
        worker = FileUploadWorker(file_path=str(non_existent))

        finished_emissions = []
        worker.finished.connect(lambda s, m, r: finished_emissions.append((s, m, r)))

        with patch.object(worker, '_create_worker_db') as mock_create_db:
            mock_db = MagicMock()
            mock_create_db.return_value = mock_db

            worker.run()

        assert len(finished_emissions) == 1
        success, message, room_id = finished_emissions[0]
        assert success is False
        assert room_id == -1
        assert "Error:" in message

    def test_run_uses_provided_room_name(self, qapp, sample_chat_file):
        """run uses provided room_name instead of extracting from file."""
        worker = FileUploadWorker(
            file_path=str(sample_chat_file),
            room_name="Custom Room Name"
        )

        finished_emissions = []
        worker.finished.connect(lambda s, m, r: finished_emissions.append((s, m, r)))

        with patch.object(worker, '_create_worker_db') as mock_create_db:
            mock_db = MagicMock()
            mock_room = MagicMock()
            mock_room.id = 1
            mock_db.get_room_by_name.return_value = None
            mock_db.create_room.return_value = mock_room
            mock_db.add_messages.return_value = 5
            mock_db.update_room_sync_time = MagicMock()
            mock_db.add_sync_log = MagicMock()
            mock_create_db.return_value = mock_db

            worker.run()

        # Verify custom room name was used
        mock_db.create_room.assert_called_once()
        call_args = mock_db.create_room.call_args[0]
        assert call_args[0] == "Custom Room Name"

    def test_run_disposes_db_in_finally(self, qapp, sample_chat_file):
        """run disposes database in finally block when error occurs in try block."""
        worker = FileUploadWorker(file_path=str(sample_chat_file))

        finished_emissions = []
        worker.finished.connect(lambda s, m, r: finished_emissions.append((s, m, r)))

        with patch.object(worker, '_create_worker_db') as mock_create_db:
            mock_db = MagicMock()
            mock_db.engine.dispose = MagicMock()
            mock_create_db.return_value = mock_db

            # Mock storage to work initially, then cause error in try block
            with patch('file_storage.get_storage') as mock_get_storage:
                mock_storage = MagicMock()
                # get_original_file_size raises error inside try block
                mock_storage.get_original_file_size.side_effect = Exception("Storage error")
                mock_storage.save_all_daily_originals.return_value = ["2024-02-10"]
                mock_get_storage.return_value = mock_storage

                worker.run()

            # Verify dispose was called even with error
            mock_db.engine.dispose.assert_called()
            # Verify finished was emitted with error
            assert len(finished_emissions) == 1
            success, message, room_id = finished_emissions[0]
            assert success is False
            assert "Error:" in message


class TestFileUploadWorkerMessageProcessing:
    """Test FileUploadWorker message processing behavior."""

    def test_run_processes_messages_by_date(self, qapp, temp_dir):
        """run processes and saves messages grouped by date."""
        # Create a chat file with multiple dates
        chat_content = """KakaoTalk Chat Export
---------------------

--------------- 2024년 2월 10일 토요일 ---------------
[홍길동] [오전 10:00] 안녕하세요
[김철수] [오전 10:05] 반갑습니다

--------------- 2024년 2월 11일 일요일 ---------------
[이영희] [오후 2:00] 점심 드셨나요?
"""
        chat_file = temp_dir / "multi_date.txt"
        chat_file.write_text(chat_content, encoding="utf-8")

        worker = FileUploadWorker(file_path=str(chat_file))

        add_messages_calls = []

        with patch.object(worker, '_create_worker_db') as mock_create_db:
            mock_db = MagicMock()
            mock_room = MagicMock()
            mock_room.id = 1
            mock_db.get_room_by_name.return_value = None
            mock_db.create_room.return_value = mock_room

            def capture_messages(room_id, messages):
                add_messages_calls.append({
                    'room_id': room_id,
                    'count': len(messages),
                    'dates': set(m['date'] for m in messages) if messages else set()
                })
                return len(messages)

            mock_db.add_messages.side_effect = capture_messages
            mock_db.update_room_sync_time = MagicMock()
            mock_db.add_sync_log = MagicMock()
            mock_create_db.return_value = mock_db

            worker.run()

        # Verify messages were processed for multiple dates
        assert len(add_messages_calls) >= 1


class TestFileUploadWorkerSyncLog:
    """Test FileUploadWorker sync log behavior."""

    def test_run_adds_sync_log(self, qapp, sample_chat_file):
        """run adds sync log entry after upload."""
        worker = FileUploadWorker(file_path=str(sample_chat_file))

        with patch.object(worker, '_create_worker_db') as mock_create_db:
            mock_db = MagicMock()
            mock_room = MagicMock()
            mock_room.id = 1
            mock_db.get_room_by_name.return_value = None
            mock_db.create_room.return_value = mock_room
            mock_db.add_messages.return_value = 5
            mock_db.update_room_sync_time = MagicMock()
            mock_create_db.return_value = mock_db

            worker.run()

        mock_db.add_sync_log.assert_called_once()
        call_kwargs = mock_db.add_sync_log.call_args[1]
        assert call_kwargs['message_count'] >= 0
        assert 'new_message_count' in call_kwargs
