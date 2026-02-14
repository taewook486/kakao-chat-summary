"""Database recovery worker.

Handles:
- Scanning file storage for chat rooms
- Rebuilding database from file storage
- Restoring messages and summaries
"""
from datetime import datetime
from typing import List

from PySide6.QtCore import Signal

from .base import BaseWorker
from .file_upload_worker import MessageParser


class RecoveryWorker(BaseWorker):
    """Worker for recovering database from file storage.

    Thread Safety:
        Creates its own Database instance in run() - never shares DB.

    Signals:
        progress: (int, str) - Progress percentage and status message
        finished: (bool, str) - Success and recovery summary or error
    """

    # Use base class signals
    finished = Signal(bool, str)

    def __init__(self, parent=None):
        """Initialize recovery worker.

        Args:
            parent: Optional parent QObject.
        """
        super().__init__(parent)
        self.storage = None  # Initialized in run()

    def run(self) -> None:
        """Execute database recovery.

        Steps:
        1. Reset database
        2. Scan file storage for rooms
        3. Restore messages for each room
        4. Restore summaries for each room
        """
        from file_storage import get_storage
        from db import get_db, reset_db

        # Initialize storage
        self.storage = get_storage()

        try:
            self.progress.emit(5, "Initializing database...")

            # Reset database
            reset_db()
            db = get_db(force_new=True)

            # Scan for rooms
            self.progress.emit(10, "Scanning file storage...")
            rooms = self.storage.get_all_rooms()

            if not rooms:
                self.finished.emit(False, "No data to recover.")
                return

            total_messages = 0
            total_summaries = 0

            for room_idx, room_name in enumerate(rooms):
                room_progress = 10 + int((room_idx / len(rooms)) * 80)
                self.progress.emit(
                    room_progress,
                    f"Recovering '{room_name}'..."
                )

                # Create room
                room = db.create_room(room_name)

                # Restore messages
                messages_by_date = self.storage.load_all_originals(room_name)

                for date_str, lines in messages_by_date.items():
                    msg_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                    messages = []

                    for line in lines:
                        parsed = MessageParser.parse_message(line, msg_date)
                        if parsed:
                            messages.append(parsed)

                    if messages:
                        try:
                            db.add_messages(room.id, messages)
                            total_messages += len(messages)
                        except Exception:
                            pass  # Continue with other data

                # Restore summaries
                summary_dates = self.storage.get_summarized_dates(room_name)
                for date_str in summary_dates:
                    summary_content = self.storage.load_daily_summary(
                        room_name, date_str
                    )
                    if summary_content:
                        try:
                            summary_date = datetime.strptime(
                                date_str, '%Y-%m-%d'
                            ).date()
                            db.add_summary(
                                room.id,
                                summary_date,
                                "daily",
                                summary_content
                            )
                            total_summaries += 1
                        except Exception:
                            pass  # Continue with other summaries

            self.progress.emit(100, "Recovery complete!")
            self.finished.emit(
                True,
                f"Recovery complete!\n\n"
                f"Rooms: {len(rooms)}\n"
                f"Messages: {total_messages:,}\n"
                f"Summaries: {total_summaries}"
            )

        except Exception as e:
            self.finished.emit(False, f"Recovery failed: {str(e)}")

        finally:
            # Dispose DB if it was created
            try:
                if 'db' in dir():
                    db.engine.dispose()
            except Exception:
                pass
