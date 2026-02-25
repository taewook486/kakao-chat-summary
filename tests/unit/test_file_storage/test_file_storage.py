"""
Unit tests for FileStorage class methods.

Tests cover:
- Original chat file storage and loading
- Summary file storage and loading
- URL management
- Room directory management
- Backup and restore functionality
- File sanitization and validation
- Message merging and deduplication
"""

import pytest
import shutil
from pathlib import Path
from datetime import date

from src.file_storage import FileStorage, get_storage


class TestFileStorageInitialization:
    """Test FileStorage initialization."""

    def test_init_creates_directories(self, temp_dir):
        """Test that initialization creates required directories."""
        storage = FileStorage(base_dir=temp_dir)
        assert storage.original_dir.exists()
        assert storage.summary_dir.exists()
        assert storage.url_dir.exists()

    def test_init_with_default_base_dir(self):
        """Test initialization with default base directory."""
        storage = FileStorage()
        assert storage.base_dir is not None


class TestOriginalFileStorage:
    """Test original chat file storage."""

    def test_save_daily_original_creates_file(self, file_storage):
        """Test saving daily original creates file."""
        messages = ["Message 1", "Message 2"]
        filepath = file_storage.save_daily_original("Test Room", "2024-01-01", messages)
        assert filepath.exists()
        assert "20240101" in filepath.name

    def test_save_daily_original_content_format(self, file_storage):
        """Test that saved file has correct format."""
        messages = ["Message 1", "Message 2"]
        filepath = file_storage.save_daily_original("Test Room", "2024-01-01", messages)
        content = filepath.read_text(encoding='utf-8')
        assert "Test Room" in content
        assert "2024-01-01" in content
        assert "Message 1" in content
        assert "Message 2" in content

    def test_save_daily_original_merges_existing(self, file_storage):
        """Test that saving merges with existing content."""
        # First save
        file_storage.save_daily_original("Test Room", "2024-01-01", ["Msg 1"])
        # Second save with new message
        file_storage.save_daily_original("Test Room", "2024-01-01", ["Msg 2"])

        messages = file_storage.load_daily_original("Test Room", "2024-01-01")
        assert len(messages) >= 2

    def test_save_daily_original_prevents_data_loss(self, file_storage):
        """Test that save prevents data loss on merge."""
        # Save initial content
        file_storage.save_daily_original("Test Room", "2024-01-01", ["Msg 1", "Msg 2"])

        # Load and verify
        messages = file_storage.load_daily_original("Test Room", "2024-01-01")
        initial_count = len(messages)

        # Save again with subset
        file_storage.save_daily_original("Test Room", "2024-01-01", ["Msg 1"])

        # Should not have fewer messages
        messages = file_storage.load_daily_original("Test Room", "2024-01-01")
        assert len(messages) >= initial_count

    def test_save_all_daily_originals(self, file_storage):
        """Test saving multiple dates."""
        messages_by_date = {
            "2024-01-01": ["Msg 1"],
            "2024-01-02": ["Msg 2"],
        }
        saved_files = file_storage.save_all_daily_originals("Test Room", messages_by_date)
        assert len(saved_files) == 2

    def test_load_daily_original(self, file_storage):
        """Test loading daily original."""
        messages = ["Message 1", "Message 2"]
        file_storage.save_daily_original("Test Room", "2024-01-01", messages)

        loaded = file_storage.load_daily_original("Test Room", "2024-01-01")
        assert len(loaded) >= 2

    def test_load_daily_original_nonexistent(self, file_storage):
        """Test loading non-existent file."""
        loaded = file_storage.load_daily_original("Test Room", "2099-01-01")
        assert loaded == []

    def test_load_all_originals(self, file_storage):
        """Test loading all originals for a room."""
        messages_by_date = {
            "2024-01-01": ["Msg 1"],
            "2024-01-02": ["Msg 2"],
        }
        file_storage.save_all_daily_originals("Test Room", messages_by_date)

        all_messages = file_storage.load_all_originals("Test Room")
        assert "2024-01-01" in all_messages
        assert "2024-01-02" in all_messages

    def test_get_available_dates(self, file_storage):
        """Test getting available dates."""
        messages_by_date = {
            "2024-01-02": ["Msg 2"],
            "2024-01-01": ["Msg 1"],
        }
        file_storage.save_all_daily_originals("Test Room", messages_by_date)

        dates = file_storage.get_available_dates("Test Room")
        assert len(dates) == 2
        assert dates == sorted(dates)

    def test_get_available_dates_empty(self, file_storage):
        """Test getting available dates for room with no files."""
        dates = file_storage.get_available_dates("Nonexistent Room")
        assert dates == []


class TestSummaryFileStorage:
    """Test summary file storage."""

    def test_save_daily_summary(self, file_storage):
        """Test saving daily summary."""
        content = "# Summary\n\nTest content"
        filepath = file_storage.save_daily_summary("Test Room", "2024-01-01", content, "test")
        assert filepath.exists()
        assert "20240101" in filepath.name

    def test_save_daily_summary_content(self, file_storage):
        """Test that summary file has correct content."""
        content = "# Summary\n\nTest content"
        filepath = file_storage.save_daily_summary("Test Room", "2024-01-01", content, "test")
        file_content = filepath.read_text(encoding='utf-8')
        assert "Test Room" in file_content
        assert "2024-01-01" in file_content
        assert "Test content" in file_content
        assert "test" in file_content

    def test_load_daily_summary(self, file_storage):
        """Test loading daily summary."""
        content = "# Summary\n\nTest content"
        file_storage.save_daily_summary("Test Room", "2024-01-01", content)

        loaded = file_storage.load_daily_summary("Test Room", "2024-01-01")
        assert loaded is not None
        assert "Test content" in loaded

    def test_load_daily_summary_nonexistent(self, file_storage):
        """Test loading non-existent summary."""
        loaded = file_storage.load_daily_summary("Test Room", "2099-01-01")
        assert loaded is None

    def test_has_summary(self, file_storage):
        """Test checking if summary exists."""
        content = "# Summary"
        file_storage.save_daily_summary("Test Room", "2024-01-01", content)

        assert file_storage.has_summary("Test Room", "2024-01-01") is True
        assert file_storage.has_summary("Test Room", "2099-01-01") is False

    def test_delete_daily_summary(self, file_storage):
        """Test deleting daily summary."""
        content = "# Summary"
        file_storage.save_daily_summary("Test Room", "2024-01-01", content)

        deleted = file_storage.delete_daily_summary("Test Room", "2024-01-01")
        assert deleted is True

        # Should be backed up
        assert not file_storage.has_summary("Test Room", "2024-01-01")

    def test_delete_daily_summary_nonexistent(self, file_storage):
        """Test deleting non-existent summary."""
        deleted = file_storage.delete_daily_summary("Test Room", "2099-01-01")
        assert deleted is False

    def test_get_summarized_dates(self, file_storage):
        """Test getting summarized dates."""
        file_storage.save_daily_summary("Test Room", "2024-01-02", "# Summary 2")
        file_storage.save_daily_summary("Test Room", "2024-01-01", "# Summary 1")

        dates = file_storage.get_summarized_dates("Test Room")
        assert len(dates) == 2
        assert dates == sorted(dates)


class TestRoomManagement:
    """Test room directory management."""

    def test_get_all_rooms(self, file_storage):
        """Test getting all rooms."""
        file_storage.save_daily_original("Room 1", "2024-01-01", ["Msg 1"])
        file_storage.save_daily_summary("Room 2", "2024-01-01", "# Summary")

        rooms = file_storage.get_all_rooms()
        assert len(rooms) >= 2

    def test_create_room_directories(self, file_storage):
        """Test creating room directories."""
        file_storage.create_room_directories("Test Room")

        room_dir_original = file_storage.original_dir / file_storage._sanitize_name("Test Room")
        room_dir_summary = file_storage.summary_dir / file_storage._sanitize_name("Test Room")

        assert room_dir_original.exists()
        assert room_dir_summary.exists()

    def test_get_room_stats(self, file_storage):
        """Test getting room statistics."""
        messages_by_date = {
            "2024-01-01": ["Msg 1"],
            "2024-01-02": ["Msg 2"],
        }
        file_storage.save_all_daily_originals("Test Room", messages_by_date)
        file_storage.save_daily_summary("Test Room", "2024-01-01", "# Summary")

        stats = file_storage.get_room_stats("Test Room")
        assert stats['room_name'] == "Test Room"
        assert stats['total_days'] == 2
        assert stats['summarized_days'] == 1
        assert stats['unsummarized_days'] == 1

    def test_get_dates_needing_summary(self, file_storage):
        """Test getting dates that need summary."""
        messages_by_date = {
            "2024-01-01": ["Msg 1"],
            "2024-01-02": ["Msg 2"],
        }
        file_storage.save_all_daily_originals("Test Room", messages_by_date)
        file_storage.save_daily_summary("Test Room", "2024-01-01", "# Summary")

        dates = file_storage.get_dates_needing_summary("Test Room")
        assert "2024-01-02" in dates
        assert "2024-01-01" not in dates


class TestURLManagement:
    """Test URL file management."""

    def test_save_url_lists(self, file_storage):
        """Test saving URL lists."""
        urls_recent = {"https://example.com": ["Example"]}
        urls_weekly = {"https://example.com": ["Example"]}
        urls_all = {"https://example.com": ["Example"]}

        paths = file_storage.save_url_lists("Test Room", urls_recent, urls_weekly, urls_all)
        assert len(paths) == 3
        assert all(p.exists() for p in paths.values())

    def test_load_url_list(self, file_storage):
        """Test loading URL list."""
        urls = {"https://example.com": ["Example site"]}
        file_storage.save_url_lists("Test Room", urls, urls, urls)

        loaded = file_storage.load_url_list("Test Room", "all")
        assert "https://example.com" in loaded
        assert "Example site" in loaded["https://example.com"]

    def test_load_url_list_nonexistent(self, file_storage):
        """Test loading non-existent URL list."""
        loaded = file_storage.load_url_list("Test Room", "all")
        assert loaded == {}

    def test_get_url_file_info(self, file_storage):
        """Test getting URL file info."""
        urls = {"https://example.com": ["Example"]}
        file_storage.save_url_lists("Test Room", urls, urls, urls)

        info = file_storage.get_url_file_info("Test Room")
        assert info is not None
        assert "all" in info
        assert "recent" in info
        assert "weekly" in info


class TestFileInvalidation:
    """Test summary invalidation based on file changes."""

    def test_invalidate_summary_if_file_changed(self, file_storage):
        """Test invalidating summary when file size changes."""
        content = "# Summary"
        file_storage.save_daily_summary("Test Room", "2024-01-01", content)
        old_size = file_storage.get_original_file_size("Test Room", "2024-01-01")

        # Save more messages
        file_storage.save_daily_original("Test Room", "2024-01-01", ["Msg 1", "Msg 2", "Msg 3"])
        new_size = file_storage.get_original_file_size("Test Room", "2024-01-01")

        invalidated = file_storage.invalidate_summary_if_file_changed(
            "Test Room", "2024-01-01", old_size, new_size
        )
        assert invalidated is True

    def test_invalidate_summary_if_unchanged(self, file_storage):
        """Test not invalidating when file size unchanged."""
        file_storage.save_daily_original("Test Room", "2024-01-01", ["Msg 1"])
        size = file_storage.get_original_file_size("Test Room", "2024-01-01")

        invalidated = file_storage.invalidate_summary_if_file_changed(
            "Test Room", "2024-01-01", size, size
        )
        assert invalidated is False

    def test_get_original_file_size(self, file_storage):
        """Test getting original file size."""
        messages = ["Message 1"] * 100
        file_storage.save_daily_original("Test Room", "2024-01-01", messages)

        size = file_storage.get_original_file_size("Test Room", "2024-01-01")
        assert size > 0

    def test_get_original_file_size_nonexistent(self, file_storage):
        """Test getting size of non-existent file."""
        size = file_storage.get_original_file_size("Test Room", "2099-01-01")
        assert size == 0


class TestBackupAndRestore:
    """Test backup and restore functionality."""

    def test_create_full_backup(self, file_storage):
        """Test creating full backup."""
        # Create some data
        file_storage.save_daily_original("Test Room", "2024-01-01", ["Msg 1"])
        file_storage.save_daily_summary("Test Room", "2024-01-01", "# Summary")

        backup_path = file_storage.create_full_backup()
        assert backup_path is not None
        assert backup_path.exists()

    def test_get_backup_list(self, file_storage):
        """Test getting backup list."""
        # Create backup
        file_storage.save_daily_original("Test Room", "2024-01-01", ["Msg 1"])
        file_storage.create_full_backup()

        backups = file_storage.get_backup_list()
        assert len(backups) >= 1
        assert 'name' in backups[0]
        assert 'path' in backups[0]
        assert 'created' in backups[0]

    def test_backup_room(self, file_storage):
        """Test backing up single room."""
        file_storage.save_daily_original("Test Room", "2024-01-01", ["Msg 1"])

        backup_path = file_storage.backup_room("Test Room")
        assert backup_path is not None
        assert backup_path.exists()

    def test_restore_from_backup(self, file_storage):
        """Test restoring from backup."""
        # Create original data
        file_storage.save_daily_original("Test Room", "2024-01-01", ["Original"])
        backup_path = file_storage.create_full_backup()

        # Modify data
        file_storage.save_daily_original("Test Room", "2024-01-01", ["Modified"])

        # Restore
        restored = file_storage.restore_from_backup(backup_path)
        assert restored is True

        # Check restored content
        messages = file_storage.load_daily_original("Test Room", "2024-01-01")
        assert "Original" in str(messages)


class TestHelperMethods:
    """Test internal helper methods."""

    def test_sanitize_name(self, file_storage):
        """Test name sanitization."""
        assert file_storage._sanitize_name("Test Room") == "Test_Room"
        assert file_storage._sanitize_name("Room/Name\\Test") == "RoomNameTest"
        assert file_storage._sanitize_name("Room<>:\"|?*Name") == "RoomName"

    def test_merge_messages(self, file_storage):
        """Test message merging and deduplication."""
        existing = ["Msg 1", "Msg 2"]
        new = ["Msg 2", "Msg 3"]

        merged = file_storage._merge_messages(existing, new)
        assert len(merged) == 3
        assert "Msg 1" in merged
        assert "Msg 2" in merged
        assert "Msg 3" in merged

    def test_format_original_content(self, file_storage):
        """Test original content formatting."""
        messages = ["Msg 1", "Msg 2"]
        content = file_storage._format_original_content("Test Room", "2024-01-01", messages)

        assert "Test Room" in content
        assert "2024-01-01" in content
        assert "Msg 1" in content
        assert "Msg 2" in content
        assert "---" in content

    def test_format_summary_content(self, file_storage):
        """Test summary content formatting."""
        summary = "# Test\n\nContent"
        content = file_storage._format_summary_content("Test Room", "2024-01-01", summary, "test")

        assert "Test Room" in content
        assert "2024-01-01" in content
        assert "test" in content
        assert "# Test" in content


class TestFileStorageSingleton:
    """Test FileStorage singleton pattern."""

    def test_get_storage_returns_same_instance(self):
        """Test that get_storage returns same instance."""
        storage1 = get_storage()
        storage2 = get_storage()
        assert storage1 is storage2
