"""
FFmpeg command generation and export helpers.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from shutil import which
from subprocess import CompletedProcess, list2cmdline, run
from typing import Callable, Optional, Sequence

from core.export_recipe import AREA_CLEANUP_TYPE_BLUR, AREA_CLEANUP_TYPE_LOGO
from core.output_resolution import (
    OutputStandardization,
    RESIZE_MODE_FILL_AND_CROP,
    RESIZE_MODE_FIT_WITH_PADDING,
)
from core.selection import NormalizedSelection, PixelSelection, normalized_selection_to_pixel_rect
from core.video_probe import VideoInfo

ENCODER_OPTION_AUTO = "Auto - Prefer NVIDIA NVENC"
ENCODER_OPTION_CPU = "CPU - libx264"
ENCODER_OPTION_NVIDIA = "NVIDIA - h264_nvenc"

ENCODER_H264_NVENC = "h264_nvenc"
ENCODER_H264_QSV = "h264_qsv"
ENCODER_H264_AMF = "h264_amf"
ENCODER_LIBX264 = "libx264"

OUTPUT_QUALITY_FAST = "Fast"
OUTPUT_QUALITY_BALANCED = "Balanced"
OUTPUT_QUALITY_HIGH = "High Quality"

OUTPUT_QUALITY_OPTIONS = (
    OUTPUT_QUALITY_FAST,
    OUTPUT_QUALITY_BALANCED,
    OUTPUT_QUALITY_HIGH,
)

SUPPORTED_ENCODERS = {
    ENCODER_H264_NVENC,
    ENCODER_H264_QSV,
    ENCODER_H264_AMF,
    ENCODER_LIBX264,
}

OUTPUT_SUFFIX_BLURRED = "_blurred"
OUTPUT_SUFFIX_BRANDED = "_branded"
OUTPUT_SUFFIX_ZOOMED = "_zoomed"
OUTPUT_SUFFIX_STANDARDIZED = "_standardized"
OUTPUT_SUFFIX_PROCESSED = "_processed"

DEFAULT_OUTPUT_SUFFIX = OUTPUT_SUFFIX_BLURRED
FFMPEG_NOT_FOUND_MESSAGE = (
    "FFmpeg was not found. Install FFmpeg, add it to PATH, or place it at "
    r"C:\ffmpeg\bin\ffmpeg.exe."
)


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
        self._configured_ffmpeg_path = ffmpeg_path
        self._resolved_ffmpeg_path: Optional[str] = None

    @property
    def ffmpeg_path(self) -> str:
        """Return the resolved FFmpeg executable when available."""
        return self.get_ffmpeg_executable() or self._configured_ffmpeg_path

    @property
    def resolved_ffmpeg_path(self) -> Optional[str]:
        """Expose the resolved FFmpeg executable path for UI/logging."""
        return self.get_ffmpeg_executable()

    @staticmethod
    def get_app_root() -> Path:
        """Return the repository/application root used for bundled FFmpeg lookups."""
        return Path(__file__).resolve().parent.parent

    @classmethod
    def discovery_candidates(cls, ffmpeg_path: str = "ffmpeg") -> tuple[Path | str, ...]:
        """Return the ordered FFmpeg discovery candidates."""
        app_root = cls.get_app_root()
        candidates: list[Path | str] = []
        if ffmpeg_path and ffmpeg_path != "ffmpeg":
            candidates.append(Path(ffmpeg_path))
        candidates.extend(
            [
                "ffmpeg",
                Path(r"C:\ffmpeg\bin\ffmpeg.exe"),
                app_root / "ffmpeg" / "bin" / "ffmpeg.exe",
                app_root / "ffmpeg.exe",
            ]
        )
        return tuple(candidates)

    @classmethod
    def resolve_ffmpeg_path(cls, ffmpeg_path: str = "ffmpeg") -> Optional[str]:
        """Resolve FFmpeg from PATH or common Windows/bundled locations."""
        for candidate in cls.discovery_candidates(ffmpeg_path):
            if candidate == "ffmpeg":
                resolved = which("ffmpeg")
                if resolved:
                    return resolved
                continue

            candidate_path = Path(candidate)
            if candidate_path.exists():
                return str(candidate_path.resolve())
        return None

    def get_ffmpeg_executable(self) -> Optional[str]:
        """Return a cached FFmpeg executable path, resolving it when needed."""
        if self._resolved_ffmpeg_path:
            return self._resolved_ffmpeg_path

        resolved = self.resolve_ffmpeg_path(self._configured_ffmpeg_path)
        if resolved:
            self._resolved_ffmpeg_path = resolved
        return resolved

    def is_ffmpeg_available(self) -> bool:
        """Return True when FFmpeg is available from any supported discovery path."""
        return self.get_ffmpeg_executable() is not None

    def detect_available_encoders(self) -> EncoderAvailability:
        """Detect a subset of H.264 encoders supported by the local FFmpeg build."""
        ffmpeg_executable = self.get_ffmpeg_executable()
        if ffmpeg_executable is None:
            return EncoderAvailability(frozenset())

        try:
            result = run(
                [ffmpeg_executable, "-encoders"],
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
        output_quality: str = OUTPUT_QUALITY_BALANCED,
        output_standardization: Optional[OutputStandardization] = None,
    ) -> list[str]:
        """Build an FFmpeg command that blurs the selected region and writes MP4 output."""
        return self.build_recipe_command(
            input_path=input_path,
            output_path=output_path,
            video_width=video_width,
            video_height=video_height,
            encoder=encoder,
            area_cleanup_type=AREA_CLEANUP_TYPE_BLUR,
            selection=selection,
            blur_strength=blur_strength,
            output_quality=output_quality,
            output_standardization=output_standardization,
        )

    def build_logo_overlay_command(
        self,
        input_path: Path | str,
        output_path: Path | str,
        overlay_image_path: Path | str,
        selection: NormalizedSelection,
        video_width: int,
        video_height: int,
        encoder: str,
        output_quality: str = OUTPUT_QUALITY_BALANCED,
        output_standardization: Optional[OutputStandardization] = None,
    ) -> list[str]:
        """Build an FFmpeg command that overlays a scaled logo/image on the selected region."""
        return self.build_recipe_command(
            input_path=input_path,
            output_path=output_path,
            video_width=video_width,
            video_height=video_height,
            encoder=encoder,
            area_cleanup_type=AREA_CLEANUP_TYPE_LOGO,
            selection=selection,
            overlay_image_path=overlay_image_path,
            output_quality=output_quality,
            output_standardization=output_standardization,
        )

    def build_zoom_crop_command(
        self,
        input_path: Path | str,
        output_path: Path | str,
        video_width: int,
        video_height: int,
        zoom_percent: int,
        encoder: str,
        output_quality: str = OUTPUT_QUALITY_BALANCED,
        output_standardization: Optional[OutputStandardization] = None,
    ) -> list[str]:
        """Build an FFmpeg command that scales and center-crops back to the original size."""
        return self.build_recipe_command(
            input_path=input_path,
            output_path=output_path,
            video_width=video_width,
            video_height=video_height,
            encoder=encoder,
            zoom_percent=zoom_percent,
            output_quality=output_quality,
            output_standardization=output_standardization,
        )

    def build_recipe_command(
        self,
        input_path: Path | str,
        output_path: Path | str,
        video_width: int,
        video_height: int,
        encoder: str,
        area_cleanup_type: Optional[str] = None,
        selection: Optional[NormalizedSelection] = None,
        blur_strength: int = 10,
        overlay_image_path: Optional[Path | str] = None,
        zoom_percent: Optional[int] = None,
        output_quality: str = OUTPUT_QUALITY_BALANCED,
        output_standardization: Optional[OutputStandardization] = None,
        pixel_rect: Optional[PixelSelection] = None,
    ) -> list[str]:
        """Build an FFmpeg command for the full export recipe pipeline."""
        input_file = Path(input_path)
        output_file = Path(output_path)
        overlay_file = Path(overlay_image_path) if overlay_image_path is not None else None
        if area_cleanup_type == AREA_CLEANUP_TYPE_LOGO and overlay_file is None:
            raise ValueError("Logo overlay exports require an overlay image path.")
        filter_graph = build_recipe_filter(
            video_width=video_width,
            video_height=video_height,
            area_cleanup_type=area_cleanup_type,
            selection=selection,
            blur_strength=blur_strength,
            zoom_percent=zoom_percent,
            output_standardization=output_standardization,
            pixel_rect=pixel_rect,
        )

        command = [
            self.ffmpeg_path,
            "-y",
            "-i",
            str(input_file),
        ]
        if overlay_file is not None:
            command.extend(["-i", str(overlay_file)])
        command.extend(
            [
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
        )
        command.extend(self._build_output_arguments(encoder, output_file, output_quality))
        return command

    def export_blur_video(
        self,
        video_info: VideoInfo,
        selection: NormalizedSelection,
        output_directory: Path | str,
        blur_strength: int,
        encoder_plan: EncoderPlan,
        output_quality: str = OUTPUT_QUALITY_BALANCED,
        output_standardization: Optional[OutputStandardization] = None,
    ) -> ExportResult:
        """Export one blurred video, retrying with CPU when Auto NVENC fails."""
        return self.export_recipe_video(
            video_info=video_info,
            output_directory=output_directory,
            encoder_plan=encoder_plan,
            area_cleanup_type=AREA_CLEANUP_TYPE_BLUR,
            selection=selection,
            blur_strength=blur_strength,
            output_quality=output_quality,
            output_standardization=output_standardization,
        )

    def export_logo_overlay_video(
        self,
        video_info: VideoInfo,
        selection: NormalizedSelection,
        overlay_image_path: Path | str,
        output_directory: Path | str,
        encoder_plan: EncoderPlan,
        output_quality: str = OUTPUT_QUALITY_BALANCED,
        output_standardization: Optional[OutputStandardization] = None,
    ) -> ExportResult:
        """Export one video with a scaled logo/image overlay."""
        return self.export_recipe_video(
            video_info=video_info,
            output_directory=output_directory,
            encoder_plan=encoder_plan,
            area_cleanup_type=AREA_CLEANUP_TYPE_LOGO,
            selection=selection,
            overlay_image_path=overlay_image_path,
            output_quality=output_quality,
            output_standardization=output_standardization,
        )

    def export_zoom_crop_video(
        self,
        video_info: VideoInfo,
        output_directory: Path | str,
        zoom_percent: int,
        encoder_plan: EncoderPlan,
        output_quality: str = OUTPUT_QUALITY_BALANCED,
        output_standardization: Optional[OutputStandardization] = None,
    ) -> ExportResult:
        """Export one video with a centered zoom/crop effect."""
        return self.export_recipe_video(
            video_info=video_info,
            output_directory=output_directory,
            encoder_plan=encoder_plan,
            zoom_percent=zoom_percent,
            output_quality=output_quality,
            output_standardization=output_standardization,
        )

    def export_recipe_video(
        self,
        video_info: VideoInfo,
        output_directory: Path | str,
        encoder_plan: EncoderPlan,
        area_cleanup_type: Optional[str] = None,
        selection: Optional[NormalizedSelection] = None,
        blur_strength: int = 10,
        overlay_image_path: Optional[Path | str] = None,
        zoom_percent: Optional[int] = None,
        output_quality: str = OUTPUT_QUALITY_BALANCED,
        output_standardization: Optional[OutputStandardization] = None,
    ) -> ExportResult:
        """Export one video using the full multi-effect recipe pipeline."""
        output_path = build_output_path(
            output_directory,
            video_info.file_name,
            suffix=build_recipe_output_suffix(
                area_cleanup_type=area_cleanup_type,
                zoom_enabled=zoom_percent is not None,
                output_standardization=output_standardization,
            ),
        )
        pixel_rect: Optional[PixelSelection] = None
        if area_cleanup_type is not None:
            if selection is None:
                raise ValueError("Area cleanup requires a valid selection.")
            pixel_rect = normalized_selection_to_pixel_rect(
                selection,
                video_info.width,
                video_info.height,
            )

        base_debug_log = build_export_debug_log_header(
            input_path=video_info.file_path,
            output_path=output_path,
            recipe_state=build_recipe_state_description(
                area_cleanup_type=area_cleanup_type,
                blur_strength=blur_strength,
                zoom_percent=zoom_percent,
                overlay_image_path=overlay_image_path,
                output_standardization=output_standardization,
            ),
            video_width=video_info.width,
            video_height=video_info.height,
            selection=selection,
            pixel_rect=pixel_rect,
            output_standardization=output_standardization,
        )
        return self._export_video_with_retry(
            video_info=video_info,
            output_path=output_path,
            encoder_plan=encoder_plan,
            base_debug_log=base_debug_log,
            command_builder=lambda encoder: self.build_recipe_command(
                input_path=video_info.file_path,
                output_path=output_path,
                video_width=video_info.width,
                video_height=video_info.height,
                encoder=encoder,
                area_cleanup_type=area_cleanup_type,
                selection=selection,
                blur_strength=blur_strength,
                overlay_image_path=overlay_image_path,
                zoom_percent=zoom_percent,
                output_quality=output_quality,
                output_standardization=output_standardization,
                pixel_rect=pixel_rect,
            ),
        )

    def _export_video_with_retry(
        self,
        video_info: VideoInfo,
        output_path: Path,
        encoder_plan: EncoderPlan,
        base_debug_log: str,
        command_builder: Callable[[str], list[str]],
    ) -> ExportResult:
        primary_result = self._run_export_attempt(
            video_info=video_info,
            output_path=output_path,
            encoder=encoder_plan.primary_encoder,
            command=command_builder(encoder_plan.primary_encoder),
            attempt_label="primary",
            base_debug_log=base_debug_log,
        )
        if primary_result.success:
            return primary_result

        if encoder_plan.requested_option == ENCODER_OPTION_AUTO and encoder_plan.fallback_encoder:
            fallback_result = self._run_export_attempt(
                video_info=video_info,
                output_path=output_path,
                encoder=encoder_plan.fallback_encoder,
                command=command_builder(encoder_plan.fallback_encoder),
                attempt_label="fallback",
                base_debug_log=base_debug_log,
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
        attempt_label: str,
        base_debug_log: str,
        prior_log_text: str = "",
    ) -> ExportResult:
        completed = self.run_command(command)
        attempt_log = build_ffmpeg_attempt_log(
            base_debug_log=base_debug_log,
            attempt_label=attempt_label,
            encoder=encoder,
            command=command,
            returncode=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )
        combined_log = join_log_text(prior_log_text, attempt_log)
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
    def _build_output_arguments(
        cls,
        encoder: str,
        output_file: Path,
        output_quality: str,
    ) -> list[str]:
        output_arguments = cls._encoder_arguments(encoder, output_quality)
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
    def _encoder_arguments(encoder: str, output_quality: str) -> list[str]:
        return get_encoder_quality_arguments(encoder, output_quality)


def get_encoder_quality_arguments(encoder: str, output_quality: str) -> list[str]:
    """Return codec arguments for the selected encoder and quality preset."""
    quality_profiles = {
        ENCODER_H264_NVENC: {
            OUTPUT_QUALITY_FAST: ["-preset", "p4", "-cq", "28"],
            OUTPUT_QUALITY_BALANCED: ["-preset", "p5", "-cq", "23"],
            OUTPUT_QUALITY_HIGH: ["-preset", "p7", "-cq", "19"],
        },
        ENCODER_LIBX264: {
            OUTPUT_QUALITY_FAST: ["-preset", "veryfast", "-crf", "25"],
            OUTPUT_QUALITY_BALANCED: ["-preset", "medium", "-crf", "23"],
            OUTPUT_QUALITY_HIGH: ["-preset", "slow", "-crf", "20"],
        },
    }

    encoder_profiles = quality_profiles.get(encoder)
    if not encoder_profiles:
        return []

    if output_quality not in encoder_profiles:
        output_quality = OUTPUT_QUALITY_BALANCED
    return list(encoder_profiles[output_quality])


def build_recipe_state_description(
    area_cleanup_type: Optional[str],
    blur_strength: int,
    zoom_percent: Optional[int],
    overlay_image_path: Optional[Path | str],
    output_standardization: Optional[OutputStandardization],
) -> str:
    """Build a compact recipe-state description for export diagnostics."""
    parts: list[str] = []
    if area_cleanup_type == AREA_CLEANUP_TYPE_BLUR:
        parts.append(f"area_cleanup=blur(radius={max(1, int(blur_strength))})")
    elif area_cleanup_type == AREA_CLEANUP_TYPE_LOGO:
        parts.append(
            "area_cleanup=logo"
            f"(overlay={Path(overlay_image_path).name if overlay_image_path is not None else 'missing'})"
        )
    else:
        parts.append("area_cleanup=off")

    if zoom_percent is not None:
        parts.append(f"zoom={int(zoom_percent)}%")
    else:
        parts.append("zoom=off")

    if output_standardization is None:
        parts.append("output=keep_original")
    else:
        parts.append(
            "output="
            f"{output_standardization.target_width}x{output_standardization.target_height}"
            f" ({output_standardization.resize_mode})"
        )

    return ", ".join(parts)


def build_export_debug_log_header(
    input_path: Path | str,
    output_path: Path | str,
    recipe_state: str,
    video_width: int,
    video_height: int,
    selection: Optional[NormalizedSelection],
    pixel_rect: Optional[PixelSelection],
    output_standardization: Optional[OutputStandardization],
) -> str:
    """Build the shared diagnostic header that should appear for every FFmpeg attempt."""
    return "\n".join(
        [
            f"Input path: {input_path}",
            f"Output path: {output_path}",
            f"Recipe state: {recipe_state}",
            f"Input video size: {video_width}x{video_height}",
            f"Normalized selection: {format_normalized_selection(selection)}",
            f"Pixel crop rectangle: {format_pixel_rect(pixel_rect)}",
            f"Output resolution settings: {describe_output_standardization(output_standardization)}",
        ]
    )


def build_ffmpeg_attempt_log(
    base_debug_log: str,
    attempt_label: str,
    encoder: str,
    command: Sequence[str],
    returncode: int,
    stdout: str,
    stderr: str,
) -> str:
    """Build a detailed diagnostic log for one FFmpeg attempt."""
    lines = [
        base_debug_log,
        f"Attempt: {attempt_label}",
        f"Encoder selected: {encoder}",
        f"FFmpeg command: {list2cmdline(list(command))}",
        f"FFmpeg return code: {returncode}",
        "FFmpeg stdout:",
        stdout.strip() or "<empty>",
        "FFmpeg stderr:",
        stderr.strip() or "<empty>",
    ]
    return "\n".join(lines)


def format_normalized_selection(selection: Optional[NormalizedSelection]) -> str:
    """Format normalized selection values for readable export logs."""
    if selection is None:
        return "none"

    normalized = selection.clamped()
    return (
        f"x_percent={normalized.x_percent:.6f}, "
        f"y_percent={normalized.y_percent:.6f}, "
        f"width_percent={normalized.width_percent:.6f}, "
        f"height_percent={normalized.height_percent:.6f}"
    )


def format_pixel_rect(pixel_rect: Optional[PixelSelection]) -> str:
    """Format a pixel crop rectangle for readable export logs."""
    if pixel_rect is None:
        return "none"
    return (
        f"x={pixel_rect.x}, y={pixel_rect.y}, "
        f"width={pixel_rect.width}, height={pixel_rect.height}"
    )


def describe_output_standardization(
    output_standardization: Optional[OutputStandardization],
) -> str:
    """Describe output-size settings in a compact log-friendly format."""
    if output_standardization is None:
        return "Keep original"
    return (
        f"{output_standardization.target_width}x{output_standardization.target_height}"
        f" ({output_standardization.resize_mode})"
    )


def build_safe_boxblur_expression(pixel_rect: PixelSelection, blur_strength: int) -> str:
    """Build a boxblur expression that stays valid for tiny watermark crops."""
    requested_radius = max(1, int(blur_strength))
    luma_radius = min(requested_radius, max_boxblur_radius(pixel_rect.width, pixel_rect.height))
    chroma_radius = min(
        requested_radius,
        max_boxblur_radius(max(pixel_rect.width // 2, 1), max(pixel_rect.height // 2, 1)),
    )
    return (
        "boxblur="
        f"luma_radius={luma_radius}:luma_power=1:"
        f"chroma_radius={chroma_radius}:chroma_power=1"
    )


def max_boxblur_radius(width: int, height: int) -> int:
    """Return the largest valid boxblur radius for a plane of the given size."""
    return max(0, (min(int(width), int(height)) - 1) // 2)


def build_blur_filter(pixel_rect: PixelSelection, blur_strength: int) -> str:
    """Build the FFmpeg filter_complex string for the blur overlay pipeline."""
    return build_blur_filter_step("[0:v]", "[outv]", pixel_rect, blur_strength)


def build_blur_filter_step(
    input_label: str,
    output_label: str,
    pixel_rect: PixelSelection,
    blur_strength: int,
) -> str:
    """Build one blur step within a larger filter graph."""
    blur_expression = build_safe_boxblur_expression(pixel_rect, blur_strength)
    return (
        f"{input_label}split[base][tmp];"
        f"[tmp]crop=w={pixel_rect.width}:h={pixel_rect.height}:x={pixel_rect.x}:y={pixel_rect.y},"
        f"{blur_expression}[blurred];"
        f"[base][blurred]overlay=x={pixel_rect.x}:y={pixel_rect.y}{output_label}"
    )


def build_logo_overlay_filter(pixel_rect: PixelSelection) -> str:
    """Build the FFmpeg filter_complex string for the logo overlay pipeline."""
    return build_logo_overlay_filter_step("[0:v]", "[outv]", pixel_rect)


def build_logo_overlay_filter_step(
    input_label: str,
    output_label: str,
    pixel_rect: PixelSelection,
) -> str:
    """Build one logo-overlay step within a larger filter graph."""
    return (
        f"[1:v]scale=w={pixel_rect.width}:h={pixel_rect.height}:force_original_aspect_ratio=decrease,"
        f"pad={pixel_rect.width}:{pixel_rect.height}:(ow-iw)/2:(oh-ih)/2:color=0x00000000[logo];"
        f"{input_label}[logo]overlay=x={pixel_rect.x}:y={pixel_rect.y}:format=auto{output_label}"
    )


def build_zoom_crop_filter(video_width: int, video_height: int, zoom_percent: int) -> str:
    """Build the FFmpeg filter_complex string for the centered zoom/crop pipeline."""
    return build_zoom_crop_filter_step("[0:v]", "[outv]", video_width, video_height, zoom_percent)


def build_zoom_crop_filter_step(
    input_label: str,
    output_label: str,
    video_width: int,
    video_height: int,
    zoom_percent: int,
) -> str:
    """Build one centered zoom/crop step within a larger filter graph."""
    if video_width <= 0 or video_height <= 0:
        raise ValueError("Video dimensions must be positive integers.")

    zoom_factor = max(float(zoom_percent), 100.0) / 100.0
    scaled_width = max(video_width, int(round(video_width * zoom_factor)))
    scaled_height = max(video_height, int(round(video_height * zoom_factor)))
    return (
        f"{input_label}scale={scaled_width}:{scaled_height},"
        f"crop={video_width}:{video_height}:(iw-{video_width})/2:(ih-{video_height})/2{output_label}"
    )


def append_output_standardization_filter(
    filter_graph: str,
    output_standardization: Optional[OutputStandardization],
) -> str:
    """Append the final output standardization step after the main processing mode."""
    if output_standardization is None:
        return filter_graph
    if not filter_graph.endswith("[outv]"):
        raise ValueError("Filter graph must end with [outv] before standardization is appended.")

    prior_output_label = "[preoutv]"
    base_graph = f"{filter_graph[:-6]}{prior_output_label}"
    resize_filter = build_output_standardization_filter(output_standardization)
    return f"{base_graph};{prior_output_label}{resize_filter}[outv]"


def build_output_standardization_filter(output_standardization: OutputStandardization) -> str:
    """Build the final scale/crop or scale/pad filter for standardized output."""
    target_width = output_standardization.target_width
    target_height = output_standardization.target_height

    if output_standardization.resize_mode == RESIZE_MODE_FILL_AND_CROP:
        return (
            f"scale={target_width}:{target_height}:force_original_aspect_ratio=increase:flags=lanczos,"
            f"crop={target_width}:{target_height}"
        )

    if output_standardization.resize_mode == RESIZE_MODE_FIT_WITH_PADDING:
        return (
            f"scale={target_width}:{target_height}:force_original_aspect_ratio=decrease:flags=lanczos,"
            f"pad={target_width}:{target_height}:(ow-iw)/2:(oh-ih)/2:color=black"
        )

    raise ValueError(f"Unsupported resize mode: {output_standardization.resize_mode}")


def build_output_standardization_filter_step(
    input_label: str,
    output_label: str,
    output_standardization: OutputStandardization,
) -> str:
    """Build one final output-standardization step within a larger filter graph."""
    return f"{input_label}{build_output_standardization_filter(output_standardization)}{output_label}"


def build_recipe_filter(
    video_width: int,
    video_height: int,
    area_cleanup_type: Optional[str] = None,
    selection: Optional[NormalizedSelection] = None,
    blur_strength: int = 10,
    zoom_percent: Optional[int] = None,
    output_standardization: Optional[OutputStandardization] = None,
    pixel_rect: Optional[PixelSelection] = None,
) -> str:
    """Build the ordered multi-effect filter graph for one export recipe."""
    steps: list[str] = []
    current_label = "[0:v]"
    has_zoom = zoom_percent is not None
    has_output_standardization = output_standardization is not None

    if area_cleanup_type is not None:
        if selection is None:
            raise ValueError("Area cleanup requires a valid selection.")
        if pixel_rect is None:
            pixel_rect = normalized_selection_to_pixel_rect(selection, video_width, video_height)
        if has_zoom:
            next_label = "[cleaned]"
        elif has_output_standardization:
            next_label = "[cleaned]"
        else:
            next_label = "[outv]"
        if area_cleanup_type == AREA_CLEANUP_TYPE_BLUR:
            steps.append(build_blur_filter_step(current_label, next_label, pixel_rect, blur_strength))
        elif area_cleanup_type == AREA_CLEANUP_TYPE_LOGO:
            steps.append(build_logo_overlay_filter_step(current_label, next_label, pixel_rect))
        else:
            raise ValueError(f"Unsupported area cleanup type: {area_cleanup_type}")
        current_label = next_label

    if has_zoom:
        next_label = "[zoomed]" if has_output_standardization else "[outv]"
        steps.append(
            build_zoom_crop_filter_step(
                current_label,
                next_label,
                video_width,
                video_height,
                zoom_percent,
            )
        )
        current_label = next_label

    if output_standardization is not None:
        steps.append(
            build_output_standardization_filter_step(
                current_label,
                "[outv]",
                output_standardization,
            )
        )
    elif not steps:
        steps.append(f"{current_label}null[outv]")

    return ";".join(steps)


def build_mode_output_suffix(
    base_suffix: str,
    output_standardization: Optional[OutputStandardization],
) -> str:
    """Build a readable output suffix that includes standardized resolution when used."""
    if output_standardization is None:
        return base_suffix
    return f"{base_suffix}_{output_standardization.resolution_suffix}"


def build_recipe_output_suffix(
    area_cleanup_type: Optional[str],
    zoom_enabled: bool,
    output_standardization: Optional[OutputStandardization],
) -> str:
    """Build a readable filename suffix for a multi-effect recipe export."""
    suffix_parts: list[str] = []

    if area_cleanup_type == AREA_CLEANUP_TYPE_BLUR:
        suffix_parts.append(OUTPUT_SUFFIX_BLURRED.lstrip("_"))
    elif area_cleanup_type == AREA_CLEANUP_TYPE_LOGO:
        suffix_parts.append(OUTPUT_SUFFIX_BRANDED.lstrip("_"))

    if zoom_enabled:
        suffix_parts.append(OUTPUT_SUFFIX_ZOOMED.lstrip("_"))

    if not suffix_parts and output_standardization is not None:
        suffix_parts.append(OUTPUT_SUFFIX_STANDARDIZED.lstrip("_"))
    elif not suffix_parts:
        suffix_parts.append(OUTPUT_SUFFIX_PROCESSED.lstrip("_"))

    return build_mode_output_suffix(f"_{'_'.join(suffix_parts)}", output_standardization)


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
