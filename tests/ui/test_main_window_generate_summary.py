"""
Regression tests for MainWindow._on_generate_summary guard.

Rooms created via "채팅방 만들기" have no file_path in the DB, and uploading
into an existing room never fills it in. The summary worker reads daily
originals from file storage by room name, so the guard must check storage,
not current_room_file.
"""

from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtWidgets import QDialog

from ui.main_window import MainWindow

NO_FILE_MSG = "선택된 채팅방에 파일이 없습니다"


def _make_window(room_file):
    window = MagicMock()
    window.current_room_id = 4
    window.current_room_file = room_file
    window.worker_coordinator.summary_in_progress = False
    window.chat_room_repo.get_by_id.return_value.name = "노동공제회"
    return window


def _make_storage(available_dates):
    storage = MagicMock()
    storage.get_available_dates.return_value = available_dates
    storage.get_summarized_dates.return_value = []
    storage.get_dates_needing_summary.return_value = available_dates
    return storage


def _warned_no_file(warning_mock):
    return any(NO_FILE_MSG in str(call.args[2]) for call in warning_mock.call_args_list)


@pytest.mark.ui
def test_room_without_file_path_but_with_stored_data_opens_options(qapp):
    window = _make_window(room_file=None)
    storage = _make_storage(["2026-10-20", "2026-10-21"])

    with patch("ui.main_window.QMessageBox.warning") as warning, \
         patch("file_storage.get_storage", return_value=storage), \
         patch("full_config.config"), \
         patch("ui.main_window.SummaryOptionsDialog") as dialog_cls:
        dialog_cls.return_value.exec.return_value = QDialog.Rejected
        MainWindow._on_generate_summary(window)

    assert not _warned_no_file(warning)
    dialog_cls.assert_called_once()


@pytest.mark.ui
def test_room_without_stored_data_warns_no_file(qapp):
    window = _make_window(room_file=None)
    storage = _make_storage([])

    with patch("ui.main_window.QMessageBox.warning") as warning, \
         patch("file_storage.get_storage", return_value=storage), \
         patch("full_config.config"), \
         patch("ui.main_window.SummaryOptionsDialog") as dialog_cls:
        MainWindow._on_generate_summary(window)

    assert _warned_no_file(warning)
    dialog_cls.assert_not_called()
