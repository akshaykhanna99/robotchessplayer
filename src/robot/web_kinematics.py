"""Backend kinematics helpers for the web control centre."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from src.motion.board_mapper import BoardGeometry, BoardMapper
from src.motion.types import Pose
from src.robot.config import (
    BaseToBoardTransform,
    JointLimitDeg,
    JointLimitsDeg,
    LinkLengthsMm,
    RobotKinematicsConfig,
    ToolOffsetMm,
)
from src.robot.kinematics import JointAngles, SimpleArmKinematics


@dataclass(frozen=True)
class JointDegreeConfig:
    min_deg: float
    max_deg: float
    home_deg: float
    solver_sign: float = 1.0


@dataclass(frozen=True)
class WebJointTelemetry:
    minimum_deg: float
    maximum_deg: float
    target_deg: float
    current_deg: float
    control_mode: str = "manual"


class WebKinematicsModel:
    """Maps servo pulse targets to joint degrees for the web control centre."""

    def __init__(
        self,
        joint_configs: dict[str, JointDegreeConfig],
        board_mapper: BoardMapper,
        solver: SimpleArmKinematics,
    ) -> None:
        self._joint_configs = joint_configs
        self._board_mapper = board_mapper
        self._solver = solver

    @classmethod
    def from_digital_twin_config(cls, path: str | Path) -> "WebKinematicsModel":
        with Path(path).open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        joints = data.get("robot", {}).get("joints", {})
        joint_configs = {
            name: JointDegreeConfig(
                min_deg=float(config["min_deg"]),
                max_deg=float(config["max_deg"]),
                home_deg=float(config["home_deg"]),
                solver_sign=float(config.get("solver_sign", 1.0)),
            )
            for name, config in joints.items()
        }
        board = data["board"]
        board_size = float(board["square_size_mm"]) * 8.0
        border_x = (float(board["board_size_x_mm"]) - board_size) / 2.0
        border_y = (float(board["board_size_y_mm"]) - board_size) / 2.0
        board_mapper = BoardMapper(
            BoardGeometry(
                origin_x_mm=float(board["origin_x_mm"]) + border_x,
                origin_y_mm=float(board["origin_y_mm"]) + border_y,
                board_z_mm=float(board["origin_z_mm"]),
                square_size_mm=float(board["square_size_mm"]),
                approach_height_mm=float(data.get("pieces", {}).get("default_clearance_above_piece_mm", 40.0)),
                lift_height_mm=float(data.get("pieces", {}).get("default_clearance_above_piece_mm", 40.0)),
            )
        )
        robot = data["robot"]
        tool = data["tool"]
        pickup = tool.get("pickup_point_offset_mm", {})
        mount = tool.get("mount_offset_mm", {})
        solver = SimpleArmKinematics(
            kinematics=RobotKinematicsConfig(
                link_lengths_mm=LinkLengthsMm(
                    shoulder_mm=float(robot["links"][0]["length_mm"]),
                    elbow_mm=float(robot["links"][1]["length_mm"]),
                    wrist_mm=float(robot["links"][2]["length_mm"]),
                ),
                base_height_mm=0.0,
                tool_offset_mm=ToolOffsetMm(
                    x_mm=float(mount.get("x_mm", 0.0)) + float(pickup.get("x_mm", 0.0)),
                    y_mm=float(mount.get("y_mm", 0.0)) + float(pickup.get("y_mm", 0.0)),
                    z_mm=float(mount.get("z_mm", 0.0)) + float(pickup.get("z_mm", 0.0)),
                ),
            ),
            joint_limits=JointLimitsDeg(
                base=JointLimitDeg(joint_configs["base"].min_deg, joint_configs["base"].max_deg),
                shoulder=JointLimitDeg(joint_configs["shoulder"].min_deg, joint_configs["shoulder"].max_deg),
                elbow=JointLimitDeg(joint_configs["elbow"].min_deg, joint_configs["elbow"].max_deg),
                wrist=JointLimitDeg(joint_configs["wrist"].min_deg, joint_configs["wrist"].max_deg),
            ),
            base_to_board=BaseToBoardTransform(
                x_mm=float(robot["base_frame"]["x_mm"]),
                y_mm=float(robot["base_frame"]["y_mm"]),
                z_mm=float(robot["base_frame"]["z_mm"]),
                yaw_deg=float(robot["base_frame"].get("yaw_deg", 0.0)),
            ),
        )
        return cls(joint_configs, board_mapper, solver)

    def has_joint(self, name: str) -> bool:
        return name in self._joint_configs

    def home_pulse(self, name: str, pulse_min: float, pulse_max: float) -> float:
        config = self._joint_configs[name]
        return self.degrees_to_pulse(name, config.home_deg, pulse_min, pulse_max)

    def pulse_to_degrees(self, name: str, pulse: float, pulse_min: float, pulse_max: float) -> float:
        config = self._joint_configs[name]
        if pulse_max <= pulse_min:
            return config.min_deg
        ratio = (pulse - pulse_min) / (pulse_max - pulse_min)
        return config.min_deg + ratio * (config.max_deg - config.min_deg)

    def current_joint_angles_from_pulses(self, joints: dict[str, Any]) -> JointAngles:
        return JointAngles(
            base_deg=self.pulse_to_degrees("base", joints["base"].current, joints["base"].minimum, joints["base"].maximum),
            shoulder_deg=self.pulse_to_degrees(
                "shoulder",
                joints["shoulder"].current,
                joints["shoulder"].minimum,
                joints["shoulder"].maximum,
            ),
            elbow_deg=self.pulse_to_degrees("elbow", joints["elbow"].current, joints["elbow"].minimum, joints["elbow"].maximum),
            wrist_deg=self.pulse_to_degrees("wrist", joints["wrist"].current, joints["wrist"].minimum, joints["wrist"].maximum),
        )

    def degrees_to_pulse(self, name: str, degrees: float, pulse_min: float, pulse_max: float) -> float:
        config = self._joint_configs[name]
        if config.max_deg <= config.min_deg:
            return pulse_min
        ratio = (degrees - config.min_deg) / (config.max_deg - config.min_deg)
        return pulse_min + ratio * (pulse_max - pulse_min)

    def auto_level_wrist_degrees(self, shoulder_deg: float, elbow_deg: float) -> float:
        wrist = self._joint_configs["wrist"]
        shoulder_internal = shoulder_deg * self._joint_configs["shoulder"].solver_sign
        elbow_internal = elbow_deg * self._joint_configs["elbow"].solver_sign
        wrist_internal = -(shoulder_internal + elbow_internal)
        target = wrist_internal / wrist.solver_sign
        return max(wrist.min_deg, min(wrist.max_deg, target))

    def solve_square_pickup(
        self,
        square: str,
        initial_guess: JointAngles | None = None,
    ) -> tuple[Pose, JointAngles]:
        pose = self._board_mapper.square_center_pose(square)
        solved = self._solver.solve_cartesian_to_joint(pose, apply_calibration=False)
        base_deg = solved.base_deg * self._joint_configs["base"].solver_sign
        shoulder_deg = solved.shoulder_deg * self._joint_configs["shoulder"].solver_sign
        elbow_deg = solved.elbow_deg * self._joint_configs["elbow"].solver_sign
        return pose, JointAngles(
            base_deg=base_deg,
            shoulder_deg=shoulder_deg,
            elbow_deg=elbow_deg,
            wrist_deg=self.auto_level_wrist_degrees(shoulder_deg, elbow_deg),
        )

    def maybe_apply_coupled_targets(self, joints: dict[str, Any], changed_joint: str) -> dict[str, float]:
        targets = {name: float(joint.target) for name, joint in joints.items()}
        if changed_joint not in {"shoulder", "elbow"}:
            return targets
        if not {"shoulder", "elbow", "wrist"}.issubset(joints):
            return targets
        shoulder = joints["shoulder"]
        elbow = joints["elbow"]
        wrist = joints["wrist"]
        shoulder_deg = self.pulse_to_degrees("shoulder", targets["shoulder"], shoulder.minimum, shoulder.maximum)
        elbow_deg = self.pulse_to_degrees("elbow", targets["elbow"], elbow.minimum, elbow.maximum)
        wrist_deg = self.auto_level_wrist_degrees(shoulder_deg, elbow_deg)
        targets["wrist"] = round(self.degrees_to_pulse("wrist", wrist_deg, wrist.minimum, wrist.maximum))
        return targets

    def telemetry_for_joint(self, name: str, current: float, target: float, pulse_min: float, pulse_max: float) -> WebJointTelemetry | None:
        if name not in self._joint_configs:
            return None
        config = self._joint_configs[name]
        control_mode = "auto-level" if name == "wrist" else "manual"
        return WebJointTelemetry(
            minimum_deg=config.min_deg,
            maximum_deg=config.max_deg,
            target_deg=self.pulse_to_degrees(name, target, pulse_min, pulse_max),
            current_deg=self.pulse_to_degrees(name, current, pulse_min, pulse_max),
            control_mode=control_mode,
        )
