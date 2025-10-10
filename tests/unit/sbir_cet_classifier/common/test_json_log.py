"""Unit tests for JSON log manager."""

import json
from pathlib import Path

import pytest

from sbir_cet_classifier.common.json_log import JsonLogManager


class TestJsonLogManagerInit:
    """Test JsonLogManager initialization."""

    def test_init_creates_parent_directory(self, tmp_path: Path):
        """Test that parent directories are created."""
        log_path = tmp_path / "subdir" / "logs" / "test.json"
        manager = JsonLogManager(log_path, "entries")

        assert log_path.parent.exists()
        assert manager.log_path == log_path
        assert manager.key == "entries"

    def test_init_with_existing_directory(self, tmp_path: Path):
        """Test initialization when directory already exists."""
        log_path = tmp_path / "test.json"
        manager = JsonLogManager(log_path, "runs")

        assert manager.log_path == log_path
        assert manager.key == "runs"


class TestAppend:
    """Test appending entries to the log."""

    def test_append_to_new_file(self, tmp_path: Path):
        """Test appending to a new log file creates the structure."""
        log_path = tmp_path / "test.json"
        manager = JsonLogManager(log_path, "events")

        entry = {"timestamp": "2024-01-01", "status": "success"}
        manager.append(entry)

        assert log_path.exists()
        data = json.loads(log_path.read_text())
        assert "events" in data
        assert data["events"] == [entry]

    def test_append_to_existing_file(self, tmp_path: Path):
        """Test appending to existing log file."""
        log_path = tmp_path / "test.json"
        manager = JsonLogManager(log_path, "runs")

        # First append
        manager.append({"id": 1})
        # Second append
        manager.append({"id": 2})

        data = json.loads(log_path.read_text())
        assert len(data["runs"]) == 2
        assert data["runs"][0] == {"id": 1}
        assert data["runs"][1] == {"id": 2}

    def test_append_multiple_entries(self, tmp_path: Path):
        """Test appending multiple entries maintains order."""
        log_path = tmp_path / "test.json"
        manager = JsonLogManager(log_path, "items")

        entries = [
            {"value": "a"},
            {"value": "b"},
            {"value": "c"},
        ]

        for entry in entries:
            manager.append(entry)

        data = json.loads(log_path.read_text())
        assert data["items"] == entries

    def test_append_with_complex_entry(self, tmp_path: Path):
        """Test appending complex nested structures."""
        log_path = tmp_path / "test.json"
        manager = JsonLogManager(log_path, "complex")

        entry = {
            "timestamp": "2024-01-01T00:00:00Z",
            "metadata": {
                "user": "test",
                "tags": ["a", "b", "c"]
            },
            "count": 42
        }

        manager.append(entry)

        data = json.loads(log_path.read_text())
        assert data["complex"][0] == entry


class TestGetAll:
    """Test retrieving all log entries."""

    def test_get_all_from_nonexistent_file(self, tmp_path: Path):
        """Test get_all returns empty list for nonexistent file."""
        log_path = tmp_path / "nonexistent.json"
        manager = JsonLogManager(log_path, "items")

        assert manager.get_all() == []

    def test_get_all_from_empty_log(self, tmp_path: Path):
        """Test get_all returns empty list for empty log."""
        log_path = tmp_path / "test.json"
        log_path.write_text(json.dumps({"items": []}))

        manager = JsonLogManager(log_path, "items")
        assert manager.get_all() == []

    def test_get_all_with_entries(self, tmp_path: Path):
        """Test get_all returns all entries."""
        log_path = tmp_path / "test.json"
        manager = JsonLogManager(log_path, "runs")

        entries = [{"id": 1}, {"id": 2}, {"id": 3}]
        for entry in entries:
            manager.append(entry)

        assert manager.get_all() == entries

    def test_get_all_with_wrong_key(self, tmp_path: Path):
        """Test get_all returns empty list when key doesn't exist."""
        log_path = tmp_path / "test.json"
        log_path.write_text(json.dumps({"other_key": [{"id": 1}]}))

        manager = JsonLogManager(log_path, "missing_key")
        assert manager.get_all() == []


class TestGetLatest:
    """Test retrieving the most recent entry."""

    def test_get_latest_from_nonexistent_file(self, tmp_path: Path):
        """Test get_latest returns None for nonexistent file."""
        log_path = tmp_path / "nonexistent.json"
        manager = JsonLogManager(log_path, "items")

        assert manager.get_latest() is None

    def test_get_latest_from_empty_log(self, tmp_path: Path):
        """Test get_latest returns None for empty log."""
        log_path = tmp_path / "test.json"
        log_path.write_text(json.dumps({"items": []}))

        manager = JsonLogManager(log_path, "items")
        assert manager.get_latest() is None

    def test_get_latest_with_single_entry(self, tmp_path: Path):
        """Test get_latest returns the only entry."""
        log_path = tmp_path / "test.json"
        manager = JsonLogManager(log_path, "runs")

        entry = {"timestamp": "2024-01-01"}
        manager.append(entry)

        assert manager.get_latest() == entry

    def test_get_latest_with_multiple_entries(self, tmp_path: Path):
        """Test get_latest returns most recent entry."""
        log_path = tmp_path / "test.json"
        manager = JsonLogManager(log_path, "runs")

        manager.append({"id": 1, "time": "10:00"})
        manager.append({"id": 2, "time": "11:00"})
        manager.append({"id": 3, "time": "12:00"})

        latest = manager.get_latest()
        assert latest == {"id": 3, "time": "12:00"}


class TestClear:
    """Test clearing the log."""

    def test_clear_creates_empty_structure(self, tmp_path: Path):
        """Test clear creates empty log structure."""
        log_path = tmp_path / "test.json"
        manager = JsonLogManager(log_path, "items")

        # Add some entries
        manager.append({"id": 1})
        manager.append({"id": 2})

        # Clear the log
        manager.clear()

        assert log_path.exists()
        data = json.loads(log_path.read_text())
        assert data == {"items": []}
        assert manager.get_all() == []

    def test_clear_on_new_file(self, tmp_path: Path):
        """Test clear works on non-existent file."""
        log_path = tmp_path / "test.json"
        manager = JsonLogManager(log_path, "runs")

        manager.clear()

        assert log_path.exists()
        data = json.loads(log_path.read_text())
        assert data == {"runs": []}


class TestJsonFormatting:
    """Test JSON file formatting."""

    def test_append_creates_formatted_json(self, tmp_path: Path):
        """Test that appended JSON is formatted with indentation."""
        log_path = tmp_path / "test.json"
        manager = JsonLogManager(log_path, "items")

        manager.append({"key": "value"})

        content = log_path.read_text()
        # Check for indentation (formatted JSON)
        assert "\n" in content
        assert "  " in content  # 2-space indentation
