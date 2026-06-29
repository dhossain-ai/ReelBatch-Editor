"""
Persistent application settings for ReelBatch Editor.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from core.app_paths import get_settings_file_path
from core.output_resolution import DEFAULT_OUTPUT_RESOLUTION, DEFAULT_RESIZE_MODE


@dataclass(frozen=True)
class AppSettings:
    """Serializable UI settings that should persist across launches."""

    last_output_folder: Optional[str] = None
    last_encoder_selection: str = ""
    last_processing_mode: str = ""
    last_zoom_percentage: int = 110
    last_blur_strength: int = 10
    last_output_quality: str = "Balanced"
    last_output_resolution: str = DEFAULT_OUTPUT_RESOLUTION
    last_resize_mode: str = DEFAULT_RESIZE_MODE
    last_custom_output_width: int = 1080
    last_custom_output_height: int = 1920

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-friendly representation."""
        return {
            "last_output_folder": self.last_output_folder,
            "last_encoder_selection": self.last_encoder_selection,
            "last_processing_mode": self.last_processing_mode,
            "last_zoom_percentage": int(self.last_zoom_percentage),
            "last_blur_strength": int(self.last_blur_strength),
            "last_output_quality": self.last_output_quality,
            "last_output_resolution": self.last_output_resolution,
            "last_resize_mode": self.last_resize_mode,
            "last_custom_output_width": int(self.last_custom_output_width),
            "last_custom_output_height": int(self.last_custom_output_height),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "AppSettings":
        """Build settings from decoded JSON."""
        return cls(
            last_output_folder=(
                str(payload["last_output_folder"])
                if payload.get("last_output_folder")
                else None
            ),
            last_encoder_selection=str(payload.get("last_encoder_selection", "")),
            last_processing_mode=str(payload.get("last_processing_mode", "")),
            last_zoom_percentage=int(payload.get("last_zoom_percentage", 110)),
            last_blur_strength=int(payload.get("last_blur_strength", 10)),
            last_output_quality=str(payload.get("last_output_quality", "Balanced")),
            last_output_resolution=str(
                payload.get("last_output_resolution", DEFAULT_OUTPUT_RESOLUTION)
            ),
            last_resize_mode=str(payload.get("last_resize_mode", DEFAULT_RESIZE_MODE)),
            last_custom_output_width=int(payload.get("last_custom_output_width", 1080)),
            last_custom_output_height=int(payload.get("last_custom_output_height", 1920)),
        )


class AppSettingsStore:
    """Read and write persistent app settings to a JSON file."""

    def __init__(self, settings_path: Optional[Path] = None) -> None:
        self.settings_path = settings_path or get_settings_file_path()

    def load(self) -> AppSettings:
        """Load settings from disk, or return defaults when missing."""
        if not self.settings_path.exists():
            return AppSettings()

        payload = json.loads(self.settings_path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("App settings JSON must contain an object.")
        return AppSettings.from_dict(payload)

    def save(self, settings: AppSettings) -> Path:
        """Persist settings to disk."""
        self.settings_path.parent.mkdir(parents=True, exist_ok=True)
        self.settings_path.write_text(
            json.dumps(settings.to_dict(), indent=2),
            encoding="utf-8",
        )
        return self.settings_path
