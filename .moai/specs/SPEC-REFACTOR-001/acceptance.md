# Acceptance Criteria: SPEC-REFACTOR-001

---

## TAG BLOCK

```
SPEC-ID: SPEC-REFACTOR-001
Related: spec.md, plan.md
Validation: EARS Requirements Verification
Format: Given-When-Then (Gherkin)
```

---

## Testing Infrastructure Acceptance

### AC-TEST-001: Pytest Configuration and Fixtures

**Given**: The project has pytest and related dependencies installed
**When**: Developer runs `pytest --version`
**Then**: Pytest version 7.4.0+ is displayed
**And**: All dependencies (pytest-cov, pytest-mock, responses) are importable

### AC-TEST-002: Test Fixtures Functionality

**Given**: The tests/conftest.py contains shared fixtures
**When**: Unit tests import `db_session`, `temp_dir`, `mock_llm_client` fixtures
**Then**: Fixtures are available and provide:
- `db_session`: In-memory SQLite database with tables created
- `temp_dir`: Temporary directory that auto-cleans after test
- `mock_llm_client`: Mocked LLMClient with predefined responses
- `qt_app`: QApplication instance for UI tests

### AC-TEST-003: Characterization Test Template

**Given**: Legacy code needs behavior preservation
**When**: Developer creates characterization test using template
**Then**: Test captures current behavior without modification
**And**: Test file placed in `tests/characterization/` directory
**And**: Test marked with `@pytest.mark.characterization`

### AC-TEST-004: Coverage Reporting

**Given**: pytest-cov is configured in pyproject.toml
**When**: Developer runs `pytest --cov=src --cov-report=term-missing`
**Then**: Coverage report displays percentage for each module
**And**: Missing lines are shown in terminal output
**And**: HTML report generated in `htmlcov/` directory

### AC-TEST-005: Test Execution Speed

**Given**: Full test suite is present
**When**: Developer runs `pytest tests/`
**Then**: All unit tests complete within 30 seconds
**And**: All integration tests complete within 30 seconds
**And**: Total test suite time < 60 seconds

### AC-TEST-006: Pre-commit Hooks

**Given**: Pre-commit hooks are configured in `.git/hooks/pre-commit`
**When**: Developer attempts to commit code changes
**Then**: Hooks run automatically:
- ruff linter (zero warnings required)
- mypy type checker (zero errors required)
- pytest with coverage (minimum 85% required)
**And**: Commit is blocked if any check fails

---

## Repository Layer Acceptance

### AC-REPO-001: Base Repository Interface

**Given**: Base repository interface exists in `src/repositories/base.py`
**When**: New repository class inherits from `Repository[T]`
**Then**: Class must implement all abstract methods:
- `create(**kwargs) -> T`
- `get_by_id(entity_id: int) -> Optional[T]`
- `get_all() -> List[T]`
- `update(entity_id: int, **kwargs) -> Optional[T]`
- `delete(entity_id: int) -> bool`

### AC-REPO-002: ChatRoomRepository Implementation

**Given**: ChatRoomRepository is implemented
**When**: Application needs chat room data access
**Then**: Repository provides methods:
- `create(name, file_path) -> ChatRoom`
- `get_by_id(room_id) -> Optional[ChatRoom]`
- `get_by_name(name) -> Optional[ChatRoom]`
- `get_all() -> List[ChatRoom]` (sorted by message count)
- `update_sync_time(room_id) -> None`
- `delete(room_id) -> bool`
- `get_stats(room_id) -> Dict[str, Any]`

### AC-REPO-003: Repository Unit Tests

**Given**: All 5 repositories are implemented
**When**: Test suite runs for repository layer
**Then**: Each repository has unit tests with >= 90% coverage
**And**: Tests use in-memory SQLite database
**And**: Tests verify CRUD operations
**And**: Tests verify error handling

### AC-REPO-004: Repository Integration

**Given**: Repositories are implemented and tested
**When**: main_window.py uses repositories instead of direct database access
**Then**: All existing functionality preserved
**And**: Zero direct database access calls in main_window.py
**And**: Repository methods return detached ORM objects

---

## Service Layer Acceptance

### AC-SVC-001: ChatService Business Logic

**Given**: ChatService is implemented in `src/services/chat_service.py`
**When**: Application imports chat file
**Then**: Service orchestrates workflow:
1. Parse file using KakaoLogParser
2. Get or create chat room via ChatRoomRepository
3. Import messages via MessageRepository
4. Return result dictionary with room_id, message_count

### AC-SVC-002: SummaryService Orchestration

**Given**: SummaryService is implemented
**When**: User generates LLM summary
**Then**: Service orchestrates workflow:
1. Load original chat content via FileService
2. Generate summary via LLMClient
3. Save summary file via FileService
4. Store summary metadata via SummaryRepository
5. Return summary content

### AC-SVC-003: Service Integration Tests

**Given**: All services are implemented
**When**: Integration tests run for service layer
**Then**: Each service has integration tests with >= 80% coverage
**And**: Tests verify end-to-end workflows
**And**: Tests use real database (in-memory SQLite)
**And**: Tests verify business logic, not just CRUD

### AC-SVC-004: Service Dependency Injection

**Given**: Services are implemented with constructor injection
**When**: Services are instantiated
**Then**: All dependencies passed via constructor
**And**: Services use Protocol types for interface abstraction
**And**: No global state or singleton dependencies (except ConfigManager)

---

## Worker Thread Acceptance

### AC-WORKER-001: Base Worker Class

**Given**: BaseWorker class exists in `src/workers/base.py`
**When**: Worker thread is created
**Then**: Worker provides:
- `_init_db()` method for thread-local database
- `_cleanup_db()` method for resource cleanup
- `progress` signal for progress updates
- `finished` signal for completion notification
- `error` signal for error reporting

### AC-WORKER-002: Worker Thread Safety

**Given**: Workers are extracted to separate modules
**When**: Multiple workers run concurrently
**Then**: Each worker creates dedicated Database instance
**And**: Workers do not share database connections
**And**: Zero "database is locked" errors occur
**And**: Zero database corruption incidents occur

### AC-WORKER-003: Worker Extraction

**Given**: Workers existed in main_window.py
**When**: Refactoring is complete
**Then**: All workers moved to `src/workers/`:
- FileUploadWorker
- SyncWorker
- SummaryGeneratorWorker
- RecoveryWorker
**And**: main_window.py imports workers from workers module
**And**: main_window.py reduced by ~1000 lines

### AC-WORKER-004: Thread Safety Tests

**Given**: Thread safety tests exist in `tests/integration/test_thread_safety.py`
**When**: Tests run with 5 concurrent workers
**Then**: All workers complete successfully
**And**: Database remains consistent (no corruption)
**And**: All data correctly persisted
**And**: No race conditions detected

---

## Dialog Separation Acceptance

### AC-DLG-001: Base Dialog Class

**Given**: BaseDialog class exists in `src/ui/dialogs/base_dialog.py`
**When**: New dialog is created
**Then**: Dialog inherits from BaseDialog
**And**: Dialog implements `_setup_ui()` method
**And**: Dialog implements `validate_input()` method

### AC-DLG-002: Dialog Extraction

**Given**: Dialogs existed in main_window.py
**When**: Refactoring is complete
**Then**: All dialogs moved to `src/ui/dialogs/`:
- CreateRoomDialog
- UploadFileDialog
- SummaryOptionsDialog
- SettingsDialog
**And**: main_window.py imports dialogs from dialogs module
**And**: main_window.py reduced by ~500 lines

### AC-DLG-003: Dialog Validation Tests

**Given**: Dialogs are separated
**When**: Dialog tests run
**Then**: Each dialog has tests for:
- Input validation logic
- Error message display
- Accept/reject behavior
- UI component initialization

### AC-DLG-004: Dialog Integration

**Given**: Dialogs are in separate modules
**When**: main_window.py uses dialogs
**Then**: All dialog functionality preserved
**And**: Dialog behavior identical to pre-refactoring
**And**: Zero regressions in user workflows

---

## Configuration Management Acceptance

### AC-CONFIG-001: ConfigManager Singleton

**Given**: ConfigManager is implemented
**When**: Application starts
**Then**: ConfigManager validates at least one LLM provider API key
**And**: If no API keys configured, exits with clear error message
**And**: Error message lists all required environment variables

### AC-CONFIG-002: Configuration Structure

**Given**: ConfigManager is implemented
**When**: Configuration is accessed
**Then**: Uses dataclasses for type safety
**And**: Provides typed LLMConfig objects
**And**: Thread-safe singleton pattern with locking

### AC-CONFIG-003: API Key Validation

**Given**: Application starts with .env.local file
**When**: API keys are missing or empty
**Then**: Application displays error:
  "No LLM provider configured. Please set ZAI_API_KEY,
   OPENAI_API_KEY, MINIMAX_API_KEY, or PERPLEXITY_API_KEY
   in .env.local file."
**And**: Application exits with error code 1

### AC-CONFIG-004: API Key Security

**Given**: Application runs with valid API keys
**When**: Logging occurs (info, debug, error levels)
**Then**: API keys never appear in log files
**And**: API keys never appear in error messages
**And**: API keys never printed to console

### AC-CONFIG-005: Runtime Configuration

**Given**: ConfigManager is singleton
**When**: Multiple threads access configuration
**Then**: No race conditions occur
**And**: Thread-safe access via threading.Lock()
**And**: Configuration loaded only once at startup

---

## Error Handling Acceptance

### AC-ERR-001: Custom Exception Hierarchy

**Given**: Exception hierarchy exists in `src/exceptions/`
**When**: Application errors occur
**Then**: Exceptions use custom types:
- `KakaoChatSummaryError` (base)
- `ConfigurationError`
- `DatabaseError`
- `FileOperationError`
- `LLMError`
- `ValidationError`

### AC-ERR-002: Exception Context

**Given**: Custom exceptions are raised
**When**: Exception is caught and logged
**Then**: Exception includes context dictionary
**And**: Context contains relevant debugging information
**And**: Context logged via structured logging

### AC-ERR-003: User-Facing Error Messages

**Given**: Business logic raises exceptions
**When**: Error reaches UI layer
**Then**: Error message displayed in Korean
**And**: Error message provides actionable guidance
**And**: Technical details logged but not shown to user

### AC-ERR-004: Database Error Handling

**Given**: Database operation fails
**When**: Repository catches database exception
**Then**: Wrapped in `DatabaseError` with context
**And**: Raw SQL never exposed to user
**And**: Error logged with SQL query and parameters

### AC-ERR-005: LLM Error Handling

**Given**: LLM API call fails
**When**: LLMClient catches API error
**Then**: Retry up to 3 times with exponential backoff
**And**: After 3 failures, raise `LLMError` with API response
**And**: Error message includes provider and error type

### AC-ERR-006: File Operation Error Handling

**Given**: File operation fails (read, write, parse)
**When**: FileService catches exception
**Then**: Distinguish error types:
- PermissionError (file access denied)
- FileNotFoundError (file not found)
- CorruptFileError (parse failure)
**And**: Raise appropriate `FileOperationError` subclass

---

## Code Quality Acceptance

### AC-QUAL-001: Type Hints Coverage

**Given**: All modules are refactored
**When**: Developer runs `mypy --strict src/`
**Then**: Zero type checking errors occur
**And**: Type hints coverage >= 90% of functions
**And**: All public APIs have complete type hints

### AC-QUAL-002: Code Style Compliance

**Given**: ruff is configured
**When**: Developer runs `ruff check src/`
**Then**: Zero linting warnings occur
**And**: Code follows PEP 8 standards
**And**: Maximum line length = 100 characters

### AC-QUAL-003: Function Complexity

**Given**: Code is refactored
**When**: Cyclomatic complexity is measured
**Then**: No function exceeds complexity of 10
**And**: No function exceeds 50 lines
**And**: Complex logic extracted to helper functions

### AC-QUAL-004: Class Design

**Given**: Classes are refactored
**When**: Class size is measured
**Then**: No class has more than 10 public methods
**And**: Classes have single responsibility
**And**: Class names are descriptive nouns

### AC-QUAL-005: Code Duplication

**Given**: Codebase is analyzed for duplication
**When**: Duplicate patterns are found
**Then**: Duplicates extracted to reusable utilities
**And**: Duplication ratio < 5% (excluding tests)

### AC-QUAL-006: Documentation

**Given**: Modules are refactored
**When**: Documentation is reviewed
**Then**: All public functions have docstrings
**And**: Docstrings follow Google style guide
**And**: Complex logic has inline comments

---

## Architecture Acceptance

### AC-ARCH-001: Layer Separation

**Given**: Refactored architecture
**When**: Dependency graph is analyzed
**Then**: No circular dependencies exist
**And**: UI layer has no dependency on database
**And**: Service layer has no dependency on UI
**And**: Repository layer has no dependency on services

### AC-ARCH-002: Module Size

**Given**: Refactoring is complete
**When**: Module line counts are measured
**Then**: main_window.py <= 800 lines
**And**: No other module exceeds 1000 lines
**And**: Total line count comparable to pre-refactoring

### AC-ARCH-003: Import Structure

**Given**: Modules are organized
**When**: Import statements are reviewed
**Then**: No relative imports across package boundaries
**And**: Imports grouped by stdlib, third-party, local
**And**: No unused imports (verified by ruff)

### AC-ARCH-004: Dependency Injection

**Given**: Services and repositories are implemented
**When**: Dependencies are instantiated
**Then**: Constructor injection used for all dependencies
**And**: Explicit type hints for all injected objects
**And**: No global mutable state (except ConfigManager)

---

## Performance Acceptance

### AC-PERF-001: Application Startup Time

**Given**: Application is refactored
**When**: Application starts with valid configuration
**Then**: Startup time <= 2 seconds (comparable to v2.5.1)
**And**: No noticeable performance degradation

### AC-PERF-002: Test Execution Speed

**Given**: Full test suite is present
**When**: Developer runs `pytest tests/`
**Then**: Unit tests complete in < 30 seconds
**And**: Integration tests complete in < 30 seconds
**And**: Total test suite time < 60 seconds

### AC-PERF-003: Database Operation Performance

**Given**: Database operations use repository layer
**When**: Benchmark tests run
**Then**: Repository operations <= 10% slower than direct database access
**And**: No N+1 query problems detected

### AC-PERF-004: Memory Usage

**Given**: Application runs with refactored code
**When**: Memory usage is monitored
**Then**: Memory consumption comparable to v2.5.1
**And**: No memory leaks from undisposed database connections

---

## Regression Testing Acceptance

### AC-REG-001: Characterization Tests

**Given**: Legacy code characterization tests exist
**When**: Refactoring changes code
**Then**: All characterization tests pass
**And**: Zero behavior regressions detected

### AC-REG-002: Smoke Tests

**Given**: Application is fully refactored
**When**: Manual smoke test is performed
**Then**: All critical workflows work:
- Create chat room
- Upload chat file
- Generate LLM summary
- View dashboard statistics
- Browse summaries by date
- View URL information
- Settings dialog functionality

### AC-REG-003: Data Migration

**Given**: User has v2.5.1 database and files
**When**: User runs refactored application
**Then**: All existing data accessible
**And**: No database migration required
**And**: Zero data loss occurs

---

## Documentation Acceptance

### AC-DOC-001: Developer Guide

**Given**: Refactoring is complete
**When**: New developer joins project
**Then**: Developer guide includes:
- Architecture overview
- Testing guide with examples
- Code style guidelines
- Contribution workflow
**And**: Guide is comprehensive and up-to-date

### AC-DOC-002: API Documentation

**Given**: Service and repository layers exist
**When**: API documentation is generated
**Then**: All public methods documented
**And**: Docstrings include parameter types and return types
**And**: Usage examples provided for complex operations

### AC-DOC-003: Changelog

**Given**: Refactoring is complete
**When**: CHANGELOG.md is reviewed
**Then**: v3.0.0 entry describes refactoring
**And**: Breaking changes clearly documented
**And**: Migration guide provided for users

---

## Final Quality Gates

### AC-FINAL-001: Test Coverage

**Given**: All code is refactored and tested
**When**: `pytest --cov=src --cov-report=term-missing` runs
**Then**: Overall coverage >= 85%
**And**: Each module coverage >= 80%
**And**: Critical paths (parser, database, file_storage) >= 90%

### AC-FINAL-002: Type Safety

**Given**: All code has type hints
**When**: `mypy --strict src/` runs
**Then**: Zero type checking errors
**And`: No `type: ignore` comments except for legacy compatibility

### AC-FINAL-003: Code Quality

**Given**: All code follows standards
**When**: `ruff check src/` runs
**Then**: Zero linting warnings
**And**: No formatting issues

### AC-FINAL-004: Pre-commit Hooks

**Given**: Pre-commit hooks are installed
**When**: Developer attempts to commit
**Then**: All hooks pass:
- ruff check
- mypy check
- pytest with coverage
**And**: Commit succeeds only if all checks pass

### AC-FINAL-005: Continuous Integration

**Given**: CI pipeline is configured
**When**: Pull request is created
**Then**: CI runs full test suite
**And**: All quality checks pass
**And**: PR blocked if any check fails

---

## Success Criteria Summary

### Must Have (Critical)

- [ ] Test coverage >= 85% (pytest-cov)
- [ ] Zero mypy errors (--strict mode)
- [ ] Zero ruff warnings
- [ ] main_window.py <= 800 lines
- [ ] All layers separated (UI, Service, Repository, Worker)
- [ ] Thread-safe database access (no corruption)
- [ ] Pre-commit hooks enforcing quality
- [ ] Zero critical bugs in first month

### Should Have (High Priority)

- [ ] Test suite runs in < 60 seconds
- [ ] All modules have docstrings
- [ ] Custom exception hierarchy implemented
- [ ] ConfigManager with startup validation
- [ ] Structured logging with context
- [ ] Developer guide updated

### Could Have (Medium Priority)

- [ ] Performance benchmarks documented
- [ ] API documentation generated
- [ ] Migration guide for users
- [ ] Integration with CI/CD pipeline

### Won't Have (Out of Scope)

- Desktop application packaging/installer
- Multi-user support
- Cloud synchronization
- Mobile application

---

## Validation Process

### Test Execution

1. **Unit Tests**: `pytest tests/unit/ -v`
   - Coverage: 90%+ for repositories, services

2. **Integration Tests**: `pytest tests/integration/ -v`
   - Coverage: 80%+ for workflows

3. **UI Tests**: `pytest tests/ui/ -v`
   - Coverage: 70%+ for dialogs and widgets

4. **Full Suite**: `pytest tests/ --cov=src --cov-report=html`
   - Coverage: 85%+ overall
   - Time: < 60 seconds

### Code Quality Checks

1. **Type Checking**: `mypy --strict src/`
   - Result: Zero errors

2. **Linting**: `ruff check src/`
   - Result: Zero warnings

3. **Formatting**: `ruff format --check src/`
   - Result: Zero formatting issues

### Manual Validation

1. **Smoke Test**: Run application, test all critical workflows
2. **Performance Test**: Monitor startup time, memory usage
3. **Data Migration Test**: Use v2.5.1 database, verify accessibility

---

## Sign-off Criteria

**Refactoring is complete when**:
- All acceptance criteria met
- Code review approved by maintainer
- Documentation updated
- CHANGELOG.md updated
- Tagged as v3.0.0
- Release notes published
