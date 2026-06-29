from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from core.ffmpeg_processor import (
    ENCODER_H264_NVENC,
    ENCODER_LIBX264,
    ENCODER_OPTION_AUTO,
    ENCODER_OPTION_NVIDIA,
    EncoderAvailability,
    FFmpegProcessor,
    OUTPUT_SUFFIX_BRANDED,
    OUTPUT_SUFFIX_ZOOMED,
    build_output_path,
)
from core.selection import NormalizedSelection, normalized_selection_to_pixel_rect


class FFmpegProcessorTests(unittest.TestCase):
    def test_normalized_selection_to_pixel_rect_matches_expected_vertical_video(self):
        selection = NormalizedSelection(
            x_percent=83.333333,
            y_percent=2.083333,
            width_percent=12.962963,
            height_percent=6.25,
        )

        pixel_rect = normalized_selection_to_pixel_rect(selection, 1080, 1920)

        self.assertEqual(pixel_rect.x, 900)
        self.assertEqual(pixel_rect.y, 40)
        self.assertEqual(pixel_rect.width, 140)
        self.assertEqual(pixel_rect.height, 120)

    def test_normalized_selection_to_pixel_rect_clamps_outside_bounds(self):
        selection = NormalizedSelection(
            x_percent=99.9,
            y_percent=99.9,
            width_percent=10.0,
            height_percent=10.0,
        )

        pixel_rect = normalized_selection_to_pixel_rect(selection, 1080, 1920)

        self.assertEqual(pixel_rect.x, 1078)
        self.assertEqual(pixel_rect.y, 1918)
        self.assertEqual(pixel_rect.width, 2)
        self.assertEqual(pixel_rect.height, 2)

    def test_build_blur_command_contains_expected_filter_and_audio_mapping(self):
        processor = FFmpegProcessor(ffmpeg_path="ffmpeg")
        selection = NormalizedSelection(
            x_percent=83.333333,
            y_percent=2.083333,
            width_percent=12.962963,
            height_percent=6.25,
        )

        command = processor.build_blur_command(
            input_path=Path("input.mp4"),
            output_path=Path("output.mp4"),
            selection=selection,
            video_width=1080,
            video_height=1920,
            blur_strength=12,
            encoder=ENCODER_LIBX264,
        )

        filter_index = command.index("-filter_complex") + 1
        self.assertEqual(
            command[filter_index],
            "[0:v]split[base][tmp];"
            "[tmp]crop=w=140:h=120:x=900:y=40,boxblur=12:1[blurred];"
            "[base][blurred]overlay=x=900:y=40[outv]",
        )
        self.assertIn("[outv]", command)
        self.assertIn("0:a?", command)
        self.assertIn(ENCODER_LIBX264, command)
        self.assertEqual(command[-1], "output.mp4")

    def test_output_filename_collision_adds_numeric_suffix(self):
        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            first_path = output_dir / "video_blurred.mp4"
            second_path = output_dir / "video_blurred_1.mp4"
            first_path.touch()
            second_path.touch()

            output_path = build_output_path(output_dir, "video.mp4")

            self.assertEqual(output_path.name, "video_blurred_2.mp4")

    def test_output_filename_uses_requested_mode_suffix(self):
        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)

            branded_output = build_output_path(
                output_dir,
                "video.mp4",
                suffix=OUTPUT_SUFFIX_BRANDED,
            )
            zoomed_output = build_output_path(
                output_dir,
                "video.mp4",
                suffix=OUTPUT_SUFFIX_ZOOMED,
            )

            self.assertEqual(branded_output.name, "video_branded.mp4")
            self.assertEqual(zoomed_output.name, "video_zoomed.mp4")

    def test_build_logo_overlay_command_contains_scaled_overlay_filter(self):
        processor = FFmpegProcessor(ffmpeg_path="ffmpeg")
        selection = NormalizedSelection(
            x_percent=83.333333,
            y_percent=2.083333,
            width_percent=12.962963,
            height_percent=6.25,
        )

        command = processor.build_logo_overlay_command(
            input_path=Path("input.mp4"),
            output_path=Path("output.mp4"),
            overlay_image_path=Path("brand logo.png"),
            selection=selection,
            video_width=1080,
            video_height=1920,
            encoder=ENCODER_LIBX264,
        )

        filter_index = command.index("-filter_complex") + 1
        self.assertEqual(
            command[filter_index],
            "[1:v]scale=w=140:h=120:force_original_aspect_ratio=decrease,"
            "pad=140:120:(ow-iw)/2:(oh-ih)/2:color=0x00000000[logo];"
            "[0:v][logo]overlay=x=900:y=40:format=auto[outv]",
        )
        self.assertEqual(command[5], "brand logo.png")
        self.assertIn("0:a?", command)
        self.assertIn(ENCODER_LIBX264, command)

    def test_build_zoom_crop_command_contains_center_crop_filter(self):
        processor = FFmpegProcessor(ffmpeg_path="ffmpeg")

        command = processor.build_zoom_crop_command(
            input_path=Path("input.mp4"),
            output_path=Path("output.mp4"),
            video_width=1080,
            video_height=1920,
            zoom_percent=108,
            encoder=ENCODER_LIBX264,
        )

        filter_index = command.index("-filter_complex") + 1
        self.assertEqual(
            command[filter_index],
            "[0:v]scale=1166:2074,crop=1080:1920:(iw-1080)/2:(ih-1920)/2[outv]",
        )
        self.assertIn("0:a?", command)
        self.assertIn(ENCODER_LIBX264, command)
        self.assertEqual(command[-1], "output.mp4")

    def test_resolve_encoder_plan_auto_prefers_nvenc_and_falls_back_to_cpu(self):
        processor = FFmpegProcessor()
        availability = EncoderAvailability(frozenset({ENCODER_H264_NVENC, ENCODER_LIBX264}))

        plan = processor.resolve_encoder_plan(ENCODER_OPTION_AUTO, availability)

        self.assertEqual(plan.primary_encoder, ENCODER_H264_NVENC)
        self.assertEqual(plan.fallback_encoder, ENCODER_LIBX264)

    def test_resolve_encoder_plan_nvidia_requires_nvenc(self):
        processor = FFmpegProcessor()
        availability = EncoderAvailability(frozenset({ENCODER_LIBX264}))

        with self.assertRaisesRegex(ValueError, "h264_nvenc"):
            processor.resolve_encoder_plan(ENCODER_OPTION_NVIDIA, availability)

    @patch("core.ffmpeg_processor.run")
    @patch("core.ffmpeg_processor.which")
    def test_detect_available_encoders_parses_ffmpeg_output(self, mock_which, mock_run):
        mock_which.return_value = "C:/ffmpeg/bin/ffmpeg.exe"
        mock_run.return_value.stdout = " V..... h264_nvenc\n V..... libx264\n"
        mock_run.return_value.stderr = ""
        mock_run.return_value.returncode = 0
        processor = FFmpegProcessor()

        availability = processor.detect_available_encoders()

        self.assertTrue(availability.has(ENCODER_H264_NVENC))
        self.assertTrue(availability.has(ENCODER_LIBX264))


if __name__ == "__main__":
    unittest.main()
