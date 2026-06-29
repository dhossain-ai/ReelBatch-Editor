"""
Background worker for batch FFmpeg exports.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Sequence

from PySide6.QtCore import QObject, Signal

from core.export_logging import ExportLogWriter, extract_ffmpeg_error_snippet
from core.ffmpeg_processor import EncoderPlan, ExportResult, FFmpegProcessor
from core.output_resolution import OutputStandardization
from core.processing_modes import (
    PROCESSING_MODE_BLUR,
    PROCESSING_MODE_LOGO,
    PROCESSING_MODE_ZOOM,
    processing_mode_progress_label,
)
from core.selection import NormalizedSelection
from core.video_probe import VideoInfo


@dataclass(frozen=True)
class ExportSettings:
    """Mode-specific export settings shared by the worker and UI."""

    processing_mode: str
    blur_strength: int = 10
    zoom_percent: int = 100
    output_quality: str = "Balanced"
    output_standardization: Optional[OutputStandardization] = None
    selection: Optional[NormalizedSelection] = None
    overlay_image_path: Optional[Path] = None


@dataclass(frozen=True)
class BatchExportSummary:
    """Summary for one batch export run."""

    total_videos: int
    success_count: int
    failure_count: int
    fallback_count: int
    output_directory: str
    log_file_path: str
    successes: tuple[tuple[str, str], ...]
    failures: tuple[tuple[str, str], ...]


def format_export_summary(summary: BatchExportSummary) -> str:
    """Create a readable summary for the export completion dialog."""
    summary_lines = [
        f"Total files: {summary.total_videos}",
        f"Successful files: {summary.success_count}",
        f"Failed files: {summary.failure_count}",
        f"Output folder: {summary.output_directory}",
    ]
    if summary.fallback_count:
        summary_lines.append(f"CPU fallback used: {summary.fallback_count}")
    if summary.log_file_path:
        summary_lines.append(f"Log file: {summary.log_file_path}")
    if summary.failures:
        summary_lines.append("")
        summary_lines.append("Failed files:")
        for file_name, error_message in summary.failures[:5]:
            summary_lines.append(f"- {file_name}: {error_message}")
        if len(summary.failures) > 5:
            summary_lines.append(f"... and {len(summary.failures) - 5} more")
    return "\n".join(summary_lines)


class ExportWorker(QObject):
    """Run batch exports in a background thread."""

    progress_changed = Signal(int, int)
    status_changed = Signal(str)
    file_finished = Signal(object)
    finished = Signal(object)

    def __init__(
        self,
        videos: Sequence[VideoInfo],
        output_directory: Path | str,
        settings: ExportSettings,
        encoder_plan: EncoderPlan,
        ffmpeg_path: str = "ffmpeg",
        log_file_path: Optional[Path | str] = None,
    ) -> None:
        super().__init__()
        self._videos = list(videos)
        self._output_directory = Path(output_directory)
        self._settings = settings
        self._encoder_plan = encoder_plan
        self._processor = FFmpegProcessor(ffmpeg_path=ffmpeg_path)
        self._log_writer = ExportLogWriter.create(
            Path(log_file_path) if log_file_path is not None else None
        )
        self._resolved_ffmpeg_path = self._processor.resolved_ffmpeg_path

    def run(self) -> None:
        """Export all queued videos and emit a final batch summary."""
        success_count = 0
        fallback_count = 0
        successes: list[tuple[str, str]] = []
        failures: list[tuple[str, str]] = []
        total = len(self._videos)
        self._log_writer.write_line(
            "Export batch started"
            f" | mode={self._settings.processing_mode}"
            f" | encoder_request={self._encoder_plan.requested_option}"
            f" | primary_encoder={self._encoder_plan.primary_encoder}"
            f" | output_quality={self._settings.output_quality}"
            f" | output_resolution={self._describe_output_standardization()}"
            f" | output_directory={self._output_directory}"
            f" | total_files={total}"
            f" | ffmpeg_path={self._resolved_ffmpeg_path or 'unresolved'}"
        )

        self.progress_changed.emit(0, total)

        try:
            self._output_directory.mkdir(parents=True, exist_ok=True)
        except Exception as exc:
            summary = BatchExportSummary(
                total_videos=total,
                success_count=0,
                failure_count=total,
                fallback_count=0,
                output_directory=str(self._output_directory),
                log_file_path=str(self._log_writer.log_file_path),
                successes=(),
                failures=(("Batch export", str(exc)),),
            )
            self._log_writer.write_line(f"Export batch aborted before processing: {exc}")
            self.finished.emit(summary)
            return

        for index, video_info in enumerate(self._videos, start=1):
            progress_label = processing_mode_progress_label(self._settings.processing_mode)
            self.status_changed.emit(f"{progress_label} {index}/{total}: {video_info.file_name}")
            self._log_writer.write_line(
                f"Processing file {index}/{total}"
                f" | input={video_info.file_path}"
                f" | mode={self._settings.processing_mode}"
            )
            try:
                result = self._export_video(video_info)
            except Exception as exc:
                result = ExportResult(
                    success=False,
                    input_path=Path(video_info.file_path),
                    output_path=self._output_directory,
                    encoder_used=self._encoder_plan.primary_encoder,
                    fallback_used=False,
                    log_text=str(exc),
                    error_message=str(exc),
                )
            self.file_finished.emit(result)
            self._log_result(video_info, result)

            if result.success:
                success_count += 1
                successes.append((video_info.file_name, str(result.output_path)))
            else:
                failures.append(
                    (
                        video_info.file_name,
                        result.error_message or "Export failed.",
                    )
                )

            if result.fallback_used:
                fallback_count += 1

            self.progress_changed.emit(index, total)

        summary = BatchExportSummary(
            total_videos=total,
            success_count=success_count,
            failure_count=len(failures),
            fallback_count=fallback_count,
            output_directory=str(self._output_directory),
            log_file_path=str(self._log_writer.log_file_path),
            successes=tuple(successes),
            failures=tuple(failures),
        )
        self._log_writer.write_line(
            "Export batch finished"
            f" | success_count={summary.success_count}"
            f" | failure_count={summary.failure_count}"
            f" | fallback_count={summary.fallback_count}"
        )
        self.finished.emit(summary)

    def _export_video(self, video_info: VideoInfo) -> ExportResult:
        """Dispatch export processing for the configured mode."""
        if self._settings.processing_mode == PROCESSING_MODE_BLUR:
            if self._settings.selection is None:
                raise ValueError("Blur export requires a rectangle selection.")
            return self._processor.export_blur_video(
                video_info=video_info,
                selection=self._settings.selection,
                output_directory=self._output_directory,
                blur_strength=self._settings.blur_strength,
                encoder_plan=self._encoder_plan,
                output_quality=self._settings.output_quality,
                output_standardization=self._settings.output_standardization,
            )

        if self._settings.processing_mode == PROCESSING_MODE_LOGO:
            if self._settings.selection is None:
                raise ValueError("Logo/image export requires a rectangle selection.")
            if self._settings.overlay_image_path is None:
                raise ValueError("Logo/image export requires a selected image file.")
            return self._processor.export_logo_overlay_video(
                video_info=video_info,
                selection=self._settings.selection,
                overlay_image_path=self._settings.overlay_image_path,
                output_directory=self._output_directory,
                encoder_plan=self._encoder_plan,
                output_quality=self._settings.output_quality,
                output_standardization=self._settings.output_standardization,
            )

        if self._settings.processing_mode == PROCESSING_MODE_ZOOM:
            return self._processor.export_zoom_crop_video(
                video_info=video_info,
                output_directory=self._output_directory,
                zoom_percent=self._settings.zoom_percent,
                encoder_plan=self._encoder_plan,
                output_quality=self._settings.output_quality,
                output_standardization=self._settings.output_standardization,
            )

        raise ValueError(f"Unsupported processing mode: {self._settings.processing_mode}")

    def _log_result(self, video_info: VideoInfo, result: ExportResult) -> None:
        """Write a compact per-file log entry for debugging."""
        message = (
            f"Result | input={video_info.file_path}"
            f" | output={result.output_path}"
            f" | success={result.success}"
            f" | encoder_used={result.encoder_used}"
        )
        if result.fallback_used:
            message += " | fallback_used=True"
        if result.error_message:
            message += f" | error={result.error_message}"
        self._log_writer.write_line(message)

        if result.fallback_used:
            self._log_writer.write_line(
                f"Fallback event | file={video_info.file_path} | fallback_encoder={result.encoder_used}"
            )

        if not result.success:
            self._log_writer.write_line(
                "FFmpeg error snippet follows:\n"
                f"{extract_ffmpeg_error_snippet(result.log_text)}"
            )

    def _describe_output_standardization(self) -> str:
        """Return a compact log label for the selected output standardization."""
        if self._settings.output_standardization is None:
            return "Keep original"

        standardization = self._settings.output_standardization
        return (
            f"{standardization.target_width}x{standardization.target_height}"
            f" ({standardization.resize_mode})"
        )
