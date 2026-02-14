"""Base worker class for all background workers.

Provides common functionality:
- Progress signals
- Cancellation support
- Thread-safe Database instance management
"""
from abc import ABCMeta
from typing import Optional

from PySide6.QtCore import QThread, Signal


class QABCMeta(type(QThread), ABCMeta):
    """Combined metaclass for QThread + ABC compatibility."""
    pass


class BaseWorker(QThread, metaclass=QABCMeta):
    """Abstract base class for all worker threads.

    All workers MUST create their own Database instance in run()
    to ensure thread safety. Never share DB instances across threads.

    Signals:
        progress: (progress: int, message: str) - Progress updates (0-100)
        finished: (success: bool, message: str) - Work completion status
    """

    # Common signals
    progress = Signal(int, str)  # (progress_percent, status_message)
    finished = Signal(bool, str)  # (success, result_or_error_message)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._cancelled = False

    def cancel(self) -> None:
        """Request cancellation of the worker.

        Workers should check is_cancelled() periodically in their run() method.
        """
        self._cancelled = True

    def is_cancelled(self) -> bool:
        """Check if cancellation has been requested.

        Returns:
            True if cancel() was called, False otherwise.
        """
        return self._cancelled

    def run(self) -> None:
        """Execute the worker's task.

        Implementations must:
        1. Check is_cancelled() periodically
        2. Emit progress signals during long operations
        3. Emit finished signal when complete
        4. Create their own Database instance (never share across threads)
        """
        raise NotImplementedError("Subclasses must implement run()")

    def _create_worker_db(self):
        """Create a thread-local Database instance.

        CRITICAL: This must be called within run(), not __init__().
        The returned instance must be disposed after use with engine.dispose().

        Returns:
            Database: A new Database instance for this thread.
        """
        from db.database import Database
        return Database()

    def _dispose_db(self, db) -> None:
        """Safely dispose of a Database instance.

        Args:
            db: The Database instance to dispose.
        """
        try:
            if db and hasattr(db, 'engine'):
                db.engine.dispose()
        except Exception:
            pass  # Ignore disposal errors
