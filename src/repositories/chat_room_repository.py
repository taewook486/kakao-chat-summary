"""ChatRoom repository for chat room data access."""

from typing import Optional, List, Dict, Any

from .base import Repository
from ..db.models import ChatRoom


class ChatRoomRepository(Repository[ChatRoom]):
    """
    Repository for ChatRoom entity.

    Provides data access methods for chat room operations,
    abstracting the underlying database implementation.
    """

    def __init__(self, db):
        """
        Initialize repository with database instance.

        Args:
            db: Database instance for data access.
        """
        self.db = db

    def create(self, name: str, file_path: Optional[str] = None, **kwargs) -> ChatRoom:
        """
        Create a new chat room.

        Args:
            name: Chat room name.
            file_path: Optional file path for chat data.
            **kwargs: Additional fields (participant_count, etc.).

        Returns:
            Created ChatRoom entity with ID assigned.
        """
        return self.db.create_room(name, file_path)

    def get_by_id(self, entity_id: int) -> Optional[ChatRoom]:
        """
        Retrieve chat room by ID.

        Args:
            entity_id: Chat room ID.

        Returns:
            ChatRoom if found, None otherwise.
        """
        return self.db.get_room_by_id(entity_id)

    def get_by_name(self, name: str) -> Optional[ChatRoom]:
        """
        Retrieve chat room by name.

        Args:
            name: Chat room name.

        Returns:
            ChatRoom if found, None otherwise.
        """
        return self.db.get_room_by_name(name)

    def get_all(self) -> List[ChatRoom]:
        """
        Retrieve all chat rooms.

        Returns:
            List of all chat rooms sorted by message count (descending).
        """
        return self.db.get_all_rooms()

    def update(
        self,
        entity_id: int,
        name: Optional[str] = None,
        file_path: Optional[str] = None,
        **kwargs
    ) -> Optional[ChatRoom]:
        """
        Update chat room fields.

        Note: Current Database implementation doesn't support
        direct room updates. This method is provided for
        interface compatibility.

        Args:
            entity_id: Chat room ID.
            name: New name (optional).
            file_path: New file path (optional).
            **kwargs: Additional fields to update.

        Returns:
            Updated ChatRoom if supported, None otherwise.
        """
        # Current implementation doesn't support updates
        # This can be implemented when Database.add_update_room is added
        return None

    def delete(self, entity_id: int) -> bool:
        """
        Delete a chat room by ID.

        Args:
            entity_id: Chat room ID to delete.

        Returns:
            True if deleted, False if not found.
        """
        return self.db.delete_room(entity_id)

    def get_stats(self, room_id: int) -> Dict[str, Any]:
        """
        Get statistics for a chat room.

        Args:
            room_id: Chat room ID.

        Returns:
            Dictionary with stats (message_count, participant_count, etc.).
        """
        return self.db.get_room_stats(room_id)

    def update_sync_time(self, room_id: int) -> None:
        """
        Update the last sync timestamp for a room.

        Args:
            room_id: Chat room ID.
        """
        self.db.update_room_sync_time(room_id)
