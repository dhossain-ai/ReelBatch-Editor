"""
Preview Canvas Widget
"""
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QColor, QPen


class PreviewCanvas(QWidget):
    """Widget for displaying video preview and future rectangle selection."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(400, 600)
        self.setStyleSheet("background-color: #1e1e1e; border: 2px dashed #3a3a3a;")
        
        self.layout = QVBoxLayout(self)
        self.layout.setAlignment(Qt.AlignCenter)
        
        self.placeholder_label = QLabel("Preview will appear here")
        self.placeholder_label.setStyleSheet("color: #666; font-size: 14px;")
        self.placeholder_label.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.placeholder_label)
    
    def paintEvent(self, event):
        """Override paint event for future rectangle drawing."""
        super().paintEvent(event)
        # Rectangle selection will be implemented here in future phases
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
