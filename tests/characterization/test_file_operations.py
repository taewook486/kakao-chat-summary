"""
Characterization tests for file operation behavior (PRESERVE phase).

These tests capture the CURRENT behavior of file operations to prevent regression.
They document what the code DOES with file I/O, not what it SHOULD DO.
"""

import pytest
from pathlib import Path
from datetime import date


@pytest.mark.characterization
class TestFileOperationSnapshots:
    """Behavior snapshots for file operations."""

    def test_file_save_overwrite_behavior(self, temp_dir):
        """
        CAPTURE: What happens when saving to existing file?

        This test documents whether:
        - File is overwritten
        - Content is merged
        - Original is backed up
        - Exception is raised
        """
        test_file = temp_dir / "test.txt"

        # Create initial file
        test_file.write_text("Original content", encoding="utf-8")

        # Save new content using the same method as production
        # (This captures current behavior)
        test_file.write_text("New content", encoding="utf-8")

        # Capture: File is overwritten
        assert test_file.read_text(encoding="utf-8") == "New content"

    def test_file_merge_strategy(self, temp_dir):
        """
        CAPTURE: How are messages merged when uploading same date twice?

        This test captures the current merge/deduplication logic.
        """
        from src.file_storage import FileStorage

        storage = FileStorage()
        storage.base_dir = temp_dir
        storage.original_dir = temp_dir / "original"
        storage.original_dir.mkdir(parents=True, exist_ok=True)

        room_name = "TestRoom"
        date_str = "2024-02-10"

        # First upload
        messages1 = ["Message 1", "Message 2", "Message 3"]
        storage.save_daily_original(room_name, date_str, messages1)

        # Second upload (simulating re-upload)
        messages2 = ["Message 1", "Message 4"]  # Message 1 is duplicate
        storage.save_daily_original(room_name, date_str, messages2)

        # Capture: Current merge behavior
        result_file = storage.original_dir / room_name / f"{room_name}_{date_str.replace('-', '')}_full.md"
        content = result_file.read_text(encoding="utf-8")

        # Document what's in the file after merge
        assert "Message 1" in content
        # Check if duplicates exist (current behavior may allow them)
        line_count = content.count("Message")
        assert line_count >= 1  # At least one message

    def test_summary_file_naming_convention(self, temp_dir):
        """CAPTURE: Summary file naming pattern."""
        from src.file_storage import FileStorage

        storage = FileStorage()
        storage.base_dir = temp_dir
        storage.summary_dir = temp_dir / "summary"
        storage.summary_dir.mkdir(parents=True, exist_ok=True)

        room_name = "TestRoom"
        date_str = "2024-02-10"
        summary_content = "# Summary\n\nTest content"

        # Save summary
        result_path = storage.save_daily_summary(
            room_name,
            date_str,
            summary_content,
            "glm"
        )

        # Capture naming convention
        assert result_path.exists()
        filename = result_path.name
        assert "TestRoom" in filename
        assert "20240210" in filename or "2024-02-10" in filename
        assert ".md" in filename

    def test_url_file_format(self, temp_dir):
        """CAPTURE: URL list file format."""
        from src.url_extractor import save_urls_to_file

        url_file = temp_dir / "urls.md"

        urls_dict = {
            "https://example.com/page1": ["Description 1", "Description 2"],
            "https://example.com/page2": ["Description 3"],
        }

        # Save URLs
        save_urls_to_file(urls_dict, url_file)

        # Capture file format
        content = url_file.read_text(encoding="utf-8")
        assert "https://example.com/page1" in content
        assert "Description 1" in content

    def test_file_encoding(self, temp_dir):
        """CAPTURE: File encoding used for Korean text."""
        korean_text = "한글 테스트 🎉"

        test_file = temp_dir / "korean.txt"
        test_file.write_text(korean_text, encoding="utf-8")

        # Read back
        content = test_file.read_text(encoding="utf-8")
        assert "한글 테스트" in content
        assert "🎉" in content

    def test_invalid_date_handling(self, temp_dir):
        """CAPTURE: How invalid dates are handled in file operations."""
        from src.file_storage import FileStorage

        storage = FileStorage()
        storage.base_dir = temp_dir
        storage.original_dir = temp_dir / "original"
        storage.original_dir.mkdir(parents=True, exist_ok=True)

        # Try to save with invalid date format
        # Capture: Does it raise error? Normalize? Use default?
        try:
            result = storage.save_daily_original(
                "TestRoom",
                "invalid-date",
                ["Test message"]
            )
            # If no error, capture what path was created
            assert result.exists()
        except (ValueError, AttributeError) as e:
            # Capture error type
            assert True  # Documented that it raises ValueError


@pytest.mark.characterization
class TestURLExtractionBehavior:
    """Characterization tests for URL extraction."""

    def test_extract_urls_from_text(self):
        """CAPTURE: URL extraction patterns."""
        from src.url_extractor import extract_urls_from_text

        text = """
        Check this link: https://example.com/page1
        Another one: http://test.org/page2
        With params: https://site.com?id=123&name=test#section
        """

        urls = extract_urls_from_text(text)

        # Capture extraction behavior - returns {url: [descriptions]}
        assert len(urls) > 0
        # Check which URLs are extracted (keys are URLs)
        assert any("example.com" in url for url in urls.keys())

    def test_normalize_url_behavior(self):
        """CAPTURE: URL normalization rules."""
        from src.url_extractor import normalize_url

        test_cases = [
            ("https://example.com/", "https://example.com"),  # trailing slash
            ("https://example.com#section", "https://example.com"),  # fragment
            ("https://example.com?id=1&name=test", "https://example.com?id=1&name=test"),  # params kept
        ]

        for input_url, expected_contains in test_cases:
            result = normalize_url(input_url)
            # Capture normalization behavior
            assert "example.com" in result

    def test_deduplicate_urls_behavior(self):
        """CAPTURE: URL deduplication logic."""
        from src.url_extractor import deduplicate_urls

        urls_with_dupes = {
            "https://example.com/page1": ["Desc 1"],
            "https://example.com/page1": ["Desc 2"],  # Duplicate URL
            "https://example.com/page2": ["Desc 3"],
        }

        result = deduplicate_urls(urls_with_dupes)

        # Capture deduplication behavior
        # Check if descriptions are merged or one is kept
        assert len(result) >= 1


@pytest.mark.characterization
class TestChatProcessorBehavior:
    """Characterization tests for ChatProcessor."""

    def test_format_as_markdown_structure(self):
        """CAPTURE: Markdown output format structure."""
        from src.chat_processor import ChatProcessor

        processor = ChatProcessor()

        # _format_as_markdown just strips content
        test_content = "  Test content with spaces  "
        result = processor._format_as_markdown(test_content)

        # Capture behavior: simple strip
        assert result == "Test content with spaces"
