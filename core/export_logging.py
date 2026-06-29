"""
Simple export logging helpers for ReelBatch Editor.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from core.app_paths import get_logs_directory


def build_export_log_path() -> Path:
    """Create a timestamped log-file path in the user-writable logs folder."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return get_logs_directory() / f"export_{timestamp}.log"


def extract_ffmpeg_error_snippet(log_text: str, max_lines: int = 8, max_chars: int = 1200) -> str:
    """Return a compact FFmpeg log snippet that is small enough for log files."""
    if not log_text.strip():
        return "No FFmpeg output captured."

    lines = [line.strip() for line in log_text.splitlines() if line.strip()]
    snippet = "\n".join(lines[-max_lines:])
    if len(snippet) > max_chars:
        snippet = snippet[-max_chars:]
    return snippet


@dataclass
class ExportLogWriter:
    """Append human-readable export events to one batch log file."""

    log_file_path: Path

    @classmethod
    def create(cls, log_file_path: Optional[Path] = None) -> "ExportLogWriter":
        """Create a writer using the default logs directory when needed."""
        path = log_file_path or build_export_log_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch(exist_ok=True)
        return cls(path)

    def write_line(self, message: str) -> None:
        """Append one timestamped line to the log file."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self.log_file_path.open("a", encoding="utf-8") as handle:
            handle.write(f"[{timestamp}] {message}\n")
