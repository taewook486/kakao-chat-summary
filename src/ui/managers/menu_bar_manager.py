"""MenuBarManager - 메뉴바 구성 및 관리.

MainWindow에서 추출됨 (SPEC-IMPROVE-001 Milestone 2.3).
이 관리자는 다음을 담당합니다:
- 파일, 도구, 도움말 메뉴 생성
- 메뉴 액션의 시그널 방출
- 단축키 설정

@MX:NOTE: Extracted from main_window.py Milestone 2.3
@MX:SPEC: SPEC-IMPROVE-001
"""

from typing import Optional

from PySide6.QtWidgets import QMainWindow, QMenuBar, QMenu
from PySide6.QtGui import QAction
from PySide6.QtCore import Signal, QObject


class MenuBarManager(QObject):
    """메뉴바 관리자.

    MainWindow의 메뉴바를 구성하고 관리합니다.
    각 메뉴 액션이 트리거되면 해당 시그널을 방출합니다.

    @MX:ANCHOR: MainWindow의 메뉴바 구성을 담당
    @MX:REASON: 메뉴 관련 로직을 분리하여 MainWindow 복잡도 감소
    """

    # 파일 메뉴 시그널
    add_room_triggered = Signal()
    delete_room_triggered = Signal()
    exit_triggered = Signal()

    # 도구 메뉴 시그널
    manual_sync_triggered = Signal()
    generate_summary_triggered = Signal()
    backup_triggered = Signal()
    room_backup_triggered = Signal()
    restore_from_backup_triggered = Signal()
    recovery_triggered = Signal()
    room_recovery_triggered = Signal()
    settings_triggered = Signal()

    # 도움말 메뉴 시그널
    about_triggered = Signal()

    def __init__(self, parent: Optional[QMainWindow] = None):
        """MenuBarManager 초기화.

        Args:
            parent: 부모 QMainWindow (메뉴바를 가져올 창)
        """
        super().__init__(parent)
        self._parent = parent
        self._menubar: Optional[QMenuBar] = None

        # 메뉴 참조 저장
        self._file_menu: Optional[QMenu] = None
        self._tools_menu: Optional[QMenu] = None
        self._help_menu: Optional[QMenu] = None

    def setup_menu(self, window: Optional[QMainWindow] = None) -> None:
        """메뉴바 구성.

        Args:
            window: 메뉴바를 구성할 QMainWindow (None이면 __init__의 parent 사용)
        """
        target = window or self._parent
        if target is None:
            raise ValueError("QMainWindow가 필요합니다.")

        self._parent = target
        self._menubar = target.menuBar()

        self._setup_file_menu()
        self._setup_tools_menu()
        self._setup_help_menu()

    def _setup_file_menu(self) -> None:
        """파일 메뉴 구성."""
        self._file_menu = self._menubar.addMenu("파일")

        # 채팅방 추가
        add_action = QAction("채팅방 추가...", self._parent)
        add_action.setShortcut("Ctrl+O")
        add_action.triggered.connect(self.add_room_triggered.emit)
        self._file_menu.addAction(add_action)

        # 채팅방 삭제
        delete_room_action = QAction("채팅방 삭제...", self._parent)
        delete_room_action.triggered.connect(self.delete_room_triggered.emit)
        self._file_menu.addAction(delete_room_action)

        self._file_menu.addSeparator()

        # 종료
        exit_action = QAction("종료", self._parent)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.exit_triggered.emit)
        self._file_menu.addAction(exit_action)

    def _setup_tools_menu(self) -> None:
        """도구 메뉴 구성."""
        self._tools_menu = self._menubar.addMenu("도구")

        # 지금 동기화
        sync_action = QAction("지금 동기화", self._parent)
        sync_action.setShortcut("Ctrl+R")
        sync_action.triggered.connect(self.manual_sync_triggered.emit)
        self._tools_menu.addAction(sync_action)

        # LLM 요약 생성
        summary_action = QAction("LLM 요약 생성", self._parent)
        summary_action.setShortcut("Ctrl+G")
        summary_action.triggered.connect(self.generate_summary_triggered.emit)
        self._tools_menu.addAction(summary_action)

        self._tools_menu.addSeparator()

        # === 백업/복원 (스냅샷 관리) ===
        backup_action = QAction("💾 전체 백업...", self._parent)
        backup_action.setShortcut("Ctrl+B")
        backup_action.setToolTip("DB, 원본 대화, 요약 파일을 타임스탬프 디렉터리에 백업")
        backup_action.triggered.connect(self.backup_triggered.emit)
        self._tools_menu.addAction(backup_action)

        room_backup_action = QAction("💾 채팅방 백업...", self._parent)
        room_backup_action.setToolTip("선택된 채팅방의 파일만 백업")
        room_backup_action.triggered.connect(self.room_backup_triggered.emit)
        self._tools_menu.addAction(room_backup_action)

        self._tools_menu.addSeparator()

        restore_action = QAction("📂 백업에서 복원...", self._parent)
        restore_action.setToolTip("백업 디렉터리에서 선택하여 복원")
        restore_action.triggered.connect(self.restore_from_backup_triggered.emit)
        self._tools_menu.addAction(restore_action)

        self._tools_menu.addSeparator()

        # === 파일↔DB 동기화 ===
        rebuild_action = QAction("🔄 파일에서 DB 재구축...", self._parent)
        rebuild_action.setToolTip("기존 DB를 삭제하고 data/original, data/summary 파일에서 재구축")
        rebuild_action.triggered.connect(self.recovery_triggered.emit)
        self._tools_menu.addAction(rebuild_action)

        add_missing_action = QAction("🔄 누락 채팅방 DB 추가...", self._parent)
        add_missing_action.setToolTip("파일 디렉터리에 있지만 DB에 없는 채팅방을 추가 (비파괴적)")
        add_missing_action.triggered.connect(self.room_recovery_triggered.emit)
        self._tools_menu.addAction(add_missing_action)

        self._tools_menu.addSeparator()

        settings_action = QAction("설정...", self._parent)
        settings_action.setShortcut("Ctrl+,")
        settings_action.triggered.connect(self.settings_triggered.emit)
        self._tools_menu.addAction(settings_action)

    def _setup_help_menu(self) -> None:
        """도움말 메뉴 구성."""
        self._help_menu = self._menubar.addMenu("도움말")

        about_action = QAction("정보", self._parent)
        about_action.triggered.connect(self.about_triggered.emit)
        self._help_menu.addAction(about_action)

    @property
    def file_menu(self) -> Optional[QMenu]:
        """파일 메뉴 참조 반환."""
        return self._file_menu

    @property
    def tools_menu(self) -> Optional[QMenu]:
        """도구 메뉴 참조 반환."""
        return self._tools_menu

    @property
    def help_menu(self) -> Optional[QMenu]:
        """도움말 메뉴 참조 반환."""
        return self._help_menu
