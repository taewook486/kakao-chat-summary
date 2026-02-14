"""Worker threads for background processing.

This module provides thread-safe worker classes for:
- File upload and parsing
- Chat synchronization
- Summary generation
- Database recovery

CRITICAL: All workers create their own Database instances in run()
to ensure thread safety. Never share DB instances across threads.
"""

from .base import BaseWorker
from .file_upload_worker import FileUploadWorker
from .sync_worker import SyncWorker
from .summary_worker import SummaryWorker
from .recovery_worker import RecoveryWorker

__all__ = [
    "BaseWorker",
    "FileUploadWorker",
    "SyncWorker",
    "SummaryWorker",
    "RecoveryWorker",
]
