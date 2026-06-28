"""
Video Queue Widget
"""
from __future__ import annotations
from typing import Optional, List, Tuple
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QListWidget, QListWidgetItem
from PySide6.QtCore import Qt, Signal
from core.video_probe import VideoInfo


class VideoQueue(QWidget):
    """Widget for managing the video import queue."""
    
    # Signal emitted when a video is selected
    video_selected = Signal(object)  # VideoInfo or None
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.videos = []  # List of VideoInfo objects
        self.setup_ui()
        self.setup_connections()
    
    def setup_ui(self):
        """Set up the video queue UI."""
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("Video Queue")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #ffffff;")
        layout.addWidget(title)
        
        # Video list
        self.video_list = QListWidget()
        self.video_list.setStyleSheet("""
            QListWidget {
                background-color: #2d2d2d;
                border: 1px solid #3a3a3a;
                border-radius: 8px;
                padding: 8px;
            }
            QListWidget::item {
                color: #e0e0e0;
                padding: 8px;
                border-radius: 4px;
            }
            QListWidget::item:hover {
                background-color: #3a3a3a;
            }
            QListWidget::item:selected {
                background-color: #0078d4;
            }
        """)
        layout.addWidget(self.video_list)
        
        # Buttons
        button_layout = QVBoxLayout()
        
        self.add_videos_button = QPushButton("Add Videos")
        self.add_videos_button.setStyleSheet("""
            QPushButton {
                background-color: #0078d4;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #1084d8;
            }
            QPushButton:pressed {
                background-color: #006cbd;
            }
        """)
        button_layout.addWidget(self.add_videos_button)
        
        self.clear_queue_button = QPushButton("Clear Queue")
        self.clear_queue_button.setStyleSheet("""
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
        button_layout.addWidget(self.clear_queue_button)
        
        layout.addLayout(button_layout)
    
    def setup_connections(self):
        """Set up internal signal connections."""
        self.video_list.itemSelectionChanged.connect(self.on_selection_changed)
    
    def connect_signals(self, add_handler, clear_handler):
        """Connect button signals to handlers."""
        self.add_videos_button.clicked.connect(add_handler)
        self.clear_queue_button.clicked.connect(clear_handler)
    
    def add_videos(self, video_infos: List[VideoInfo]) -> Tuple[int, int]:
        """
        Add multiple videos to the queue.
        
        Args:
            video_infos: List of VideoInfo objects
            
        Returns:
            Tuple of (added_count, skipped_count)
        """
        added_count = 0
        skipped_count = 0
        
        for video_info in video_infos:
            # Check for duplicates
            if any(v.file_path == video_info.file_path for v in self.videos):
                skipped_count += 1
                continue
            
            # Add to list
            self.videos.append(video_info)
            
            # Create list item with metadata
            item_text = f"{video_info.file_name} — {video_info.resolution} — {video_info.duration_display}"
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, video_info)  # Store VideoInfo in item
            self.video_list.addItem(item)
            added_count += 1
        
        return added_count, skipped_count
    
    def clear_queue(self):
        """Clear all videos from the queue."""
        self.videos.clear()
        self.video_list.clear()
        self.video_selected.emit(None)
    
    def on_selection_changed(self):
        """Handle video selection changes."""
        selected_items = self.video_list.selectedItems()
        if selected_items:
            video_info = selected_items[0].data(Qt.UserRole)
            self.video_selected.emit(video_info)
        else:
            self.video_selected.emit(None)
    
    def get_selected_video(self) -> Optional[VideoInfo]:
        """Get the currently selected video."""
        selected_items = self.video_list.selectedItems()
        if selected_items:
            return selected_items[0].data(Qt.UserRole)
        return None
    
    def get_all_videos(self) -> List[VideoInfo]:
        """Get all videos in the queue."""
        return self.videos.copy()
    
    def get_video_count(self) -> int:
        """Get the number of videos in the queue."""
        return len(self.videos)
