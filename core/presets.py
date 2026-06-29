"""
JSON-based preset storage for ReelBatch Editor.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from core.app_paths import get_presets_directory, sanitize_filename
from core.output_resolution import DEFAULT_OUTPUT_RESOLUTION, DEFAULT_RESIZE_MODE
from core.selection import NormalizedSelection


@dataclass(frozen=True)
class ExportPreset:
    """Serializable preset for the main export workflow."""

    name: str
    processing_mode: str
    blur_strength: int
    zoom_percentage: int
    encoder_preference: str
    output_quality: str = "Balanced"
    output_resolution: str = DEFAULT_OUTPUT_RESOLUTION
    resize_mode: str = DEFAULT_RESIZE_MODE
    custom_output_width: int = 1080
    custom_output_height: int = 1920
    selection: Optional[NormalizedSelection] = None
    logo_image_path: Optional[str] = None

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-friendly representation of this preset."""
        payload: dict[str, object] = {
            "preset_name": self.name,
            "processing_mode": self.processing_mode,
            "blur_strength": int(self.blur_strength),
            "zoom_percentage": int(self.zoom_percentage),
            "encoder_preference": self.encoder_preference,
            "output_quality": self.output_quality,
            "output_resolution": self.output_resolution,
            "resize_mode": self.resize_mode,
            "custom_output_width": int(self.custom_output_width),
            "custom_output_height": int(self.custom_output_height),
        }
        if self.selection is not None:
            payload["selection"] = self.selection.to_dict()
        if self.logo_image_path:
            payload["logo_image_path"] = self.logo_image_path
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "ExportPreset":
        """Build a preset from JSON data."""
        return cls(
            name=str(payload["preset_name"]),
            processing_mode=str(payload["processing_mode"]),
            blur_strength=int(payload["blur_strength"]),
            zoom_percentage=int(payload["zoom_percentage"]),
            encoder_preference=str(payload["encoder_preference"]),
            output_quality=str(payload.get("output_quality", "Balanced")),
            output_resolution=str(payload.get("output_resolution", DEFAULT_OUTPUT_RESOLUTION)),
            resize_mode=str(payload.get("resize_mode", DEFAULT_RESIZE_MODE)),
            custom_output_width=int(payload.get("custom_output_width", 1080)),
            custom_output_height=int(payload.get("custom_output_height", 1920)),
            selection=NormalizedSelection.from_mapping(payload.get("selection")),  # type: ignore[arg-type]
            logo_image_path=(
                str(payload["logo_image_path"])
                if payload.get("logo_image_path")
                else None
            ),
        )


class PresetStore:
    """Load and save presets in the user's app-data directory or arbitrary JSON files."""

    def __init__(self, presets_directory: Optional[Path] = None) -> None:
        self.presets_directory = presets_directory or get_presets_directory()
        self.presets_directory.mkdir(parents=True, exist_ok=True)

    def build_default_preset_path(self, preset_name: str) -> Path:
        """Return the default app-data path for a named preset."""
        safe_name = sanitize_filename(preset_name, fallback="preset")
        return self.presets_directory / f"{safe_name}.json"

    def save_preset(self, preset: ExportPreset) -> Path:
        """Save a preset into the default app-data presets folder."""
        preset_path = self.build_default_preset_path(preset.name)
        self.save_preset_to_path(preset, preset_path)
        return preset_path

    def save_preset_to_path(self, preset: ExportPreset, output_path: Path | str) -> Path:
        """Save a preset JSON file to a specific path."""
        preset_path = Path(output_path)
        preset_path.parent.mkdir(parents=True, exist_ok=True)
        preset_path.write_text(
            json.dumps(preset.to_dict(), indent=2),
            encoding="utf-8",
        )
        return preset_path

    def load_preset(self, preset_path: Path | str) -> ExportPreset:
        """Load a preset JSON file from disk."""
        payload = json.loads(Path(preset_path).read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("Preset JSON must contain an object.")
        return ExportPreset.from_dict(payload)
