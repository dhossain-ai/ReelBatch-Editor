from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from core.app_settings import AppSettings, AppSettingsStore
from core.output_resolution import DEFAULT_OUTPUT_RESOLUTION, DEFAULT_RESIZE_MODE


class AppSettingsStoreTests(unittest.TestCase):
    def test_load_returns_defaults_when_file_missing(self):
        with TemporaryDirectory() as temp_dir:
            store = AppSettingsStore(Path(temp_dir) / "settings.json")
            settings = store.load()

        self.assertEqual(settings.last_zoom_percentage, 110)
        self.assertEqual(settings.last_blur_strength, 10)
        self.assertEqual(settings.last_output_quality, "Balanced")
        self.assertFalse(settings.area_cleanup_enabled)
        self.assertFalse(settings.zoom_enabled)
        self.assertFalse(settings.output_standardization_enabled)
        self.assertEqual(settings.last_output_resolution, DEFAULT_OUTPUT_RESOLUTION)
        self.assertEqual(settings.last_resize_mode, DEFAULT_RESIZE_MODE)
        self.assertEqual(settings.last_custom_output_width, 1080)
        self.assertEqual(settings.last_custom_output_height, 1920)

    def test_save_and_load_round_trip(self):
        expected = AppSettings(
            last_output_folder="C:/exports",
            last_encoder_selection="CPU - libx264",
            last_processing_mode="Zoom/crop",
            area_cleanup_enabled=True,
            cleanup_type="Cover with logo/image",
            zoom_enabled=True,
            last_zoom_percentage=124,
            last_blur_strength=7,
            last_output_quality="High Quality",
            output_standardization_enabled=True,
            last_output_resolution="1440x2560",
            last_resize_mode="Fit with Padding",
            last_custom_output_width=864,
            last_custom_output_height=1536,
        )

        with TemporaryDirectory() as temp_dir:
            store = AppSettingsStore(Path(temp_dir) / "settings.json")
            store.save(expected)
            loaded = store.load()

        self.assertEqual(loaded, expected)

    def test_load_legacy_processing_mode_infers_new_toggle_fields(self):
        legacy_payload = {
            "last_processing_mode": "Blur selected area",
            "last_output_resolution": "1080x1920",
        }

        with TemporaryDirectory() as temp_dir:
            settings_path = Path(temp_dir) / "settings.json"
            settings_path.write_text(json.dumps(legacy_payload), encoding="utf-8")
            store = AppSettingsStore(settings_path)
            loaded = store.load()

        self.assertTrue(loaded.area_cleanup_enabled)
        self.assertEqual(loaded.cleanup_type, "Blur selected area")
        self.assertFalse(loaded.zoom_enabled)
        self.assertTrue(loaded.output_standardization_enabled)


if __name__ == "__main__":
    unittest.main()
