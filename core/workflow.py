"""
Workflow helpers for the creator-focused main window UI.
"""
from __future__ import annotations

from typing import Optional

from core.export_recipe import legacy_processing_mode_to_recipe_state
from core.processing_modes import (
    PROCESSING_MODE_BLUR,
    PROCESSING_MODE_LOGO,
    PROCESSING_MODE_ZOOM,
)

AREA_CLEANUP_OPTION_NONE = "None"
AREA_CLEANUP_OPTIONS = (
    AREA_CLEANUP_OPTION_NONE,
    PROCESSING_MODE_BLUR,
    PROCESSING_MODE_LOGO,
)


def derive_processing_mode(
    area_cleanup_mode: str,
    apply_zoom_crop: bool,
) -> Optional[str]:
    """Translate the simplified UI state into the existing export mode model."""
    if apply_zoom_crop:
        return PROCESSING_MODE_ZOOM
    if area_cleanup_mode in {PROCESSING_MODE_BLUR, PROCESSING_MODE_LOGO}:
        return area_cleanup_mode
    return None


def workflow_state_from_processing_mode(processing_mode: Optional[str]) -> tuple[str, bool]:
    """Map a stored preset/settings mode back into the simplified UI controls."""
    area_cleanup_enabled, cleanup_type, zoom_enabled = (
        legacy_processing_mode_to_recipe_state(processing_mode)
    )
    if not area_cleanup_enabled:
        return AREA_CLEANUP_OPTION_NONE, zoom_enabled
    return cleanup_type, zoom_enabled


def build_workflow_hint(
    video_count: int,
    has_selection: bool,
    processing_mode: Optional[str],
    has_output_directory: bool,
    is_exporting: bool = False,
    recipe_enabled: Optional[bool] = None,
    area_cleanup_enabled: Optional[bool] = None,
) -> str:
    """Return a compact guided-workflow hint for the right panel."""
    base_hint = "1. Add videos -> 2. Draw area -> 3. Choose options -> 4. Export"
    if recipe_enabled is None:
        recipe_enabled = processing_mode is not None
    if area_cleanup_enabled is None:
        area_cleanup_enabled = processing_mode in {PROCESSING_MODE_BLUR, PROCESSING_MODE_LOGO}

    if is_exporting:
        return f"{base_hint}\nExport in progress..."
    if video_count <= 0:
        return f"{base_hint}\nNext: add one or more videos."
    if area_cleanup_enabled and not has_selection:
        return f"{base_hint}\nNext: draw the logo/watermark area on the preview."
    if not recipe_enabled:
        return f"{base_hint}\nNext: enable area cleanup, zoom/crop, or output size."
    if not has_output_directory:
        return f"{base_hint}\nNext: choose an output folder."
    return f"{base_hint}\nReady to export."


def format_playback_time(seconds: float) -> str:
    """Return a user-friendly playback timestamp."""
    safe_seconds = max(0, int(seconds))
    hours, remainder = divmod(safe_seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


def frame_index_for_time(
    target_time_seconds: float,
    fps: float,
    frame_count: int,
) -> int:
    """Convert a playback time to a safe frame index."""
    safe_frame_count = max(1, int(frame_count))
    safe_fps = fps if fps and fps > 0 else 30.0
    frame_index = int(max(target_time_seconds, 0.0) * safe_fps)
    return min(frame_index, safe_frame_count - 1)


def playback_interval_ms(fps: float) -> int:
    """Return a practical QTimer interval for the current video FPS."""
    safe_fps = fps if fps and fps > 0 else 30.0
    return max(15, int(round(1000.0 / safe_fps)))
