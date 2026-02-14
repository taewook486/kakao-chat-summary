"""Tests for BaseWorker abstract class."""
import pytest
from unittest.mock import MagicMock, patch
from PySide6.QtCore import QThread

from src.workers.base import BaseWorker


class ConcreteWorker(BaseWorker):
    """Concrete implementation for testing."""

    def run(self) -> None:
        """Test implementation."""
        self.progress.emit(50, "Halfway")
        self.finished.emit(True, "Done")


class TestBaseWorker:
    """Test BaseWorker functionality."""

    def test_worker_initialization(self, qapp):
        """Worker initializes with correct default state."""
        worker = ConcreteWorker()

        assert worker.is_cancelled() is False
        assert isinstance(worker, QThread)

    def test_cancel_request(self, qapp):
        """Cancel request sets cancelled flag."""
        worker = ConcreteWorker()

        assert worker.is_cancelled() is False

        worker.cancel()

        assert worker.is_cancelled() is True

    def test_progress_signal_defined(self, qapp):
        """Progress signal is defined."""
        worker = ConcreteWorker()

        # Signal exists and is connectable
        assert hasattr(worker, 'progress')
        assert hasattr(worker.progress, 'connect')

    def test_finished_signal_defined(self, qapp):
        """Finished signal is defined."""
        worker = ConcreteWorker()

        # Signal exists and is connectable
        assert hasattr(worker, 'finished')
        assert hasattr(worker.finished, 'connect')

    def test_create_worker_db_returns_database(self, qapp):
        """_create_worker_db returns Database instance."""
        worker = ConcreteWorker()

        with patch('db.database.Database') as MockDB:
            mock_db = MagicMock()
            MockDB.return_value = mock_db

            db = worker._create_worker_db()

            MockDB.assert_called_once()
            assert db == mock_db

    def test_dispose_db_calls_engine_dispose(self, qapp):
        """_dispose_db safely disposes database engine."""
        worker = ConcreteWorker()
        mock_db = MagicMock()
        mock_db.engine = MagicMock()

        worker._dispose_db(mock_db)

        mock_db.engine.dispose.assert_called_once()

    def test_dispose_db_handles_exception(self, qapp):
        """_dispose_db handles exceptions gracefully."""
        worker = ConcreteWorker()
        mock_db = MagicMock()
        mock_db.engine.dispose.side_effect = Exception("Dispose error")

        # Should not raise
        worker._dispose_db(mock_db)

    def test_dispose_db_handles_none(self, qapp):
        """_dispose_db handles None database."""
        worker = ConcreteWorker()

        # Should not raise
        worker._dispose_db(None)

    def test_dispose_db_handles_missing_engine(self, qapp):
        """_dispose_db handles database without engine attribute."""
        worker = ConcreteWorker()
        mock_db = MagicMock(spec=[])  # No engine attribute

        # Should not raise
        worker._dispose_db(mock_db)
