"""File service for file upload, parsing, and storage abstraction."""

from typing import List, Dict, Any, Optional
from pathlib import Path

from ..parser import KakaoLogParser
from ..file_storage import FileStorage
from ..repositories.chat_room_repository import ChatRoomRepository


class FileService:
    """
    Service for file operations abstraction.

    Provides high-level file operations for chat file handling,
    abstracting the details of parsing and storage.
    """

    def __init__(
        self,
        chat_room_repo: ChatRoomRepository,
        file_storage: Optional[FileStorage] = None,
    ):
        """
        Initialize FileService with required dependencies.

        Args:
            chat_room_repo: Repository for chat room operations.
            file_storage: Optional FileStorage instance.
        """
        self.chat_room_repo = chat_room_repo
        self.file_storage = file_storage or FileStorage()
        self.parser = KakaoLogParser()

    def validate_chat_file(self, file_path: str) -> Dict[str, Any]:
        """
        Validate if a file is a valid KakaoTalk chat file.

        Args:
            file_path: Path to the file.

        Returns:
            Dictionary with validation results:
                - valid: bool
                - reason: str or None
                - date_count: int (number of dates found)
        """
        try:
            file_path_obj = Path(file_path)

            if not file_path_obj.exists():
                return {
                    "valid": False,
                    "reason": "File does not exist",
                    "date_count": 0,
                }

            # Try to parse the file
            parse_result = self.parser.parse(file_path_obj)

            if parse_result.total_dates == 0:
                return {
                    "valid": False,
                    "reason": "No valid date headers found in file",
                    "date_count": 0,
                }

            return {
                "valid": True,
                "reason": None,
                "date_count": parse_result.total_dates,
            }

        except Exception as e:
            return {
                "valid": False,
                "reason": f"Error parsing file: {str(e)}",
                "date_count": 0,
            }

    def get_available_dates_for_room(self, room_name: str) -> List[str]:
        """
        Get list of dates with stored chat data for a room.

        Args:
            room_name: Chat room name.

        Returns:
            List of date strings (YYYY-MM-DD format).
        """
        return self.file_storage.get_available_dates(room_name)

    def get_chat_content_for_date(
        self, room_name: str, date_str: str
    ) -> Optional[List[str]]:
        """
        Get stored chat content for a specific date.

        Args:
            room_name: Chat room name.
            date_str: Date string (YYYY-MM-DD format).

        Returns:
            List of chat message lines, or None if not found.
        """
        return self.file_storage.load_daily_original(room_name, date_str)

    def get_summary_content_for_date(
        self, room_name: str, date_str: str
    ) -> Optional[str]:
        """
        Get stored summary content for a specific date.

        Args:
            room_name: Chat room name.
            date_str: Date string (YYYY-MM-DD format).

        Returns:
            Summary content string, or None if not found.
        """
        return self.file_storage.load_daily_summary(room_name, date_str)

    def check_summary_exists(self, room_name: str, date_str: str) -> bool:
        """
        Check if a summary exists for a room and date.

        Args:
            room_name: Chat room name.
            date_str: Date string (YYYY-MM-DD format).

        Returns:
            True if summary exists, False otherwise.
        """
        summarized_dates = self.file_storage.get_summarized_dates(room_name)
        return date_str in summarized_dates

    def get_dates_needing_summary(self, room_name: str) -> Dict[str, str]:
        """
        Get dates that have chat data but no summary.

        Args:
            room_name: Chat room name.

        Returns:
            Dictionary mapping date strings to status strings.
        """
        return self.file_storage.get_dates_needing_summary(room_name)

    def delete_summary(self, room_name: str, date_str: str) -> bool:
        """
        Delete a summary file.

        Args:
            room_name: Chat room name.
            date_str: Date string (YYYY-MM-DD format).

        Returns:
            True if deleted, False otherwise.
        """
        return self.file_storage.delete_daily_summary(room_name, date_str)

    def get_file_size_info(
        self, room_name: str, date_str: str
    ) -> Dict[str, int]:
        """
        Get file size information for room data.

        Args:
            room_name: Chat room name.
            date_str: Date string (YYYY-MM-DD format).

        Returns:
            Dictionary with size info:
                - original_size: int (bytes)
                - summary_size: int (bytes)
                - total_size: int (bytes)
        """
        original_size = self.file_storage.get_original_file_size(
            room_name, date_str
        )
        summary_size = self.file_storage.get_summary_file_size(
            room_name, date_str
        )

        return {
            "original_size": original_size,
            "summary_size": summary_size,
            "total_size": original_size + summary_size,
        }
