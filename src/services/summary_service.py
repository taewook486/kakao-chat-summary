"""Summary generation service for LLM orchestration."""

from typing import List, Dict, Any, Optional
from datetime import date, timedelta
from pathlib import Path

from ..llm_client import LLMClient
from ..chat_processor import ChatProcessor
from ..file_storage import FileStorage
from ..repositories.chat_room_repository import ChatRoomRepository
from ..repositories.message_repository import MessageRepository
from ..repositories.summary_repository import SummaryRepository
from ..repositories.sync_log_repository import SyncLogRepository


class SummaryService:
    """
    Service for LLM summary generation workflows.

    Orchestrates summary generation, storage, and retrieval.
    Coordinates between LLM client, chat processor, and storage.
    """

    def __init__(
        self,
        chat_room_repo: ChatRoomRepository,
        message_repo: MessageRepository,
        summary_repo: SummaryRepository,
        sync_log_repo: SyncLogRepository,
        file_storage: Optional[FileStorage] = None,
    ):
        """
        Initialize SummaryService with required repositories.

        Args:
            chat_room_repo: Repository for chat room operations.
            message_repo: Repository for message operations.
            summary_repo: Repository for summary operations.
            sync_log_repo: Repository for sync log operations.
            file_storage: Optional FileStorage instance.
        """
        self.chat_room_repo = chat_room_repo
        self.message_repo = message_repo
        self.summary_repo = summary_repo
        self.sync_log_repo = sync_log_repo
        self.file_storage = file_storage or FileStorage()
        self.processor = ChatProcessor()

    def generate_summary_for_date(
        self,
        room_id: int,
        target_date: date,
        llm_provider: str = "glm",
        skip_existing: bool = True,
    ) -> Dict[str, Any]:
        """
        Generate LLM summary for a specific date.

        Args:
            room_id: Chat room ID.
            target_date: Date to generate summary for.
            llm_provider: LLM provider to use (glm, chatgpt, etc.).
            skip_existing: If True, skip if summary already exists.

        Returns:
            Dictionary with generation results:
                - success: bool
                - summary_id: int or None
                - content: str or None
                - error: str or None
        """
        try:
            # Check if summary already exists
            if skip_existing:
                existing_summaries = self.summary_repo.get_summaries_by_room(
                    room_id, summary_type="daily"
                )
                for summary in existing_summaries:
                    if summary.summary_date == target_date:
                        return {
                            "success": True,
                            "summary_id": summary.id,
                            "content": summary.content,
                            "error": None,
                            "skipped": True,
                        }

            # Get room
            room = self.chat_room_repo.get_by_id(room_id)
            if not room:
                return {
                    "success": False,
                    "summary_id": None,
                    "content": None,
                    "error": f"Room not found: {room_id}",
                }

            # Get messages for the date
            messages = self.message_repo.get_messages_by_room(
                room_id, start_date=target_date, end_date=target_date
            )

            if not messages:
                return {
                    "success": False,
                    "summary_id": None,
                    "content": None,
                    "error": f"No messages found for date: {target_date}",
                }

            # Format messages for LLM
            chat_text = self._format_messages_for_llm(messages, room.name, target_date)

            # Call LLM
            llm_client = LLMClient(provider=llm_provider)
            llm_result = llm_client.summarize(chat_text)

            if not llm_result["success"]:
                return {
                    "success": False,
                    "summary_id": None,
                    "content": None,
                    "error": llm_result.get("error", "Unknown LLM error"),
                }

            summary_content = llm_result["content"]

            # Validate summary content
            validation = self._validate_summary_content(summary_content)
            if not validation["valid"]:
                return {
                    "success": False,
                    "summary_id": None,
                    "content": None,
                    "error": f"Summary validation failed: {validation['reason']}",
                }

            # Save to database
            summary = self.summary_repo.create(
                room_id=room_id,
                summary_date=target_date,
                summary_type="daily",
                content=summary_content,
                llm_provider=llm_provider,
            )

            # Save to file
            date_str = target_date.strftime("%Y-%m-%d")
            self.file_storage.save_daily_summary(
                room.name, date_str, summary_content, llm_provider
            )

            return {
                "success": True,
                "summary_id": summary.id,
                "content": summary_content,
                "error": None,
                "skipped": False,
            }

        except Exception as e:
            return {
                "success": False,
                "summary_id": None,
                "content": None,
                "error": str(e),
            }

    def generate_summaries_for_date_range(
        self,
        room_id: int,
        start_date: date,
        end_date: date,
        llm_provider: str = "glm",
        skip_existing: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Generate summaries for a date range.

        Args:
            room_id: Chat room ID.
            start_date: Start date (inclusive).
            end_date: End date (inclusive).
            llm_provider: LLM provider to use.
            skip_existing: If True, skip dates with existing summaries.

        Returns:
            List of generation result dictionaries.
        """
        results = []
        current_date = start_date

        while current_date <= end_date:
            result = self.generate_summary_for_date(
                room_id, current_date, llm_provider, skip_existing
            )
            results.append({
                "date": current_date.isoformat(),
                **result,
            })
            current_date += timedelta(days=1)

        return results

    def _format_messages_for_llm(
        self, messages: List, room_name: str, target_date: date
    ) -> str:
        """
        Format messages for LLM input.

        Args:
            messages: List of Message objects.
            room_name: Chat room name.
            target_date: Date of messages.

        Returns:
            Formatted text for LLM.
        """
        # Convert Message objects to dict format for processor
        message_dicts = []
        for msg in messages:
            message_dicts.append({
                "sender": msg.sender,
                "content": msg.content,
                "date": msg.message_date,
                "time": msg.message_time,
            })

        # Use chat processor to format
        return self.processor.process_chat(
            message_dicts, room_name, target_date
        )

    def _validate_summary_content(self, content: str) -> Dict[str, Any]:
        """
        Validate generated summary content.

        Args:
            content: Summary content to validate.

        Returns:
            Dictionary with validation results:
                - valid: bool
                - reason: str or None
        """
        if not content or not content.strip():
            return {
                "valid": False,
                "reason": "Empty summary content",
            }

        # Check minimum length
        if len(content.strip()) < 50:
            return {
                "valid": False,
                "reason": "Summary too short (minimum 50 characters)",
            }

        # Check for truncation patterns
        truncation_patterns = ["...", "[truncated", "[incomplete"]
        for pattern in truncation_patterns:
            if pattern.lower() in content.lower():
                return {
                    "valid": False,
                    "reason": f"Summary appears truncated (contains '{pattern}')",
                }

        return {
            "valid": True,
            "reason": None,
        }

    def get_summaries_by_room(
        self, room_id: int, summary_type: Optional[str] = None
    ) -> List:
        """
        Get summaries for a chat room.

        Args:
            room_id: Chat room ID.
            summary_type: Optional filter by summary type.

        Returns:
            List of Summary objects.
        """
        return self.summary_repo.get_summaries_by_room(room_id, summary_type)

    def get_dates_needing_summary(
        self, room_id: int, summary_type: str = "daily"
    ) -> List[date]:
        """
        Get dates that need summary generation.

        Args:
            room_id: Chat room ID.
            summary_type: Type of summary to check for.

        Returns:
            List of dates needing summaries.
        """
        # Get all dates with messages
        messages = self.message_repo.get_messages_by_room(room_id)
        message_dates = set(msg.message_date for msg in messages)

        # Get existing summary dates
        existing_summaries = self.summary_repo.get_summaries_by_room(
            room_id, summary_type=summary_type
        )
        summary_dates = set(summary.summary_date for summary in existing_summaries)

        # Find dates needing summaries
        needed_dates = message_dates - summary_dates

        return sorted(needed_dates)
