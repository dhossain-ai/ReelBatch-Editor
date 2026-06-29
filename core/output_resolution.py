"""
Shared output-resolution helpers for export standardization.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

OUTPUT_RESOLUTION_KEEP_ORIGINAL = "Keep original"
OUTPUT_RESOLUTION_720X1280 = "720x1280"
OUTPUT_RESOLUTION_1080X1920 = "1080x1920"
OUTPUT_RESOLUTION_1440X2560 = "1440x2560"
OUTPUT_RESOLUTION_CUSTOM = "Custom"

OUTPUT_RESOLUTION_OPTIONS = (
    OUTPUT_RESOLUTION_KEEP_ORIGINAL,
    OUTPUT_RESOLUTION_720X1280,
    OUTPUT_RESOLUTION_1080X1920,
    OUTPUT_RESOLUTION_1440X2560,
    OUTPUT_RESOLUTION_CUSTOM,
)

DEFAULT_OUTPUT_RESOLUTION = OUTPUT_RESOLUTION_1080X1920

RESIZE_MODE_FILL_AND_CROP = "Fill & Crop"
RESIZE_MODE_FIT_WITH_PADDING = "Fit with Padding"

RESIZE_MODE_OPTIONS = (
    RESIZE_MODE_FILL_AND_CROP,
    RESIZE_MODE_FIT_WITH_PADDING,
)

DEFAULT_RESIZE_MODE = RESIZE_MODE_FILL_AND_CROP

PRESET_OUTPUT_RESOLUTIONS = {
    OUTPUT_RESOLUTION_720X1280: (720, 1280),
    OUTPUT_RESOLUTION_1080X1920: (1080, 1920),
    OUTPUT_RESOLUTION_1440X2560: (1440, 2560),
}


@dataclass(frozen=True)
class OutputStandardization:
    """Resolved export-standardization settings for one export run."""

    target_width: int
    target_height: int
    resize_mode: str
    source_label: str

    @property
    def resolution_suffix(self) -> str:
        return f"{self.target_width}x{self.target_height}"


def is_positive_even(value: int) -> bool:
    """Return True when the value is a positive even integer."""
    return int(value) > 0 and int(value) % 2 == 0


def validate_output_resolution(
    output_resolution: str,
    custom_width: Optional[int] = None,
    custom_height: Optional[int] = None,
) -> Optional[str]:
    """Return a user-facing validation message, or None when valid."""
    try:
        resolve_output_resolution_dimensions(
            output_resolution,
            custom_width=custom_width,
            custom_height=custom_height,
        )
    except ValueError as exc:
        return str(exc)
    return None


def resolve_output_resolution_dimensions(
    output_resolution: str,
    custom_width: Optional[int] = None,
    custom_height: Optional[int] = None,
) -> Optional[tuple[int, int]]:
    """Resolve the selected output-resolution choice into target dimensions."""
    if output_resolution == OUTPUT_RESOLUTION_KEEP_ORIGINAL:
        return None

    if output_resolution in PRESET_OUTPUT_RESOLUTIONS:
        return PRESET_OUTPUT_RESOLUTIONS[output_resolution]

    if output_resolution == OUTPUT_RESOLUTION_CUSTOM:
        if custom_width is None or custom_height is None:
            raise ValueError("Custom output resolution requires both width and height.")
        if not is_positive_even(custom_width) or not is_positive_even(custom_height):
            raise ValueError("Custom width and height must be positive even numbers.")
        return int(custom_width), int(custom_height)

    raise ValueError(f"Unsupported output resolution: {output_resolution}")


def build_output_standardization(
    output_resolution: str,
    resize_mode: str,
    custom_width: Optional[int] = None,
    custom_height: Optional[int] = None,
) -> Optional[OutputStandardization]:
    """Return resolved standardization settings, or None for Keep original."""
    dimensions = resolve_output_resolution_dimensions(
        output_resolution,
        custom_width=custom_width,
        custom_height=custom_height,
    )
    if dimensions is None:
        return None

    if resize_mode not in RESIZE_MODE_OPTIONS:
        raise ValueError(f"Unsupported resize mode: {resize_mode}")

    return OutputStandardization(
        target_width=dimensions[0],
        target_height=dimensions[1],
        resize_mode=resize_mode,
        source_label=output_resolution,
    )
