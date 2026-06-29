"""
Video Queue Widget
"""
from __future__ import annotations

from typing import List, Optional, Tuple

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QLabel, QListWidget, QListWidgetItem, QPushButton, QVBoxLayout, QWidget

from core.video_probe import VideoInfo


def format_queue_item_label(video_info: VideoInfo, status: Optional[str] = None) -> str:
    """Return a compact multi-line queue label with metadata and optional status."""
    metadata_parts = [video_info.resolution, video_info.duration_display]
    if status:
        metadata_parts.append(status)
    metadata_line = " | ".join(metadata_parts)
    return f"{video_info.file_name}\n{metadata_line}"


class VideoQueue(QWidget):
    """Widget for managing the video import queue."""
    
    # Signal emitted when a video is selected
    video_selected = Signal(object)  # VideoInfo or None
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.videos = []  # List of VideoInfo objects
        self._status_by_path: dict[str, str] = {}
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
            item_text = format_queue_item_label(
                video_info,
                self._status_by_path.get(video_info.file_path),
            )
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, video_info)  # Store VideoInfo in item
            item.setToolTip(video_info.file_path)
            self.video_list.addItem(item)
            added_count += 1
        
        return added_count, skipped_count
    
    def clear_queue(self):
        """Clear all videos from the queue."""
        self.videos.clear()
        self._status_by_path.clear()
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

    def set_video_status(self, file_path: str, status: Optional[str]) -> None:
        """Update the visible status for one queued video."""
        if status:
            self._status_by_path[file_path] = status
        else:
            self._status_by_path.pop(file_path, None)

        for index in range(self.video_list.count()):
            item = self.video_list.item(index)
            video_info = item.data(Qt.UserRole)
            if video_info and video_info.file_path == file_path:
                item.setText(format_queue_item_label(video_info, status))
                break

    def set_status_for_videos(self, file_paths: List[str], status: Optional[str]) -> None:
        """Update the visible status for multiple queued videos."""
        for file_path in file_paths:
            self.set_video_status(file_path, status)
