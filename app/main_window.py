"""
Main Window for ReelBatch Editor
"""
from __future__ import annotations
from pathlib import Path
from typing import List, Optional
from PySide6.QtCore import Qt, QThread, QUrl
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                               QLabel, QComboBox, QSlider, QPushButton, 
                               QProgressBar, QFileDialog, QMessageBox, QFrame,
                               QGridLayout, QInputDialog)
from PySide6.QtGui import QCloseEvent, QDesktopServices
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
    FFmpegProcessor,
    OUTPUT_QUALITY_BALANCED,
    OUTPUT_QUALITY_OPTIONS,
)
from core.presets import ExportPreset, PresetStore
from core.processing_modes import (
    PROCESSING_MODE_BLUR,
    PROCESSING_MODE_LOGO,
    PROCESSING_MODE_ZOOM,
    PROCESSING_MODES,
    processing_mode_progress_label,
    processing_mode_status_text,
    validate_export_request,
)
from core.selection import NormalizedSelection
from core.video_probe import VideoInfo, read_video_metadata, extract_preview_frame


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
        self._is_restoring_app_settings = False
        self.setWindowTitle("ReelBatch Editor")
        self.setMinimumSize(1200, 800)
        self.setup_ui()
        self.connect_signals()
        self.load_app_settings()
        self.update_mode_controls(self.processing_mode.currentText())
    
    def setup_ui(self):
        """Set up the main window UI."""
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        # Content area with three panels
        content_layout = QHBoxLayout()
        content_layout.setSpacing(10)
        
        # Left panel - Video Queue
        self.video_queue = VideoQueue()
        self.video_queue.setMaximumWidth(250)
        content_layout.addWidget(self.video_queue)
        
        # Center panel - Preview Canvas
        center_panel = QFrame()
        center_panel.setStyleSheet("""
            QFrame {
                background-color: #252526;
                border-radius: 8px;
                padding: 10px;
            }
        """)
        center_layout = QVBoxLayout(center_panel)
        center_layout.setContentsMargins(0, 0, 0, 0)
        
        preview_title = QLabel("Preview")
        preview_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #ffffff;")
        center_layout.addWidget(preview_title)
        
        self.preview_canvas = PreviewCanvas()
        center_layout.addWidget(self.preview_canvas)
        
        content_layout.addWidget(center_panel, stretch=1)
        
        # Right panel - Edit Settings
        right_panel = QFrame()
        right_panel.setStyleSheet("""
            QFrame {
                background-color: #252526;
                border-radius: 8px;
                padding: 10px;
            }
        """)
        right_panel.setMaximumWidth(300)
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        settings_title = QLabel("Edit Settings")
        settings_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #ffffff;")
        right_layout.addWidget(settings_title)
        
        # Processing Mode
        right_layout.addWidget(QLabel("Processing Mode:"))
        self.processing_mode = QComboBox()
        self.processing_mode.addItems(list(PROCESSING_MODES))
        self.processing_mode.setStyleSheet("""
            QComboBox {
                background-color: #3a3a3a;
                color: #e0e0e0;
                border: 1px solid #4a4a4a;
                border-radius: 4px;
                padding: 6px;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #e0e0e0;
            }
        """)
        right_layout.addWidget(self.processing_mode)

        self.mode_help_label = QLabel(processing_mode_status_text(self.processing_mode.currentText()))
        self.mode_help_label.setStyleSheet("color: #9a9a9a; font-size: 12px;")
        self.mode_help_label.setWordWrap(True)
        right_layout.addWidget(self.mode_help_label)
        
        # Blur Strength
        right_layout.addWidget(QLabel("Blur Strength:"))
        self.blur_slider = QSlider(Qt.Horizontal)
        self.blur_slider.setRange(1, 20)
        self.blur_slider.setValue(10)
        self.blur_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                height: 6px;
                background: #3a3a3a;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #0078d4;
                width: 16px;
                height: 16px;
                border-radius: 8px;
                margin: -5px 0;
            }
        """)
        right_layout.addWidget(self.blur_slider)

        self.blur_value_label = QLabel("10")
        self.blur_value_label.setStyleSheet("color: #9a9a9a; font-size: 12px;")
        right_layout.addWidget(self.blur_value_label)
        
        # Logo/Image Picker
        self.logo_button = QPushButton("Select Logo/Image")
        self.logo_button.setStyleSheet("""
            QPushButton {
                background-color: #3a3a3a;
                color: #e0e0e0;
                border: none;
                border-radius: 6px;
                padding: 10px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #4a4a4a;
            }
            QPushButton:pressed {
                background-color: #2a2a2a;
            }
        """)
        right_layout.addWidget(self.logo_button)

        self.logo_file_label = QLabel("No logo/image selected")
        self.logo_file_label.setStyleSheet("color: #9a9a9a; font-size: 12px;")
        self.logo_file_label.setWordWrap(True)
        right_layout.addWidget(self.logo_file_label)
        
        # Zoom Percentage
        right_layout.addWidget(QLabel("Zoom Percentage:"))
        self.zoom_slider = QSlider(Qt.Horizontal)
        self.zoom_slider.setRange(100, 150)
        self.zoom_slider.setValue(110)
        self.zoom_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                height: 6px;
                background: #3a3a3a;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #0078d4;
                width: 16px;
                height: 16px;
                border-radius: 8px;
                margin: -5px 0;
            }
        """)
        right_layout.addWidget(self.zoom_slider)

        self.zoom_value_label = QLabel("110%")
        self.zoom_value_label.setStyleSheet("color: #9a9a9a; font-size: 12px;")
        right_layout.addWidget(self.zoom_value_label)
        
        # Encoder Selection
        right_layout.addWidget(QLabel("Encoder:"))
        self.encoder_combo = QComboBox()
        self.encoder_combo.addItems([ENCODER_OPTION_AUTO, ENCODER_OPTION_CPU, ENCODER_OPTION_NVIDIA])
        self.encoder_combo.setStyleSheet("""
            QComboBox {
                background-color: #3a3a3a;
                color: #e0e0e0;
                border: 1px solid #4a4a4a;
                border-radius: 4px;
                padding: 6px;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #e0e0e0;
            }
        """)
        right_layout.addWidget(self.encoder_combo)

        # Output Quality
        right_layout.addWidget(QLabel("Output Quality:"))
        self.output_quality_combo = QComboBox()
        self.output_quality_combo.addItems(list(OUTPUT_QUALITY_OPTIONS))
        self.output_quality_combo.setCurrentText(OUTPUT_QUALITY_BALANCED)
        self.output_quality_combo.setStyleSheet("""
            QComboBox {
                background-color: #3a3a3a;
                color: #e0e0e0;
                border: 1px solid #4a4a4a;
                border-radius: 4px;
                padding: 6px;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #e0e0e0;
            }
        """)
        right_layout.addWidget(self.output_quality_combo)
        
        # Output Folder
        self.output_button = QPushButton("Select Output Folder")
        self.output_button.setStyleSheet("""
            QPushButton {
                background-color: #3a3a3a;
                color: #e0e0e0;
                border: none;
                border-radius: 6px;
                padding: 10px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #4a4a4a;
            }
            QPushButton:pressed {
                background-color: #2a2a2a;
            }
        """)
        right_layout.addWidget(self.output_button)

        self.output_folder_label = QLabel("No output folder selected")
        self.output_folder_label.setStyleSheet("color: #9a9a9a; font-size: 12px;")
        self.output_folder_label.setWordWrap(True)
        right_layout.addWidget(self.output_folder_label)
        
        # Preset Buttons
        preset_layout = QHBoxLayout()
        
        self.save_preset_button = QPushButton("Save Preset")
        self.save_preset_button.setStyleSheet("""
            QPushButton {
                background-color: #3a3a3a;
                color: #e0e0e0;
                border: none;
                border-radius: 6px;
                padding: 10px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #4a4a4a;
            }
            QPushButton:pressed {
                background-color: #2a2a2a;
            }
        """)
        preset_layout.addWidget(self.save_preset_button)
        
        self.load_preset_button = QPushButton("Load Preset")
        self.load_preset_button.setStyleSheet("""
            QPushButton {
                background-color: #3a3a3a;
                color: #e0e0e0;
                border: none;
                border-radius: 6px;
                padding: 10px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #4a4a4a;
            }
            QPushButton:pressed {
                background-color: #2a2a2a;
            }
        """)
        preset_layout.addWidget(self.load_preset_button)
        
        right_layout.addLayout(preset_layout)

        self.selection_section = QFrame()
        self.selection_section.setStyleSheet("""
            QFrame {
                background-color: #2d2d2d;
                border: 1px solid #3a3a3a;
                border-radius: 8px;
                padding: 10px;
            }
        """)
        selection_layout = QVBoxLayout(self.selection_section)
        selection_layout.setContentsMargins(12, 12, 12, 12)
        selection_layout.setSpacing(10)

        selection_title = QLabel("Selection")
        selection_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #ffffff;")
        selection_layout.addWidget(selection_title)

        self.selection_requirement_label = QLabel("Required for blur and logo/image modes")
        self.selection_requirement_label.setStyleSheet("color: #9a9a9a; font-size: 12px;")
        self.selection_requirement_label.setWordWrap(True)
        selection_layout.addWidget(self.selection_requirement_label)

        selection_grid = QGridLayout()
        selection_grid.setHorizontalSpacing(12)
        selection_grid.setVerticalSpacing(8)

        self.selection_value_labels: dict[str, QLabel] = {}
        selection_fields = [
            ("X %", "x_percent"),
            ("Y %", "y_percent"),
            ("Width %", "width_percent"),
            ("Height %", "height_percent"),
        ]

        for row, (label_text, key) in enumerate(selection_fields):
            field_label = QLabel(label_text)
            field_label.setStyleSheet("color: #cfcfcf; font-size: 12px;")
            selection_grid.addWidget(field_label, row, 0)

            value_label = QLabel("--")
            value_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            value_label.setStyleSheet("""
                QLabel {
                    background-color: #1f1f1f;
                    color: #4ea6ff;
                    border: 1px solid #3a3a3a;
                    border-radius: 4px;
                    padding: 6px 8px;
                    font-size: 12px;
                    font-weight: bold;
                }
            """)
            selection_grid.addWidget(value_label, row, 1)
            self.selection_value_labels[key] = value_label

        selection_layout.addLayout(selection_grid)

        self.clear_selection_button = QPushButton("Clear Selection")
        self.clear_selection_button.setStyleSheet("""
            QPushButton {
                background-color: #3a3a3a;
                color: #e0e0e0;
                border: none;
                border-radius: 6px;
                padding: 10px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #4a4a4a;
            }
            QPushButton:pressed {
                background-color: #2a2a2a;
            }
        """)
        selection_layout.addWidget(self.clear_selection_button)

        right_layout.addWidget(self.selection_section)
        
        right_layout.addStretch()
        content_layout.addWidget(right_panel)
        
        main_layout.addLayout(content_layout)
        
        # Bottom status bar
        bottom_panel = QFrame()
        bottom_panel.setStyleSheet("""
            QFrame {
                background-color: #252526;
                border-radius: 8px;
                padding: 10px;
            }
        """)
        bottom_layout = QHBoxLayout(bottom_panel)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        
        # Status text
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("color: #e0e0e0; font-size: 13px;")
        bottom_layout.addWidget(self.status_label)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #3a3a3a;
                border: none;
                border-radius: 4px;
                height: 20px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #0078d4;
                border-radius: 4px;
            }
        """)
        self.progress_bar.setMaximumWidth(300)
        self.progress_bar.setValue(0)
        bottom_layout.addWidget(self.progress_bar)
        
        bottom_layout.addStretch()
        
        # Export button
        self.export_button = QPushButton("Export All")
        self.export_button.setStyleSheet("""
            QPushButton {
                background-color: #107c10;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0b8a0b;
            }
            QPushButton:pressed {
                background-color: #0a6c0a;
            }
        """)
        bottom_layout.addWidget(self.export_button)
        
        main_layout.addWidget(bottom_panel)
    
    def connect_signals(self):
        """Connect signals to handlers."""
        # Video queue signals
        self.video_queue.connect_signals(
            self.on_add_videos,
            self.on_clear_queue
        )
        
        # Connect video selection signal
        self.video_queue.video_selected.connect(self.on_video_selected)
        self.preview_canvas.selection_changed.connect(self.on_selection_changed)
        
        # Edit settings signals
        self.processing_mode.currentTextChanged.connect(self.on_processing_mode_changed)
        self.processing_mode.currentTextChanged.connect(self.on_persistent_setting_changed)
        self.logo_button.clicked.connect(self.on_select_logo)
        self.output_button.clicked.connect(self.on_select_output)
        self.save_preset_button.clicked.connect(self.on_save_preset)
        self.load_preset_button.clicked.connect(self.on_load_preset)
        self.clear_selection_button.clicked.connect(self.on_clear_selection)
        self.blur_slider.valueChanged.connect(self.on_persistent_setting_changed)
        self.zoom_slider.valueChanged.connect(self.on_persistent_setting_changed)
        self.encoder_combo.currentTextChanged.connect(self.on_persistent_setting_changed)
        self.output_quality_combo.currentTextChanged.connect(self.on_persistent_setting_changed)
        
        # Export signal
        self.export_button.clicked.connect(self.on_export)
        self.blur_slider.valueChanged.connect(self.update_slider_labels)
        self.zoom_slider.valueChanged.connect(self.update_slider_labels)
        self.apply_tooltips()
        self.update_slider_labels()
    
    def on_add_videos(self):
        """Handler for add videos button - opens file dialog and imports videos."""
        # Open file dialog for video selection
        file_dialog = QFileDialog(self)
        file_dialog.setFileMode(QFileDialog.ExistingFiles)
        file_dialog.setNameFilter("Video Files (*.mp4 *.mov *.mkv *.avi)")
        
        if file_dialog.exec():
            selected_files = file_dialog.selectedFiles()
            if selected_files:
                self.import_videos(selected_files)
    
    def on_clear_queue(self):
        """Handler for clear queue button - removes all videos and resets preview."""
        self.current_video_info = None
        self.current_selection = None
        self.video_queue.clear_queue()
        self.preview_canvas.clear_preview()
        self.update_selection_display(None)
        self.progress_bar.setValue(0)
        self.status_label.setText("Queue cleared")
    
    def on_video_selected(self, video_info: Optional[VideoInfo]):
        """Handler for video selection changes - updates preview."""
        self.current_video_info = video_info
        if video_info:
            self.status_label.setText(f"Selected video: {video_info.file_name}")
            self.update_preview(video_info)
        else:
            self.status_label.setText("Ready")
            self.preview_canvas.clear_preview()
    
    def import_videos(self, file_paths: List[str]):
        """
        Import video files from the given paths.
        
        Args:
            file_paths: List of video file paths
        """
        video_infos = []
        failed_files = []
        
        for file_path in file_paths:
            # Read video metadata
            video_info = read_video_metadata(file_path)
            if video_info:
                video_infos.append(video_info)
            else:
                failed_files.append(file_path)
        
        # Add videos to queue
        added_count, skipped_count = self.video_queue.add_videos(video_infos)
        
        # Show status message
        if added_count > 0:
            self.status_label.setText(f"Imported {added_count} videos")
            
            # Automatically preview the first imported video
            if video_infos:
                self.update_preview(video_infos[0])
        
        # Show error message for failed files
        if failed_files:
            self.status_label.setText(f"Failed to read {len(failed_files)} files")
            error_msg = f"Failed to read {len(failed_files)} files:\n\n"
            error_msg += "\n".join([f"• {path}" for path in failed_files[:5]])
            if len(failed_files) > 5:
                error_msg += f"\n... and {len(failed_files) - 5} more"
            QMessageBox.warning(self, "Import Errors", error_msg)
        
        if skipped_count > 0:
            self.status_label.setText(f"Imported {added_count} videos, skipped {skipped_count} duplicates")
    
    def update_preview(self, video_info: VideoInfo):
        """
        Update the preview canvas with a frame from the selected video.
        
        Args:
            video_info: VideoInfo object for the selected video
        """
        try:
            self.current_video_info = video_info

            # Extract preview frame (prefer frame at 1 second)
            preview_image = extract_preview_frame(video_info.file_path, target_time_seconds=1.0)
            
            if preview_image:
                self.preview_canvas.set_preview(
                    preview_image,
                    video_width=video_info.width,
                    video_height=video_info.height,
                )
                self.preview_canvas.set_normalized_selection(self.current_selection)
            else:
                # If extraction fails, show friendly message
                self.preview_canvas.clear_preview()
                self.status_label.setText(f"Could not extract preview: {video_info.file_name}")
                
        except Exception as e:
            print(f"Error updating preview: {e}")
            self.preview_canvas.clear_preview()
            self.status_label.setText(f"Preview error: {video_info.file_name}")

    def on_selection_changed(self, selection: Optional[dict]):
        """Update the settings panel when the canvas selection changes."""
        self.current_selection = NormalizedSelection.from_mapping(selection)
        self.update_selection_display(self.current_selection)

        if self.current_selection is None:
            self.status_label.setText("Selection cleared")
        else:
            self.status_label.setText("Selection updated")

    def on_clear_selection(self):
        """Clear the current rectangle selection."""
        self.preview_canvas.clear_selection()

    def update_selection_display(self, selection: Optional[NormalizedSelection]):
        """Refresh the selection values shown in the settings panel."""
        if selection is None:
            for value_label in self.selection_value_labels.values():
                value_label.setText("--")
            return

        normalized = selection.to_dict()
        for key, value_label in self.selection_value_labels.items():
            value_label.setText(f"{normalized[key]:.2f}")

    def build_current_preset(self, preset_name: str) -> ExportPreset:
        """Build a preset object from the current workflow state."""
        return ExportPreset(
            name=preset_name,
            processing_mode=self.processing_mode.currentText(),
            blur_strength=self.blur_slider.value(),
            zoom_percentage=self.zoom_slider.value(),
            encoder_preference=self.encoder_combo.currentText(),
            output_quality=self.output_quality_combo.currentText(),
            selection=self.current_selection,
            logo_image_path=str(self.logo_image_path) if self.logo_image_path else None,
        )

    def apply_preset(self, preset: ExportPreset) -> Optional[str]:
        """Apply a loaded preset and return any friendly warning text."""
        self.current_selection = preset.selection
        self.processing_mode.setCurrentText(preset.processing_mode)
        self.blur_slider.setValue(preset.blur_strength)
        self.zoom_slider.setValue(preset.zoom_percentage)
        self.encoder_combo.setCurrentText(preset.encoder_preference)
        self.output_quality_combo.setCurrentText(preset.output_quality)

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
        self.update_mode_controls(self.processing_mode.currentText())
        return warning_text
    
    def on_select_logo(self):
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
    
    def on_select_output(self):
        """Select and store the output folder for batch exports."""
        selected_directory = QFileDialog.getExistingDirectory(self, "Select Output Folder")
        if not selected_directory:
            return

        self.output_directory = Path(selected_directory)
        self.output_folder_label.setText(str(self.output_directory))
        self.status_label.setText("Output folder selected")
        self.save_app_settings()
    
    def on_save_preset(self):
        """Save the current settings to the app-data preset store and optionally export JSON."""
        preset_name, accepted = QInputDialog.getText(
            self,
            "Save Preset",
            "Preset name:",
            text=self.processing_mode.currentText(),
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
    
    def on_load_preset(self):
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

    def on_processing_mode_changed(self, mode: str) -> None:
        """Update UI affordances and status text when the mode changes."""
        self.update_mode_controls(mode)
        self.status_label.setText(processing_mode_status_text(mode))

    def update_slider_labels(self, *_args) -> None:
        """Keep the slider value labels in sync with the current controls."""
        self.blur_value_label.setText(f"{self.blur_slider.value()}")
        self.zoom_value_label.setText(f"{self.zoom_slider.value()}%")

    def build_app_settings(self) -> AppSettings:
        """Capture the currently persistent UI state."""
        return AppSettings(
            last_output_folder=str(self.output_directory) if self.output_directory else None,
            last_encoder_selection=self.encoder_combo.currentText(),
            last_processing_mode=self.processing_mode.currentText(),
            last_zoom_percentage=self.zoom_slider.value(),
            last_blur_strength=self.blur_slider.value(),
            last_output_quality=self.output_quality_combo.currentText(),
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
            if settings.last_processing_mode:
                self.processing_mode.setCurrentText(settings.last_processing_mode)
            if settings.last_encoder_selection:
                self.encoder_combo.setCurrentText(settings.last_encoder_selection)
            if settings.last_output_quality:
                self.output_quality_combo.setCurrentText(settings.last_output_quality)
            self.zoom_slider.setValue(settings.last_zoom_percentage)
            self.blur_slider.setValue(settings.last_blur_strength)
            if settings.last_output_folder:
                self.output_directory = Path(settings.last_output_folder)
                self.output_folder_label.setText(str(self.output_directory))
        finally:
            self._is_restoring_app_settings = False

    def save_app_settings(self) -> None:
        """Persist the current settings to the writable app-data location."""
        if self._is_restoring_app_settings:
            return

        self.app_settings_store.save(self.build_app_settings())

    def on_persistent_setting_changed(self, *_args) -> None:
        """Persist app settings when tracked controls change."""
        self.save_app_settings()

    def update_mode_controls(self, mode: str) -> None:
        """Enable only the controls relevant to the currently selected mode."""
        is_blur_mode = mode == PROCESSING_MODE_BLUR
        is_logo_mode = mode == PROCESSING_MODE_LOGO
        is_zoom_mode = mode == PROCESSING_MODE_ZOOM

        self.blur_slider.setEnabled(is_blur_mode)
        self.blur_value_label.setEnabled(is_blur_mode)
        self.logo_button.setEnabled(is_logo_mode)
        self.logo_file_label.setEnabled(is_logo_mode)
        self.zoom_slider.setEnabled(is_zoom_mode)
        self.zoom_value_label.setEnabled(is_zoom_mode)
        self.mode_help_label.setText(processing_mode_status_text(mode))

        if is_zoom_mode:
            self.selection_requirement_label.setText("Selection is not used in zoom/crop mode")
            self.selection_section.setStyleSheet("""
                QFrame {
                    background-color: #252526;
                    border: 1px solid #333333;
                    border-radius: 8px;
                    padding: 10px;
                }
            """)
        else:
            self.selection_requirement_label.setText("Required for the active mode")
            self.selection_section.setStyleSheet("""
                QFrame {
                    background-color: #2d2d2d;
                    border: 1px solid #3a3a3a;
                    border-radius: 8px;
                    padding: 10px;
                }
            """)

    def apply_tooltips(self) -> None:
        """Add lightweight guidance to the most important controls."""
        self.processing_mode.setToolTip("Choose the batch processing mode to apply to every queued video.")
        self.blur_slider.setToolTip("Controls how strongly the selected rectangle is blurred in blur mode.")
        self.logo_button.setToolTip("Choose a PNG, JPG, JPEG, or WEBP file to overlay in logo/image mode.")
        self.zoom_slider.setToolTip("Scales the video up, then center-crops back to the original size in zoom mode.")
        self.encoder_combo.setToolTip("Select Auto to prefer NVIDIA NVENC and fall back to CPU when needed.")
        self.output_quality_combo.setToolTip("Choose a faster or higher-quality encoder preset without manual bitrate tuning.")
        self.output_button.setToolTip("Select the folder where exported MP4 files will be written.")
        self.save_preset_button.setToolTip("Save the current selection, mode, sliders, quality, and encoder settings as a preset.")
        self.load_preset_button.setToolTip("Load a preset from the app-data presets folder or any exported preset JSON file.")
        self.clear_selection_button.setToolTip("Remove the current rectangle selection from the preview.")
        self.export_button.setToolTip("Start batch export for every queued video using the current settings.")
    
    def on_export(self):
        """Validate inputs and start a background export."""
        videos = self.video_queue.get_all_videos()
        validation_error = self.validate_export_request(videos)
        if validation_error:
            QMessageBox.warning(self, "Export Error", validation_error)
            self.status_label.setText("Export blocked")
            return

        if not self.ffmpeg_processor.is_ffmpeg_available():
            message = (
                "FFmpeg was not found on PATH. Install FFmpeg or add it to PATH, "
                "then try exporting again."
            )
            QMessageBox.warning(self, "FFmpeg Not Found", message)
            self.status_label.setText("FFmpeg not available")
            return

        encoder_availability = self.ffmpeg_processor.detect_available_encoders()
        try:
            encoder_plan = self.ffmpeg_processor.resolve_encoder_plan(
                self.encoder_combo.currentText(),
                encoder_availability,
            )
        except ValueError as exc:
            QMessageBox.warning(self, "Encoder Error", str(exc))
            self.status_label.setText("Encoder unavailable")
            return

        self.start_export(videos, encoder_plan)

    def validate_export_request(self, videos: List[VideoInfo]) -> Optional[str]:
        """Return a user-facing validation error for export, or None when ready."""
        return validate_export_request(
            mode=self.processing_mode.currentText(),
            videos=videos,
            output_directory=self.output_directory,
            selection=self.current_selection,
            overlay_image_path=self.logo_image_path,
        )

    def start_export(self, videos: List[VideoInfo], encoder_plan) -> None:
        """Create the worker thread and begin batch export."""
        if self.output_directory is None:
            return

        mode = self.processing_mode.currentText()
        export_settings = ExportSettings(
            processing_mode=mode,
            blur_strength=self.blur_slider.value(),
            zoom_percent=self.zoom_slider.value(),
            output_quality=self.output_quality_combo.currentText(),
            selection=self.current_selection,
            overlay_image_path=self.logo_image_path,
        )

        self.export_button.setEnabled(False)
        self.progress_bar.setRange(0, len(videos))
        self.progress_bar.setValue(0)
        progress_label = processing_mode_progress_label(mode)
        self.status_label.setText(f"Starting {progress_label.lower()} export...")

        self.export_thread = QThread(self)
        self.export_worker = ExportWorker(
            videos=videos,
            output_directory=self.output_directory,
            settings=export_settings,
            encoder_plan=encoder_plan,
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

    def on_export_progress(self, completed: int, total: int) -> None:
        """Update the progress bar with batch-level progress."""
        self.progress_bar.setRange(0, max(total, 1))
        self.progress_bar.setValue(completed)

    def on_export_file_finished(self, result) -> None:
        """Update lightweight status text when a file finishes exporting."""
        if result.success and result.fallback_used:
            self.status_label.setText(f"CPU fallback used for {result.input_path.name}")

    def on_export_finished(self, summary: BatchExportSummary) -> None:
        """Show a readable export summary when the batch completes."""
        self.export_button.setEnabled(True)
        message = format_export_summary(summary)

        dialog = QMessageBox(self)
        dialog.setIcon(
            QMessageBox.Warning if summary.failure_count else QMessageBox.Information
        )
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
            self.status_label.setText("Export complete")

    def on_export_thread_finished(self) -> None:
        """Clear worker references after the background thread stops."""
        self.export_thread = None
        self.export_worker = None

    def closeEvent(self, event: QCloseEvent) -> None:
        """Persist settings when the window closes."""
        self.save_app_settings()
        super().closeEvent(event)
