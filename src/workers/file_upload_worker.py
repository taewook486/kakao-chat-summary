"""File upload and parsing worker.

Handles:
- Chat file parsing
- Daily file storage
- Database message storage
- Summary invalidation
"""
import re
from datetime import datetime, date, time as dt_time
from pathlib import Path
from typing import Optional, Dict, Any, List

from PySide6.QtCore import Signal

from .base import BaseWorker


class MessageParser:
    """KakaoTalk message parser.

    Parses message lines in format: [nickname] [AM/PM HH:MM] content
    """

    # Pattern: [nickname] [AM/PM time] content
    MSG_PATTERN = re.compile(
        r'\[(.*?)\]\s*\[(오전|오후)\s*(\d{1,2}):(\d{2})\]\s*(.*)',
        re.DOTALL
    )

    @classmethod
    def parse_message(cls, line: str, msg_date: date) -> Optional[Dict[str, Any]]:
        """Parse a message line.

        Args:
            line: Raw message line from chat log.
            msg_date: Date of the message.

        Returns:
            Parsed message dict or None if line doesn't match pattern.
        """
        match = cls.MSG_PATTERN.match(line)
        if not match:
            return None

        sender = match.group(1)
        am_pm = match.group(2)
        hour = int(match.group(3))
        minute = int(match.group(4))
        content = match.group(5)

        # Convert to 24-hour format
        if am_pm == "오후" and hour != 12:
            hour += 12
        elif am_pm == "오전" and hour == 12:
            hour = 0

        msg_time = dt_time(hour, minute)

        return {
            'sender': sender,
            'content': content,
            'date': msg_date,
            'time': msg_time,
            'raw_line': line
        }


class FileUploadWorker(BaseWorker):
    """Worker for uploading and parsing chat files.

    Thread Safety:
        Creates its own Database instance in run() - never shares DB.

    Signals:
        progress: (int, str) - Progress percentage and status message
        finished: (bool, str, int) - Success, message, room_id
    """

    # Override finished signal to include room_id
    finished = Signal(bool, str, int)  # (success, message, room_id)

    def __init__(
        self,
        file_path: str,
        room_name: Optional[str] = None,
        parent=None
    ):
        """Initialize file upload worker.

        Args:
            file_path: Path to the chat file to upload.
            room_name: Optional room name (extracted from file if not provided).
            parent: Optional parent QObject.
        """
        super().__init__(parent)
        self.file_path = Path(file_path)
        self.room_name = room_name
        self.storage = None  # Initialized in run()

    def run(self) -> None:
        """Execute file upload and parsing.

        Steps:
        1. Extract room name from file or use provided name
        2. Create or get chat room
        3. Parse chat file
        4. Save daily files to storage
        5. Invalidate changed summaries
        6. Save messages to database
        7. Update sync log
        """
        # Import here to avoid circular imports and ensure thread-local instance
        from file_storage import get_storage
        from parser import KakaoLogParser

        # Initialize storage (thread-safe - uses Path operations)
        self.storage = get_storage()

        # Create thread-local DB instance
        worker_db = self._create_worker_db()

        try:
            self.progress.emit(10, "Reading file...")

            # 1. Extract room name
            room_name = self.room_name or self._extract_room_name()

            # 2. Get or create room
            self.progress.emit(20, "Creating chat room...")
            room = self._get_or_create_room(room_name, worker_db)

            # 3. Parse file
            self.progress.emit(30, "Parsing conversation...")
            parser = KakaoLogParser()
            parse_result = parser.parse(self.file_path)

            # 4. Get old file sizes for invalidation check
            self.progress.emit(35, "Checking existing data...")
            old_file_sizes = {}
            for date_str in parse_result.messages_by_date.keys():
                old_file_sizes[date_str] = self.storage.get_original_file_size(
                    room_name, date_str
                )

            # 5. Save daily files
            self.progress.emit(40, "Saving daily files...")
            saved_files = self.storage.save_all_daily_originals(
                room_name,
                parse_result.messages_by_date
            )

            # 6. Invalidate summaries for changed files
            self.progress.emit(50, "Checking summary status...")
            invalidated_dates = []
            for date_str in parse_result.messages_by_date.keys():
                old_size = old_file_sizes.get(date_str, 0)
                new_size = self.storage.get_original_file_size(room_name, date_str)

                if self.storage.invalidate_summary_if_file_changed(
                    room_name, date_str, old_size, new_size
                ):
                    invalidated_dates.append(date_str)

            # 7. Extract and save messages to DB
            self.progress.emit(60, "Saving to database...")
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
                    try:
                        new_count = worker_db.add_messages(room.id, messages)
                        new_messages += new_count
                    except Exception:
                        # File is already saved, DB error is non-fatal
                        pass

            # 8. Update sync time
            self.progress.emit(90, "Finalizing...")
            try:
                worker_db.update_room_sync_time(room.id)
                worker_db.add_sync_log(
                    room.id, 'success',
                    message_count=total_messages,
                    new_message_count=new_messages
                )
            except Exception:
                pass  # Non-fatal DB error

            self.progress.emit(100, "Complete!")

            # Build result message
            result_msg = (
                f"File: {room_name}\n"
                f"Days saved: {len(saved_files)}\n"
                f"Total messages: {total_messages:,}"
            )
            if invalidated_dates:
                result_msg += f"\nSummaries needing update: {len(invalidated_dates)}"

            self.finished.emit(True, result_msg, room.id if room else -1)

        except Exception as e:
            self.finished.emit(False, f"Error: {str(e)}", -1)

        finally:
            self._dispose_db(worker_db)

    def _extract_room_name(self) -> str:
        """Extract room name from file path.

        Returns:
            Extracted room name or default name.
        """
        name = self.file_path.stem
        # Extract from KakaoTalk_20260131_1416_15_783_group format
        if "_KakaoTalk_" in name:
            return name.split("_KakaoTalk_")[0]
        elif "KakaoTalk_" in name:
            return "KakaoTalk Chat"
        return name

    def _get_or_create_room(self, name: str, db):
        """Get existing room or create new one.

        Args:
            name: Room name.
            db: Database instance.

        Returns:
            ChatRoom instance.
        """
        from db import ChatRoom

        room = db.get_room_by_name(name)
        if room is None:
            room = db.create_room(name, str(self.file_path))
        return room
