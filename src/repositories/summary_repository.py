"""Summary repository for summary data access."""

from typing import Optional, List
from datetime import date

from .base import Repository
from ..db.models import Summary


class SummaryRepository(Repository[Summary]):
    """
    Repository for Summary entity.

    Provides data access methods for summary operations,
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
        summary_date: date,
        summary_type: str,
        content: str,
        llm_provider: Optional[str] = None,
        **kwargs
    ) -> Summary:
        """
        Create a new summary.

        Args:
            room_id: Chat room ID.
            summary_date: Date of the summary.
            summary_type: Type (daily, 2days, weekly).
            content: Summary content.
            llm_provider: Optional LLM provider name.
            **kwargs: Additional fields.

        Returns:
            Created Summary entity with ID assigned.
        """
        return self.db.add_summary(
            room_id=room_id,
            summary_date=summary_date,
            summary_type=summary_type,
            content=content,
            llm_provider=llm_provider,
        )

    def get_by_id(self, entity_id: int) -> Optional[Summary]:
        """
        Retrieve summary by ID.

        Args:
            entity_id: Summary ID.

        Returns:
            Summary if found, None otherwise.
        """
        return self.db.get_summary_by_id(entity_id)

    def get_all(self) -> List[Summary]:
        """
        Retrieve all summaries from all rooms.

        Returns:
            Empty list (use get_summaries_by_room instead).
        """
        return []

    def get_summaries_by_room(
        self, room_id: int, summary_type: Optional[str] = None
    ) -> List[Summary]:
        """
        Retrieve summaries for a specific room.

        Args:
            room_id: Chat room ID.
            summary_type: Optional filter by summary type.

        Returns:
            List of Summary objects for the room.
        """
        return self.db.get_summaries_by_room(room_id, summary_type)

    def get_by_room(self, room_id: int, summary_type: Optional[str] = None) -> List[Summary]:
        """
        Alias for get_summaries_by_room().

        Args:
            room_id: Chat room ID.
            summary_type: Optional filter by summary type.

        Returns:
            List of Summary objects for the room.
        """
        return self.get_summaries_by_room(room_id, summary_type)

    def update(self, entity_id: int, **kwargs) -> Optional[Summary]:
        """
        Update summary fields.

        Note: Current implementation doesn't support updates.

        Args:
            entity_id: Summary ID.
            **kwargs: Fields to update.

        Returns:
            Updated Summary if supported, None otherwise.
        """
        return None

    def delete(self, entity_id: int) -> bool:
        """
        Delete a summary by ID (not supported).

        Args:
            entity_id: Summary ID.

        Returns:
            False (use delete_by_date instead).
        """
        return False

    def delete_by_date(self, room_id: int, summary_date: date) -> bool:
        """
        Delete summary for a specific date.

        Args:
            room_id: Chat room ID.
            summary_date: Date of summary to delete.

        Returns:
            True if deleted, False if not found.
        """
        return self.db.delete_summary(room_id, summary_date)
