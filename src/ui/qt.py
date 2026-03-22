"""Qt import shim to support PySide6 or PyQt6."""

from __future__ import annotations

try:  # Prefer PySide6
    from PySide6.QtCore import QObject, Signal, Slot, Qt, QThread, QTimer
    from PySide6.QtGui import QAction, QColor, QFont, QImage, QPainter, QPen, QPixmap
    from PySide6.QtWidgets import (
        QApplication,
        QComboBox,
        QFileDialog,
        QFrame,
        QHBoxLayout,
        QLabel,
        QMainWindow,
        QMessageBox,
        QPushButton,
        QSizePolicy,
        QSplitter,
        QStatusBar,
        QToolBar,
        QVBoxLayout,
        QWidget,
        QTextEdit,
        QTabWidget,
    )
    USING_PYSIDE6 = True
except ImportError:  # Fallback to PyQt6
    from PyQt6.QtCore import QObject, pyqtSignal as Signal, pyqtSlot as Slot, Qt, QThread, QTimer
    from PyQt6.QtGui import QAction, QColor, QFont, QImage, QPainter, QPen, QPixmap
    from PyQt6.QtWidgets import (
        QApplication,
        QComboBox,
        QFileDialog,
        QFrame,
        QHBoxLayout,
        QLabel,
        QMainWindow,
        QMessageBox,
        QPushButton,
        QSizePolicy,
        QSplitter,
        QStatusBar,
        QToolBar,
        QVBoxLayout,
        QWidget,
        QTextEdit,
        QTabWidget,
    )
    USING_PYSIDE6 = False

__all__ = [
    "QAction",
    "QApplication",
    "QColor",
    "QComboBox",
    "QFileDialog",
    "QFrame",
    "QHBoxLayout",
    "QImage",
    "QLabel",
    "QMainWindow",
    "QMessageBox",
    "QObject",
    "QPainter",
    "QPen",
    "QPixmap",
    "QPushButton",
    "QSizePolicy",
    "QSplitter",
    "QStatusBar",
    "QTabWidget",
    "QTextEdit",
    "QThread",
    "QTimer",
    "QToolBar",
    "QVBoxLayout",
    "QWidget",
    "QFont",
    "Signal",
    "Slot",
    "Qt",
    "USING_PYSIDE6",
]
