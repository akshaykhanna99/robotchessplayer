"""UI utilities for image conversion and formatting."""

from __future__ import annotations

import numpy as np

from src.ui.qt import QImage


def bgr_to_qimage(frame_bgr: np.ndarray) -> QImage:
    if frame_bgr is None:
        return QImage()
    height, width, channels = frame_bgr.shape
    rgb = frame_bgr[:, :, ::-1].copy()
    bytes_per_line = channels * width
    return QImage(rgb.data, width, height, bytes_per_line, QImage.Format.Format_RGB888).copy()


def format_timestamp(ts: float) -> str:
    from datetime import datetime

    return datetime.fromtimestamp(ts).strftime("%H:%M:%S")
