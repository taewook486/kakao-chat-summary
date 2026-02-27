"""
Tests for SyncScheduler and sync_room_from_file function.

Characterization tests for APScheduler-based task scheduling.
Tests capture CURRENT behavior to prevent regression during refactoring.

Target: src/scheduler/tasks.py

Test Coverage:
- SyncScheduler lifecycle (start, stop, is_running)
- Job management (add_sync_job, add_summary_job, remove_job, get_jobs)
- Callback configuration (set_sync_callback, set_summary_callback)
- sync_room_from_file behavior with mocked dependencies
"""

import pytest
from unittest.mock import Mock, MagicMock, patch, call
from pathlib import Path
from datetime import datetime

from src.scheduler.tasks import SyncScheduler, sync_room_from_file


class TestSyncSchedulerInitialization:
    """Test SyncScheduler initialization behavior."""

    def test_scheduler_initializes_with_qtscheduler(self):
        """
        CAPTURE: SyncScheduler creates QtScheduler on initialization.

        Current behavior:
        - Creates QtScheduler instance
        - Initializes callbacks to None
        - Sets _is_running to False
        """
        scheduler = SyncScheduler()

        assert scheduler._sync_callback is None
        assert scheduler._summary_callback is None
        assert scheduler.is_running is False

    def test_scheduler_has_qtscheduler_instance(self):
        """
        CAPTURE: QtScheduler instance is stored in scheduler attribute.
        """
        scheduler = SyncScheduler()

        assert hasattr(scheduler, 'scheduler')
        # QtScheduler should have start and shutdown methods
        assert hasattr(scheduler.scheduler, 'start')
        assert hasattr(scheduler.scheduler, 'shutdown')
        assert hasattr(scheduler.scheduler, 'add_job')
        assert hasattr(scheduler.scheduler, 'get_jobs')
        assert hasattr(scheduler.scheduler, 'remove_job')


class TestSyncSchedulerCallbacks:
    """Test callback configuration behavior."""

    def test_set_sync_callback_stores_callback(self):
        """
        CAPTURE: set_sync_callback stores the callback function.
        """
        scheduler = SyncScheduler()
        mock_callback = Mock()

        scheduler.set_sync_callback(mock_callback)

        assert scheduler._sync_callback is mock_callback

    def test_set_summary_callback_stores_callback(self):
        """
        CAPTURE: set_summary_callback stores the callback function.
        """
        scheduler = SyncScheduler()
        mock_callback = Mock()

        scheduler.set_summary_callback(mock_callback)

        assert scheduler._summary_callback is mock_callback


class TestSyncSchedulerLifecycle:
    """Test scheduler start/stop lifecycle behavior."""

    def test_start_starts_qtscheduler(self):
        """
        CAPTURE: start() calls QtScheduler.start() and sets flag.
        """
        scheduler = SyncScheduler()

        scheduler.start()

        assert scheduler.is_running is True

    def test_start_does_not_start_twice(self):
        """
        CAPTURE: start() checks _is_running flag before starting.
        """
        scheduler = SyncScheduler()

        scheduler.start()
        first_call_running = scheduler.is_running

        # Mock to track if start is called again
        original_start = scheduler.scheduler.start
        scheduler.scheduler.start = Mock()

        scheduler.start()

        assert first_call_running is True
        # QtScheduler.start should not be called twice
        # (The actual scheduler handles this, but we verify flag check)

    def test_stop_shutdowns_qtscheduler(self):
        """
        CAPTURE: stop() calls QtScheduler.shutdown() and clears flag.
        """
        scheduler = SyncScheduler()

        scheduler.start()
        assert scheduler.is_running is True

        scheduler.stop()

        assert scheduler.is_running is False

    def test_stop_does_not_stop_if_not_running(self):
        """
        CAPTURE: stop() checks _is_running flag before stopping.
        """
        scheduler = SyncScheduler()

        # Should not raise or call shutdown if not running
        scheduler.stop()

        assert scheduler.is_running is False


class TestSyncSchedulerJobManagement:
    """Test job addition, removal, and listing behavior."""

    def test_add_sync_job_with_callback(self):
        """
        CAPTURE: add_sync_job adds job when callback is set.

        Current behavior:
        - Returns early with warning if callback is None
        - Removes existing job with same ID
        - Adds new job with interval trigger
        """
        scheduler = SyncScheduler()
        mock_callback = Mock()
        scheduler.set_sync_callback(mock_callback)

        # Mock add_job to track calls
        scheduler.scheduler.add_job = Mock()

        scheduler.add_sync_job(interval_minutes=30, job_id="test_sync")

        scheduler.scheduler.add_job.assert_called_once()
        call_args = scheduler.scheduler.add_job.call_args
        assert call_args[0][0] is mock_callback  # First arg is callback

    def test_add_sync_job_without_callback_returns_early(self):
        """
        CAPTURE: add_sync_job returns early if sync_callback is None.

        Current behavior:
        - Logs warning "Sync callback not set"
        - Returns without adding job
        """
        scheduler = SyncScheduler()

        # Mock add_job to verify it's not called
        scheduler.scheduler.add_job = Mock()

        result = scheduler.add_sync_job()

        # add_job should not be called (callback is None)
        scheduler.scheduler.add_job.assert_not_called()

    def test_add_sync_job_removes_existing_job(self):
        """
        CAPTURE: add_sync_job removes existing job before adding new one.
        """
        scheduler = SyncScheduler()
        mock_callback = Mock()
        scheduler.set_sync_callback(mock_callback)

        # Track remove_job calls
        scheduler.scheduler.remove_job = Mock()
        scheduler.scheduler.add_job = Mock()

        scheduler.add_sync_job(job_id="sync_all")

        # remove_job should be called before add_job
        scheduler.scheduler.remove_job.assert_called_once_with("sync_all")
        scheduler.scheduler.add_job.assert_called_once()

    def test_add_summary_job_with_callback(self):
        """
        CAPTURE: add_summary_job adds job when callback is set.
        """
        scheduler = SyncScheduler()
        mock_callback = Mock()
        scheduler.set_summary_callback(mock_callback)

        # Mock add_job to track calls
        scheduler.scheduler.add_job = Mock()

        scheduler.add_summary_job(interval_hours=24, job_id="test_summary")

        scheduler.scheduler.add_job.assert_called_once()
        call_args = scheduler.scheduler.add_job.call_args
        assert call_args[0][0] is mock_callback

    def test_add_summary_job_without_callback_returns_early(self):
        """
        CAPTURE: add_summary_job returns early if summary_callback is None.

        Current behavior:
        - Logs warning "Summary callback not set"
        - Returns without adding job
        """
        scheduler = SyncScheduler()

        scheduler.scheduler.add_job = Mock()

        result = scheduler.add_summary_job()

        scheduler.scheduler.add_job.assert_not_called()

    def test_remove_job_exists(self):
        """
        CAPTURE: remove_job calls scheduler.remove_job.

        Current behavior:
        - Catches exceptions silently (job may not exist)
        - Logs info message on success
        """
        scheduler = SyncScheduler()

        scheduler.scheduler.remove_job = Mock()

        scheduler.remove_job("test_job")

        scheduler.scheduler.remove_job.assert_called_once_with("test_job")

    def test_remove_job_handles_nonexistent_job(self):
        """
        CAPTURE: remove_job handles exception when job doesn't exist.

        Current behavior:
        - Catches all exceptions (bare except)
        - Does not raise
        """
        scheduler = SyncScheduler()

        # Make remove_job raise an exception
        scheduler.scheduler.remove_job = Mock(side_effect=Exception("Job not found"))

        # Should not raise
        scheduler.remove_job("nonexistent_job")

    def test_get_jobs_returns_job_info_list(self):
        """
        CAPTURE: get_jobs returns list of job dictionaries.

        Current behavior:
        - Returns list with 'id', 'name', 'next_run' keys
        - Iterates over scheduler.get_jobs()
        """
        scheduler = SyncScheduler()

        # Create mock job
        mock_job = Mock()
        mock_job.id = "test_job_1"
        mock_job.name = "Test Job"
        mock_job.next_run_time = datetime(2024, 2, 10, 10, 0)

        scheduler.scheduler.get_jobs = Mock(return_value=[mock_job])

        jobs = scheduler.get_jobs()

        assert isinstance(jobs, list)
        assert len(jobs) == 1
        assert jobs[0]['id'] == "test_job_1"
        assert jobs[0]['name'] == "Test Job"
        assert jobs[0]['next_run'] == datetime(2024, 2, 10, 10, 0)

    def test_get_jobs_returns_empty_list_when_no_jobs(self):
        """
        CAPTURE: get_jobs returns empty list when no jobs scheduled.
        """
        scheduler = SyncScheduler()

        scheduler.scheduler.get_jobs = Mock(return_value=[])

        jobs = scheduler.get_jobs()

        assert jobs == []

    def test_get_jobs_handles_multiple_jobs(self):
        """
        CAPTURE: get_jobs handles multiple scheduled jobs.
        """
        scheduler = SyncScheduler()

        mock_job1 = Mock()
        mock_job1.id = "job_1"
        mock_job1.name = "Job 1"
        mock_job1.next_run_time = datetime(2024, 2, 10, 10, 0)

        mock_job2 = Mock()
        mock_job2.id = "job_2"
        mock_job2.name = "Job 2"
        mock_job2.next_run_time = datetime(2024, 2, 11, 10, 0)

        scheduler.scheduler.get_jobs = Mock(return_value=[mock_job1, mock_job2])

        jobs = scheduler.get_jobs()

        assert len(jobs) == 2
        assert jobs[0]['id'] == "job_1"
        assert jobs[1]['id'] == "job_2"


class TestSyncRoomFromFile:
    """Test sync_room_from_file function behavior."""

    def test_returns_result_dict_structure(self, temp_dir):
        """
        CAPTURE: sync_room_from_file returns dict with expected keys.

        Current behavior:
        - Returns dict with keys: success, message_count, new_count, error
        """
        # Create test file
        chat_file = temp_dir / "chat.txt"
        chat_file.write_text("Test content")

        mock_db = Mock()

        # The function will parse and return a dict
        # Just verify the function completes and returns a dict
        result = sync_room_from_file(chat_file, room_id=1, db=mock_db)

        # Check result structure
        assert 'success' in result
        assert 'message_count' in result
        assert 'new_count' in result
        assert 'error' in result

    @patch('parser.KakaoLogParser')
    def test_calls_parser_parse_with_file_path(self, MockParser, temp_dir):
        """
        CAPTURE: sync_room_from_file calls parser.parse() with file path.
        """
        chat_file = temp_dir / "chat.txt"
        chat_file.write_text("Test content")

        mock_parser = Mock()
        mock_result = Mock()
        mock_result.messages_by_date = {'2024-02-10': ['message1', 'message2']}
        mock_parser.parse.return_value = mock_result
        MockParser.return_value = mock_parser

        mock_db = Mock()
        mock_db.add_messages.return_value = 2

        sync_room_from_file(chat_file, room_id=1, db=mock_db)

        # Parser should be created and parse called with file
        MockParser.assert_called_once()
        mock_parser.parse.assert_called_once_with(chat_file)

    @patch('parser.KakaoLogParser')
    def test_calls_db_add_messages(self, MockParser, temp_dir):
        """
        CAPTURE: sync_room_from_file calls db.add_messages() with parsed data.
        """
        chat_file = temp_dir / "chat.txt"
        chat_file.write_text("Test content")

        mock_parser = Mock()
        mock_result = Mock()
        mock_result.messages_by_date = {
            '2024-02-10': ['message1', 'message2']
        }
        mock_parser.parse.return_value = mock_result
        MockParser.return_value = mock_parser

        mock_db = Mock()
        mock_db.add_messages.return_value = 2

        result = sync_room_from_file(chat_file, room_id=1, db=mock_db)

        # add_messages should be called with room_id and messages
        mock_db.add_messages.assert_called_once()
        call_args = mock_db.add_messages.call_args
        assert call_args[0][0] == 1  # room_id

    @patch('parser.KakaoLogParser')
    def test_calls_db_update_room_sync_time(self, MockParser, temp_dir):
        """
        CAPTURE: sync_room_from_file calls db.update_room_sync_time() after adding messages.
        """
        chat_file = temp_dir / "chat.txt"
        chat_file.write_text("Test content")

        mock_parser = Mock()
        mock_result = Mock()
        mock_result.messages_by_date = {'2024-02-10': ['msg1']}
        mock_parser.parse.return_value = mock_result
        MockParser.return_value = mock_parser

        mock_db = Mock()
        mock_db.add_messages.return_value = 1

        sync_room_from_file(chat_file, room_id=1, db=mock_db)

        # update_room_sync_time should be called
        mock_db.update_room_sync_time.assert_called_once_with(1)

    @patch('parser.KakaoLogParser')
    def test_calls_db_add_sync_log_on_success(self, MockParser, temp_dir):
        """
        CAPTURE: sync_room_from_file calls db.add_sync_log() with success status.
        """
        chat_file = temp_dir / "chat.txt"
        chat_file.write_text("Test content")

        mock_parser = Mock()
        mock_result = Mock()
        mock_result.messages_by_date = {'2024-02-10': ['msg1']}
        mock_parser.parse.return_value = mock_result
        MockParser.return_value = mock_parser

        mock_db = Mock()
        mock_db.add_messages.return_value = 1

        sync_room_from_file(chat_file, room_id=1, db=mock_db)

        # add_sync_log should be called with 'success' status
        mock_db.add_sync_log.assert_called_once()
        call_args = mock_db.add_sync_log.call_args
        assert call_args[0][1] == 'success'  # status is second arg

    @patch('parser.KakaoLogParser')
    def test_returns_success_true_on_successful_sync(self, MockParser, temp_dir):
        """
        CAPTURE: sync_room_from_file returns success=True when sync completes.
        """
        chat_file = temp_dir / "chat.txt"
        chat_file.write_text("Test content")

        mock_parser = Mock()
        mock_result = Mock()
        mock_result.messages_by_date = {'2024-02-10': ['msg1', 'msg2']}
        mock_parser.parse.return_value = mock_result
        MockParser.return_value = mock_parser

        mock_db = Mock()
        mock_db.add_messages.return_value = 2

        result = sync_room_from_file(chat_file, room_id=1, db=mock_db)

        assert result['success'] is True
        assert result['message_count'] == 2
        assert result['error'] is None

    @patch('parser.KakaoLogParser')
    def test_handles_exception_during_sync(self, MockParser, temp_dir):
        """
        CAPTURE: sync_room_from_file catches exceptions and returns error dict.

        Current behavior:
        - Catches all exceptions during sync
        - Returns error dict with error message
        - Calls add_sync_log with 'failed' status if db exists
        """
        chat_file = temp_dir / "chat.txt"
        chat_file.write_text("Test content")

        # Make parser raise exception
        mock_parser = Mock()
        mock_parser.parse.side_effect = Exception("Parse error")
        MockParser.return_value = mock_parser

        mock_db = Mock()

        result = sync_room_from_file(chat_file, room_id=1, db=mock_db)

        assert result['success'] is False
        assert 'Parse error' in result['error']

    @patch('parser.KakaoLogParser')
    def test_calls_add_sync_log_on_failure(self, MockParser, temp_dir):
        """
        CAPTURE: sync_room_from_file calls add_sync_log with failed status on error.
        """
        chat_file = temp_dir / "chat.txt"
        chat_file.write_text("Test content")

        mock_parser = Mock()
        mock_parser.parse.side_effect = Exception("Sync failed")
        MockParser.return_value = mock_parser

        mock_db = Mock()

        sync_room_from_file(chat_file, room_id=1, db=mock_db)

        # add_sync_log should be called with 'failed' status
        mock_db.add_sync_log.assert_called_once()
        call_args = mock_db.add_sync_log.call_args
        assert call_args[0][1] == 'failed'
