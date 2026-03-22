"""Robot top-view (XY) digital twin rendering."""

from __future__ import annotations

from src.motion.types import MotionPlan, Pose
from src.ui.qt import QColor, QPainter, QPen, QWidget


class RobotTopViewPanel(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self._board_origin = (0.0, 0.0)
        self._square_size = 50.0
        self._waypoints: list[Pose] = []
        self._current_index = -1

    def set_board_geometry(self, origin_x: float, origin_y: float, square_size: float) -> None:
        self._board_origin = (origin_x, origin_y)
        self._square_size = square_size
        self.update()

    def set_plan(self, plan: MotionPlan) -> None:
        self._waypoints = self._extract_waypoints(plan)
        self._current_index = -1
        self.update()

    def update_progress(self, pose: Pose | None) -> None:
        if pose is None:
            return
        try:
            self._current_index = self._waypoints.index(pose)
        except ValueError:
            pass
        self.update()

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#10141a"))

        width = self.width()
        height = self.height()
        board_size = self._square_size * 8
        margin = 20
        scale = min((width - 2 * margin) / board_size, (height - 2 * margin) / board_size)
        if scale <= 0:
            return
        origin_x = margin
        origin_y = margin

        pen = QPen(QColor("#2d7d46"))
        pen.setWidth(2)
        painter.setPen(pen)
        painter.drawRect(origin_x, origin_y, board_size * scale, board_size * scale)

        path_pen = QPen(QColor("#3da9fc"))
        path_pen.setWidth(2)
        painter.setPen(path_pen)
        for idx, pose in enumerate(self._waypoints):
            x = origin_x + (pose.x_mm - self._board_origin[0]) * scale
            y = origin_y + (pose.y_mm - self._board_origin[1]) * scale
            radius = 4
            painter.drawEllipse(int(x - radius), int(y - radius), radius * 2, radius * 2)
            if idx == self._current_index:
                painter.setPen(QPen(QColor("#f6d32d"), 3))
                painter.drawEllipse(int(x - 6), int(y - 6), 12, 12)
                painter.setPen(path_pen)

        painter.end()

    @staticmethod
    def _extract_waypoints(plan: MotionPlan) -> list[Pose]:
        waypoints: list[Pose] = []
        for segment in plan.segments:
            if segment.name == "gripper":
                continue
            for waypoint in segment.waypoints:
                waypoints.append(waypoint.pose)
        return waypoints
