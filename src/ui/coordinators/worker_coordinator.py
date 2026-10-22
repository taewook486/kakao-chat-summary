"""WorkerCoordinator - Background worker lifecycle management.

Manages creation, signal connections, and lifecycle of all background workers:
- FileUploadWorker: File parsing and message storage
- SyncWorker: Incremental chat synchronization
- SummaryWorker: LLM-based summary generation
- RecoveryWorker: Database recovery from file storage

@MX:NOTE: Extracted from main_window.py Milestone 2.3
@MX:SPEC: SPEC-IMPROVE-001
"""

from typing import Optional, Callable, Any
from dataclasses import dataclass

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QWidget, QMessageBox, QStatusBar

from src.workers.file_upload_worker import FileUploadWorker
from src.workers.sync_worker import SyncWorker
from src.workers.summary_worker import SummaryWorker
from src.workers.recovery_worker import RecoveryWorker


@dataclass
class WorkerCallbacks:
    """Callbacks for worker events.

    @MX:NOTE: Data class for dependency injection pattern
    """
    update_status: Callable[[str, str], None]
    refresh_rooms: Callable[[], None]
    select_room: Callable[[int, str], None]
    set_generate_button_enabled: Callable[[bool], None]
    show_message: Callable[[str, str, str], None]  # title, message, type


class WorkerCoordinator(QObject):
    """Manages background worker lifecycle for MainWindow.

    Responsibilities:
    - Create workers with appropriate parameters
    - Connect worker signals to callbacks
    - Track worker state and progress
    - Handle worker completion and cleanup

    Signals:
        upload_finished: Emitted when upload completes (success, message, room_id)
        sync_finished: Emitted when sync completes (success, message)
        summary_finished: Emitted when summary completes (success, result)
        recovery_finished: Emitted when recovery completes (success, message)
        progress_update: Emitted for progress updates (progress, message)

    @MX:ANCHOR: Central worker management point
    @MX:REASON: fan_in >= 4 (upload, sync, summary, recovery all flow through here)
    """

    # Worker completion signals
    upload_finished = Signal(bool, str, int)  # success, message, room_id
    sync_finished = Signal(bool, str)  # success, message
    summary_finished = Signal(bool, str)  # success, result
    recovery_finished = Signal(bool, str)  # success, message

    # Progress signal
    progress_update = Signal(int, str)  # progress, message

    def __init__(
        self,
        parent: QWidget,
        callbacks: WorkerCallbacks,
        statusbar: Optional[QStatusBar] = None
    ):
        """Initialize worker coordinator.

        Args:
            parent: Parent widget for message boxes
            callbacks: Callback functions for worker events
            statusbar: Optional status bar for progress widgets
        """
        super().__init__(parent)
        self._parent = parent
        self._callbacks = callbacks
        self._statusbar = statusbar

        # Worker references
        self._upload_worker: Optional[FileUploadWorker] = None
        self._sync_worker: Optional[SyncWorker] = None
        self._summary_worker: Optional[SummaryWorker] = None
        self._recovery_worker: Optional[RecoveryWorker] = None

        # Summary state tracking
        self._summary_in_progress: bool = False
        self._summary_source_room_id: Optional[int] = None
        self._summary_progress_widget: Optional[QWidget] = None

    # === Worker State Properties ===

    @property
    def summary_in_progress(self) -> bool:
        """Check if summary generation is in progress."""
        return self._summary_in_progress

    @property
    def summary_source_room_id(self) -> Optional[int]:
        """Get the room ID for current summary operation."""
        return self._summary_source_room_id

    # === File Upload Worker ===

    def start_upload(self, file_path: str, room_name: str) -> bool:
        """Start file upload worker.

        Args:
            file_path: Path to the chat file
            room_name: Name of the chat room

        Returns:
            True if worker started successfully
        """
        self._callbacks.update_status("파일 업로드 중...", "working")
        self._callbacks.set_generate_button_enabled(False)

        self._upload_worker = FileUploadWorker(file_path, room_name)
        self._upload_worker.progress.connect(self._on_upload_progress)
        self._upload_worker.finished.connect(self._on_upload_finished)
        self._upload_worker.start()
        return True

    def _on_upload_progress(self, progress: int, message: str):
        """Handle upload progress updates."""
        self._callbacks.update_status(f"{message} ({progress}%)", "working")
        self.progress_update.emit(progress, message)

    def _on_upload_finished(self, success: bool, message: str, room_id: int):
        """Handle upload completion."""
        self._callbacks.set_generate_button_enabled(True)

        if success:
            self._callbacks.update_status("업로드 완료", "success")
            self._callbacks.show_message("업로드 완료", message, "info")
            self._callbacks.refresh_rooms()

            if room_id > 0:
                self._callbacks.select_room(room_id, "")
        else:
            self._callbacks.update_status("업로드 실패", "error")
            self._callbacks.show_message("업로드 실패", message, "warning")

        self.upload_finished.emit(success, message, room_id)
        self._upload_worker = None

    # === Sync Worker ===

    def start_sync(self, room_id: int, file_path: str) -> bool:
        """Start sync worker.

        Args:
            room_id: ID of the room to sync
            file_path: Path to the chat file

        Returns:
            True if worker started successfully
        """
        self._callbacks.update_status("동기화 중...", "working")

        self._sync_worker = SyncWorker(room_id, file_path)
        self._sync_worker.progress.connect(
            lambda p, m: self._callbacks.update_status(f"{m} ({p}%)", "working")
        )
        self._sync_worker.finished.connect(self._on_sync_finished)
        self._sync_worker.start()
        return True

    def _on_sync_finished(self, success: bool, message: str):
        """Handle sync completion."""
        if success:
            self._callbacks.update_status(message, "success")
            self._callbacks.refresh_rooms()
        else:
            self._callbacks.update_status(f"동기화 실패: {message}", "error")

        self.sync_finished.emit(success, message)
        self._sync_worker = None

    # === Summary Worker ===

    def start_summary(
        self,
        room_id: int,
        room_name: str,
        file_path: Optional[str],
        summary_type: str,
        skip_existing: bool,
        llm_provider: str,
        progress_widget: Optional[QWidget] = None
    ) -> bool:
        """Start summary generation worker.

        Args:
            room_id: ID of the room
            room_name: Name of the room
            file_path: Path to the chat file
            summary_type: Type of summary ('today', 'yesterday', '2days', 'all', 'pending')
            skip_existing: Whether to skip already summarized dates
            llm_provider: LLM provider to use
            progress_widget: Optional widget for progress display

        Returns:
            True if worker started successfully
        """
        if self._summary_in_progress:
            self._callbacks.show_message(
                "알림",
                "이미 요약이 진행 중입니다.\n완료 후 다시 시도하세요.",
                "warning"
            )
            return False

        self._summary_in_progress = True
        self._summary_source_room_id = room_id
        self._callbacks.set_generate_button_enabled(False)

        # Handle progress widget
        self._summary_progress_widget = progress_widget
        if progress_widget and self._statusbar:
            self._statusbar.insertPermanentWidget(0, progress_widget)
            progress_widget.show()

        self._callbacks.update_status(f"요약 생성 중...", "working")

        self._summary_worker = SummaryWorker(
            room_id=room_id,
            summary_type=summary_type,
            file_path=file_path,
            room_name=room_name,
            skip_existing=skip_existing,
            llm_provider=llm_provider
        )

        # Connect signals
        if progress_widget and hasattr(progress_widget, 'update_progress'):
            self._summary_worker.progress.connect(progress_widget.update_progress)

        self._summary_worker.progress.connect(
            lambda p, m: self._callbacks.update_status(m, "working")
        )
        self._summary_worker.finished.connect(self._on_summary_finished)

        # Connect cancel if available
        if progress_widget and hasattr(progress_widget, 'cancel_requested'):
            progress_widget.cancel_requested.connect(self._summary_worker.cancel)

        self._summary_worker.start()
        return True

    def _on_summary_finished(self, success: bool, result: str):
        """Handle summary completion."""
        self._callbacks.set_generate_button_enabled(True)
        self._summary_in_progress = False

        # Remove progress widget
        if self._summary_progress_widget and self._statusbar:
            self._statusbar.removeWidget(self._summary_progress_widget)
            self._summary_progress_widget.deleteLater()
            self._summary_progress_widget = None

        if success:
            self._callbacks.update_status("요약 생성 완료", "success")
        else:
            self._callbacks.update_status("요약 생성 실패", "error")
            self._callbacks.show_message("요약 실패", result, "warning")

        self.summary_finished.emit(success, result)
        self._summary_worker = None

    # === Recovery Worker ===

    def start_recovery(self) -> bool:
        """Start database recovery worker.

        Returns:
            True if worker started successfully
        """
        # Confirm with user
        reply = QMessageBox.question(
            self._parent, "DB 복구",
            "주의: 기존 DB를 삭제하고 파일 저장소에서 복구합니다.\n\n"
            "data/original 및 data/summary 폴더의 파일을 기반으로\n"
            "새로운 데이터베이스를 생성합니다.\n\n"
            "계속하시겠습니까?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply != QMessageBox.Yes:
            return False

        self._callbacks.update_status("DB 복구 중...", "working")
        self._callbacks.set_generate_button_enabled(False)

        self._recovery_worker = RecoveryWorker()
        self._recovery_worker.progress.connect(
            lambda p, m: self._callbacks.update_status(f"{m} ({p}%)", "working")
        )
        self._recovery_worker.finished.connect(self._on_recovery_finished)
        self._recovery_worker.start()
        return True

    def _on_recovery_finished(self, success: bool, message: str):
        """Handle recovery completion."""
        self._callbacks.set_generate_button_enabled(True)

        if success:
            self._callbacks.update_status("DB 복구 완료", "success")
            self._callbacks.show_message("복구 완료", message, "info")
        else:
            self._callbacks.update_status("DB 복구 실패", "error")
            self._callbacks.show_message("복구 실패", message, "warning")

        self.recovery_finished.emit(success, message)
        self._recovery_worker = None

    # === Utility Methods ===

    def cancel_summary(self):
        """Cancel ongoing summary generation."""
        if self._summary_worker and self._summary_in_progress:
            self._summary_worker.cancel()

    def cleanup(self):
        """Clean up any running workers."""
        for worker in [
            self._upload_worker,
            self._sync_worker,
            self._summary_worker,
            self._recovery_worker
        ]:
            if worker and worker.isRunning():
                worker.cancel()
                worker.wait(1000)  # Wait up to 1 second
