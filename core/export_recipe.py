"""
Helpers for the toggle-based export recipe workflow.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Sequence

from core.output_resolution import (
    DEFAULT_OUTPUT_RESOLUTION,
    DEFAULT_RESIZE_MODE,
    OUTPUT_RESOLUTION_KEEP_ORIGINAL,
    OutputStandardization,
    build_output_standardization,
    validate_output_resolution,
)
from core.processing_modes import (
    PROCESSING_MODE_BLUR,
    PROCESSING_MODE_LOGO,
    PROCESSING_MODE_ZOOM,
    is_supported_overlay_image,
)
from core.selection import NormalizedSelection

AREA_CLEANUP_TYPE_BLUR = PROCESSING_MODE_BLUR
AREA_CLEANUP_TYPE_LOGO = PROCESSING_MODE_LOGO
AREA_CLEANUP_TYPE_OPTIONS = (
    AREA_CLEANUP_TYPE_BLUR,
    AREA_CLEANUP_TYPE_LOGO,
)


@dataclass(frozen=True)
class ExportRecipe:
    """Serializable export recipe state shared by the UI and worker."""

    area_cleanup_enabled: bool = False
    cleanup_type: str = AREA_CLEANUP_TYPE_BLUR
    blur_strength: int = 10
    zoom_enabled: bool = False
    zoom_percent: int = 110
    output_standardization_enabled: bool = False
    output_resolution: str = DEFAULT_OUTPUT_RESOLUTION
    resize_mode: str = DEFAULT_RESIZE_MODE
    custom_output_width: int = 1080
    custom_output_height: int = 1920
    output_quality: str = "Balanced"
    selection: Optional[NormalizedSelection] = None
    overlay_image_path: Optional[Path] = None

    def has_active_steps(self) -> bool:
        """Return True when at least one transform is enabled."""
        return (
            self.area_cleanup_enabled
            or self.zoom_enabled
            or self.output_standardization_enabled
        )

    def resolved_output_standardization(self) -> Optional[OutputStandardization]:
        """Resolve the output standardization settings when enabled."""
        if not self.output_standardization_enabled:
            return None
        return build_output_standardization(
            self.output_resolution,
            self.resize_mode,
            custom_width=self.custom_output_width,
            custom_height=self.custom_output_height,
        )


def legacy_processing_mode_to_recipe_state(processing_mode: Optional[str]) -> tuple[bool, str, bool]:
    """Map the legacy single-mode workflow to the new toggle-based recipe state."""
    if processing_mode == PROCESSING_MODE_LOGO:
        return True, AREA_CLEANUP_TYPE_LOGO, False
    if processing_mode == PROCESSING_MODE_BLUR:
        return True, AREA_CLEANUP_TYPE_BLUR, False
    if processing_mode == PROCESSING_MODE_ZOOM:
        return False, AREA_CLEANUP_TYPE_BLUR, True
    return False, AREA_CLEANUP_TYPE_BLUR, False


def recipe_state_to_legacy_processing_mode(
    area_cleanup_enabled: bool,
    cleanup_type: str,
    zoom_enabled: bool,
) -> str:
    """Collapse the toggle-based recipe into the best legacy single-mode label."""
    if area_cleanup_enabled:
        if cleanup_type == AREA_CLEANUP_TYPE_LOGO:
            return PROCESSING_MODE_LOGO
        return PROCESSING_MODE_BLUR
    if zoom_enabled:
        return PROCESSING_MODE_ZOOM
    return ""


def validate_recipe_export_request(
    recipe: ExportRecipe,
    videos: Sequence[object],
    output_directory: Optional[Path],
) -> Optional[str]:
    """Return a user-facing validation error, or None when the request is ready."""
    if not videos:
        return "Add at least one video."

    if output_directory is None:
        return "Choose an output folder."

    if not recipe.has_active_steps():
        return "Enable at least one effect or output option."

    if recipe.area_cleanup_enabled:
        if recipe.selection is None:
            if recipe.cleanup_type == AREA_CLEANUP_TYPE_LOGO:
                return "Draw an area to cover."
            return "Draw an area to blur."

        if recipe.cleanup_type == AREA_CLEANUP_TYPE_LOGO:
            if recipe.overlay_image_path is None:
                return "Choose a logo image."
            if not recipe.overlay_image_path.is_file():
                return "The selected logo image could not be found."
            if not is_supported_overlay_image(recipe.overlay_image_path):
                return "Logo/image files must use .png, .jpg, .jpeg, or .webp."

    if recipe.output_standardization_enabled:
        resolution_validation_error = validate_output_resolution(
            recipe.output_resolution,
            custom_width=recipe.custom_output_width,
            custom_height=recipe.custom_output_height,
        )
        if resolution_validation_error:
            return resolution_validation_error

    return None


def build_recipe_summary(recipe: ExportRecipe, encoder_summary: str = "") -> str:
    """Return the compact live recipe summary shown in the right panel."""
    missing_items: list[str] = []
    steps: list[str] = []

    if recipe.area_cleanup_enabled:
        if recipe.cleanup_type == AREA_CLEANUP_TYPE_LOGO:
            steps.append("Cover logo")
            if recipe.selection is None:
                missing_items.append("draw an area to cover")
            if recipe.overlay_image_path is None:
                missing_items.append("choose a logo image")
        else:
            steps.append("Blur area")
            if recipe.selection is None:
                missing_items.append("draw an area to blur")

    if recipe.zoom_enabled:
        steps.append(f"Zoom {recipe.zoom_percent}%")

    if recipe.output_standardization_enabled:
        try:
            standardization = recipe.resolved_output_standardization()
        except ValueError:
            missing_items.append("choose a valid output size")
        else:
            if standardization is not None:
                steps.append(standardization.source_label)

    if missing_items:
        return "Missing: " + " and ".join(missing_items)

    if not steps:
        return "Missing: enable at least one effect or output option"

    if encoder_summary:
        steps.append(encoder_summary)
    return "Will apply: " + " -> ".join(steps)


def build_area_cleanup_status(recipe: ExportRecipe) -> str:
    """Return a short readiness label for the Area Cleanup section."""
    if not recipe.area_cleanup_enabled:
        return "Off"
    if recipe.selection is None:
        return "Missing area"
    if recipe.cleanup_type == AREA_CLEANUP_TYPE_LOGO and recipe.overlay_image_path is None:
        return "Missing logo"
    return "Ready"


def infer_output_standardization_enabled(output_resolution: str, payload: dict[str, object]) -> bool:
    """Infer the new output-size toggle from older stored settings or presets."""
    if "output_standardization_enabled" in payload:
        return bool(payload.get("output_standardization_enabled"))
    return output_resolution != OUTPUT_RESOLUTION_KEEP_ORIGINAL
