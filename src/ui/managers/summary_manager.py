"""Summary Manager - handles summary viewing and date navigation.

This manager extracts summary-related functionality from MainWindow:
- Summary browser management (summary_browser)
- Date-based summary viewing (detail_browser)
- Date navigation controls (prev_date_btn, next_date_btn, date_edit, calendar_btn)
- Date information display (date_info_label)
"""

from pathlib import Path
from typing import Optional, Dict, List
from datetime import date, datetime

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextBrowser, QDateEdit, QCalendarWidget, QDialog, QFrame
)
from PySide6.QtCore import Qt, Signal, Slot, QDate
from PySide6.QtGui import QAction

from src.repositories.summary_repository import SummaryRepository
from src.repositories.chat_room_repository import ChatRoomRepository
from file_storage import get_storage


class SummaryManager(QWidget):
    """Manager for summary viewing and date navigation."""

    # Signals
    summary_requested = Signal()  # Emitted when user requests to generate summary
    date_changed = Signal(str)  # Emitted when date changes (date_str)

    def __init__(
        self,
        parent=None,
        summary_repo: Optional[SummaryRepository] = None,
        chat_room_repo: Optional[ChatRoomRepository] = None,
        storage=None
    ):
        super().__init__(parent)
        self.summary_repo = summary_repo
        self.chat_room_repo = chat_room_repo
        self.storage = storage or get_storage()

        # State
        self._current_room_id: Optional[int] = None
        self._current_room_name: Optional[str] = None

        # UI Components (created by create_tab_widgets)
        self.summary_browser: Optional[QTextBrowser] = None
        self.detail_browser: Optional[QTextBrowser] = None
        self.date_edit: Optional[QDateEdit] = None
        self.date_info_label: Optional[QLabel] = None
        self.prev_date_btn: Optional[QPushButton] = None
        self.next_date_btn: Optional[QPushButton] = None
        self.calendar_btn: Optional[QPushButton] = None

    def create_tab_widgets(self, tab_widget, room_id_callback, dashboard_cards=None):
        """Create and add tab widgets to the parent tab widget.

        Args:
            tab_widget: The QTabWidget to add tabs to
            room_id_callback: A callable that returns the current room_id
            dashboard_cards: Optional tuple of (card_messages, card_participants, card_summaries)

        Returns:
            None
        """
        self._room_id_callback = room_id_callback
        self._dashboard_cards = dashboard_cards

        # ===== Tab 1: Summary (Dashboard) =====
        dashboard_tab = QWidget()
        dashboard_layout = QVBoxLayout(dashboard_tab)
        dashboard_layout.setContentsMargins(0, 0, 0, 0)

        # Add dashboard cards if provided
        if dashboard_cards:
            from src.ui.widgets import DashboardCard
            card_messages, card_participants, card_summaries = dashboard_cards

            cards_widget = QWidget()
            cards_layout = QHBoxLayout(cards_widget)
            cards_layout.setContentsMargins(10, 5, 10, 5)

            cards_layout.addWidget(card_messages)
            cards_layout.addWidget(card_participants)
            cards_layout.addWidget(card_summaries)

            dashboard_layout.addWidget(cards_widget)

        # Summary frame
        summary_frame = QFrame()
        summary_frame.setObjectName("summaryViewer")
        summary_frame.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border: 1px solid #E8E8E8;
                border-radius: 12px;
                margin: 10px;
            }
        """)
        summary_layout = QVBoxLayout(summary_frame)

        # Summary header
        summary_header = QHBoxLayout()
        summary_title = QLabel("📅 최근 요약")
        summary_title.setStyleSheet("font-size: 16px; font-weight: bold;")
        summary_header.addWidget(summary_title)

        self.generate_btn = QPushButton("🤖 LLM 요약 생성")
        self.generate_btn.clicked.connect(self.summary_requested.emit)
        summary_header.addWidget(self.generate_btn)

        summary_layout.addLayout(summary_header)

        # Summary browser
        self.summary_browser = QTextBrowser()
        self.summary_browser.setOpenExternalLinks(True)
        self.summary_browser.setStyleSheet("""
            QTextBrowser {
                border: none;
                background-color: transparent;
                font-size: 13px;
            }
        """)
        self.summary_browser.setPlaceholderText("채팅방을 선택하면 요약이 표시됩니다.")
        summary_layout.addWidget(self.summary_browser)

        dashboard_layout.addWidget(summary_frame, 1)

        tab_widget.addTab(dashboard_tab, "📊 대시보드")

        # ===== Tab 2: Date-based Summary =====
        detail_tab = QWidget()
        detail_layout = QVBoxLayout(detail_tab)
        detail_layout.setContentsMargins(10, 10, 10, 10)
        detail_layout.setSpacing(10)

        # Date navigation
        nav_widget = self._create_date_navigation()
        detail_layout.addWidget(nav_widget)

        # Date info
        self.date_info_label = QLabel("📊 날짜를 선택하세요")
        self.date_info_label.setStyleSheet("""
            font-size: 12px;
            color: #666;
            padding: 5px 10px;
        """)
        detail_layout.addWidget(self.date_info_label)

        # Detail summary viewer
        detail_frame = QFrame()
        detail_frame.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border: 1px solid #E8E8E8;
                border-radius: 12px;
            }
        """)
        detail_frame_layout = QVBoxLayout(detail_frame)

        self.detail_browser = QTextBrowser()
        self.detail_browser.setOpenExternalLinks(True)
        self.detail_browser.setStyleSheet("""
            QTextBrowser {
                border: none;
                background-color: transparent;
                font-size: 14px;
                line-height: 1.6;
            }
        """)
        self.detail_browser.setPlaceholderText("채팅방과 날짜를 선택하면 상세 요약이 표시됩니다.")
        detail_frame_layout.addWidget(self.detail_browser)

        detail_layout.addWidget(detail_frame, 1)

        tab_widget.addTab(detail_tab, "📅 날짜별 요약")

    def _create_date_navigation(self) -> QWidget:
        """Create date navigation widget."""
        nav_widget = QWidget()
        nav_widget.setStyleSheet("""
            QWidget {
                background-color: #FFFFFF;
                border: 1px solid #E8E8E8;
                border-radius: 8px;
            }
        """)
        nav_layout = QHBoxLayout(nav_widget)
        nav_layout.setContentsMargins(15, 10, 15, 10)

        # Previous date button
        self.prev_date_btn = QPushButton("◀ 이전")
        self.prev_date_btn.setStyleSheet("""
            QPushButton {
                background-color: #E0E0E0;
                padding: 8px 20px;
                border-radius: 6px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #BDBDBD;
            }
        """)
        self.prev_date_btn.clicked.connect(self._on_prev_date)
        nav_layout.addWidget(self.prev_date_btn)

        nav_layout.addStretch()

        # Date edit
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDate(QDate.currentDate())
        self.date_edit.setDisplayFormat("yyyy년 MM월 dd일")
        self.date_edit.setStyleSheet("""
            QDateEdit {
                border: 2px solid #FEE500;
                border-radius: 6px;
                padding: 8px 15px;
                font-size: 14px;
                font-weight: bold;
                min-width: 160px;
            }
            QDateEdit::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: center right;
                width: 30px;
                border: none;
            }
            QDateEdit::down-arrow {
                image: none;
                width: 0;
            }
        """)

        # Calendar widget styling
        calendar = self.date_edit.calendarWidget()
        calendar.setStyleSheet("""
            QCalendarWidget {
                background-color: #FFFFFF;
            }
            QCalendarWidget QToolButton {
                color: #333;
                font-size: 14px;
                font-weight: bold;
                icon-size: 20px;
                padding: 5px;
            }
            QCalendarWidget QToolButton:hover {
                background-color: #FEE500;
                border-radius: 4px;
            }
            QCalendarWidget QMenu {
                background-color: #FFFFFF;
            }
            QCalendarWidget QSpinBox {
                font-size: 14px;
                font-weight: bold;
            }
            QCalendarWidget QWidget#qt_calendar_navigationbar {
                background-color: #FEE500;
            }
            QCalendarWidget QTableView {
                selection-background-color: #FEE500;
                selection-color: #000000;
            }
            QCalendarWidget QTableView::item:hover {
                background-color: #FFF9C4;
            }
        """)
        self.date_edit.dateChanged.connect(self._on_date_changed)
        nav_layout.addWidget(self.date_edit)

        # Calendar button
        self.calendar_btn = QPushButton("📅")
        self.calendar_btn.setToolTip("달력에서 선택")
        self.calendar_btn.setStyleSheet("""
            QPushButton {
                background-color: #FEE500;
                border: none;
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: #FFD700;
            }
        """)
        self.calendar_btn.clicked.connect(self._show_calendar_dialog)
        nav_layout.addWidget(self.calendar_btn)

        nav_layout.addStretch()

        # Next date button
        self.next_date_btn = QPushButton("다음 ▶")
        self.next_date_btn.setStyleSheet("""
            QPushButton {
                background-color: #E0E0E0;
                padding: 8px 20px;
                border-radius: 6px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #BDBDBD;
            }
        """)
        self.next_date_btn.clicked.connect(self._on_next_date)
        nav_layout.addWidget(self.next_date_btn)

        return nav_widget

    @Slot()
    def _on_prev_date(self):
        """Move to previous date."""
        current = self.date_edit.date()
        self.date_edit.setDate(current.addDays(-1))

    @Slot()
    def _on_next_date(self):
        """Move to next date."""
        current = self.date_edit.date()
        self.date_edit.setDate(current.addDays(1))

    @Slot(QDate)
    def _on_date_changed(self, date: QDate):
        """Load summary for selected date."""
        room_id = self._room_id_callback() if self._room_id_callback else None
        if room_id is None:
            self.detail_browser.setHtml("""
                <div style="text-align: center; padding: 50px; color: #888;">
                    <p style="font-size: 48px;">📁</p>
                    <p style="font-size: 16px;">먼저 채팅방을 선택하세요</p>
                </div>
            """)
            return

        # Get current room
        room = self.chat_room_repo.get_by_id(room_id) if self.chat_room_repo else None
        if not room:
            return

        room_name = room.name
        date_str = date.toString("yyyy-MM-dd")

        # Load data from file storage
        storage = get_storage()

        # Load original messages
        messages = storage.load_daily_original(room_name, date_str)

        # Load summary
        summary = storage.load_daily_summary(room_name, date_str)

        # Get available dates
        available_dates = storage.get_available_dates(room_name)
        summarized_dates = storage.get_summarized_dates(room_name)

        # Update date info
        has_original = date_str in available_dates
        has_summary = date_str in summarized_dates

        status_parts = []
        if has_original:
            status_parts.append(f"💬 {len(messages)}개 메시지")
        if has_summary:
            status_parts.append("✅ 요약 완료")
        else:
            status_parts.append("⚠️ 요약 없음")

        self.date_info_label.setText(f"📅 {date_str} | " + " | ".join(status_parts))

        # Generate HTML
        if not has_original and not has_summary:
            self.detail_browser.setHtml(f"""
                <div style="text-align: center; padding: 50px; color: #888;">
                    <p style="font-size: 48px;">📭</p>
                    <p style="font-size: 16px;">{date_str}에는 대화 기록이 없습니다</p>
                    <p style="font-size: 12px; color: #AAA;">다른 날짜를 선택해보세요</p>
                </div>
            """)
            return

        html = f"<h2>📅 {room_name} - {date_str}</h2>"

        # Display summary
        if summary:
            # Extract content after metadata separator
            summary_lines = summary.split('\n')
            content_start = 0
            for i, line in enumerate(summary_lines):
                if line.strip() == '---' and i > 0:
                    content_start = i + 1
                    break

            # Remove footer
            content_lines = []
            for line in summary_lines[content_start:]:
                if line.strip().startswith('_Generated'):
                    break
                content_lines.append(line)

            summary_content = '\n'.join(content_lines)
            html += f"""
                <div style="background-color: #FFF8E1; padding: 15px; border-radius: 8px; margin: 10px 0; border-left: 4px solid #FFC107;">
                    <h3 style="margin-top: 0;">📝 AI 요약</h3>
                    <div style="line-height: 1.8;">{summary_content.replace(chr(10), '<br>')}</div>
                </div>
            """
        else:
            html += """
                <div style="background-color: #FFEBEE; padding: 15px; border-radius: 8px; margin: 10px 0; border-left: 4px solid #F44336;">
                    <p style="margin: 0; color: #C62828;">⚠️ 이 날짜의 요약이 아직 생성되지 않았습니다.</p>
                    <p style="margin: 5px 0 0 0; color: #888; font-size: 12px;">대시보드 탭에서 '🤖 LLM 요약 생성' 버튼을 클릭하세요.</p>
                </div>
            """

        self.detail_browser.setHtml(html)

        # Emit date changed signal
        self.date_changed.emit(date_str)

    @Slot()
    def _show_calendar_dialog(self):
        """Show calendar dialog for date selection."""
        dialog = QDialog(self.parent())
        dialog.setWindowTitle("📅 날짜 선택")
        dialog.setFixedSize(350, 300)

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(10, 10, 10, 10)

        # Calendar widget
        calendar = QCalendarWidget()
        calendar.setSelectedDate(self.date_edit.date())
        calendar.setStyleSheet("""
            QCalendarWidget {
                background-color: #FFFFFF;
            }
            QCalendarWidget QToolButton {
                color: #333;
                font-size: 13px;
                font-weight: bold;
                padding: 5px;
            }
            QCalendarWidget QToolButton:hover {
                background-color: #FEE500;
                border-radius: 4px;
            }
            QCalendarWidget QWidget#qt_calendar_navigationbar {
                background-color: #FEE500;
                padding: 5px;
            }
            QCalendarWidget QTableView {
                selection-background-color: #FEE500;
                selection-color: #000000;
                font-size: 12px;
            }
            QCalendarWidget QTableView::item:hover {
                background-color: #FFF9C4;
            }
        """)
        layout.addWidget(calendar)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        today_btn = QPushButton("오늘")
        today_btn.setStyleSheet("""
            QPushButton {
                background-color: #5B9BD5;
                color: white;
                padding: 8px 20px;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #4A8BC4;
            }
        """)
        today_btn.clicked.connect(lambda: calendar.setSelectedDate(QDate.currentDate()))
        btn_layout.addWidget(today_btn)

        select_btn = QPushButton("선택")
        select_btn.setStyleSheet("""
            QPushButton {
                background-color: #FEE500;
                padding: 8px 20px;
                border-radius: 6px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #FFD700;
            }
        """)
        select_btn.clicked.connect(dialog.accept)
        btn_layout.addWidget(select_btn)

        layout.addLayout(btn_layout)

        # Double-click to select
        calendar.activated.connect(dialog.accept)

        if dialog.exec() == QDialog.Accepted:
            self.date_edit.setDate(calendar.selectedDate())

    def update_date_tab_for_room(self, room_name: str):
        """Update date tab when a room is selected."""
        storage = get_storage()

        available_dates = storage.get_available_dates(room_name)

        if available_dates:
            # Set to most recent date
            latest_date = available_dates[-1]
            year, month, day = map(int, latest_date.split('-'))
            self.date_edit.setDate(QDate(year, month, day))
        else:
            self.date_edit.setDate(QDate.currentDate())

        # Trigger date change event
        self._on_date_changed(self.date_edit.date())

    def display_room_summaries(self, room_id: int, stats: Dict, room_name: str):
        """Display summaries for a selected room.

        Args:
            room_id: The selected room ID
            stats: Room statistics dictionary
            room_name: The room name
        """
        if not stats:
            self.summary_browser.setHtml("""
                <h3>🌟 요약</h3>
                <p>채팅방 데이터가 없습니다.</p>
            """)
            return

        # Get summaries from repository
        summaries = self.summary_repo.get_by_room(room_id) if self.summary_repo else []

        if summaries:
            html = "<h3>📅 최근 요약</h3>"
            for s in summaries[:5]:
                html += f"<p><b>{s.summary_date}</b> ({s.summary_type})</p>"
                html += f"<p>{s.content[:200]}...</p><hr>"
            self.summary_browser.setHtml(html)
        else:
            date_range = ""
            if stats.get('first_date') and stats.get('last_date'):
                date_range = f"<p>📅 대화 기간: {stats['first_date']} ~ {stats['last_date']}</p>"

            self.summary_browser.setHtml(f"""
                <h3>📊 채팅방 정보</h3>
                <p>💬 총 메시지: <b>{stats.get('total_messages', 0):,}개</b></p>
                <p>👥 참여자: <b>{stats.get('unique_senders', 0)}명</b></p>
                {date_range}
                <hr>
                <p style="color: #888;">요약을 생성하려면 '🤖 LLM 요약 생성' 버튼을 클릭하세요.</p>
            """)

    def clear_summaries(self):
        """Clear summary display when no room is selected."""
        self.summary_browser.setHtml("<p style='color: #888;'>채팅방을 선택하세요.</p>")
