"""Tests for MessageParser utility class."""
import pytest
from datetime import date, time

from src.workers.file_upload_worker import MessageParser


class TestMessageParser:
    """Test MessageParser message line parsing."""

    def test_parse_basic_message(self):
        """Parse a basic AM message."""
        line = "[홍길동] [오전 9:30] 안녕하세요"
        result = MessageParser.parse_message(line, date(2024, 2, 10))

        assert result is not None
        assert result['sender'] == "홍길동"
        assert result['time'] == time(9, 30)
        assert result['content'] == "안녕하세요"
        assert result['date'] == date(2024, 2, 10)

    def test_parse_pm_message(self):
        """Parse a PM message with hour conversion."""
        line = "[철수] [오후 3:45] 점심 먹었어?"
        result = MessageParser.parse_message(line, date(2024, 2, 10))

        assert result is not None
        assert result['sender'] == "철수"
        assert result['time'] == time(15, 45)  # 3:45 PM = 15:45
        assert result['content'] == "점심 먹었어?"

    def test_parse_noon_am(self):
        """Parse 12 AM (midnight) correctly."""
        line = "[영희] [오전 12:00] 새해 복 많이 받으세요"
        result = MessageParser.parse_message(line, date(2024, 1, 1))

        assert result is not None
        assert result['time'] == time(0, 0)  # 12 AM = 00:00

    def test_parse_noon_pm(self):
        """Parse 12 PM (noon) correctly."""
        line = "[민수] [오후 12:30] 점심 시간이에요"
        result = MessageParser.parse_message(line, date(2024, 2, 10))

        assert result is not None
        assert result['time'] == time(12, 30)  # 12 PM = 12:30

    def test_parse_multiline_content(self):
        """Parse message with multiline content."""
        line = "[테스터] [오전 10:00] 첫 번째 줄\n두 번째 줄"
        result = MessageParser.parse_message(line, date(2024, 2, 10))

        assert result is not None
        assert "첫 번째 줄" in result['content']
        assert "두 번째 줄" in result['content']

    def test_parse_invalid_format(self):
        """Return None for invalid format."""
        line = "This is not a valid message format"
        result = MessageParser.parse_message(line, date(2024, 2, 10))

        assert result is None

    def test_parse_system_message(self):
        """Return None for system messages without sender."""
        line = "--------------- 2024년 2월 10일 토요일 ---------------"
        result = MessageParser.parse_message(line, date(2024, 2, 10))

        assert result is None

    def test_parse_single_digit_hour(self):
        """Parse single digit hours."""
        line = "[유저] [오전 9:05] 아침!"
        result = MessageParser.parse_message(line, date(2024, 2, 10))

        assert result is not None
        assert result['time'] == time(9, 5)

    def test_parse_double_digit_hour(self):
        """Parse double digit hours."""
        line = "[유저] [오전 10:05] 늦은 아침!"
        result = MessageParser.parse_message(line, date(2024, 2, 10))

        assert result is not None
        assert result['time'] == time(10, 5)

    def test_parse_preserves_raw_line(self):
        """Raw line is preserved in result."""
        line = "[테스트] [오후 2:30] 원본 라인 보존 테스트"
        result = MessageParser.parse_message(line, date(2024, 2, 10))

        assert result is not None
        assert result['raw_line'] == line
