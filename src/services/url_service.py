"""URL management service for URL extraction and storage coordination."""

from typing import Dict, List, Optional
from datetime import date

from ..url_extractor import (
    extract_urls_from_text,
    normalize_url,
    deduplicate_urls,
    save_urls_to_file,
)
from ..file_storage import FileStorage
from ..repositories.chat_room_repository import ChatRoomRepository
from ..repositories.url_repository import URLRepository
from ..repositories.summary_repository import SummaryRepository


class URLService:
    """
    Service for URL extraction and management workflows.

    Orchestrates URL extraction from summaries, storage coordination,
    and URL list management.
    """

    def __init__(
        self,
        chat_room_repo: ChatRoomRepository,
        url_repo: URLRepository,
        summary_repo: SummaryRepository,
        file_storage: Optional[FileStorage] = None,
    ):
        """
        Initialize URLService with required repositories.

        Args:
            chat_room_repo: Repository for chat room operations.
            url_repo: Repository for URL operations.
            summary_repo: Repository for summary operations.
            file_storage: Optional FileStorage instance.
        """
        self.chat_room_repo = chat_room_repo
        self.url_repo = url_repo
        self.summary_repo = summary_repo
        self.file_storage = file_storage or FileStorage()

    def extract_urls_from_summary(
        self, room_id: int, summary_date: date
    ) -> Dict[str, List[str]]:
        """
        Extract URLs from a summary and store them.

        Args:
            room_id: Chat room ID.
            summary_date: Date of the summary.

        Returns:
            Dictionary mapping URLs to their descriptions.
        """
        # Get room
        room = self.chat_room_repo.get_by_id(room_id)
        if not room:
            return {}

        # Get summary
        summaries = self.summary_repo.get_summaries_by_room(
            room_id, summary_type="daily"
        )
        summary = next(
            (s for s in summaries if s.summary_date == summary_date), None
        )

        if not summary or not summary.content:
            return {}

        # Extract URLs from summary content
        urls = extract_urls_from_text(summary.content, section_only=False)

        if urls:
            # Normalize URLs
            normalized_urls = {}
            for url, descriptions in urls.items():
                normalized = normalize_url(url)
                normalized_urls[normalized] = descriptions

            # Deduplicate
            deduplicated = deduplicate_urls(normalized_urls)

            # Store in database
            if deduplicated:
                self.url_repo.add_urls_batch(room_id, deduplicated)

            # Store in file
            room_name = room.name
            self._save_url_lists_to_file(room_name, deduplicated)

        return urls

    def extract_urls_from_all_summaries(self, room_id: int) -> Dict[str, List[str]]:
        """
        Extract URLs from all summaries in a room.

        Args:
            room_id: Chat room ID.

        Returns:
            Dictionary mapping URLs to their descriptions.
        """
        # Get all summaries
        summaries = self.summary_repo.get_summaries_by_room(room_id)

        all_urls = {}

        for summary in summaries:
            urls = extract_urls_from_text(summary.content, section_only=False)

            # Merge URLs
            for url, descriptions in urls.items():
                normalized = normalize_url(url)
                if normalized not in all_urls:
                    all_urls[normalized] = []
                all_urls[normalized].extend(descriptions)

        # Deduplicate combined URLs
        if all_urls:
            deduplicated = deduplicate_urls(all_urls)

            # Store in database
            self.url_repo.clear_urls_by_room(room_id)
            self.url_repo.add_urls_batch(room_id, deduplicated)

            # Save to file
            room = self.chat_room_repo.get_by_id(room_id)
            if room:
                self._save_url_lists_to_file(room.name, deduplicated)

            return deduplicated

        return {}

    def get_urls_by_room(self, room_id: int) -> Dict[str, List[str]]:
        """
        Get all URLs for a chat room.

        Args:
            room_id: Chat room ID.

        Returns:
            Dictionary mapping URLs to their descriptions.
        """
        return self.url_repo.get_urls_by_room(room_id)

    def sync_urls_from_file(self, room_id: int) -> int:
        """
        Sync URLs from file storage to database.

        Args:
            room_id: Chat room ID.

        Returns:
            Number of URLs synced.
        """
        room = self.chat_room_repo.get_by_id(room_id)
        if not room:
            return 0

        # Load URLs from file
        room_name = room.name

        # Try to load from different list types
        urls_recent = self.file_storage.load_url_list(room_name, "recent")
        urls_weekly = self.file_storage.load_url_list(room_name, "weekly")
        urls_all = self.file_storage.load_url_list(room_name, "all")

        # Combine all URLs
        combined_urls = {}
        for url_dict in [urls_recent, urls_weekly, urls_all]:
            if url_dict:
                for url, descriptions in url_dict.items():
                    normalized = normalize_url(url)
                    if normalized not in combined_urls:
                        combined_urls[normalized] = []
                    combined_urls[normalized].extend(descriptions)

        # Deduplicate and store
        if combined_urls:
            deduplicated = deduplicate_urls(combined_urls)

            # Clear existing and add new
            self.url_repo.clear_urls_by_room(room_id)
            count = self.url_repo.add_urls_batch(room_id, deduplicated)

            return count

        return 0

    def _save_url_lists_to_file(
        self, room_name: str, urls: Dict[str, List[str]]
    ) -> None:
        """
        Save URL lists to file storage.

        Creates three files: recent, weekly, and all.

        Args:
            room_name: Chat room name.
            urls: Dictionary mapping URLs to descriptions.
        """
        # For simplicity, save the same URLs to all three files
        # In a more sophisticated implementation, we might filter by date
        url_dir = self.file_storage.url_dir / self.file_storage._sanitize_name(room_name)
        url_dir.mkdir(parents=True, exist_ok=True)

        # Save to all three list types
        save_urls_to_file(urls, url_dir / f"{room_name}_urls_recent.md")
        save_urls_to_file(urls, url_dir / f"{room_name}_urls_weekly.md")
        save_urls_to_file(urls, url_dir / f"{room_name}_urls_all.md")

    def get_url_count(self, room_id: int) -> int:
        """
        Get total URL count for a room.

        Args:
            room_id: Chat room ID.

        Returns:
            Number of unique URLs.
        """
        return self.url_repo.get_count_by_room(room_id)
