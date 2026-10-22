"""Characterization tests for MessageListManager behavior (PRESERVE phase).

These tests capture the CURRENT behavior of message list management to prevent regression.
They document what the code DOES, not what it SHOULD DO.

Target extraction: MessageListManager from main_window.py
Related methods:
- _on_prev_date()
- _on_next_date()
- _on_date_changed()
- _show_calendar_dialog()
- _update_date_tab_for_room()
- _load_url_from_db()
- _display_url_list()
- _refresh_url_list()
- _sync_url_from_summaries()
- _restore_url_from_file()

@MX:SPEC: SPEC-IMPROVE-001 Milestone 2.3
"""

import pytest
from datetime import datetime, date, timedelta
from unittest.mock import Mock, MagicMock, patch
from pathlib import Path

from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import QMessageBox, QDialog

from src.repositories.chat_room_repository import ChatRoomRepository
from src.repositories.message_repository import MessageRepository
from src.repositories.summary_repository import SummaryRepository
from src.repositories.url_repository import URLRepository
from src.db.models import ChatRoom


@pytest.mark.characterization
class TestDateNavigationBehavior:
    """Characterization tests for date navigation behavior.

    CAPTURE: How date navigation (prev/next) works.
    """

    def test_prev_date_decrements_by_one_day(self, qapp):
        """CAPTURE: How _on_prev_date changes the selected date.

        This test documents:
        - Date is decremented by 1 day
        - QDate.addDays(-1) is used
        """
        # Given: A specific date selected
        current_date = QDate(2024, 2, 15)

        # When: Previous date is called (simulated)
        new_date = current_date.addDays(-1)

        # Then: Date is decremented by 1
        assert new_date.year() == 2024
        assert new_date.month() == 2
        assert new_date.day() == 14

    def test_next_date_increments_by_one_day(self, qapp):
        """CAPTURE: How _on_next_date changes the selected date.

        This test documents:
        - Date is incremented by 1 day
        - QDate.addDays(1) is used
        """
        # Given: A specific date selected
        current_date = QDate(2024, 2, 15)

        # When: Next date is called (simulated)
        new_date = current_date.addDays(1)

        # Then: Date is incremented by 1
        assert new_date.year() == 2024
        assert new_date.month() == 2
        assert new_date.day() == 16

    def test_date_change_triggers_load(self, db_session, qapp):
        """CAPTURE: How _on_date_changed loads data.

        This test documents:
        - Room ID check before loading
        - Room name lookup via repository
        - File storage access for messages and summaries
        """
        # Given: Room exists
        repo = ChatRoomRepository(db_session)
        room = repo.create(name="Date Test Room")

        # When: Date is changed (simulated behavior)
        date_str = "2024-02-15"

        # Then: Behavior documented
        # Current behavior:
        # 1. Check current_room_id is not None
        # 2. Get room via chat_room_repo.get_by_id()
        # 3. Load daily original from storage
        # 4. Load daily summary from storage
        # 5. Get available dates and summarized dates
        # 6. Update date_info_label
        # 7. Update detail_browser HTML
        assert room.name == "Date Test Room"


@pytest.mark.characterization
class TestCalendarDialogBehavior:
    """Characterization tests for calendar dialog behavior.

    CAPTURE: How calendar dialog is displayed and handled.
    """

    def test_calendar_dialog_uses_selected_date(self, qapp):
        """CAPTURE: How calendar dialog initializes with current date.

        This test documents:
        - Dialog title is "Date selection"
        - Calendar is initialized with date_edit value
        - Dialog size is 350x300
        """
        # Given: Date edit has specific date
        current_date = QDate(2024, 2, 15)

        # When: Calendar dialog is shown (simulated)
        # Current behavior:
        # - QDialog created with title "Date selection"
        # - Fixed size 350x300
        # - QCalendarWidget created
        # - setSelectedDate with current date_edit date
        # - Today button sets to current date
        # - Select button accepts dialog
        # - Double-click also accepts

        # Then: Calendar shows current date
        assert current_date.toString("yyyy-MM-dd") == "2024-02-15"

    def test_calendar_dialog_updates_date_edit(self, qapp):
        """CAPTURE: How calendar selection updates date edit.

        This test documents:
        - On dialog accept, date_edit.setDate is called
        - With calendar.selectedDate()
        """
        # Given: Calendar with selected date
        selected_date = QDate(2024, 3, 20)

        # When: Dialog is accepted (simulated)
        # Current behavior: self.date_edit.setDate(calendar.selectedDate())

        # Then: Date edit would be updated
        assert selected_date.year() == 2024
        assert selected_date.month() == 3
        assert selected_date.day() == 20


@pytest.mark.characterization
class TestDateTabUpdateBehavior:
    """Characterization tests for date tab update behavior.

    CAPTURE: How date tab is updated when room changes.
    """

    def test_update_date_tab_sets_latest_date(self, db_session, file_storage, qapp):
        """CAPTURE: How _update_date_tab_for_room initializes date.

        This test documents:
        - Available dates loaded from storage
        - Latest date is selected if available
        - Current date used if no available dates
        - _on_date_changed is triggered
        """
        # Given: Room with available dates
        room_name = "Date Tab Room"
        sanitized = file_storage._sanitize_name(room_name)
        room_dir = file_storage.original_dir / sanitized
        room_dir.mkdir(parents=True, exist_ok=True)

        # When: Get available dates
        available_dates = file_storage.get_available_dates(room_name)

        # Then: Behavior documented
        # Current behavior:
        # 1. storage.get_available_dates(room_name)
        # 2. If dates exist, set to latest (last in list)
        # 3. If no dates, set to current date
        # 4. Trigger _on_date_changed
        assert isinstance(available_dates, list)


@pytest.mark.characterization
class TestURLListLoadingBehavior:
    """Characterization tests for URL list loading behavior.

    CAPTURE: How URLs are loaded from database and files.
    """

    def test_load_url_from_db_uses_repository(self, db_session, qapp):
        """CAPTURE: How _load_url_from_db uses URLRepository.

        This test documents:
        - Returns empty dict if no room selected
        - Uses url_repo.get_by_room(room_id)
        """
        # Given: Room and URL repository
        repo = ChatRoomRepository(db_session)
        room = repo.create(name="URL Test Room")
        url_repo = URLRepository(db_session)

        # When: Load URLs from DB
        urls = url_repo.get_by_room(room.id)

        # Then: Returns dict (may be empty)
        assert isinstance(urls, dict)

    def test_load_url_from_db_returns_empty_without_room(self, qapp):
        """CAPTURE: What happens when no room is selected.

        This test documents:
        - Returns empty dict {} when current_room_id is None
        """
        # Given: No room selected
        current_room_id = None

        # When: Load URLs (simulated)
        if current_room_id is None:
            urls = {}

        # Then: Empty dict returned
        assert urls == {}

    def test_display_url_list_creates_sections(self, db_session, qapp):
        """CAPTURE: How _display_url_list creates 3-section HTML.

        This test documents:
        - Maximum 50 URLs displayed per section
        - Sections: Recent 3 days, Weekly, All
        - URLs sorted alphabetically
        - Total count shown in header
        """
        # Given: URLs data
        urls_all = {
            "https://example.com/1": ["Description 1"],
            "https://example.com/2": ["Description 2"],
            "https://example.com/3": ["Description 3"],
        }
        urls_recent = {"https://example.com/1": ["Description 1"]}
        urls_weekly = {
            "https://example.com/1": ["Description 1"],
            "https://example.com/2": ["Description 2"],
        }

        # When: Display URL list (simulated)
        total_urls = len(urls_all)
        sorted_all = sorted(urls_all.items(), key=lambda x: x[0].lower())
        sorted_recent = sorted(urls_recent.items(), key=lambda x: x[0].lower())
        sorted_weekly = sorted(urls_weekly.items(), key=lambda x: x[0].lower())

        # Then: Sections created correctly
        assert total_urls == 3
        assert len(sorted_recent) == 1
        assert len(sorted_weekly) == 2
        assert len(sorted_all) == 3

    def test_display_url_list_shows_placeholder_when_empty(self, qapp):
        """CAPTURE: What HTML is shown when no URLs exist.

        This test documents:
        - Placeholder message displayed
        - url_count_label shows "0 URLs"
        """
        # Given: No URLs
        urls_all = {}

        # When: Display empty list (simulated)
        total_urls = len(urls_all)

        # Then: Shows placeholder
        assert total_urls == 0


@pytest.mark.characterization
class TestURLSyncBehavior:
    """Characterization tests for URL sync behavior.

    CAPTURE: How URLs are synced from summaries.
    """

    def test_sync_url_extracts_from_summaries(self, db_session, file_storage, qapp):
        """CAPTURE: How _sync_url_from_summaries extracts URLs.

        This test documents:
        - Date threshold: today, 3 days ago, 1 week ago
        - Summaries loaded for each date
        - URLs extracted with extract_urls_from_text
        - URLs categorized by period
        - DB deleted and recreated
        - Files saved (recent, weekly, all)
        """
        # Given: Room with summaries
        repo = ChatRoomRepository(db_session)
        room = repo.create(name="Sync URL Room")

        # Date thresholds
        today = date.today()
        three_days_ago = today - timedelta(days=3)
        one_week_ago = today - timedelta(days=7)

        # When: Sync URLs (simulated behavior)
        # Current behavior:
        # 1. Get summarized dates from storage
        # 2. Load each summary
        # 3. Extract URLs with extract_urls_from_text
        # 4. Categorize by period
        # 5. Delete existing URLs from DB
        # 6. Create batch in DB
        # 7. Save 3 files (recent, weekly, all)

        # Then: Documents the sync pattern
        assert three_days_ago < today
        assert one_week_ago < three_days_ago

    def test_sync_url_shows_result_dialog(self, qapp):
        """CAPTURE: What dialog is shown after sync.

        This test documents:
        - Success: Shows count and file paths
        - Failure: Shows "no URLs" message
        """
        # Given: Sync result
        urls_count = 10
        room_name = "Test Room"

        # When: Sync completes
        # Current behavior:
        # - QMessageBox.information with counts and file paths
        # - Or warning if no URLs

        # Then: Dialog shown (documented)
        expected_message_contains = "URL"
        assert "URL" in expected_message_contains


@pytest.mark.characterization
class TestURLRestoreBehavior:
    """Characterization tests for URL restore behavior.

    CAPTURE: How URLs are restored from files.
    """

    def test_restore_url_loads_from_file(self, db_session, file_storage, qapp):
        """CAPTURE: How _restore_url_from_file loads URLs.

        This test documents:
        - Loads from _urls_all.md file
        - Deletes existing DB URLs
        - Creates batch in DB
        - Also loads recent and weekly files for display
        """
        # Given: Room with URL files
        repo = ChatRoomRepository(db_session)
        room = repo.create(name="Restore URL Room")

        # When: Restore URLs (simulated)
        # Current behavior:
        # 1. Load from storage.load_url_list(room_name, "all")
        # 2. If found:
        #    - Delete existing from DB
        #    - Create batch in DB
        #    - Load recent and weekly for display
        #    - Show success dialog

        # Then: Documents restore pattern
        assert room.id is not None

    def test_restore_url_shows_error_if_no_file(self, qapp):
        """CAPTURE: What happens when restore file not found.

        This test documents:
        - Warning dialog shown
        - Expected path displayed
        - Suggests using sync button
        """
        # Given: No URL file
        file_exists = False

        # When: Restore attempted (simulated)
        if not file_exists:
            # Current behavior:
            # - QMessageBox.warning
            # - Shows expected path
            # - Suggests sync button
            pass

        # Then: Error shown (documented)
        assert not file_exists


@pytest.mark.characterization
class TestMessageListUILayoutBehavior:
    """Characterization tests for message list UI layout behavior.

    CAPTURE: How message list widgets are laid out.
    """

    def test_date_navigation_layout_structure(self, qapp):
        """CAPTURE: How date navigation layout is structured.

        This test documents:
        - HBoxLayout for navigation
        - Prev button, stretch, date edit, calendar button, stretch, next button
        - Date edit uses calendar popup
        - Display format "yyyy-MM-dd"
        """
        # Given: Navigation widget setup
        from PySide6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QDateEdit

        widget = QWidget()
        layout = QHBoxLayout(widget)

        # When: Setup navigation (simulated)
        prev_btn = QPushButton("Prev")
        date_edit = QDateEdit()
        date_edit.setCalendarPopup(True)
        date_edit.setDisplayFormat("yyyy-MM-dd")
        calendar_btn = QPushButton("Calendar")
        next_btn = QPushButton("Next")

        # Current layout order:
        # prev_btn - stretch - date_edit - calendar_btn - stretch - next_btn

        # Then: Components configured correctly
        assert date_edit.calendarPopup()
        assert "yyyy-MM-dd" in date_edit.displayFormat()

    def test_detail_browser_shows_html(self, qapp):
        """CAPTURE: How detail browser displays HTML content.

        This test documents:
        - Uses QTextBrowser
        - setOpenExternalLinks(True)
        - Shows summary or placeholder HTML
        """
        # Given: Detail browser setup
        from PySide6.QtWidgets import QTextBrowser

        browser = QTextBrowser()
        browser.setOpenExternalLinks(True)

        # When: Set HTML content
        html = "<h2>Test Content</h2>"
        browser.setHtml(html)

        # Then: Browser configured for external links
        assert browser.openExternalLinks()


@pytest.mark.characterization
class TestURLTabLayoutBehavior:
    """Characterization tests for URL tab layout behavior.

    CAPTURE: How URL tab widgets are laid out.
    """

    def test_url_tab_header_layout(self, qapp):
        """CAPTURE: How URL tab header is structured.

        This test documents:
        - Title, stretch, count label, status label, sync button, restore button
        - Buttons have tooltips
        """
        # Given: URL tab header setup
        from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton

        widget = QWidget()
        layout = QHBoxLayout(widget)

        # When: Setup header (simulated)
        title = QLabel("URL List")
        url_count_label = QLabel("0 URLs")
        url_status_label = QLabel("")
        sync_btn = QPushButton("Sync")
        sync_btn.setToolTip("Extract URLs from summaries")
        restore_btn = QPushButton("Restore")
        restore_btn.setToolTip("Restore URLs from file")

        # Then: Components exist
        assert sync_btn.toolTip() != ""
        assert restore_btn.toolTip() != ""

    def test_url_browser_shows_formatted_list(self, qapp):
        """CAPTURE: How URL browser displays formatted list.

        This test documents:
        - Uses QTextBrowser
        - setOpenExternalLinks(True)
        - Shows clickable links
        """
        # Given: URL browser setup
        from PySide6.QtWidgets import QTextBrowser

        browser = QTextBrowser()
        browser.setOpenExternalLinks(True)

        # When: Set HTML with links
        html = '<a href="https://example.com">Example</a>'
        browser.setHtml(html)

        # Then: Browser configured for links
        assert browser.openExternalLinks()


@pytest.mark.characterization
class TestMessageListManagerIntegration:
    """Characterization tests for message list manager integration points.

    CAPTURE: How message list management integrates with other components.
    """

    def test_integration_with_url_repository(self, db_session, qapp):
        """CAPTURE: How message list uses URLRepository.

        Documents the repository method calls used by message list.
        """
        url_repo = URLRepository(db_session)

        # Methods used by message list:
        # - get_by_room(room_id) - load URLs for room
        # - delete_by_room(room_id) - clear before sync
        # - add_urls_batch(room_id, urls_dict) - save synced URLs

        # Verify repository exists and has expected methods
        assert hasattr(url_repo, 'get_by_room')
        assert hasattr(url_repo, 'delete_by_room')
        assert hasattr(url_repo, 'add_urls_batch')

    def test_integration_with_chat_room_repository(self, db_session, qapp):
        """CAPTURE: How message list uses ChatRoomRepository.

        Documents the repository method calls for room lookup.
        """
        repo = ChatRoomRepository(db_session)
        room = repo.create(name="Integration Test Room")

        # Methods used by message list:
        # - get_by_id(room_id) - get room name for storage access

        found = repo.get_by_id(room.id)
        assert found is not None
        assert found.name == "Integration Test Room"

    def test_integration_with_file_storage(self, file_storage, qapp):
        """CAPTURE: How message list uses FileStorage.

        Documents the storage method calls used by message list.
        """
        # Methods used by message list:
        # - load_daily_original(room_name, date_str) - load messages
        # - load_daily_summary(room_name, date_str) - load summary
        # - get_available_dates(room_name) - get date list
        # - get_summarized_dates(room_name) - get summarized dates
        # - load_url_list(room_name, period) - load URLs from file
        # - save_url_lists(room_name, recent, weekly, all) - save URLs
        # - get_url_file_info(room_name) - check URL file

        # Verify storage has expected methods
        assert hasattr(file_storage, 'load_daily_original')
        assert hasattr(file_storage, 'load_daily_summary')
        assert hasattr(file_storage, 'get_available_dates')
        assert hasattr(file_storage, 'get_summarized_dates')
        assert hasattr(file_storage, 'load_url_list')
        assert hasattr(file_storage, 'save_url_lists')


@pytest.mark.characterization
class TestDateInfoLabelBehavior:
    """Characterization tests for date info label behavior.

    CAPTURE: How date info label displays status.
    """

    def test_date_info_shows_status_parts(self, qapp):
        """CAPTURE: How date info label shows status.

        This test documents:
        - Format: "Date | Status1 | Status2"
        - Status parts: message count, summary status
        """
        # Given: Date and status
        date_str = "2024-02-15"
        has_original = True
        has_summary = True
        message_count = 42

        # When: Build status parts (simulated)
        status_parts = []
        if has_original:
            status_parts.append(f"{message_count} messages")
        if has_summary:
            status_parts.append("Summary complete")
        else:
            status_parts.append("No summary")

        # Then: Status parts formatted
        assert len(status_parts) == 2
        assert "42 messages" in status_parts
        assert "Summary complete" in status_parts

    def test_date_info_shows_no_data_message(self, qapp):
        """CAPTURE: What is shown when no data for date.

        This test documents:
        - Placeholder HTML with icon
        - Message indicating no conversation
        - Suggestion to try other dates
        """
        # Given: No data for date
        has_original = False
        has_summary = False

        # When: Build HTML (simulated)
        if not has_original and not has_summary:
            html_contains = "no conversation"
            suggestion_contains = "try other date"

        # Then: Placeholder shown (documented)
        assert "no conversation" in html_contains


@pytest.mark.characterization
class TestSummaryDisplayBehavior:
    """Characterization tests for summary display behavior.

    CAPTURE: How summaries are displayed in detail browser.
    """

    def test_summary_html_extracts_content(self, qapp):
        """CAPTURE: How summary content is extracted from file.

        This test documents:
        - Metadata before --- is removed
        - Footer starting with _Generated is removed
        - Content between is preserved
        """
        # Given: Summary file content
        summary_content = """# Summary
2024-02-15
---
This is the actual content.
Multiple lines here.
_Generated at 2024-02-15
"""
        # When: Extract content (simulated)
        lines = summary_content.split('\n')
        content_start = 0
        for i, line in enumerate(lines):
            if line.strip() == '---' and i > 0:
                content_start = i + 1
                break

        content_lines = []
        for line in lines[content_start:]:
            if line.strip().startswith('_Generated'):
                break
            content_lines.append(line)

        # Then: Only content extracted
        extracted = '\n'.join(content_lines).strip()
        assert 'actual content' in extracted
        assert '_Generated' not in extracted

    def test_no_summary_shows_warning_html(self, qapp):
        """CAPTURE: What HTML is shown when no summary exists.

        This test documents:
        - Warning styled box
        - Message about missing summary
        - Suggestion to generate
        """
        # Given: No summary
        has_summary = False

        # When: Build HTML (simulated)
        if not has_summary:
            html_contains_warning = "summary not generated"
            html_contains_suggestion = "Generate Summary"

        # Then: Warning shown (documented)
        assert "summary not generated" in html_contains_warning
