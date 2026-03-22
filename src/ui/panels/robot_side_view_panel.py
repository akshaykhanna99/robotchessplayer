"""Robot side-view (XZ) digital twin rendering."""

from __future__ import annotations

from src.motion.types import MotionPlan, Pose
from src.ui.qt import QColor, QPainter, QPen, QWidget


class RobotSideViewPanel(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self._board_origin_x = 0.0
        self._board_z = 0.0
        self._square_size = 50.0
        self._waypoints: list[Pose] = []
        self._current_index = -1

    def set_board_geometry(self, origin_x: float, board_z: float, square_size: float) -> None:
        self._board_origin_x = origin_x
        self._board_z = board_z
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
        max_z = max([pose.z_mm for pose in self._waypoints], default=self._board_z + 120)
        z_range = max_z - self._board_z if max_z > self._board_z else 100
        scale_x = (width - 2 * margin) / board_size if board_size > 0 else 1
        scale_z = (height - 2 * margin) / z_range if z_range > 0 else 1
        scale = min(scale_x, scale_z)

        origin_x = margin
        origin_y = height - margin

        pen = QPen(QColor("#2d7d46"))
        pen.setWidth(2)
        painter.setPen(pen)
        painter.drawLine(origin_x, origin_y, origin_x + board_size * scale, origin_y)

        path_pen = QPen(QColor("#ff6b6b"))
        path_pen.setWidth(2)
        painter.setPen(path_pen)
        for idx, pose in enumerate(self._waypoints):
            x = origin_x + (pose.x_mm - self._board_origin_x) * scale
            z = origin_y - (pose.z_mm - self._board_z) * scale
            radius = 4
            painter.drawEllipse(int(x - radius), int(z - radius), radius * 2, radius * 2)
            if idx == self._current_index:
                painter.setPen(QPen(QColor("#f6d32d"), 3))
                painter.drawEllipse(int(x - 6), int(z - 6), 12, 12)
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
