"""
ReelBatch Editor - Main Entry Point
"""
import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QFile, QTextStream
from app.main_window import MainWindow


def load_stylesheet():
    """Load the QSS stylesheet for the application."""
    style_file = QFile("app/styles.qss")
    if style_file.exists():
        style_file.open(QFile.ReadOnly | QFile.Text)
        style_stream = QTextStream(style_file)
        stylesheet = style_stream.readAll()
        style_file.close()
        return stylesheet
    return ""


def main():
    """Main application entry point."""
    app = QApplication(sys.argv)
    app.setApplicationName("ReelBatch Editor")
    
    # Load stylesheet
    stylesheet = load_stylesheet()
    if stylesheet:
        app.setStyleSheet(stylesheet)
    
    # Create and show main window
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
