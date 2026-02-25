"""ChatRoomListManager - Manages chat room list UI and operations.

Extracted from main_window.py as part of architecture refactoring (SPEC-IMPROVE-001).
This manager handles:
- Room list loading and display
- Room selection handling
- Room creation/deletion
- Room recovery from file system
- Room backup operations

@MX:NOTE: Extracted from main_window.py Milestone 2.1
@MX:SPEC: SPEC-IMPROVE-001
"""

from typing import Optional, List, Dict, Any, Callable
from datetime import datetime
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QMessageBox,
    QScrollArea, QFrame
)
from PySide6.QtCore import Qt, Signal, QObject

from src.repositories.chat_room_repository import ChatRoomRepository
from src.repositories.message_repository import MessageRepository
from src.repositories.summary_repository import SummaryRepository
from src.services.chat_service import ChatService
from src.file_storage import FileStorage


class ChatRoomWidget(QFrame):
    """Chat room item widget for the room list.

    @MX:ANCHOR: Used by ChatRoomListManager for displaying rooms
    @MX:REASON: Moved from main_window.py to maintain cohesion with manager
    """

    clicked = Signal(int, str)  # room_id, file_path

    def __init__(
        self,
        room_id: int,
        name: str,
        message_count: int = 0,
        new_count: int = 0,
        last_sync: Optional[datetime] = None,
        file_path: Optional[str] = None,
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        self.room_id = room_id
        self.file_path = file_path or ""
        self.setObjectName("chatRoomItem")
        self.setProperty("class", "ChatRoomItem")
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(70)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)

        # Icon/avatar area
        avatar = QLabel("Message")
        avatar.setFixedSize(40, 40)
        avatar.setAlignment(Qt.AlignCenter)
        avatar.setStyleSheet("""
            background-color: #FEE500;
            border-radius: 20px;
            font-size: 18px;
        """)
        layout.addWidget(avatar)

        # Info area
        info_layout = QVBoxLayout()
        info_layout.setSpacing(4)

        # Name + new message badge
        name_layout = QHBoxLayout()
        name_label = QLabel(name)
        name_label.setProperty("class", "ChatRoomName")
        name_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        name_layout.addWidget(name_label)

        if new_count > 0:
            badge = QLabel(str(new_count))
            badge.setProperty("class", "NewBadge")
            badge.setStyleSheet("""
                background-color: #FF5252;
                color: white;
                font-size: 10px;
                font-weight: bold;
                padding: 2px 6px;
                border-radius: 10px;
            """)
            badge.setFixedHeight(18)
            name_layout.addWidget(badge)

        name_layout.addStretch()
        info_layout.addLayout(name_layout)

        # Message count and sync time
        sync_text = "Not synced"
        if last_sync:
            sync_text = last_sync.strftime("%m/%d %H:%M")

        info_label = QLabel(f"Stats: {message_count:,} messages - {sync_text}")
        info_label.setProperty("class", "ChatRoomInfo")
        info_label.setStyleSheet("color: #888888; font-size: 11px;")
        info_layout.addWidget(info_label)

        layout.addLayout(info_layout, 1)

    def mousePressEvent(self, event):
        """Emit clicked signal on mouse press."""
        self.clicked.emit(self.room_id, self.file_path)
        super().mousePressEvent(event)


class ChatRoomListManager(QObject):
    """Manages chat room list UI and operations.

    This manager encapsulates all room list-related functionality,
    providing a clean interface for the main window.

    Signals:
        room_selected: Emitted when a room is selected (room_id, room_name, file_path)
        rooms_loaded: Emitted when room list is refreshed
        room_created: Emitted when a room is created (room_id, room_name)
        room_deleted: Emitted when a room is deleted (room_id)

    @MX:NOTE: Extracted from main_window.py to reduce complexity
    @MX:SPEC: SPEC-IMPROVE-001 Phase 2, Milestone 2.1
    """

    # Signals for communication with main window
    room_selected = Signal(int, str, str)  # room_id, room_name, file_path
    rooms_loaded = Signal()
    room_created = Signal(int, str)  # room_id, room_name
    room_deleted = Signal(int)  # room_id

    def __init__(
        self,
        parent: QWidget,
        chat_room_repo: ChatRoomRepository,
        message_repo: MessageRepository,
        summary_repo: SummaryRepository,
        chat_service: ChatService,
        storage: FileStorage,
    ):
        """Initialize the chat room list manager.

        Args:
            parent: Parent widget for UI components
            chat_room_repo: Repository for chat room operations
            message_repo: Repository for message operations
            summary_repo: Repository for summary operations
            chat_service: Service for chat-related operations
            storage: File storage for backup/recovery
        """
        super().__init__(parent)
        self._parent = parent
        self._chat_room_repo = chat_room_repo
        self._message_repo = message_repo
        self._summary_repo = summary_repo
        self._chat_service = chat_service
        self._storage = storage

        # Current room state
        self._current_room_id: Optional[int] = None
        self._current_room_file: Optional[str] = None

        # UI components (created by setup_ui)
        self._room_list_widget: Optional[QWidget] = None
        self._room_list_layout: Optional[QVBoxLayout] = None

    @property
    def current_room_id(self) -> Optional[int]:
        """Get the currently selected room ID."""
        return self._current_room_id

    @property
    def current_room_file(self) -> Optional[str]:
        """Get the currently selected room file path."""
        return self._current_room_file

    @property
    def room_list_widget(self) -> QWidget:
        """Get the room list widget for adding to layouts."""
        if self._room_list_widget is None:
            self._setup_room_list_ui()
        return self._room_list_widget

    def _setup_room_list_ui(self) -> QWidget:
        """Set up the room list UI components.

        Creates the room list widget with scroll area.
        Called lazily when room_list_widget is first accessed.
        """
        self._room_list_widget = QWidget()
        self._room_list_layout = QVBoxLayout(self._room_list_widget)
        self._room_list_layout.setContentsMargins(5, 5, 5, 5)
        self._room_list_layout.setSpacing(5)
        self._room_list_layout.addStretch()  # Push items to top

        return self._room_list_widget

    def create_scroll_area(self) -> QScrollArea:
        """Create a scroll area containing the room list widget.

        Returns:
            QScrollArea configured for room list display.
        """
        scroll = QScrollArea()
        scroll.setWidget(self.room_list_widget)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet(
            "QScrollArea { border: none; background-color: #F5F5F5; }"
        )
        return scroll

    def load_rooms(self) -> None:
        """Load and display all chat rooms from the repository.

        Clears existing room widgets and creates new ChatRoomWidget
        instances for each room in the database.
        """
        if self._room_list_layout is None:
            return

        # Clear existing widgets
        while self._room_list_layout.count() > 1:
            item = self._room_list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Load rooms from repository
        rooms = self._chat_room_repo.get_all()

        if not rooms:
            # Show placeholder for empty list
            empty_label = QLabel("Folder: Please add chat room")
            empty_label.setAlignment(Qt.AlignCenter)
            empty_label.setStyleSheet("color: #888888; padding: 20px;")
            self._room_list_layout.insertWidget(0, empty_label)
            return

        # Create widget for each room
        for room in rooms:
            # Get message count for room
            msg_count = self._message_repo.get_count_by_room(room.id)

            widget = ChatRoomWidget(
                room_id=room.id,
                name=room.name,
                message_count=msg_count,
                new_count=0,  # TODO: Calculate new message count
                last_sync=room.last_sync_at,
                file_path=room.file_path
            )
            widget.clicked.connect(self._on_room_clicked)
            self._room_list_layout.insertWidget(
                self._room_list_layout.count() - 1, widget
            )

        self.rooms_loaded.emit()

    def _on_room_clicked(self, room_id: int, file_path: str) -> None:
        """Handle room widget click.

        Args:
            room_id: ID of the clicked room
            file_path: File path of the clicked room
        """
        self._current_room_id = room_id
        self._current_room_file = file_path

        # Get room name for signal
        room = self._chat_room_repo.get_by_id(room_id)
        room_name = room.name if room else ""

        self.room_selected.emit(room_id, room_name, file_path)

    def get_room_statistics(self, room_id: int) -> Dict[str, Any]:
        """Get statistics for a room.

        Args:
            room_id: Room ID to get statistics for.

        Returns:
            Dictionary with room statistics.
        """
        return self._chat_service.get_room_statistics(room_id)

    def get_room_summaries(self, room_id: int) -> List[Any]:
        """Get summaries for a room.

        Args:
            room_id: Room ID to get summaries for.

        Returns:
            List of summary objects.
        """
        return self._summary_repo.get_by_room(room_id)

    def create_room(self, room_name: str) -> Optional[int]:
        """Create a new chat room.

        Args:
            room_name: Name for the new room.

        Returns:
            Room ID if created, None if already exists or error.
        """
        # Check if room already exists
        existing = self._chat_room_repo.get_by_name(room_name)
        if existing:
            QMessageBox.warning(
                self._parent,
                "Notification",
                f"Room '{room_name}' already exists."
            )
            return None

        try:
            # Create room in repository
            room = self._chat_room_repo.create(room_name)

            # Create storage directories
            sanitized = self._storage._sanitize_name(room_name)
            (self._storage.original_dir / sanitized).mkdir(parents=True, exist_ok=True)
            (self._storage.summary_dir / sanitized).mkdir(parents=True, exist_ok=True)

            # Refresh room list
            self.load_rooms()

            # Notify main window
            self.room_created.emit(room.id, room_name)

            return room.id

        except Exception as e:
            QMessageBox.warning(
                self._parent,
                "Error",
                f"Failed to create room: {str(e)}"
            )
            return None

    def delete_room(self, room_id: int) -> bool:
        """Delete a chat room.

        Args:
            room_id: ID of room to delete.

        Returns:
            True if deleted, False otherwise.
        """
        room = self._chat_room_repo.get_by_id(room_id)
        if not room:
            QMessageBox.warning(
                self._parent,
                "Error",
                "Selected room not found."
            )
            return False

        room_name = room.name

        # Confirm deletion
        reply = QMessageBox.question(
            self._parent,
            "Delete Room",
            f"Are you sure you want to delete '{room_name}'?\n\n"
            f"DB messages, summaries, and URL data will be deleted.\n"
            f"(Files in data/ folder will be preserved)",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply != QMessageBox.Yes:
            return False

        try:
            self._chat_room_repo.delete(room_id)

            # Clear current room if deleted
            if self._current_room_id == room_id:
                self._current_room_id = None
                self._current_room_file = None

            # Refresh room list
            self.load_rooms()

            # Notify main window
            self.room_deleted.emit(room_id)

            return True

        except Exception as e:
            QMessageBox.warning(
                self._parent,
                "Error",
                f"Failed to delete room: {str(e)}"
            )
            return False

    def recover_missing_rooms(self) -> int:
        """Recover rooms from file system that are missing from database.

        Scans file directories for room names not in the database
        and offers to create them.

        Returns:
            Number of rooms recovered.
        """
        # Get rooms from file system
        file_rooms = self._storage.get_all_rooms()

        # Get existing DB room names
        db_rooms = self._chat_room_repo.get_all()
        db_room_names = {r.name for r in db_rooms}

        # Find missing rooms
        missing = [name for name in file_rooms if name not in db_room_names]

        if not missing:
            QMessageBox.information(
                self._parent,
                "Room Recovery",
                "All rooms exist in DB.\nNo missing rooms found."
            )
            return 0

        # Confirm recovery
        reply = QMessageBox.question(
            self._parent,
            "Room Recovery",
            f"Found {len(missing)} rooms in files not in DB:\n\n"
            + "\n".join(f"  - {name}" for name in missing)
            + "\n\nAdd to DB?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )

        if reply != QMessageBox.Yes:
            return 0

        # Create missing rooms
        created = 0
        for name in missing:
            try:
                self._chat_room_repo.create(name)
                created += 1
            except Exception:
                pass

        # Refresh room list
        self.load_rooms()

        QMessageBox.information(
            self._parent,
            "Room Recovery Complete",
            f"Added {created} rooms to DB."
        )

        return created

    def backup_room(self, room_id: int) -> Optional[str]:
        """Backup a specific room.

        Args:
            room_id: ID of room to backup.

        Returns:
            Backup path if successful, None otherwise.
        """
        room = self._chat_room_repo.get_by_id(room_id)
        if not room:
            QMessageBox.warning(
                self._parent,
                "Room Backup",
                "Please select a room first."
            )
            return None

        room_name = room.name

        # Confirm backup
        reply = QMessageBox.question(
            self._parent,
            "Room Backup",
            f"Backup '{room_name}'?\n\n"
            f"Backup includes:\n"
            f"- Original chats (data/original/{room_name}/)\n"
            f"- Summaries (data/summary/{room_name}/)\n"
            f"- URL files (data/url/{room_name}/)",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )

        if reply != QMessageBox.Yes:
            return None

        # Perform backup
        backup_path = self._storage.backup_room(room_name)

        if backup_path:
            QMessageBox.information(
                self._parent,
                "Backup Complete",
                f"'{room_name}' backup complete.\n\nPath: {backup_path}"
            )
            return str(backup_path)
        else:
            QMessageBox.warning(
                self._parent,
                "Backup Failed",
                "An error occurred during backup."
            )
            return None

    def select_room(self, room_id: int, file_path: str) -> None:
        """Programmatically select a room.

        Args:
            room_id: ID of room to select.
            file_path: File path of the room.
        """
        self._on_room_clicked(room_id, file_path)

    def clear_selection(self) -> None:
        """Clear the current room selection."""
        self._current_room_id = None
        self._current_room_file = None
