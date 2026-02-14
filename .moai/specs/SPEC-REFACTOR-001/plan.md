# Implementation Plan: SPEC-REFACTOR-001

---

## TAG BLOCK

```
SPEC-ID: SPEC-REFACTOR-001
Related: spec.md, acceptance.md
Phase: Plan
Approach: Strangler Fig Pattern (Incremental Refactoring)
Methodology: DDD (Domain-Driven Development)
```

---

## Milestones by Priority

### Primary Goal (Critical - Week 1-2)

**Milestone 1: Test Infrastructure Foundation**

**Objectives**:
- Configure pytest with coverage reporting
- Create shared test fixtures and helpers
- Establish characterization test patterns

**Technical Approach**:
1. Create `tests/conftest.py` with fixtures for:
   - In-memory SQLite database
   - Temporary file directories (auto-cleanup)
   - Mock LLM API responses
   - Qt application event loop

2. Configure pytest in `pyproject.toml`:
   ```toml
   [tool.pytest.ini_options]
   testpaths = ["tests"]
   python_files = ["test_*.py"]
   python_classes = ["Test*"]
   python_functions = ["test_*"]
   addopts = [
       "--cov=src",
       "--cov-report=term-missing",
       "--cov-report=html",
       "--cov-fail-under=85",
       "-v"
   ]
   asyncio_mode = "auto"
   ```

3. Create characterization test template:
   ```python
   # tests/characterization/test_worker_behavior.py
   import pytest
   from pathlib import Path

   @pytest.mark.characterization
   class TestFileUploadWorkerBehavior:
       """Characterization tests for FileUploadWorker."""

       def test_parse_kakao_log_format(self, sample_chat_file):
           """Capture current behavior: Parse real KakaoTalk log format."""
           # Given: Real sample file from production
           # When: Parse with KakaoLogParser
           # Then: Capture exact output structure
           pass
   ```

**Success Criteria**:
- pytest runs without errors
- Coverage reporting works (pytest --cov)
- Temporary fixtures auto-cleanup verified
- Can run unit tests in < 30 seconds

**Risks**:
- Risk: Characterization tests may be brittle
- Mitigation: Use sample files from real data, normalize paths

---

### Secondary Goal (High Priority - Week 3-4)

**Milestone 2: Repository Layer Extraction**

**Objectives**:
- Extract database operations into Repository pattern
- Add comprehensive unit tests for repositories
- Update main_window.py to use repositories

**Technical Approach**:

**Step 1: Create Base Repository Interface**

```python
# src/repositories/base.py
from abc import ABC, abstractmethod
from typing import TypeVar, Generic, Optional, List

T = TypeVar('T')

class Repository(ABC, Generic[T]):
    """Base repository interface."""

    @abstractmethod
    def create(self, **kwargs) -> T:
        """Create new entity."""
        pass

    @abstractmethod
    def get_by_id(self, entity_id: int) -> Optional[T]:
        """Retrieve entity by ID."""
        pass

    @abstractmethod
    def get_all(self) -> List[T]:
        """Retrieve all entities."""
        pass

    @abstractmethod
    def update(self, entity_id: int, **kwargs) -> Optional[T]:
        """Update entity."""
        pass

    @abstractmethod
    def delete(self, entity_id: int) -> bool:
        """Delete entity."""
        pass
```

**Step 2: Implement ChatRoomRepository**

```python
# src/repositories/chat_room_repository.py
from .base import Repository
from src.db.models import ChatRoom
from typing import Optional, List

class ChatRoomRepository(Repository[ChatRoom]):
    """ChatRoom data access layer."""

    def __init__(self, db):
        self.db = db

    def create(self, name: str, file_path: Optional[str] = None) -> ChatRoom:
        """Create new chat room."""
        return self.db.create_room(name, file_path)

    def get_by_id(self, room_id: int) -> Optional[ChatRoom]:
        """Get room by ID."""
        return self.db.get_room_by_id(room_id)

    def get_by_name(self, name: str) -> Optional[ChatRoom]:
        """Get room by name."""
        return self.db.get_room_by_name(name)

    def get_all(self) -> List[ChatRoom]:
        """Get all rooms ordered by message count."""
        return self.db.get_all_rooms()

    def update_sync_time(self, room_id: int) -> None:
        """Update last sync timestamp."""
        self.db.update_room_sync_time(room_id)

    def delete(self, room_id: int) -> bool:
        """Delete room by ID."""
        return self.db.delete_room(room_id)
```

**Step 3: Unit Tests for Repositories**

```python
# tests/unit/test_repositories/test_chat_room_repository.py
import pytest
from src.repositories.chat_room_repository import ChatRoomRepository
from src.db.models import ChatRoom

class TestChatRoomRepository:
    """Unit tests for ChatRoomRepository."""

    @pytest.fixture
    def repository(self, db_session):
        """Create repository with test database."""
        return ChatRoomRepository(db_session)

    def test_create_room(self, repository):
        """Test creating a new chat room."""
        # When: Create room
        room = repository.create(name="Test Room")

        # Then: Room is created with ID
        assert room.id is not None
        assert room.name == "Test Room"

    def test_get_by_name(self, repository):
        """Test retrieving room by name."""
        # Given: Room exists
        created = repository.create(name="Existing Room")

        # When: Retrieve by name
        found = repository.get_by_name("Existing Room")

        # Then: Room is found
        assert found is not None
        assert found.id == created.id

    def test_get_all_returns_sorted_by_message_count(self, repository):
        """Test that get_all returns rooms sorted by message count."""
        # Given: Multiple rooms with different message counts
        room1 = repository.create(name="Room 1")
        room2 = repository.create(name="Room 2")

        # When: Retrieve all rooms
        rooms = repository.get_all()

        # Then: Rooms are sorted by message count (descending)
        # Implementation detail: Add messages and verify order
        assert len(rooms) >= 2
```

**Step 4: Update main_window.py**

```python
# Before (direct database access):
from db import get_db
db = get_db()
room = db.create_room(name)

# After (repository pattern):
from src.repositories.chat_room_repository import ChatRoomRepository
repo = ChatRoomRepository(get_db())
room = repo.create(name)
```

**Success Criteria**:
- All 5 repositories implemented (ChatRoom, Message, Summary, SyncLog, URL)
- Repository unit tests achieve 90%+ coverage
- main_window.py updated to use repositories
- All existing functionality preserved

**Risks**:
- Risk: Circular dependencies between repositories
- Mitigation: Use dependency injection, clear ownership boundaries

---

### Secondary Goal (High Priority - Week 5-6)

**Milestone 3: Service Layer Extraction**

**Objectives**:
- Extract business logic into service layer
- Add integration tests for service workflows
- Remove business logic from UI layer

**Technical Approach**:

**Step 1: Create ChatService**

```python
# src/services/chat_service.py
from typing import Dict, List
from src.repositories.chat_room_repository import ChatRoomRepository
from src.repositories.message_repository import MessageRepository
from src.parser import KakaoLogParser
from src.exceptions.chat_exceptions import ChatProcessingError

class ChatService:
    """Chat processing business logic."""

    def __init__(
        self,
        room_repo: ChatRoomRepository,
        message_repo: MessageRepository
    ):
        self.room_repo = room_repo
        self.message_repo = message_repo

    def import_chat_file(
        self,
        file_path: str,
        room_name: str
    ) -> Dict[str, any]:
        """
        Import chat file into database.

        Returns:
            Dict with keys: room_id, message_count, new_message_count
        """
        # 1. Parse file
        parser = KakaoLogParser()
        try:
            parse_result = parser.parse(file_path)
        except Exception as e:
            raise ChatProcessingError(f"Failed to parse file: {e}")

        # 2. Get or create room
        room = self.room_repo.get_by_name(room_name)
        if not room:
            room = self.room_repo.create(name=room_name, file_path=file_path)

        # 3. Import messages
        message_count = self.message_repo.add_messages(
            room.id,
            parse_result.messages
        )

        return {
            "room_id": room.id,
            "message_count": message_count,
            "room_name": room.name
        }
```

**Step 2: Create SummaryService**

```python
# src/services/summary_service.py
from typing import List, Dict
from src.repositories.summary_repository import SummaryRepository
from src.services.file_service import FileService
from src.llm_client import LLMClient
from src.exceptions.summary_exceptions import SummaryGenerationError

class SummaryService:
    """LLM summary generation orchestration."""

    def __init__(
        self,
        summary_repo: SummaryRepository,
        file_service: FileService,
        llm_client: LLMClient
    ):
        self.summary_repo = summary_repo
        self.file_service = file_service
        self.llm_client = llm_client

    def generate_daily_summary(
        self,
        room_id: int,
        target_date: str
    ) -> str:
        """
        Generate LLM summary for a specific date.

        Returns:
            Summary content string
        """
        # 1. Load original chat for date
        room = self._get_room(room_id)
        original_content = self.file_service.load_daily_original(
            room.name,
            target_date
        )

        if not original_content:
            raise SummaryGenerationError(
                f"No chat data found for {target_date}"
            )

        # 2. Generate summary
        result = self.llm_client.summarize(original_content)

        if not result["success"]:
            raise SummaryGenerationError(
                f"LLM API error: {result['error']}"
            )

        # 3. Save to file and database
        self.file_service.save_daily_summary(
            room.name,
            target_date,
            result["content"],
            self.llm_client.provider
        )

        self.summary_repo.add_summary(
            room_id,
            target_date,
            "daily",
            result["content"],
            self.llm_client.provider
        )

        return result["content"]
```

**Step 3: Integration Tests for Services**

```python
# tests/integration/test_chat_service.py
import pytest
from pathlib import Path
from src.services.chat_service import ChatService
from src.repositories.chat_room_repository import ChatRoomRepository
from src.repositories.message_repository import MessageRepository

class TestChatServiceIntegration:
    """Integration tests for ChatService."""

    @pytest.fixture
    def service(self, db_session):
        """Create service with test database."""
        room_repo = ChatRoomRepository(db_session)
        message_repo = MessageRepository(db_session)
        return ChatService(room_repo, message_repo)

    def test_import_chat_file_end_to_end(self, service, sample_chat_file):
        """Test complete chat file import workflow."""
        # When: Import chat file
        result = service.import_chat_file(
            str(sample_chat_file),
            "Test Room"
        )

        # Then: Import succeeds
        assert result["room_id"] > 0
        assert result["message_count"] > 0
        assert result["room_name"] == "Test Room"

        # And: Messages are in database
        room = service.room_repo.get_by_id(result["room_id"])
        messages = service.message_repo.get_messages_by_room(room.id)
        assert len(messages) == result["message_count"]
```

**Success Criteria**:
- All services implemented (Chat, Summary, URL, Config, File)
- Service integration tests achieve 80%+ coverage
- Business logic removed from main_window.py
- Services can be tested without UI dependencies

**Risks**:
- Risk: Service layer may become anemic (just delegating to repositories)
- Mitigation: Ensure services contain business logic, not just CRUD

---

### Secondary Goal (High Priority - Week 7)

**Milestone 4: Worker Thread Separation**

**Objectives**:
- Extract workers from main_window.py to separate modules
- Ensure thread-safe database access
- Add thread safety tests

**Technical Approach**:

**Step 1: Create Base Worker Class**

```python
# src/workers/base.py
from PySide6.QtCore import QThread, Signal, QObject
from typing import Optional
from src.db.database import Database

class BaseWorker(QThread):
    """Base worker class with thread-safe database access."""

    progress = Signal(int, str)  # (progress_percent, message)
    finished = Signal(bool, str, object)  # (success, message, result)
    error = Signal(str)  # error_message

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._worker_db: Optional[Database] = None

    def run(self):
        """Override in subclass. Must call _init_db() first."""
        raise NotImplementedError

    def _init_db(self) -> Database:
        """
        Initialize thread-specific database instance.

        IMPORTANT: Each worker MUST create its own Database instance
        to prevent SQLite concurrency issues.
        """
        if self._worker_db is None:
            self._worker_db = Database()
        return self._worker_db

    def _cleanup_db(self):
        """Cleanup database connection after work completes."""
        if self._worker_db:
            self._worker_db.engine.dispose()
            self._worker_db = None
```

**Step 2: Extract FileUploadWorker**

```python
# src/workers/file_upload_worker.py
from .base import BaseWorker
from pathlib import Path
from src.services.chat_service import ChatService
from src.repositories.chat_room_repository import ChatRoomRepository
from src.repositories.message_repository import MessageRepository

class FileUploadWorker(BaseWorker):
    """Worker for file upload and parsing."""

    def __init__(self, file_path: str, room_name: Optional[str] = None, parent=None):
        super().__init__(parent)
        self.file_path = Path(file_path)
        self.room_name = room_name

    def run(self):
        """Execute file upload workflow."""
        try:
            # Create thread-local database and repositories
            db = self._init_db()
            room_repo = ChatRoomRepository(db)
            message_repo = MessageRepository(db)

            # Create service
            chat_service = ChatService(room_repo, message_repo)

            # Import chat file
            self.progress.emit(10, "파일 파싱 중...")
            result = chat_service.import_chat_file(
                str(self.file_path),
                self.room_name or self._extract_room_name()
            )

            self.progress.emit(100, "완료")
            self.finished.emit(True, "파일 업로드 성공", result)

        except Exception as e:
            self.error.emit(f"파일 업로드 실패: {str(e)}")
            self.finished.emit(False, str(e), None)

        finally:
            self._cleanup_db()
```

**Step 3: Thread Safety Tests**

```python
# tests/integration/test_thread_safety.py
import pytest
import threading
from time import sleep
from src.workers.file_upload_worker import FileUploadWorker
from src.db.database import Database

class TestThreadSafety:
    """Thread safety tests for workers."""

    def test_concurrent_database_access(self, temp_db, sample_chat_files):
        """Test that concurrent workers don't corrupt database."""
        results = []
        errors = []

        def worker_thread(file_path):
            try:
                worker = FileUploadWorker(file_path, "Test Room")
                worker.run()
                results.append(worker._worker_db is not None)
            except Exception as e:
                errors.append(e)

        # When: Run 5 workers concurrently
        threads = [
            threading.Thread(target=worker_thread, args=(fp,))
            for fp in sample_chat_files[:5]
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=30)

        # Then: No errors and all workers completed
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(results) == 5

        # And: Database is not corrupted
        db = Database(temp_db)
        rooms = db.get_all_rooms()
        assert len(rooms) > 0
```

**Success Criteria**:
- All workers extracted to `src/workers/`
- Each worker uses dedicated Database instance
- Thread safety tests pass with 5 concurrent workers
- Zero "database is locked" errors

**Risks**:
- Risk: Memory leaks from undisposed database connections
- Mitigation: Explicit cleanup in finally blocks, resource monitoring

---

### Secondary Goal (High Priority - Week 8)

**Milestone 5: Dialog Separation**

**Objectives**:
- Extract dialogs to dedicated files
- Add UI tests for dialog components
- Reduce main_window.py size

**Technical Approach**:

**Step 1: Create Base Dialog Class**

```python
# src/ui/dialogs/base_dialog.py
from PySide6.QtWidgets import QDialog
from typing import Optional

class BaseDialog(QDialog):
    """Base dialog with common functionality."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        """Override in subclass to setup UI."""
        raise NotImplementedError

    def validate_input(self) -> tuple[bool, Optional[str]]:
        """
        Validate dialog input.

        Returns:
            (is_valid, error_message)
        """
        raise NotImplementedError
```

**Step 2: Extract CreateRoomDialog**

```python
# src/ui/dialogs/create_room_dialog.py
from .base_dialog import BaseDialog
from PySide6.QtWidgets import QVBoxLayout, QLineEdit, QPushButton

class CreateRoomDialog(BaseDialog):
    """Dialog for creating a new chat room."""

    def __init__(self, parent=None):
        self.name_input: Optional[QLineEdit] = None
        self.create_btn: Optional[QPushButton] = None
        super().__init__(parent)

    def _setup_ui(self):
        """Setup dialog UI components."""
        layout = QVBoxLayout()

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("채팅방 이름 입력")
        self.name_input.setMinimumWidth(300)

        self.create_btn = QPushButton("만들기")
        self.create_btn.setDefault(True)
        self.create_btn.clicked.connect(self.accept)

        layout.addWidget(self.name_input)
        layout.addWidget(self.create_btn)
        self.setLayout(layout)

    def validate_input(self) -> tuple[bool, Optional[str]]:
        """Validate room name input."""
        name = self.name_input.text().strip()

        if not name:
            return False, "채팅방 이름을 입력해주세요."

        if len(name) > 255:
            return False, "채팅방 이름은 255자 이내로 입력해주세요."

        return True, None

    def get_room_name(self) -> str:
        """Get validated room name."""
        is_valid, error_msg = self.validate_input()

        if not is_valid:
            raise ValueError(error_msg)

        return self.name_input.text().strip()
```

**Step 3: Update main_window.py**

```python
# Before: Dialog class in main_window.py
class CreateRoomDialog(QDialog):
    # ... 100+ lines of dialog code
    pass

# After: Import from dialogs module
from src.ui.dialogs.create_room_dialog import CreateRoomDialog

# Usage:
dialog = CreateRoomDialog(self)
if dialog.exec():
    room_name = dialog.get_room_name()
    # ... create room
```

**Success Criteria**:
- All dialogs extracted to `src/ui/dialogs/`
- Dialog tests cover validation logic
- main_window.py reduced by ~500 lines

---

### Final Goal (Medium Priority - Week 9-10)

**Milestone 6: Configuration and Error Handling**

**Objectives**:
- Implement ConfigManager with startup validation
- Add custom exception hierarchy
- Implement structured logging

**Technical Approach**:

**Step 1: Create ConfigManager**

```python
# src/config/config_manager.py
from dataclasses import dataclass
from typing import Dict, Optional
import os
from pathlib import Path
from src.exceptions.config_exceptions import ConfigurationError

@dataclass(frozen=True)
class LLMConfig:
    """LLM provider configuration."""
    provider: str
    api_key: str
    base_url: str
    timeout: int = 600

class ConfigManager:
    """Thread-safe configuration manager."""

    _instance: Optional['ConfigManager'] = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, '_initialized'):
            return

        self._llm_configs: Dict[str, LLMConfig] = {}
        self._load_configurations()
        self._validate_required_configs()
        self._initialized = True

    def _load_configurations(self):
        """Load configurations from environment variables."""
        # Load Z.AI GLM
        glm_key = os.getenv("ZAI_API_KEY")
        if glm_key:
            self._llm_configs['glm'] = LLMConfig(
                provider='glm',
                api_key=glm_key,
                base_url='https://open.bigmodel.cn/api/paas/v4/chat'
            )

        # Load other providers...
        # ChatGPT, MiniMax, Perplexity

    def _validate_required_configs(self):
        """Validate that at least one LLM provider is configured."""
        if not self._llm_configs:
            raise ConfigurationError(
                "No LLM provider configured. "
                "Please set ZAI_API_KEY, OPENAI_API_KEY, "
                "MINIMAX_API_KEY, or PERPLEXITY_API_KEY "
                "in .env.local file."
            )

    def get_llm_config(self, provider: str) -> LLMConfig:
        """Get configuration for specific LLM provider."""
        config = self._llm_configs.get(provider)

        if not config:
            available = ', '.join(self._llm_configs.keys())
            raise ConfigurationError(
                f"LLM provider '{provider}' not configured. "
                f"Available providers: {available}"
            )

        return config

    @property
    def available_providers(self) -> list[str]:
        """Get list of available LLM providers."""
        return list(self._llm_configs.keys())
```

**Step 2: Custom Exception Hierarchy**

```python
# src/exceptions/base.py
class KakaoChatSummaryError(Exception):
    """Base exception for application."""

    def __init__(self, message: str, context: Optional[Dict] = None):
        self.message = message
        self.context = context or {}
        super().__init__(self.message)

# src/exceptions/configuration_exceptions.py
class ConfigurationError(KakaoChatSummaryError):
    """Configuration related errors."""
    pass

class MissingAPIKeyError(ConfigurationError):
    """Raised when required API key is missing."""
    pass

# src/exceptions/database_exceptions.py
class DatabaseError(KakaoChatSummaryError):
    """Database operation errors."""
    pass

class ChatRoomNotFoundError(DatabaseError):
    """Raised when chat room is not found."""
    pass

# Usage in code:
try:
    room = repo.get_by_id(room_id)
    if not room:
        raise ChatRoomNotFoundError(
            f"Chat room with ID {room_id} not found",
            context={"room_id": room_id}
        )
except ChatRoomNotFoundError as e:
    logger.error(f"Room not found: {e.message}", extra=e.context)
    # Handle error
```

**Step 3: Structured Logging**

```python
# src/logging_config.py
import logging
import sys
from pathlib import Path

def setup_logging(log_dir: Path):
    """Configure structured logging for application."""

    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s - %(context)s'
    )

    # File handler for detailed logs
    log_file = log_dir / f"summarizer_{datetime.now():%Y%m%d}.log"
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(detailed_formatter)

    # Console handler for user-facing messages
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))

    # Root logger configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

# Usage in code:
import logging
logger = logging.getLogger(__name__)

try:
    room = repo.get_by_id(room_id)
except ChatRoomNotFoundError as e:
    logger.error(
        "Failed to retrieve chat room",
        extra={"context": e.context, "room_id": room_id}
    )
```

**Success Criteria**:
- ConfigManager validates API keys at startup
- All exceptions use custom hierarchy
- Structured logging with context information
- No API keys logged or exposed

---

## Risk Mitigation Strategies

### Risk: Breaking Existing Functionality

**Mitigation**:
1. Create comprehensive characterization tests before refactoring
2. Run full test suite after each milestone
3. Maintain feature freeze during refactoring period
4. Keep v2.5.1 branch for rollback capability

### Risk: Test Maintenance Overhead

**Mitigation**:
1. Focus on critical paths first (database, file operations)
2. Use characterization tests for legacy code
3. Use pytest markers to categorize tests (unit, integration, slow)
4. Document test intent clearly in docstrings

### Risk: Team Adoption Resistance

**Mitigation**:
1. Pair programming sessions for test writing
2. Demonstrate value through quick bug detection
3. Make pre-commit hooks optional during learning period
4. Provide clear testing documentation with examples

---

## Technical Approach Summary

### Architecture Principles

1. **Separation of Concerns**:
   - UI Layer (main_window.py, dialogs): Presentation only
   - Service Layer: Business logic orchestration
   - Repository Layer: Data access abstraction
   - Worker Layer: Background task execution

2. **Dependency Injection**:
   - Constructor injection for all dependencies
   - Explicit type hints for all injected objects
   - No global mutable state

3. **Thread Safety**:
   - Each worker thread gets dedicated Database instance
   - Repository objects are thread-local
   - No shared state across threads

4. **Testability**:
   - All layers testable without dependencies
   - Mock-friendly interfaces
   - In-memory database for tests

### Design Patterns Used

- **Repository Pattern**: Data access abstraction
- **Service Layer Pattern**: Business logic encapsulation
- **Dependency Injection**: Loose coupling
- **Singleton Pattern**: ConfigManager (thread-safe)
- **Factory Pattern**: Worker creation
- **Strategy Pattern**: LLM provider switching

---

## Validation Strategy

### Continuous Validation

1. **After Each Commit**:
   - Run ruff for code style
   - Run mypy for type checking
   - Run pytest for unit tests

2. **After Each Milestone**:
   - Full test suite with coverage report
   - Integration tests for modified modules
   - Manual smoke test of GUI functionality

3. **End of Refactoring**:
   - Complete regression test suite
   - Performance benchmark comparison
   - Documentation review and updates

---

## Definition of Done

**Milestone is complete when**:
- All acceptance criteria from `acceptance.md` are met
- Test coverage >= 85% for affected modules
- Zero mypy errors (--strict mode)
- Zero ruff warnings
- Manual smoke test passes
- Code review approved
- Documentation updated

**Overall refactoring is complete when**:
- All 6 milestones completed
- main_window.py <= 800 lines
- Full test suite runs in < 60 seconds
- Zero critical bugs in first month post-refactoring
- Team training completed
- Development guide updated
