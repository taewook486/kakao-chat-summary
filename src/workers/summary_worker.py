"""Summary generation worker.

Handles:
- Loading chat data from storage
- LLM-based summary generation
- Summary file and database storage
- Cancellation support
"""
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict

from PySide6.QtCore import Signal

from .base import BaseWorker


class SummaryWorker(BaseWorker):
    """Worker for generating chat summaries using LLM.

    Thread Safety:
        Creates its own Database instance in run() - never shares DB.

    Signals:
        progress: (int, str) - Progress percentage and status message
        finished: (bool, str) - Success and combined summary or error
    """

    # Use base class signals
    finished = Signal(bool, str)

    def __init__(
        self,
        room_id: int,
        summary_type: str,
        file_path: Optional[str] = None,
        room_name: Optional[str] = None,
        skip_existing: bool = True,
        llm_provider: str = "glm",
        parent=None
    ):
        """Initialize summary worker.

        Args:
            room_id: ID of the chat room.
            summary_type: Type of summary ('today', 'yesterday', '2days', 'all', 'pending').
            file_path: Optional path to source chat file.
            room_name: Name of the chat room.
            skip_existing: Whether to skip already summarized dates.
            llm_provider: LLM provider to use ('glm', 'openai', etc.).
            parent: Optional parent QObject.
        """
        super().__init__(parent)
        self.room_id = room_id
        self.summary_type = summary_type
        self.file_path = file_path
        self.room_name = room_name or "Unknown"
        self.skip_existing = skip_existing
        self.llm_provider = llm_provider
        self.storage = None  # Initialized in run()

    def run(self) -> None:
        """Execute summary generation.

        Steps:
        1. Load messages from storage or file
        2. Determine which dates need summarization
        3. Generate summaries using LLM
        4. Save summaries to storage and database
        """
        from pathlib import Path as PathLib
        import sys

        # Add src to path for imports
        sys.path.insert(0, str(PathLib(__file__).parent.parent))

        from file_storage import get_storage
        from chat_processor import ChatProcessor
        from full_config import config

        # Initialize storage
        self.storage = get_storage()

        try:
            self.progress.emit(10, "Loading data...")

            # Load messages from storage (priority) or file
            messages_by_date = self.storage.load_all_originals(self.room_name)

            # Fallback to file parsing if storage is empty
            if not messages_by_date and self.file_path and Path(self.file_path).exists():
                from parser import KakaoLogParser
                parser = KakaoLogParser()
                parse_result = parser.parse(Path(self.file_path))
                messages_by_date = parse_result.messages_by_date

            if not messages_by_date:
                self.finished.emit(False, "No chat data available.")
                return

            # Determine dates to process
            dates_to_process, skipped_count = self._get_dates_to_process(
                messages_by_date
            )

            if not dates_to_process:
                summarized_count = len(self.storage.get_summarized_dates(self.room_name))
                self.finished.emit(
                    True,
                    f"All dates already summarized. (Total: {summarized_count} days)"
                )
                return

            # Configure LLM
            config.set_provider(self.llm_provider)
            llm_provider_info = config.get_provider_info()

            self.progress.emit(
                20,
                f"Summarizing with {llm_provider_info.name}... "
                f"({len(dates_to_process)} days, {skipped_count} skipped)"
            )

            # Generate summaries
            processor = ChatProcessor()
            llm_name = llm_provider_info.name
            all_summaries: List[str] = []
            success_count = 0
            fail_count = 0

            for i, date_str in enumerate(sorted(dates_to_process)):
                # Check for cancellation
                if self.is_cancelled():
                    self.progress.emit(100, "Cancelled")
                    status_msg = (
                        f"Cancelled (Complete: {success_count} / "
                        f"Cancelled: {len(dates_to_process) - i})"
                    )
                    if all_summaries:
                        combined = self._combine_summaries(status_msg, all_summaries)
                        self.finished.emit(True, combined)
                    else:
                        self.finished.emit(True, status_msg)
                    return

                progress = 20 + int((i + 1) / len(dates_to_process) * 70)
                self.progress.emit(
                    progress,
                    f"Summarizing {date_str}... ({i+1}/{len(dates_to_process)})"
                )

                messages = messages_by_date.get(date_str, [])
                if not messages:
                    fail_count += 1
                    continue

                chat_content = "\n".join(messages)
                summary = processor.process_summary(chat_content)

                if "[ERROR]" not in summary:
                    # Save to file storage
                    self.storage.save_daily_summary(
                        self.room_name, date_str, summary, llm_name
                    )

                    # Save to database with thread-local DB
                    self._save_summary_to_db(date_str, summary, llm_name)

                    all_summaries.append(f"## Date: {date_str}\n\n{summary}")
                    success_count += 1
                else:
                    fail_count += 1

            self.progress.emit(100, "Complete!")

            # Build result message
            status_msg = f"Summarized: {success_count} days"
            if skipped_count > 0:
                status_msg += f" | Skipped: {skipped_count}"
            if fail_count > 0:
                status_msg += f" | Failed: {fail_count}"

            if all_summaries:
                combined = self._combine_summaries(status_msg, all_summaries)
                self.finished.emit(True, combined)
            else:
                self.finished.emit(True, status_msg)

        except Exception as e:
            self.finished.emit(False, f"Error: {str(e)}")

    def _get_dates_to_process(
        self,
        messages_by_date: Dict[str, List[str]]
    ) -> tuple[List[str], int]:
        """Determine which dates need summarization.

        Args:
            messages_by_date: All available messages by date.

        Returns:
            Tuple of (dates_to_process, skipped_count).
        """
        if self.summary_type == "pending":
            # Only dates needing summary (new + needs_update)
            dates_needing = self.storage.get_dates_needing_summary(self.room_name)
            dates_to_process = list(dates_needing.keys())

            if not dates_to_process:
                return [], 0

            skipped_count = len(messages_by_date) - len(dates_to_process)
            return dates_to_process, skipped_count

        # Calculate date range for other types
        today = datetime.now().strftime("%Y-%m-%d")
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        day_before = (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d")

        if self.summary_type == "today":
            start_date = today
        elif self.summary_type == "yesterday":
            start_date = yesterday
        elif self.summary_type == "2days":
            start_date = day_before
        else:  # all
            start_date = None

        # Filter by date range
        if start_date:
            target_dates = [d for d in messages_by_date.keys() if d >= start_date]
        else:
            target_dates = list(messages_by_date.keys())

        if not target_dates:
            return [], 0

        # Check existing summaries
        summarized = set(self.storage.get_summarized_dates(self.room_name))

        if self.skip_existing:
            dates_to_process = [d for d in target_dates if d not in summarized]
            skipped_count = len(target_dates) - len(dates_to_process)
        else:
            dates_to_process = target_dates
            skipped_count = 0

        return dates_to_process, skipped_count

    def _save_summary_to_db(
        self,
        date_str: str,
        summary: str,
        llm_name: str
    ) -> None:
        """Save summary to database.

        Creates a thread-local DB instance for safety.

        Args:
            date_str: Date string (YYYY-MM-DD).
            summary: Summary content.
            llm_name: Name of LLM provider.
        """
        worker_db = self._create_worker_db()
        try:
            summary_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            worker_db.delete_summary(self.room_id, summary_date)
            worker_db.add_summary(
                self.room_id, summary_date, "daily", summary, llm_name
            )
        except Exception:
            pass  # File save succeeded, DB failure is non-fatal
        finally:
            self._dispose_db(worker_db)

    def _combine_summaries(
        self,
        status_msg: str,
        summaries: List[str]
    ) -> str:
        """Combine status message with summaries.

        Args:
            status_msg: Status message.
            summaries: List of summary strings.

        Returns:
            Combined summary string.
        """
        return f"{status_msg}\n\n---\n\n" + "\n\n---\n\n".join(summaries)
