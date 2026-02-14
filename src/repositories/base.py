"""Base repository interface for data access layer.

This module defines the abstract interface that all repositories must implement,
providing a consistent API for CRUD operations and ensuring type safety.
"""

from abc import ABC, abstractmethod
from typing import TypeVar, Generic, Optional, List

T = TypeVar("T")


class Repository(ABC, Generic[T]):
    """
    Base repository interface.

    All repositories must inherit from this class and implement
    the abstract methods. This provides a consistent interface
    for data access operations.
    """

    @abstractmethod
    def create(self, **kwargs) -> T:
        """
        Create a new entity.

        Returns:
            The created entity with ID assigned.
        """
        pass

    @abstractmethod
    def get_by_id(self, entity_id: int) -> Optional[T]:
        """
        Retrieve entity by ID.

        Args:
            entity_id: The ID of the entity to retrieve.

        Returns:
            The entity if found, None otherwise.
        """
        pass

    @abstractmethod
    def get_all(self) -> List[T]:
        """
        Retrieve all entities.

        Returns:
            List of all entities, optionally sorted/filtered.
        """
        pass

    @abstractmethod
    def update(self, entity_id: int, **kwargs) -> Optional[T]:
        """
        Update an existing entity.

        Args:
            entity_id: The ID of the entity to update.
            **kwargs: Fields to update.

        Returns:
            The updated entity if found, None otherwise.
        """
        pass

    @abstractmethod
    def delete(self, entity_id: int) -> bool:
        """
        Delete an entity by ID.

        Args:
            entity_id: The ID of the entity to delete.

        Returns:
            True if deleted, False if not found.
        """
        pass

    def exists(self, entity_id: int) -> bool:
        """
        Check if an entity exists by ID.

        Args:
            entity_id: The ID to check.

        Returns:
            True if entity exists, False otherwise.
        """
        return self.get_by_id(entity_id) is not None

    def count(self) -> int:
        """
        Get total count of entities.

        Returns:
            Number of entities.
        """
        return len(self.get_all())
