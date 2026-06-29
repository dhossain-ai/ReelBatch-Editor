from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from core.processing_modes import (
    PROCESSING_MODE_BLUR,
    PROCESSING_MODE_LOGO,
    PROCESSING_MODE_ZOOM,
    validate_export_request,
)
from core.selection import NormalizedSelection


class ExportValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.selection = NormalizedSelection(
            x_percent=80.0,
            y_percent=5.0,
            width_percent=15.0,
            height_percent=10.0,
        )

    def test_blur_mode_requires_selection(self):
        error = validate_export_request(
            mode=PROCESSING_MODE_BLUR,
            videos=["video.mp4"],
            output_directory=Path("exports"),
            selection=None,
            overlay_image_path=None,
        )

        self.assertEqual(error, "Draw a valid rectangle selection before exporting.")

    def test_logo_mode_requires_selected_image(self):
        error = validate_export_request(
            mode=PROCESSING_MODE_LOGO,
            videos=["video.mp4"],
            output_directory=Path("exports"),
            selection=self.selection,
            overlay_image_path=None,
        )

        self.assertEqual(
            error,
            "Select a logo/image before exporting in 'Cover with logo/image' mode.",
        )

    def test_logo_mode_rejects_unsupported_image_extensions(self):
        with TemporaryDirectory() as temp_dir:
            image_path = Path(temp_dir) / "brand.gif"
            image_path.touch()

            error = validate_export_request(
                mode=PROCESSING_MODE_LOGO,
                videos=["video.mp4"],
                output_directory=Path(temp_dir),
                selection=self.selection,
                overlay_image_path=image_path,
            )

        self.assertEqual(
            error,
            "Logo/image files must use .png, .jpg, .jpeg, or .webp.",
        )

    def test_zoom_mode_does_not_require_selection(self):
        error = validate_export_request(
            mode=PROCESSING_MODE_ZOOM,
            videos=["video.mp4"],
            output_directory=Path("exports"),
            selection=None,
            overlay_image_path=None,
        )

        self.assertIsNone(error)


if __name__ == "__main__":
    unittest.main()
