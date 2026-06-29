"""
Selection data model and preview coordinate helpers.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Optional


def clamp(value: float, minimum: float, maximum: float) -> float:
    """Clamp a float between a minimum and maximum value."""
    return max(minimum, min(value, maximum))


@dataclass(frozen=True)
class FloatRect:
    """Simple float rectangle used for testable preview math."""

    x: float
    y: float
    width: float
    height: float

    @property
    def left(self) -> float:
        return self.x

    @property
    def top(self) -> float:
        return self.y

    @property
    def right(self) -> float:
        return self.x + self.width

    @property
    def bottom(self) -> float:
        return self.y + self.height


@dataclass(frozen=True)
class NormalizedSelection:
    """Selection stored as percentages of the original video dimensions."""

    x_percent: float
    y_percent: float
    width_percent: float
    height_percent: float

    def clamped(self) -> "NormalizedSelection":
        """Return a safely clamped copy with all values in the 0-100 range."""
        x_percent = clamp(self.x_percent, 0.0, 100.0)
        y_percent = clamp(self.y_percent, 0.0, 100.0)
        width_percent = clamp(self.width_percent, 0.0, 100.0 - x_percent)
        height_percent = clamp(self.height_percent, 0.0, 100.0 - y_percent)
        return NormalizedSelection(
            x_percent=x_percent,
            y_percent=y_percent,
            width_percent=width_percent,
            height_percent=height_percent,
        )

    def to_dict(self) -> dict[str, float]:
        """Return a JSON-friendly dictionary representation."""
        selection = self.clamped()
        return {
            "x_percent": selection.x_percent,
            "y_percent": selection.y_percent,
            "width_percent": selection.width_percent,
            "height_percent": selection.height_percent,
        }

    @classmethod
    def from_mapping(
        cls, selection: Optional[Mapping[str, float]]
    ) -> Optional["NormalizedSelection"]:
        """Create a normalized selection from a mapping or return None."""
        if selection is None:
            return None

        return cls(
            x_percent=float(selection["x_percent"]),
            y_percent=float(selection["y_percent"]),
            width_percent=float(selection["width_percent"]),
            height_percent=float(selection["height_percent"]),
        ).clamped()


@dataclass(frozen=True)
class PixelSelection:
    """Selection stored as integer video pixel coordinates."""

    x: int
    y: int
    width: int
    height: int


def fit_rect_within_bounds(
    content_width: float,
    content_height: float,
    bounds_width: float,
    bounds_height: float,
    padding: float = 10.0,
    allow_upscale: bool = False,
) -> FloatRect:
    """Fit content inside bounds while preserving aspect ratio."""
    if content_width <= 0 or content_height <= 0 or bounds_width <= 0 or bounds_height <= 0:
        return FloatRect(0.0, 0.0, 0.0, 0.0)

    available_width = max(bounds_width - (padding * 2.0), 1.0)
    available_height = max(bounds_height - (padding * 2.0), 1.0)

    scale = min(available_width / content_width, available_height / content_height)
    if not allow_upscale:
        scale = min(scale, 1.0)

    fitted_width = content_width * scale
    fitted_height = content_height * scale
    x = (bounds_width - fitted_width) / 2.0
    y = (bounds_height - fitted_height) / 2.0
    return FloatRect(x=x, y=y, width=fitted_width, height=fitted_height)


def clamp_point_to_rect(x: float, y: float, rect: FloatRect) -> tuple[float, float]:
    """Clamp a point to the inside of a rectangle."""
    return (
        clamp(x, rect.left, rect.right),
        clamp(y, rect.top, rect.bottom),
    )


def rect_from_drag(
    start_x: float,
    start_y: float,
    end_x: float,
    end_y: float,
    bounds: FloatRect,
) -> FloatRect:
    """Create a rectangle from a drag gesture clamped to the image bounds."""
    clamped_start_x, clamped_start_y = clamp_point_to_rect(start_x, start_y, bounds)
    clamped_end_x, clamped_end_y = clamp_point_to_rect(end_x, end_y, bounds)

    left = min(clamped_start_x, clamped_end_x)
    top = min(clamped_start_y, clamped_end_y)
    right = max(clamped_start_x, clamped_end_x)
    bottom = max(clamped_start_y, clamped_end_y)
    return FloatRect(x=left, y=top, width=right - left, height=bottom - top)


def rect_meets_minimum_size(
    rect: FloatRect,
    minimum_width: float = 5.0,
    minimum_height: float = 5.0,
) -> bool:
    """Return True when the rectangle is large enough to keep."""
    return rect.width >= minimum_width and rect.height >= minimum_height


def normalized_selection_from_display_rect(
    selection_rect: FloatRect,
    image_rect: FloatRect,
) -> NormalizedSelection:
    """Convert a display-space selection to normalized video coordinates."""
    if image_rect.width <= 0 or image_rect.height <= 0:
        return NormalizedSelection(0.0, 0.0, 0.0, 0.0)

    selection = NormalizedSelection(
        x_percent=((selection_rect.x - image_rect.x) / image_rect.width) * 100.0,
        y_percent=((selection_rect.y - image_rect.y) / image_rect.height) * 100.0,
        width_percent=(selection_rect.width / image_rect.width) * 100.0,
        height_percent=(selection_rect.height / image_rect.height) * 100.0,
    )
    return selection.clamped()


def display_rect_from_normalized_selection(
    selection: NormalizedSelection,
    image_rect: FloatRect,
) -> FloatRect:
    """Project a normalized selection back into display-space coordinates."""
    normalized = selection.clamped()
    return FloatRect(
        x=image_rect.x + (normalized.x_percent / 100.0) * image_rect.width,
        y=image_rect.y + (normalized.y_percent / 100.0) * image_rect.height,
        width=(normalized.width_percent / 100.0) * image_rect.width,
        height=(normalized.height_percent / 100.0) * image_rect.height,
    )


def normalized_selection_to_pixel_rect(
    selection: NormalizedSelection,
    video_width: int,
    video_height: int,
    minimum_size: int = 2,
    prefer_even_dimensions: bool = True,
) -> PixelSelection:
    """Convert a normalized selection to a clamped integer video-space rectangle."""
    if video_width <= 0 or video_height <= 0:
        raise ValueError("Video dimensions must be positive integers.")

    normalized = selection.clamped()
    minimum_size = max(1, int(minimum_size))

    max_x = max(video_width - minimum_size, 0)
    max_y = max(video_height - minimum_size, 0)
    x = min(max(int(round((normalized.x_percent / 100.0) * video_width)), 0), max_x)
    y = min(max(int(round((normalized.y_percent / 100.0) * video_height)), 0), max_y)

    available_width = max(video_width - x, 1)
    available_height = max(video_height - y, 1)
    width = _normalize_crop_dimension(
        value=(normalized.width_percent / 100.0) * video_width,
        available=available_width,
        minimum_size=minimum_size,
        prefer_even_dimensions=prefer_even_dimensions,
    )
    height = _normalize_crop_dimension(
        value=(normalized.height_percent / 100.0) * video_height,
        available=available_height,
        minimum_size=minimum_size,
        prefer_even_dimensions=prefer_even_dimensions,
    )

    if x + width > video_width:
        x = max(video_width - width, 0)
    if y + height > video_height:
        y = max(video_height - height, 0)

    return PixelSelection(x=x, y=y, width=width, height=height)


def _normalize_crop_dimension(
    value: float,
    available: int,
    minimum_size: int,
    prefer_even_dimensions: bool,
) -> int:
    """Clamp a crop width/height to valid video bounds."""
    available = max(1, int(available))
    minimum = min(max(1, int(minimum_size)), available)
    dimension = int(round(value))
    dimension = max(minimum, min(dimension, available))

    if prefer_even_dimensions and available >= 2 and dimension % 2 != 0:
        if dimension < available:
            dimension += 1
        else:
            dimension -= 1
            if dimension < minimum:
                dimension = available if available % 2 == 0 else available - 1

    if dimension <= 0:
        return 1
    return min(dimension, available)
