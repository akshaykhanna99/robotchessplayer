"""Execution pipeline for MotionPlan -> robot adapter commands."""

from __future__ import annotations

from dataclasses import dataclass

from src.motion.types import MotionPlan, MotionSegment
from src.robot.kinematics import SimpleArmKinematics
from src.robot.interfaces import RobotArmInterface


@dataclass(frozen=True)
class MotionPlanExecutor:
    kinematics: SimpleArmKinematics
    adapter: RobotArmInterface
    apply_calibration: bool = True

    def execute(self, plan: MotionPlan) -> None:
        for segment in plan.segments:
            if segment.name == "gripper":
                self._execute_gripper(segment)
            else:
                self._execute_waypoints(segment)

    def _execute_gripper(self, segment: MotionSegment) -> None:
        if not segment.waypoints:
            return
        label = segment.waypoints[0].label or ""
        action = self._parse_gripper_label(label)
        if action == "open":
            self.adapter.open_gripper()
        elif action == "close":
            self.adapter.close_gripper()

    def _execute_waypoints(self, segment: MotionSegment) -> None:
        for waypoint in segment.waypoints:
            joint_targets = self.kinematics.solve_cartesian_to_joint(
                waypoint.pose,
                apply_calibration=self.apply_calibration,
            )
            self.adapter.send_joint_positions(joint_targets.to_dict(), speed_mm_s=waypoint.speed_mm_s)

    @staticmethod
    def _parse_gripper_label(label: str) -> str | None:
        if not label.startswith("gripper:"):
            return None
        parts = label.split(":")
        if len(parts) < 2:
            return None
        return parts[1]
