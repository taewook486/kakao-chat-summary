"""Unit tests for ChatRoomRepository."""

import pytest
from datetime import datetime

from src.repositories.chat_room_repository import ChatRoomRepository
from src.db.models import ChatRoom


@pytest.mark.unit
class TestChatRoomRepository:
    """Unit tests for ChatRoomRepository."""

    @pytest.fixture
    def repository(self, db_session):
        """Create repository with test database."""
        return ChatRoomRepository(db_session)

    def test_create_room(self, repository):
        """Test creating a new chat room."""
        # When: Create room
        room = repository.create(name="Test Room", file_path="/test/path")

        # Then: Room is created with ID
        assert room is not None
        assert room.id is not None
        assert room.id > 0
        assert room.name == "Test Room"
        assert room.file_path == "/test/path"

    def test_create_room_without_file_path(self, repository):
        """Test creating room without file path."""
        # When: Create room without file path
        room = repository.create(name="No Path Room")

        # Then: Room is created successfully
        assert room is not None
        assert room.name == "No Path Room"
        assert room.file_path is None

    def test_get_by_id(self, repository):
        """Test retrieving room by ID."""
        # Given: Room exists
        created = repository.create(name="Find By ID Room", file_path="/test")

        # When: Retrieve by ID
        found = repository.get_by_id(created.id)

        # Then: Room is found
        assert found is not None
        assert found.id == created.id
        assert found.name == "Find By ID Room"

    def test_get_by_id_not_found(self, repository):
        """Test retrieving non-existent room by ID."""
        # When: Retrieve non-existent room
        found = repository.get_by_id(99999)

        # Then: None is returned
        assert found is None

    def test_get_by_name(self, repository):
        """Test retrieving room by name."""
        # Given: Room exists
        created = repository.create(name="Unique Room Name")

        # When: Retrieve by name
        found = repository.get_by_name("Unique Room Name")

        # Then: Room is found
        assert found is not None
        assert found.id == created.id
        assert found.name == "Unique Room Name"

    def test_get_by_name_not_found(self, repository):
        """Test retrieving non-existent room by name."""
        # When: Retrieve non-existent room
        found = repository.get_by_name("Nonexistent Room")

        # Then: None is returned
        assert found is None

    def test_get_all_returns_list(self, repository):
        """Test that get_all returns a list."""
        # Given: Multiple rooms exist
        repository.create(name="Room 1")
        repository.create(name="Room 2")
        repository.create(name="Room 3")

        # When: Retrieve all rooms
        rooms = repository.get_all()

        # Then: List is returned
        assert isinstance(rooms, list)
        assert len(rooms) >= 3

    def test_get_all_includes_created_rooms(self, repository):
        """Test that get_all includes all created rooms."""
        # Given: Create rooms with specific names
        repository.create(name="Alpha Room")
        repository.create(name="Beta Room")
        repository.create(name="Gamma Room")

        # When: Get all rooms
        rooms = repository.get_all()

        # Then: All created rooms are present
        room_names = [room.name for room in rooms]
        assert "Alpha Room" in room_names
        assert "Beta Room" in room_names
        assert "Gamma Room" in room_names

    def test_delete_room(self, repository):
        """Test deleting a room."""
        # Given: Room exists
        room = repository.create(name="Delete Me Room")

        # When: Delete the room
        result = repository.delete(room.id)

        # Then: Room is deleted (delete_room returns None, verify by checking)
        assert result is None  # delete_room doesn't return a value
        # Verify room no longer exists
        found = repository.get_by_id(room.id)
        assert found is None

    def test_delete_nonexistent_room(self, repository):
        """Test deleting non-existent room."""
        # When: Delete non-existent room (should not raise error)
        result = repository.delete(99999)

        # Then: Returns None (no error raised)
        assert result is None

    def test_exists_true(self, repository):
        """Test exists returns True for existing room."""
        # Given: Room exists
        room = repository.create(name="Exists Test Room")

        # When: Check if exists
        result = repository.exists(room.id)

        # Then: Returns True
        assert result is True

    def test_exists_false(self, repository):
        """Test exists returns False for non-existent room."""
        # When: Check non-existent room
        result = repository.exists(99999)

        # Then: Returns False
        assert result is False

    def test_count(self, repository):
        """Test counting total rooms."""
        # Given: Multiple rooms exist
        repository.create(name="Count Room 1")
        repository.create(name="Count Room 2")
        repository.create(name="Count Room 3")

        # When: Count rooms
        count = repository.count()

        # Then: Count matches
        assert count >= 3

    def test_get_stats(self, repository):
        """Test getting room statistics."""
        # Given: Room exists
        room = repository.create(name="Stats Room")

        # When: Get stats
        stats = repository.get_stats(room.id)

        # Then: Stats dictionary is returned with actual keys
        assert isinstance(stats, dict)
        assert "total_messages" in stats  # Key is total_messages, not message_count
        assert "unique_senders" in stats
        assert "room_name" in stats
        assert stats["total_messages"] >= 0
        assert stats["room_name"] == "Stats Room"

    def test_update_sync_time(self, repository):
        """Test updating sync time."""
        # Given: Room exists
        room = repository.create(name="Sync Time Room")

        # When: Update sync time
        repository.update_sync_time(room.id)

        # Then: Sync time is updated (verify by retrieving room)
        updated_room = repository.get_by_id(room.id)
        assert updated_room is not None
        # last_sync_at should be set to recent time
        assert updated_room.last_sync_at is not None

    def test_update_returns_none(self, repository):
        """Test that update returns None (not implemented)."""
        # Given: Room exists
        room = repository.create(name="Update Test Room")

        # When: Attempt update (not supported)
        result = repository.update(room.id, name="New Name")

        # Then: Returns None
        assert result is None
        # Verify original name unchanged
        unchanged = repository.get_by_id(room.id)
        assert unchanged.name == "Update Test Room"
