# SPEC-REFACTOR-001: Architecture Refactoring for Testability

---

## TAG BLOCK

```
SPEC-ID: SPEC-REFACTOR-001
Title: Architecture Refactoring for Testability
Status: Planned
Priority: High
Created: 2026-02-11
Updated: 2026-02-11
Assigned: manager-spec
Domain: Architecture Refactoring
Traceability: plan.md, acceptance.md
```

---

## Environment

### Current System State

**Application Type**: PySide6 (Qt) Desktop Application
**Language**: Python 3.11+
**Current Version**: v2.5.1
**Total Code Size**: ~10,000 lines (9987 lines in src/)
**Test Coverage**: 0%

### Technical Context

**Current Architecture**:
- Monolithic `main_window.py` (~3,133 lines)
- Tight coupling between UI and business logic
- Mixed threading patterns (QThread workers)
- Direct database access from UI layer
- File storage operations embedded in UI code

**Key Dependencies**:
- PySide6 6.6.0+ (Qt GUI framework)
- SQLAlchemy 2.0+ (ORM)
- APScheduler 3.10.0+ (Task scheduling)
- requests 2.31.0+ (HTTP client)
- python-dotenv 1.0.0+ (Configuration)

**Development Tools Available**:
- pytest 7.4.0+ (Testing framework)
- pytest-cov 4.1.0+ (Coverage reporting)
- pytest-mock 3.11.0+ (Mocking utilities)
- responses 0.23.0+ (HTTP mocking)
- ruff 0.1.0+ (Linter)
- mypy 1.5.0+ (Type checker)

---

## Assumptions

### Technical Assumptions

1. **SQLite is sufficient for current data volume** (High Confidence)
   - Evidence: Single-user desktop application with modest data size
   - Risk if wrong: Performance degradation with large datasets
   - Validation: Check production database sizes from current users

2. **PySide6 is the correct GUI framework choice** (High Confidence)
   - Evidence: Successful v2.5.1 release with PySide6
   - Risk if wrong: High rework cost if framework change needed
   - Validation: Continue with PySide6 for v3.0

3. **Current user workflow is stable** (Medium Confidence)
   - Evidence: Limited user feedback data
   - Risk if wrong: Refactored architecture may not support future workflows
   - Validation: Review GitHub issues and user feedback

### Business Assumptions

1. **Single-user desktop application model continues** (High Confidence)
   - Evidence: Current deployment model
   - Risk if wrong: Architecture may not scale to multi-user
   - Validation: Confirm product roadmap with stakeholders

2. **LLM provider integration remains core feature** (High Confidence)
   - Evidence: Feature central to product value
   - Risk if wrong: Over-engineering for non-core feature
   - Validation: Product requirements review

### Team Assumptions

1. **Python 3.11+ familiarity in team** (Medium Confidence)
   - Evidence: Existing codebase uses modern Python features
   - Risk if wrong: Training needed for type hints, async patterns
   - Validation: Team skill assessment

2. **Testing culture adoption feasible** (Medium Confidence)
   - Evidence: Test infrastructure already configured (pytest, pytest-cov)
   - Risk if wrong: Low compliance with testing practices
   - Validation: Pilot testing program and gather feedback

---

## Requirements (EARS Format)

### Ubiquitous Requirements (System-wide Quality Attributes)

**REQ-001**: The system SHALL maintain backward compatibility with existing v2.5.1 data files and database schema.

**REQ-002**: The system SHALL provide 85%+ test coverage across all modules (excluding UI widgets).

**REQ-003**: The system SHALL enforce type safety using mypy with strict mode enabled.

**REQ-004**: The system SHALL follow PEP 8 coding standards with ruff linter integration.

**REQ-005**: The system SHALL isolate business logic from UI layer for testability.

### Testing Infrastructure Requirements

**REQ-TEST-001**: WHEN the test suite runs, THEN it SHALL execute all unit tests within 60 seconds for rapid feedback.

**REQ-TEST-002**: WHEN code changes are committed, THEN pre-commit hooks SHALL enforce test coverage >= 85% and zero mypy errors.

**REQ-TEST-003**: WHEN running integration tests, THEN they SHALL use in-memory SQLite database for isolation.

**REQ-TEST-004**: WHEN testing LLM client interactions, THEN they SHALL mock HTTP responses using responses library.

**REQ-TEST-005**: WHEN testing file storage operations, THEN they SHALL use temporary directories with automatic cleanup.

**REQ-TEST-006**: WHEN testing UI components, THEN they SHALL use Qt Test framework with widget mocking.

**REQ-TEST-007**: WHEN characterization tests are created for existing code, THEN they SHALL capture current behavior to prevent regression.

### Architecture Refactoring Requirements

**REQ-ARCH-001**: WHEN extracting workers from main_window.py, THEN each worker SHALL reside in a separate module in `src/workers/` directory.

**REQ-ARCH-002**: WHEN implementing database operations, THEN they SHALL use Repository pattern with interfaces in `src/repositories/`.

**REQ-ARCH-003**: WHEN implementing business logic, THEN it SHALL be isolated in `src/services/` layer without UI dependencies.

**REQ-ARCH-004**: WHEN creating dialog classes, THEN they SHALL be separated into `src/ui/dialogs/` with dedicated modules per dialog.

**REQ-ARCH-005**: WHEN implementing dependency injection, THEN it SHALL use constructor injection with explicit type hints.

**REQ-ARCH-006**: WHEN refactoring main_window.py, THEN it SHALL be reduced to <= 800 lines focused on UI composition.

**REQ-ARCH-007**: WHEN accessing database from workers, THEN each worker SHALL create its own Database instance to prevent SQLite concurrency issues.

**REQ-ARCH-008**: WHEN implementing file operations, THEN they SHALL be abstracted through FileStorage interface for testability.

### Configuration Management Requirements

**REQ-CONFIG-001**: WHEN the application starts, THEN it SHALL validate all required API keys and exit with clear error message if missing.

**REQ-CONFIG-002**: WHEN configuration is loaded, THEN it SHALL use typed dataclasses for structure validation.

**REQ-CONFIG-003**: WHEN environment-specific settings are needed, THEN they SHALL be loaded from `.env.local` with clear error messages for missing keys.

**REQ-CONFIG-004**: WHEN runtime configuration updates occur, THEN they SHALL use singleton ConfigManager with thread-safe access.

**REQ-CONFIG-005**: WHEN API keys are accessed, THEN they SHALL never be logged or exposed in error messages.

### Error Handling Requirements

**REQ-ERR-001**: WHEN an exception occurs in business logic, THEN it SHALL be wrapped in custom exception types from dedicated hierarchy.

**REQ-ERR-002**: WHEN errors are logged, THEN they SHALL use structured logging with context information.

**REQ-ERR-003**: WHEN user-facing errors are displayed, THEN they SHALL provide actionable guidance in Korean language.

**REQ-ERR-004**: WHEN database errors occur, THEN they SHALL be caught and logged without exposing raw SQL to user.

**REQ-ERR-005**: WHEN file operation errors occur, THEN they SHALL distinguish between permission errors, not found errors, and corruption errors.

**REQ-ERR-006**: WHEN LLM API errors occur, THEN they SHALL be retried up to 3 times with exponential backoff.

**REQ-ERR-007**: WHEN unhandled exceptions occur in workers, THEN they SHALL emit error signal to UI thread for graceful display.

### Code Quality Requirements

**REQ-QUAL-001**: WHEN duplicate code patterns are identified, THEN they SHALL be extracted into reusable utilities.

**REQ-QUAL-002**: WHEN functions exceed 50 lines, THEN they SHALL be refactored into smaller functions.

**REQ-QUAL-003**: WHEN classes have more than 10 public methods, THEN they SHALL be split into smaller classes.

**REQ-QUAL-004**: WHEN type hints are added, THEN they SHALL use strict typing with Optional, List, Dict, and Protocol types.

**REQ-QUAL-005**: WHEN code is committed, THEN it SHALL pass ruff linting with zero warnings.

**REQ-QUAL-006**: WHEN code is committed, THEN it SHALL pass mypy type checking with zero errors.

**REQ-QUAL-007**: WHEN pre-commit hooks are configured, THEN they SHALL include ruff, mypy, and pytest checks.

### Optional Requirements (Nice-to-Have)

**REQ-OPT-001**: WHERE possible, the system SHOULD provide async/await patterns for I/O operations to improve responsiveness.

**REQ-OPT-002**: WHERE feasible, the system SHOULD implement dependency injection container for complex object graphs.

**REQ-OPT-003**: WHERE appropriate, the system SHOULD use Protocol types for interface definitions instead of ABC.

### Unwanted Requirements (Prohibitions)

**REQ-UNWANTED-001**: The system SHALL NOT introduce circular dependencies between modules.

**REQ-UNWANTED-002**: The system SHALL NOT use global mutable state for application configuration.

**REQ-UNWANTED-003**: The system SHALL NOT hardcode file paths or database connection strings.

**REQ-UNWANTED-004**: The system SHALL NOT use print() statements in production code (use logging instead).

**REQ-UNWANTED-005**: The system SHALL NOT catch bare Exception except in top-level error handlers.

**REQ-UNWANTED-006**: The system SHALL NOT use mutable default arguments in function signatures.

**REQ-UNWANTED-007**: Workers SHALL NOT share Database instances across threads.

---

## Specifications

### Test Module Structure

```
tests/
├── __init__.py
├── conftest.py                    # Shared pytest fixtures
├── unit/
│   ├── test_parser.py            # KakaoLogParser tests
│   ├── test_file_storage.py      # FileStorage tests
│   ├── test_llm_client.py        # LLMClient tests with mocked HTTP
│   ├── test_url_extractor.py     # URL extraction tests
│   └── test_full_config.py       # Configuration tests
├── integration/
│   ├── test_database_workflow.py # End-to-end database operations
│   ├── test_chat_processor.py    # Chat processing integration
│   └── test_import_workflow.py   # Import to DB integration
├── ui/
│   ├── test_main_window.py       # MainWindow widget tests
│   └── test_dialogs.py           # Dialog component tests
└── characterization/
    ├── test_worker_behavior.py   # Worker thread behavior characterization
    └── test_file_operations.py   # File operation behavior snapshots
```

### Repository Layer Structure

```
src/repositories/
├── __init__.py
├── base.py                       # Base repository interface
├── chat_room_repository.py       # ChatRoom data access
├── message_repository.py         # Message data access
├── summary_repository.py         # Summary data access
├── sync_log_repository.py        # SyncLog data access
└── url_repository.py             # URL data access
```

### Service Layer Structure

```
src/services/
├── __init__.py
├── chat_service.py               # Chat processing business logic
├── summary_service.py            # LLM summary orchestration
├── url_service.py                # URL extraction and storage
├── config_service.py             # Configuration validation
└── file_service.py               # File operation orchestration
```

### Worker Layer Structure

```
src/workers/
├── __init__.py
├── base.py                       # Base worker class
├── file_upload_worker.py         # File upload worker
├── sync_worker.py                # Background sync worker
├── summary_worker.py             # LLM summary worker
└── recovery_worker.py            # Recovery worker
```

### Dialog Structure

```
src/ui/dialogs/
├── __init__.py
├── create_room_dialog.py         # ChatRoom creation dialog
├── upload_file_dialog.py         # File upload dialog
├── summary_options_dialog.py     # Summary options dialog
└── settings_dialog.py            # Settings dialog
```

### Exception Hierarchy

```
src/exceptions/
├── __init__.py
├── base.py                       # Base application exception
├── configuration_exceptions.py   # Config related errors
├── database_exceptions.py        # Database operation errors
├── file_operation_exceptions.py  # File operation errors
├── llm_exceptions.py             # LLM API errors
└── validation_exceptions.py      # Input validation errors
```

---

## Traceability

| Requirement ID | Module/File | Test Location |
|---------------|-------------|---------------|
| REQ-TEST-001 to REQ-TEST-007 | tests/ | pytest configuration |
| REQ-ARCH-001 | src/workers/*.py | tests/unit/test_workers.py |
| REQ-ARCH-002 | src/repositories/*.py | tests/integration/test_repositories.py |
| REQ-ARCH-003 | src/services/*.py | tests/integration/test_services.py |
| REQ-ARCH-004 | src/ui/dialogs/*.py | tests/ui/test_dialogs.py |
| REQ-ARCH-005 to REQ-ARCH-006 | src/ui/main_window.py | tests/ui/test_main_window.py |
| REQ-ARCH-007 | All workers | Thread safety tests |
| REQ-ARCH-008 | src/services/file_service.py | File storage abstraction tests |
| REQ-CONFIG-001 to REQ-CONFIG-005 | src/config/ | tests/unit/test_config.py |
| REQ-ERR-001 to REQ-ERR-007 | src/exceptions/*.py | Exception handling tests |
| REQ-QUAL-001 to REQ-QUAL-007 | All modules | Pre-commit hook validation |

---

## Success Criteria

### Primary Goals (High Priority)

1. **Test Coverage Achievement**: 85%+ code coverage measured by pytest-cov
   - Exclusion: UI widget visual tests may use manual validation
   - Measurement: `pytest --cov=src --cov-report=term-missing`

2. **Architecture Decoupling**: main_window.py reduced to <= 800 lines
   - Business logic extracted to services
   - Workers extracted to separate modules
   - Dialogs separated into dedicated files

3. **Type Safety**: Zero mypy errors in strict mode
   - All modules pass `mypy --strict src/`
   - Type hints coverage >= 90% of functions

4. **Thread Safety**: Zero database corruption incidents in testing
   - Each worker uses dedicated Database instance
   - No SQLite "database is locked" errors

### Secondary Goals (Medium Priority)

1. **Code Quality**: Zero ruff warnings
   - All code passes `ruff check src/`
   - Pre-commit hooks enforce standards

2. **Test Execution Speed**: Full test suite under 60 seconds
   - Unit tests: < 30 seconds
   - Integration tests: < 30 seconds

3. **Error Handling**: All exceptions wrapped in custom types
   - No bare Exception catches except top-level
   - Structured logging with context

### Final Goals (Optional)

1. **Performance**: Application startup time unchanged (< 2 seconds)
2. **Documentation**: All modules have docstrings with examples
3. **Developer Experience**: Clear onboarding guide for testing

---

## Risk Assessment

### High Risk Items

| Risk | Impact | Mitigation Strategy |
|------|--------|-------------------|
| Breaking existing functionality during refactoring | Critical | Characterization tests before refactoring, incremental changes |
| Thread safety regressions causing DB corruption | Critical | Dedicated thread safety tests, Database instance per worker |
| Test maintenance burden exceeding development capacity | High | Start with critical paths, use characterization tests |
| Type system friction slowing development | Medium | Gradual adoption, allow # type: ignore for legacy code |

### Medium Risk Items

| Risk | Impact | Mitigation Strategy |
|------|--------|-------------------|
| Learning curve for team unfamiliar with testing | Medium | Pair programming, knowledge sharing sessions |
| Pre-commit hooks rejected by team due to friction | Medium | Configuration options, gradual rollout |
| Mock maintenance burden for LLM tests | Medium | Use recording-based VCR approach if needed |

---

## Dependencies

### Internal Dependencies

- None (this is foundational refactoring work)

### External Dependencies

- Python 3.11+ features (typing.Protocol, dataclasses)
- PySide6 Qt Test framework
- pytest 7.4.0+
- pytest-cov 4.1.0+
- pytest-mock 3.11.0+
- responses 0.23.0+
- ruff 0.1.0+
- mypy 1.5.0+

---

## Notes

### Refactoring Philosophy

This refactoring follows the **Strangler Fig Pattern**:

1. **Preserve**: Create characterization tests for existing behavior
2. **Extract**: Gradually extract components without breaking functionality
3. **Validate**: Run tests after each extraction to verify behavior preservation
4. **Delete**: Remove old code only after new implementation is verified

### Incremental Migration Strategy

**Phase 1**: Test infrastructure setup (Week 1)
- Configure pytest, fixtures, test helpers
- Create characterization tests for critical paths

**Phase 2**: Repository layer extraction (Week 2)
- Extract database operations into repositories
- Add unit tests for repository methods
- Update main_window.py to use repositories

**Phase 3**: Service layer extraction (Week 3)
- Extract business logic into services
- Add integration tests for service workflows
- Update workers to use services

**Phase 4**: Worker separation (Week 4)
- Extract workers to separate modules
- Add thread safety tests
- Verify no database corruption

**Phase 5**: Dialog separation (Week 5)
- Extract dialogs to dedicated files
- Add UI tests
- Verify no regressions

**Phase 6**: Configuration and error handling (Week 6)
- Implement ConfigManager
- Add custom exception hierarchy
- Add structured logging

### Success Metrics

- **Code Coverage**: 85%+ (pytest-cov)
- **Type Safety**: 0 mypy errors (--strict)
- **Code Quality**: 0 ruff warnings
- **Test Speed**: < 60 seconds full suite
- **Regression Bugs**: 0 critical bugs in first month post-refactoring
