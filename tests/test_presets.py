from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from core.presets import ExportPreset, PresetStore
from core.selection import NormalizedSelection


class PresetStoreTests(unittest.TestCase):
    def test_save_and_load_preset_round_trip(self):
        preset = ExportPreset(
            name="Brand Preset",
            processing_mode="Cover with logo/image",
            blur_strength=12,
            zoom_percentage=108,
            encoder_preference="Auto - Prefer NVIDIA NVENC",
            output_quality="High Quality",
            selection=NormalizedSelection(80.0, 5.0, 12.0, 8.0),
            logo_image_path="C:/assets/logo.png",
        )

        with TemporaryDirectory() as temp_dir:
            store = PresetStore(Path(temp_dir))
            saved_path = store.save_preset(preset)
            loaded = store.load_preset(saved_path)

        self.assertEqual(saved_path.name, "Brand_Preset.json")
        self.assertEqual(loaded.name, preset.name)
        self.assertEqual(loaded.processing_mode, preset.processing_mode)
        self.assertEqual(loaded.blur_strength, preset.blur_strength)
        self.assertEqual(loaded.zoom_percentage, preset.zoom_percentage)
        self.assertEqual(loaded.encoder_preference, preset.encoder_preference)
        self.assertEqual(loaded.output_quality, preset.output_quality)
        self.assertEqual(loaded.logo_image_path, preset.logo_image_path)
        self.assertEqual(loaded.selection, preset.selection)

    def test_save_preset_to_explicit_export_path(self):
        preset = ExportPreset(
            name="Zoom Preset",
            processing_mode="Zoom/crop",
            blur_strength=10,
            zoom_percentage=125,
            encoder_preference="CPU - libx264",
        )

        with TemporaryDirectory() as temp_dir:
            store = PresetStore(Path(temp_dir) / "internal")
            export_path = Path(temp_dir) / "exports" / "zoom.json"
            saved_path = store.save_preset_to_path(preset, export_path)
            loaded = store.load_preset(saved_path)

        self.assertEqual(saved_path, export_path)
        self.assertEqual(loaded.name, "Zoom Preset")
        self.assertEqual(loaded.processing_mode, "Zoom/crop")


if __name__ == "__main__":
    unittest.main()
