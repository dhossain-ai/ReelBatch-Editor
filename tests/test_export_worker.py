from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from core.ffmpeg_processor import ENCODER_LIBX264, EncoderPlan, ExportResult
from core.export_worker import ExportSettings, ExportWorker
from core.selection import NormalizedSelection
from core.video_probe import VideoInfo


class ExportWorkerTests(unittest.TestCase):
    def test_export_worker_logs_resolved_crop_rectangle_before_export(self):
        selection = NormalizedSelection(
            x_percent=95.0,
            y_percent=95.0,
            width_percent=5.0,
            height_percent=5.0,
        )
        video_info = VideoInfo(
            file_path="C:/videos/sample.mp4",
            file_name="sample.mp4",
            width=720,
            height=1280,
            fps=30.0,
            frame_count=300,
            duration_seconds=10.0,
        )
        encoder_plan = EncoderPlan(
            primary_encoder=ENCODER_LIBX264,
            fallback_encoder=None,
            requested_option="CPU - libx264",
        )

        with TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "export.log"
            output_dir = Path(temp_dir) / "exports"
            worker = ExportWorker(
                videos=[video_info],
                output_directory=output_dir,
                settings=ExportSettings(
                    area_cleanup_enabled=True,
                    selection=selection,
                ),
                encoder_plan=encoder_plan,
                log_file_path=log_path,
            )

            with patch.object(worker._processor, "export_recipe_video") as mock_export:
                mock_export.return_value = ExportResult(
                    success=True,
                    input_path=Path(video_info.file_path),
                    output_path=output_dir / "sample_blurred.mp4",
                    encoder_used=ENCODER_LIBX264,
                    fallback_used=False,
                    log_text="",
                    error_message=None,
                )

                worker._export_video(video_info)

            log_text = log_path.read_text(encoding="utf-8")
            self.assertIn("Resolved crop rectangle", log_text)
            self.assertIn("video_size=720x1280", log_text)
            self.assertIn("x=684", log_text)
            self.assertIn("y=1216", log_text)
            self.assertIn("width=36", log_text)
            self.assertIn("height=64", log_text)

    def test_log_result_writes_full_ffmpeg_diagnostics(self):
        video_info = VideoInfo(
            file_path="C:/videos/sample.mp4",
            file_name="sample.mp4",
            width=1080,
            height=1920,
            fps=30.0,
            frame_count=300,
            duration_seconds=10.0,
        )
        encoder_plan = EncoderPlan(
            primary_encoder=ENCODER_LIBX264,
            fallback_encoder=None,
            requested_option="CPU - libx264",
        )

        with TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "export.log"
            worker = ExportWorker(
                videos=[video_info],
                output_directory=Path(temp_dir) / "exports",
                settings=ExportSettings(),
                encoder_plan=encoder_plan,
                log_file_path=log_path,
            )

            worker._log_result(
                video_info,
                ExportResult(
                    success=False,
                    input_path=Path(video_info.file_path),
                    output_path=Path(temp_dir) / "exports" / "sample.mp4",
                    encoder_used=ENCODER_LIBX264,
                    fallback_used=False,
                    log_text=(
                        "Recipe state: area_cleanup=blur(radius=20)\n"
                        "Input video size: 1080x1920\n"
                        "Normalized selection: x_percent=92.777778, y_percent=97.395833, "
                        "width_percent=6.296296, height_percent=2.083333\n"
                        "Pixel crop rectangle: x=1002, y=1870, width=68, height=40\n"
                        "Output resolution settings: Keep original\n"
                        "Encoder selected: libx264\n"
                        "FFmpeg command: ffmpeg -i input.mp4 -filter_complex test\n"
                    ),
                    error_message="FFmpeg exited with code 1.",
                ),
            )

            log_text = log_path.read_text(encoding="utf-8")
            self.assertIn("FFmpeg diagnostic log follows:", log_text)
            self.assertIn("Recipe state: area_cleanup=blur(radius=20)", log_text)
            self.assertIn("Input video size: 1080x1920", log_text)
            self.assertIn("FFmpeg command: ffmpeg -i input.mp4 -filter_complex test", log_text)


if __name__ == "__main__":
    unittest.main()
