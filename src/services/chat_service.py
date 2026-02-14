"""Chat processing service for coordinating chat data workflows."""

from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import date

from ..parser import KakaoLogParser
from ..chat_processor import ChatProcessor
from ..file_storage import FileStorage
from ..repositories.chat_room_repository import ChatRoomRepository
from ..repositories.message_repository import MessageRepository
from ..repositories.sync_log_repository import SyncLogRepository


class ChatService:
    """
    Service for chat processing workflows.

    Orchestrates chat file parsing, storage, and database operations.
    Uses repositories for data access and coordinates between parser,
    processor, and storage components.
    """

    def __init__(
        self,
        chat_room_repo: ChatRoomRepository,
        message_repo: MessageRepository,
        sync_log_repo: SyncLogRepository,
        file_storage: Optional[FileStorage] = None,
    ):
        """
        Initialize ChatService with required repositories.

        Args:
            chat_room_repo: Repository for chat room operations.
            message_repo: Repository for message operations.
            sync_log_repo: Repository for sync log operations.
            file_storage: Optional FileStorage instance (created if not provided).
        """
        self.chat_room_repo = chat_room_repo
        self.message_repo = message_repo
        self.sync_log_repo = sync_log_repo
        self.file_storage = file_storage or FileStorage()
        self.parser = KakaoLogParser()
        self.processor = ChatProcessor()

    def upload_and_parse_chat_file(
        self,
        room_name: str,
        file_path: str,
    ) -> Dict[str, Any]:
        """
        Upload and parse a chat file.

        This method orchestrates the complete workflow:
        1. Parse the chat file
        2. Create or get chat room
        3. Store parsed messages in database
        4. Store original file
        5. Record sync log

        Args:
            room_name: Name of the chat room.
            file_path: Path to the chat file.

        Returns:
            Dictionary with upload results:
                - success: bool
                - room_id: int
                - message_count: int
                - new_message_count: int
                - error: str or None
        """
        try:
            # Parse the chat file
            file_path_obj = Path(file_path)
            if not file_path_obj.exists():
                return {
                    "success": False,
                    "error": f"File not found: {file_path}",
                    "room_id": None,
                    "message_count": 0,
                    "new_message_count": 0,
                }

            parse_result = self.parser.parse(file_path_obj)

            # Get or create chat room
            room = self.chat_room_repo.get_by_name(room_name)
            if room is None:
                room = self.chat_room_repo.create(
                    name=room_name,
                    file_path=str(file_path_obj)
                )

            # Process parsed messages and add to database
            total_messages = 0
            new_messages = 0

            for date_str, message_lines in parse_result.messages_by_date.items():
                # Convert date string to date object
                try:
                    msg_date = self._parse_date_string(date_str)
                except ValueError:
                    continue

                # Parse individual messages from lines
                messages_data = self._extract_message_data(
                    message_lines, msg_date
                )

                if messages_data:
                    # Add to database
                    added_count = self.message_repo.add_messages(
                        room.id, messages_data
                    )
                    total_messages += len(messages_data)
                    new_messages += added_count

                # Store original file
                self.file_storage.save_daily_original(
                    room_name, date_str, message_lines
                )

            # Update sync time
            self.chat_room_repo.update_sync_time(room.id)

            # Record sync log
            self.sync_log_repo.create(
                room_id=room.id,
                status="success",
                message_count=total_messages,
                new_message_count=new_messages,
                error_message=None,
            )

            return {
                "success": True,
                "room_id": room.id,
                "message_count": total_messages,
                "new_message_count": new_messages,
                "error": None,
            }

        except Exception as e:
            # Log error and return failure
            if room and room.id:
                self.sync_log_repo.create(
                    room_id=room.id,
                    status="failed",
                    message_count=0,
                    new_message_count=0,
                    error_message=str(e),
                )

            return {
                "success": False,
                "error": str(e),
                "room_id": room.id if room else None,
                "message_count": 0,
                "new_message_count": 0,
            }

    def _parse_date_string(self, date_str: str) -> date:
        """
        Parse date string from parser to date object.

        Args:
            date_str: Date string in YYYY-MM-DD format.

        Returns:
            date object.

        Raises:
            ValueError: If date string is invalid.
        """
        year, month, day = map(int, date_str.split("-"))
        return date(year, month, day)

    def _extract_message_data(
        self, message_lines: List[str], message_date: date
    ) -> List[Dict[str, Any]]:
        """
        Extract message data from raw message lines.

        Args:
            message_lines: List of raw message lines.
            message_date: Date of the messages.

        Returns:
            List of message data dictionaries for database insertion.
        """
        messages = []

        for line in message_lines:
            # Parse message line format
            # Expected: --------------- [시간] 닉네임: 내용
            if not line.strip() or not line.startswith("---------------"):
                continue

            # Extract sender and content
            try:
                # Remove dashes and brackets
                content_part = line.split("]", 1)[1].strip(" ")
                sender_part, message_content = content_part.split(":", 1)

                sender = sender_part.strip()
                content = message_content.strip()

                if sender and content:
                    messages.append({
                        "sender": sender,
                        "content": content,
                        "date": message_date,
                        "time": None,  # Time not extracted in current format
                    })
            except (ValueError, IndexError):
                # Skip malformed lines
                continue

        return messages

    def get_room_statistics(self, room_id: int) -> Dict[str, Any]:
        """
        Get comprehensive statistics for a chat room.

        Args:
            room_id: Chat room ID.

        Returns:
            Dictionary with room statistics.
        """
        room = self.chat_room_repo.get_by_id(room_id)
        if not room:
            return {}

        stats = self.chat_room_repo.get_stats(room_id)

        # Add unique senders
        unique_senders = self.message_repo.get_unique_senders(room_id)
        stats["unique_senders_list"] = unique_senders

        return stats

    def sync_room_from_file(
        self, room_id: int, file_path: str
    ) -> Dict[str, Any]:
        """
        Sync chat room data from file.

        Similar to upload_and_parse_chat_file but for existing rooms.

        Args:
            room_id: Existing chat room ID.
            file_path: Path to the chat file.

        Returns:
            Dictionary with sync results.
        """
        room = self.chat_room_repo.get_by_id(room_id)
        if not room:
            return {
                "success": False,
                "error": f"Room not found: {room_id}",
                "message_count": 0,
                "new_message_count": 0,
            }

        return self.upload_and_parse_chat_file(room.name, file_path)
