from __future__ import annotations

import unittest

from core.processing_modes import (
    PROCESSING_MODE_BLUR,
    PROCESSING_MODE_LOGO,
    PROCESSING_MODE_ZOOM,
)
from core.workflow import (
    AREA_CLEANUP_OPTION_NONE,
    build_workflow_hint,
    derive_processing_mode,
    format_playback_time,
    frame_index_for_time,
    playback_interval_ms,
    workflow_state_from_processing_mode,
)


class WorkflowHelperTests(unittest.TestCase):
    def test_area_cleanup_blur_maps_to_existing_blur_mode(self):
        self.assertEqual(
            derive_processing_mode(PROCESSING_MODE_BLUR, apply_zoom_crop=False),
            PROCESSING_MODE_BLUR,
        )

    def test_zoom_checkbox_maps_to_zoom_mode(self):
        self.assertEqual(
            derive_processing_mode(AREA_CLEANUP_OPTION_NONE, apply_zoom_crop=True),
            PROCESSING_MODE_ZOOM,
        )

    def test_no_area_cleanup_and_no_zoom_means_not_ready_to_export(self):
        self.assertIsNone(
            derive_processing_mode(AREA_CLEANUP_OPTION_NONE, apply_zoom_crop=False)
        )

    def test_saved_zoom_mode_restores_none_plus_zoom_checkbox(self):
        area_cleanup_mode, apply_zoom = workflow_state_from_processing_mode(PROCESSING_MODE_ZOOM)

        self.assertEqual(area_cleanup_mode, AREA_CLEANUP_OPTION_NONE)
        self.assertTrue(apply_zoom)

    def test_workflow_hint_points_user_to_selection_for_blur_mode(self):
        hint = build_workflow_hint(
            video_count=2,
            has_selection=False,
            processing_mode=PROCESSING_MODE_BLUR,
            has_output_directory=False,
        )

        self.assertIn("Next: draw the logo/watermark area on the preview.", hint)

    def test_workflow_hint_marks_ready_once_required_state_exists(self):
        hint = build_workflow_hint(
            video_count=3,
            has_selection=True,
            processing_mode=PROCESSING_MODE_LOGO,
            has_output_directory=True,
        )

        self.assertIn("Ready to export.", hint)

    def test_playback_time_formats_hours_when_needed(self):
        self.assertEqual(format_playback_time(5), "0:05")
        self.assertEqual(format_playback_time(75), "1:15")
        self.assertEqual(format_playback_time(3665), "1:01:05")

    def test_frame_index_for_time_clamps_to_last_frame(self):
        self.assertEqual(frame_index_for_time(1.0, fps=30.0, frame_count=120), 30)
        self.assertEqual(frame_index_for_time(10.0, fps=30.0, frame_count=120), 119)

    def test_playback_interval_uses_reasonable_floor(self):
        self.assertEqual(playback_interval_ms(30.0), 33)
        self.assertEqual(playback_interval_ms(0.0), 33)


if __name__ == "__main__":
    unittest.main()
