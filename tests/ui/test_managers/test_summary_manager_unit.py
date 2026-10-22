"""
Unit tests for SummaryManager class.

These tests verify the SummaryManager behavior using mocked dependencies
to isolate the manager logic from Qt UI components.

Target: src/ui/managers/summary_manager.py

Test Coverage:
- SummaryManager initialization
- UI widget creation
- Date navigation
- Summary display
- Signal emissions
- Room selection handling
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from pathlib import Path
from datetime import date

from PySide6.QtWidgets import QWidget, QTabWidget, QApplication
from PySide6.QtCore import QDate, Signal

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


class TestSummaryManagerInitialization:
    """Test SummaryManager initialization behavior."""

    def test_manager_inherits_from_qwidget(self, manager):
        """
        CAPTURE: SummaryManager inherits from QWidget.
        """
        assert isinstance(manager, QWidget)

    def test_manager_has_signals(self, manager):
        """
        CAPTURE: SummaryManager has defined signals.
        """
        assert hasattr(manager, 'summary_requested')
        assert hasattr(manager, 'date_changed')

    def test_manager_initializes_with_none_state(self, manager):
        """
        CAPTURE: SummaryManager initializes with None room state.
        """
        assert manager._current_room_id is None
        assert manager._current_room_name is None

    def test_manager_stores_repositories(self, manager, mock_repos):
        """
        CAPTURE: SummaryManager stores repository references.
        """
        assert manager.summary_repo is mock_repos['summary_repo']
        assert manager.chat_room_repo is mock_repos['chat_room_repo']


class TestSummaryManagerTabCreation:
    """Test tab widget creation."""

    def test_create_tab_widgets_creates_two_tabs(self, manager, tab_widget):
        """
        CAPTURE: create_tab_widgets creates exactly 2 tabs.
        """
        manager.create_tab_widgets(tab_widget, lambda: 1)

        assert tab_widget.count() == 2

    def test_create_tab_widgets_tab_names(self, manager, tab_widget):
        """
        CAPTURE: create_tab_widgets creates tabs with expected names.
        """
        manager.create_tab_widgets(tab_widget, lambda: 1)

        tab_names = [tab_widget.tabText(i) for i in range(tab_widget.count())]
        assert "대시보드" in tab_names[0] or "dashboard" in tab_names[0].lower()
        assert "날짜별" in tab_names[1] or "date" in tab_names[1].lower()

    def test_create_tab_widgets_stores_callback(self, manager, tab_widget):
        """
        CAPTURE: create_tab_widgets stores room_id_callback.
        """
        manager.create_tab_widgets(tab_widget, lambda: 123)

        assert manager._room_id_callback() == 123

    def test_create_tab_widgets_creates_ui_components(self, manager, tab_widget):
        """
        CAPTURE: create_tab_widgets creates all UI components.
        """
        manager.create_tab_widgets(tab_widget, lambda: 1)

        assert manager.summary_browser is not None
        assert manager.detail_browser is not None
        assert manager.date_edit is not None
        assert manager.date_info_label is not None
        assert manager.prev_date_btn is not None
        assert manager.next_date_btn is not None
        assert manager.calendar_btn is not None
        assert manager.generate_btn is not None


class TestSummaryManagerDateNavigation:
    """Test date navigation functionality."""

    def test_on_prev_date_decrements_date(self, manager, tab_widget):
        """
        CAPTURE: _on_prev_date decrements date by one day.
        """
        manager.create_tab_widgets(tab_widget, lambda: 1)
        manager.date_edit.setDate(QDate(2024, 2, 10))

        manager._on_prev_date()

        new_date = manager.date_edit.date()
        assert new_date.year() == 2024
        assert new_date.month() == 2
        assert new_date.day() == 9

    def test_on_next_date_increments_date(self, manager, tab_widget):
        """
        CAPTURE: _on_next_date increments date by one day.
        """
        manager.create_tab_widgets(tab_widget, lambda: 1)
        manager.date_edit.setDate(QDate(2024, 2, 10))

        manager._on_next_date()

        new_date = manager.date_edit.date()
        assert new_date.year() == 2024
        assert new_date.month() == 2
        assert new_date.day() == 11


class TestSummaryManagerDateChanged:
    """Test date change handling."""

    def test_on_date_changed_with_no_room_shows_message(self, manager, tab_widget):
        """
        CAPTURE: _on_date_changed shows message when no room selected.
        """
        manager.create_tab_widgets(tab_widget, lambda: None)

        manager._on_date_changed(QDate(2024, 2, 10))

        # Verify detail_browser shows room selection message
        html = manager.detail_browser.toHtml()
        assert "채팅방을 선택하세요" in html or "select" in html.lower()

    @patch('src.ui.managers.summary_manager.get_storage')
    def test_on_date_changed_loads_storage_data(self, mock_get_storage, manager, tab_widget, mock_storage):
        """
        CAPTURE: _on_date_changed loads data from file storage.
        """
        mock_room = Mock()
        mock_room.name = "TestRoom"
        mock_repos = {'chat_room_repo': Mock()}
        mock_repos['chat_room_repo'].get_by_id.return_value = mock_room

        manager.chat_room_repo = mock_repos['chat_room_repo']
        manager.create_tab_widgets(tab_widget, lambda: 1)
        mock_get_storage.return_value = mock_storage

        manager._on_date_changed(QDate(2024, 2, 10))

        # Verify storage methods were called
        mock_storage.load_daily_original.assert_called_once()
        mock_storage.load_daily_summary.assert_called_once()
        mock_storage.get_available_dates.assert_called_once()
        mock_storage.get_summarized_dates.assert_called_once()

    @patch('src.ui.managers.summary_manager.get_storage')
    def test_on_date_changed_emits_signal(self, mock_get_storage, manager, tab_widget, mock_storage):
        """
        CAPTURE: _on_date_changed emits date_changed signal.

        Note: Signal is only emitted when both room and data are available.
        This test verifies the signal emission path.
        """
        mock_room = Mock()
        mock_room.name = "TestRoom"
        mock_repos = {'chat_room_repo': Mock()}
        mock_repos['chat_room_repo'].get_by_id.return_value = mock_room

        manager.chat_room_repo = mock_repos['chat_room_repo']
        manager.create_tab_widgets(tab_widget, lambda: 1)
        mock_get_storage.return_value = mock_storage

        # Setup storage with available data to trigger signal emission
        mock_storage.load_daily_original.return_value = ["msg1"]
        mock_storage.load_daily_summary.return_value = "Test summary"
        mock_storage.get_available_dates.return_value = ["2024-02-10"]
        mock_storage.get_summarized_dates.return_value = ["2024-02-10"]

        # Track signal emissions
        emitted_dates = []
        manager.date_changed.connect(lambda d: emitted_dates.append(d))

        manager._on_date_changed(QDate(2024, 2, 10))

        # Signal should be emitted when data is available
        assert len(emitted_dates) >= 1
        if emitted_dates:
            assert emitted_dates[0] == "2024-02-10"

    @patch('src.ui.managers.summary_manager.get_storage')
    def test_on_date_changed_updates_date_info_label(self, mock_get_storage, manager, tab_widget, mock_storage):
        """
        CAPTURE: _on_date_changed updates date_info_label with status.
        """
        mock_room = Mock()
        mock_room.name = "TestRoom"
        mock_repos = {'chat_room_repo': Mock()}
        mock_repos['chat_room_repo'].get_by_id.return_value = mock_room

        manager.chat_room_repo = mock_repos['chat_room_repo']
        manager.create_tab_widgets(tab_widget, lambda: 1)

        # Setup storage with data
        mock_storage.load_daily_original.return_value = ["msg1", "msg2"]
        mock_storage.load_daily_summary.return_value = "Test summary"
        mock_storage.get_available_dates.return_value = ["2024-02-10"]
        mock_storage.get_summarized_dates.return_value = ["2024-02-10"]
        mock_get_storage.return_value = mock_storage

        manager._on_date_changed(QDate(2024, 2, 10))

        # Verify date_info_label was updated
        label_text = manager.date_info_label.text()
        assert "2024-02-10" in label_text


class TestSummaryManagerDisplaySummaries:
    """Test summary display functionality."""

    def test_display_room_summaries_with_no_stats(self, manager, tab_widget):
        """
        CAPTURE: display_room_summaries shows message when no stats.
        """
        manager.create_tab_widgets(tab_widget, lambda: 1)

        manager.display_room_summaries(1, {}, "TestRoom")

        html = manager.summary_browser.toHtml()
        assert "데이터가 없습니다" in html or "no data" in html.lower()

    def test_display_room_summaries_with_summaries(self, manager, tab_widget):
        """
        CAPTURE: display_room_summaries shows summaries from repository.
        """
        manager.create_tab_widgets(tab_widget, lambda: 1)

        # Mock summary
        mock_summary = Mock()
        mock_summary.summary_date = "2024-02-10"
        mock_summary.summary_type = "daily"
        mock_summary.content = "Test summary content"

        manager.summary_repo.get_by_room.return_value = [mock_summary]

        manager.display_room_summaries(1, {'total_messages': 100}, "TestRoom")

        # Verify repo was called
        manager.summary_repo.get_by_room.assert_called_once_with(1)

    def test_display_room_summaries_without_summaries_shows_stats(self, manager, tab_widget):
        """
        CAPTURE: display_room_summaries shows stats when no summaries.
        """
        manager.create_tab_widgets(tab_widget, lambda: 1)
        manager.summary_repo.get_by_room.return_value = []

        stats = {
            'total_messages': 1000,
            'unique_senders': 5,
            'first_date': '2024-02-01',
            'last_date': '2024-02-10'
        }

        manager.display_room_summaries(1, stats, "TestRoom")

        html = manager.summary_browser.toHtml()
        assert "1000" in html or "1,000" in html

    def test_clear_summaries(self, manager, tab_widget):
        """
        CAPTURE: clear_summaries displays selection message.
        """
        manager.create_tab_widgets(tab_widget, lambda: 1)

        manager.clear_summaries()

        html = manager.summary_browser.toHtml()
        assert "채팅방을 선택하세요" in html or "select" in html.lower()


class TestSummaryManagerUpdateDateTab:
    """Test date tab update functionality."""

    @patch('src.ui.managers.summary_manager.get_storage')
    def test_update_date_tab_for_room_with_dates(self, mock_get_storage, manager, tab_widget, mock_storage):
        """
        CAPTURE: update_date_tab_for_room sets date to latest available.
        """
        manager.create_tab_widgets(tab_widget, lambda: 1)
        mock_storage.get_available_dates.return_value = ["2024-02-01", "2024-02-10"]
        mock_get_storage.return_value = mock_storage

        manager.update_date_tab_for_room("TestRoom")

        # Should be set to latest date
        date = manager.date_edit.date()
        assert date.year() == 2024
        assert date.month() == 2
        assert date.day() == 10

    @patch('src.ui.managers.summary_manager.get_storage')
    def test_update_date_tab_for_room_without_dates(self, mock_get_storage, manager, tab_widget, mock_storage):
        """
        CAPTURE: update_date_tab_for_room sets to current date when no dates available.
        """
        manager.create_tab_widgets(tab_widget, lambda: 1)
        mock_storage.get_available_dates.return_value = []
        mock_get_storage.return_value = mock_storage

        manager.update_date_tab_for_room("TestRoom")

        # Should be set to current date
        date = manager.date_edit.date()
        current = QDate.currentDate()
        assert date == current


class TestSummaryManagerSignals:
    """Test signal emissions."""

    def test_generate_button_emits_signal(self, manager, tab_widget):
        """
        CAPTURE: generate button click emits summary_requested signal.
        """
        manager.create_tab_widgets(tab_widget, lambda: 1)

        # Track signal emissions
        emitted = []
        manager.summary_requested.connect(lambda: emitted.append(True))

        manager.generate_btn.click()

        assert len(emitted) == 1


class TestSummaryManagerCalendarDialog:
    """Test calendar dialog functionality."""

    def test_calendar_dialog_exists(self, manager, tab_widget):
        """
        CAPTURE: _show_calendar_dialog method exists and is callable.
        """
        manager.create_tab_widgets(tab_widget, lambda: 1)

        # Just verify the method exists and can be called
        # (actual dialog testing is complex due to exec() blocking)
        assert hasattr(manager, '_show_calendar_dialog')
        assert callable(manager._show_calendar_dialog)
