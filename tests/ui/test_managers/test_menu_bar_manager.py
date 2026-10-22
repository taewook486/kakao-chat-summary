"""MenuBarManager에 대한 특성화 테스트.

이 테스트는 메뉴바 관리자의 현재 동작을 캡처합니다.
리팩토링 후에도 동일한 동작이 유지되는지 확인합니다.

@MX:NOTE: Characterization tests for MenuBarManager extraction
@MX:SPEC: SPEC-IMPROVE-001 Milestone 2.3
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from PySide6.QtWidgets import QMainWindow, QMenuBar, QMenu
from PySide6.QtGui import QAction
from PySide6.QtCore import Signal, QObject


class TestMainWindowMenuHandlers:
    """MainWindow의 메뉴 핸들러 메서드 존재 여부 테스트.

    이 테스트들은 MenuBarManager 추출 후에도 핸들러 메서드가 MainWindow에 남아있는지 확인합니다.
    """

    def test_characterize_add_room_handler_exists(self):
        """_on_add_room 핸들러가 존재하는지 확인합니다."""
        from src.ui.main_window import MainWindow

        # 클래스 레벨에서 메서드 존재 확인
        assert hasattr(MainWindow, '_on_add_room')
        assert callable(getattr(MainWindow, '_on_add_room'))

    def test_characterize_delete_room_handler_exists(self):
        """_on_delete_room 핸들러가 존재하는지 확인합니다."""
        from src.ui.main_window import MainWindow

        assert hasattr(MainWindow, '_on_delete_room')
        assert callable(getattr(MainWindow, '_on_delete_room'))

    def test_characterize_manual_sync_handler_exists(self):
        """_on_manual_sync 핸들러가 존재하는지 확인합니다."""
        from src.ui.main_window import MainWindow

        assert hasattr(MainWindow, '_on_manual_sync')
        assert callable(getattr(MainWindow, '_on_manual_sync'))

    def test_characterize_generate_summary_handler_exists(self):
        """_on_generate_summary 핸들러가 존재하는지 확인합니다."""
        from src.ui.main_window import MainWindow

        assert hasattr(MainWindow, '_on_generate_summary')
        assert callable(getattr(MainWindow, '_on_generate_summary'))

    def test_characterize_backup_handler_exists(self):
        """_on_backup 핸들러가 존재하는지 확인합니다."""
        from src.ui.main_window import MainWindow

        assert hasattr(MainWindow, '_on_backup')
        assert callable(getattr(MainWindow, '_on_backup'))

    def test_characterize_room_backup_handler_exists(self):
        """_on_room_backup 핸들러가 존재하는지 확인합니다."""
        from src.ui.main_window import MainWindow

        assert hasattr(MainWindow, '_on_room_backup')
        assert callable(getattr(MainWindow, '_on_room_backup'))

    def test_characterize_restore_from_backup_handler_exists(self):
        """_on_restore_from_backup 핸들러가 존재하는지 확인합니다."""
        from src.ui.main_window import MainWindow

        assert hasattr(MainWindow, '_on_restore_from_backup')
        assert callable(getattr(MainWindow, '_on_restore_from_backup'))

    def test_characterize_recovery_handler_exists(self):
        """_on_recovery 핸들러가 존재하는지 확인합니다."""
        from src.ui.main_window import MainWindow

        assert hasattr(MainWindow, '_on_recovery')
        assert callable(getattr(MainWindow, '_on_recovery'))

    def test_characterize_room_recovery_handler_exists(self):
        """_on_room_recovery 핸들러가 존재하는지 확인합니다."""
        from src.ui.main_window import MainWindow

        assert hasattr(MainWindow, '_on_room_recovery')
        assert callable(getattr(MainWindow, '_on_room_recovery'))

    def test_characterize_settings_handler_exists(self):
        """_on_settings 핸들러가 존재하는지 확인합니다."""
        from src.ui.main_window import MainWindow

        assert hasattr(MainWindow, '_on_settings')
        assert callable(getattr(MainWindow, '_on_settings'))

    def test_characterize_about_handler_exists(self):
        """_on_about 핸들러가 존재하는지 확인합니다."""
        from src.ui.main_window import MainWindow

        assert hasattr(MainWindow, '_on_about')
        assert callable(getattr(MainWindow, '_on_about'))

    def test_characterize_setup_menu_method_exists(self):
        """_setup_menu 메서드가 존재하는지 확인합니다."""
        from src.ui.main_window import MainWindow

        assert hasattr(MainWindow, '_setup_menu')
        assert callable(getattr(MainWindow, '_setup_menu'))


class TestMenuBarManagerClass:
    """MenuBarManager 클래스 테스트.

    MenuBarManager 추출 후 이 테스트들은 새 클래스의 동작을 검증합니다.
    """

    def test_menu_bar_manager_has_add_room_signal(self):
        """MenuBarManager가 add_room_triggered 시그널을 가지고 있는지 확인합니다."""
        from src.ui.managers.menu_bar_manager import MenuBarManager

        # 클래스 레벨에서 시그널 존재 확인
        assert hasattr(MenuBarManager, 'add_room_triggered')

    def test_menu_bar_manager_has_delete_room_signal(self):
        """MenuBarManager가 delete_room_triggered 시그널을 가지고 있는지 확인합니다."""
        from src.ui.managers.menu_bar_manager import MenuBarManager

        assert hasattr(MenuBarManager, 'delete_room_triggered')

    def test_menu_bar_manager_has_all_required_signals(self):
        """MenuBarManager가 모든 필수 시그널을 가지고 있는지 확인합니다."""
        from src.ui.managers.menu_bar_manager import MenuBarManager

        required_signals = [
            'add_room_triggered',
            'delete_room_triggered',
            'manual_sync_triggered',
            'generate_summary_triggered',
            'backup_triggered',
            'room_backup_triggered',
            'restore_from_backup_triggered',
            'recovery_triggered',
            'room_recovery_triggered',
            'settings_triggered',
            'about_triggered',
            'exit_triggered'
        ]
        for signal in required_signals:
            assert hasattr(MenuBarManager, signal), f"'{signal}' 시그널이 필요합니다"


class TestMenuBarStructure:
    """메뉴 구조 검증 테스트.

    MenuBarManager의 메뉴 구조를 검증합니다.
    """

    def test_setup_menu_creates_file_menu(self):
        """MenuBarManager가 파일 메뉴를 생성하는지 확인합니다."""
        from src.ui.managers.menu_bar_manager import MenuBarManager
        import inspect

        # _setup_file_menu 메서드의 소스 코드 확인
        source = inspect.getsource(MenuBarManager._setup_file_menu)
        assert '"파일"' in source or "'파일'" in source, "파일 메뉴가 정의되어야 합니다"

    def test_setup_menu_creates_tools_menu(self):
        """MenuBarManager가 도구 메뉴를 생성하는지 확인합니다."""
        from src.ui.managers.menu_bar_manager import MenuBarManager
        import inspect

        source = inspect.getsource(MenuBarManager._setup_tools_menu)
        assert '"도구"' in source or "'도구'" in source, "도구 메뉴가 정의되어야 합니다"

    def test_setup_menu_creates_help_menu(self):
        """MenuBarManager가 도움말 메뉴를 생성하는지 확인합니다."""
        from src.ui.managers.menu_bar_manager import MenuBarManager
        import inspect

        source = inspect.getsource(MenuBarManager._setup_help_menu)
        assert '"도움말"' in source or "'도움말'" in source, "도움말 메뉴가 정의되어야 합니다"

    def test_setup_menu_uses_menu_manager(self):
        """_setup_menu가 MenuBarManager를 사용하는지 확인합니다."""
        from src.ui.main_window import MainWindow
        import inspect

        source = inspect.getsource(MainWindow._setup_menu)
        assert 'menu_manager' in source, "MenuBarManager가 사용되어야 합니다"

    def test_main_window_has_menu_manager(self):
        """MainWindow가 menu_manager 속성을 가지고 있는지 확인합니다."""
        from src.ui.main_window import MainWindow

        assert hasattr(MainWindow, '__init__')
        # __init__ 소스에서 menu_manager 초기화 확인
        import inspect
        source = inspect.getsource(MainWindow.__init__)
        assert 'menu_manager' in source, "menu_manager가 초기화되어야 합니다"
