"""
Preview Canvas Widget
"""
from __future__ import annotations
from typing import Optional
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QColor, QPen, QImage, QPixmap


class PreviewCanvas(QWidget):
    """Widget for displaying video preview and future rectangle selection."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(400, 600)
        self.setStyleSheet("background-color: #1e1e1e; border: 2px dashed #3a3a3a;")
        
        self.layout = QVBoxLayout(self)
        self.layout.setAlignment(Qt.AlignCenter)
        
        self.preview_label = QLabel()
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setStyleSheet("background-color: #1e1e1e;")
        self.preview_label.setScaledContents(False)  # We'll handle scaling manually
        self.layout.addWidget(self.preview_label)
        
        self.placeholder_label = QLabel("Preview will appear here")
        self.placeholder_label.setStyleSheet("color: #666; font-size: 14px;")
        self.placeholder_label.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.placeholder_label)
        
        self.current_pixmap: Optional[QPixmap] = None
        
        # Initially hide preview label
        self.preview_label.hide()
    
    def set_preview_image(self, image: QImage):
        """
        Display a preview image on the canvas.
        
        Args:
            image: QImage to display
        """
        if image is None:
            self.clear_preview()
            return
        
        # Convert QImage to QPixmap
        pixmap = QPixmap.fromImage(image)
        self.current_pixmap = pixmap
        
        # Scale pixmap to fit canvas while preserving aspect ratio
        scaled_pixmap = self.scale_pixmap(pixmap)
        
        # Display the scaled pixmap
        self.preview_label.setPixmap(scaled_pixmap)
        self.placeholder_label.hide()
        self.preview_label.show()
    
    def clear_preview(self):
        """Clear the preview and show placeholder text."""
        self.current_pixmap = None
        self.preview_label.clear()
        self.preview_label.hide()
        self.placeholder_label.show()
        self.preview_label.setPixmap(QPixmap())  # Clear any existing pixmap
    
    def scale_pixmap(self, pixmap: QPixmap) -> QPixmap:
        """
        Scale pixmap to fit canvas while preserving aspect ratio.
        
        Args:
            pixmap: Original QPixmap
            
        Returns:
            Scaled QPixmap
        """
        if pixmap.isNull():
            return pixmap
        
        # Get canvas size (subtract some padding)
        canvas_width = self.width() - 20
        canvas_height = self.height() - 20
        
        # Get original pixmap size
        pixmap_width = pixmap.width()
        pixmap_height = pixmap.height()
        
        # Calculate scaling factors
        width_ratio = canvas_width / pixmap_width
        height_ratio = canvas_height / pixmap_height
        
        # Use the smaller ratio to fit within canvas
        scale_ratio = min(width_ratio, height_ratio)
        
        # Only scale down, not up
        if scale_ratio > 1.0:
            scale_ratio = 1.0
        
        # Calculate new dimensions
        new_width = int(pixmap_width * scale_ratio)
        new_height = int(pixmap_height * scale_ratio)
        
        # Scale the pixmap
        return pixmap.scaled(
            new_width, 
            new_height, 
            Qt.KeepAspectRatio, 
            Qt.SmoothTransformation
        )
    
    def resizeEvent(self, event):
        """Handle resize events to rescale the preview image."""
        super().resizeEvent(event)
        
        # Rescale current pixmap if it exists
        if self.current_pixmap and not self.current_pixmap.isNull():
            scaled_pixmap = self.scale_pixmap(self.current_pixmap)
            self.preview_label.setPixmap(scaled_pixmap)
    
    def paintEvent(self, event):
        """Override paint event for future rectangle drawing."""
        super().paintEvent(event)
        # Rectangle selection will be implemented here in future phases
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
