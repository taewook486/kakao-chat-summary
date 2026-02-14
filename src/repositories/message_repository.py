"""Message repository for message data access."""

from typing import Optional, List, Dict, Any
from datetime import date

from .base import Repository
from ..db.models import Message


class MessageRepository(Repository[Message]):
    """
    Repository for Message entity.

    Provides data access methods for message operations,
    abstracting the underlying database implementation.
    """

    def __init__(self, db):
        """
        Initialize repository with database instance.

        Args:
            db: Database instance for data access.
        """
        self.db = db

    def create(
        self,
        room_id: int,
        sender: str,
        content: str,
        message_date: date,
        message_time: Optional[str] = None,
        **kwargs
    ) -> Message:
        """
        Create a single message.

        Note: For bulk inserts, use add_messages instead.

        Args:
            room_id: Chat room ID.
            sender: Message sender name.
            content: Message content.
            message_date: Message date.
            message_time: Optional message time.
            **kwargs: Additional fields.

        Returns:
            Created Message entity (minimal data, as bulk operation returns count).
        """
        # Wrapper around add_messages for single message
        message_data = {
            "sender": sender,
            "content": content,
            "date": message_date,
            "time": message_time,
        }
        self.db.add_messages(room_id, [message_data])

        # Return a minimal Message object for compatibility
        return Message(
            room_id=room_id,
            sender=sender,
            content=content,
            message_date=message_date,
        )

    def get_by_id(self, entity_id: int) -> Optional[Message]:
        """
        Retrieve message by ID.

        Note: Current Database implementation doesn't have
        a get_message_by_id method. This is a placeholder
        for interface compatibility.

        Args:
            entity_id: Message ID.

        Returns:
            Message if found, None otherwise.
        """
        # Implementation would require db.get_message_by_id()
        return None

    def get_all(self) -> List[Message]:
        """
        Retrieve all messages from all rooms.

        Note: This returns an empty list as getting all messages
        across all rooms is not a typical use case.

        Returns:
            Empty list (use get_messages_by_room instead).
        """
        return []

    def get_messages_by_room(
        self,
        room_id: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> List[Message]:
        """
        Retrieve messages for a specific room.

        Args:
            room_id: Chat room ID.
            start_date: Optional start date filter.
            end_date: Optional end date filter.

        Returns:
            List of Message objects for the room.
        """
        return self.db.get_messages_by_room(room_id, start_date, end_date)

    def update(self, entity_id: int, **kwargs) -> Optional[Message]:
        """
        Update message fields.

        Note: Current implementation doesn't support updates.

        Args:
            entity_id: Message ID.
            **kwargs: Fields to update.

        Returns:
            Updated Message if supported, None otherwise.
        """
        return None

    def delete(self, entity_id: int) -> bool:
        """
        Delete a message by ID.

        Note: Current implementation doesn't support single message deletion.

        Args:
            entity_id: Message ID.

        Returns:
            False (not supported).
        """
        return False

    def add_messages(self, room_id: int, messages: List[Dict[str, Any]]) -> int:
        """
        Add multiple messages in bulk (optimized).

        Args:
            room_id: Chat room ID.
            messages: List of message dictionaries with keys:
                      sender, content, date, time (optional).

        Returns:
            Number of messages added.
        """
        return self.db.add_messages(room_id, messages)

    def get_count_by_room(self, room_id: int) -> int:
        """
        Get total message count for a room.

        Args:
            room_id: Chat room ID.

        Returns:
            Number of messages in the room.
        """
        return self.db.get_message_count_by_room(room_id)

    def get_count_by_date(self, room_id: int, target_date: date) -> int:
        """
        Get message count for a specific date.

        Args:
            room_id: Chat room ID.
            target_date: Date to count messages for.

        Returns:
            Number of messages on the target date.
        """
        return self.db.get_message_count_by_date(room_id, target_date)

    def get_unique_senders(self, room_id: int) -> List[str]:
        """
        Get list of unique senders in a room.

        Args:
            room_id: Chat room ID.

        Returns:
            List of unique sender names.
        """
        return self.db.get_unique_senders(room_id)
