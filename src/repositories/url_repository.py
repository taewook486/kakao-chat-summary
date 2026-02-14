"""URL repository for URL data access."""

from typing import Optional, List, Dict
from datetime import date

from .base import Repository
from ..db.models import URL


class URLRepository(Repository[URL]):
    """
    Repository for URL entity.

    Provides data access methods for URL operations,
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
        url: str,
        descriptions: Optional[str] = None,
        source_date: Optional[date] = None,
        **kwargs
    ) -> URL:
        """
        Create a new URL entry.

        Args:
            room_id: Chat room ID.
            url: URL string.
            descriptions: Optional descriptions (space-separated).
            source_date: Optional date URL was shared.
            **kwargs: Additional fields.

        Returns:
            Created URL entity with ID assigned.
        """
        return self.db.add_url(room_id, url, descriptions, source_date)

    def get_by_id(self, entity_id: int) -> Optional[URL]:
        """
        Retrieve URL by ID.

        Note: Not directly supported by current Database implementation.

        Args:
            entity_id: URL ID.

        Returns:
            URL if found, None otherwise.
        """
        return None

    def get_all(self) -> List[URL]:
        """
        Retrieve all URLs from all rooms.

        Returns:
            Empty list (use get_urls_by_room instead).
        """
        return []

    def get_urls_by_room(self, room_id: int) -> Dict[str, List[str]]:
        """
        Retrieve URLs for a specific room.

        Args:
            room_id: Chat room ID.

        Returns:
            Dictionary mapping URLs to their descriptions.
        """
        return self.db.get_urls_by_room(room_id)

    def update(self, entity_id: int, **kwargs) -> Optional[URL]:
        """
        Update URL fields.

        Note: Not supported (URLs are immutable).

        Args:
            entity_id: URL ID.
            **kwargs: Fields to update.

        Returns:
            None (not supported).
        """
        return None

    def delete(self, entity_id: int) -> bool:
        """
        Delete a URL by ID.

        Note: Use clear_urls_by_room instead for bulk deletion.

        Args:
            entity_id: URL ID.

        Returns:
            False (use clear_urls_by_room instead).
        """
        return False

    def add_urls_batch(self, room_id: int, urls: Dict[str, List[str]]) -> int:
        """
        Add multiple URLs in bulk.

        Args:
            room_id: Chat room ID.
            urls: Dictionary mapping URLs to descriptions.

        Returns:
            Number of URLs added.
        """
        return self.db.add_urls_batch(room_id, urls)

    def get_count_by_room(self, room_id: int) -> int:
        """
        Get total URL count for a room.

        Args:
            room_id: Chat room ID.

        Returns:
            Number of unique URLs in the room.
        """
        return self.db.get_url_count_by_room(room_id)

    def clear_urls_by_room(self, room_id: int) -> int:
        """
        Clear all URLs for a room.

        Args:
            room_id: Chat room ID.

        Returns:
            Number of URLs deleted.
        """
        return self.db.clear_urls_by_room(room_id)
