from __future__ import annotations

import unittest
from pathlib import Path

from core.export_recipe import ExportRecipe, build_recipe_summary, validate_recipe_export_request
from core.selection import NormalizedSelection


class ExportRecipeTests(unittest.TestCase):
    def test_all_disabled_recipe_validation_blocks_export(self):
        recipe = ExportRecipe()

        error = validate_recipe_export_request(
            recipe=recipe,
            videos=["video.mp4"],
            output_directory=Path("exports"),
        )

        self.assertEqual(error, "Enable at least one effect or output option.")

    def test_recipe_summary_reports_missing_blur_area(self):
        recipe = ExportRecipe(
            area_cleanup_enabled=True,
            cleanup_type="Blur selected area",
        )

        summary = build_recipe_summary(recipe, encoder_summary="GPU export")

        self.assertEqual(summary, "Missing: draw an area to blur")

    def test_recipe_summary_reports_output_size_only(self):
        recipe = ExportRecipe(
            output_standardization_enabled=True,
            output_resolution="1080x1920",
            resize_mode="Fill & Crop",
        )

        summary = build_recipe_summary(recipe, encoder_summary="GPU export")

        self.assertEqual(summary, "Will apply: 1080x1920 -> GPU export")

    def test_recipe_summary_reports_logo_zoom_and_output(self):
        recipe = ExportRecipe(
            area_cleanup_enabled=True,
            cleanup_type="Cover with logo/image",
            zoom_enabled=True,
            zoom_percent=108,
            output_standardization_enabled=True,
            output_resolution="1080x1920",
            resize_mode="Fill & Crop",
            selection=NormalizedSelection(80.0, 5.0, 12.0, 8.0),
            overlay_image_path=Path("logo.png"),
        )

        summary = build_recipe_summary(recipe, encoder_summary="GPU export")

        self.assertEqual(
            summary,
            "Will apply: Cover logo -> Zoom 108% -> 1080x1920 -> GPU export",
        )


if __name__ == "__main__":
    unittest.main()
