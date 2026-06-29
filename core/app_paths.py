"""
Helpers for user-writable ReelBatch Editor data folders.
"""
from __future__ import annotations

import os
import re
from pathlib import Path

APP_DIRECTORY_NAME = "ReelBatch Editor"


def get_app_data_directory() -> Path:
    """Return the base writable data directory for the application."""
    if os.name == "nt":
        appdata = os.environ.get("APPDATA")
        if appdata:
            return Path(appdata) / APP_DIRECTORY_NAME

    return Path.home() / ".reelbatch-editor"


def ensure_directory(path: Path) -> Path:
    """Create a directory when missing and return it."""
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_presets_directory() -> Path:
    """Return the writable presets directory."""
    return ensure_directory(get_app_data_directory() / "presets")


def get_logs_directory() -> Path:
    """Return the writable logs directory."""
    return ensure_directory(get_app_data_directory() / "logs")


def get_settings_file_path() -> Path:
    """Return the JSON settings file path."""
    ensure_directory(get_app_data_directory())
    return get_app_data_directory() / "settings.json"


def sanitize_filename(value: str, fallback: str = "preset") -> str:
    """Convert a user-facing label to a filesystem-safe filename stem."""
    cleaned = re.sub(r"[^\w\- ]+", "", value).strip().replace(" ", "_")
    return cleaned or fallback
