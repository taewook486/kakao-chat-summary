"""Synchronization worker for incremental chat updates.

Handles:
- Incremental message sync from file
- Database update with new messages
- Sync log recording
"""
from datetime import datetime, date
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Signal

from .base import BaseWorker
from .file_upload_worker import MessageParser


class SyncWorker(BaseWorker):
    """Worker for synchronizing chat files with database.

    Thread Safety:
        Creates its own Database instance in run() - never shares DB.

    Signals:
        progress: (int, str) - Progress percentage and status message
        finished: (bool, str) - Success and result message
    """

    # Use base class signals (bool, str)
    finished = Signal(bool, str)

    def __init__(
        self,
        room_id: int,
        file_path: str,
        parent=None
    ):
        """Initialize sync worker.

        Args:
            room_id: ID of the chat room to sync.
            file_path: Path to the chat file.
            parent: Optional parent QObject.
        """
        super().__init__(parent)
        self.room_id = room_id
        self.file_path = Path(file_path)

    def run(self) -> None:
        """Execute synchronization.

        Steps:
        1. Parse chat file
        2. Extract and save new messages
        3. Update sync time and log
        """
        from parser import KakaoLogParser

        # Create thread-local DB instance
        worker_db = self._create_worker_db()

        try:
            self.progress.emit(20, "Parsing...")

            parser = KakaoLogParser()
            parse_result = parser.parse(self.file_path)

            self.progress.emit(50, "Saving messages...")
            total_messages = 0
            new_messages = 0

            for date_str, lines in parse_result.messages_by_date.items():
                msg_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                messages = []

                for line in lines:
                    parsed = MessageParser.parse_message(line, msg_date)
                    if parsed:
                        messages.append(parsed)

                if messages:
                    total_messages += len(messages)
                    new_count = worker_db.add_messages(self.room_id, messages)
                    new_messages += new_count

            # Update sync time and log
            worker_db.update_room_sync_time(self.room_id)
            worker_db.add_sync_log(
                self.room_id, 'success',
                message_count=total_messages,
                new_message_count=new_messages
            )

            self.progress.emit(100, "Complete!")
            self.finished.emit(
                True,
                f"Sync complete: {new_messages:,} new messages"
            )

        except Exception as e:
            self.finished.emit(False, str(e))

        finally:
            self._dispose_db(worker_db)
