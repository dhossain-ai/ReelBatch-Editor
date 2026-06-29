"""
Preview Canvas Widget
"""
from __future__ import annotations

from typing import Mapping, Optional

from PySide6.QtCore import QRectF, Qt, Signal
from PySide6.QtGui import QColor, QImage, QMouseEvent, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QWidget

from core.selection import (
    FloatRect,
    NormalizedSelection,
    display_rect_from_normalized_selection,
    fit_rect_within_bounds,
    normalized_selection_from_display_rect,
    rect_from_drag,
    rect_meets_minimum_size,
)


class PreviewCanvas(QWidget):
    """Widget for displaying a video preview and a normalized rectangle selection."""

    selection_changed = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(400, 600)
        self.setStyleSheet("background-color: #1e1e1e; border: 2px dashed #3a3a3a;")

        self._preview_padding = 10.0
        self._minimum_selection_size = 5.0
        self._current_pixmap: Optional[QPixmap] = None
        self._preview_width = 0
        self._preview_height = 0
        self._selection: Optional[NormalizedSelection] = None
        self._drag_start: Optional[tuple[float, float]] = None
        self._drag_current: Optional[tuple[float, float]] = None
        self._is_dragging = False

    def set_preview(
        self,
        image: Optional[QImage],
        video_width: Optional[int] = None,
        video_height: Optional[int] = None,
    ) -> None:
        """Display a preview image and remember its source video dimensions."""
        if image is None:
            self.clear_preview()
            return

        self._current_pixmap = QPixmap.fromImage(image)
        self._preview_width = int(video_width or image.width())
        self._preview_height = int(video_height or image.height())
        self.update()

    def set_preview_image(self, image: Optional[QImage]) -> None:
        """Backward-compatible alias for older callers."""
        self.set_preview(image)

    def clear_preview(self) -> None:
        """Clear the preview image while preserving any saved normalized selection."""
        self._current_pixmap = None
        self._preview_width = 0
        self._preview_height = 0
        self._cancel_drag()
        self.update()

    def clear_selection(self) -> None:
        """Clear the current selection and notify listeners."""
        self._selection = None
        self._cancel_drag()
        self.update()
        self.selection_changed.emit(None)

    def get_normalized_selection(self) -> Optional[dict[str, float]]:
        """Return the current normalized selection as percentages."""
        if self._selection is None:
            return None
        return self._selection.to_dict()

    def set_normalized_selection(
        self,
        selection: Optional[Mapping[str, float] | NormalizedSelection],
    ) -> None:
        """Set the current normalized selection without emitting a change signal."""
        if isinstance(selection, NormalizedSelection):
            self._selection = selection.clamped()
        else:
            self._selection = NormalizedSelection.from_mapping(selection)

        self._cancel_drag()
        self.update()

    def resizeEvent(self, event) -> None:
        """Repaint the preview and overlay when the widget size changes."""
        super().resizeEvent(event)
        self.update()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Start a rectangle selection when the user presses inside the image area."""
        if event.button() != Qt.LeftButton or not self._has_preview():
            super().mousePressEvent(event)
            return

        image_rect = self._get_image_rect()
        if not self._point_in_rect(event.position().x(), event.position().y(), image_rect):
            super().mousePressEvent(event)
            return

        self._is_dragging = True
        self._drag_start = (event.position().x(), event.position().y())
        self._drag_current = self._drag_start
        self.update()
        event.accept()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """Update the active drag rectangle."""
        if not self._is_dragging or self._drag_start is None:
            super().mouseMoveEvent(event)
            return

        image_rect = self._get_image_rect()
        clamped_x = min(max(event.position().x(), image_rect.left), image_rect.right)
        clamped_y = min(max(event.position().y(), image_rect.top), image_rect.bottom)
        self._drag_current = (clamped_x, clamped_y)
        self.update()
        event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        """Finalize the current selection when the drag ends."""
        if event.button() != Qt.LeftButton or not self._is_dragging or self._drag_start is None:
            super().mouseReleaseEvent(event)
            return

        drag_rect = self._get_active_drag_rect(event)
        self._cancel_drag()

        if drag_rect and rect_meets_minimum_size(
            drag_rect,
            minimum_width=self._minimum_selection_size,
            minimum_height=self._minimum_selection_size,
        ):
            self._selection = normalized_selection_from_display_rect(
                drag_rect,
                self._get_image_rect(),
            )
            self.selection_changed.emit(self._selection.to_dict())

        self.update()
        event.accept()

    def paintEvent(self, event) -> None:
        """Draw the preview image and rectangle selection overlay."""
        super().paintEvent(event)

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        if self._has_preview() and self._current_pixmap is not None:
            image_rect = self._get_image_rect()
            target_rect = QRectF(image_rect.x, image_rect.y, image_rect.width, image_rect.height)
            source_rect = QRectF(
                0.0,
                0.0,
                float(self._current_pixmap.width()),
                float(self._current_pixmap.height()),
            )
            painter.drawPixmap(target_rect, self._current_pixmap, source_rect)
        else:
            painter.setPen(QColor("#666666"))
            painter.drawText(self.rect(), Qt.AlignCenter, "Preview will appear here")

        selection_rect = self._get_overlay_rect()
        if selection_rect is not None:
            self._draw_selection_rect(painter, selection_rect)

    def _has_preview(self) -> bool:
        return (
            self._current_pixmap is not None
            and not self._current_pixmap.isNull()
            and self._preview_width > 0
            and self._preview_height > 0
        )

    def _cancel_drag(self) -> None:
        self._is_dragging = False
        self._drag_start = None
        self._drag_current = None

    def _get_image_rect(self) -> FloatRect:
        return fit_rect_within_bounds(
            content_width=float(self._preview_width),
            content_height=float(self._preview_height),
            bounds_width=float(self.width()),
            bounds_height=float(self.height()),
            padding=self._preview_padding,
            allow_upscale=False,
        )

    def _get_active_drag_rect(self, event: Optional[QMouseEvent] = None) -> Optional[FloatRect]:
        if self._drag_start is None:
            return None

        drag_current = self._drag_current
        if event is not None:
            image_rect = self._get_image_rect()
            drag_current = (
                min(max(event.position().x(), image_rect.left), image_rect.right),
                min(max(event.position().y(), image_rect.top), image_rect.bottom),
            )

        if drag_current is None:
            return None

        return rect_from_drag(
            start_x=self._drag_start[0],
            start_y=self._drag_start[1],
            end_x=drag_current[0],
            end_y=drag_current[1],
            bounds=self._get_image_rect(),
        )

    def _get_overlay_rect(self) -> Optional[FloatRect]:
        if self._is_dragging:
            return self._get_active_drag_rect()

        if self._selection is None or not self._has_preview():
            return None

        return display_rect_from_normalized_selection(self._selection, self._get_image_rect())

    def _draw_selection_rect(self, painter: QPainter, rect: FloatRect) -> None:
        if rect.width <= 0 or rect.height <= 0:
            return

        painter.setPen(QPen(QColor("#4ea6ff"), 2))
        painter.setBrush(QColor(0, 120, 215, 70))
        painter.drawRect(QRectF(rect.x, rect.y, rect.width, rect.height))

    @staticmethod
    def _point_in_rect(x: float, y: float, rect: FloatRect) -> bool:
        return rect.left <= x <= rect.right and rect.top <= y <= rect.bottom
