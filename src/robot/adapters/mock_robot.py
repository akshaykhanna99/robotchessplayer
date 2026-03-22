"""Mock robot adapter for end-to-end integration without hardware."""

from __future__ import annotations

from dataclasses import dataclass, field

from src.motion.types import MotionPlan
from src.robot.config import RobotArmConfig
from src.robot.executor import MotionPlanExecutor
from src.robot.kinematics import KinematicsError, SimpleArmKinematics


@dataclass
class MockRobotArm:
    config: RobotArmConfig
    kinematics: SimpleArmKinematics
    log: list[str] = field(default_factory=list)

    def connect(self) -> None:
        self._log("connect")

    def disconnect(self) -> None:
        self._log("disconnect")

    def home(self) -> None:
        pose = None
        if self.config.named_poses:
            pose = self.config.named_poses.get(self.config.home_pose_name)
        if pose and pose.joint_deg:
            self.send_joint_positions(
                {
                    "base": pose.joint_deg.base_deg,
                    "shoulder": pose.joint_deg.shoulder_deg,
                    "elbow": pose.joint_deg.elbow_deg,
                    "wrist": pose.joint_deg.wrist_deg,
                }
            )
        elif pose and pose.pose:
            try:
                joint_targets = self.kinematics.solve_cartesian_to_joint(pose.pose)
                self.send_joint_positions(joint_targets.to_dict())
            except KinematicsError as exc:
                self._log(f"home failed: {exc}")
        else:
            self._log("home (no named pose configured)")

    def execute_motion_plan(self, plan: MotionPlan) -> None:
        executor = MotionPlanExecutor(self.kinematics, self)
        executor.execute(plan)

    def send_joint_positions(self, joint_targets_deg: dict[str, float], speed_mm_s: float | None = None) -> None:
        speed_label = f" speed={speed_mm_s}" if speed_mm_s else ""
        self._log(f"joints {joint_targets_deg}{speed_label}")

    def open_gripper(self) -> None:
        self._log("gripper open")

    def close_gripper(self) -> None:
        self._log("gripper close")

    def _log(self, message: str) -> None:
        entry = f"[mock_robot] {message}"
        print(entry)
        self.log.append(entry)
