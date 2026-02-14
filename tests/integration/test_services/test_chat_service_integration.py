"""Integration tests for ChatService."""

import pytest
from datetime import date
from pathlib import Path

from src.services.chat_service import ChatService
from src.repositories.chat_room_repository import ChatRoomRepository
from src.repositories.message_repository import MessageRepository
from src.repositories.sync_log_repository import SyncLogRepository


@pytest.mark.integration
class TestChatServiceIntegration:
    """Integration tests for ChatService with real database operations."""

    @pytest.fixture
    def repositories(self, db_session):
        """Create all required repositories."""
        chat_room_repo = ChatRoomRepository(db_session)
        message_repo = MessageRepository(db_session)
        sync_log_repo = SyncLogRepository(db_session)
        return {
            "chat_room_repo": chat_room_repo,
            "message_repo": message_repo,
            "sync_log_repo": sync_log_repo,
        }

    @pytest.fixture
    def service(self, repositories, temp_dir):
        """Create ChatService with mocked file storage."""
        from src.file_storage import FileStorage

        # Create FileStorage with temp directory
        file_storage = FileStorage()
        file_storage.base_dir = temp_dir
        file_storage.original_dir = temp_dir / "original"
        file_storage.original_dir.mkdir(parents=True, exist_ok=True)

        service = ChatService(
            chat_room_repo=repositories["chat_room_repo"],
            message_repo=repositories["message_repo"],
            sync_log_repo=repositories["sync_log_repo"],
            file_storage=file_storage,
        )
        return service

    def test_upload_and_parse_new_chat_file(self, service, sample_chat_file):
        """Test uploading and parsing a new chat file."""
        # When: Upload new chat file
        result = service.upload_and_parse_chat_file(
            room_name="Test Room",
            file_path=str(sample_chat_file),
        )

        # Then: Upload succeeds
        assert result["success"] is True
        assert result["room_id"] is not None
        assert result["message_count"] > 0
        assert result["error"] is None

    def test_upload_creates_new_room(self, service, sample_chat_file, db_session):
        """Test that uploading creates a new chat room."""
        # Given: Room doesn't exist
        chat_room_repo = ChatRoomRepository(db_session)
        room_before = chat_room_repo.get_by_name("New Room")
        assert room_before is None

        # When: Upload file for new room
        result = service.upload_and_parse_chat_file(
            room_name="New Room",
            file_path=str(sample_chat_file),
        )

        # Then: Room is created
        room_after = chat_room_repo.get_by_name("New Room")
        assert room_after is not None
        assert room_after.name == "New Room"
        assert result["room_id"] == room_after.id

    def test_upload_reuses_existing_room(self, service, sample_chat_file, db_session):
        """Test that uploading to existing room reuses it."""
        # Given: Existing room
        chat_room_repo = ChatRoomRepository(db_session)
        existing_room = chat_room_repo.create(name="Existing Room")

        # When: Upload file to existing room
        result = service.upload_and_parse_chat_file(
            room_name="Existing Room",
            file_path=str(sample_chat_file),
        )

        # Then: Existing room is used
        assert result["room_id"] == existing_room.id

    def test_upload_saves_to_file_storage(self, service, sample_chat_file):
        """Test that upload saves to file storage."""
        # When: Upload file
        result = service.upload_and_parse_chat_file(
            room_name="File Storage Test",
            file_path=str(sample_chat_file),
        )

        # Then: Files are saved
        assert result["success"] is True

        # Check that files exist in storage
        available_dates = service.file_storage.get_available_dates("File Storage Test")
        assert len(available_dates) > 0

    def test_upload_records_sync_log(self, service, sample_chat_file):
        """Test that upload creates sync log entry."""
        # When: Upload file
        result = service.upload_and_parse_chat_file(
            room_name="Sync Log Test",
            file_path=str(sample_chat_file),
        )

        # Then: Sync log is created
        assert result["success"] is True

        # Get sync logs for the room
        sync_logs = service.sync_log_repo.get_logs_by_room(result["room_id"])
        assert len(sync_logs) > 0
        assert sync_logs[0].status == "success"

    def test_upload_nonexistent_file(self, service):
        """Test uploading a non-existent file."""
        # When: Upload non-existent file
        result = service.upload_and_parse_chat_file(
            room_name="Test Room",
            file_path="/nonexistent/file.txt",
        )

        # Then: Upload fails gracefully
        assert result["success"] is False
        assert result["error"] is not None
        assert "not found" in result["error"].lower()

    def test_get_room_statistics(self, service, sample_chat_file):
        """Test getting room statistics."""
        # Given: Room with data
        upload_result = service.upload_and_parse_chat_file(
            room_name="Stats Test Room",
            file_path=str(sample_chat_file),
        )

        # When: Get statistics
        stats = service.get_room_statistics(upload_result["room_id"])

        # Then: Statistics are returned
        assert isinstance(stats, dict)
        assert "total_messages" in stats
        assert "room_name" in stats
        assert stats["room_name"] == "Stats Test Room"

    def test_sync_room_from_file(self, service, sample_chat_file):
        """Test syncing existing room from file."""
        # Given: Existing room
        upload_result = service.upload_and_parse_chat_file(
            room_name="Sync Test Room",
            file_path=str(sample_chat_file),
        )
        room_id = upload_result["room_id"]

        # When: Sync from file again
        sync_result = service.sync_room_from_file(
            room_id=room_id,
            file_path=str(sample_chat_file),
        )

        # Then: Sync succeeds
        assert sync_result["success"] is True
        assert sync_result["message_count"] >= 0

    def test_sync_nonexistent_room(self, service, sample_chat_file):
        """Test syncing a non-existent room."""
        # When: Sync non-existent room
        result = service.sync_room_from_file(
            room_id=99999,
            file_path=str(sample_chat_file),
        )

        # Then: Sync fails
        assert result["success"] is False
        assert result["error"] is not None

    def test_get_room_statistics_nonexistent_room(self, service):
        """Test getting statistics for non-existent room."""
        # When: Get stats for non-existent room
        stats = service.get_room_statistics(99999)

        # Then: Empty dict is returned
        assert stats == {}

    def test_message_extraction_from_lines(self, service):
        """Test internal message extraction logic."""
        # Given: Sample message lines
        message_lines = [
            "--------------- [오전 10:00] 홍길동: 안녕하세요",
            "--------------- [오전 10:05] 김철수: 네 안녕하세요",
        ]
        test_date = date(2024, 2, 10)

        # When: Extract message data
        messages = service._extract_message_data(message_lines, test_date)

        # Then: Messages are extracted correctly
        assert len(messages) == 2
        assert messages[0]["sender"] == "홍길동"
        assert messages[0]["content"] == "안녕하세요"
        assert messages[1]["sender"] == "김철수"
        assert messages[1]["content"] == "네 안녕하세요"
