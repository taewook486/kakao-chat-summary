"""메인 윈도우 - 카카오톡 스타일 대화 분석기."""
import sys
import re
from pathlib import Path
from datetime import datetime, timedelta, date
from typing import Optional, List, Dict, Any

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QListWidget, QListWidgetItem, QLabel, QPushButton, QTextBrowser,
    QFrame, QScrollArea, QFileDialog, QMessageBox, QProgressBar,
    QStatusBar, QMenuBar, QMenu, QDialog, QSpinBox, QComboBox,
    QFormLayout, QDialogButtonBox, QGroupBox, QGridLayout, QApplication,
    QLineEdit, QRadioButton, QButtonGroup, QCheckBox, QProgressDialog,
    QTabWidget, QDateEdit, QCalendarWidget
)
from PySide6.QtCore import Qt, Signal, Slot, QTimer, QThread, QDate
from PySide6.QtGui import QAction, QFont, QIcon

from .styles import MAIN_STYLESHEET

# 프로젝트 모듈 import
sys.path.insert(0, str(Path(__file__).parent.parent))

# Direct imports from src modules
from db import get_db, ChatRoom, Message
from db.database import Database
from file_storage import get_storage
from parser import KakaoLogParser
from url_extractor import extract_urls_from_text, save_urls_to_file, deduplicate_urls

# Repository layer - using absolute imports from src package
import sys
from pathlib import Path as PathLib
src_root = str(PathLib(__file__).parent.parent.parent)
if src_root not in sys.path:
    sys.path.insert(0, src_root)

from src.repositories.chat_room_repository import ChatRoomRepository
from src.repositories.message_repository import MessageRepository
from src.repositories.summary_repository import SummaryRepository
from src.repositories.sync_log_repository import SyncLogRepository
from src.repositories.url_repository import URLRepository

# Service layer
from src.services.chat_service import ChatService
from src.services.summary_service import SummaryService
from src.services.url_service import URLService
from src.services.file_service import FileService

# Worker layer (external workers)
from src.workers.file_upload_worker import FileUploadWorker, MessageParser
from src.workers.sync_worker import SyncWorker
from src.workers.summary_worker import SummaryWorker as SummaryGeneratorWorker
from src.workers.recovery_worker import RecoveryWorker

# Manager layer (extracted from main_window)
from src.ui.managers.chat_room_list_manager import ChatRoomListManager
from src.ui.managers.menu_bar_manager import MenuBarManager
from src.ui.managers.summary_manager import SummaryManager

# Coordinator layer (extracted from main_window)
from src.ui.coordinators.worker_coordinator import WorkerCoordinator, WorkerCallbacks

# Dialogs (externalized to src/ui/dialogs/)
from src.ui.dialogs.summary_options_dialog import SummaryOptionsDialog
from src.ui.dialogs.create_room_dialog import CreateRoomDialog
from src.ui.dialogs.upload_file_dialog import UploadFileDialog
from src.ui.dialogs.settings_dialog import SettingsDialog

# Widgets (externalized to src/ui/widgets/)
from src.ui.widgets import DashboardCard, SummaryProgressDialog, SummaryProgressWidget


class ChatRoomWidget(QFrame):
    """채팅방 아이템 위젯."""
    clicked = Signal(int, str)  # room_id, file_path
    def __init__(self, room_id: int, name: str, message_count: int = 0,
                 new_count: int = 0, last_sync: Optional[datetime] = None,
                 file_path: Optional[str] = None):
        super().__init__()
        self.room_id = room_id
        self.file_path = file_path or ""
        self.setObjectName("chatRoomItem")
        self.setProperty("class", "ChatRoomItem")
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(70)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        
        # 아이콘/아바타 영역
        avatar = QLabel("💬")
        avatar.setFixedSize(40, 40)
        avatar.setAlignment(Qt.AlignCenter)
        avatar.setStyleSheet("""
            background-color: #FEE500;
            border-radius: 20px;
            font-size: 18px;
        """)
        layout.addWidget(avatar)
        
        # 정보 영역
        info_layout = QVBoxLayout()
        info_layout.setSpacing(4)
        
        # 이름 + 새 메시지 배지
        name_layout = QHBoxLayout()
        name_label = QLabel(name)
        name_label.setProperty("class", "ChatRoomName")
        name_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        name_layout.addWidget(name_label)
        
        if new_count > 0:
            badge = QLabel(str(new_count))
            badge.setProperty("class", "NewBadge")
            badge.setStyleSheet("""
                background-color: #FF5252;
                color: white;
                font-size: 10px;
                font-weight: bold;
                padding: 2px 6px;
                border-radius: 10px;
            """)
            badge.setFixedHeight(18)
            name_layout.addWidget(badge)
        
        name_layout.addStretch()

        info_layout.addLayout(name_layout)

        # 메시지 수 및 동기화 시간
        sync_text = "동기화 안됨"
        if last_sync:
            sync_text = last_sync.strftime("%m/%d %H:%M")
        
        info_label = QLabel(f"📊 {message_count:,}개 메시지 · {sync_text}")
        info_label.setProperty("class", "ChatRoomInfo")
        info_label.setStyleSheet("color: #888888; font-size: 11px;")
        info_layout.addWidget(info_label)
        
        layout.addLayout(info_layout, 1)
    
    def mousePressEvent(self, event):
        self.clicked.emit(self.room_id, self.file_path)
        super().mousePressEvent(event)


class MainWindow(QMainWindow):
    """메인 윈도우."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🗨️ 카카오톡 대화 분석기")
        self.setMinimumSize(1000, 700)
        self.setStyleSheet(MAIN_STYLESHEET)
        
        self.current_room_id: Optional[int] = None
        self.current_room_file: Optional[str] = None

        # Database instance (for backward compatibility during transition)
        self.db = get_db()
        self.storage = get_storage()

        # Repository layer
        self.chat_room_repo = ChatRoomRepository(self.db)
        self.message_repo = MessageRepository(self.db)
        self.summary_repo = SummaryRepository(self.db)
        self.url_repo = URLRepository(self.db)
        self.sync_log_repo = SyncLogRepository(self.db)

        # Service layer
        self.chat_service = ChatService(
            chat_room_repo=self.chat_room_repo,
            message_repo=self.message_repo,
            sync_log_repo=self.sync_log_repo,
            file_storage=self.storage,
        )
        self.summary_service = SummaryService(
            chat_room_repo=self.chat_room_repo,
            message_repo=self.message_repo,
            summary_repo=self.summary_repo,
            sync_log_repo=self.sync_log_repo,
        )
        self.url_service = URLService(
            chat_room_repo=self.chat_room_repo,
            url_repo=self.url_repo,
            summary_repo=self.summary_repo,
            file_storage=self.storage,
        )
        self.file_service = FileService(
            file_storage=self.storage,
            chat_room_repo=self.chat_room_repo,
        )

        # Manager layer (extracted from main_window)
        # @MX:NOTE: ChatRoomListManager handles room list UI and operations
        self.room_manager = ChatRoomListManager(
            parent=self,
            chat_room_repo=self.chat_room_repo,
            message_repo=self.message_repo,
            summary_repo=self.summary_repo,
            chat_service=self.chat_service,
            storage=self.storage,
        )

        # Connect manager signals to MainWindow handlers
        self.room_manager.room_selected.connect(self._on_room_manager_selected)

        # @MX:NOTE: MenuBarManager handles menu creation and action signals
        self.menu_manager = MenuBarManager(self)

        # Connect menu manager signals to MainWindow handlers
        self.menu_manager.add_room_triggered.connect(self._on_add_room)
        self.menu_manager.delete_room_triggered.connect(self._on_delete_room)
        self.menu_manager.exit_triggered.connect(self.close)
        self.menu_manager.manual_sync_triggered.connect(self._on_manual_sync)
        self.menu_manager.generate_summary_triggered.connect(self._on_generate_summary)
        self.menu_manager.backup_triggered.connect(self._on_backup)
        self.menu_manager.room_backup_triggered.connect(self._on_room_backup)
        self.menu_manager.restore_from_backup_triggered.connect(self._on_restore_from_backup)
        self.menu_manager.recovery_triggered.connect(self._on_recovery)
        self.menu_manager.room_recovery_triggered.connect(self._on_room_recovery)
        self.menu_manager.settings_triggered.connect(self._on_settings)
        self.menu_manager.about_triggered.connect(self._on_about)

        # @MX:NOTE: SummaryManager handles summary viewing and date navigation
        self.summary_manager = SummaryManager(
            parent=self,
            summary_repo=self.summary_repo,
            chat_room_repo=self.chat_room_repo,
            storage=self.storage,
        )

        # Connect summary manager signals to MainWindow handlers
        self.summary_manager.summary_requested.connect(self._on_generate_summary)

        # Create placeholder for generate_btn (will be set in _setup_ui)
        self.generate_btn = None

        # 워커 코디네이터 초기화
        self._init_worker_coordinator()

        self._setup_ui()
        self._setup_menu()
        self._setup_statusbar()
        self._load_rooms()

    def _init_worker_coordinator(self):
        """워커 코디네이터 초기화."""
        callbacks = WorkerCallbacks(
            update_status=self._update_status,
            refresh_rooms=self._load_rooms,
            select_room=self._on_room_selected,
            set_generate_button_enabled=lambda enabled: self.generate_btn.setEnabled(enabled),
            show_message=self._show_message
        )
        self.worker_coordinator = WorkerCoordinator(
            parent=self,
            callbacks=callbacks,
            statusbar=None  # Will be set after statusbar creation
        )

    def _show_message(self, title: str, message: str, msg_type: str):
        """Show message box (callback for WorkerCoordinator)."""
        if msg_type == "warning":
            QMessageBox.warning(self, title, message)
        else:
            QMessageBox.information(self, title, message)
    
    def _setup_ui(self):
        """UI 구성."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 스플리터
        splitter = QSplitter(Qt.Horizontal)
        
        # ===== 좌측 패널: 채팅방 목록 =====
        left_panel = QWidget()
        left_panel.setObjectName("chatListPanel")
        left_panel.setMinimumWidth(250)
        left_panel.setMaximumWidth(350)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)
        
        # 헤더
        header = QLabel("💬 채팅방")
        header.setObjectName("chatListTitle")
        header.setStyleSheet("""
            font-size: 18px;
            font-weight: bold;
            color: #191919;
            padding: 15px;
            background-color: #FEE500;
        """)
        left_layout.addWidget(header)
        
        # 채팅방 목록 (using ChatRoomListManager)
        scroll = self.room_manager.create_scroll_area()
        left_layout.addWidget(scroll, 1)
        
        # 채팅방 만들기 버튼
        add_btn = QPushButton("➕ 채팅방 만들기")
        add_btn.clicked.connect(self._on_add_room)
        add_btn.setStyleSheet("""
            QPushButton {
                margin: 10px 10px 5px 10px;
                padding: 12px;
            }
        """)
        left_layout.addWidget(add_btn)
        
        splitter.addWidget(left_panel)
        
        # ===== 우측 패널: 탭 =====
        right_panel = QWidget()
        right_panel.setObjectName("mainPanel")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)
        
        # 헤더
        header_widget = QWidget()
        header_widget.setStyleSheet("background-color: #FEE500;")
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(15, 10, 15, 10)
        
        self.header_label = QLabel("📊 대시보드")
        self.header_label.setObjectName("headerTitle")
        self.header_label.setStyleSheet("""
            font-size: 20px;
            font-weight: bold;
            color: #191919;
            background-color: transparent;
        """)
        header_layout.addWidget(self.header_label)
        
        header_layout.addStretch()
        
        # 업로드 버튼
        self.upload_btn = QPushButton("📤 파일 업로드")
        self.upload_btn.clicked.connect(self._on_upload_file)
        self.upload_btn.setStyleSheet("""
            QPushButton {
                background-color: #3C1E1E;
                color: white;
                padding: 8px 15px;
                border-radius: 6px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #5C3E3E;
            }
        """)
        header_layout.addWidget(self.upload_btn)
        
        right_layout.addWidget(header_widget)
        
        # 탭 위젯
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: none;
                background-color: #FAFAFA;
            }
            QTabBar::tab {
                background-color: #E0E0E0;
                padding: 10px 25px;
                margin-right: 2px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                font-size: 13px;
            }
            QTabBar::tab:selected {
                background-color: #FEE500;
                font-weight: bold;
            }
            QTabBar::tab:hover:!selected {
                background-color: #EEEEEE;
            }
        """)
        
        # Create dashboard cards
        self.card_messages = DashboardCard("총 메시지", "0", "전체 기간", "💬")
        self.card_participants = DashboardCard("참여자", "0", "명", "👥")
        self.card_summaries = DashboardCard("요약", "0", "개 생성됨", "📝")

        # Create summary and date tabs using SummaryManager
        # @MX:NOTE: SummaryManager creates and manages summary viewing tabs
        self.summary_manager.create_tab_widgets(
            self.tab_widget,
            lambda: self.current_room_id,
            dashboard_cards=(self.card_messages, self.card_participants, self.card_summaries)
        )

        # Reference generate_btn for WorkerCoordinator callback
        self.generate_btn = self.summary_manager.generate_btn
        
        # ===== 탭 3: URL 정보 =====
        url_tab = QWidget()
        url_layout = QVBoxLayout(url_tab)
        url_layout.setContentsMargins(10, 10, 10, 10)
        url_layout.setSpacing(10)
        
        # URL 탭 헤더
        url_header = QWidget()
        url_header.setStyleSheet("""
            QWidget {
                background-color: #FFFFFF;
                border: 1px solid #E8E8E8;
                border-radius: 12px;
            }
        """)
        url_header_layout = QHBoxLayout(url_header)
        url_header_layout.setContentsMargins(15, 10, 15, 10)
        
        url_title = QLabel("🔗 공유된 URL 목록")
        url_title.setStyleSheet("border: none; font-size: 16px; font-weight: bold;")
        url_header_layout.addWidget(url_title)
        
        url_header_layout.addStretch()
        
        # URL 개수 및 상태 표시
        self.url_count_label = QLabel("0개 URL")
        self.url_count_label.setStyleSheet("border: none; color: #666; font-size: 13px;")
        url_header_layout.addWidget(self.url_count_label)
        
        self.url_status_label = QLabel("")
        self.url_status_label.setStyleSheet("border: none; color: #888; font-size: 11px;")
        url_header_layout.addWidget(self.url_status_label)

        # 동기화 버튼 (요약에서 URL 추출 → DB/파일 저장)
        self.sync_url_btn = QPushButton("🔄 동기화")
        self.sync_url_btn.setToolTip("요약 파일에서 URL을 추출하여 DB와 파일에 저장")
        self.sync_url_btn.setStyleSheet("""
            QPushButton {
                background-color: #43A047;
                color: white;
                padding: 6px 15px;
                border-radius: 6px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #388E3C;
            }
        """)
        self.sync_url_btn.clicked.connect(self._sync_url_from_summaries)
        url_header_layout.addWidget(self.sync_url_btn)

        # 파일에서 복구 버튼
        self.restore_url_btn = QPushButton("📂 파일 복구")
        self.restore_url_btn.setToolTip("파일에서 URL 목록을 DB로 복구")
        self.restore_url_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                padding: 6px 15px;
                border-radius: 6px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #F57C00;
            }
        """)
        self.restore_url_btn.clicked.connect(self._restore_url_from_file)
        url_header_layout.addWidget(self.restore_url_btn)

        url_layout.addWidget(url_header)
        
        # URL 목록 뷰어
        url_frame = QFrame()
        url_frame.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border: 1px solid #E8E8E8;
                border-radius: 12px;
            }
        """)
        url_frame_layout = QVBoxLayout(url_frame)
        
        self.url_browser = QTextBrowser()
        self.url_browser.setOpenExternalLinks(True)
        self.url_browser.setStyleSheet("""
            QTextBrowser {
                border: none;
                background-color: transparent;
                font-size: 13px;
                line-height: 1.8;
            }
        """)
        self.url_browser.setPlaceholderText("채팅방을 선택하면 공유된 URL 목록이 표시됩니다.")
        url_frame_layout.addWidget(self.url_browser)
        
        url_layout.addWidget(url_frame, 1)
        
        self.tab_widget.addTab(url_tab, "🔗 URL 정보")

        # === 기타 기능 탭 ===
        etc_tab = QWidget()
        etc_layout = QVBoxLayout(etc_tab)
        etc_layout.setSpacing(12)
        etc_layout.setContentsMargins(10, 10, 10, 10)

        # 통계 갱신 카드
        stats_card = QFrame()
        stats_card.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border: 1px solid #E8E8E8;
                border-radius: 12px;
            }
        """)
        stats_card_layout = QVBoxLayout(stats_card)
        stats_card_layout.setContentsMargins(15, 12, 15, 12)

        stats_title = QLabel("📊 통계 정보 갱신")
        stats_title.setStyleSheet("border: none; font-size: 15px; font-weight: bold;")
        stats_card_layout.addWidget(stats_title)

        stats_desc = QLabel("대시보드 통계와 채팅방 목록을 최신 상태로 갱신합니다.")
        stats_desc.setStyleSheet("border: none; color: #666; font-size: 12px;")
        stats_desc.setWordWrap(True)
        stats_card_layout.addWidget(stats_desc)

        stats_btn_layout = QHBoxLayout()
        stats_btn_layout.addStretch()
        self.etc_refresh_btn = QPushButton("🔄 갱신")
        self.etc_refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #1E88E5;
                color: white;
                padding: 6px 18px;
                border-radius: 6px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #1565C0;
            }
        """)
        self.etc_refresh_btn.clicked.connect(self._on_refresh_stats)
        stats_btn_layout.addWidget(self.etc_refresh_btn)
        stats_card_layout.addLayout(stats_btn_layout)

        etc_layout.addWidget(stats_card)

        etc_layout.addStretch()

        self.tab_widget.addTab(etc_tab, "🔧 기타")

        right_layout.addWidget(self.tab_widget, 1)
        
        splitter.addWidget(right_panel)
        splitter.setSizes([280, 720])
        
        main_layout.addWidget(splitter)
    
    def _setup_menu(self):
        """메뉴바 구성 - MenuBarManager에 위임."""
        self.menu_manager.setup_menu(self)
    
    def _setup_statusbar(self):
        """상태바 구성."""
        self.statusbar = QStatusBar()
        self.setStatusBar(self.statusbar)

        # 작업 상태 (왼쪽)
        self.task_status = QLabel("준비")
        self.task_status.setStyleSheet("font-size: 12px; padding: 0 10px;")
        self.statusbar.addWidget(self.task_status)

        self.statusbar.addPermanentWidget(QLabel(""))  # 스페이서

        # 마지막 작업 시간
        self.last_sync_label = QLabel("")
        self.last_sync_label.setStyleSheet("color: #666; font-size: 11px;")
        self.statusbar.addPermanentWidget(self.last_sync_label)

        # 워커 코디네이터에 statusbar 설정
        self.worker_coordinator._statusbar = self.statusbar
    
    def _load_rooms(self):
        """채팅방 목록 로드 - ChatRoomListManager에 위임."""
        if self.room_manager:
            self.room_manager.load_rooms()
    
    @Slot(int, str)
    def _on_room_selected(self, room_id: int, file_path: str):
        """채팅방 선택 시."""
        self.current_room_id = room_id
        self.current_room_file = file_path

        # 채팅방 통계 로드 (using service layer)
        stats = self.chat_service.get_room_statistics(room_id)
        room_name = "채팅방"

        if stats:
            room_name = stats.get('room_name', '채팅방')
            self.header_label.setText(f"📊 {room_name}")

            # 대화 기간 서브텍스트
            first_date = stats.get('first_date')
            last_date = stats.get('last_date')
            if first_date and last_date:
                days_span = (last_date - first_date).days + 1
                msg_date_sub = f"{first_date} ~ {last_date} ({days_span}일)"
            else:
                msg_date_sub = "대화 없음"

            # 대시보드 카드 업데이트
            total_msg = stats.get('total_messages', 0)
            self.card_messages.update_card(f"{total_msg:,}", msg_date_sub)
            self.card_participants.update_card(
                f"{stats.get('unique_senders', 0)}",
                "명"
            )

            # 파일 저장소에서 요약 통계 가져오기
            from file_storage import get_storage
            storage = get_storage()
            available_dates = storage.get_available_dates(room_name)
            summarized_dates = storage.get_summarized_dates(room_name)
            total_dates = len(available_dates)
            done_dates = len(summarized_dates)
            if total_dates > 0:
                pct = int(done_dates / total_dates * 100)
                summary_sub = f"{done_dates}/{total_dates}일 ({pct}%)"
            else:
                summary_sub = "대화 데이터 없음"
            self.card_summaries.update_card(f"{done_dates}", summary_sub)

            # 요약 목록 조회 (using repository)
            summaries = self.summary_repo.get_by_room(room_id)

            # @MX:NOTE: Use SummaryManager to display room summaries
            self.summary_manager.display_room_summaries(room_id, stats, room_name)
        else:
            self.header_label.setText(f"📊 채팅방 #{room_id}")
            # @MX:NOTE: Use SummaryManager to display room summaries
            self.summary_manager.display_room_summaries(room_id, {}, room_name)

        # 날짜 탭 업데이트
        # @MX:NOTE: Use SummaryManager to update date tab
        self.summary_manager.update_date_tab_for_room(room_name)
        
        # URL 탭 자동 로드
        self._current_url_data = {}
        self._refresh_url_list()

    def _on_room_manager_selected(self, room_id: int, room_name: str, file_path: str):
        """ChatRoomListManager에서 채팅방 선택 시그널 처리."""
        self.current_room_id = room_id
        self.current_room_file = file_path

        # 채팅방 통계 로드 (using service layer)
        stats = self.chat_service.get_room_statistics(room_id)
        display_name = room_name or "채팅방"

        if stats:
            display_name = stats.get('room_name', display_name)
            self.header_label.setText(f"📊 {display_name}")

            # 대화 기간 서브텍스트
            first_date = stats.get('first_date')
            last_date = stats.get('last_date')
            if first_date and last_date:
                days_span = (last_date - first_date).days + 1
                msg_date_sub = f"{first_date} ~ {last_date} ({days_span}일)"
            else:
                msg_date_sub = "대화 없음"

            # 대시보드 카드 업데이트
            total_msg = stats.get('total_messages', 0)
            self.card_messages.update_card(f"{total_msg:,}", msg_date_sub)
            self.card_participants.update_card(
                f"{stats.get('unique_senders', 0)}",
                "명"
            )

            # 파일 저장소에서 요약 통계 가져오기
            from file_storage import get_storage
            storage = get_storage()
            available_dates = storage.get_available_dates(display_name)
            summarized_dates = storage.get_summarized_dates(display_name)
            total_dates = len(available_dates)
            done_dates = len(summarized_dates)
            if total_dates > 0:
                pct = int(done_dates / total_dates * 100)
                summary_sub = f"{done_dates}/{total_dates}일 ({pct}%)"
            else:
                summary_sub = "대화 데이터 없음"
            self.card_summaries.update_card(f"{done_dates}", summary_sub)

            # 요약 목록 조회 (using repository)
            summaries = self.summary_repo.get_by_room(room_id)

            # @MX:NOTE: Use SummaryManager to display room summaries
            self.summary_manager.display_room_summaries(room_id, stats, display_name)
        else:
            self.header_label.setText(f"📊 {display_name}")
            # @MX:NOTE: Use SummaryManager to display room summaries
            self.summary_manager.display_room_summaries(room_id, {}, display_name)

        # 날짜 탭 업데이트
        # @MX:NOTE: Use SummaryManager to update date tab
        self.summary_manager.update_date_tab_for_room(display_name)

        # URL 탭 자동 로드
        self._current_url_data = {}
        self._refresh_url_list()

    @Slot()
    def _on_add_room(self):
        """채팅방 만들기."""
        dialog = CreateRoomDialog(self)
        if dialog.exec() != QDialog.Accepted:
            return
        
        room_name = dialog.room_name
        if not room_name:
            return
        
        # 채팅방 생성 (using repository and storage)
        try:
            # Repository에서 채팅방 확인
            room = self.chat_room_repo.get_by_name(room_name)
            if room:
                QMessageBox.warning(self, "알림", f"'{room_name}' 채팅방이 이미 존재합니다.")
                return

            # Repository에서 채팅방 생성
            room = self.chat_room_repo.create(room_name)

            # 파일 저장소 디렉토리 생성
            (self.storage.original_dir / self.storage._sanitize_name(room_name)).mkdir(parents=True, exist_ok=True)
            (self.storage.summary_dir / self.storage._sanitize_name(room_name)).mkdir(parents=True, exist_ok=True)
            
            QMessageBox.information(self, "생성 완료", f"✅ '{room_name}' 채팅방이 생성되었습니다.\n\n이제 파일을 업로드하세요.")
            self._load_rooms()
            
        except Exception as e:
            QMessageBox.warning(self, "오류", f"채팅방 생성 실패: {str(e)}")
    
    @Slot()
    def _on_delete_room(self):
        """채팅방 삭제 (파일 메뉴에서 호출)."""
        if self.current_room_id is None:
            QMessageBox.warning(self, "알림", "먼저 채팅방을 선택하세요.")
            return

        room = self.chat_room_repo.get_by_id(self.current_room_id)
        if not room:
            QMessageBox.warning(self, "오류", "선택된 채팅방을 찾을 수 없습니다.")
            return

        room_name = room.name
        reply = QMessageBox.question(
            self, "채팅방 삭제",
            f"'{room_name}' 채팅방을 정말 삭제하시겠습니까?\n\n"
            f"DB의 메시지, 요약, URL 데이터가 모두 삭제됩니다.\n"
            f"(data/ 폴더의 파일은 유지됩니다)",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return

        try:
            self.chat_room_repo.delete(self.current_room_id)
            self.current_room_id = None
            self.current_room_file = None
            self.header_label.setText("📊 대시보드")
            self.summary_manager.clear_summaries()
            self._load_rooms()
            self._update_status(f"'{room_name}' 채팅방 삭제 완료", "success")
        except Exception as e:
            QMessageBox.warning(self, "오류", f"채팅방 삭제 실패: {str(e)}")

    @Slot()
    def _on_upload_file(self):
        """현재 선택된 채팅방에 파일 업로드."""
        if self.current_room_id is None:
            QMessageBox.warning(self, "알림", "먼저 채팅방을 선택하세요.")
            return

        # 현재 채팅방 이름 가져오기
        room = self.chat_room_repo.get_by_id(self.current_room_id)
        if not room:
            QMessageBox.warning(self, "오류", "채팅방을 찾을 수 없습니다.")
            return

        # 파일 업로드 다이얼로그
        dialog = UploadFileDialog(room.name, self)
        if dialog.exec() != QDialog.Accepted:
            return

        file_path = dialog.file_path
        if not file_path:
            return

        # 워커 코디네이터를 통한 업로드 시작
        self.worker_coordinator.start_upload(file_path, room.name)

    @Slot()
    def _on_manual_sync(self):
        """수동 동기화."""
        if self.current_room_id is None:
            QMessageBox.warning(self, "알림", "먼저 채팅방을 선택하세요.")
            return

        if not self.current_room_file or not Path(self.current_room_file).exists():
            QMessageBox.warning(self, "알림", "파일 경로가 유효하지 않습니다.")
            return

        # 워커 코디네이터를 통한 동기화 시작
        self.worker_coordinator.start_sync(self.current_room_id, self.current_room_file)

    @Slot(bool, str)
    def _on_sync_finished(self, success: bool, message: str):
        """동기화 완료."""
        if success:
            self._update_status(message, "success")
            # UI 새로고침
            self._load_rooms()
            if self.current_room_id:
                self._on_room_selected(self.current_room_id, self.current_room_file or "")
        else:
            self._update_status(f"동기화 실패: {message}", "error")
    
    def _update_status(self, message: str, status_type: str = "info"):
        """상태바 업데이트."""
        icons = {
            "info": "ℹ️",
            "working": "⏳",
            "success": "✅",
            "error": "❌",
            "warning": "⚠️"
        }
        icon = icons.get(status_type, "ℹ️")
        self.task_status.setText(f"{icon} {message}")
        
        # 시간 표시
        if status_type in ("success", "error"):
            self.last_sync_label.setText(f"({datetime.now().strftime('%H:%M:%S')})")
    
    @Slot()
    def _on_generate_summary(self):
        """요약 생성."""
        if self.current_room_id is None:
            QMessageBox.warning(self, "알림", "먼저 채팅방을 선택하세요.")
            return

        if not self.current_room_file:
            QMessageBox.warning(self, "알림", "선택된 채팅방에 파일이 없습니다.\n먼저 파일을 업로드해주세요.")
            return

        # Check if summary already in progress via coordinator
        if self.worker_coordinator.summary_in_progress:
            QMessageBox.warning(self, "알림", "이미 요약이 진행 중입니다.\n완료 후 다시 시도하세요.")
            return

        # 현재 채팅방 이름 가져오기
        room_name = "Unknown"
        if self.current_room_id:
            room = self.chat_room_repo.get_by_id(self.current_room_id)
            if room:
                room_name = room.name

        # 통계 조회
        from file_storage import get_storage
        storage = get_storage()
        available_dates = storage.get_available_dates(room_name)
        summarized_dates = storage.get_summarized_dates(room_name)

        # 요약 필요한 날짜 조회
        dates_needing_summary = storage.get_dates_needing_summary(room_name)
        new_count = len(dates_needing_summary)
        needs_update_count = 0

        # 현재 LLM 설정 가져오기
        from full_config import config
        current_llm = config.current_provider

        # 요약 옵션 다이얼로그 (모달 OK - 옵션 선택은 차단이 자연스럽다)
        dialog = SummaryOptionsDialog(
            self,
            summarized_count=len(summarized_dates),
            total_count=len(available_dates),
            needs_update_count=needs_update_count,
            new_count=new_count,
            current_llm=current_llm
        )
        if dialog.exec() != QDialog.Accepted:
            return

        summary_type = dialog.summary_type
        skip_existing = dialog.skip_existing
        selected_llm = dialog.selected_llm
        llm_display_name = dialog.llm_combo.currentText()

        # 상태바에 프로그레스 위젯 삽입
        self.summary_progress_widget = SummaryProgressWidget(
            self, llm_name=llm_display_name, room_name=room_name
        )

        # 워커 코디네이터를 통한 요약 시작
        self.worker_coordinator.start_summary(
            room_id=self.current_room_id,
            room_name=room_name,
            file_path=self.current_room_file,
            summary_type=summary_type,
            skip_existing=skip_existing,
            llm_provider=selected_llm,
            progress_widget=self.summary_progress_widget
        )

        # 코디네이터 시그널 연결 (UI 업데이트용)
        self.worker_coordinator.summary_finished.connect(
            lambda success, result: self._handle_summary_result(success, result, room_name)
        )

    def _handle_summary_result(self, success: bool, result: str, room_name: str):
        """요약 결과 처리 (UI 업데이트)."""
        if success:
            # 현재 보고 있는 채팅방이 요약 대상 채팅방과 같으면 대시보드 갱신
            source_room_id = self.worker_coordinator.summary_source_room_id
            if self.current_room_id == source_room_id:
                # SummaryManager를 통해 요약 표시
                self.summary_manager.display_room_summaries(
                    self.current_room_id,
                    {},  # 통계는 빈 dict 전달 (필요시 조회)
                    room_name
                )
                # 대시보드 통계도 갱신
                self._on_room_selected(self.current_room_id, self.current_room_file or "")

    @Slot()
    def _on_recovery(self):
        """DB 복구 - 워커 코디네이터에 위임."""
        if self.worker_coordinator.start_recovery():
            # 코디네이터 시그널 연결 (DB 재연결용)
            self.worker_coordinator.recovery_finished.connect(self._handle_recovery_result)

    def _handle_recovery_result(self, success: bool, message: str):
        """복구 결과 처리 (DB 재연결)."""
        if success:
            # DB 재연결 및 UI 새로고침
            from db import get_db
            self.db = get_db(force_new=True)
            self._load_rooms()
        
        if success:
            self._update_status("DB 복구 완료", "success")
            QMessageBox.information(self, "복구 완료", message)
            
            # DB 재연결 및 UI 새로고침
            from db import get_db
            self.db = get_db(force_new=True)
            self._load_rooms()
        else:
            self._update_status("DB 복구 실패", "error")
            QMessageBox.warning(self, "복구 실패", message)
    
    @Slot()
    def _on_room_recovery(self):
        """파일 디렉터리에서 누락된 채팅방 복구 (비파괴적)."""
        self._update_status("채팅방 복구 스캔 중...", "working")

        storage = get_storage()
        file_rooms = storage.get_all_rooms()

        # DB에 이미 있는 채팅방 이름 목록
        db_rooms = self.chat_room_repo.get_all()
        db_room_names = {r.name for r in db_rooms}

        # 파일에는 있지만 DB에 없는 채팅방
        missing = [name for name in file_rooms if name not in db_room_names]

        if not missing:
            self._update_status("채팅방 복구 불필요", "success")
            QMessageBox.information(
                self, "채팅방 복구",
                "✅ 모든 채팅방이 DB에 존재합니다.\n누락된 채팅방이 없습니다."
            )
            return

        reply = QMessageBox.question(
            self, "채팅방 복구",
            f"📂 파일에는 있지만 DB에 없는 채팅방 {len(missing)}개를 발견했습니다:\n\n"
            + "\n".join(f"  • {name}" for name in missing)
            + "\n\nDB에 추가하시겠습니까?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )

        if reply != QMessageBox.Yes:
            self._update_status("채팅방 복구 취소", "info")
            return

        created = 0
        for name in missing:
            try:
                self.chat_room_repo.create(name)
                created += 1
            except Exception:
                pass

        self._update_status(f"채팅방 {created}개 복구 완료", "success")
        self._load_rooms()
        QMessageBox.information(
            self, "채팅방 복구 완료",
            f"✅ {created}개 채팅방을 DB에 추가했습니다."
        )

    @Slot()
    def _on_backup(self):
        """전체 백업 생성."""
        # 백업 목록 조회
        backups = self.storage.get_backup_list()
        
        # 확인 다이얼로그
        msg = "다음 항목을 백업합니다:\n\n"
        msg += "• DB (chat_history.db)\n"
        msg += "• 원본 대화 (data/original/)\n"
        msg += "• 요약 파일 (data/summary/)\n"
        msg += "• URL 파일 (data/url/)\n\n"
        
        if backups:
            msg += f"기존 백업: {len(backups)}개\n"
            msg += f"최근: {backups[0]['name']} ({backups[0]['size_mb']} MB)\n"
        
        reply = QMessageBox.question(
            self, "전체 백업",
            msg,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        self._update_status("백업 중...", "working")
        
        # 백업 실행
        backup_path = self.storage.create_full_backup()
        
        if backup_path:
            self._update_status("백업 완료", "success")
            QMessageBox.information(
                self, "백업 완료",
                f"✅ 백업이 완료되었습니다.\n\n📁 {backup_path}"
            )
        else:
            self._update_status("백업 실패", "error")
            QMessageBox.warning(
                self, "백업 실패",
                "❌ 백업 중 오류가 발생했습니다."
            )

    @Slot()
    def _on_refresh_stats(self):
        """통계 정보 갱신."""
        self._update_status("통계 갱신 중...", "working")
        self._load_rooms()
        if self.current_room_id:
            self._on_room_selected(self.current_room_id, self.current_room_file)
        self._update_status("통계 갱신 완료", "success")

    @Slot()
    def _on_settings(self):
        """설정 다이얼로그."""
        dialog = SettingsDialog(self)
        if dialog.exec() == QDialog.Accepted:
            # TODO: 설정 저장
            pass

    @Slot()
    def _on_room_backup(self):
        """선택된 채팅방 백업."""
        if not self.current_room_id:
            QMessageBox.warning(self, "채팅방 백업", "먼저 채팅방을 선택하세요.")
            return
        
        # 현재 채팅방 이름 가져오기
        room = self.chat_room_repo.get_by_id(self.current_room_id)
        if not room:
            QMessageBox.warning(self, "채팅방 백업", "채팅방 정보를 찾을 수 없습니다.")
            return
        
        room_name = room.name
        
        reply = QMessageBox.question(
            self, "채팅방 백업",
            f"'{room_name}' 채팅방을 백업하시겠습니까?\n\n"
            f"백업 대상:\n"
            f"• 원본 대화 (data/original/{room_name}/)\n"
            f"• 요약 파일 (data/summary/{room_name}/)\n"
            f"• URL 파일 (data/url/{room_name}/)",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        self._update_status(f"'{room_name}' 백업 중...", "working")
        
        backup_path = self.storage.backup_room(room_name)
        
        if backup_path:
            self._update_status(f"'{room_name}' 백업 완료", "success")
            QMessageBox.information(
                self, "채팅방 백업 완료",
                f"✅ '{room_name}' 백업이 완료되었습니다.\n\n📁 {backup_path}"
            )
        else:
            self._update_status("백업 실패", "error")
            QMessageBox.warning(self, "백업 실패", "❌ 백업 중 오류가 발생했습니다.")

    @Slot()
    def _on_restore_from_backup(self):
        """백업에서 복원."""
        backups = self.storage.get_backup_list()
        
        if not backups:
            QMessageBox.information(
                self, "백업에서 복원",
                "사용 가능한 백업이 없습니다.\n\n"
                "먼저 '💾 전체 백업...' 또는 '💾 채팅방 백업...'을 실행하세요."
            )
            return
        
        # 백업 선택 다이얼로그
        from PySide6.QtWidgets import QInputDialog
        
        backup_items = [
            f"{b['name']} ({b['size_mb']} MB)" for b in backups
        ]
        
        selected, ok = QInputDialog.getItem(
            self, "백업에서 복원",
            "복원할 백업을 선택하세요:",
            backup_items, 0, False
        )
        
        if not ok:
            return
        
        # 선택된 백업 찾기
        selected_idx = backup_items.index(selected)
        backup = backups[selected_idx]
        backup_path = backup['path']
        
        # 채팅방 목록 조회
        rooms_in_backup = self.storage.get_rooms_in_backup(backup_path)
        
        # 복원 범위 선택
        restore_options = ["전체 복원 (DB 포함)"] + [f"채팅방: {r}" for r in rooms_in_backup]
        
        selected_restore, ok = QInputDialog.getItem(
            self, "복원 범위 선택",
            f"백업: {backup['name']}\n\n복원 범위를 선택하세요:",
            restore_options, 0, False
        )
        
        if not ok:
            return
        
        # 복원 실행
        if selected_restore == "전체 복원 (DB 포함)":
            reply = QMessageBox.warning(
                self, "전체 복원 확인",
                "⚠️ 전체 복원은 현재 데이터를 덮어씁니다.\n\n"
                "• 현재 DB가 백업 시점의 DB로 교체됩니다\n"
                "• 모든 파일이 백업 시점으로 복원됩니다\n\n"
                "계속하시겠습니까?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply != QMessageBox.StandardButton.Yes:
                return
            
            self._update_status("전체 복원 중...", "working")
            success = self.storage.restore_from_backup(backup_path)
            
            if success:
                self._update_status("전체 복원 완료 (재시작 권장)", "success")
                QMessageBox.information(
                    self, "복원 완료",
                    "✅ 전체 복원이 완료되었습니다.\n\n"
                    "⚠️ DB가 변경되었으므로 앱을 재시작하세요."
                )
            else:
                self._update_status("복원 실패", "error")
                QMessageBox.warning(self, "복원 실패", "❌ 복원 중 오류가 발생했습니다.")
        else:
            # 개별 채팅방 복원
            room_name = selected_restore.replace("채팅방: ", "")
            
            self._update_status(f"'{room_name}' 복원 중...", "working")
            success = self.storage.restore_from_backup(backup_path, room_name)
            
            if success:
                self._update_status(f"'{room_name}' 복원 완료", "success")
                self._load_rooms()
                QMessageBox.information(
                    self, "복원 완료",
                    f"✅ '{room_name}' 채팅방이 복원되었습니다."
                )
            else:
                self._update_status("복원 실패", "error")
                QMessageBox.warning(self, "복원 실패", "❌ 복원 중 오류가 발생했습니다.")

    # ===== URL 정보 탭 메서드 =====
    # @MX:NOTE: Date-related methods (_show_calendar_dialog, _on_prev_date, _on_next_date,
    #          _on_date_changed, _update_date_tab_for_room) are now handled by SummaryManager

    
    def _load_url_from_db(self) -> Dict[str, List[str]]:
        """DB에서 URL 목록 로드."""
        if self.current_room_id is None:
            return {}
        return self.url_repo.get_by_room(self.current_room_id)
    
    def _display_url_list(self, urls_all: Dict[str, List[str]], source: str = "DB",
                          urls_recent: Dict[str, List[str]] = None,
                          urls_weekly: Dict[str, List[str]] = None):
        """URL 목록 표시 (3개 섹션: 3일, 1주, 전체)."""
        MAX_DISPLAY = 50  # 섹션당 최대 표시 개수
        
        # 알파벳순 정렬
        sorted_all = sorted(urls_all.items(), key=lambda x: x[0].lower())
        sorted_recent = sorted(urls_recent.items(), key=lambda x: x[0].lower()) if urls_recent else []
        sorted_weekly = sorted(urls_weekly.items(), key=lambda x: x[0].lower()) if urls_weekly else []
        
        total_urls = len(sorted_all)
        
        # HTML 섹션 생성 헬퍼
        def generate_url_section(title: str, emoji: str, urls: list, color: str, max_items: int = MAX_DISPLAY) -> str:
            if not urls:
                return f"""
                <div style="margin-bottom: 25px;">
                    <h3 style="color: {color}; margin-bottom: 10px;">{emoji} {title}</h3>
                    <p style="color: #999; font-size: 13px; padding: 15px; background: #F5F5F5; border-radius: 8px;">
                        해당 기간에 공유된 URL이 없습니다.
                    </p>
                </div>
                """
            
            total_count = len(urls)
            display_urls = urls[:max_items]
            has_more = total_count > max_items
            
            html = f"""
            <div style="margin-bottom: 25px;">
                <h3 style="color: {color}; margin-bottom: 10px; border-bottom: 2px solid {color}; padding-bottom: 5px;">
                    {emoji} {title} ({total_count}개)
                </h3>
            """
            for i, (url, descriptions) in enumerate(display_urls, 1):
                desc_text = " / ".join(descriptions) if descriptions else "설명 없음"
                html += f"""
                <div style="margin-bottom: 10px; padding: 10px; background-color: #F9F9F9; border-radius: 8px; border-left: 3px solid {color};">
                    <span style="color: #999; font-size: 11px; margin-right: 8px;">&nbsp;&nbsp;#{i}</span>
                    <a href="{url}" style="color: #1E88E5; text-decoration: none; word-break: break-all; font-size: 13px;">
                        {url}
                    </a>
                    <div style="color: #666; font-size: 11px; margin-top: 5px; margin-left: 25px;">
                        &nbsp;&nbsp;&nbsp;&nbsp;: {desc_text}
                    </div>
                </div>
                """
            
            # 초과 시 "더 있음" 표시
            if has_more:
                remaining = total_count - max_items
                html += f"""
                <div style="text-align: center; padding: 15px; background: #F0F0F0; border-radius: 8px; color: #666;">
                    <span style="font-size: 14px;">... 외 <b>{remaining}개</b> URL이 더 있습니다</span>
                </div>
                """
            
            html += "</div>"
            return html
        
        # HTML 생성
        if total_urls > 0:
            html = f"""
            <div style="padding: 10px;">
                <div style="background: linear-gradient(135deg, #FEE500, #FFD700); padding: 15px; border-radius: 10px; margin-bottom: 20px;">
                    <p style="color: #333; font-size: 14px; margin: 0;">
                        📊 총 <b>{total_urls}개</b> URL이 공유되었습니다.
                        <span style="font-size: 12px; color: #555;">
                            (출처: {source})
                            | 🔥 3일: {len(sorted_recent)}개
                            | 📅 1주: {len(sorted_weekly)}개
                        </span>
                    </p>
                </div>
            """
            
            # 섹션 1: 최근 3일
            html += generate_url_section("최근 3일", "🔥", sorted_recent, "#E53935", MAX_DISPLAY)
            
            # 섹션 2: 최근 1주 (제한 없이 모두 표시)
            html += generate_url_section("최근 1주", "📅", sorted_weekly, "#1E88E5", len(sorted_weekly))
            
            # 섹션 3: 전체 URL (제한 없이 모두 표시)
            html += generate_url_section("전체 URL", "📚", sorted_all, "#43A047", len(sorted_all))
            
            html += "</div>"
            self.url_browser.setHtml(html)
            self.url_count_label.setText(f"{total_urls}개 URL")
        else:
            self.url_browser.setHtml("""
                <div style="text-align: center; padding: 50px; color: #888;">
                    <p style="font-size: 48px;">🔗</p>
                    <p style="font-size: 16px;">공유된 URL이 없습니다</p>
                    <p style="font-size: 13px;">'🔄 동기화' 버튼을 눌러 요약에서 URL을 추출하세요</p>
                </div>
            """)
            self.url_count_label.setText("0개 URL")
        
        self._current_url_data = urls_all
    
    @Slot()
    def _refresh_url_list(self):
        """URL 목록 새로고침 (DB + 파일에서 로드)."""
        if self.current_room_id is None:
            self.url_browser.setHtml("""
                <div style="text-align: center; padding: 50px; color: #888;">
                    <p style="font-size: 48px;">📁</p>
                    <p style="font-size: 16px;">먼저 채팅방을 선택하세요</p>
                </div>
            """)
            self.url_count_label.setText("0개 URL")
            self.url_status_label.setText("")
            return
        
        self._update_status("URL 로드 중...", "working")
        
        room = self.chat_room_repo.get_by_id(self.current_room_id)
        if not room:
            return
        
        # 1. DB에서 전체 URL 로드
        urls_all = self._load_url_from_db()
        
        # 2. 파일에서 기간별 URL 로드
        urls_recent = self.storage.load_url_list(room.name, "recent")
        urls_weekly = self.storage.load_url_list(room.name, "weekly")
        
        if urls_all:
            self._display_url_list(urls_all, "DB", urls_recent, urls_weekly)
            self.url_status_label.setText("(DB)")
            self._update_status("URL 로드 완료", "success")
        else:
            # DB에 없으면 파일에서 전체 로드
            urls_all = self.storage.load_url_list(room.name, "all")
            if urls_all:
                self._display_url_list(urls_all, "파일", urls_recent, urls_weekly)
                self.url_status_label.setText("(파일)")
                self._update_status("URL 로드 완료 (파일)", "success")
            else:
                self._display_url_list({}, "", {}, {})
                self.url_status_label.setText("(동기화 필요)")
                self._update_status("URL 없음", "info")
    
    @Slot()
    def _sync_url_from_summaries(self):
        """요약 파일에서 URL 추출하여 DB와 파일(3개)에 저장."""
        if self.current_room_id is None:
            QMessageBox.warning(self, "알림", "먼저 채팅방을 선택하세요.")
            return
        
        room = self.chat_room_repo.get_by_id(self.current_room_id)
        if not room:
            return
        
        room_name = room.name
        self._update_status("URL 동기화 중...", "working")
        
        # 날짜 기준
        today = date.today()
        three_days_ago = today - timedelta(days=3)
        one_week_ago = today - timedelta(days=7)
        
        # 날짜별 URL 추출
        urls_by_date = {}  # {date_str: {url: [descriptions]}}
        summary_dates = self.storage.get_summarized_dates(room_name)
        
        for date_str in sorted(summary_dates):
            summary = self.storage.load_daily_summary(room_name, date_str)
            if summary:
                urls = extract_urls_from_text(summary)
                if urls:
                    urls_by_date[date_str] = urls
        
        # 기간별 URL 분류
        def extract_urls_for_period(start_date: date) -> dict:
            period_urls = {}
            for date_str, urls in urls_by_date.items():
                try:
                    d = date.fromisoformat(date_str)
                    if d >= start_date:
                        for url, descriptions in urls.items():
                            if url not in period_urls:
                                period_urls[url] = []
                            for desc in descriptions:
                                if desc and desc not in period_urls[url]:
                                    period_urls[url].append(desc)
                except:
                    pass
            return period_urls
        
        # 3개 기간별 URL
        urls_recent = deduplicate_urls(extract_urls_for_period(three_days_ago))
        urls_weekly = deduplicate_urls(extract_urls_for_period(one_week_ago))
        urls_all = {}
        for date_str, urls in urls_by_date.items():
            for url, descriptions in urls.items():
                if url not in urls_all:
                    urls_all[url] = []
                for desc in descriptions:
                    if desc and desc not in urls_all[url]:
                        urls_all[url].append(desc)
        
        # 최종 중복 제거 및 정렬
        urls_all = deduplicate_urls(urls_all)
        
        if urls_all:
            # DB에 저장 (기존 삭제 후 새로 추가)
            self.url_repo.delete_by_room(self.current_room_id)
            self.url_repo.add_urls_batch(self.current_room_id, urls_all)
            
            # 파일에 3개로 저장
            paths = self.storage.save_url_lists(room_name, urls_recent, urls_weekly, urls_all)
            
            # 3개 섹션과 함께 표시
            self._display_url_list(urls_all, "동기화됨", urls_recent, urls_weekly)
            self.url_status_label.setText("(동기화됨)")
            self._update_status(f"URL 동기화 완료 ({len(urls_all)}개)", "success")
            
            QMessageBox.information(
                self, "동기화 완료",
                f"✅ URL이 동기화되었습니다.\n\n"
                f"- DB에 저장됨\n"
                f"- 파일 저장:\n"
                f"  📁 {room_name}_urls_recent.md ({len(urls_recent)}개)\n"
                f"  📁 {room_name}_urls_weekly.md ({len(urls_weekly)}개)\n"
                f"  📁 {room_name}_urls_all.md ({len(urls_all)}개)"
            )
        else:
            self._display_url_list({}, "")
            self.url_status_label.setText("(URL 없음)")
            self._update_status("동기화할 URL 없음", "info")
            QMessageBox.information(self, "알림", "요약에서 추출된 URL이 없습니다.")
    
    @Slot()
    def _restore_url_from_file(self):
        """파일에서 URL 목록을 DB로 복구 (_urls_all.md 사용)."""
        if self.current_room_id is None:
            QMessageBox.warning(self, "알림", "먼저 채팅방을 선택하세요.")
            return
        
        room = self.chat_room_repo.get_by_id(self.current_room_id)
        if not room:
            return
        
        room_name = room.name
        self._update_status("URL 복구 중...", "working")
        
        # 전체 URL 파일에서 로드
        file_urls = self.storage.load_url_list(room_name, "all")
        
        if file_urls:
            # DB에 저장 (기존 삭제 후 새로 추가)
            self.url_repo.delete_by_room(self.current_room_id)
            self.url_repo.add_urls_batch(self.current_room_id, file_urls)
            
            # 기간별 파일도 로드
            urls_recent = self.storage.load_url_list(room_name, "recent")
            urls_weekly = self.storage.load_url_list(room_name, "weekly")
            
            self._display_url_list(file_urls, "복구됨", urls_recent, urls_weekly)
            self.url_status_label.setText("(복구됨)")
            self._update_status(f"URL 복구 완료 ({len(file_urls)}개)", "success")
            
            QMessageBox.information(
                self, "복구 완료",
                f"✅ {len(file_urls)}개 URL이 파일에서 DB로 복구되었습니다."
            )
        else:
            file_info = self.storage.get_url_file_info(room_name)
            if file_info is None:
                QMessageBox.warning(
                    self, "복구 실패",
                    f"URL 파일을 찾을 수 없습니다.\n\n"
                    f"예상 경로: data/url/{room_name}/{room_name}_urls_all.md\n\n"
                    f"'🔄 동기화' 버튼으로 요약에서 URL을 먼저 추출하세요."
                )
            else:
                QMessageBox.warning(self, "복구 실패", "파일에 URL이 없습니다.")
            self._update_status("URL 복구 실패", "error")
    
    def closeEvent(self, event):
        """앱 종료 시 진행 중인 요약 처리."""
        if self.worker_coordinator.summary_in_progress:
            reply = QMessageBox.question(
                self, "종료 확인",
                "요약이 진행 중입니다. 취소하고 종료하시겠습니까?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                event.ignore()
                return
            self.worker_coordinator.cancel_summary()
        event.accept()

    @Slot()
    def _on_about(self):
        """정보 다이얼로그."""
        QMessageBox.about(
            self, "카카오톡 대화 분석기",
            """<h3>🗨️ 카카오톡 대화 분석기</h3>
            <p>버전 2.3.1</p>
            <p>카카오톡 대화를 분석하고 AI로 요약하는 도구입니다.</p>
            <p>제작자: 민연홍<br>
            <a href="https://github.com/YeonHongMin/kakao-chat-summary">https://github.com/YeonHongMin/kakao-chat-summary</a></p>
            <p>&copy; 2026 KakaoTalk Chat Summary</p>"""
        )
