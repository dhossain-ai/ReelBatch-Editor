"""
Background worker for batch FFmpeg blur exports.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from PySide6.QtCore import QObject, Signal

from core.ffmpeg_processor import EncoderPlan, ExportResult, FFmpegProcessor
from core.selection import NormalizedSelection
from core.video_probe import VideoInfo


@dataclass(frozen=True)
class BatchExportSummary:
    """Summary for one batch export run."""

    total_videos: int
    success_count: int
    failure_count: int
    fallback_count: int
    output_directory: str
    failures: tuple[tuple[str, str], ...]


class ExportWorker(QObject):
    """Run blur exports in a background thread."""

    progress_changed = Signal(int, int)
    status_changed = Signal(str)
    file_finished = Signal(object)
    finished = Signal(object)

    def __init__(
        self,
        videos: Sequence[VideoInfo],
        selection: NormalizedSelection,
        output_directory: Path | str,
        blur_strength: int,
        encoder_plan: EncoderPlan,
        ffmpeg_path: str = "ffmpeg",
    ) -> None:
        super().__init__()
        self._videos = list(videos)
        self._selection = selection
        self._output_directory = Path(output_directory)
        self._blur_strength = int(blur_strength)
        self._encoder_plan = encoder_plan
        self._processor = FFmpegProcessor(ffmpeg_path=ffmpeg_path)

    def run(self) -> None:
        """Export all queued videos and emit a final batch summary."""
        success_count = 0
        fallback_count = 0
        failures: list[tuple[str, str]] = []
        total = len(self._videos)

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
                failures=(("Batch export", str(exc)),),
            )
            self.finished.emit(summary)
            return

        for index, video_info in enumerate(self._videos, start=1):
            self.status_changed.emit(f"Exporting {index}/{total}: {video_info.file_name}")
            try:
                result = self._processor.export_blur_video(
                    video_info=video_info,
                    selection=self._selection,
                    output_directory=self._output_directory,
                    blur_strength=self._blur_strength,
                    encoder_plan=self._encoder_plan,
                )
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

            if result.success:
                success_count += 1
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
            failures=tuple(failures),
        )
        self.finished.emit(summary)
