"""
Main Window for ReelBatch Editor
"""
from __future__ import annotations
from typing import List, Optional
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                               QLabel, QComboBox, QSlider, QPushButton, 
                               QProgressBar, QFileDialog, QMessageBox, QFrame)
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction
from app.preview_canvas import PreviewCanvas
from app.video_queue import VideoQueue
from core.video_probe import VideoInfo, read_video_metadata, extract_preview_frame


class MainWindow(QMainWindow):
    """Main application window."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ReelBatch Editor")
        self.setMinimumSize(1200, 800)
        self.setup_ui()
        self.connect_signals()
    
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
        self.processing_mode.addItems(["Blur selected area", "Cover with logo/image", "Zoom/crop"])
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
        
        # Encoder Selection
        right_layout.addWidget(QLabel("Encoder:"))
        self.encoder_combo = QComboBox()
        self.encoder_combo.addItems(["Auto - Prefer NVIDIA NVENC", "CPU - libx264", "NVIDIA - h264_nvenc"])
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
        
        # Edit settings signals
        self.logo_button.clicked.connect(self.on_select_logo)
        self.output_button.clicked.connect(self.on_select_output)
        self.save_preset_button.clicked.connect(self.on_save_preset)
        self.load_preset_button.clicked.connect(self.on_load_preset)
        
        # Export signal
        self.export_button.clicked.connect(self.on_export)
    
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
        self.video_queue.clear_queue()
        self.preview_canvas.clear_preview()
        self.status_label.setText("Queue cleared")
    
    def on_video_selected(self, video_info: Optional[VideoInfo]):
        """Handler for video selection changes - updates preview."""
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
            # Extract preview frame (prefer frame at 1 second)
            preview_image = extract_preview_frame(video_info.file_path, target_time_seconds=1.0)
            
            if preview_image:
                self.preview_canvas.set_preview_image(preview_image)
            else:
                # If extraction fails, show friendly message
                self.preview_canvas.clear_preview()
                self.status_label.setText(f"Could not extract preview: {video_info.file_name}")
                
        except Exception as e:
            print(f"Error updating preview: {e}")
            self.preview_canvas.clear_preview()
            self.status_label.setText(f"Preview error: {video_info.file_name}")
    
    def on_select_logo(self):
        """Placeholder handler for logo selection."""
        QMessageBox.information(self, "Select Logo", "Logo selection will be implemented in Phase 4")
        self.status_label.setText("Select logo clicked")
    
    def on_select_output(self):
        """Placeholder handler for output folder selection."""
        QMessageBox.information(self, "Select Output", "Output folder selection will be implemented in Phase 4")
        self.status_label.setText("Select output folder clicked")
    
    def on_save_preset(self):
        """Placeholder handler for save preset."""
        QMessageBox.information(self, "Save Preset", "Preset saving will be implemented in Phase 4")
        self.status_label.setText("Save preset clicked")
    
    def on_load_preset(self):
        """Placeholder handler for load preset."""
        QMessageBox.information(self, "Load Preset", "Preset loading will be implemented in Phase 4")
        self.status_label.setText("Load preset clicked")
    
    def on_export(self):
        """Placeholder handler for export button."""
        QMessageBox.information(self, "Export", "Video export will be implemented in Phase 5")
        self.status_label.setText("Export clicked")
