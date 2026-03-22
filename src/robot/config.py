"""Robot and board configuration dataclasses/loaders."""

from dataclasses import dataclass, field
import json
from pathlib import Path

from src.motion.board_mapper import BoardGeometry
from src.motion.types import Pose


@dataclass(frozen=True)
class SerialTransportConfig:
    port: str
    baud: int = 115200
    timeout_sec: float = 1.0


@dataclass(frozen=True)
class ServoChannelMap:
    base: int
    shoulder: int
    elbow: int
    wrist: int
    gripper: int


@dataclass(frozen=True)
class LinkLengthsMm:
    shoulder_mm: float
    elbow_mm: float
    wrist_mm: float


@dataclass(frozen=True)
class ToolOffsetMm:
    x_mm: float = 0.0
    y_mm: float = 0.0
    z_mm: float = 0.0


@dataclass(frozen=True)
class RobotKinematicsConfig:
    link_lengths_mm: LinkLengthsMm
    base_height_mm: float = 0.0
    tool_offset_mm: ToolOffsetMm = field(default_factory=ToolOffsetMm)


@dataclass(frozen=True)
class JointLimitDeg:
    min_deg: float
    max_deg: float


@dataclass(frozen=True)
class JointLimitsDeg:
    base: JointLimitDeg
    shoulder: JointLimitDeg
    elbow: JointLimitDeg
    wrist: JointLimitDeg


@dataclass(frozen=True)
class CalibrationConfig:
    zero_offsets_deg: dict[str, float]
    direction_signs: dict[str, float]
    command_scale: dict[str, float]


@dataclass(frozen=True)
class BaseToBoardTransform:
    x_mm: float
    y_mm: float
    z_mm: float
    yaw_deg: float = 0.0


@dataclass(frozen=True)
class GripperConfig:
    open_deg: float = 0.0
    close_deg: float = 90.0


@dataclass(frozen=True)
class JointPose:
    base_deg: float
    shoulder_deg: float
    elbow_deg: float
    wrist_deg: float


@dataclass(frozen=True)
class RobotNamedPose:
    name: str
    joint_deg: JointPose | None = None
    pose: Pose | None = None


@dataclass(frozen=True)
class RobotArmConfig:
    name: str
    transport: SerialTransportConfig
    channels: ServoChannelMap
    kinematics: RobotKinematicsConfig | None = None
    joint_limits: JointLimitsDeg | None = None
    calibration: CalibrationConfig | None = None
    named_poses: dict[str, RobotNamedPose] | None = None
    base_to_board: BaseToBoardTransform | None = None
    gripper: GripperConfig = field(default_factory=GripperConfig)
    home_pose_name: str = "home"
    max_linear_speed_mm_s: float = 100.0


@dataclass(frozen=True)
class PhysicalSetupConfig:
    """Combined physical setup profile for one board + robot installation."""

    setup_name: str
    board: BoardGeometry
    robot: RobotArmConfig


def _load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_physical_setup_config(path: str | Path) -> PhysicalSetupConfig:
    data = _load_json(Path(path))

    board = BoardGeometry(**data["board"])
    robot_data = data["robot"]
    transport = SerialTransportConfig(**robot_data["transport"])
    channels = ServoChannelMap(**robot_data["channels"])
    kinematics = _parse_kinematics(robot_data.get("kinematics"))
    joint_limits = _parse_joint_limits(robot_data.get("joint_limits_deg"))
    calibration = _parse_calibration(robot_data.get("calibration"))
    named_poses = _parse_named_poses(robot_data.get("named_poses"))
    base_to_board = _parse_base_to_board(robot_data.get("base_to_board"))
    gripper = _parse_gripper(robot_data.get("gripper"))
    robot = RobotArmConfig(
        name=robot_data["name"],
        transport=transport,
        channels=channels,
        kinematics=kinematics,
        joint_limits=joint_limits,
        calibration=calibration,
        named_poses=named_poses,
        base_to_board=base_to_board,
        gripper=gripper,
        home_pose_name=robot_data.get("home_pose_name", "home"),
        max_linear_speed_mm_s=robot_data.get("max_linear_speed_mm_s", 100.0),
    )
    return PhysicalSetupConfig(
        setup_name=data["setup_name"],
        board=board,
        robot=robot,
    )


def _parse_kinematics(data: dict | None) -> RobotKinematicsConfig | None:
    if not data:
        return None
    link_lengths = LinkLengthsMm(**data["link_lengths_mm"])
    tool_offset = ToolOffsetMm(**data.get("tool_offset_mm", {}))
    return RobotKinematicsConfig(
        link_lengths_mm=link_lengths,
        base_height_mm=data.get("base_height_mm", 0.0),
        tool_offset_mm=tool_offset,
    )


def _parse_joint_limits(data: dict | None) -> JointLimitsDeg | None:
    if not data:
        return None
    return JointLimitsDeg(
        base=_parse_joint_limit(data["base"]),
        shoulder=_parse_joint_limit(data["shoulder"]),
        elbow=_parse_joint_limit(data["elbow"]),
        wrist=_parse_joint_limit(data["wrist"]),
    )


def _parse_joint_limit(data: dict) -> JointLimitDeg:
    return JointLimitDeg(min_deg=data["min_deg"], max_deg=data["max_deg"])


def _parse_calibration(data: dict | None) -> CalibrationConfig | None:
    if not data:
        return None
    return CalibrationConfig(
        zero_offsets_deg=data.get("zero_offsets_deg", {}),
        direction_signs=data.get("direction_signs", {}),
        command_scale=data.get("command_scale", {}),
    )


def _parse_named_poses(data: dict | None) -> dict[str, RobotNamedPose] | None:
    if not data:
        return None
    named: dict[str, RobotNamedPose] = {}
    for name, pose_data in data.items():
        joint = pose_data.get("joint_deg")
        cart = pose_data.get("pose")
        joint_pose = JointPose(**joint) if joint else None
        cart_pose = Pose(**cart) if cart else None
        named[name] = RobotNamedPose(name=name, joint_deg=joint_pose, pose=cart_pose)
    return named


def _parse_base_to_board(data: dict | None) -> BaseToBoardTransform | None:
    if not data:
        return None
    return BaseToBoardTransform(**data)


def _parse_gripper(data: dict | None) -> GripperConfig:
    if not data:
        return GripperConfig()
    return GripperConfig(open_deg=data.get("open_deg", 0.0), close_deg=data.get("close_deg", 90.0))
