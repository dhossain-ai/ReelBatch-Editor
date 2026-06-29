from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from core.app_settings import AppSettings, AppSettingsStore


class AppSettingsStoreTests(unittest.TestCase):
    def test_load_returns_defaults_when_file_missing(self):
        with TemporaryDirectory() as temp_dir:
            store = AppSettingsStore(Path(temp_dir) / "settings.json")
            settings = store.load()

        self.assertEqual(settings.last_zoom_percentage, 110)
        self.assertEqual(settings.last_blur_strength, 10)
        self.assertEqual(settings.last_output_quality, "Balanced")

    def test_save_and_load_round_trip(self):
        expected = AppSettings(
            last_output_folder="C:/exports",
            last_encoder_selection="CPU - libx264",
            last_processing_mode="Zoom/crop",
            last_zoom_percentage=124,
            last_blur_strength=7,
            last_output_quality="High Quality",
        )

        with TemporaryDirectory() as temp_dir:
            store = AppSettingsStore(Path(temp_dir) / "settings.json")
            store.save(expected)
            loaded = store.load()

        self.assertEqual(loaded, expected)


if __name__ == "__main__":
    unittest.main()
