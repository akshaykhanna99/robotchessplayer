"""PCA9686 serial robot adapter scaffold using Arduino protocol."""

from __future__ import annotations

from dataclasses import dataclass

from src.motion.types import MotionPlan
from src.robot.config import RobotArmConfig
from src.robot.executor import MotionPlanExecutor
from src.robot.kinematics import SimpleArmKinematics

try:
    import serial
except ImportError:  # pragma: no cover - optional dependency
    serial = None


@dataclass
class Pca9686SerialRobotArm:
    config: RobotArmConfig
    kinematics: SimpleArmKinematics
    serial_handle: "serial.Serial | None" = None

    def connect(self) -> None:
        if serial is None:
            raise RuntimeError("pyserial is not installed; cannot open serial connection")
        transport = self.config.transport
        self.serial_handle = serial.Serial(
            port=transport.port,
            baudrate=transport.baud,
            timeout=transport.timeout_sec,
        )

    def disconnect(self) -> None:
        if self.serial_handle:
            self.serial_handle.close()
        self.serial_handle = None

    def home(self) -> None:
        if self.config.named_poses and self.config.home_pose_name in self.config.named_poses:
            pose = self.config.named_poses[self.config.home_pose_name]
            if pose.joint_deg:
                self.send_joint_positions(
                    {
                        "base": pose.joint_deg.base_deg,
                        "shoulder": pose.joint_deg.shoulder_deg,
                        "elbow": pose.joint_deg.elbow_deg,
                        "wrist": pose.joint_deg.wrist_deg,
                    }
                )
                return
            if pose.pose:
                joint_targets = self.kinematics.solve_cartesian_to_joint(pose.pose)
                self.send_joint_positions(joint_targets.to_dict())
                return
        raise RuntimeError("Home pose not configured for robot")

    def execute_motion_plan(self, plan: MotionPlan) -> None:
        executor = MotionPlanExecutor(self.kinematics, self)
        executor.execute(plan)

    def send_joint_positions(self, joint_targets_deg: dict[str, float], speed_mm_s: float | None = None) -> None:
        self._ensure_connected()
        channels = self.config.channels
        mapping = {
            "base": channels.base,
            "shoulder": channels.shoulder,
            "elbow": channels.elbow,
            "wrist": channels.wrist,
        }
        for joint_name, angle in joint_targets_deg.items():
            if joint_name not in mapping:
                continue
            channel = mapping[joint_name]
            self._send_servo_command(channel, angle)

    def open_gripper(self) -> None:
        self._ensure_connected()
        self._send_servo_command(self.config.channels.gripper, self.config.gripper.open_deg)

    def close_gripper(self) -> None:
        self._ensure_connected()
        self._send_servo_command(self.config.channels.gripper, self.config.gripper.close_deg)

    def _send_servo_command(self, channel: int, angle: float) -> None:
        if not self.serial_handle:
            return
        command = f"PCA {channel} {angle:.1f}\n"
        self.serial_handle.write(command.encode("utf-8"))

    def _ensure_connected(self) -> None:
        if not self.serial_handle:
            raise RuntimeError("Robot serial connection is not open")
