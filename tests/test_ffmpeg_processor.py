from __future__ import annotations

import unittest
from pathlib import Path
from subprocess import CompletedProcess
from tempfile import TemporaryDirectory
from unittest.mock import patch

from core.ffmpeg_processor import (
    ENCODER_H264_NVENC,
    ENCODER_LIBX264,
    ENCODER_OPTION_AUTO,
    ENCODER_OPTION_NVIDIA,
    EncoderAvailability,
    EncoderPlan,
    FFmpegProcessor,
    OUTPUT_QUALITY_BALANCED,
    OUTPUT_QUALITY_FAST,
    OUTPUT_QUALITY_HIGH,
    OUTPUT_SUFFIX_BRANDED,
    OUTPUT_SUFFIX_ZOOMED,
    build_mode_output_suffix,
    build_output_path,
    get_encoder_quality_arguments,
)
from core.output_resolution import (
    OUTPUT_RESOLUTION_1080X1920,
    RESIZE_MODE_FILL_AND_CROP,
    RESIZE_MODE_FIT_WITH_PADDING,
    build_output_standardization,
)
from core.selection import NormalizedSelection, normalized_selection_to_pixel_rect
from core.video_probe import VideoInfo


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

    def test_normalized_selection_to_pixel_rect_preserves_bottom_right_selection_on_720x1280(self):
        selection = NormalizedSelection(
            x_percent=95.0,
            y_percent=95.0,
            width_percent=5.0,
            height_percent=5.0,
        )

        pixel_rect = normalized_selection_to_pixel_rect(selection, 720, 1280)

        self.assertEqual(pixel_rect.x, 684)
        self.assertEqual(pixel_rect.y, 1216)
        self.assertEqual(pixel_rect.width, 36)
        self.assertEqual(pixel_rect.height, 64)
        self.assertEqual(pixel_rect.x + pixel_rect.width, 720)
        self.assertEqual(pixel_rect.y + pixel_rect.height, 1280)

    def test_normalized_selection_to_pixel_rect_preserves_bottom_right_selection_on_1080x1920(self):
        selection = NormalizedSelection(
            x_percent=95.0,
            y_percent=95.0,
            width_percent=5.0,
            height_percent=5.0,
        )

        pixel_rect = normalized_selection_to_pixel_rect(selection, 1080, 1920)

        self.assertEqual(pixel_rect.x, 1026)
        self.assertEqual(pixel_rect.y, 1824)
        self.assertEqual(pixel_rect.width, 54)
        self.assertEqual(pixel_rect.height, 96)
        self.assertEqual(pixel_rect.x + pixel_rect.width, 1080)
        self.assertEqual(pixel_rect.y + pixel_rect.height, 1920)

    def test_normalized_selection_to_pixel_rect_shrinks_odd_edge_dimensions_instead_of_expanding(self):
        selection = NormalizedSelection(
            x_percent=95.7,
            y_percent=94.9,
            width_percent=4.3,
            height_percent=5.1,
        )

        pixel_rect = normalized_selection_to_pixel_rect(selection, 720, 1280)

        self.assertEqual(pixel_rect.width % 2, 0)
        self.assertEqual(pixel_rect.height % 2, 0)
        self.assertLessEqual(pixel_rect.x + pixel_rect.width, 720)
        self.assertLessEqual(pixel_rect.y + pixel_rect.height, 1280)

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
            "[tmp]crop=w=140:h=120:x=900:y=40,"
            "boxblur=luma_radius=12:luma_power=1:chroma_radius=12:chroma_power=1[blurred];"
            "[base][blurred]overlay=x=900:y=40[outv]",
        )
        self.assertIn("[outv]", command)
        self.assertIn("0:a?", command)
        self.assertIn(ENCODER_LIBX264, command)
        self.assertEqual(command[-1], "output.mp4")

    def test_build_blur_command_keeps_bottom_right_selection_inside_720x1280_frame(self):
        processor = FFmpegProcessor(ffmpeg_path="ffmpeg")
        selection = NormalizedSelection(
            x_percent=95.0,
            y_percent=95.0,
            width_percent=5.0,
            height_percent=5.0,
        )

        command = processor.build_blur_command(
            input_path=Path("input.mp4"),
            output_path=Path("output.mp4"),
            selection=selection,
            video_width=720,
            video_height=1280,
            blur_strength=12,
            encoder=ENCODER_LIBX264,
        )

        filter_index = command.index("-filter_complex") + 1
        self.assertEqual(
            command[filter_index],
            "[0:v]split[base][tmp];"
            "[tmp]crop=w=36:h=64:x=684:y=1216,"
            "boxblur=luma_radius=12:luma_power=1:chroma_radius=8:chroma_power=1[blurred];"
            "[base][blurred]overlay=x=684:y=1216[outv]",
        )

    def test_build_blur_command_keeps_bottom_right_selection_inside_1080x1920_frame(self):
        processor = FFmpegProcessor(ffmpeg_path="ffmpeg")
        selection = NormalizedSelection(
            x_percent=95.0,
            y_percent=95.0,
            width_percent=5.0,
            height_percent=5.0,
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
            "[tmp]crop=w=54:h=96:x=1026:y=1824,"
            "boxblur=luma_radius=12:luma_power=1:chroma_radius=12:chroma_power=1[blurred];"
            "[base][blurred]overlay=x=1026:y=1824[outv]",
        )

    def test_build_blur_command_clamps_boxblur_radius_for_tiny_bottom_right_crop(self):
        processor = FFmpegProcessor(ffmpeg_path="ffmpeg")
        selection = NormalizedSelection(
            x_percent=92.7777778,
            y_percent=97.3958333,
            width_percent=6.2962963,
            height_percent=2.0833333,
        )

        command = processor.build_blur_command(
            input_path=Path("input.mp4"),
            output_path=Path("output.mp4"),
            selection=selection,
            video_width=1080,
            video_height=1920,
            blur_strength=20,
            encoder=ENCODER_LIBX264,
        )

        filter_index = command.index("-filter_complex") + 1
        self.assertIn("crop=w=68:h=40:x=1002:y=1870", command[filter_index])
        self.assertIn(
            "boxblur=luma_radius=19:luma_power=1:chroma_radius=9:chroma_power=1",
            command[filter_index],
        )

    def test_build_blur_command_appends_fill_crop_output_standardization(self):
        processor = FFmpegProcessor(ffmpeg_path="ffmpeg")
        selection = NormalizedSelection(
            x_percent=83.333333,
            y_percent=2.083333,
            width_percent=12.962963,
            height_percent=6.25,
        )
        output_standardization = build_output_standardization(
            OUTPUT_RESOLUTION_1080X1920,
            RESIZE_MODE_FILL_AND_CROP,
        )

        command = processor.build_blur_command(
            input_path=Path("input.mp4"),
            output_path=Path("output.mp4"),
            selection=selection,
            video_width=720,
            video_height=1280,
            blur_strength=12,
            encoder=ENCODER_LIBX264,
            output_standardization=output_standardization,
        )

        filter_index = command.index("-filter_complex") + 1
        self.assertEqual(
            command[filter_index],
            "[0:v]split[base][tmp];"
            "[tmp]crop=w=92:h=80:x=600:y=26,"
            "boxblur=luma_radius=12:luma_power=1:chroma_radius=12:chroma_power=1[blurred];"
            "[base][blurred]overlay=x=600:y=26[cleaned];"
            "[cleaned]scale=1080:1920:force_original_aspect_ratio=increase:flags=lanczos,"
            "crop=1080:1920[outv]",
        )

    def test_build_recipe_command_for_blur_plus_output_size(self):
        processor = FFmpegProcessor(ffmpeg_path="ffmpeg")
        selection = NormalizedSelection(
            x_percent=83.333333,
            y_percent=2.083333,
            width_percent=12.962963,
            height_percent=6.25,
        )
        output_standardization = build_output_standardization(
            OUTPUT_RESOLUTION_1080X1920,
            RESIZE_MODE_FILL_AND_CROP,
        )

        command = processor.build_recipe_command(
            input_path=Path("input.mp4"),
            output_path=Path("output.mp4"),
            video_width=720,
            video_height=1280,
            encoder=ENCODER_LIBX264,
            area_cleanup_type="Blur selected area",
            selection=selection,
            blur_strength=12,
            output_standardization=output_standardization,
        )

        filter_index = command.index("-filter_complex") + 1
        self.assertEqual(
            command[filter_index],
            "[0:v]split[base][tmp];"
            "[tmp]crop=w=92:h=80:x=600:y=26,"
            "boxblur=luma_radius=12:luma_power=1:chroma_radius=12:chroma_power=1[blurred];"
            "[base][blurred]overlay=x=600:y=26[cleaned];"
            "[cleaned]scale=1080:1920:force_original_aspect_ratio=increase:flags=lanczos,"
            "crop=1080:1920[outv]",
        )

    def test_build_recipe_command_for_output_size_only(self):
        processor = FFmpegProcessor(ffmpeg_path="ffmpeg")
        output_standardization = build_output_standardization(
            OUTPUT_RESOLUTION_1080X1920,
            RESIZE_MODE_FILL_AND_CROP,
        )

        command = processor.build_recipe_command(
            input_path=Path("input.mp4"),
            output_path=Path("output.mp4"),
            video_width=720,
            video_height=1280,
            encoder=ENCODER_LIBX264,
            output_standardization=output_standardization,
        )

        filter_index = command.index("-filter_complex") + 1
        self.assertEqual(
            command[filter_index],
            "[0:v]scale=1080:1920:force_original_aspect_ratio=increase:flags=lanczos,"
            "crop=1080:1920[outv]",
        )

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

    def test_output_suffix_includes_standardized_resolution_when_requested(self):
        output_standardization = build_output_standardization(
            OUTPUT_RESOLUTION_1080X1920,
            RESIZE_MODE_FILL_AND_CROP,
        )

        suffix = build_mode_output_suffix("_blurred", output_standardization)

        self.assertEqual(suffix, "_blurred_1080x1920")

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

    def test_build_recipe_command_for_logo_plus_output_size(self):
        processor = FFmpegProcessor(ffmpeg_path="ffmpeg")
        selection = NormalizedSelection(
            x_percent=83.333333,
            y_percent=2.083333,
            width_percent=12.962963,
            height_percent=6.25,
        )
        output_standardization = build_output_standardization(
            OUTPUT_RESOLUTION_1080X1920,
            RESIZE_MODE_FILL_AND_CROP,
        )

        command = processor.build_recipe_command(
            input_path=Path("input.mp4"),
            output_path=Path("output.mp4"),
            video_width=1080,
            video_height=1920,
            encoder=ENCODER_LIBX264,
            area_cleanup_type="Cover with logo/image",
            selection=selection,
            overlay_image_path=Path("brand logo.png"),
            output_standardization=output_standardization,
        )

        filter_index = command.index("-filter_complex") + 1
        self.assertEqual(
            command[filter_index],
            "[1:v]scale=w=140:h=120:force_original_aspect_ratio=decrease,"
            "pad=140:120:(ow-iw)/2:(oh-ih)/2:color=0x00000000[logo];"
            "[0:v][logo]overlay=x=900:y=40:format=auto[cleaned];"
            "[cleaned]scale=1080:1920:force_original_aspect_ratio=increase:flags=lanczos,"
            "crop=1080:1920[outv]",
        )

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

    def test_build_zoom_crop_command_appends_fit_padding_standardization(self):
        processor = FFmpegProcessor(ffmpeg_path="ffmpeg")
        output_standardization = build_output_standardization(
            OUTPUT_RESOLUTION_1080X1920,
            RESIZE_MODE_FIT_WITH_PADDING,
        )

        command = processor.build_zoom_crop_command(
            input_path=Path("input.mp4"),
            output_path=Path("output.mp4"),
            video_width=720,
            video_height=1280,
            zoom_percent=100,
            encoder=ENCODER_LIBX264,
            output_standardization=output_standardization,
        )

        filter_index = command.index("-filter_complex") + 1
        self.assertEqual(
            command[filter_index],
            "[0:v]scale=720:1280,crop=720:1280:(iw-720)/2:(ih-1280)/2[zoomed];"
            "[zoomed]scale=1080:1920:force_original_aspect_ratio=decrease:flags=lanczos,"
            "pad=1080:1920:(ow-iw)/2:(oh-ih)/2:color=black[outv]",
        )

    def test_build_recipe_command_for_zoom_plus_output_size(self):
        processor = FFmpegProcessor(ffmpeg_path="ffmpeg")
        output_standardization = build_output_standardization(
            OUTPUT_RESOLUTION_1080X1920,
            RESIZE_MODE_FIT_WITH_PADDING,
        )

        command = processor.build_recipe_command(
            input_path=Path("input.mp4"),
            output_path=Path("output.mp4"),
            video_width=720,
            video_height=1280,
            zoom_percent=108,
            encoder=ENCODER_LIBX264,
            output_standardization=output_standardization,
        )

        filter_index = command.index("-filter_complex") + 1
        self.assertEqual(
            command[filter_index],
            "[0:v]scale=778:1382,crop=720:1280:(iw-720)/2:(ih-1280)/2[zoomed];"
            "[zoomed]scale=1080:1920:force_original_aspect_ratio=decrease:flags=lanczos,"
            "pad=1080:1920:(ow-iw)/2:(oh-ih)/2:color=black[outv]",
        )

    def test_keep_original_does_not_append_output_standardization_filter(self):
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
            output_standardization=None,
        )

        filter_index = command.index("-filter_complex") + 1
        self.assertNotIn("force_original_aspect_ratio", command[filter_index])
        self.assertNotIn("scale=", command[filter_index])
        self.assertNotIn("pad=", command[filter_index])
        self.assertEqual(command[filter_index].count("crop="), 1)

    def test_auto_fallback_cpu_command_drops_nvenc_only_options(self):
        processor = FFmpegProcessor(ffmpeg_path="ffmpeg")
        selection = NormalizedSelection(
            x_percent=92.7777778,
            y_percent=97.3958333,
            width_percent=6.2962963,
            height_percent=2.0833333,
        )
        encoder_plan = EncoderPlan(
            primary_encoder=ENCODER_H264_NVENC,
            fallback_encoder=ENCODER_LIBX264,
            requested_option=ENCODER_OPTION_AUTO,
        )
        video_info = VideoInfo(
            file_path="C:/videos/sample.mp4",
            file_name="sample.mp4",
            width=1080,
            height=1920,
            fps=30.0,
            frame_count=300,
            duration_seconds=10.0,
        )

        run_results = [
            CompletedProcess(args=["ffmpeg"], returncode=1, stdout="", stderr="primary failed"),
            CompletedProcess(args=["ffmpeg"], returncode=0, stdout="fallback ok", stderr=""),
        ]

        with TemporaryDirectory() as temp_dir, patch.object(
            processor,
            "run_command",
            side_effect=run_results,
        ):
            result = processor.export_recipe_video(
                video_info=video_info,
                output_directory=Path(temp_dir),
                encoder_plan=encoder_plan,
                area_cleanup_type="Blur selected area",
                selection=selection,
                blur_strength=20,
                output_quality=OUTPUT_QUALITY_BALANCED,
            )

        self.assertTrue(result.fallback_used)
        self.assertIn("Attempt: primary", result.log_text)
        self.assertIn("Encoder selected: h264_nvenc", result.log_text)
        self.assertIn("Attempt: fallback", result.log_text)
        self.assertIn("Encoder selected: libx264", result.log_text)
        fallback_log = result.log_text.split("Attempt: fallback", maxsplit=1)[1]
        self.assertIn("-c:v libx264", fallback_log)
        self.assertIn("-crf 23", fallback_log)
        self.assertNotIn("-cq 23", fallback_log)
        self.assertNotIn("-preset p5", fallback_log)

    @unittest.skipUnless(
        FFmpegProcessor.resolve_ffmpeg_path() is not None,
        "FFmpeg not available",
    )
    def test_real_ffmpeg_smoke_blur_bottom_right_selection(self):
        processor = FFmpegProcessor()
        selection = NormalizedSelection(
            x_percent=92.7777778,
            y_percent=97.3958333,
            width_percent=6.2962963,
            height_percent=2.0833333,
        )
        encoder_plan = EncoderPlan(
            primary_encoder=ENCODER_LIBX264,
            fallback_encoder=None,
            requested_option="CPU - libx264",
        )

        with TemporaryDirectory() as temp_dir:
            temp_dir_path = Path(temp_dir)
            input_path = temp_dir_path / "synthetic.mp4"
            synth_command = [
                processor.ffmpeg_path,
                "-y",
                "-f",
                "lavfi",
                "-i",
                "color=c=blue:s=1080x1920:d=1",
                "-f",
                "lavfi",
                "-i",
                "anullsrc=r=48000:cl=stereo",
                "-shortest",
                "-c:v",
                ENCODER_LIBX264,
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "aac",
                str(input_path),
            ]
            synth_result = processor.run_command(synth_command)
            self.assertEqual(synth_result.returncode, 0, synth_result.stderr)

            smoke_video_info = VideoInfo(
                file_path=str(input_path),
                file_name=input_path.name,
                width=1080,
                height=1920,
                fps=25.0,
                frame_count=25,
                duration_seconds=1.0,
            )
            export_result = processor.export_recipe_video(
                video_info=smoke_video_info,
                output_directory=temp_dir_path,
                encoder_plan=encoder_plan,
                area_cleanup_type="Blur selected area",
                selection=selection,
                blur_strength=20,
            )

            self.assertTrue(export_result.success, export_result.log_text)
            self.assertTrue(export_result.output_path.exists())

    def test_quality_mapping_for_libx264_profiles(self):
        self.assertEqual(
            get_encoder_quality_arguments(ENCODER_LIBX264, OUTPUT_QUALITY_FAST),
            ["-preset", "veryfast", "-crf", "25"],
        )
        self.assertEqual(
            get_encoder_quality_arguments(ENCODER_LIBX264, OUTPUT_QUALITY_BALANCED),
            ["-preset", "medium", "-crf", "23"],
        )
        self.assertEqual(
            get_encoder_quality_arguments(ENCODER_LIBX264, OUTPUT_QUALITY_HIGH),
            ["-preset", "slow", "-crf", "20"],
        )

    def test_quality_mapping_for_nvenc_profiles(self):
        self.assertEqual(
            get_encoder_quality_arguments(ENCODER_H264_NVENC, OUTPUT_QUALITY_FAST),
            ["-preset", "p4", "-cq", "28"],
        )
        self.assertEqual(
            get_encoder_quality_arguments(ENCODER_H264_NVENC, OUTPUT_QUALITY_BALANCED),
            ["-preset", "p5", "-cq", "23"],
        )
        self.assertEqual(
            get_encoder_quality_arguments(ENCODER_H264_NVENC, OUTPUT_QUALITY_HIGH),
            ["-preset", "p7", "-cq", "19"],
        )

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

    @patch("core.ffmpeg_processor.Path.exists", autospec=True)
    @patch("core.ffmpeg_processor.which")
    def test_resolve_ffmpeg_path_prefers_path_lookup_first(self, mock_which, mock_exists):
        mock_which.return_value = "C:/Program Files/ffmpeg/bin/ffmpeg.exe"
        mock_exists.return_value = False

        resolved = FFmpegProcessor.resolve_ffmpeg_path()

        self.assertEqual(resolved, "C:/Program Files/ffmpeg/bin/ffmpeg.exe")
        mock_which.assert_called_once_with("ffmpeg")

    @patch("core.ffmpeg_processor.Path.exists", autospec=True)
    @patch("core.ffmpeg_processor.which")
    def test_resolve_ffmpeg_path_uses_common_windows_install(self, mock_which, mock_exists):
        mock_which.return_value = None

        def exists_side_effect(path_obj: Path) -> bool:
            return str(path_obj) == r"C:\ffmpeg\bin\ffmpeg.exe"

        mock_exists.side_effect = exists_side_effect

        resolved = FFmpegProcessor.resolve_ffmpeg_path()

        self.assertEqual(resolved, str(Path(r"C:\ffmpeg\bin\ffmpeg.exe").resolve()))

    @patch("core.ffmpeg_processor.Path.exists", autospec=True)
    @patch("core.ffmpeg_processor.which")
    @patch.object(FFmpegProcessor, "get_app_root")
    def test_resolve_ffmpeg_path_uses_bundled_bin_location(
        self,
        mock_app_root,
        mock_which,
        mock_exists,
    ):
        mock_which.return_value = None
        mock_app_root.return_value = Path("W:/ReelBatch Editor")
        bundled_path = Path("W:/ReelBatch Editor") / "ffmpeg" / "bin" / "ffmpeg.exe"

        def exists_side_effect(path_obj: Path) -> bool:
            return Path(path_obj) == bundled_path

        mock_exists.side_effect = exists_side_effect

        resolved = FFmpegProcessor.resolve_ffmpeg_path()

        self.assertEqual(
            resolved,
            str(bundled_path.resolve()),
        )

    @patch("core.ffmpeg_processor.Path.exists", autospec=True)
    @patch("core.ffmpeg_processor.which")
    @patch.object(FFmpegProcessor, "get_app_root")
    def test_resolve_ffmpeg_path_uses_repo_root_ffmpeg_exe_last(
        self,
        mock_app_root,
        mock_which,
        mock_exists,
    ):
        mock_which.return_value = None
        mock_app_root.return_value = Path("W:/ReelBatch Editor")
        repo_root_ffmpeg = Path("W:/ReelBatch Editor") / "ffmpeg.exe"

        def exists_side_effect(path_obj: Path) -> bool:
            return Path(path_obj) == repo_root_ffmpeg

        mock_exists.side_effect = exists_side_effect

        resolved = FFmpegProcessor.resolve_ffmpeg_path()

        self.assertEqual(
            resolved,
            str(repo_root_ffmpeg.resolve()),
        )

    @patch("core.ffmpeg_processor.run")
    @patch.object(FFmpegProcessor, "resolve_ffmpeg_path")
    def test_detect_available_encoders_parses_ffmpeg_output(self, mock_resolve, mock_run):
        mock_resolve.return_value = "C:/ffmpeg/bin/ffmpeg.exe"
        mock_run.return_value.stdout = " V..... h264_nvenc\n V..... libx264\n"
        mock_run.return_value.stderr = ""
        mock_run.return_value.returncode = 0
        processor = FFmpegProcessor()

        availability = processor.detect_available_encoders()

        mock_run.assert_called_once_with(
            ["C:/ffmpeg/bin/ffmpeg.exe", "-encoders"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertTrue(availability.has(ENCODER_H264_NVENC))
        self.assertTrue(availability.has(ENCODER_LIBX264))


if __name__ == "__main__":
    unittest.main()
