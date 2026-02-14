"""Tests for CreateRoomDialog."""
import pytest
from PySide6.QtCore import Qt

from src.ui.dialogs.create_room_dialog import CreateRoomDialog


class TestCreateRoomDialog:
    """Test CreateRoomDialog functionality."""

    def test_dialog_initialization(self, qapp):
        """Dialog initializes with correct default state."""
        dialog = CreateRoomDialog()

        assert dialog.room_name == ""
        assert dialog.create_btn.isEnabled() is False
        assert dialog.name_input.text() == ""

    def test_create_button_enables_with_input(self, qapp):
        """Create button enables when text is entered."""
        dialog = CreateRoomDialog()

        assert dialog.create_btn.isEnabled() is False

        dialog.name_input.setText("Test Room")

        assert dialog.create_btn.isEnabled() is True

    def test_create_button_disables_with_whitespace(self, qapp):
        """Create button disables when only whitespace entered."""
        dialog = CreateRoomDialog()

        dialog.name_input.setText("   ")

        assert dialog.create_btn.isEnabled() is False

    def test_accept_sets_room_name(self, qapp):
        """Accepting dialog sets room name."""
        dialog = CreateRoomDialog()
        dialog.name_input.setText("My Room")

        dialog._on_create()

        assert dialog.room_name == "My Room"

    def test_accept_ignores_whitespace(self, qapp):
        """Accept with whitespace only does nothing."""
        dialog = CreateRoomDialog()
        dialog.name_input.setText("   ")

        # Should not raise and room_name should stay empty
        dialog._on_create()

        assert dialog.room_name == ""

    def test_get_room_name(self, qapp):
        """get_room_name returns the room name."""
        dialog = CreateRoomDialog()
        dialog.room_name = "Test"

        assert dialog.get_room_name() == "Test"
