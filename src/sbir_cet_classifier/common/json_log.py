"""JSON log manager for append-only structured log files."""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional


class JsonLogManager:
    """Manages append-only JSON log files with a consistent structure.

    Provides a simple interface for:
    - Appending entries to a JSON log file
    - Reading all entries from the log
    - Getting the most recent entry

    The log file has the structure:
    {
        "key_name": [
            {"entry": 1},
            {"entry": 2},
            ...
        ]
    }

    Example:
        log = JsonLogManager(
            Path("data/artifacts/backfill_runs.json"),
            "backfill_runs"
        )

        log.append({
            "timestamp": "2024-01-01T00:00:00Z",
            "status": "completed",
            "records_processed": 1000
        })

        latest = log.get_latest()
        all_runs = log.get_all()
    """

    def __init__(self, log_path: Path, key: str):
        """Initialize the JSON log manager.

        Args:
            log_path: Path to the JSON log file
            key: Key name for the array in the JSON structure
        """
        self.log_path = log_path
        self.key = key
        # Ensure directory exists
        log_path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, entry: Dict[str, Any]) -> None:
        """Append an entry to the log file.

        If the file doesn't exist, it will be created with the initial structure.
        If it exists, the entry is appended to the existing array.

        Args:
            entry: Dictionary to append to the log
        """
        if self.log_path.exists():
            data = json.loads(self.log_path.read_text())
        else:
            data = {self.key: []}

        data[self.key].append(entry)
        self.log_path.write_text(json.dumps(data, indent=2))

    def get_all(self) -> List[Dict[str, Any]]:
        """Get all log entries.

        Returns:
            List of all entries in the log, or empty list if file doesn't exist
        """
        if not self.log_path.exists():
            return []

        data = json.loads(self.log_path.read_text())
        return data.get(self.key, [])

    def get_latest(self) -> Optional[Dict[str, Any]]:
        """Get the most recent log entry.

        Returns:
            Most recent entry, or None if log is empty
        """
        entries = self.get_all()
        return entries[-1] if entries else None

    def clear(self) -> None:
        """Clear all entries from the log.

        Resets the log to an empty array structure.
        """
        data = {self.key: []}
        self.log_path.write_text(json.dumps(data, indent=2))
