"""
Pytest configuration and shared fixtures for kakao-chat-summary tests.

This module provides fixtures for:
- In-memory SQLite database
- Temporary file directories with auto-cleanup
- Mock LLM API responses
- Qt application event loop
- Sample data for testing
"""

import os
import sys
import tempfile
from pathlib import Path
from datetime import date, time
from unittest.mock import Mock, MagicMock

import pytest
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


@pytest.fixture(scope="session")
def qapp():
    """
    Create QApplication instance for Qt tests.

    This fixture is session-scoped to avoid creating multiple QApplication instances,
    which is not allowed by Qt.
    """
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app
    # Don't delete the app, as it may be needed by other tests


@pytest.fixture
def temp_dir():
    """
    Create a temporary directory for test files.

    The directory is automatically cleaned up after the test.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def temp_db(temp_dir):
    """
    Create an in-memory SQLite database for testing.

    Returns the database file path. The database is created in a temp directory
    and automatically cleaned up after the test.
    """
    db_path = temp_dir / "test.db"
    yield db_path


@pytest.fixture
def db_session(temp_db):
    """
    Create a Database instance with test database.

    This fixture provides a clean database for each test function.
    All data is isolated between tests.
    """
    from src.db.database import Database

    # Create database with temp file
    db = Database(db_path=str(temp_db))

    # Create all tables
    from src.db.models import Base
    Base.metadata.create_all(db.engine)

    yield db

    # Cleanup: close connection and delete file
    db.engine.dispose()
    if temp_db.exists():
        temp_db.unlink()


@pytest.fixture
def sample_chat_file(temp_dir):
    """
    Create a sample KakaoTalk chat log file for testing.

    The file contains realistic Korean chat messages with various formats.
    Uses PC/Mac format with dashes around date headers.
    """
    chat_content = """KakaoTalk Chat Export
---------------------

--------------- 2024년 2월 10일 토요일 ---------------
--------------- [오전 10:00] 홍길동: 안녕하세요!
--------------- [오전 10:05] 김철수: 네 안녕하세요! 오늘 날씨가 좋네요.
--------------- [오전 10:10] 이영희: 맞아요, 산책하기 딱 좋은 날씨네요.
--------------- [오전 10:15] 홍길동: https://www.example.com/weather 여기 날씨 보니까 오후에 비 온대요
--------------- [오전 10:20] 김철수: 아 그렇군요, 우산 챙겨야겠네요

--------------- 2024년 2월 11일 일요일 ---------------
--------------- [오후 2:00] 이영희: 점심 맛있게 드셨나요?
--------------- [오후 2:05] 홍길동: 네 김치찌개 먹었어요
--------------- [오후 2:10] 김철수: 저는 샌드위치로 간단히 해결했어요 ㅎㅎ
"""

    chat_file = temp_dir / "sample_chat.txt"
    chat_file.write_text(chat_content, encoding="utf-8")
    yield chat_file


@pytest.fixture
def sample_chat_files(temp_dir):
    """
    Create multiple sample KakaoTalk chat log files for testing.

    Returns a list of file paths.
    """
    files = []

    for i in range(3):
        chat_content = f"""KakaoTalk Chat Export {i+1}
---------------------

--------------- 2024년 2월 10일 토요일 ---------------
--------------- [오전 10:00] 사용자{i}: 테스트 메시지 {i}
--------------- [오전 10:05] 사용자{i}: 두번째 메시지
"""
        chat_file = temp_dir / f"chat_{i}.txt"
        chat_file.write_text(chat_content, encoding="utf-8")
        files.append(chat_file)

    yield files


@pytest.fixture
def mock_llm_response():
    """
    Create a mock LLM API response for testing.

    Returns a dictionary simulating a successful LLM summary response.
    """
    return {
        "success": True,
        "content": """# 카카오톡 대화 요약

## 주요 대화 주제
- 날씨에 대한 이야기
- 점심 메뉴에 대한 대화

## 참여자
- 홍길동
- 김철수
- 이영희

## 주요 내용
- 오후에 비가 온다는 예보
- 점심으로 김치찌개와 샌드위치를 먹음
""",
        "error": None,
        "tokens_used": 500,
    }


@pytest.fixture
def mock_llm_client():
    """
    Create a mock LLMClient for testing.

    The mock client returns predefined responses without making actual API calls.
    """
    mock_client = Mock()
    mock_client.provider = "test"
    mock_client.summarize.return_value = {
        "success": True,
        "content": "Test summary content",
        "error": None,
    }
    yield mock_client


@pytest.fixture
def sample_room(db_session):
    """
    Create a sample ChatRoom in the test database.

    Returns the ChatRoom object.
    """
    # Create room with participant_count
    with db_session.get_session() as session:
        from src.db.models import ChatRoom
        room = ChatRoom(
            name="Test Room",
            file_path="/path/to/chat.txt",
            participant_count=3
        )
        session.add(room)
        session.flush()
        # Return a copy to avoid detached instance issues
        result = ChatRoom(
            id=room.id,
            name=room.name,
            file_path=room.file_path,
            participant_count=room.participant_count
        )
    yield result


@pytest.fixture
def sample_messages(db_session, sample_room):
    """
    Create sample messages in the test database.

    Returns a list of dictionaries with message data.
    """
    messages_data = [
        {
            "sender": "홍길동",
            "content": "안녕하세요!",
            "date": date(2024, 2, 10),
            "time": time(10, 0),
        },
        {
            "sender": "김철수",
            "content": "네 안녕하세요!",
            "date": date(2024, 2, 10),
            "time": time(10, 5),
        },
        {
            "sender": "이영희",
            "content": "날씨가 좋네요",
            "date": date(2024, 2, 10),
            "time": time(10, 10),
        },
    ]

    # Add messages using database method
    count = db_session.add_messages(sample_room.id, messages_data)

    # Fetch and return messages
    messages = db_session.get_messages_by_room(sample_room.id)
    yield messages


@pytest.fixture
def sample_summary(db_session, sample_room):
    """
    Create a sample summary in the test database.

    Returns the Summary object.
    """
    from src.db.models import Summary

    # Create summary using session context manager
    with db_session.get_session() as session:
        summary = Summary(
            room_id=sample_room.id,
            summary_date=date(2024, 2, 10),
            summary_type="daily",
            content="# 요약\n\n테스트 요약 내용",
            llm_provider="test",
        )
        session.add(summary)
        session.flush()
        # Return a copy
        result = Summary(
            id=summary.id,
            room_id=summary.room_id,
            summary_date=summary.summary_date,
            summary_type=summary.summary_type,
            content=summary.content,
            llm_provider=summary.llm_provider
        )
    yield result


@pytest.fixture
def mock_config(temp_dir):
    """
    Create a mock configuration for testing.

    Sets up temporary .env.local file with test API keys.
    """
    env_file = temp_dir / ".env.local"
    env_file.write_text(
        "ZAI_API_KEY=test_key_123\n"
        "OPENAI_API_KEY=sk_test_456\n"
        "MINIMAX_API_KEY=test_789\n"
        "PERPLEXITY_API_KEY=pplx_test_012\n"
    )
    yield env_file


@pytest.fixture
def file_storage(temp_dir):
    """
    Create a FileStorage instance with temporary directory.

    Uses a temporary base directory that is automatically cleaned up.
    """
    from src.file_storage import FileStorage

    # Override base directory for testing
    storage = FileStorage()
    storage.base_dir = temp_dir
    storage.original_dir = temp_dir / "original"
    storage.summary_dir = temp_dir / "summary"
    storage.url_dir = temp_dir / "url"

    # Create directories
    storage.original_dir.mkdir(parents=True, exist_ok=True)
    storage.summary_dir.mkdir(parents=True, exist_ok=True)
    storage.url_dir.mkdir(parents=True, exist_ok=True)

    yield storage


@pytest.fixture
def mock_responses():
    """
    Mock HTTP responses for LLM API testing.

    Uses the responses library to mock HTTP requests.
    """
    import responses

    responses.start()
    yield responses
    responses.stop()
    responses.reset()


@pytest.fixture
def qtbot(qapp):
    """
    Create a QtBot instance for widget testing.

    Provides methods for simulating user interaction with Qt widgets.
    """
    from pytestqt.qtbot import QtBot

    result = QtBot(qapp)
    yield result


def pytest_configure(config):
    """
    Configure pytest with custom markers.

    This is called once at the start of the test run.
    """
    config.addinivalue_line(
        "markers",
        "characterization: Characterization tests for existing behavior (PRESERVE phase)"
    )
    config.addinivalue_line(
        "markers",
        "unit: Unit tests for individual functions/classes"
    )
    config.addinivalue_line(
        "markers",
        "integration: Integration tests for multiple components"
    )
    config.addinivalue_line(
        "markers",
        "ui: UI component tests"
    )
    config.addinivalue_line(
        "markers",
        "slow: Slow-running tests (network, file I/O)"
    )


@pytest.fixture(autouse=True)
def reset_singletons():
    """
    Reset singleton instances before each test.

    Prevents state leakage between tests for singleton classes like ConfigManager.
    """
    yield

    # Reset any singleton instances here
    # For example: ConfigManager._instance = None
    pass
