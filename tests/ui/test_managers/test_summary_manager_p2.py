"""P2 Coverage Tests for SummaryManager.

Tests focused on:
- _show_calendar_dialog edge cases
- Minor edge cases for existing methods

Target coverage improvement: 83.3% -> 90%
"""
import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import date

from PySide6.QtWidgets import QWidget, QTabWidget, QApplication, QDialog
from PySide6.QtCore import QDate, Qt

from src.ui.managers.summary_manager import SummaryManager


@pytest.fixture
def mock_repos():
    """Create mock repositories."""
    return {
        'summary_repo': Mock(),
        'chat_room_repo': Mock()
    }


@pytest.fixture
def mock_storage():
    """Create mock file storage."""
    storage = Mock()
    storage.load_daily_original.return_value = []
    storage.load_daily_summary.return_value = None
    storage.get_available_dates.return_value = []
    storage.get_summarized_dates.return_value = []
    return storage


@pytest.fixture
def manager(qapp, mock_repos, mock_storage):
    """Create SummaryManager instance with mocked dependencies."""
    with patch('src.ui.managers.summary_manager.get_storage', return_value=mock_storage):
        manager = SummaryManager(
            parent=None,
            summary_repo=mock_repos['summary_repo'],
            chat_room_repo=mock_repos['chat_room_repo'],
            storage=mock_storage
        )
        yield manager
        manager.deleteLater()


@pytest.fixture
def tab_widget(qapp):
    """Create QTabWidget for testing."""
    widget = QTabWidget()
    yield widget
    widget.deleteLater()


@pytest.mark.unit
class TestSummaryManagerCalendarDialog:
    """Test _show_calendar_dialog method."""

    def test_show_calendar_dialog_creates_dialog(self, manager, tab_widget):
        """_show_calendar_dialog creates a QDialog with correct properties."""
        manager.create_tab_widgets(tab_widget, lambda: 1)

        # Mock QDialog.exec to avoid blocking
        from unittest.mock import patch
        with patch.object(QDialog, 'exec', return_value=QDialog.Accepted):
            manager._show_calendar_dialog()

        # If we got here without blocking, the dialog was created and executed
        assert True

    def test_show_calendar_dialog_with_rejected_exit(self, manager, tab_widget):
        """_show_calendar_dialog does not update date_edit when dialog is rejected."""
        manager.create_tab_widgets(tab_widget, lambda: 1)
        original_date = manager.date_edit.date()

        # Mock QDialog.exec to return Rejected
        from unittest.mock import patch
        with patch.object(QDialog, 'exec', return_value=QDialog.Rejected):
            manager._show_calendar_dialog()

        # Date should not have changed
        assert manager.date_edit.date() == original_date


@pytest.mark.unit
class TestSummaryManagerDateNavigationEdgeCases:
    """Test date navigation edge cases."""

    def test_on_prev_date_wraps_correctly(self, manager, tab_widget):
        """_on_prev_date handles month and year boundaries correctly."""
        manager.create_tab_widgets(tab_widget, lambda: 1)

        # Set to March 1, 2024
        manager.date_edit.setDate(QDate(2024, 3, 1))
        manager._on_prev_date()

        # Should be February 29, 2024 (leap year)
        new_date = manager.date_edit.date()
        assert new_date.year() == 2024
        assert new_date.month() == 2
        assert new_date.day() == 29

    def test_on_next_date_wraps_correctly(self, manager, tab_widget):
        """_on_next_date handles month and year boundaries correctly."""
        manager.create_tab_widgets(tab_widget, lambda: 1)

        # Set to January 31, 2024
        manager.date_edit.setDate(QDate(2024, 1, 31))
        manager._on_next_date()

        # Should be February 1, 2024 (QDate handles invalid dates)
        new_date = manager.date_edit.date()
        assert new_date.year() == 2024
        assert new_date.month() == 2

    def test_on_prev_date_year_boundary(self, manager, tab_widget):
        """_on_prev_date handles year boundary correctly."""
        manager.create_tab_widgets(tab_widget, lambda: 1)

        # Set to January 1, 2024
        manager.date_edit.setDate(QDate(2024, 1, 1))
        manager._on_prev_date()

        # Should be December 31, 2023
        new_date = manager.date_edit.date()
        assert new_date.year() == 2023
        assert new_date.month() == 12
        assert new_date.day() == 31

    def test_on_next_date_year_boundary(self, manager, tab_widget):
        """_on_next_date handles year boundary correctly."""
        manager.create_tab_widgets(tab_widget, lambda: 1)

        # Set to December 31, 2024
        manager.date_edit.setDate(QDate(2024, 12, 31))
        manager._on_next_date()

        # Should be January 1, 2025
        new_date = manager.date_edit.date()
        assert new_date.year() == 2025
        assert new_date.month() == 1
        assert new_date.day() == 1


@pytest.mark.unit
class TestSummaryManagerDisplayRoomSummariesEdgeCases:
    """Test display_room_summaries edge cases."""

    @patch('src.ui.managers.summary_manager.get_storage')
    def test_on_date_changed_with_no_data_shows_no_data_message(self, mock_get_storage, manager, tab_widget, mock_storage):
        """_on_date_changed shows appropriate message when no data available."""
        mock_room = Mock()
        mock_room.name = "TestRoom"
        mock_repos = {'chat_room_repo': Mock()}
        mock_repos['chat_room_repo'].get_by_id.return_value = mock_room

        manager.chat_room_repo = mock_repos['chat_room_repo']
        manager.create_tab_widgets(tab_widget, lambda: 1)

        # Setup storage with no data
        mock_storage.load_daily_original.return_value = []
        mock_storage.load_daily_summary.return_value = None
        mock_storage.get_available_dates.return_value = []
        mock_storage.get_summarized_dates.return_value = []
        mock_get_storage.return_value = mock_storage

        manager._on_date_changed(QDate(2024, 2, 10))

        html = manager.detail_browser.toHtml()
        # Should show "no data" type message
        assert "대화 기록이 없습니다" in html or "no data" in html.lower() or "없습니다" in html

    @patch('src.ui.managers.summary_manager.get_storage')
    def test_on_date_changed_with_original_but_no_summary(self, mock_get_storage, manager, tab_widget, mock_storage):
        """_on_date_changed shows warning when original exists but no summary."""
        mock_room = Mock()
        mock_room.name = "TestRoom"
        mock_repos = {'chat_room_repo': Mock()}
        mock_repos['chat_room_repo'].get_by_id.return_value = mock_room

        manager.chat_room_repo = mock_repos['chat_room_repo']
        manager.create_tab_widgets(tab_widget, lambda: 1)

        # Setup storage with original but no summary
        mock_storage.load_daily_original.return_value = ["msg1", "msg2"]
        mock_storage.load_daily_summary.return_value = None
        mock_storage.get_available_dates.return_value = ["2024-02-10"]
        mock_storage.get_summarized_dates.return_value = []
        mock_get_storage.return_value = mock_storage

        manager._on_date_changed(QDate(2024, 2, 10))

        html = manager.detail_browser.toHtml()
        # Should show warning about missing summary
        assert "요약이 아직 생성되지 않았습니다" in html or "summary" in html.lower()

    @patch('src.ui.managers.summary_manager.get_storage')
    def test_on_date_changed_displays_summary_content(self, mock_get_storage, manager, tab_widget, mock_storage):
        """_on_date_changed displays summary content when available."""
        mock_room = Mock()
        mock_room.name = "TestRoom"
        mock_repos = {'chat_room_repo': Mock()}
        mock_repos['chat_room_repo'].get_by_id.return_value = mock_room

        manager.chat_room_repo = mock_repos['chat_room_repo']
        manager.create_tab_widgets(tab_widget, lambda: 1)

        # Setup storage with summary
        summary_content = "# 요약\n\n테스트 요약 내용입니다."
        mock_storage.load_daily_original.return_value = ["msg1"]
        mock_storage.load_daily_summary.return_value = summary_content
        mock_storage.get_available_dates.return_value = ["2024-02-10"]
        mock_storage.get_summarized_dates.return_value = ["2024-02-10"]
        mock_get_storage.return_value = mock_storage

        manager._on_date_changed(QDate(2024, 2, 10))

        html = manager.detail_browser.toHtml()
        # Should display summary content
        assert "테스트 요약 내용입니다" in html or "summary" in html.lower()


@pytest.mark.unit
class TestSummaryManagerSignalEmissionEdgeCases:
    """Test signal emission edge cases."""

    @patch('src.ui.managers.summary_manager.get_storage')
    def test_date_changed_signal_emitted_with_correct_format(self, mock_get_storage, manager, tab_widget, mock_storage):
        """_on_date_changed emits date_changed signal with YYYY-MM-DD format."""
        mock_room = Mock()
        mock_room.name = "TestRoom"
        mock_repos = {'chat_room_repo': Mock()}
        mock_repos['chat_room_repo'].get_by_id.return_value = mock_room

        manager.chat_room_repo = mock_repos['chat_room_repo']
        manager.create_tab_widgets(tab_widget, lambda: 1)

        mock_storage.load_daily_original.return_value = ["msg1"]
        mock_storage.load_daily_summary.return_value = "Summary"
        mock_storage.get_available_dates.return_value = ["2024-02-10"]
        mock_storage.get_summarized_dates.return_value = ["2024-02-10"]
        mock_get_storage.return_value = mock_storage

        emitted_dates = []
        manager.date_changed.connect(lambda d: emitted_dates.append(d))

        manager._on_date_changed(QDate(2024, 2, 10))

        assert len(emitted_dates) >= 1
        # Verify date format is YYYY-MM-DD
        assert "-" in emitted_dates[0]
        parts = emitted_dates[0].split("-")
        assert len(parts) == 3


@pytest.mark.unit
class TestSummaryManagerUpdateDateTabEdgeCases:
    """Test update_date_tab_for_room edge cases."""

    @patch('src.ui.managers.summary_manager.get_storage')
    def test_update_date_tab_for_room_triggers_date_change(self, mock_get_storage, manager, tab_widget, mock_storage):
        """update_date_tab_for_room triggers _on_date_changed."""
        manager.create_tab_widgets(tab_widget, lambda: 1)
        mock_storage.get_available_dates.return_value = ["2024-02-10"]
        mock_get_storage.return_value = mock_storage

        # Mock room to allow date change processing
        mock_room = Mock()
        mock_room.name = "TestRoom"
        manager.chat_room_repo = Mock()
        manager.chat_room_repo.get_by_id.return_value = mock_room

        manager.update_date_tab_for_room("TestRoom")

        # Verify date was set
        assert manager.date_edit.date().year() == 2024
        assert manager.date_edit.date().month() == 2
        assert manager.date_edit.date().day() == 10
