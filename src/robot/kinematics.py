"""Robot kinematics and Cartesian-to-joint conversion."""

from __future__ import annotations

from dataclasses import dataclass
import math

from src.motion.types import Pose
from src.robot.config import (
    BaseToBoardTransform,
    CalibrationConfig,
    JointLimitsDeg,
    RobotArmConfig,
    RobotKinematicsConfig,
)


class KinematicsError(ValueError):
    """Raised when inverse kinematics cannot find a valid solution."""


@dataclass(frozen=True)
class JointAngles:
    base_deg: float
    shoulder_deg: float
    elbow_deg: float
    wrist_deg: float

    def to_dict(self) -> dict[str, float]:
        return {
            "base": self.base_deg,
            "shoulder": self.shoulder_deg,
            "elbow": self.elbow_deg,
            "wrist": self.wrist_deg,
        }


class SimpleArmKinematics:
    """Inverse kinematics for a 4-DOF arm (base + planar 3-link)."""

    def __init__(
        self,
        kinematics: RobotKinematicsConfig,
        joint_limits: JointLimitsDeg | None = None,
        calibration: CalibrationConfig | None = None,
        base_to_board: BaseToBoardTransform | None = None,
    ) -> None:
        self.kinematics = kinematics
        self.joint_limits = joint_limits
        self.calibration = calibration
        self.base_to_board = base_to_board

    @classmethod
    def from_robot_config(cls, config: RobotArmConfig) -> "SimpleArmKinematics":
        if config.kinematics is None:
            raise KinematicsError("Robot config missing kinematics definition")
        return cls(
            kinematics=config.kinematics,
            joint_limits=config.joint_limits,
            calibration=config.calibration,
            base_to_board=config.base_to_board,
        )

    def solve_cartesian_to_joint(self, pose: Pose, apply_calibration: bool = True) -> JointAngles:
        joint_angles = self._solve_ik(pose)
        self._validate_limits(joint_angles)
        if apply_calibration and self.calibration:
            return self._apply_calibration(joint_angles)
        return joint_angles

    def board_pose_to_base(self, pose: Pose) -> Pose:
        if not self.base_to_board:
            return pose
        yaw = math.radians(self.base_to_board.yaw_deg)
        dx = pose.x_mm - self.base_to_board.x_mm
        dy = pose.y_mm - self.base_to_board.y_mm
        dz = pose.z_mm - self.base_to_board.z_mm
        cos_yaw = math.cos(-yaw)
        sin_yaw = math.sin(-yaw)
        x_base = dx * cos_yaw - dy * sin_yaw
        y_base = dx * sin_yaw + dy * cos_yaw
        return Pose(x_mm=x_base, y_mm=y_base, z_mm=dz, yaw_deg=pose.yaw_deg)

    def _solve_ik(self, pose: Pose) -> JointAngles:
        if abs(pose.pitch_deg) > 1e-6 or abs(pose.roll_deg) > 1e-6:
            raise KinematicsError("SimpleArmKinematics does not support non-zero pitch/roll targets")
        base_pose = self.board_pose_to_base(pose)
        x = base_pose.x_mm
        y = base_pose.y_mm
        z = base_pose.z_mm
        r_xy = math.hypot(x, y)
        base_angle = math.degrees(math.atan2(y, x))

        link = self.kinematics.link_lengths_mm
        tool_offset = self.kinematics.tool_offset_mm
        tool_offset_planar = math.hypot(tool_offset.x_mm, tool_offset.y_mm)
        l1 = link.shoulder_mm
        l2 = link.elbow_mm
        l3 = link.wrist_mm + tool_offset_planar
        z_rel = z - self.kinematics.base_height_mm - tool_offset.z_mm
        target_dist = math.hypot(r_xy, z_rel)
        wrist_dist = target_dist - l3

        if wrist_dist <= 0:
            raise KinematicsError("Target too close for wrist reach")
        if wrist_dist > l1 + l2 or wrist_dist < abs(l1 - l2):
            raise KinematicsError("Target is unreachable for given link lengths")

        cos_elbow = (l1**2 + l2**2 - wrist_dist**2) / (2 * l1 * l2)
        cos_elbow = max(-1.0, min(1.0, cos_elbow))
        elbow_angle = math.pi - math.acos(cos_elbow)

        cos_shoulder = (l1**2 + wrist_dist**2 - l2**2) / (2 * l1 * wrist_dist)
        cos_shoulder = max(-1.0, min(1.0, cos_shoulder))
        shoulder_offset = math.acos(cos_shoulder)
        angle_to_target = math.atan2(z_rel, r_xy)
        shoulder_angle = angle_to_target - shoulder_offset

        wrist_angle = angle_to_target - shoulder_angle - elbow_angle

        return JointAngles(
            base_deg=base_angle,
            shoulder_deg=math.degrees(shoulder_angle),
            elbow_deg=math.degrees(elbow_angle),
            wrist_deg=math.degrees(wrist_angle),
        )

    def _apply_calibration(self, joints: JointAngles) -> JointAngles:
        def calibrated(name: str, angle: float) -> float:
            offset = self.calibration.zero_offsets_deg.get(name, 0.0) if self.calibration else 0.0
            sign = self.calibration.direction_signs.get(name, 1.0) if self.calibration else 1.0
            scale = self.calibration.command_scale.get(name, 1.0) if self.calibration else 1.0
            return offset + sign * angle * scale

        return JointAngles(
            base_deg=calibrated("base", joints.base_deg),
            shoulder_deg=calibrated("shoulder", joints.shoulder_deg),
            elbow_deg=calibrated("elbow", joints.elbow_deg),
            wrist_deg=calibrated("wrist", joints.wrist_deg),
        )

    def _validate_limits(self, joints: JointAngles) -> None:
        if not self.joint_limits:
            return
        limits = {
            "base": self.joint_limits.base,
            "shoulder": self.joint_limits.shoulder,
            "elbow": self.joint_limits.elbow,
            "wrist": self.joint_limits.wrist,
        }
        values = joints.to_dict()
        for name, limit in limits.items():
            angle = values[name]
            if angle < limit.min_deg or angle > limit.max_deg:
                raise KinematicsError(
                    f"Joint '{name}' angle {angle:.2f} out of limits {limit.min_deg}..{limit.max_deg}"
                )
