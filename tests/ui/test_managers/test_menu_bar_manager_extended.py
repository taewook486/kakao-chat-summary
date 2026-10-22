"""Extended tests for MenuBarManager (P1 Coverage Gaps).

This test file covers previously untested lines in menu_bar_manager.py:
- __init__ method initialization
- setup_menu method with window parameter
- _setup_file_menu menu structure and signal connections
- _setup_tools_menu menu structure and signal connections
- _setup_help_menu menu structure and signal connections

@MX:NOTE: Extended tests for MenuBarManager coverage improvement
@MX:SPEC: SPEC-IMPROVE-001 Milestone 2.3
Target Coverage: 85%+
Current Coverage: 28%
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from PySide6.QtWidgets import QMainWindow, QMenuBar, QMenu, QApplication
from PySide6.QtGui import QAction
from PySide6.QtCore import Qt, QMetaObject, QMetaMethod


@pytest.mark.unit
class TestMenuBarManagerInitialization:
    """Tests for MenuBarManager.__init__ method (6 missing lines)."""

    def test_init_creates_manager_with_parent(self, qapp):
        """Test MenuBarManager initialization with parent window."""
        from src.ui.managers.menu_bar_manager import MenuBarManager

        parent_window = QMainWindow()
        manager = MenuBarManager(parent=parent_window)

        # Verify parent is stored
        assert manager._parent is parent_window
        # Verify initial state
        assert manager._menubar is None
        assert manager._file_menu is None
        assert manager._tools_menu is None
        assert manager._help_menu is None

    def test_init_without_parent(self, qapp):
        """Test MenuBarManager initialization without parent."""
        from src.ui.managers.menu_bar_manager import MenuBarManager

        manager = MenuBarManager(parent=None)

        # Verify parent is None
        assert manager._parent is None
        # Verify initial state
        assert manager._menubar is None
        assert manager._file_menu is None
        assert manager._tools_menu is None
        assert manager._help_menu is None


@pytest.mark.unit
class TestMenuBarManagerSetupMenu:
    """Tests for MenuBarManager.setup_menu method (8 missing lines)."""

    def test_setup_menu_creates_menubar(self, qapp):
        """Test setup_menu creates menu bar from window."""
        from src.ui.managers.menu_bar_manager import MenuBarManager

        window = QMainWindow()
        manager = MenuBarManager(parent=None)

        manager.setup_menu(window)

        # Verify menubar is created
        assert manager._menubar is not None
        assert isinstance(manager._menubar, QMenuBar)
        # Verify parent is updated
        assert manager._parent is window

    def test_setup_menu_uses_init_parent(self, qapp):
        """Test setup_menu uses parent from __init__ when window is None."""
        from src.ui.managers.menu_bar_manager import MenuBarManager

        window = QMainWindow()
        manager = MenuBarManager(parent=window)
        manager.setup_menu(window=None)

        # Verify menubar is created using init parent
        assert manager._menubar is not None
        assert manager._parent is window

    def test_setup_menu_raises_error_without_window(self, qapp):
        """Test setup_menu raises ValueError when no window available."""
        from src.ui.managers.menu_bar_manager import MenuBarManager

        manager = MenuBarManager(parent=None)

        with pytest.raises(ValueError, match="QMainWindow.*"):
            manager.setup_menu(window=None)

    def test_setup_menu_creates_all_submenus(self, qapp):
        """Test setup_menu creates file, tools, and help menus."""
        from src.ui.managers.menu_bar_manager import MenuBarManager

        window = QMainWindow()
        manager = MenuBarManager(parent=None)
        manager.setup_menu(window)

        # Verify all submenus are created
        assert manager._file_menu is not None
        assert manager._tools_menu is not None
        assert manager._help_menu is not None

        # Verify they are QMenu instances
        assert isinstance(manager._file_menu, QMenu)
        assert isinstance(manager._tools_menu, QMenu)
        assert isinstance(manager._help_menu, QMenu)

    def test_setup_menu_properties_return_menus(self, qapp):
        """Test menu properties return created menus."""
        from src.ui.managers.menu_bar_manager import MenuBarManager

        window = QMainWindow()
        manager = MenuBarManager(parent=None)
        manager.setup_menu(window)

        # Verify property access
        assert manager.file_menu is manager._file_menu
        assert manager.tools_menu is manager._tools_menu
        assert manager.help_menu is manager._help_menu


@pytest.mark.unit
class TestMenuBarManagerFileMenu:
    """Tests for MenuBarManager._setup_file_menu method (14 missing lines)."""

    def test_file_menu_has_correct_title(self, qapp):
        """Test file menu has '파일' title."""
        from src.ui.managers.menu_bar_manager import MenuBarManager

        window = QMainWindow()
        manager = MenuBarManager(parent=None)
        manager.setup_menu(window)

        assert manager._file_menu.title() == "파일"

    def test_file_menu_has_add_room_action(self, qapp):
        """Test file menu has '채팅방 추가...' action."""
        from src.ui.managers.menu_bar_manager import MenuBarManager

        window = QMainWindow()
        manager = MenuBarManager(parent=None)
        manager.setup_menu(window)

        actions = manager._file_menu.actions()
        add_action = None
        for action in actions:
            if action.text() == "채팅방 추가...":
                add_action = action
                break

        assert add_action is not None, "채팅방 추가... action not found"
        # Verify shortcut
        assert add_action.shortcut().toString() == "Ctrl+O"

    def test_file_menu_has_delete_room_action(self, qapp):
        """Test file menu has '채팅방 삭제...' action."""
        from src.ui.managers.menu_bar_manager import MenuBarManager

        window = QMainWindow()
        manager = MenuBarManager(parent=None)
        manager.setup_menu(window)

        actions = manager._file_menu.actions()
        delete_action = None
        for action in actions:
            if action.text() == "채팅방 삭제...":
                delete_action = action
                break

        assert delete_action is not None, "채팅방 삭제... action not found"

    def test_file_menu_has_exit_action(self, qapp):
        """Test file menu has '종료' action."""
        from src.ui.managers.menu_bar_manager import MenuBarManager

        window = QMainWindow()
        manager = MenuBarManager(parent=None)
        manager.setup_menu(window)

        actions = manager._file_menu.actions()
        exit_action = None
        for action in actions:
            if action.text() == "종료":
                exit_action = action
                break

        assert exit_action is not None, "종료 action not found"
        # Verify shortcut
        assert exit_action.shortcut().toString() == "Ctrl+Q"

    def test_file_menu_add_room_signal_connection(self, qapp):
        """Test add_room action triggers add_room_triggered signal."""
        from src.ui.managers.menu_bar_manager import MenuBarManager

        window = QMainWindow()
        manager = MenuBarManager(parent=None)
        manager.setup_menu(window)

        # Track signal emission
        signal_received = []
        manager.add_room_triggered.connect(lambda: signal_received.append(True))

        # Find and trigger add_room action
        actions = manager._file_menu.actions()
        for action in actions:
            if action.text() == "채팅방 추가...":
                action.triggered.emit()
                break

        assert len(signal_received) == 1

    def test_file_menu_delete_room_signal_connection(self, qapp):
        """Test delete_room action triggers delete_room_triggered signal."""
        from src.ui.managers.menu_bar_manager import MenuBarManager

        window = QMainWindow()
        manager = MenuBarManager(parent=None)
        manager.setup_menu(window)

        # Track signal emission
        signal_received = []
        manager.delete_room_triggered.connect(lambda: signal_received.append(True))

        # Find and trigger delete_room action
        actions = manager._file_menu.actions()
        for action in actions:
            if action.text() == "채팅방 삭제...":
                action.triggered.emit()
                break

        assert len(signal_received) == 1

    def test_file_menu_exit_signal_connection(self, qapp):
        """Test exit action triggers exit_triggered signal."""
        from src.ui.managers.menu_bar_manager import MenuBarManager

        window = QMainWindow()
        manager = MenuBarManager(parent=None)
        manager.setup_menu(window)

        # Track signal emission
        signal_received = []
        manager.exit_triggered.connect(lambda: signal_received.append(True))

        # Find and trigger exit action
        actions = manager._file_menu.actions()
        for action in actions:
            if action.text() == "종료":
                action.triggered.emit()
                break

        assert len(signal_received) == 1

    def test_file_menu_structure(self, qapp):
        """Test file menu has correct structure (actions + separator)."""
        from src.ui.managers.menu_bar_manager import MenuBarManager

        window = QMainWindow()
        manager = MenuBarManager(parent=None)
        manager.setup_menu(window)

        actions = manager._file_menu.actions()

        # Should have: add, delete, separator, exit
        # Total actions excluding separator: 3
        # With separator: 4 items
        non_separator_count = sum(1 for a in actions if not a.isSeparator())

        assert non_separator_count == 3  # add, delete, exit


@pytest.mark.unit
class TestMenuBarManagerToolsMenu:
    """Tests for MenuBarManager._setup_tools_menu method (26 missing lines)."""

    def test_tools_menu_has_correct_title(self, qapp):
        """Test tools menu has '도구' title."""
        from src.ui.managers.menu_bar_manager import MenuBarManager

        window = QMainWindow()
        manager = MenuBarManager(parent=None)
        manager.setup_menu(window)

        assert manager._tools_menu.title() == "도구"

    def test_tools_menu_has_sync_action(self, qapp):
        """Test tools menu has '지금 동기화' action."""
        from src.ui.managers.menu_bar_manager import MenuBarManager

        window = QMainWindow()
        manager = MenuBarManager(parent=None)
        manager.setup_menu(window)

        actions = manager._tools_menu.actions()
        sync_action = None
        for action in actions:
            if "지금 동기화" in action.text():
                sync_action = action
                break

        assert sync_action is not None
        assert sync_action.shortcut().toString() == "Ctrl+R"

    def test_tools_menu_has_summary_action(self, qapp):
        """Test tools menu has 'LLM 요약 생성' action."""
        from src.ui.managers.menu_bar_manager import MenuBarManager

        window = QMainWindow()
        manager = MenuBarManager(parent=None)
        manager.setup_menu(window)

        actions = manager._tools_menu.actions()
        summary_action = None
        for action in actions:
            if "LLM 요약 생성" in action.text():
                summary_action = action
                break

        assert summary_action is not None
        assert summary_action.shortcut().toString() == "Ctrl+G"

    def test_tools_menu_has_backup_action(self, qapp):
        """Test tools menu has '전체 백업' action."""
        from src.ui.managers.menu_bar_manager import MenuBarManager

        window = QMainWindow()
        manager = MenuBarManager(parent=None)
        manager.setup_menu(window)

        actions = manager._tools_menu.actions()
        backup_action = None
        for action in actions:
            if "전체 백업" in action.text():
                backup_action = action
                break

        assert backup_action is not None
        assert backup_action.shortcut().toString() == "Ctrl+B"
        assert "타임스탬프" in backup_action.toolTip()

    def test_tools_menu_has_room_backup_action(self, qapp):
        """Test tools menu has '채팅방 백업' action."""
        from src.ui.managers.menu_bar_manager import MenuBarManager

        window = QMainWindow()
        manager = MenuBarManager(parent=None)
        manager.setup_menu(window)

        actions = manager._tools_menu.actions()
        room_backup_action = None
        for action in actions:
            if "채팅방 백업" in action.text():
                room_backup_action = action
                break

        assert room_backup_action is not None
        assert "선택된 채팅방" in room_backup_action.toolTip()

    def test_tools_menu_has_restore_action(self, qapp):
        """Test tools menu has '백업에서 복원' action."""
        from src.ui.managers.menu_bar_manager import MenuBarManager

        window = QMainWindow()
        manager = MenuBarManager(parent=None)
        manager.setup_menu(window)

        actions = manager._tools_menu.actions()
        restore_action = None
        for action in actions:
            if "백업에서 복원" in action.text():
                restore_action = action
                break

        assert restore_action is not None

    def test_tools_menu_has_recovery_action(self, qapp):
        """Test tools menu has '파일에서 DB 재구축' action."""
        from src.ui.managers.menu_bar_manager import MenuBarManager

        window = QMainWindow()
        manager = MenuBarManager(parent=None)
        manager.setup_menu(window)

        actions = manager._tools_menu.actions()
        recovery_action = None
        for action in actions:
            if "파일에서 DB 재구축" in action.text():
                recovery_action = action
                break

        assert recovery_action is not None

    def test_tools_menu_has_room_recovery_action(self, qapp):
        """Test tools menu has '누락 채팅방 DB 추가' action."""
        from src.ui.managers.menu_bar_manager import MenuBarManager

        window = QMainWindow()
        manager = MenuBarManager(parent=None)
        manager.setup_menu(window)

        actions = manager._tools_menu.actions()
        room_recovery_action = None
        for action in actions:
            if "누락 채팅방 DB 추가" in action.text():
                room_recovery_action = action
                break

        assert room_recovery_action is not None

    def test_tools_menu_has_settings_action(self, qapp):
        """Test tools menu has '설정' action."""
        from src.ui.managers.menu_bar_manager import MenuBarManager

        window = QMainWindow()
        manager = MenuBarManager(parent=None)
        manager.setup_menu(window)

        actions = manager._tools_menu.actions()
        settings_action = None
        for action in actions:
            if "설정" in action.text():
                settings_action = action
                break

        assert settings_action is not None
        assert settings_action.shortcut().toString() == "Ctrl+,"

    def test_tools_menu_signal_connections(self, qapp):
        """Test all tools menu actions trigger correct signals."""
        from src.ui.managers.menu_bar_manager import MenuBarManager

        window = QMainWindow()
        manager = MenuBarManager(parent=None)
        manager.setup_menu(window)

        signal_tests = [
            ("manual_sync_triggered", "지금 동기화"),
            ("generate_summary_triggered", "LLM 요약 생성"),
            ("backup_triggered", "전체 백업"),
            ("room_backup_triggered", "채팅방 백업"),
            ("restore_from_backup_triggered", "백업에서 복원"),
            ("recovery_triggered", "파일에서 DB 재구축"),
            ("room_recovery_triggered", "누락 채팅방 DB 추가"),
            ("settings_triggered", "설정"),
        ]

        for signal_name, action_text in signal_tests:
            signal_received = []
            signal = getattr(manager, signal_name)
            signal.connect(lambda: signal_received.append(True))

            actions = manager._tools_menu.actions()
            for action in actions:
                if action_text in action.text():
                    action.triggered.emit()
                    break

            assert len(signal_received) == 1, f"Signal {signal_name} not triggered for {action_text}"


@pytest.mark.unit
class TestMenuBarManagerHelpMenu:
    """Tests for MenuBarManager._setup_help_menu method (4 missing lines)."""

    def test_help_menu_has_correct_title(self, qapp):
        """Test help menu has '도움말' title."""
        from src.ui.managers.menu_bar_manager import MenuBarManager

        window = QMainWindow()
        manager = MenuBarManager(parent=None)
        manager.setup_menu(window)

        assert manager._help_menu.title() == "도움말"

    def test_help_menu_has_about_action(self, qapp):
        """Test help menu has '정보' action."""
        from src.ui.managers.menu_bar_manager import MenuBarManager

        window = QMainWindow()
        manager = MenuBarManager(parent=None)
        manager.setup_menu(window)

        actions = manager._help_menu.actions()
        about_action = None
        for action in actions:
            if "정보" in action.text():
                about_action = action
                break

        assert about_action is not None

    def test_help_menu_about_signal_connection(self, qapp):
        """Test about action triggers about_triggered signal."""
        from src.ui.managers.menu_bar_manager import MenuBarManager

        window = QMainWindow()
        manager = MenuBarManager(parent=None)
        manager.setup_menu(window)

        # Track signal emission
        signal_received = []
        manager.about_triggered.connect(lambda: signal_received.append(True))

        # Find and trigger about action
        actions = manager._help_menu.actions()
        for action in actions:
            if "정보" in action.text():
                action.triggered.emit()
                break

        assert len(signal_received) == 1

    def test_help_menu_has_only_one_action(self, qapp):
        """Test help menu has exactly one non-separator action."""
        from src.ui.managers.menu_bar_manager import MenuBarManager

        window = QMainWindow()
        manager = MenuBarManager(parent=None)
        manager.setup_menu(window)

        actions = manager._help_menu.actions()
        non_separator_count = sum(1 for a in actions if not a.isSeparator())

        assert non_separator_count == 1


@pytest.mark.unit
class TestMenuBarManagerSignalDefinitions:
    """Tests for all signal definitions on MenuBarManager class."""

    def test_all_signals_are_signals(self, qapp):
        """Test all required attributes are Signal instances."""
        from src.ui.managers.menu_bar_manager import MenuBarManager
        from PySide6.QtCore import Signal

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

        for signal_name in required_signals:
            assert hasattr(MenuBarManager, signal_name)
            attr = getattr(MenuBarManager, signal_name)
            assert isinstance(attr, (Signal, type)), f"{signal_name} should be a Signal"
