from __future__ import annotations

import unittest

from core.selection import (
    FloatRect,
    NormalizedSelection,
    clamp_point_to_rect,
    display_rect_from_normalized_selection,
    fit_rect_within_bounds,
    normalized_selection_from_display_rect,
    rect_from_drag,
)


class SelectionMathTests(unittest.TestCase):
    def test_vertical_video_fit_with_letterboxing(self):
        image_rect = fit_rect_within_bounds(
            content_width=1080,
            content_height=1920,
            bounds_width=800,
            bounds_height=600,
        )

        self.assertAlmostEqual(image_rect.width, 326.25)
        self.assertAlmostEqual(image_rect.height, 580.0)
        self.assertAlmostEqual(image_rect.x, 236.875)
        self.assertAlmostEqual(image_rect.y, 10.0)

    def test_top_right_selection_maps_to_expected_percentages(self):
        image_rect = fit_rect_within_bounds(
            content_width=1080,
            content_height=1920,
            bounds_width=800,
            bounds_height=600,
        )
        selection_rect = FloatRect(
            x=image_rect.x + (900.0 / 1080.0) * image_rect.width,
            y=image_rect.y + (40.0 / 1920.0) * image_rect.height,
            width=(140.0 / 1080.0) * image_rect.width,
            height=(120.0 / 1920.0) * image_rect.height,
        )

        selection = normalized_selection_from_display_rect(selection_rect, image_rect)

        self.assertAlmostEqual(selection.x_percent, 83.333333, places=4)
        self.assertAlmostEqual(selection.y_percent, 2.083333, places=4)
        self.assertAlmostEqual(selection.width_percent, 12.962963, places=4)
        self.assertAlmostEqual(selection.height_percent, 6.25, places=4)

    def test_drag_outside_image_bounds_is_clamped_safely(self):
        image_rect = FloatRect(x=236.875, y=10.0, width=326.25, height=580.0)

        selection_rect = rect_from_drag(
            start_x=image_rect.right - 30.0,
            start_y=image_rect.top - 50.0,
            end_x=image_rect.right + 80.0,
            end_y=image_rect.top + 40.0,
            bounds=image_rect,
        )
        selection = normalized_selection_from_display_rect(selection_rect, image_rect)

        self.assertAlmostEqual(selection.x_percent, 90.804598, places=4)
        self.assertAlmostEqual(selection.y_percent, 0.0, places=4)
        self.assertAlmostEqual(selection.width_percent, 9.195402, places=4)
        self.assertAlmostEqual(selection.height_percent, 6.896552, places=4)

    def test_projection_back_to_display_rect_preserves_selection(self):
        image_rect = FloatRect(x=236.875, y=10.0, width=326.25, height=580.0)
        selection = NormalizedSelection(
            x_percent=83.333333,
            y_percent=2.083333,
            width_percent=12.962963,
            height_percent=6.25,
        )

        display_rect = display_rect_from_normalized_selection(selection, image_rect)

        self.assertAlmostEqual(display_rect.x, 508.75, places=2)
        self.assertAlmostEqual(display_rect.y, 22.08333, places=2)
        self.assertAlmostEqual(display_rect.width, 42.29167, places=2)
        self.assertAlmostEqual(display_rect.height, 36.25, places=2)

    def test_clamp_point_to_rect_limits_coordinates(self):
        image_rect = FloatRect(x=100.0, y=50.0, width=200.0, height=400.0)

        self.assertEqual(clamp_point_to_rect(90.0, 40.0, image_rect), (100.0, 50.0))
        self.assertEqual(clamp_point_to_rect(320.0, 500.0, image_rect), (300.0, 450.0))


if __name__ == "__main__":
    unittest.main()
