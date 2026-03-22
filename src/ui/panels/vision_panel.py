"""Vision panel: camera feeds, warped board, and status."""

from __future__ import annotations

from src.ui.qt import QLabel, QSplitter, QTabWidget, QVBoxLayout, QWidget, QFont, Qt
from src.ui.widgets.clickable_label import ClickableLabel


class VisionPanel(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("VisionPanel")
        self._raw_pixmap = None
        self._warped_pixmap = None
        self._inference_pixmap = None
        layout = QVBoxLayout(self)

        self.status_label = QLabel("Camera: disconnected | Corners: 0 | Grid: unlocked")
        self.status_label.setFont(QFont("Helvetica", 10))
        layout.addWidget(self.status_label)

        self.tabs = QTabWidget()
        self.raw_label = ClickableLabel("Camera feed")
        self.raw_label.setMinimumSize(320, 240)
        self.raw_label.setStyleSheet("background: #111; color: #ddd;")
        self.raw_label.setScaledContents(False)
        self.raw_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.warped_label = QLabel("Warped board")
        self.warped_label.setMinimumSize(320, 240)
        self.warped_label.setStyleSheet("background: #111; color: #ddd;")
        self.warped_label.setScaledContents(False)
        self.warped_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.tabs.addTab(self.raw_label, "Raw")
        self.tabs.addTab(self.warped_label, "Warped")

        self.inference_label = QLabel("Inference overlay")
        self.inference_label.setMinimumSize(320, 240)
        self.inference_label.setStyleSheet("background: #111; color: #ddd;")
        self.inference_label.setScaledContents(False)
        self.inference_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.image_splitter = QSplitter(Qt.Orientation.Vertical)
        self.image_splitter.addWidget(self.tabs)
        self.image_splitter.addWidget(self.inference_label)
        self.image_splitter.setChildrenCollapsible(False)
        self.image_splitter.setSizes([400, 400])
        self.image_splitter.setStretchFactor(0, 1)
        self.image_splitter.setStretchFactor(1, 1)
        layout.addWidget(self.image_splitter, 1)

    def update_status(self, camera_connected: bool, corners: int, grid_locked: bool, next_corner: str = "-") -> None:
        camera = "connected" if camera_connected else "disconnected"
        grid = "locked" if grid_locked else "unlocked"
        self.status_label.setText(
            f"Camera: {camera} | Corners: {corners} | Grid: {grid} | Next: {next_corner}"
        )

    def set_raw_image(self, pixmap) -> None:
        self._raw_pixmap = pixmap
        self._apply_scaled_pixmap(self.raw_label, self._raw_pixmap)

    def set_warped_image(self, pixmap) -> None:
        self._warped_pixmap = pixmap
        self._apply_scaled_pixmap(self.warped_label, self._warped_pixmap)

    def set_inference_image(self, pixmap) -> None:
        self._inference_pixmap = pixmap
        self._apply_scaled_pixmap(self.inference_label, self._inference_pixmap)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._apply_scaled_pixmap(self.raw_label, self._raw_pixmap)
        self._apply_scaled_pixmap(self.warped_label, self._warped_pixmap)
        self._apply_scaled_pixmap(self.inference_label, self._inference_pixmap)

    def _apply_scaled_pixmap(self, label: QLabel, pixmap) -> None:
        if pixmap is None or label.width() <= 0 or label.height() <= 0:
            return
        aspect_mode = getattr(Qt, "AspectRatioMode", None)
        transform_mode = getattr(Qt, "TransformationMode", None)
        keep_aspect = (
            aspect_mode.KeepAspectRatio if aspect_mode is not None else Qt.KeepAspectRatio
        )
        smooth = (
            transform_mode.SmoothTransformation if transform_mode is not None else Qt.SmoothTransformation
        )
        label.setPixmap(pixmap.scaled(label.size(), keep_aspect, smooth))
