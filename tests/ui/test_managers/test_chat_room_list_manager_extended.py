"""Extended tests for ChatRoomListManager (P1 Coverage Gaps).

This test file covers previously untested lines in chat_room_list_manager.py:
- ChatRoomWidget.mousePressEvent (2 missing lines)
- ChatRoomListManager.load_rooms edge cases (3 missing lines)
- ChatRoomListManager.create_room edge cases (3 missing lines)
- ChatRoomListManager.delete_room edge cases (6 missing lines)
- ChatRoomListManager.recover_missing_rooms (12 missing lines)
- ChatRoomListManager.backup_room (9 missing lines)

@MX:NOTE: Extended tests for ChatRoomListManager coverage improvement
@MX:SPEC: SPEC-IMPROVE-001 Milestone 2.1
Target Coverage: 85%+
Current Coverage: 81.7%
"""

import pytest
from datetime import datetime, date
from unittest.mock import Mock, MagicMock, patch, call
from pathlib import Path
from PySide6.QtCore import Qt, QEvent
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QMessageBox

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
class TestChatRoomWidgetMousePressEvent:
    """Tests for ChatRoomWidget.mousePressEvent method (2 missing lines)."""

    def test_mouse_press_event_emits_clicked_signal(self, qapp):
        """Test mousePressEvent emits clicked signal with room_id and file_path."""
        widget = ChatRoomWidget(
            room_id=42,
            name="Test Room",
            message_count=100,
            file_path="/test/path.txt"
        )

        # Track signal emission
        signal_received = []
        widget.clicked.connect(lambda rid, path: signal_received.append((rid, path)))

        # Simulate mouse press event
        mouse_event = QMouseEvent(
            QEvent.MouseButtonPress,
            widget.pos(),
            Qt.LeftButton,
            Qt.LeftButton,
            Qt.NoModifier
        )
        widget.mousePressEvent(mouse_event)

        # Verify signal was emitted
        assert len(signal_received) == 1
        assert signal_received[0] == (42, "/test/path.txt")

    def test_mouse_press_event_calls_super(self, qapp):
        """Test mousePressEvent calls parent class implementation."""
        widget = ChatRoomWidget(
            room_id=1,
            name="Super Test",
            message_count=50
        )

        # Signal should still work
        signal_received = []
        widget.clicked.connect(lambda: signal_received.append(True))

        mouse_event = QMouseEvent(
            QEvent.MouseButtonPress,
            widget.pos(),
            Qt.LeftButton,
            Qt.LeftButton,
            Qt.NoModifier
        )

        # Should not raise exception
        widget.mousePressEvent(mouse_event)

        # Signal should be emitted
        assert len(signal_received) == 1

    def test_mouse_press_event_with_empty_file_path(self, qapp):
        """Test mousePressEvent with empty file_path."""
        widget = ChatRoomWidget(
            room_id=99,
            name="Empty Path Room",
            message_count=0,
            file_path=""
        )

        signal_received = []
        widget.clicked.connect(lambda rid, path: signal_received.append((rid, path)))

        mouse_event = QMouseEvent(
            QEvent.MouseButtonPress,
            widget.pos(),
            Qt.LeftButton,
            Qt.LeftButton,
            Qt.NoModifier
        )
        widget.mousePressEvent(mouse_event)

        assert len(signal_received) == 1
        assert signal_received[0] == (99, "")


@pytest.mark.unit
class TestChatRoomListManagerLoadRoomsEdgeCases:
    """Tests for ChatRoomListManager.load_rooms edge cases (3 missing lines)."""

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

    def test_load_rooms_with_empty_database_shows_placeholder(self, manager):
        """Test load_rooms shows placeholder when database is empty."""
        # Access room_list_widget first to create layout
        _ = manager.room_list_widget
        manager.load_rooms()

        # Should have empty placeholder message
        layout = manager._room_list_layout
        assert layout is not None

        # Find the placeholder label
        found_placeholder = False
        for i in range(layout.count()):
            item = layout.itemAt(i)
            if item and item.widget():
                widget = item.widget()
                if isinstance(widget, QLabel):
                    text = widget.text()
                    if "Please add chat room" in text or "Folder" in text:
                        found_placeholder = True
                        break

        assert found_placeholder, "Placeholder label should be shown for empty room list"

    def test_load_rooms_emits_rooms_loaded_signal(self, manager, manager_deps):
        """Test load_rooms emits rooms_loaded signal."""
        signal_received = []
        manager.rooms_loaded.connect(lambda: signal_received.append(True))

        # Create a room first
        repo = manager_deps["chat_room_repo"]
        repo.create(name="Test Room")

        # Load rooms
        _ = manager.room_list_widget
        manager.load_rooms()

        # Verify signal was emitted
        assert len(signal_received) == 1

    def test_load_rooms_returns_early_when_layout_is_none(self, manager):
        """Test load_rooms returns early if room_list_layout is None."""
        # Don't access room_list_widget, so layout stays None
        assert manager._room_list_layout is None

        # Should not raise exception
        manager.load_rooms()

        # Layout should still be None (early return)
        assert manager._room_list_layout is None


@pytest.mark.unit
class TestChatRoomListManagerCreateRoomEdgeCases:
    """Tests for ChatRoomListManager.create_room edge cases (3 missing lines)."""

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

    def test_create_room_creates_storage_directories(self, manager, manager_deps):
        """Test create_room creates storage directories."""
        room_name = "New Test Room"
        storage = manager_deps["storage"]

        # Mock QMessageBox
        with patch('src.ui.managers.chat_room_list_manager.QMessageBox.warning'):
            room_id = manager.create_room(room_name)

        assert room_id is not None

        # Verify directories were created
        sanitized = storage._sanitize_name(room_name)
        original_dir = storage.original_dir / sanitized
        summary_dir = storage.summary_dir / sanitized

        assert original_dir.exists()
        assert summary_dir.exists()

    def test_create_room_emits_room_created_signal(self, manager, manager_deps):
        """Test create_room emits room_created signal."""
        signal_received = []
        manager.room_created.connect(lambda rid, name: signal_received.append((rid, name)))

        with patch('src.ui.managers.chat_room_list_manager.QMessageBox.warning'):
            room_id = manager.create_room("Signal Test Room")

        assert len(signal_received) == 1
        assert signal_received[0][0] == room_id
        assert signal_received[0][1] == "Signal Test Room"

    def test_create_room_calls_load_rooms(self, manager, manager_deps):
        """Test create_room calls load_rooms to refresh the list."""
        # Track load_rooms call
        original_load_rooms = manager.load_rooms
        load_rooms_called = []

        def mock_load_rooms():
            load_rooms_called.append(True)
            return original_load_rooms()

        manager.load_rooms = mock_load_rooms

        with patch('src.ui.managers.chat_room_list_manager.QMessageBox.warning'):
            manager.create_room("Refresh Test Room")

        # Verify load_rooms was called
        assert len(load_rooms_called) == 1


@pytest.mark.unit
class TestChatRoomListManagerDeleteRoomEdgeCases:
    """Tests for ChatRoomListManager.delete_room edge cases (6 missing lines)."""

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

    def test_delete_room_clears_current_selection(self, manager, manager_deps):
        """Test delete_room clears current_room_id and current_room_file when deleted room is selected."""
        repo = manager_deps["chat_room_repo"]
        room = repo.create(name="Delete Selection Test", file_path="/test/path.txt")

        # Select the room first
        manager.select_room(room.id, room.file_path)
        assert manager.current_room_id == room.id
        assert manager.current_room_file == room.file_path

        # Delete with mock confirmation
        with patch('src.ui.managers.chat_room_list_manager.QMessageBox.question') as mock_q:
            mock_q.return_value = QMessageBox.Yes
            with patch('src.ui.managers.chat_room_list_manager.QMessageBox.warning'):
                result = manager.delete_room(room.id)

        assert result is True
        # Verify current selection is cleared
        assert manager.current_room_id is None
        assert manager.current_room_file is None

    def test_delete_room_does_not_clear_other_selection(self, manager, manager_deps):
        """Test delete_room doesn't clear selection when deleting different room."""
        repo = manager_deps["chat_room_repo"]
        room1 = repo.create(name="Room 1", file_path="/path1.txt")
        room2 = repo.create(name="Room 2", file_path="/path2.txt")

        # Select room1
        manager.select_room(room1.id, room1.file_path)

        # Delete room2
        with patch('src.ui.managers.chat_room_list_manager.QMessageBox.question') as mock_q:
            mock_q.return_value = QMessageBox.Yes
            with patch('src.ui.managers.chat_room_list_manager.QMessageBox.warning'):
                result = manager.delete_room(room2.id)

        assert result is True
        # room1 selection should remain
        assert manager.current_room_id == room1.id
        assert manager.current_room_file == room1.file_path

    def test_delete_room_emits_room_deleted_signal(self, manager, manager_deps):
        """Test delete_room emits room_deleted signal."""
        repo = manager_deps["chat_room_repo"]
        room = repo.create(name="Signal Delete Test")

        signal_received = []
        manager.room_deleted.connect(lambda rid: signal_received.append(rid))

        with patch('src.ui.managers.chat_room_list_manager.QMessageBox.question') as mock_q:
            mock_q.return_value = QMessageBox.Yes
            with patch('src.ui.managers.chat_room_list_manager.QMessageBox.warning'):
                manager.delete_room(room.id)

        assert len(signal_received) == 1
        assert signal_received[0] == room.id

    def test_delete_room_user_declines_confirmation(self, manager, manager_deps):
        """Test delete_room returns False when user declines confirmation."""
        repo = manager_deps["chat_room_repo"]
        room = repo.create(name="Decline Test")

        with patch('src.ui.managers.chat_room_list_manager.QMessageBox.question') as mock_q:
            mock_q.return_value = QMessageBox.No
            result = manager.delete_room(room.id)

        assert result is False
        # Room should still exist
        assert repo.get_by_id(room.id) is not None

    def test_delete_room_not_found_shows_warning(self, manager):
        """Test delete_room shows warning when room not found."""
        non_existent_id = 99999

        with patch('src.ui.managers.chat_room_list_manager.QMessageBox.warning') as mock_warn:
            result = manager.delete_room(non_existent_id)

            assert result is False
            assert mock_warn.called
            args = mock_warn.call_args
            assert "not found" in str(args).lower() or "Selected room" in str(args)

    def test_delete_room_calls_load_rooms_after_deletion(self, manager, manager_deps):
        """Test delete_room calls load_rooms after successful deletion."""
        repo = manager_deps["chat_room_repo"]
        room = repo.create(name="Load After Delete")

        # Track load_rooms call
        original_load_rooms = manager.load_rooms
        load_rooms_called = []

        def mock_load_rooms():
            load_rooms_called.append(True)
            return original_load_rooms()

        manager.load_rooms = mock_load_rooms

        with patch('src.ui.managers.chat_room_list_manager.QMessageBox.question') as mock_q:
            mock_q.return_value = QMessageBox.Yes
            with patch('src.ui.managers.chat_room_list_manager.QMessageBox.warning'):
                manager.delete_room(room.id)

        # Verify load_rooms was called
        assert len(load_rooms_called) == 1


@pytest.mark.unit
class TestChatRoomListManagerRecoverMissingRooms:
    """Tests for ChatRoomListManager.recover_missing_rooms (12 missing lines)."""

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

    def test_recover_missing_rooms_scans_file_system(self, manager, manager_deps):
        """Test recover_missing_rooms scans file system for missing rooms."""
        storage = manager_deps["storage"]

        # Create a room directory in file system
        # Note: get_all_rooms returns sanitized directory names
        room_name = "MissingRoom"  # No spaces for simpler testing
        room_dir = storage.original_dir / room_name
        room_dir.mkdir(parents=True, exist_ok=True)

        # Room is in file system but not in DB
        with patch('src.ui.managers.chat_room_list_manager.QMessageBox.question') as mock_q:
            mock_q.return_value = QMessageBox.Yes
            with patch('src.ui.managers.chat_room_list_manager.QMessageBox.information'):
                result = manager.recover_missing_rooms()

        # Should have created 1 room
        assert result == 1

        # Verify room is now in DB (name will be the directory name)
        repo = manager_deps["chat_room_repo"]
        found = repo.get_by_name(room_name)
        assert found is not None

    def test_recover_missing_rooms_shows_confirmation(self, manager, manager_deps):
        """Test recover_missing_rooms shows confirmation dialog."""
        storage = manager_deps["storage"]

        # Create room directories (use sanitized names without spaces)
        for i in range(3):
            room_name = f"FileRoom{i}"
            room_dir = storage.original_dir / room_name
            room_dir.mkdir(parents=True, exist_ok=True)

        with patch('src.ui.managers.chat_room_list_manager.QMessageBox.question') as mock_q:
            mock_q.return_value = QMessageBox.Yes
            with patch('src.ui.managers.chat_room_list_manager.QMessageBox.information') as mock_info:
                manager.recover_missing_rooms()

                # Verify confirmation was shown
                assert mock_q.called
                # Check call was made with parent and title
                assert mock_q.call_count >= 1

    def test_recover_missing_rooms_user_declines(self, manager, manager_deps):
        """Test recover_missing_rooms returns 0 when user declines."""
        storage = manager_deps["storage"]

        # Create a room directory
        room_name = "Decline Recovery Room"
        sanitized = storage._sanitize_name(room_name)
        room_dir = storage.original_dir / sanitized
        room_dir.mkdir(parents=True, exist_ok=True)

        with patch('src.ui.managers.chat_room_list_manager.QMessageBox.question') as mock_q:
            mock_q.return_value = QMessageBox.No
            result = manager.recover_missing_rooms()

        assert result == 0

        # Room should NOT be in DB
        repo = manager_deps["chat_room_repo"]
        found = repo.get_by_name(room_name)
        assert found is None

    def test_recover_missing_rooms_shows_complete_message(self, manager, manager_deps):
        """Test recover_missing_rooms shows completion message."""
        storage = manager_deps["storage"]

        # Create room directories (use sanitized names without spaces)
        for i in range(2):
            room_name = f"CompleteRoom{i}"
            room_dir = storage.original_dir / room_name
            room_dir.mkdir(parents=True, exist_ok=True)

        with patch('src.ui.managers.chat_room_list_manager.QMessageBox.question') as mock_q:
            mock_q.return_value = QMessageBox.Yes
            with patch('src.ui.managers.chat_room_list_manager.QMessageBox.information') as mock_info:
                manager.recover_missing_rooms()

                # Verify completion message was shown
                assert mock_info.called
                assert mock_info.call_count >= 1

    def test_recover_missing_rooms_calls_load_rooms(self, manager, manager_deps):
        """Test recover_missing_rooms calls load_rooms after recovery."""
        storage = manager_deps["storage"]

        room_name = "Recovery Load Test"
        sanitized = storage._sanitize_name(room_name)
        room_dir = storage.original_dir / sanitized
        room_dir.mkdir(parents=True, exist_ok=True)

        # Track load_rooms call
        original_load_rooms = manager.load_rooms
        load_rooms_called = []

        def mock_load_rooms():
            load_rooms_called.append(True)
            return original_load_rooms()

        manager.load_rooms = mock_load_rooms

        with patch('src.ui.managers.chat_room_list_manager.QMessageBox.question') as mock_q:
            mock_q.return_value = QMessageBox.Yes
            with patch('src.ui.managers.chat_room_list_manager.QMessageBox.information'):
                manager.recover_missing_rooms()

        # Verify load_rooms was called
        assert len(load_rooms_called) == 1


@pytest.mark.unit
class TestChatRoomListManagerBackupRoom:
    """Tests for ChatRoomListManager.backup_room (9 missing lines)."""

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

    def test_backup_room_shows_confirmation(self, manager, manager_deps):
        """Test backup_room shows confirmation dialog with room details."""
        repo = manager_deps["chat_room_repo"]
        room = repo.create(name="Backup Test Room")

        with patch('src.ui.managers.chat_room_list_manager.QMessageBox.question') as mock_q:
            mock_q.return_value = QMessageBox.Yes
            with patch('src.ui.managers.chat_room_list_manager.QMessageBox.information'):
                with patch.object(manager._storage, 'backup_room') as mock_backup:
                    mock_backup.return_value = "/backup/path"
                    manager.backup_room(room.id)

                    # Verify confirmation dialog
                    assert mock_q.called
                    args, kwargs = mock_q.call_args
                    # Should mention room name
                    assert "Backup Test Room" in str(args)

    def test_backup_room_user_declines(self, manager, manager_deps):
        """Test backup_room returns None when user declines."""
        repo = manager_deps["chat_room_repo"]
        room = repo.create(name="Decline Backup Room")

        with patch('src.ui.managers.chat_room_list_manager.QMessageBox.question') as mock_q:
            mock_q.return_value = QMessageBox.No
            result = manager.backup_room(room.id)

        assert result is None

    def test_backup_room_shows_success_message(self, manager, manager_deps):
        """Test backup_room shows success message after backup."""
        repo = manager_deps["chat_room_repo"]
        room = repo.create(name="Success Backup Room")

        with patch('src.ui.managers.chat_room_list_manager.QMessageBox.question') as mock_q:
            mock_q.return_value = QMessageBox.Yes
            with patch('src.ui.managers.chat_room_list_manager.QMessageBox.information') as mock_info:
                with patch.object(manager._storage, 'backup_room') as mock_backup:
                    mock_backup.return_value = "/backup/test_path"
                    result = manager.backup_room(room.id)

                    # Verify success message
                    assert mock_info.called
                    args, kwargs = mock_info.call_args
                    message = str(args)
                    assert "complete" in message.lower() or "Success" in message

    def test_backup_room_shows_failure_message(self, manager, manager_deps):
        """Test backup_room shows warning when backup fails."""
        repo = manager_deps["chat_room_repo"]
        room = repo.create(name="Fail Backup Room")

        with patch('src.ui.managers.chat_room_list_manager.QMessageBox.question') as mock_q:
            mock_q.return_value = QMessageBox.Yes
            with patch('src.ui.managers.chat_room_list_manager.QMessageBox.warning') as mock_warn:
                with patch('src.ui.managers.chat_room_list_manager.QMessageBox.information'):
                    with patch.object(manager._storage, 'backup_room') as mock_backup:
                        mock_backup.return_value = None  # Backup failed
                        result = manager.backup_room(room.id)

                        # Verify warning message
                        assert mock_warn.called
                        assert result is None

    def test_backup_room_includes_file_details_in_confirmation(self, manager, manager_deps):
        """Test backup_room confirmation includes file path details."""
        repo = manager_deps["chat_room_repo"]
        room = repo.create(name="Detailed Backup Room")

        with patch('src.ui.managers.chat_room_list_manager.QMessageBox.question') as mock_q:
            mock_q.return_value = QMessageBox.Yes
            with patch('src.ui.managers.chat_room_list_manager.QMessageBox.information'):
                with patch.object(manager._storage, 'backup_room') as mock_backup:
                    mock_backup.return_value = "/backup/path"
                    manager.backup_room(room.id)

                    # Verify details in confirmation
                    args, kwargs = mock_q.call_args
                    message = str(args)
                    # Should mention what's included in backup
                    assert "Original" in message or "original" in message
                    assert "Summary" in message or "summary" in message

    def test_backup_room_calls_storage_backup_room(self, manager, manager_deps):
        """Test backup_room calls storage.backup_room with correct room name."""
        repo = manager_deps["chat_room_repo"]
        room = repo.create(name="Storage Call Test")

        with patch('src.ui.managers.chat_room_list_manager.QMessageBox.question') as mock_q:
            mock_q.return_value = QMessageBox.Yes
            with patch('src.ui.managers.chat_room_list_manager.QMessageBox.information'):
                with patch.object(manager._storage, 'backup_room') as mock_backup:
                    mock_backup.return_value = "/backup/path"
                    manager.backup_room(room.id)

                    # Verify backup_room was called with room name
                    mock_backup.assert_called_once_with("Storage Call Test")
