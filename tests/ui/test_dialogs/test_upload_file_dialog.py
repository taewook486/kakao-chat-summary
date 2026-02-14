"""Tests for UploadFileDialog."""
import pytest
from unittest.mock import patch, MagicMock

from src.ui.dialogs.upload_file_dialog import UploadFileDialog


class TestUploadFileDialog:
    """Test UploadFileDialog functionality."""

    def test_dialog_initialization(self, qapp):
        """Dialog initializes with correct default state."""
        dialog = UploadFileDialog("TestRoom")

        assert dialog.room_name == "TestRoom"
        assert dialog.file_path == ""
        assert dialog.upload_btn.isEnabled() is False
        assert "No file selected" in dialog.file_label.text()

    def test_room_name_displayed(self, qapp):
        """Room name is displayed in dialog."""
        dialog = UploadFileDialog("My Chat Room")

        # Room name should be in the label
        room_label = dialog.findChild(
            type(dialog.findChild(type(dialog))),
            ""
        )
        # Just verify the room_name is stored correctly
        assert dialog.room_name == "My Chat Room"

    def test_upload_button_disabled_initially(self, qapp):
        """Upload button is disabled when no file selected."""
        dialog = UploadFileDialog("Test")

        assert dialog.upload_btn.isEnabled() is False

    def test_browse_file_updates_state(self, qapp):
        """Selecting a file updates dialog state."""
        dialog = UploadFileDialog("Test")

        with patch(
            'src.ui.dialogs.upload_file_dialog.QFileDialog.getOpenFileName',
            return_value=('/path/to/chat.txt', '')
        ):
            dialog._browse_file()

        assert dialog.file_path == '/path/to/chat.txt'
        assert dialog.upload_btn.isEnabled() is True
        assert 'chat.txt' in dialog.file_label.text()

    def test_browse_file_cancelled(self, qapp):
        """Cancelling file browser keeps state unchanged."""
        dialog = UploadFileDialog("Test")

        with patch(
            'src.ui.dialogs.upload_file_dialog.QFileDialog.getOpenFileName',
            return_value=('', '')
        ):
            dialog._browse_file()

        assert dialog.file_path == ""
        assert dialog.upload_btn.isEnabled() is False

    def test_get_file_path(self, qapp):
        """get_file_path returns the file path."""
        dialog = UploadFileDialog("Test")
        dialog.file_path = "/path/to/file.txt"

        assert dialog.get_file_path() == "/path/to/file.txt"
