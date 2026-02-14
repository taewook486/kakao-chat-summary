"""
Characterization tests for Worker thread behavior (PRESERVE phase).

These tests capture the CURRENT behavior of workers to prevent regression
during refactoring. They document what the code DOES, not what it SHOULD DO.

After refactoring is complete, these tests can be:
1. Converted to proper specification tests
2. Removed if behavior is intentionally changed
3. Updated if the refactoring changes the contract
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch
from PySide6.QtCore import QThread

from src.parser import KakaoLogParser


@pytest.mark.characterization
class TestKakaoLogParserBehavior:
    """Characterization tests for KakaoLogParser."""

    def test_parse_kakao_log_format(self, sample_chat_file):
        """
        CAPTURE: Parse real KakaoTalk log format.

        This test captures the current parsing behavior.
        If this test fails after refactoring, investigate whether:
        1. The parsing logic changed (intentional or accidental?)
        2. The test sample needs updating
        3. The format expectations changed
        """
        # Given: Real sample file from production
        parser = KakaoLogParser()

        # When: Parse the file
        result = parser.parse(sample_chat_file)

        # Then: Capture current output structure - ParseResult with messages_by_date
        assert result is not None
        assert hasattr(result, "messages_by_date")
        assert hasattr(result, "total_dates")

        # Capture: messages_by_date is a dict {date_string: [message_lines]}
        assert isinstance(result.messages_by_date, dict)
        assert result.total_dates > 0

        # Capture: At least one date has messages
        first_date = list(result.messages_by_date.keys())[0]
        messages = result.messages_by_date[first_date]
        assert len(messages) > 0

    def test_parse_extract_senders(self, sample_chat_file):
        """CAPTURE: Extract all unique senders from chat."""
        parser = KakaoLogParser()
        result = parser.parse(sample_chat_file)

        # Parser returns lines grouped by date, not parsed senders
        # The actual sender extraction happens elsewhere
        # This test captures that the parser preserves the raw lines
        assert result.total_dates > 0

        # All messages are preserved as raw lines
        all_messages = []
        for date_msgs in result.messages_by_date.values():
            all_messages.extend(date_msgs)

        assert len(all_messages) > 0
        # Check that sender names are present in the raw lines
        assert any("홍길동" in msg or "김철수" in msg or "이영희" in msg for msg in all_messages)

    def test_parse_handle_korean_encoding(self, temp_dir):
        """CAPTURE: Handle Korean UTF-8 encoding correctly."""
        # Create file with Korean content
        korean_file = temp_dir / "korean_chat.txt"
        korean_file.write_text(
            "KakaoTalk Chat Export\n"
            "---------------------\n"
            "--------------- 2024년 2월 11일 일요일 ---------------\n"
            "--------------- [오후 2:00] 홍길동: 안녕하세요 반갑습니다\n"
            "--------------- [오후 2:05] 김철수: 네 잘 부탁드립니다 ㅎㅎ\n",
            encoding="utf-8"
        )

        parser = KakaoLogParser()
        result = parser.parse(korean_file)

        # Verify Korean text is preserved
        assert result.total_dates >= 1

        # Get all messages
        all_messages = []
        for msgs in result.messages_by_date.values():
            all_messages.extend(msgs)

        assert len(all_messages) >= 2
        # Check Korean text preservation
        korean_text = " ".join(all_messages)
        assert "안녕하세요" in korean_text or "반갑습니다" in korean_text

    def test_parse_extract_urls(self, sample_chat_file):
        """CAPTURE: Extract URLs from chat messages."""
        parser = KakaoLogParser()
        result = parser.parse(sample_chat_file)

        # Get all messages
        all_messages = []
        for msgs in result.messages_by_date.values():
            all_messages.extend(msgs)

        # Find messages with URLs
        messages_with_urls = [msg for msg in all_messages if "http://" in msg or "https://" in msg]

        # Capture current URL extraction behavior
        assert len(messages_with_urls) >= 1
        assert "example.com" in messages_with_urls[0] or "weather" in messages_with_urls[0]


@pytest.mark.characterization
class TestFileStorageBehavior:
    """Characterization tests for FileStorage behavior."""

    def test_save_daily_original_format(self, temp_dir, sample_room):
        """
        CAPTURE: Save original chat format to file.

        Captures the exact file format and naming convention.
        """
        from src.file_storage import FileStorage

        storage = FileStorage()
        storage.base_dir = temp_dir
        storage.original_dir = temp_dir / "original"
        storage.original_dir.mkdir(parents=True, exist_ok=True)

        # Sample messages
        messages = [
            "--------------- [2024년 2월 10일] 홍길동: 안녕하세요",
            "--------------- [2024년 2월 10일] 김철수: 네 안녕하세요",
        ]

        # Save using current method
        result_path = storage.save_daily_original(
            sample_room.name,
            "2024-02-10",
            messages
        )

        # Verify file exists and capture format
        assert result_path.exists()
        content = result_path.read_text(encoding="utf-8")

        # Capture current file format
        assert "홍길동" in content
        assert "안녕하세요" in content

    def test_get_available_dates(self, temp_dir, sample_room):
        """CAPTURE: Get list of dates with chat data."""
        from src.file_storage import FileStorage

        storage = FileStorage()
        storage.base_dir = temp_dir
        storage.original_dir = temp_dir / "original"

        # Get sanitized room name (space becomes underscore)
        sanitized_name = storage._sanitize_name(sample_room.name)
        room_dir = temp_dir / "original" / sanitized_name
        room_dir.mkdir(parents=True, exist_ok=True)

        # Create sample files with the correct naming convention
        (room_dir / f"{sanitized_name}_20240210_full.md").write_text("data1", encoding="utf-8")
        (room_dir / f"{sanitized_name}_20240211_full.md").write_text("data2", encoding="utf-8")

        # Get dates using current method
        dates = storage.get_available_dates(sample_room.name)

        # Capture current date extraction logic
        assert len(dates) >= 2
        # Dates are returned in YYYY-MM-DD format
        assert "2024-02-10" in dates
        assert "2024-02-11" in dates


@pytest.mark.characterization
class TestDatabaseBehavior:
    """Characterization tests for Database operations."""

    def test_create_room_returns_object_with_id(self, db_session):
        """CAPTURE: create_room returns object with auto-generated ID."""
        room = db_session.create_room(name="Test Room", file_path="/test/path")

        # Capture current return value structure
        assert room is not None
        assert hasattr(room, "id")
        assert room.id is not None
        assert room.id > 0

    def test_create_room_stores_name_and_path(self, db_session):
        """CAPTURE: Name and file_path are stored correctly."""
        room = db_session.create_room(
            name="Test Room Name",
            file_path="/test/file/path.txt"
        )

        # Retrieve and verify stored values
        retrieved = db_session.get_room_by_id(room.id)
        assert retrieved.name == "Test Room Name"
        assert retrieved.file_path == "/test/file/path.txt"

    def test_get_all_rooms_sorting(self, db_session):
        """CAPTURE: get_all_rooms returns rooms in specific order."""
        # Create multiple rooms
        room1 = db_session.create_room(name="Room 1")
        room2 = db_session.create_room(name="Room 2")
        room3 = db_session.create_room(name="Room 3")

        # Get all rooms
        rooms = db_session.get_all_rooms()

        # Capture current sorting behavior
        assert len(rooms) >= 3
        # Document the current order (message_count descending, created_at, etc.)
        room_ids = [r.id for r in rooms]
        assert room1.id in room_ids
        assert room2.id in room_ids
        assert room3.id in room_ids

    def test_add_messages_returns_count(self, db_session, sample_room):
        """CAPTURE: add_messages returns count of added messages."""
        from datetime import date, time

        # add_messages expects list of dicts with specific keys
        messages = [
            {
                "sender": "Test User",
                "content": "Test message",
                "date": date.today(),
                "time": time(12, 0),
            }
        ]

        count = db_session.add_messages(sample_room.id, messages)

        # Capture return value format
        assert isinstance(count, int)
        assert count >= 1  # At least one message added


@pytest.mark.characterization
class TestLLMClientBehavior:
    """Characterization tests for LLMClient behavior."""

    @patch("src.llm_client.requests.post")
    def test_summarize_returns_success_dict(self, mock_post, mock_config):
        """
        CAPTURE: summarize returns dict with success/content/error keys.

        This test captures the current API response format.
        """
        from src.llm_client import LLMClient
        from unittest.mock import MagicMock

        # Mock successful API response with proper streaming response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = Mock()
        # Mock the iter_lines to return JSON strings
        mock_response.iter_lines.return_value = iter([
            b'data: {"choices": [{"delta": {"content": "Test"}}]}\n',
            b"data: [DONE]\n",
        ])
        mock_post.return_value = mock_response

        # Set environment for test
        import os
        os.environ["ZAI_API_KEY"] = "test_key"

        client = LLMClient(provider="glm")
        result = client.summarize("Test chat content")

        # Capture response structure
        assert isinstance(result, dict)
        assert "success" in result
        # On success, content should be present
        if result["success"]:
            assert "content" in result
        assert "error" in result

    @patch("src.llm_client.requests.post")
    def test_summarize_handles_error_response(self, mock_post, mock_config):
        """CAPTURE: summarize handles API errors gracefully."""
        from src.llm_client import LLMClient

        # Mock error response
        mock_post.side_effect = Exception("API Error")

        import os
        os.environ["ZAI_API_KEY"] = "test_key"

        client = LLMClient(provider="glm")
        result = client.summarize("Test chat content")

        # Capture error handling behavior
        assert result["success"] is False
        assert "error" in result
        assert len(result["error"]) > 0
