"""
Main Window for ReelBatch Editor
"""
from __future__ import annotations

from pathlib import Path
from typing import List, Optional

import cv2
from PySide6.QtCore import QSignalBlocker, QThread, QTimer, Qt, QUrl
from PySide6.QtGui import QCloseEvent, QDesktopServices
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from app.preview_canvas import PreviewCanvas
from app.video_queue import VideoQueue
from core.app_settings import AppSettings, AppSettingsStore
from core.export_worker import (
    BatchExportSummary,
    ExportSettings,
    ExportWorker,
    format_export_summary,
)
from core.ffmpeg_processor import (
    ENCODER_OPTION_AUTO,
    ENCODER_OPTION_CPU,
    ENCODER_OPTION_NVIDIA,
    FFMPEG_NOT_FOUND_MESSAGE,
    FFmpegProcessor,
    OUTPUT_QUALITY_BALANCED,
    OUTPUT_QUALITY_OPTIONS,
)
from core.output_resolution import (
    DEFAULT_OUTPUT_RESOLUTION,
    DEFAULT_RESIZE_MODE,
    OUTPUT_RESOLUTION_CUSTOM,
    OUTPUT_RESOLUTION_KEEP_ORIGINAL,
    OUTPUT_RESOLUTION_OPTIONS,
    RESIZE_MODE_FILL_AND_CROP,
    RESIZE_MODE_OPTIONS,
    build_output_standardization,
)
from core.presets import ExportPreset, PresetStore
from core.processing_modes import (
    PROCESSING_MODE_BLUR,
    PROCESSING_MODE_LOGO,
    PROCESSING_MODE_ZOOM,
    processing_mode_progress_label,
    processing_mode_status_text,
    validate_export_request,
)
from core.selection import NormalizedSelection
from core.video_probe import VideoInfo, frame_to_qimage, read_video_metadata
from core.workflow import (
    AREA_CLEANUP_OPTIONS,
    AREA_CLEANUP_OPTION_NONE,
    build_workflow_hint,
    derive_processing_mode,
    format_playback_time,
    frame_index_for_time,
    playback_interval_ms,
    workflow_state_from_processing_mode,
)


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self):
        super().__init__()
        self.current_video_info: Optional[VideoInfo] = None
        self.current_selection: Optional[NormalizedSelection] = None
        self.output_directory: Optional[Path] = None
        self.logo_image_path: Optional[Path] = None

        self.ffmpeg_processor = FFmpegProcessor()
        self.app_settings_store = AppSettingsStore()
        self.preset_store = PresetStore()

        self.export_thread: Optional[QThread] = None
        self.export_worker: Optional[ExportWorker] = None
        self._active_export_scope_label = "batch"
        self._is_restoring_app_settings = False
        self._is_syncing_workflow_controls = False

        self.preview_timer = QTimer(self)
        self.preview_capture: Optional[cv2.VideoCapture] = None
        self.preview_fps = 30.0
        self.preview_frame_count = 0
        self.preview_duration_seconds = 0.0
        self.preview_current_frame = 0
        self._timeline_scrubbing = False
        self._resume_playback_after_scrub = False

        self.setWindowTitle("ReelBatch Editor")
        self.setMinimumSize(1280, 840)
        self.setup_ui()
        self.connect_signals()
        self.load_app_settings()
        self.update_mode_controls()
        self.update_output_resolution_controls()
        self.update_workflow_hint()
        self.update_action_states()

    def setup_ui(self) -> None:
        """Set up the main window UI."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        content_layout = QHBoxLayout()
        content_layout.setSpacing(10)
        main_layout.addLayout(content_layout)

        self.video_queue = VideoQueue()
        self.video_queue.setMaximumWidth(290)
        content_layout.addWidget(self.video_queue)

        center_panel = QFrame()
        center_panel.setObjectName("panelCard")
        center_panel.setStyleSheet(self._panel_style())
        center_layout = QVBoxLayout(center_panel)
        center_layout.setContentsMargins(16, 16, 16, 16)
        center_layout.setSpacing(12)

        preview_title = QLabel("Preview")
        preview_title.setObjectName("panelTitle")
        center_layout.addWidget(preview_title)

        self.preview_canvas = PreviewCanvas()
        center_layout.addWidget(self.preview_canvas, stretch=1)

        playback_row = QHBoxLayout()
        playback_row.setSpacing(10)

        self.play_pause_button = QPushButton("Play")
        self._set_secondary_button_style(self.play_pause_button)
        playback_row.addWidget(self.play_pause_button)

        self.timeline_slider = QSlider(Qt.Horizontal)
        self.timeline_slider.setRange(0, 0)
        self.timeline_slider.setEnabled(False)
        self.timeline_slider.setStyleSheet(self._slider_style())
        playback_row.addWidget(self.timeline_slider, stretch=1)

        self.time_label = QLabel("0:00 / 0:00")
        self.time_label.setMinimumWidth(110)
        self.time_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.time_label.setStyleSheet("color: #cfcfcf; font-size: 12px;")
        playback_row.addWidget(self.time_label)

        center_layout.addLayout(playback_row)
        content_layout.addWidget(center_panel, stretch=1)

        right_panel = QFrame()
        right_panel.setObjectName("settingsPanel")
        right_panel.setStyleSheet(self._panel_style())
        right_panel.setMinimumWidth(380)
        right_panel.setMaximumWidth(430)
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        self.settings_scroll_area = QScrollArea()
        self.settings_scroll_area.setObjectName("settingsScrollArea")
        self.settings_scroll_area.setWidgetResizable(True)
        self.settings_scroll_area.setFrameShape(QFrame.NoFrame)
        self.settings_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        settings_content = QWidget()
        settings_content.setObjectName("settingsScrollContent")
        settings_layout = QVBoxLayout(settings_content)
        settings_layout.setContentsMargins(16, 16, 16, 16)
        settings_layout.setSpacing(14)

        settings_title = QLabel("Creator Workflow")
        settings_title.setObjectName("panelTitle")
        settings_layout.addWidget(settings_title)

        self.workflow_hint_label = QLabel()
        self.workflow_hint_label.setObjectName("workflowHintLabel")
        self.workflow_hint_label.setWordWrap(True)
        self.workflow_hint_label.setMinimumHeight(72)
        settings_layout.addWidget(self.workflow_hint_label)

        self.area_cleanup_section, area_layout = self._create_section(
            "Area Cleanup",
            "Choose how to handle the selected logo or watermark area.",
        )
        area_layout.addWidget(self._create_field_label("Area Cleanup"))
        self.area_cleanup_combo = QComboBox()
        self.area_cleanup_combo.addItems(list(AREA_CLEANUP_OPTIONS))
        self.area_cleanup_combo.setStyleSheet(self._combo_style())
        self._configure_panel_control(self.area_cleanup_combo, minimum_width=220)
        area_layout.addWidget(self.area_cleanup_combo)

        self.area_cleanup_helper_label = self._create_helper_label(
            "Draw a rectangle on the preview to choose the logo/watermark area."
        )
        self.area_cleanup_helper_label.setObjectName("accentHelperLabel")
        area_layout.addWidget(self.area_cleanup_helper_label)

        self.mode_help_label = self._create_helper_label()
        area_layout.addWidget(self.mode_help_label)

        self.blur_controls = QWidget()
        self.blur_controls.setObjectName("modeControls")
        blur_layout = QVBoxLayout(self.blur_controls)
        blur_layout.setContentsMargins(0, 0, 0, 0)
        blur_layout.setSpacing(8)
        blur_layout.addWidget(self._create_field_label("Blur Strength"))
        blur_row = QHBoxLayout()
        blur_row.setSpacing(10)
        self.blur_slider = QSlider(Qt.Horizontal)
        self.blur_slider.setRange(1, 20)
        self.blur_slider.setValue(10)
        self.blur_slider.setStyleSheet(self._slider_style())
        blur_row.addWidget(self.blur_slider, stretch=1)
        self.blur_value_label = QLabel("10")
        self.blur_value_label.setObjectName("valueBadge")
        self.blur_value_label.setMinimumWidth(28)
        self.blur_value_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        blur_row.addWidget(self.blur_value_label)
        blur_layout.addLayout(blur_row)
        area_layout.addWidget(self.blur_controls)

        self.logo_controls = QWidget()
        self.logo_controls.setObjectName("modeControls")
        logo_layout = QVBoxLayout(self.logo_controls)
        logo_layout.setContentsMargins(0, 0, 0, 0)
        logo_layout.setSpacing(8)
        self.logo_button = QPushButton("Choose Logo/Image")
        self._set_secondary_button_style(self.logo_button)
        self._configure_panel_control(self.logo_button, minimum_width=220)
        logo_layout.addWidget(self.logo_button)
        self.logo_file_label = self._create_helper_label("No logo/image selected")
        logo_layout.addWidget(self.logo_file_label)
        area_layout.addWidget(self.logo_controls)

        self.selection_section = QFrame()
        self.selection_section.setObjectName("selectionCard")
        self.selection_section.setStyleSheet(self._subsection_style())
        selection_layout = QVBoxLayout(self.selection_section)
        selection_layout.setContentsMargins(14, 14, 14, 14)
        selection_layout.setSpacing(10)

        selection_title = QLabel("Selected Area")
        selection_title.setObjectName("sectionTitle")
        selection_layout.addWidget(selection_title)

        self.selection_requirement_label = self._create_helper_label()
        selection_layout.addWidget(self.selection_requirement_label)

        selection_grid = QGridLayout()
        selection_grid.setHorizontalSpacing(12)
        selection_grid.setVerticalSpacing(10)
        selection_grid.setColumnStretch(0, 1)
        selection_grid.setColumnStretch(1, 1)
        self.selection_value_labels: dict[str, QLabel] = {}
        selection_fields = [
            ("X %", "x_percent"),
            ("Y %", "y_percent"),
            ("Width %", "width_percent"),
            ("Height %", "height_percent"),
        ]
        for row, (label_text, key) in enumerate(selection_fields):
            field_label = self._create_field_label(label_text)
            selection_grid.addWidget(field_label, row, 0)

            value_label = QLabel("--")
            value_label.setObjectName("valueBadge")
            value_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            value_label.setMinimumWidth(88)
            selection_grid.addWidget(value_label, row, 1)
            self.selection_value_labels[key] = value_label
        selection_layout.addLayout(selection_grid)

        self.clear_selection_button = QPushButton("Clear Selection")
        self._set_secondary_button_style(self.clear_selection_button)
        self._configure_panel_control(self.clear_selection_button)
        selection_layout.addWidget(self.clear_selection_button)
        area_layout.addWidget(self.selection_section)

        settings_layout.addWidget(self.area_cleanup_section)

        self.transform_section, transform_layout = self._create_section(
            "Transform",
            "Zoom/crop is available as its own export mode for this phase.",
        )
        self.apply_zoom_checkbox = QCheckBox("Apply zoom/crop")
        transform_layout.addWidget(self.apply_zoom_checkbox)

        self.transform_help_label = self._create_helper_label()
        transform_layout.addWidget(self.transform_help_label)

        transform_layout.addWidget(self._create_field_label("Zoom Percentage"))
        zoom_row = QHBoxLayout()
        zoom_row.setSpacing(10)
        self.zoom_slider = QSlider(Qt.Horizontal)
        self.zoom_slider.setRange(100, 150)
        self.zoom_slider.setValue(110)
        self.zoom_slider.setStyleSheet(self._slider_style())
        zoom_row.addWidget(self.zoom_slider, stretch=1)
        self.zoom_value_label = QLabel("110%")
        self.zoom_value_label.setObjectName("valueBadge")
        self.zoom_value_label.setMinimumWidth(44)
        self.zoom_value_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        zoom_row.addWidget(self.zoom_value_label)
        transform_layout.addLayout(zoom_row)
        settings_layout.addWidget(self.transform_section)

        self.output_section, output_layout = self._create_section(
            "Output",
            "Choose where files go and how they should be encoded.",
        )
        output_layout.addWidget(self._create_field_label("Output Folder"))
        self.output_button = QPushButton("Choose Output Folder")
        self._set_secondary_button_style(self.output_button)
        self._configure_panel_control(self.output_button, minimum_width=220)
        output_layout.addWidget(self.output_button)
        self.output_folder_label = self._create_helper_label("No output folder selected")
        output_layout.addWidget(self.output_folder_label)

        output_layout.addWidget(self._create_field_label("Output Resolution"))
        self.output_resolution_combo = QComboBox()
        self.output_resolution_combo.addItems(list(OUTPUT_RESOLUTION_OPTIONS))
        self.output_resolution_combo.setCurrentText(DEFAULT_OUTPUT_RESOLUTION)
        self.output_resolution_combo.setStyleSheet(self._combo_style())
        self._configure_panel_control(self.output_resolution_combo, minimum_width=220)
        output_layout.addWidget(self.output_resolution_combo)

        self.custom_resolution_controls = QWidget()
        custom_resolution_layout = QHBoxLayout(self.custom_resolution_controls)
        custom_resolution_layout.setContentsMargins(0, 0, 0, 0)
        custom_resolution_layout.setSpacing(8)

        custom_width_label = self._create_field_label("Width")
        custom_width_label.setMinimumWidth(42)
        custom_resolution_layout.addWidget(custom_width_label)
        self.custom_output_width_spin = QSpinBox()
        self.custom_output_width_spin.setRange(2, 7680)
        self.custom_output_width_spin.setSingleStep(2)
        self.custom_output_width_spin.setValue(1080)
        self._configure_panel_control(self.custom_output_width_spin, minimum_width=90)
        custom_resolution_layout.addWidget(self.custom_output_width_spin)

        custom_height_label = self._create_field_label("Height")
        custom_height_label.setMinimumWidth(48)
        custom_resolution_layout.addWidget(custom_height_label)
        self.custom_output_height_spin = QSpinBox()
        self.custom_output_height_spin.setRange(2, 7680)
        self.custom_output_height_spin.setSingleStep(2)
        self.custom_output_height_spin.setValue(1920)
        self._configure_panel_control(self.custom_output_height_spin, minimum_width=90)
        custom_resolution_layout.addWidget(self.custom_output_height_spin)
        output_layout.addWidget(self.custom_resolution_controls)

        output_layout.addWidget(self._create_field_label("Resize Mode"))
        self.resize_mode_combo = QComboBox()
        self.resize_mode_combo.addItems(list(RESIZE_MODE_OPTIONS))
        self.resize_mode_combo.setCurrentText(DEFAULT_RESIZE_MODE)
        self.resize_mode_combo.setStyleSheet(self._combo_style())
        self._configure_panel_control(self.resize_mode_combo, minimum_width=220)
        output_layout.addWidget(self.resize_mode_combo)

        self.output_resolution_help_label = self._create_helper_label()
        output_layout.addWidget(self.output_resolution_help_label)

        output_layout.addWidget(self._create_field_label("Output Quality"))
        self.output_quality_combo = QComboBox()
        self.output_quality_combo.addItems(list(OUTPUT_QUALITY_OPTIONS))
        self.output_quality_combo.setCurrentText(OUTPUT_QUALITY_BALANCED)
        self.output_quality_combo.setStyleSheet(self._combo_style())
        self._configure_panel_control(self.output_quality_combo, minimum_width=220)
        output_layout.addWidget(self.output_quality_combo)

        output_layout.addWidget(self._create_field_label("Encoder"))
        self.encoder_combo = QComboBox()
        self.encoder_combo.addItems([ENCODER_OPTION_AUTO, ENCODER_OPTION_CPU, ENCODER_OPTION_NVIDIA])
        self.encoder_combo.setStyleSheet(self._combo_style())
        self._configure_panel_control(self.encoder_combo, minimum_width=220)
        output_layout.addWidget(self.encoder_combo)

        self.encoder_help_label = self._create_helper_label(
            "Auto uses NVIDIA GPU encoding when available and falls back to CPU if needed."
        )
        output_layout.addWidget(self.encoder_help_label)
        settings_layout.addWidget(self.output_section)

        self.presets_section, presets_layout = self._create_section(
            "Presets",
            "Save and load reusable creator workflow setups.",
        )
        preset_buttons = QHBoxLayout()
        preset_buttons.setSpacing(10)
        self.save_preset_button = QPushButton("Save Preset")
        self._set_secondary_button_style(self.save_preset_button)
        self._configure_panel_control(self.save_preset_button, minimum_width=140)
        preset_buttons.addWidget(self.save_preset_button)
        self.load_preset_button = QPushButton("Load Preset")
        self._set_secondary_button_style(self.load_preset_button)
        self._configure_panel_control(self.load_preset_button, minimum_width=140)
        preset_buttons.addWidget(self.load_preset_button)
        presets_layout.addLayout(preset_buttons)
        settings_layout.addWidget(self.presets_section)

        settings_layout.addStretch(1)
        self.settings_scroll_area.setWidget(settings_content)
        right_layout.addWidget(self.settings_scroll_area)
        content_layout.addWidget(right_panel)

        bottom_panel = QFrame()
        bottom_panel.setObjectName("panelCard")
        bottom_panel.setStyleSheet(self._panel_style())
        bottom_layout = QHBoxLayout(bottom_panel)
        bottom_layout.setContentsMargins(16, 12, 16, 12)
        bottom_layout.setSpacing(10)

        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("color: #e0e0e0; font-size: 13px;")
        bottom_layout.addWidget(self.status_label, stretch=1)

        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet(
            "QProgressBar { background-color: #3a3a3a; border: none; border-radius: 4px; "
            "height: 20px; text-align: center; } "
            "QProgressBar::chunk { background-color: #0078d4; border-radius: 4px; }"
        )
        self.progress_bar.setMaximumWidth(260)
        self.progress_bar.setValue(0)
        bottom_layout.addWidget(self.progress_bar)

        self.test_export_button = QPushButton("Test Export Current Video")
        self._set_secondary_button_style(self.test_export_button)
        bottom_layout.addWidget(self.test_export_button)

        self.export_button = QPushButton("Export All")
        self.export_button.setStyleSheet(
            "QPushButton { background-color: #107c10; color: white; border: none; border-radius: 6px; "
            "padding: 10px 20px; font-size: 14px; font-weight: bold; } "
            "QPushButton:hover { background-color: #0b8a0b; } "
            "QPushButton:pressed { background-color: #0a6c0a; } "
            "QPushButton:disabled { background-color: #355635; color: #b8d0b8; }"
        )
        bottom_layout.addWidget(self.export_button)

        main_layout.addWidget(bottom_panel)

    def connect_signals(self) -> None:
        """Connect signals to handlers."""
        self.video_queue.connect_signals(self.on_add_videos, self.on_clear_queue)
        self.video_queue.video_selected.connect(self.on_video_selected)
        self.preview_canvas.selection_changed.connect(self.on_selection_changed)

        self.preview_timer.timeout.connect(self.on_preview_timer_tick)
        self.play_pause_button.clicked.connect(self.toggle_playback)
        self.timeline_slider.sliderPressed.connect(self.on_timeline_scrub_started)
        self.timeline_slider.sliderReleased.connect(self.on_timeline_scrub_finished)
        self.timeline_slider.valueChanged.connect(self.on_timeline_value_changed)

        self.area_cleanup_combo.currentTextChanged.connect(self.on_area_cleanup_changed)
        self.apply_zoom_checkbox.toggled.connect(self.on_zoom_toggle_changed)
        self.logo_button.clicked.connect(self.on_select_logo)
        self.output_button.clicked.connect(self.on_select_output)
        self.save_preset_button.clicked.connect(self.on_save_preset)
        self.load_preset_button.clicked.connect(self.on_load_preset)
        self.clear_selection_button.clicked.connect(self.on_clear_selection)
        self.output_resolution_combo.currentTextChanged.connect(self.on_output_resolution_changed)
        self.resize_mode_combo.currentTextChanged.connect(self.on_resize_mode_changed)
        self.custom_output_width_spin.valueChanged.connect(self.on_custom_resolution_changed)
        self.custom_output_height_spin.valueChanged.connect(self.on_custom_resolution_changed)

        self.blur_slider.valueChanged.connect(self.update_slider_labels)
        self.zoom_slider.valueChanged.connect(self.update_slider_labels)
        self.blur_slider.valueChanged.connect(self.on_persistent_setting_changed)
        self.zoom_slider.valueChanged.connect(self.on_persistent_setting_changed)
        self.encoder_combo.currentTextChanged.connect(self.on_persistent_setting_changed)
        self.output_quality_combo.currentTextChanged.connect(self.on_persistent_setting_changed)

        self.export_button.clicked.connect(self.on_export_all)
        self.test_export_button.clicked.connect(self.on_test_export_current_video)

        self.apply_tooltips()
        self.update_slider_labels()

    def on_add_videos(self) -> None:
        """Open the file dialog and import one or more videos."""
        file_dialog = QFileDialog(self)
        file_dialog.setFileMode(QFileDialog.ExistingFiles)
        file_dialog.setNameFilter("Video Files (*.mp4 *.mov *.mkv *.avi)")

        if file_dialog.exec():
            selected_files = file_dialog.selectedFiles()
            if selected_files:
                self.import_videos(selected_files)

    def on_clear_queue(self) -> None:
        """Clear all videos and reset the preview playback state."""
        self.pause_preview_playback()
        self.release_preview_capture()
        self.current_video_info = None
        self.current_selection = None
        self.video_queue.clear_queue()
        self.preview_canvas.clear_preview()
        self.update_selection_display(None)
        self.reset_timeline_controls()
        self.progress_bar.setValue(0)
        self.status_label.setText("Queue cleared")
        self.update_mode_controls()
        self.update_workflow_hint()
        self.update_action_states()

    def on_video_selected(self, video_info: Optional[VideoInfo]) -> None:
        """Update preview playback when the selected queue item changes."""
        self.pause_preview_playback()
        self.release_preview_capture()
        self.current_video_info = video_info

        if video_info is None:
            self.preview_canvas.clear_preview()
            self.reset_timeline_controls()
            self.status_label.setText("Ready")
            self.update_workflow_hint()
            self.update_action_states()
            return

        if self.load_video_for_preview(video_info):
            self.status_label.setText(f"Selected video: {video_info.file_name}")
        else:
            self.preview_canvas.clear_preview()
            self.reset_timeline_controls()
            self.status_label.setText(f"Preview error: {video_info.file_name}")

        self.update_workflow_hint()
        self.update_action_states()

    def import_videos(self, file_paths: List[str]) -> None:
        """Import video files from the given paths."""
        video_infos: list[VideoInfo] = []
        failed_files: list[str] = []

        for file_path in file_paths:
            video_info = read_video_metadata(file_path)
            if video_info:
                video_infos.append(video_info)
            else:
                failed_files.append(file_path)

        added_count, skipped_count = self.video_queue.add_videos(video_infos)

        if added_count > 0:
            if self.video_queue.get_selected_video() is None and self.video_queue.video_list.count() > 0:
                self.video_queue.video_list.setCurrentRow(0)
            self.status_label.setText(f"Imported {added_count} videos")

        if failed_files:
            self.status_label.setText(f"Failed to read {len(failed_files)} files")
            error_msg = f"Failed to read {len(failed_files)} files:\n\n"
            error_msg += "\n".join([f"• {path}" for path in failed_files[:5]])
            if len(failed_files) > 5:
                error_msg += f"\n... and {len(failed_files) - 5} more"
            QMessageBox.warning(self, "Import Errors", error_msg)

        if skipped_count > 0:
            self.status_label.setText(f"Imported {added_count} videos, skipped {skipped_count} duplicates")

        self.update_workflow_hint()
        self.update_action_states()

    def load_video_for_preview(self, video_info: VideoInfo) -> bool:
        """Open the selected video for frame-by-frame OpenCV preview playback."""
        capture = cv2.VideoCapture(video_info.file_path)
        if not capture.isOpened():
            return False

        self.preview_capture = capture
        self.preview_fps = video_info.fps if video_info.fps > 0 else capture.get(cv2.CAP_PROP_FPS) or 30.0
        if self.preview_fps <= 0:
            self.preview_fps = 30.0

        capture_frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
        self.preview_frame_count = max(video_info.frame_count, capture_frame_count, 1)
        if video_info.duration_seconds > 0:
            self.preview_duration_seconds = video_info.duration_seconds
        else:
            self.preview_duration_seconds = self.preview_frame_count / self.preview_fps

        initial_frame = frame_index_for_time(1.0, self.preview_fps, self.preview_frame_count)
        if not self.seek_preview_to_frame(initial_frame):
            if not self.seek_preview_to_frame(0):
                self.release_preview_capture()
                return False

        self.timeline_slider.setEnabled(self.preview_frame_count > 1)
        self.play_pause_button.setEnabled(self.preview_frame_count > 0)
        self.update_action_states()
        return True

    def seek_preview_to_frame(self, frame_index: int) -> bool:
        """Seek to a specific frame and refresh the preview canvas."""
        if self.preview_capture is None or self.current_video_info is None:
            return False

        safe_frame = min(max(int(frame_index), 0), max(self.preview_frame_count - 1, 0))
        self.preview_capture.set(cv2.CAP_PROP_POS_FRAMES, safe_frame)
        success, frame = self.preview_capture.read()
        if not success or frame is None:
            return False

        preview_image = frame_to_qimage(frame)
        if preview_image is None:
            return False

        self.preview_current_frame = safe_frame
        self.preview_canvas.set_preview(
            preview_image,
            video_width=self.current_video_info.width,
            video_height=self.current_video_info.height,
        )
        self.preview_canvas.set_normalized_selection(self.current_selection)
        self.update_timeline_display(safe_frame)
        return True

    def update_timeline_display(self, frame_index: int) -> None:
        """Refresh the playback slider and time label."""
        max_frame = max(self.preview_frame_count - 1, 0)
        with QSignalBlocker(self.timeline_slider):
            self.timeline_slider.setRange(0, max_frame)
            self.timeline_slider.setValue(min(max(frame_index, 0), max_frame))

        current_seconds = 0.0
        if self.preview_fps > 0:
            current_seconds = min(frame_index / self.preview_fps, self.preview_duration_seconds)
        self.time_label.setText(
            f"{format_playback_time(current_seconds)} / {format_playback_time(self.preview_duration_seconds)}"
        )

    def reset_timeline_controls(self) -> None:
        """Return the playback controls to their empty state."""
        self.preview_frame_count = 0
        self.preview_duration_seconds = 0.0
        self.preview_current_frame = 0
        with QSignalBlocker(self.timeline_slider):
            self.timeline_slider.setRange(0, 0)
            self.timeline_slider.setValue(0)
        self.timeline_slider.setEnabled(False)
        self.play_pause_button.setText("Play")
        self.play_pause_button.setEnabled(False)
        self.time_label.setText("0:00 / 0:00")

    def on_preview_timer_tick(self) -> None:
        """Advance preview playback by one frame."""
        if self.preview_capture is None or self.current_video_info is None:
            self.pause_preview_playback()
            return

        success, frame = self.preview_capture.read()
        if not success or frame is None:
            self.pause_preview_playback()
            self.preview_current_frame = max(self.preview_frame_count - 1, 0)
            self.update_timeline_display(self.preview_current_frame)
            return

        preview_image = frame_to_qimage(frame)
        if preview_image is None:
            self.pause_preview_playback()
            return

        current_frame = int(self.preview_capture.get(cv2.CAP_PROP_POS_FRAMES)) - 1
        self.preview_current_frame = min(max(current_frame, 0), max(self.preview_frame_count - 1, 0))
        self.preview_canvas.set_preview(
            preview_image,
            video_width=self.current_video_info.width,
            video_height=self.current_video_info.height,
        )
        self.preview_canvas.set_normalized_selection(self.current_selection)
        self.update_timeline_display(self.preview_current_frame)

        if self.preview_current_frame >= max(self.preview_frame_count - 1, 0):
            self.pause_preview_playback()

    def toggle_playback(self) -> None:
        """Play or pause the preview."""
        if self.preview_timer.isActive():
            self.pause_preview_playback()
            return

        if self.preview_capture is None:
            return

        if self.preview_current_frame >= max(self.preview_frame_count - 1, 0):
            self.seek_preview_to_frame(0)

        self.preview_timer.start(playback_interval_ms(self.preview_fps))
        self.play_pause_button.setText("Pause")

    def pause_preview_playback(self) -> None:
        """Pause preview playback without releasing the capture."""
        if self.preview_timer.isActive():
            self.preview_timer.stop()
        self.play_pause_button.setText("Play")

    def release_preview_capture(self) -> None:
        """Release the active OpenCV capture if one is open."""
        if self.preview_capture is not None:
            self.preview_capture.release()
            self.preview_capture = None

    def on_timeline_scrub_started(self) -> None:
        """Pause playback while the user drags the timeline."""
        self._timeline_scrubbing = True
        self._resume_playback_after_scrub = self.preview_timer.isActive()
        if self._resume_playback_after_scrub:
            self.pause_preview_playback()

    def on_timeline_value_changed(self, value: int) -> None:
        """Seek while the user scrubs the timeline."""
        if self._timeline_scrubbing:
            self.seek_preview_to_frame(value)

    def on_timeline_scrub_finished(self) -> None:
        """Finalize a timeline seek and optionally resume playback."""
        self._timeline_scrubbing = False
        self.seek_preview_to_frame(self.timeline_slider.value())
        if self._resume_playback_after_scrub:
            self.toggle_playback()
        self._resume_playback_after_scrub = False

    def on_selection_changed(self, selection: Optional[dict]) -> None:
        """Update the settings panel when the canvas selection changes."""
        self.current_selection = NormalizedSelection.from_mapping(selection)
        self.update_selection_display(self.current_selection)
        self.update_workflow_hint()
        self.update_mode_controls()
        self.status_label.setText("Selection updated" if self.current_selection else "Selection cleared")

    def on_clear_selection(self) -> None:
        """Clear the current rectangle selection."""
        self.preview_canvas.clear_selection()

    def update_selection_display(self, selection: Optional[NormalizedSelection]) -> None:
        """Refresh the selection values shown in the settings panel."""
        if selection is None:
            for value_label in self.selection_value_labels.values():
                value_label.setText("--")
            return

        normalized = selection.to_dict()
        for key, value_label in self.selection_value_labels.items():
            value_label.setText(f"{normalized[key]:.2f}")

    def get_current_processing_mode(self) -> Optional[str]:
        """Return the currently active export mode derived from the simplified UI."""
        return derive_processing_mode(
            self.area_cleanup_combo.currentText(),
            self.apply_zoom_checkbox.isChecked(),
        )

    def on_area_cleanup_changed(self, area_cleanup_mode: str) -> None:
        """Keep the simplified cleanup and transform controls in a clear state."""
        if self._is_syncing_workflow_controls:
            return

        self._is_syncing_workflow_controls = True
        try:
            if area_cleanup_mode != AREA_CLEANUP_OPTION_NONE and self.apply_zoom_checkbox.isChecked():
                self.apply_zoom_checkbox.setChecked(False)
        finally:
            self._is_syncing_workflow_controls = False

        self.update_mode_controls()
        self.update_workflow_hint()
        self.on_persistent_setting_changed()
        if area_cleanup_mode != AREA_CLEANUP_OPTION_NONE:
            self.status_label.setText(processing_mode_status_text(area_cleanup_mode))

    def on_zoom_toggle_changed(self, checked: bool) -> None:
        """Keep zoom/crop distinct from area cleanup for this phase."""
        if self._is_syncing_workflow_controls:
            return

        self._is_syncing_workflow_controls = True
        try:
            if checked and self.area_cleanup_combo.currentText() != AREA_CLEANUP_OPTION_NONE:
                self.area_cleanup_combo.setCurrentText(AREA_CLEANUP_OPTION_NONE)
        finally:
            self._is_syncing_workflow_controls = False

        self.update_mode_controls()
        self.update_workflow_hint()
        self.on_persistent_setting_changed()
        if checked:
            self.status_label.setText(processing_mode_status_text(PROCESSING_MODE_ZOOM))

    def on_output_resolution_changed(self, _value: str) -> None:
        """Refresh custom resolution controls and persist the new choice."""
        self.update_output_resolution_controls()
        self.on_persistent_setting_changed()

    def on_resize_mode_changed(self, _value: str) -> None:
        """Refresh helper text and persist the new resize mode."""
        self.update_output_resolution_controls()
        self.on_persistent_setting_changed()

    def on_custom_resolution_changed(self, value: int) -> None:
        """Keep custom dimensions even-numbered and persist them."""
        spinbox = self.sender()
        if isinstance(spinbox, QSpinBox) and value % 2 != 0:
            with QSignalBlocker(spinbox):
                spinbox.setValue(value + 1)
        self.update_output_resolution_controls()
        self.on_persistent_setting_changed()

    def update_mode_controls(self) -> None:
        """Show only the most relevant controls for the current workflow choice."""
        current_mode = self.get_current_processing_mode()
        area_cleanup_mode = self.area_cleanup_combo.currentText()
        is_blur_mode = area_cleanup_mode == PROCESSING_MODE_BLUR and current_mode == PROCESSING_MODE_BLUR
        is_logo_mode = area_cleanup_mode == PROCESSING_MODE_LOGO and current_mode == PROCESSING_MODE_LOGO
        is_zoom_mode = current_mode == PROCESSING_MODE_ZOOM

        self.blur_controls.setVisible(is_blur_mode)
        self.blur_controls.setEnabled(is_blur_mode)
        self.logo_controls.setVisible(is_logo_mode)
        self.logo_controls.setEnabled(is_logo_mode)
        zoom_enabled = self.apply_zoom_checkbox.isChecked()
        self.zoom_slider.setEnabled(zoom_enabled)
        self.zoom_value_label.setEnabled(zoom_enabled)

        if is_zoom_mode:
            self.mode_help_label.setText(processing_mode_status_text(PROCESSING_MODE_ZOOM))
            self.transform_help_label.setText("Zoom/crop is active. The rectangle selection is not used for export.")
            self.selection_requirement_label.setText(
                "Rectangle selection is optional right now because zoom/crop exports do not use it."
            )
        elif is_blur_mode:
            self.mode_help_label.setText(processing_mode_status_text(PROCESSING_MODE_BLUR))
            self.transform_help_label.setText("Enable zoom/crop when you want a separate zoom-only export.")
            self.selection_requirement_label.setText("This selection will be blurred during export.")
        elif is_logo_mode:
            self.mode_help_label.setText(processing_mode_status_text(PROCESSING_MODE_LOGO))
            self.transform_help_label.setText("Enable zoom/crop when you want a separate zoom-only export.")
            self.selection_requirement_label.setText("This selection will be covered by your chosen logo/image.")
        else:
            self.mode_help_label.setText("Choose an Area Cleanup option or enable zoom/crop before exporting.")
            self.transform_help_label.setText("The zoom slider is only active when Apply zoom/crop is enabled.")
            self.selection_requirement_label.setText(
                "Draw a rectangle now if you plan to blur or cover a logo/watermark area."
            )

    def update_output_resolution_controls(self) -> None:
        """Show custom resolution inputs only when they are relevant."""
        selected_resolution = self.output_resolution_combo.currentText()
        is_custom_resolution = selected_resolution == OUTPUT_RESOLUTION_CUSTOM
        self.custom_resolution_controls.setVisible(is_custom_resolution)
        self.custom_output_width_spin.setEnabled(is_custom_resolution)
        self.custom_output_height_spin.setEnabled(is_custom_resolution)

        selected_resize_mode = self.resize_mode_combo.currentText()
        if selected_resolution == DEFAULT_OUTPUT_RESOLUTION:
            resolution_text = "1080x1920 is recommended for standard vertical reels."
        elif selected_resolution == OUTPUT_RESOLUTION_CUSTOM:
            resolution_text = "Custom width and height must stay positive even numbers."
        else:
            resolution_text = f"Exports will be standardized to {selected_resolution}."

        if selected_resolution == OUTPUT_RESOLUTION_KEEP_ORIGINAL:
            resize_text = "Keep original skips final resizing and leaves the source dimensions unchanged."
        elif selected_resize_mode == RESIZE_MODE_FILL_AND_CROP:
            resize_text = "Fill & Crop scales to fill the frame and center-crops overflow."
        else:
            resize_text = "Fit with Padding preserves the full frame and pads any empty space."

        self.output_resolution_help_label.setText(f"{resolution_text} {resize_text}")

    def update_slider_labels(self, *_args) -> None:
        """Keep the slider value labels in sync with the current controls."""
        self.blur_value_label.setText(f"{self.blur_slider.value()}")
        self.zoom_value_label.setText(f"{self.zoom_slider.value()}%")

    def update_workflow_hint(self) -> None:
        """Refresh the guided workflow hint based on the current app state."""
        self.workflow_hint_label.setText(
            build_workflow_hint(
                video_count=self.video_queue.get_video_count(),
                has_selection=self.current_selection is not None,
                processing_mode=self.get_current_processing_mode(),
                has_output_directory=self.output_directory is not None,
                is_exporting=self.export_worker is not None,
            )
        )

    def build_current_preset(self, preset_name: str) -> ExportPreset:
        """Build a preset object from the current workflow state."""
        processing_mode = self.get_current_processing_mode() or self.area_cleanup_combo.currentText()
        return ExportPreset(
            name=preset_name,
            processing_mode=processing_mode,
            blur_strength=self.blur_slider.value(),
            zoom_percentage=self.zoom_slider.value(),
            encoder_preference=self.encoder_combo.currentText(),
            output_quality=self.output_quality_combo.currentText(),
            output_resolution=self.output_resolution_combo.currentText(),
            resize_mode=self.resize_mode_combo.currentText(),
            custom_output_width=self.custom_output_width_spin.value(),
            custom_output_height=self.custom_output_height_spin.value(),
            selection=self.current_selection,
            logo_image_path=str(self.logo_image_path) if self.logo_image_path else None,
        )

    def apply_preset(self, preset: ExportPreset) -> Optional[str]:
        """Apply a loaded preset and return any friendly warning text."""
        self.current_selection = preset.selection

        area_cleanup_mode, apply_zoom = workflow_state_from_processing_mode(preset.processing_mode)
        self._is_syncing_workflow_controls = True
        try:
            self.area_cleanup_combo.setCurrentText(area_cleanup_mode)
            self.apply_zoom_checkbox.setChecked(apply_zoom)
        finally:
            self._is_syncing_workflow_controls = False

        self.blur_slider.setValue(preset.blur_strength)
        self.zoom_slider.setValue(preset.zoom_percentage)
        self.encoder_combo.setCurrentText(preset.encoder_preference)
        self.output_quality_combo.setCurrentText(preset.output_quality)
        self.output_resolution_combo.setCurrentText(preset.output_resolution)
        self.resize_mode_combo.setCurrentText(preset.resize_mode)
        self.custom_output_width_spin.setValue(preset.custom_output_width)
        self.custom_output_height_spin.setValue(preset.custom_output_height)

        if preset.logo_image_path:
            stored_logo_path = Path(preset.logo_image_path)
            if stored_logo_path.exists():
                self.logo_image_path = stored_logo_path
                self.logo_file_label.setText(str(stored_logo_path))
                warning_text = None
            else:
                self.logo_image_path = None
                self.logo_file_label.setText("Stored logo/image path is missing")
                warning_text = (
                    f"Preset '{preset.name}' loaded, but the stored logo/image path no longer exists:\n"
                    f"{stored_logo_path}"
                )
        else:
            self.logo_image_path = None
            self.logo_file_label.setText("No logo/image selected")
            warning_text = None

        self.preview_canvas.set_normalized_selection(self.current_selection)
        self.update_selection_display(self.current_selection)
        self.update_mode_controls()
        self.update_output_resolution_controls()
        self.update_workflow_hint()
        return warning_text

    def on_select_logo(self) -> None:
        """Select and store the overlay image for logo/image export mode."""
        selected_file, _ = QFileDialog.getOpenFileName(
            self,
            "Select Logo/Image",
            "",
            "Image Files (*.png *.jpg *.jpeg *.webp)",
        )
        if not selected_file:
            return

        self.logo_image_path = Path(selected_file)
        self.logo_file_label.setText(str(self.logo_image_path))
        self.status_label.setText("Logo/image selected")
        self.update_workflow_hint()

    def on_select_output(self) -> None:
        """Select and store the output folder for exports."""
        selected_directory = QFileDialog.getExistingDirectory(self, "Select Output Folder")
        if not selected_directory:
            return

        self.output_directory = Path(selected_directory)
        self.output_folder_label.setText(str(self.output_directory))
        self.status_label.setText("Output folder selected")
        self.save_app_settings()
        self.update_workflow_hint()

    def on_save_preset(self) -> None:
        """Save the current settings to the app-data preset store and optionally export JSON."""
        suggested_name = self.get_current_processing_mode() or self.area_cleanup_combo.currentText()
        preset_name, accepted = QInputDialog.getText(
            self,
            "Save Preset",
            "Preset name:",
            text=suggested_name,
        )
        if not accepted or not preset_name.strip():
            return

        preset = self.build_current_preset(preset_name.strip())
        saved_path = self.preset_store.save_preset(preset)

        if QMessageBox.question(
            self,
            "Preset Saved",
            f"Saved preset to:\n{saved_path}\n\nDo you want to export a copy to another location?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        ) == QMessageBox.Yes:
            selected_path, _ = QFileDialog.getSaveFileName(
                self,
                "Export Preset JSON",
                str(Path.home() / saved_path.name),
                "Preset Files (*.json)",
            )
            if selected_path:
                self.preset_store.save_preset_to_path(preset, selected_path)

        self.status_label.setText(f"Preset saved: {preset.name}")

    def on_load_preset(self) -> None:
        """Load a preset from app data or any external JSON file."""
        selected_path, _ = QFileDialog.getOpenFileName(
            self,
            "Load Preset",
            str(self.preset_store.presets_directory),
            "Preset Files (*.json)",
        )
        if not selected_path:
            return

        try:
            preset = self.preset_store.load_preset(selected_path)
        except Exception as exc:
            QMessageBox.warning(self, "Load Preset Error", f"Could not load preset:\n{exc}")
            self.status_label.setText("Preset load failed")
            return

        warning_text = self.apply_preset(preset)
        self.status_label.setText(f"Preset loaded: {preset.name}")

        if warning_text:
            QMessageBox.information(self, "Preset Loaded", warning_text)

    def build_app_settings(self) -> AppSettings:
        """Capture the currently persistent UI state."""
        current_mode = self.get_current_processing_mode() or self.area_cleanup_combo.currentText()
        return AppSettings(
            last_output_folder=str(self.output_directory) if self.output_directory else None,
            last_encoder_selection=self.encoder_combo.currentText(),
            last_processing_mode=current_mode,
            last_zoom_percentage=self.zoom_slider.value(),
            last_blur_strength=self.blur_slider.value(),
            last_output_quality=self.output_quality_combo.currentText(),
            last_output_resolution=self.output_resolution_combo.currentText(),
            last_resize_mode=self.resize_mode_combo.currentText(),
            last_custom_output_width=self.custom_output_width_spin.value(),
            last_custom_output_height=self.custom_output_height_spin.value(),
        )

    def load_app_settings(self) -> None:
        """Restore the last-saved persistent UI state."""
        try:
            settings = self.app_settings_store.load()
        except Exception as exc:
            self.status_label.setText(f"Settings load skipped: {exc}")
            return

        self._is_restoring_app_settings = True
        try:
            area_cleanup_mode, apply_zoom = workflow_state_from_processing_mode(settings.last_processing_mode)
            self._is_syncing_workflow_controls = True
            try:
                self.area_cleanup_combo.setCurrentText(area_cleanup_mode)
                self.apply_zoom_checkbox.setChecked(apply_zoom)
            finally:
                self._is_syncing_workflow_controls = False

            if settings.last_encoder_selection:
                self.encoder_combo.setCurrentText(settings.last_encoder_selection)
            if settings.last_output_quality:
                self.output_quality_combo.setCurrentText(settings.last_output_quality)
            if settings.last_output_resolution:
                self.output_resolution_combo.setCurrentText(settings.last_output_resolution)
            if settings.last_resize_mode:
                self.resize_mode_combo.setCurrentText(settings.last_resize_mode)
            self.zoom_slider.setValue(settings.last_zoom_percentage)
            self.blur_slider.setValue(settings.last_blur_strength)
            self.custom_output_width_spin.setValue(settings.last_custom_output_width)
            self.custom_output_height_spin.setValue(settings.last_custom_output_height)
            if settings.last_output_folder:
                self.output_directory = Path(settings.last_output_folder)
                self.output_folder_label.setText(str(self.output_directory))
        finally:
            self._is_restoring_app_settings = False

        self.update_output_resolution_controls()

    def save_app_settings(self) -> None:
        """Persist the current settings to the writable app-data location."""
        if self._is_restoring_app_settings:
            return
        self.app_settings_store.save(self.build_app_settings())

    def on_persistent_setting_changed(self, *_args) -> None:
        """Persist app settings when tracked controls change."""
        self.save_app_settings()

    def apply_tooltips(self) -> None:
        """Add lightweight guidance to the most important controls."""
        self.area_cleanup_combo.setToolTip("Choose how to handle the selected logo or watermark area.")
        self.blur_slider.setToolTip("Controls how strongly the selected rectangle is blurred.")
        self.logo_button.setToolTip("Choose a PNG, JPG, JPEG, or WEBP file to cover the selected area.")
        self.apply_zoom_checkbox.setToolTip("Enable zoom/crop mode for a separate zoom-only export.")
        self.zoom_slider.setToolTip("Scales the video up, then center-crops back to the original size.")
        self.encoder_combo.setToolTip("Auto uses NVIDIA NVENC when available and falls back to CPU when needed.")
        self.output_quality_combo.setToolTip("Choose a faster or higher-quality preset without manual bitrate tuning.")
        self.output_resolution_combo.setToolTip("Standardize exports to a vertical reel resolution like 1080x1920.")
        self.resize_mode_combo.setToolTip("Fill & Crop is recommended for vertical reels. Fit with Padding preserves the whole frame.")
        self.custom_output_width_spin.setToolTip("Custom export width. Use positive even numbers only.")
        self.custom_output_height_spin.setToolTip("Custom export height. Use positive even numbers only.")
        self.output_button.setToolTip("Select the folder where exported MP4 files will be written.")
        self.save_preset_button.setToolTip("Save the current creator workflow as a preset.")
        self.load_preset_button.setToolTip("Load a saved preset from the presets folder or any exported preset JSON.")
        self.clear_selection_button.setToolTip("Remove the current rectangle selection from the preview.")
        self.play_pause_button.setToolTip("Preview the selected video without audio.")
        self.timeline_slider.setToolTip("Scrub through the current preview video.")
        self.test_export_button.setToolTip("Export only the currently selected video using the current settings.")
        self.export_button.setToolTip("Export every queued video using the current settings.")

    def resolve_encoder_plan(self):
        """Resolve the current encoder UI choice into a usable export plan."""
        if not self.ffmpeg_processor.is_ffmpeg_available():
            QMessageBox.warning(self, "FFmpeg Not Found", FFMPEG_NOT_FOUND_MESSAGE)
            self.status_label.setText("FFmpeg not available")
            return None

        encoder_availability = self.ffmpeg_processor.detect_available_encoders()
        try:
            return self.ffmpeg_processor.resolve_encoder_plan(
                self.encoder_combo.currentText(),
                encoder_availability,
            )
        except ValueError as exc:
            QMessageBox.warning(self, "Encoder Error", str(exc))
            self.status_label.setText("Encoder unavailable")
            return None

    def validate_export_request(self, videos: List[VideoInfo]) -> Optional[str]:
        """Return a user-facing validation error for export, or None when ready."""
        mode = self.get_current_processing_mode()
        if mode is None:
            return "Choose an Area Cleanup option or enable 'Apply zoom/crop' before exporting."

        return validate_export_request(
            mode=mode,
            videos=videos,
            output_directory=self.output_directory,
            selection=self.current_selection,
            overlay_image_path=self.logo_image_path,
            output_resolution=self.output_resolution_combo.currentText(),
            custom_output_width=self.custom_output_width_spin.value(),
            custom_output_height=self.custom_output_height_spin.value(),
        )

    def build_export_settings(self, mode: str) -> ExportSettings:
        """Return an export settings snapshot for the active workflow."""
        output_standardization = build_output_standardization(
            self.output_resolution_combo.currentText(),
            self.resize_mode_combo.currentText(),
            custom_width=self.custom_output_width_spin.value(),
            custom_height=self.custom_output_height_spin.value(),
        )
        return ExportSettings(
            processing_mode=mode,
            blur_strength=self.blur_slider.value(),
            zoom_percent=self.zoom_slider.value(),
            output_quality=self.output_quality_combo.currentText(),
            output_standardization=output_standardization,
            selection=self.current_selection,
            overlay_image_path=self.logo_image_path,
        )

    def on_export_all(self) -> None:
        """Validate inputs and start a batch export."""
        videos = self.video_queue.get_all_videos()
        validation_error = self.validate_export_request(videos)
        if validation_error:
            QMessageBox.warning(self, "Export Error", validation_error)
            self.status_label.setText("Export blocked")
            return

        encoder_plan = self.resolve_encoder_plan()
        if encoder_plan is None:
            return

        self.start_export(videos, encoder_plan, export_scope_label="batch")

    def on_test_export_current_video(self) -> None:
        """Export only the currently selected video using the current settings."""
        current_video = self.video_queue.get_selected_video()
        if current_video is None:
            QMessageBox.warning(self, "Test Export Error", "Select a video in the queue before test exporting.")
            self.status_label.setText("Test export blocked")
            return

        videos = [current_video]
        validation_error = self.validate_export_request(videos)
        if validation_error:
            QMessageBox.warning(self, "Test Export Error", validation_error)
            self.status_label.setText("Test export blocked")
            return

        encoder_plan = self.resolve_encoder_plan()
        if encoder_plan is None:
            return

        self.start_export(videos, encoder_plan, export_scope_label="current video test")

    def start_export(self, videos: List[VideoInfo], encoder_plan, export_scope_label: str) -> None:
        """Create the worker thread and begin an export run."""
        if self.output_directory is None or self.export_worker is not None:
            return

        mode = self.get_current_processing_mode()
        if mode is None:
            return

        self._active_export_scope_label = export_scope_label
        export_settings = self.build_export_settings(mode)
        ffmpeg_path = self.ffmpeg_processor.resolved_ffmpeg_path or self.ffmpeg_processor.ffmpeg_path
        progress_label = processing_mode_progress_label(mode)

        self.video_queue.set_status_for_videos([video.file_path for video in videos], "Queued")
        self.export_button.setEnabled(False)
        self.test_export_button.setEnabled(False)
        self.progress_bar.setRange(0, len(videos))
        self.progress_bar.setValue(0)
        self.status_label.setText(
            f"Starting {export_scope_label} {progress_label.lower()} export with {ffmpeg_path}..."
        )

        self.export_thread = QThread(self)
        self.export_worker = ExportWorker(
            videos=videos,
            output_directory=self.output_directory,
            settings=export_settings,
            encoder_plan=encoder_plan,
            ffmpeg_path=ffmpeg_path,
        )
        self.export_worker.moveToThread(self.export_thread)
        self.export_thread.started.connect(self.export_worker.run)
        self.export_worker.progress_changed.connect(self.on_export_progress)
        self.export_worker.status_changed.connect(self.status_label.setText)
        self.export_worker.file_finished.connect(self.on_export_file_finished)
        self.export_worker.finished.connect(self.on_export_finished)
        self.export_worker.finished.connect(self.export_thread.quit)
        self.export_worker.finished.connect(self.export_worker.deleteLater)
        self.export_thread.finished.connect(self.export_thread.deleteLater)
        self.export_thread.finished.connect(self.on_export_thread_finished)
        self.export_thread.start()

        self.update_workflow_hint()
        self.update_action_states()

    def on_export_progress(self, completed: int, total: int) -> None:
        """Update the progress bar with batch-level progress."""
        self.progress_bar.setRange(0, max(total, 1))
        self.progress_bar.setValue(completed)

    def on_export_file_finished(self, result) -> None:
        """Update queue status text when a file finishes exporting."""
        if result.success:
            status = "Done"
            if result.fallback_used:
                status = "Done (CPU fallback)"
                self.status_label.setText(f"CPU fallback used for {result.input_path.name}")
        else:
            status = "Failed"

        self.video_queue.set_video_status(str(result.input_path), status)

    def on_export_finished(self, summary: BatchExportSummary) -> None:
        """Show a readable export summary when the export completes."""
        self.export_button.setEnabled(True)
        self.test_export_button.setEnabled(self.current_video_info is not None)
        message = format_export_summary(summary)

        dialog = QMessageBox(self)
        dialog.setIcon(QMessageBox.Warning if summary.failure_count else QMessageBox.Information)
        dialog.setWindowTitle(
            "Export Completed With Errors" if summary.failure_count else "Export Complete"
        )
        dialog.setText(message)
        open_folder_button = None
        if Path(summary.output_directory).exists():
            open_folder_button = dialog.addButton("Open Output Folder", QMessageBox.ActionRole)
        dialog.addButton(QMessageBox.Ok)
        dialog.exec()

        if dialog.clickedButton() == open_folder_button:
            QDesktopServices.openUrl(QUrl.fromLocalFile(summary.output_directory))

        if summary.failure_count:
            self.status_label.setText("Export finished with errors")
        else:
            self.status_label.setText(
                "Test export complete" if summary.total_videos == 1 else "Export complete"
            )

        self.update_workflow_hint()
        self.update_action_states()

    def on_export_thread_finished(self) -> None:
        """Clear worker references after the background thread stops."""
        self.export_thread = None
        self.export_worker = None
        self._active_export_scope_label = "batch"
        self.update_workflow_hint()
        self.update_action_states()

    def update_action_states(self) -> None:
        """Refresh enabled states that depend on queue, selection, and export state."""
        export_running = self.export_worker is not None
        has_selected_video = self.current_video_info is not None
        has_preview = self.preview_capture is not None and self.preview_frame_count > 0

        self.play_pause_button.setEnabled(has_preview and not export_running)
        self.timeline_slider.setEnabled(has_preview and self.preview_frame_count > 1 and not export_running)
        self.test_export_button.setEnabled(has_selected_video and not export_running)
        self.export_button.setEnabled(not export_running)

    def closeEvent(self, event: QCloseEvent) -> None:
        """Persist settings and release preview resources when the window closes."""
        self.pause_preview_playback()
        self.release_preview_capture()
        self.save_app_settings()
        super().closeEvent(event)

    @staticmethod
    def _panel_style() -> str:
        return (
            "QFrame { background-color: #252526; border: 1px solid #30363d; border-radius: 10px; }"
        )

    @staticmethod
    def _subsection_style() -> str:
        return (
            "QFrame { background-color: #232a31; border: 1px solid #31485c; "
            "border-radius: 10px; }"
        )

    @staticmethod
    def _combo_style() -> str:
        return (
            "QComboBox { background-color: #3a3a3a; color: #e0e0e0; border: 1px solid #4a4a4a; "
            "border-radius: 4px; padding: 6px 10px; min-height: 36px; } "
            "QComboBox:disabled { background-color: #2b2b2b; color: #97a0ac; border: 1px solid #3c3c3c; } "
            "QComboBox::drop-down { border: none; } "
            "QComboBox::down-arrow { image: none; border-left: 5px solid transparent; "
            "border-right: 5px solid transparent; border-top: 5px solid #e0e0e0; }"
        )

    @staticmethod
    def _slider_style() -> str:
        return (
            "QSlider::groove:horizontal { height: 6px; background: #3a3a3a; border-radius: 3px; } "
            "QSlider::handle:horizontal { background: #0078d4; width: 16px; height: 16px; "
            "border-radius: 8px; margin: -5px 0; } "
            "QSlider:disabled::handle:horizontal { background: #5d5d5d; }"
        )

    @staticmethod
    def _set_secondary_button_style(button: QPushButton) -> None:
        button.setStyleSheet(
            "QPushButton { background-color: #3a3a3a; color: #e0e0e0; border: none; "
            "border-radius: 6px; padding: 10px 12px; font-size: 13px; min-height: 36px; } "
            "QPushButton:hover { background-color: #4a4a4a; } "
            "QPushButton:pressed { background-color: #2a2a2a; } "
            "QPushButton:disabled { background-color: #303030; color: #808080; }"
        )

    def _create_section(self, title: str, description: str) -> tuple[QFrame, QVBoxLayout]:
        """Create a framed right-panel section with consistent styling."""
        frame = QFrame()
        frame.setObjectName("settingsSection")
        frame.setStyleSheet(self._subsection_style())
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        title_label = QLabel(title)
        title_label.setObjectName("sectionTitle")
        layout.addWidget(title_label)

        description_label = self._create_helper_label(description)
        description_label.setObjectName("sectionDescription")
        layout.addWidget(description_label)

        return frame, layout

    @staticmethod
    def _create_field_label(text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("fieldLabel")
        label.setWordWrap(True)
        return label

    @staticmethod
    def _create_helper_label(text: str = "") -> QLabel:
        label = QLabel(text)
        label.setObjectName("helperLabel")
        label.setWordWrap(True)
        return label

    @staticmethod
    def _configure_panel_control(widget: QWidget, minimum_width: int = 0) -> None:
        widget.setMinimumHeight(36)
        if minimum_width > 0:
            widget.setMinimumWidth(minimum_width)
