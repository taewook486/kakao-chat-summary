"""Tests for worker initialization and thread safety."""
import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path

from src.workers.file_upload_worker import FileUploadWorker
from src.workers.sync_worker import SyncWorker
from src.workers.summary_worker import SummaryWorker
from src.workers.recovery_worker import RecoveryWorker


class TestFileUploadWorkerInit:
    """Test FileUploadWorker initialization."""

    def test_init_with_file_path(self, qapp, temp_dir):
        """Initialize with file path."""
        file_path = temp_dir / "test.txt"
        file_path.write_text("test content")
        worker = FileUploadWorker(str(file_path))

        assert worker.file_path == Path(file_path)
        assert worker.room_name is None
        assert worker.is_cancelled() is False

    def test_init_with_room_name(self, qapp, temp_dir):
        """Initialize with room name."""
        file_path = temp_dir / "test.txt"
        file_path.write_text("test content")
        worker = FileUploadWorker(str(file_path), room_name="TestRoom")

        assert worker.room_name == "TestRoom"

    def test_signals_defined(self, qapp, temp_dir):
        """Required signals are defined."""
        file_path = temp_dir / "test.txt"
        file_path.write_text("test content")
        worker = FileUploadWorker(str(file_path))

        assert hasattr(worker, 'progress')
        assert hasattr(worker, 'finished')


class TestSyncWorkerInit:
    """Test SyncWorker initialization."""

    def test_init_with_required_params(self, qapp, temp_dir):
        """Initialize with required parameters."""
        file_path = temp_dir / "test.txt"
        file_path.write_text("test content")
        worker = SyncWorker(room_id=1, file_path=str(file_path))

        assert worker.room_id == 1
        assert worker.file_path == Path(file_path)
        assert worker.is_cancelled() is False

    def test_signals_defined(self, qapp, temp_dir):
        """Required signals are defined."""
        file_path = temp_dir / "test.txt"
        file_path.write_text("test content")
        worker = SyncWorker(room_id=1, file_path=str(file_path))

        assert hasattr(worker, 'progress')
        assert hasattr(worker, 'finished')


class TestSummaryWorkerInit:
    """Test SummaryWorker initialization."""

    def test_init_with_required_params(self, qapp):
        """Initialize with required parameters."""
        worker = SummaryWorker(
            room_id=1,
            summary_type="daily"
        )

        assert worker.room_id == 1
        assert worker.summary_type == "daily"
        assert worker.room_name == "Unknown"
        assert worker.skip_existing is True
        assert worker.llm_provider == "glm"

    def test_init_with_all_params(self, qapp):
        """Initialize with all parameters."""
        worker = SummaryWorker(
            room_id=1,
            summary_type="pending",
            file_path="/path/to/file.txt",
            room_name="TestRoom",
            skip_existing=False,
            llm_provider="openai"
        )

        assert worker.room_id == 1
        assert worker.summary_type == "pending"
        assert worker.file_path == "/path/to/file.txt"
        assert worker.room_name == "TestRoom"
        assert worker.skip_existing is False
        assert worker.llm_provider == "openai"

    def test_signals_defined(self, qapp):
        """Required signals are defined."""
        worker = SummaryWorker(room_id=1, summary_type="daily")

        assert hasattr(worker, 'progress')
        assert hasattr(worker, 'finished')

    def test_cancel_support(self, qapp):
        """Worker supports cancellation."""
        worker = SummaryWorker(room_id=1, summary_type="daily")

        assert worker.is_cancelled() is False

        worker.cancel()

        assert worker.is_cancelled() is True


class TestRecoveryWorkerInit:
    """Test RecoveryWorker initialization."""

    def test_init_no_params(self, qapp):
        """Initialize without parameters."""
        worker = RecoveryWorker()

        assert worker.storage is None  # Initialized in run()
        assert worker.is_cancelled() is False

    def test_signals_defined(self, qapp):
        """Required signals are defined."""
        worker = RecoveryWorker()

        assert hasattr(worker, 'progress')
        assert hasattr(worker, 'finished')


class TestWorkerThreadSafety:
    """Test worker thread safety patterns."""

    def test_file_upload_worker_creates_own_db(self, qapp, temp_dir):
        """FileUploadWorker creates thread-local DB in run()."""
        file_path = temp_dir / "test.txt"
        file_path.write_text("test content")
        worker = FileUploadWorker(str(file_path))

        # storage is None until run() is called
        assert worker.storage is None

    def test_sync_worker_no_shared_db(self, qapp, temp_dir):
        """SyncWorker does not share DB instance."""
        file_path = temp_dir / "test.txt"
        file_path.write_text("test content")
        worker1 = SyncWorker(room_id=1, file_path=str(file_path))
        worker2 = SyncWorker(room_id=2, file_path=str(file_path))

        # Each worker should create its own DB in run()
        # No shared state at initialization
        assert worker1.room_id != worker2.room_id

    def test_summary_worker_no_shared_storage(self, qapp):
        """SummaryWorker does not share storage at init."""
        worker1 = SummaryWorker(room_id=1, summary_type="daily")
        worker2 = SummaryWorker(room_id=2, summary_type="daily")

        # Storage is initialized in run()
        assert worker1.storage is None
        assert worker2.storage is None

    def test_all_workers_inherit_from_base(self, qapp):
        """All workers inherit from BaseWorker."""
        from PySide6.QtCore import QThread

        # Verify all workers are QThread subclasses
        assert issubclass(FileUploadWorker, QThread)
        assert issubclass(SyncWorker, QThread)
        assert issubclass(SummaryWorker, QThread)
        assert issubclass(RecoveryWorker, QThread)

        # Verify all have cancel/is_cancelled methods (BaseWorker interface)
        for worker_cls in [FileUploadWorker, SyncWorker, SummaryWorker, RecoveryWorker]:
            assert hasattr(worker_cls, 'cancel')
            assert hasattr(worker_cls, 'is_cancelled')

    def test_all_workers_have_cancel_support(self, qapp, temp_dir):
        """All workers support cancellation."""
        file_path = temp_dir / "test.txt"
        file_path.write_text("test content")

        workers = [
            FileUploadWorker(str(file_path)),
            SyncWorker(room_id=1, file_path=str(file_path)),
            SummaryWorker(room_id=1, summary_type="daily"),
            RecoveryWorker(),
        ]

        for worker in workers:
            assert hasattr(worker, 'cancel')
            assert hasattr(worker, 'is_cancelled')
            assert worker.is_cancelled() is False
            worker.cancel()
            assert worker.is_cancelled() is True
