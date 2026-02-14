"""SyncLog repository for sync log data access."""

from typing import Optional, List
from datetime import datetime

from .base import Repository
from ..db.models import SyncLog


class SyncLogRepository(Repository[SyncLog]):
    """
    Repository for SyncLog entity.

    Provides data access methods for sync log operations,
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
        status: str,
        message_count: int,
        new_message_count: int = 0,
        error_message: Optional[str] = None,
        **kwargs
    ) -> SyncLog:
        """
        Create a new sync log entry.

        Args:
            room_id: Chat room ID.
            status: Sync status (success, failed, partial).
            message_count: Total message count.
            new_message_count: New message count.
            error_message: Optional error message.
            **kwargs: Additional fields.

        Returns:
            Created SyncLog entity with ID assigned.
        """
        return self.db.add_sync_log(
            room_id=room_id,
            status=status,
            message_count=message_count,
            new_message_count=new_message_count,
            error_message=error_message,
        )

    def get_by_id(self, entity_id: int) -> Optional[SyncLog]:
        """
        Retrieve sync log by ID.

        Note: Not directly supported by current Database implementation.

        Args:
            entity_id: Sync log ID.

        Returns:
            SyncLog if found, None otherwise.
        """
        return None

    def get_all(self) -> List[SyncLog]:
        """
        Retrieve all sync logs.

        Returns:
            Empty list (use get_logs_by_room instead).
        """
        return []

    def get_logs_by_room(self, room_id: int, limit: int = 10) -> List[SyncLog]:
        """
        Retrieve sync logs for a specific room.

        Args:
            room_id: Chat room ID.
            limit: Maximum number of logs to return.

        Returns:
            List of SyncLog objects for the room.
        """
        return self.db.get_sync_logs_by_room(room_id, limit)

    def update(self, entity_id: int, **kwargs) -> Optional[SyncLog]:
        """
        Update sync log fields.

        Note: Not supported (logs are immutable).

        Args:
            entity_id: Sync log ID.
            **kwargs: Fields to update.

        Returns:
            None (not supported).
        """
        return None

    def delete(self, entity_id: int) -> bool:
        """
        Delete a sync log by ID.

        Note: Not supported (logs should be kept for history).

        Args:
            entity_id: Sync log ID.

        Returns:
            False (not supported).
        """
        return False
