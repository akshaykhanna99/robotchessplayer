"""Clickable QLabel for capturing mouse positions."""

from __future__ import annotations

from src.ui.qt import QLabel, Signal


class ClickableLabel(QLabel):
    clicked = Signal(int, int, int, int)

    def mousePressEvent(self, event):
        pos = event.position() if hasattr(event, "position") else event.pos()
        x = int(pos.x())
        y = int(pos.y())

        pixmap = self.pixmap()
        if pixmap is not None and not pixmap.isNull():
            pix_w = pixmap.width()
            pix_h = pixmap.height()
            offset_x = max((self.width() - pix_w) // 2, 0)
            offset_y = max((self.height() - pix_h) // 2, 0)

            # Ignore clicks in the letterboxed padding area.
            if not (offset_x <= x < offset_x + pix_w and offset_y <= y < offset_y + pix_h):
                return

            self.clicked.emit(x - offset_x, y - offset_y, pix_w, pix_h)
        else:
            self.clicked.emit(x, y, self.width(), self.height())
        super().mousePressEvent(event)
