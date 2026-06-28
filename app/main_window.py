"""
Main Window for ReelBatch Editor
"""
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                               QLabel, QComboBox, QSlider, QPushButton, 
                               QProgressBar, QFileDialog, QMessageBox, QFrame)
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction
from app.preview_canvas import PreviewCanvas
from app.video_queue import VideoQueue


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
        """Connect signals to placeholder handlers."""
        # Video queue signals
        self.video_queue.connect_signals(
            self.on_add_videos,
            self.on_clear_queue
        )
        
        # Edit settings signals
        self.logo_button.clicked.connect(self.on_select_logo)
        self.output_button.clicked.connect(self.on_select_output)
        self.save_preset_button.clicked.connect(self.on_save_preset)
        self.load_preset_button.clicked.connect(self.on_load_preset)
        
        # Export signal
        self.export_button.clicked.connect(self.on_export)
    
    def on_add_videos(self):
        """Placeholder handler for add videos button."""
        QMessageBox.information(self, "Add Videos", "Video import will be implemented in Phase 3")
        self.status_label.setText("Add videos clicked")
    
    def on_clear_queue(self):
        """Placeholder handler for clear queue button."""
        QMessageBox.information(self, "Clear Queue", "Clear queue will be implemented in Phase 3")
        self.status_label.setText("Clear queue clicked")
    
    def on_select_logo(self):
        """Placeholder handler for logo selection."""
        QMessageBox.information(self, "Select Logo", "Logo selection will be implemented in Phase 3")
        self.status_label.setText("Select logo clicked")
    
    def on_select_output(self):
        """Placeholder handler for output folder selection."""
        QMessageBox.information(self, "Select Output", "Output folder selection will be implemented in Phase 3")
        self.status_label.setText("Select output folder clicked")
    
    def on_save_preset(self):
        """Placeholder handler for save preset."""
        QMessageBox.information(self, "Save Preset", "Preset saving will be implemented in Phase 3")
        self.status_label.setText("Save preset clicked")
    
    def on_load_preset(self):
        """Placeholder handler for load preset."""
        QMessageBox.information(self, "Load Preset", "Preset loading will be implemented in Phase 3")
        self.status_label.setText("Load preset clicked")
    
    def on_export(self):
        """Placeholder handler for export button."""
        QMessageBox.information(self, "Export", "Video export will be implemented in Phase 3")
        self.status_label.setText("Export clicked")
