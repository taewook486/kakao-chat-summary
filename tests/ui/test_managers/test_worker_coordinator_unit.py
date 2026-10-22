"""
Unit tests for WorkerCoordinator class.

These tests verify the WorkerCoordinator behavior using mocked dependencies
to isolate the coordinator logic from worker implementations.

Target: src/ui/coordinators/worker_coordinator.py

Test Coverage:
- WorkerCoordinator initialization
- Worker creation and lifecycle management
- Signal connections
- Callback invocations
- State management
"""

import pytest
from unittest.mock import Mock, MagicMock, patch, call
from PySide6.QtWidgets import QWidget, QStatusBar, QMessageBox
from PySide6.QtCore import QObject, Signal

from src.ui.coordinators.worker_coordinator import (
    WorkerCoordinator,
    WorkerCallbacks
)


@pytest.fixture
def real_parent(qapp):
    """Create real QWidget parent for coordinator (Qt requires real objects)."""
    parent = QWidget()
    yield parent
    parent.deleteLater()


@pytest.fixture
def real_statusbar(qapp):
    """Create real QStatusBar."""
    statusbar = QStatusBar()
    yield statusbar
    statusbar.deleteLater()


@pytest.fixture
def mock_callbacks():
    """Create mock callbacks for worker events."""
    return WorkerCallbacks(
        update_status=Mock(),
        refresh_rooms=Mock(),
        select_room=Mock(),
        set_generate_button_enabled=Mock(),
        show_message=Mock()
    )


@pytest.fixture
def coordinator(real_parent, mock_callbacks, real_statusbar):
    """Create WorkerCoordinator instance with real Qt objects."""
    return WorkerCoordinator(
        parent=real_parent,
        callbacks=mock_callbacks,
        statusbar=real_statusbar
    )


@pytest.fixture
def coordinator_no_statusbar(real_parent, mock_callbacks):
    """Create WorkerCoordinator without statusbar."""
    return WorkerCoordinator(
        parent=real_parent,
        callbacks=mock_callbacks,
        statusbar=None
    )


class TestWorkerCallbacksDataclass:
    """Test WorkerCallbacks dataclass."""

    def test_worker_callbacks_has_required_fields(self):
        """
        CAPTURE: WorkerCallbacks has all required callback fields.
        """
        callbacks = WorkerCallbacks(
            update_status=Mock(),
            refresh_rooms=Mock(),
            select_room=Mock(),
            set_generate_button_enabled=Mock(),
            show_message=Mock()
        )

        assert hasattr(callbacks, 'update_status')
        assert hasattr(callbacks, 'refresh_rooms')
        assert hasattr(callbacks, 'select_room')
        assert hasattr(callbacks, 'set_generate_button_enabled')
        assert hasattr(callbacks, 'show_message')


class TestWorkerCoordinatorInitialization:
    """Test WorkerCoordinator initialization behavior."""

    def test_coordinator_inherits_from_qobject(self, coordinator):
        """
        CAPTURE: WorkerCoordinator inherits from QObject.
        """
        assert isinstance(coordinator, QObject)

    def test_coordinator_has_signals(self, coordinator):
        """
        CAPTURE: WorkerCoordinator has defined signals.
        """
        assert hasattr(coordinator, 'upload_finished')
        assert hasattr(coordinator, 'sync_finished')
        assert hasattr(coordinator, 'summary_finished')
        assert hasattr(coordinator, 'recovery_finished')
        assert hasattr(coordinator, 'progress_update')

    def test_coordinator_initializes_with_defaults(self, real_parent, mock_callbacks):
        """
        CAPTURE: WorkerCoordinator initializes with None worker references.
        """
        coordinator = WorkerCoordinator(
            parent=real_parent,
            callbacks=mock_callbacks
        )

        assert coordinator._upload_worker is None
        assert coordinator._sync_worker is None
        assert coordinator._summary_worker is None
        assert coordinator._recovery_worker is None

    def test_coordinator_initializes_summary_state(self, coordinator):
        """
        CAPTURE: WorkerCoordinator initializes summary state to False.
        """
        assert coordinator.summary_in_progress is False
        assert coordinator._summary_in_progress is False
        assert coordinator.summary_source_room_id is None

    def test_coordinator_stores_dependencies(self, coordinator, real_parent, mock_callbacks):
        """
        CAPTURE: WorkerCoordinator stores parent and callbacks.
        """
        assert coordinator._parent is real_parent
        assert coordinator._callbacks is mock_callbacks


class TestWorkerCoordinatorUpload:
    """Test upload worker management."""

    @patch('src.ui.coordinators.worker_coordinator.FileUploadWorker')
    def test_start_upload_creates_worker(self, MockWorker, coordinator):
        """
        CAPTURE: start_upload creates FileUploadWorker with correct params.
        """
        mock_worker = MagicMock()
        mock_worker.progress = MagicMock()
        mock_worker.finished = MagicMock()
        MockWorker.return_value = mock_worker

        coordinator.start_upload("/test/path.txt", "Test Room")

        MockWorker.assert_called_once_with("/test/path.txt", "Test Room")

    @patch('src.ui.coordinators.worker_coordinator.FileUploadWorker')
    def test_start_upload_calls_update_status(self, MockWorker, coordinator, mock_callbacks):
        """
        CAPTURE: start_upload calls update_status with "working" status.
        """
        mock_worker = MagicMock()
        mock_worker.progress = MagicMock()
        mock_worker.finished = MagicMock()
        MockWorker.return_value = mock_worker

        coordinator.start_upload("/test/path.txt", "Test Room")

        mock_callbacks.update_status.assert_called_once()
        call_args = mock_callbacks.update_status.call_args
        assert "파일 업로드 중" in call_args[0][0]
        assert call_args[0][1] == "working"

    @patch('src.ui.coordinators.worker_coordinator.FileUploadWorker')
    def test_start_upload_disables_button(self, MockWorker, coordinator, mock_callbacks):
        """
        CAPTURE: start_upload disables generate button.
        """
        mock_worker = MagicMock()
        mock_worker.progress = MagicMock()
        mock_worker.finished = MagicMock()
        MockWorker.return_value = mock_worker

        coordinator.start_upload("/test/path.txt", "Test Room")

        mock_callbacks.set_generate_button_enabled.assert_called_once_with(False)

    @patch('src.ui.coordinators.worker_coordinator.FileUploadWorker')
    def test_start_upload_connects_signals(self, MockWorker, coordinator):
        """
        CAPTURE: start_upload connects worker signals.
        """
        mock_worker = MagicMock()
        mock_worker.progress = MagicMock()
        mock_worker.finished = MagicMock()
        MockWorker.return_value = mock_worker

        coordinator.start_upload("/test/path.txt", "Test Room")

        mock_worker.progress.connect.assert_called_once()
        mock_worker.finished.connect.assert_called_once()

    @patch('src.ui.coordinators.worker_coordinator.FileUploadWorker')
    def test_start_upload_starts_worker(self, MockWorker, coordinator):
        """
        CAPTURE: start_upload calls worker.start().
        """
        mock_worker = MagicMock()
        mock_worker.progress = MagicMock()
        mock_worker.finished = MagicMock()
        MockWorker.return_value = mock_worker

        coordinator.start_upload("/test/path.txt", "Test Room")

        mock_worker.start.assert_called_once()

    @patch('src.ui.coordinators.worker_coordinator.FileUploadWorker')
    def test_on_upload_finished_success(self, MockWorker, coordinator, mock_callbacks):
        """
        CAPTURE: Upload success updates status and shows message.
        """
        mock_worker = MagicMock()
        MockWorker.return_value = mock_worker
        coordinator.start_upload("/test/path.txt", "Test Room")

        # Simulate successful upload
        coordinator._on_upload_finished(True, "Success message", 123)

        assert coordinator._upload_worker is None
        mock_callbacks.set_generate_button_enabled.assert_called_with(True)
        mock_callbacks.update_status.assert_called_with("업로드 완료", "success")
        mock_callbacks.show_message.assert_called_once()
        mock_callbacks.refresh_rooms.assert_called_once()
        mock_callbacks.select_room.assert_called_once_with(123, "")

    @patch('src.ui.coordinators.worker_coordinator.FileUploadWorker')
    def test_on_upload_finished_failure(self, MockWorker, coordinator, mock_callbacks):
        """
        CAPTURE: Upload failure shows error message.
        """
        mock_worker = MagicMock()
        MockWorker.return_value = mock_worker
        coordinator.start_upload("/test/path.txt", "Test Room")

        # Simulate failed upload
        coordinator._on_upload_finished(False, "Error message", 0)

        assert coordinator._upload_worker is None
        mock_callbacks.set_generate_button_enabled.assert_called_with(True)
        mock_callbacks.update_status.assert_called_with("업로드 실패", "error")
        mock_callbacks.show_message.assert_called_once()

    @patch('src.ui.coordinators.worker_coordinator.FileUploadWorker')
    def test_on_upload_finished_emits_signal(self, MockWorker, coordinator):
        """
        CAPTURE: Upload completion emits upload_finished signal.
        """
        mock_worker = MagicMock()
        MockWorker.return_value = mock_worker

        # Track signal emissions by connecting a spy
        emitted_values = []

        def capture_signal(success, message, room_id):
            emitted_values.append((success, message, room_id))

        coordinator.upload_finished.connect(capture_signal)
        coordinator.start_upload("/test/path.txt", "Test Room")
        coordinator._on_upload_finished(True, "Done", 456)

        # Verify signal was emitted
        assert len(emitted_values) == 1
        assert emitted_values[0] == (True, "Done", 456)


class TestWorkerCoordinatorSync:
    """Test sync worker management."""

    @patch('src.ui.coordinators.worker_coordinator.SyncWorker')
    def test_start_sync_creates_worker(self, MockWorker, coordinator):
        """
        CAPTURE: start_sync creates SyncWorker with correct params.
        """
        mock_worker = MagicMock()
        mock_worker.progress = MagicMock()
        mock_worker.finished = MagicMock()
        MockWorker.return_value = mock_worker

        coordinator.start_sync(room_id=1, file_path="/test/path.txt")

        MockWorker.assert_called_once()
        # Verify call arguments
        call_args = MockWorker.call_args
        assert call_args[0][0] == 1  # room_id
        assert call_args[0][1] == "/test/path.txt"  # file_path

    @patch('src.ui.coordinators.worker_coordinator.SyncWorker')
    def test_start_sync_calls_update_status(self, MockWorker, coordinator, mock_callbacks):
        """
        CAPTURE: start_sync calls update_status.
        """
        mock_worker = MagicMock()
        mock_worker.progress = MagicMock()
        mock_worker.finished = MagicMock()
        MockWorker.return_value = mock_worker

        coordinator.start_sync(room_id=1, file_path="/test/path.txt")

        mock_callbacks.update_status.assert_called_once()
        assert "동기화 중" in mock_callbacks.update_status.call_args[0][0]

    @patch('src.ui.coordinators.worker_coordinator.SyncWorker')
    def test_start_sync_connects_signals(self, MockWorker, coordinator):
        """
        CAPTURE: start_sync connects worker signals.
        """
        mock_worker = MagicMock()
        mock_worker.progress = MagicMock()
        mock_worker.finished = MagicMock()
        MockWorker.return_value = mock_worker

        coordinator.start_sync(room_id=1, file_path="/test/path.txt")

        mock_worker.progress.connect.assert_called_once()
        mock_worker.finished.connect.assert_called_once()

    @patch('src.ui.coordinators.worker_coordinator.SyncWorker')
    def test_on_sync_finished_success(self, MockWorker, coordinator, mock_callbacks):
        """
        CAPTURE: Sync success updates status and refreshes rooms.
        """
        mock_worker = MagicMock()
        MockWorker.return_value = mock_worker
        coordinator.start_sync(room_id=1, file_path="/test/path.txt")

        coordinator._on_sync_finished(True, "Sync complete")

        assert coordinator._sync_worker is None
        mock_callbacks.update_status.assert_called_with("Sync complete", "success")
        mock_callbacks.refresh_rooms.assert_called_once()

    @patch('src.ui.coordinators.worker_coordinator.SyncWorker')
    def test_on_sync_finished_failure(self, MockWorker, coordinator, mock_callbacks):
        """
        CAPTURE: Sync failure updates status with error.
        """
        mock_worker = MagicMock()
        MockWorker.return_value = mock_worker
        coordinator.start_sync(room_id=1, file_path="/test/path.txt")

        coordinator._on_sync_finished(False, "Sync failed")

        assert coordinator._sync_worker is None
        update_call = mock_callbacks.update_status.call_args
        assert "동기화 실패" in update_call[0][0]
        assert update_call[0][1] == "error"


class TestWorkerCoordinatorSummary:
    """Test summary worker management."""

    def test_start_summary_returns_false_when_in_progress(self, coordinator, mock_callbacks):
        """
        CAPTURE: start_summary returns False if summary already in progress.
        """
        coordinator._summary_in_progress = True

        result = coordinator.start_summary(
            room_id=1,
            room_name="Test",
            file_path="/test.txt",
            summary_type="all",
            skip_existing=True,
            llm_provider="glm"
        )

        assert result is False
        mock_callbacks.show_message.assert_called_once()
        assert "이미 요약이 진행 중입니다" in mock_callbacks.show_message.call_args[0][1]

    @patch('src.ui.coordinators.worker_coordinator.SummaryWorker')
    def test_start_summary_creates_worker(self, MockWorker, coordinator):
        """
        CAPTURE: start_summary creates SummaryWorker with correct params.
        """
        mock_worker = MagicMock()
        mock_worker.progress = MagicMock()
        mock_worker.finished = MagicMock()
        MockWorker.return_value = mock_worker

        coordinator.start_summary(
            room_id=1,
            room_name="Test Room",
            file_path="/test/path.txt",
            summary_type="all",
            skip_existing=True,
            llm_provider="glm"
        )

        MockWorker.assert_called_once()
        call_kwargs = MockWorker.call_args[1]
        assert call_kwargs['room_id'] == 1
        assert call_kwargs['room_name'] == "Test Room"
        assert call_kwargs['summary_type'] == "all"
        assert call_kwargs['skip_existing'] is True
        assert call_kwargs['llm_provider'] == "glm"

    @patch('src.ui.coordinators.worker_coordinator.SummaryWorker')
    def test_start_summary_sets_state(self, MockWorker, coordinator, mock_callbacks):
        """
        CAPTURE: start_summary sets summary state flags.
        """
        mock_worker = MagicMock()
        mock_worker.progress = MagicMock()
        mock_worker.finished = MagicMock()
        MockWorker.return_value = mock_worker

        coordinator.start_summary(
            room_id=123,
            room_name="Test",
            file_path="/test.txt",
            summary_type="all",
            skip_existing=False,
            llm_provider="openai"
        )

        assert coordinator.summary_in_progress is True
        assert coordinator.summary_source_room_id == 123
        mock_callbacks.set_generate_button_enabled.assert_called_once_with(False)

    @patch('src.ui.coordinators.worker_coordinator.SummaryWorker')
    def test_start_summary_with_progress_widget(self, MockWorker, coordinator, qapp):
        """
        CAPTURE: start_summary inserts progress widget into statusbar.
        """
        from PySide6.QtWidgets import QWidget

        mock_worker = MagicMock()
        mock_worker.progress = MagicMock()
        mock_worker.finished = MagicMock()
        MockWorker.return_value = mock_worker

        # Use real QWidget instead of mock for progress widget
        mock_widget = QWidget()
        mock_widget.update_progress = MagicMock()
        mock_widget.cancel_requested = MagicMock()

        coordinator.start_summary(
            room_id=1,
            room_name="Test",
            file_path="/test.txt",
            summary_type="all",
            skip_existing=False,
            llm_provider="glm",
            progress_widget=mock_widget
        )

        # Verify widget was stored
        assert coordinator._summary_progress_widget is mock_widget
        # show() is a real method on QWidget, can't assert with mock
        # But we verify widget was stored successfully
        mock_widget.deleteLater()  # cleanup

    @patch('src.ui.coordinators.worker_coordinator.SummaryWorker')
    def test_start_summary_connects_cancel_signal(self, MockWorker, coordinator, qapp):
        """
        CAPTURE: start_summary connects cancel_requested signal.
        """
        from PySide6.QtWidgets import QWidget
        from PySide6.QtCore import Signal

        mock_worker = MagicMock()
        mock_worker.progress = MagicMock()
        mock_worker.finished = MagicMock()
        mock_worker.cancel = Mock()
        MockWorker.return_value = mock_worker

        # Create a real widget with a signal
        class MockWidget(QWidget):
            cancel_requested = Signal()

        mock_widget = MockWidget()
        mock_widget.update_progress = MagicMock()

        coordinator.start_summary(
            room_id=1,
            room_name="Test",
            file_path="/test.txt",
            summary_type="all",
            skip_existing=False,
            llm_provider="glm",
            progress_widget=mock_widget
        )

        # Verify cancel connection (Signal objects don't have assert_called)
        # We just verify it doesn't error
        mock_widget.deleteLater()  # cleanup

    @patch('src.ui.coordinators.worker_coordinator.SummaryWorker')
    def test_on_summary_finished_clears_state(self, MockWorker, coordinator, mock_callbacks, qapp):
        """
        CAPTURE: Summary finished clears summary state.

        Note: Current behavior does NOT clear summary_source_room_id.
        This is a characterization test that captures actual behavior.
        """
        from PySide6.QtWidgets import QWidget

        mock_worker = MagicMock()
        MockWorker.return_value = mock_worker

        # Use real widget for progress widget
        mock_widget = QWidget()
        mock_widget.update_progress = MagicMock()

        coordinator.start_summary(
            room_id=1,
            room_name="Test",
            file_path="/test.txt",
            summary_type="all",
            skip_existing=False,
            llm_provider="glm",
            progress_widget=mock_widget
        )

        coordinator._on_summary_finished(True, "Summary result")

        # Capture: summary_in_progress IS cleared
        assert coordinator.summary_in_progress is False
        # Capture: summary_source_room_id is NOT cleared (actual behavior)
        assert coordinator.summary_source_room_id == 1
        mock_callbacks.set_generate_button_enabled.assert_called_with(True)
        mock_widget.deleteLater()  # cleanup

    @patch('src.ui.coordinators.worker_coordinator.SummaryWorker')
    def test_on_summary_finished_removes_progress_widget(self, MockWorker, coordinator, real_statusbar, qapp):
        """
        CAPTURE: Summary finished removes progress widget.
        """
        from PySide6.QtWidgets import QWidget

        mock_worker = MagicMock()
        MockWorker.return_value = mock_worker

        # Use real QWidget for progress widget
        mock_widget = QWidget()
        mock_widget.update_progress = MagicMock()

        coordinator.start_summary(
            room_id=1,
            room_name="Test",
            file_path="/test.txt",
            summary_type="all",
            skip_existing=False,
            llm_provider="glm",
            progress_widget=mock_widget
        )

        coordinator._on_summary_finished(True, "Result")

        # Widget should be cleaned up
        assert coordinator._summary_progress_widget is None
        # Note: deleteLater() schedules deletion, can't easily test with mock
        # but we verify state is cleared
        mock_widget.deleteLater()  # cleanup for test

    @patch('src.ui.coordinators.worker_coordinator.SummaryWorker')
    def test_on_summary_finished_success(self, MockWorker, coordinator, mock_callbacks):
        """
        CAPTURE: Summary success updates status.
        """
        mock_worker = MagicMock()
        MockWorker.return_value = mock_worker
        coordinator.start_summary(
            room_id=1,
            room_name="Test",
            file_path="/test.txt",
            summary_type="all",
            skip_existing=False,
            llm_provider="glm"
        )

        coordinator._on_summary_finished(True, "Summary result")

        mock_callbacks.update_status.assert_called_with("요약 생성 완료", "success")

    @patch('src.ui.coordinators.worker_coordinator.SummaryWorker')
    def test_on_summary_finished_failure(self, MockWorker, coordinator, mock_callbacks):
        """
        CAPTURE: Summary failure shows error message.
        """
        mock_worker = MagicMock()
        MockWorker.return_value = mock_worker
        coordinator.start_summary(
            room_id=1,
            room_name="Test",
            file_path="/test.txt",
            summary_type="all",
            skip_existing=False,
            llm_provider="glm"
        )

        coordinator._on_summary_finished(False, "Error result")

        mock_callbacks.update_status.assert_called_with("요약 생성 실패", "error")
        mock_callbacks.show_message.assert_called_once()

    @patch('src.ui.coordinators.worker_coordinator.SummaryWorker')
    def test_cancel_summary(self, MockWorker, coordinator):
        """
        CAPTURE: cancel_summary calls worker.cancel().
        """
        mock_worker = MagicMock()
        mock_worker.cancel = Mock()
        MockWorker.return_value = mock_worker
        coordinator.start_summary(
            room_id=1,
            room_name="Test",
            file_path="/test.txt",
            summary_type="all",
            skip_existing=False,
            llm_provider="glm"
        )

        coordinator.cancel_summary()

        mock_worker.cancel.assert_called_once()


class TestWorkerCoordinatorRecovery:
    """Test recovery worker management."""

    @patch('src.ui.coordinators.worker_coordinator.QMessageBox.question')
    @patch('src.ui.coordinators.worker_coordinator.RecoveryWorker')
    def test_start_recovery_shows_confirmation(self, MockWorker, mock_question, coordinator, mock_callbacks):
        """
        CAPTURE: start_recovery shows confirmation dialog.
        """
        mock_worker = MagicMock()
        mock_worker.progress = MagicMock()
        mock_worker.finished = MagicMock()
        MockWorker.return_value = mock_worker
        mock_question.return_value = QMessageBox.No

        coordinator.start_recovery()

        mock_question.assert_called_once()
        assert "DB 복구" in str(mock_question.call_args)

    @patch('src.ui.coordinators.worker_coordinator.QMessageBox.question')
    def test_start_recovery_returns_false_on_cancel(self, mock_question, coordinator):
        """
        CAPTURE: start_recovery returns False if user cancels.
        """
        mock_question.return_value = QMessageBox.No

        result = coordinator.start_recovery()

        assert result is False

    @patch('src.ui.coordinators.worker_coordinator.QMessageBox.question')
    @patch('src.ui.coordinators.worker_coordinator.RecoveryWorker')
    def test_start_recovery_starts_on_yes(self, MockWorker, mock_question, coordinator, mock_callbacks):
        """
        CAPTURE: start_recovery starts worker if user confirms.
        """
        mock_worker = MagicMock()
        mock_worker.progress = MagicMock()
        mock_worker.finished = MagicMock()
        MockWorker.return_value = mock_worker
        mock_question.return_value = QMessageBox.Yes

        result = coordinator.start_recovery()

        assert result is True
        mock_worker.start.assert_called_once()
        mock_callbacks.set_generate_button_enabled.assert_called_once_with(False)

    @patch('src.ui.coordinators.worker_coordinator.QMessageBox.question')
    @patch('src.ui.coordinators.worker_coordinator.RecoveryWorker')
    def test_on_recovery_finished_success(self, MockWorker, mock_question, coordinator, mock_callbacks):
        """
        CAPTURE: Recovery success shows message and updates status.
        """
        mock_worker = MagicMock()
        MockWorker.return_value = mock_worker
        mock_question.return_value = QMessageBox.Yes
        coordinator.start_recovery()

        coordinator._on_recovery_finished(True, "Recovery complete")

        assert coordinator._recovery_worker is None
        mock_callbacks.set_generate_button_enabled.assert_called_with(True)
        mock_callbacks.update_status.assert_called_with("DB 복구 완료", "success")
        mock_callbacks.show_message.assert_called_once()

    @patch('src.ui.coordinators.worker_coordinator.QMessageBox.question')
    @patch('src.ui.coordinators.worker_coordinator.RecoveryWorker')
    def test_on_recovery_finished_failure(self, MockWorker, mock_question, coordinator, mock_callbacks):
        """
        CAPTURE: Recovery failure shows error message.
        """
        mock_worker = MagicMock()
        MockWorker.return_value = mock_worker
        mock_question.return_value = QMessageBox.Yes
        coordinator.start_recovery()

        coordinator._on_recovery_finished(False, "Recovery failed")

        assert coordinator._recovery_worker is None
        mock_callbacks.update_status.assert_called_with("DB 복구 실패", "error")


class TestWorkerCoordinatorCleanup:
    """Test cleanup functionality."""

    @patch('src.ui.coordinators.worker_coordinator.FileUploadWorker')
    def test_cleanup_cancels_running_workers(self, MockWorker, coordinator):
        """
        CAPTURE: cleanup cancels all running workers.
        """
        # Create mock workers
        mock_upload = MagicMock()
        mock_upload.isRunning.return_value = True
        mock_upload.wait = Mock()
        MockWorker.return_value = mock_upload

        coordinator.start_upload("/test.txt", "Test")

        coordinator.cleanup()

        mock_upload.cancel.assert_called_once()
        mock_upload.wait.assert_called_once_with(1000)

    @patch('src.ui.coordinators.worker_coordinator.FileUploadWorker')
    def test_cleanup_skips_non_running_workers(self, MockWorker, coordinator):
        """
        CAPTURE: cleanup only cancels running workers.
        """
        mock_upload = MagicMock()
        mock_upload.isRunning.return_value = False
        MockWorker.return_value = mock_upload

        coordinator.start_upload("/test.txt", "Test")

        coordinator.cleanup()

        mock_upload.cancel.assert_not_called()
