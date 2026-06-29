"""
Shared processing mode constants and export validation helpers.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional, Sequence

from core.output_resolution import validate_output_resolution
from core.selection import NormalizedSelection

PROCESSING_MODE_BLUR = "Blur selected area"
PROCESSING_MODE_LOGO = "Cover with logo/image"
PROCESSING_MODE_ZOOM = "Zoom/crop"

PROCESSING_MODES = (
    PROCESSING_MODE_BLUR,
    PROCESSING_MODE_LOGO,
    PROCESSING_MODE_ZOOM,
)

SUPPORTED_OVERLAY_IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp")


def mode_requires_selection(mode: str) -> bool:
    """Return True when the processing mode requires a rectangle selection."""
    return mode in {PROCESSING_MODE_BLUR, PROCESSING_MODE_LOGO}


def mode_requires_overlay_image(mode: str) -> bool:
    """Return True when the processing mode requires a user-selected image file."""
    return mode == PROCESSING_MODE_LOGO


def is_supported_overlay_image(path: Path | str) -> bool:
    """Return True when the selected image file uses a supported extension."""
    return Path(path).suffix.lower() in SUPPORTED_OVERLAY_IMAGE_EXTENSIONS


def validate_export_request(
    mode: str,
    videos: Sequence[object],
    output_directory: Optional[Path],
    selection: Optional[NormalizedSelection],
    overlay_image_path: Optional[Path],
    output_resolution: str = "",
    custom_output_width: Optional[int] = None,
    custom_output_height: Optional[int] = None,
) -> Optional[str]:
    """Return a user-facing validation error, or None when the request is ready."""
    if not videos:
        return "Import at least one video before exporting."

    if output_directory is None:
        return "Select an output folder before exporting."

    if mode not in PROCESSING_MODES:
        return f"Unsupported processing mode: {mode}"

    if mode_requires_selection(mode) and selection is None:
        return "Draw a valid rectangle selection before exporting."

    if mode_requires_overlay_image(mode):
        if overlay_image_path is None:
            return "Select a logo/image before exporting in 'Cover with logo/image' mode."
        if not overlay_image_path.is_file():
            return "The selected logo/image file could not be found."
        if not is_supported_overlay_image(overlay_image_path):
            return "Logo/image files must use .png, .jpg, .jpeg, or .webp."

    if output_resolution:
        resolution_validation_error = validate_output_resolution(
            output_resolution,
            custom_width=custom_output_width,
            custom_height=custom_output_height,
        )
        if resolution_validation_error:
            return resolution_validation_error

    return None


def processing_mode_status_text(mode: str) -> str:
    """Return a short status message describing the active mode requirements."""
    if mode == PROCESSING_MODE_BLUR:
        return "Blur mode ready. Draw a selection and export."
    if mode == PROCESSING_MODE_LOGO:
        return "Logo mode ready. Draw a selection, choose an image, and export."
    if mode == PROCESSING_MODE_ZOOM:
        return "Zoom/crop mode ready. No selection is required."
    return "Select a processing mode."


def processing_mode_progress_label(mode: str) -> str:
    """Return the verb used for per-file progress updates."""
    if mode == PROCESSING_MODE_BLUR:
        return "Blurring"
    if mode == PROCESSING_MODE_LOGO:
        return "Branding"
    if mode == PROCESSING_MODE_ZOOM:
        return "Zooming"
    return "Exporting"
