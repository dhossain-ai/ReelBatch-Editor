"""
Video Probe Module
Handles video metadata reading and preview frame extraction using OpenCV.
"""
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import cv2
import numpy as np
from PySide6.QtGui import QImage, QPixmap


@dataclass
class VideoInfo:
    """Data class for video file metadata."""
    file_path: str
    file_name: str
    width: int
    height: int
    fps: float
    frame_count: int
    duration_seconds: float
    
    @property
    def resolution(self) -> str:
        """Return resolution as string 'WIDTHxHEIGHT'."""
        return f"{self.width}x{self.height}"
    
    @property
    def duration_display(self) -> str:
        """Return duration as formatted string."""
        if self.duration_seconds < 60:
            return f"{self.duration_seconds:.1f}s"
        else:
            minutes = int(self.duration_seconds // 60)
            seconds = self.duration_seconds % 60
            return f"{minutes}m {seconds:.0f}s"


def read_video_metadata(file_path: str) -> Optional[VideoInfo]:
    """
    Read video metadata using OpenCV.
    
    Args:
        file_path: Path to the video file
        
    Returns:
        VideoInfo object if successful, None if file cannot be read
    """
    try:
        path = Path(file_path)
        if not path.exists():
            return None
        
        # Open video file
        cap = cv2.VideoCapture(file_path)
        if not cap.isOpened():
            return None
        
        # Get video properties
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        # Calculate duration
        if fps > 0:
            duration_seconds = frame_count / fps
        else:
            duration_seconds = 0.0
        
        cap.release()
        
        return VideoInfo(
            file_path=file_path,
            file_name=path.name,
            width=width,
            height=height,
            fps=fps,
            frame_count=frame_count,
            duration_seconds=duration_seconds
        )
        
    except Exception as e:
        print(f"Error reading video metadata for {file_path}: {e}")
        return None


def extract_preview_frame(file_path: str, target_time_seconds: float = 1.0) -> Optional[QImage]:
    """
    Extract a preview frame from video at specified time.
    
    Args:
        file_path: Path to the video file
        target_time_seconds: Target time in seconds (default: 1.0)
        
    Returns:
        QImage in RGB format if successful, None if extraction fails
    """
    try:
        cap = cv2.VideoCapture(file_path)
        if not cap.isOpened():
            return None
        
        # Get video properties
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        # Calculate target frame number
        if fps > 0:
            target_frame = int(target_time_seconds * fps)
        else:
            target_frame = 0
        
        # Ensure target frame is within video bounds
        if target_frame >= frame_count:
            target_frame = 0
        
        # Seek to target frame
        cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
        
        # Read frame
        ret, frame = cap.read()
        if not ret or frame is None:
            # If seeking failed, try reading first frame
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ret, frame = cap.read()
            if not ret or frame is None:
                cap.release()
                return None
        
        cap.release()
        
        # Convert BGR to RGB (OpenCV uses BGR by default)
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Convert to QImage
        height, width, channel = frame_rgb.shape
        bytes_per_line = 3 * width
        qimage = QImage(frame_rgb.data, width, height, bytes_per_line, QImage.Format_RGB888)
        
        # Make a copy to ensure the data persists
        return qimage.copy()
        
    except Exception as e:
        print(f"Error extracting preview frame from {file_path}: {e}")
        return None


def extract_first_frame(file_path: str) -> Optional[QImage]:
    """
    Extract the first frame from video (fallback method).
    
    Args:
        file_path: Path to the video file
        
    Returns:
        QImage in RGB format if successful, None if extraction fails
    """
    return extract_preview_frame(file_path, target_time_seconds=0.0)
