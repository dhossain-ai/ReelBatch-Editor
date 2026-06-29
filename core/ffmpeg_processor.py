"""
FFmpeg command generation and export helpers.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from shutil import which
from subprocess import CompletedProcess, run
from typing import Callable, Optional, Sequence

from core.selection import NormalizedSelection, PixelSelection, normalized_selection_to_pixel_rect
from core.video_probe import VideoInfo

ENCODER_OPTION_AUTO = "Auto - Prefer NVIDIA NVENC"
ENCODER_OPTION_CPU = "CPU - libx264"
ENCODER_OPTION_NVIDIA = "NVIDIA - h264_nvenc"

ENCODER_H264_NVENC = "h264_nvenc"
ENCODER_H264_QSV = "h264_qsv"
ENCODER_H264_AMF = "h264_amf"
ENCODER_LIBX264 = "libx264"

SUPPORTED_ENCODERS = {
    ENCODER_H264_NVENC,
    ENCODER_H264_QSV,
    ENCODER_H264_AMF,
    ENCODER_LIBX264,
}

OUTPUT_SUFFIX_BLURRED = "_blurred"
OUTPUT_SUFFIX_BRANDED = "_branded"
OUTPUT_SUFFIX_ZOOMED = "_zoomed"

DEFAULT_OUTPUT_SUFFIX = OUTPUT_SUFFIX_BLURRED


@dataclass(frozen=True)
class EncoderAvailability:
    """Detected encoder support from the local FFmpeg build."""

    available: frozenset[str]

    def has(self, encoder_name: str) -> bool:
        return encoder_name in self.available

    @property
    def has_nvenc(self) -> bool:
        return self.has(ENCODER_H264_NVENC)

    @property
    def has_libx264(self) -> bool:
        return self.has(ENCODER_LIBX264)


@dataclass(frozen=True)
class EncoderPlan:
    """Resolved encoder choice for a given export run."""

    primary_encoder: str
    fallback_encoder: Optional[str]
    requested_option: str

    @property
    def allows_fallback(self) -> bool:
        return self.fallback_encoder is not None


@dataclass(frozen=True)
class ExportResult:
    """Result for exporting a single file."""

    success: bool
    input_path: Path
    output_path: Path
    encoder_used: str
    fallback_used: bool
    log_text: str
    error_message: Optional[str] = None


class FFmpegProcessor:
    """Build and execute FFmpeg blur exports for a batch of videos."""

    def __init__(self, ffmpeg_path: str = "ffmpeg") -> None:
        self.ffmpeg_path = ffmpeg_path

    def is_ffmpeg_available(self) -> bool:
        """Return True when FFmpeg is available on PATH."""
        return which(self.ffmpeg_path) is not None

    def detect_available_encoders(self) -> EncoderAvailability:
        """Detect a subset of H.264 encoders supported by the local FFmpeg build."""
        if not self.is_ffmpeg_available():
            return EncoderAvailability(frozenset())

        try:
            result = run(
                [self.ffmpeg_path, "-encoders"],
                capture_output=True,
                text=True,
                check=False,
            )
        except OSError:
            return EncoderAvailability(frozenset())

        encoder_output = "\n".join(part for part in (result.stdout, result.stderr) if part)
        available = {
            encoder_name
            for encoder_name in SUPPORTED_ENCODERS
            if encoder_name in encoder_output
        }
        return EncoderAvailability(frozenset(available))

    def resolve_encoder_plan(
        self,
        encoder_option: str,
        availability: Optional[EncoderAvailability] = None,
    ) -> EncoderPlan:
        """Resolve the UI encoder choice into a primary encoder and optional fallback."""
        available = availability or self.detect_available_encoders()

        if encoder_option == ENCODER_OPTION_AUTO:
            if available.has_nvenc:
                fallback = ENCODER_LIBX264 if available.has_libx264 else None
                return EncoderPlan(
                    primary_encoder=ENCODER_H264_NVENC,
                    fallback_encoder=fallback,
                    requested_option=encoder_option,
                )
            if available.has_libx264:
                return EncoderPlan(
                    primary_encoder=ENCODER_LIBX264,
                    fallback_encoder=None,
                    requested_option=encoder_option,
                )
            raise ValueError("Auto encoder mode requires h264_nvenc or libx264 support in FFmpeg.")

        if encoder_option == ENCODER_OPTION_CPU:
            if not available.has_libx264:
                raise ValueError("CPU export requires libx264 support in FFmpeg.")
            return EncoderPlan(
                primary_encoder=ENCODER_LIBX264,
                fallback_encoder=None,
                requested_option=encoder_option,
            )

        if encoder_option == ENCODER_OPTION_NVIDIA:
            if not available.has_nvenc:
                raise ValueError("NVIDIA export requires h264_nvenc support in FFmpeg.")
            return EncoderPlan(
                primary_encoder=ENCODER_H264_NVENC,
                fallback_encoder=None,
                requested_option=encoder_option,
            )

        raise ValueError(f"Unsupported encoder option: {encoder_option}")

    def build_blur_command(
        self,
        input_path: Path | str,
        output_path: Path | str,
        selection: NormalizedSelection,
        video_width: int,
        video_height: int,
        blur_strength: int,
        encoder: str,
    ) -> list[str]:
        """Build an FFmpeg command that blurs the selected region and writes MP4 output."""
        input_file = Path(input_path)
        output_file = Path(output_path)
        pixel_rect = normalized_selection_to_pixel_rect(selection, video_width, video_height)
        filter_graph = build_blur_filter(pixel_rect, blur_strength)

        command = [
            self.ffmpeg_path,
            "-y",
            "-i",
            str(input_file),
            "-filter_complex",
            filter_graph,
            "-map",
            "[outv]",
            "-map",
            "0:a?",
            "-c:v",
            encoder,
            "-pix_fmt",
            "yuv420p",
        ]
        command.extend(self._build_output_arguments(encoder, output_file))
        return command

    def build_logo_overlay_command(
        self,
        input_path: Path | str,
        output_path: Path | str,
        overlay_image_path: Path | str,
        selection: NormalizedSelection,
        video_width: int,
        video_height: int,
        encoder: str,
    ) -> list[str]:
        """Build an FFmpeg command that overlays a scaled logo/image on the selected region."""
        input_file = Path(input_path)
        output_file = Path(output_path)
        overlay_file = Path(overlay_image_path)
        pixel_rect = normalized_selection_to_pixel_rect(selection, video_width, video_height)
        filter_graph = build_logo_overlay_filter(pixel_rect)

        command = [
            self.ffmpeg_path,
            "-y",
            "-i",
            str(input_file),
            "-i",
            str(overlay_file),
            "-filter_complex",
            filter_graph,
            "-map",
            "[outv]",
            "-map",
            "0:a?",
            "-c:v",
            encoder,
            "-pix_fmt",
            "yuv420p",
        ]
        command.extend(self._build_output_arguments(encoder, output_file))
        return command

    def build_zoom_crop_command(
        self,
        input_path: Path | str,
        output_path: Path | str,
        video_width: int,
        video_height: int,
        zoom_percent: int,
        encoder: str,
    ) -> list[str]:
        """Build an FFmpeg command that scales and center-crops back to the original size."""
        input_file = Path(input_path)
        output_file = Path(output_path)
        filter_graph = build_zoom_crop_filter(video_width, video_height, zoom_percent)

        command = [
            self.ffmpeg_path,
            "-y",
            "-i",
            str(input_file),
            "-filter_complex",
            filter_graph,
            "-map",
            "[outv]",
            "-map",
            "0:a?",
            "-c:v",
            encoder,
            "-pix_fmt",
            "yuv420p",
        ]
        command.extend(self._build_output_arguments(encoder, output_file))
        return command

    def export_blur_video(
        self,
        video_info: VideoInfo,
        selection: NormalizedSelection,
        output_directory: Path | str,
        blur_strength: int,
        encoder_plan: EncoderPlan,
    ) -> ExportResult:
        """Export one blurred video, retrying with CPU when Auto NVENC fails."""
        output_path = build_output_path(
            output_directory,
            video_info.file_name,
            suffix=OUTPUT_SUFFIX_BLURRED,
        )
        return self._export_video_with_retry(
            video_info=video_info,
            output_path=output_path,
            encoder_plan=encoder_plan,
            command_builder=lambda encoder: self.build_blur_command(
                input_path=video_info.file_path,
                output_path=output_path,
                selection=selection,
                video_width=video_info.width,
                video_height=video_info.height,
                blur_strength=blur_strength,
                encoder=encoder,
            )
        )

    def export_logo_overlay_video(
        self,
        video_info: VideoInfo,
        selection: NormalizedSelection,
        overlay_image_path: Path | str,
        output_directory: Path | str,
        encoder_plan: EncoderPlan,
    ) -> ExportResult:
        """Export one video with a scaled logo/image overlay."""
        output_path = build_output_path(
            output_directory,
            video_info.file_name,
            suffix=OUTPUT_SUFFIX_BRANDED,
        )
        return self._export_video_with_retry(
            video_info=video_info,
            output_path=output_path,
            encoder_plan=encoder_plan,
            command_builder=lambda encoder: self.build_logo_overlay_command(
                input_path=video_info.file_path,
                output_path=output_path,
                overlay_image_path=overlay_image_path,
                selection=selection,
                video_width=video_info.width,
                video_height=video_info.height,
                encoder=encoder,
            )
        )

    def export_zoom_crop_video(
        self,
        video_info: VideoInfo,
        output_directory: Path | str,
        zoom_percent: int,
        encoder_plan: EncoderPlan,
    ) -> ExportResult:
        """Export one video with a centered zoom/crop effect."""
        output_path = build_output_path(
            output_directory,
            video_info.file_name,
            suffix=OUTPUT_SUFFIX_ZOOMED,
        )
        return self._export_video_with_retry(
            video_info=video_info,
            output_path=output_path,
            encoder_plan=encoder_plan,
            command_builder=lambda encoder: self.build_zoom_crop_command(
                input_path=video_info.file_path,
                output_path=output_path,
                video_width=video_info.width,
                video_height=video_info.height,
                zoom_percent=zoom_percent,
                encoder=encoder,
            ),
        )

    def _export_video_with_retry(
        self,
        video_info: VideoInfo,
        output_path: Path,
        encoder_plan: EncoderPlan,
        command_builder: Callable[[str], list[str]],
    ) -> ExportResult:
        primary_result = self._run_export_attempt(
            video_info=video_info,
            output_path=output_path,
            encoder=encoder_plan.primary_encoder,
            command=command_builder(encoder_plan.primary_encoder),
        )
        if primary_result.success:
            return primary_result

        if encoder_plan.requested_option == ENCODER_OPTION_AUTO and encoder_plan.fallback_encoder:
            fallback_result = self._run_export_attempt(
                video_info=video_info,
                output_path=output_path,
                encoder=encoder_plan.fallback_encoder,
                command=command_builder(encoder_plan.fallback_encoder),
                prior_log_text=primary_result.log_text,
            )
            return ExportResult(
                success=fallback_result.success,
                input_path=fallback_result.input_path,
                output_path=fallback_result.output_path,
                encoder_used=fallback_result.encoder_used,
                fallback_used=True,
                log_text=fallback_result.log_text,
                error_message=fallback_result.error_message,
            )

        return primary_result

    def _run_export_attempt(
        self,
        video_info: VideoInfo,
        output_path: Path,
        encoder: str,
        command: Sequence[str],
        prior_log_text: str = "",
    ) -> ExportResult:
        completed = self.run_command(command)
        combined_log = join_log_text(prior_log_text, completed.stdout, completed.stderr)
        success = completed.returncode == 0
        error_message = None if success else f"FFmpeg exited with code {completed.returncode}."
        return ExportResult(
            success=success,
            input_path=Path(video_info.file_path),
            output_path=output_path,
            encoder_used=encoder,
            fallback_used=False,
            log_text=combined_log,
            error_message=error_message,
        )

    def run_command(self, command: Sequence[str]) -> CompletedProcess[str]:
        """Execute an FFmpeg command and capture output for reporting."""
        return run(command, capture_output=True, text=True, check=False)

    @classmethod
    def _build_output_arguments(cls, encoder: str, output_file: Path) -> list[str]:
        output_arguments = cls._encoder_arguments(encoder)
        output_arguments.extend(
            [
                "-c:a",
                "aac",
                "-b:a",
                "192k",
                "-movflags",
                "+faststart",
                str(output_file),
            ]
        )
        return output_arguments

    @staticmethod
    def _encoder_arguments(encoder: str) -> list[str]:
        if encoder == ENCODER_H264_NVENC:
            return ["-preset", "p5", "-cq", "23"]
        if encoder == ENCODER_LIBX264:
            return ["-preset", "medium", "-crf", "23"]
        return []


def build_blur_filter(pixel_rect: PixelSelection, blur_strength: int) -> str:
    """Build the FFmpeg filter_complex string for the blur overlay pipeline."""
    radius = max(1, int(blur_strength))
    return (
        "[0:v]split[base][tmp];"
        f"[tmp]crop=w={pixel_rect.width}:h={pixel_rect.height}:x={pixel_rect.x}:y={pixel_rect.y},"
        f"boxblur={radius}:1[blurred];"
        f"[base][blurred]overlay=x={pixel_rect.x}:y={pixel_rect.y}[outv]"
    )


def build_logo_overlay_filter(pixel_rect: PixelSelection) -> str:
    """Build the FFmpeg filter_complex string for the logo overlay pipeline."""
    return (
        f"[1:v]scale=w={pixel_rect.width}:h={pixel_rect.height}:force_original_aspect_ratio=decrease,"
        f"pad={pixel_rect.width}:{pixel_rect.height}:(ow-iw)/2:(oh-ih)/2:color=0x00000000[logo];"
        f"[0:v][logo]overlay=x={pixel_rect.x}:y={pixel_rect.y}:format=auto[outv]"
    )


def build_zoom_crop_filter(video_width: int, video_height: int, zoom_percent: int) -> str:
    """Build the FFmpeg filter_complex string for the centered zoom/crop pipeline."""
    if video_width <= 0 or video_height <= 0:
        raise ValueError("Video dimensions must be positive integers.")

    zoom_factor = max(float(zoom_percent), 100.0) / 100.0
    scaled_width = max(video_width, int(round(video_width * zoom_factor)))
    scaled_height = max(video_height, int(round(video_height * zoom_factor)))
    return (
        f"[0:v]scale={scaled_width}:{scaled_height},"
        f"crop={video_width}:{video_height}:(iw-{video_width})/2:(ih-{video_height})/2[outv]"
    )


def build_output_path(
    output_directory: Path | str,
    source_filename: str,
    suffix: str = DEFAULT_OUTPUT_SUFFIX,
) -> Path:
    """Create a non-colliding MP4 output path for a source filename."""
    output_dir = Path(output_directory)
    stem = Path(source_filename).stem
    candidate = output_dir / f"{stem}{suffix}.mp4"
    counter = 1

    while candidate.exists():
        candidate = output_dir / f"{stem}{suffix}_{counter}.mp4"
        counter += 1

    return candidate


def join_log_text(*chunks: Optional[str]) -> str:
    """Join stdout/stderr text chunks into a readable debug log."""
    return "\n".join(chunk.strip() for chunk in chunks if chunk and chunk.strip())
