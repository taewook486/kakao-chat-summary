"""Unit tests for ChatRoomListManager.

Tests for the extracted ChatRoomListManager class that handles
room list UI and operations.
"""

import pytest
from datetime import datetime, date
from unittest.mock import Mock, MagicMock, patch
from pathlib import Path

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QMessageBox
from PySide6.QtCore import Qt

from src.ui.managers.chat_room_list_manager import (
    ChatRoomListManager,
    ChatRoomWidget
)
from src.repositories.chat_room_repository import ChatRoomRepository
from src.repositories.message_repository import MessageRepository
from src.repositories.summary_repository import SummaryRepository
from src.services.chat_service import ChatService
from src.db.models import ChatRoom


@pytest.mark.unit
class TestChatRoomListManager:
    """Unit tests for ChatRoomListManager."""

    @pytest.fixture
    def manager_deps(self, db_session, qapp, file_storage):
        """Create dependencies for ChatRoomListManager."""
        parent = QWidget()

        chat_room_repo = ChatRoomRepository(db_session)
        message_repo = MessageRepository(db_session)
        summary_repo = SummaryRepository(db_session)

        sync_log_repo = MagicMock()
        chat_service = ChatService(
            chat_room_repo=chat_room_repo,
            message_repo=message_repo,
            sync_log_repo=sync_log_repo,
            file_storage=file_storage,
        )

        return {
            "parent": parent,
            "chat_room_repo": chat_room_repo,
            "message_repo": message_repo,
            "summary_repo": summary_repo,
            "chat_service": chat_service,
            "storage": file_storage,
        }

    @pytest.fixture
    def manager(self, manager_deps):
        """Create ChatRoomListManager with test dependencies."""
        return ChatRoomListManager(
            parent=manager_deps["parent"],
            chat_room_repo=manager_deps["chat_room_repo"],
            message_repo=manager_deps["message_repo"],
            summary_repo=manager_deps["summary_repo"],
            chat_service=manager_deps["chat_service"],
            storage=manager_deps["storage"],
        )

    def test_initial_state(self, manager):
        """Test manager initial state."""
        assert manager.current_room_id is None
        assert manager.current_room_file is None

    def test_room_list_widget_created(self, manager):
        """Test room list widget is created lazily."""
        widget = manager.room_list_widget

        assert widget is not None
        assert isinstance(widget, QWidget)

    def test_load_rooms_empty(self, manager):
        """Test loading rooms with empty database."""
        # Access room_list_widget first to create layout
        _ = manager.room_list_widget
        manager.load_rooms()

        # Widget should be created
        assert manager._room_list_layout is not None

    def test_load_rooms_with_data(self, manager, manager_deps):
        """Test loading rooms with data."""
        # Create test rooms
        repo = manager_deps["chat_room_repo"]
        repo.create(name="Room 1")
        repo.create(name="Room 2")

        # Access room_list_widget first to create layout
        _ = manager.room_list_widget
        manager.load_rooms()

        # Layout should have widgets (rooms + stretch)
        assert manager._room_list_layout.count() >= 2

    def test_select_room(self, manager, manager_deps):
        """Test room selection."""
        repo = manager_deps["chat_room_repo"]
        room = repo.create(name="Selected Room", file_path="/path/to/file.txt")

        # Track signal emission
        signal_received = []
        manager.room_selected.connect(
            lambda rid, name, path: signal_received.append((rid, name, path))
        )

        manager.select_room(room.id, room.file_path)

        assert manager.current_room_id == room.id
        assert manager.current_room_file == room.file_path
        assert len(signal_received) == 1

    def test_clear_selection(self, manager, manager_deps):
        """Test clearing room selection."""
        repo = manager_deps["chat_room_repo"]
        room = repo.create(name="Clear Test Room")

        manager.select_room(room.id, "/path/file.txt")
        assert manager.current_room_id is not None

        manager.clear_selection()
        assert manager.current_room_id is None
        assert manager.current_room_file is None

    def test_get_room_statistics(self, manager, manager_deps):
        """Test getting room statistics."""
        repo = manager_deps["chat_room_repo"]
        room = repo.create(name="Stats Room")

        stats = manager.get_room_statistics(room.id)

        assert stats is not None
        assert "room_name" in stats

    def test_get_room_summaries(self, manager, manager_deps):
        """Test getting room summaries."""
        repo = manager_deps["chat_room_repo"]
        room = repo.create(name="Summaries Room")

        summaries = manager.get_room_summaries(room.id)

        assert isinstance(summaries, list)

    def test_create_room_success(self, manager, manager_deps):
        """Test successful room creation."""
        # Track signal
        signal_received = []
        manager.room_created.connect(
            lambda rid, name: signal_received.append((rid, name))
        )

        room_id = manager.create_room("New Test Room")

        assert room_id is not None
        assert room_id > 0
        assert len(signal_received) == 1

    def test_create_room_duplicate(self, manager, manager_deps):
        """Test creating duplicate room returns None."""
        manager.create_room("Duplicate Room")

        # Try to create same room again
        room_id = manager.create_room("Duplicate Room")

        assert room_id is None

    def test_delete_room(self, manager, manager_deps):
        """Test room deletion."""
        repo = manager_deps["chat_room_repo"]
        room = repo.create(name="Delete Test Room")

        # Select the room first
        manager.select_room(room.id, room.file_path)

        # Mock QMessageBox to auto-confirm
        with patch('src.ui.managers.chat_room_list_manager.QMessageBox.question') as mock_question:
            mock_question.return_value = QMessageBox.Yes

            result = manager.delete_room(room.id)

            # Verify deletion succeeded
            assert result is True
            assert manager.current_room_id is None

    def test_recover_missing_rooms_none_missing(self, manager, manager_deps):
        """Test recovery when no rooms are missing."""
        # Mock QMessageBox
        with patch('src.ui.managers.chat_room_list_manager.QMessageBox.information') as mock_info:
            result = manager.recover_missing_rooms()

            # Should show "no missing rooms" message
            assert mock_info.called
            assert result == 0

    def test_backup_room_no_selection(self, manager):
        """Test backup with no room selected."""
        with patch('src.ui.managers.chat_room_list_manager.QMessageBox.warning') as mock_warn:
            result = manager.backup_room(None)

            assert result is None
            assert mock_warn.called

    def test_create_scroll_area(self, manager):
        """Test scroll area creation."""
        scroll = manager.create_scroll_area()

        assert scroll is not None
        assert scroll.widgetResizable() is True


@pytest.mark.unit
class TestChatRoomWidget:
    """Unit tests for ChatRoomWidget."""

    def test_widget_creation(self, qapp):
        """Test widget is created correctly."""
        widget = ChatRoomWidget(
            room_id=1,
            name="Test Room",
            message_count=100,
            new_count=5,
            file_path="/test/path.txt"
        )

        assert widget.room_id == 1
        assert widget.file_path == "/test/path.txt"

    def test_widget_with_sync_time(self, qapp):
        """Test widget with sync time."""
        sync_time = datetime(2024, 2, 15, 14, 30)

        widget = ChatRoomWidget(
            room_id=2,
            name="Synced Room",
            message_count=500,
            last_sync=sync_time,
            file_path="/synced/path.txt"
        )

        assert widget.room_id == 2

    def test_widget_signal_defined(self, qapp):
        """Test widget has clicked signal."""
        widget = ChatRoomWidget(
            room_id=3,
            name="Signal Test",
            message_count=0
        )

        # Verify signal exists
        assert hasattr(widget, 'clicked')

    def test_widget_properties(self, qapp):
        """Test widget properties are set correctly."""
        widget = ChatRoomWidget(
            room_id=42,
            name="Properties Test",
            message_count=999,
            new_count=10,
            file_path="/properties/test.txt"
        )

        assert widget.room_id == 42
        assert widget.file_path == "/properties/test.txt"
