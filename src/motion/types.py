"""Core hardware-agnostic motion planning types."""

from dataclasses import dataclass, field
from typing import Literal


@dataclass(frozen=True)
class Pose:
    """Cartesian end-effector pose in a shared board/world coordinate frame."""

    x_mm: float
    y_mm: float
    z_mm: float
    yaw_deg: float = 0.0
    pitch_deg: float = 0.0
    roll_deg: float = 0.0


@dataclass(frozen=True)
class BoardSquareRef:
    """Logical chessboard square reference (e.g. e2)."""

    square: str


@dataclass(frozen=True)
class MotionWaypoint:
    """Single motion waypoint with optional execution hints."""

    pose: Pose
    speed_mm_s: float | None = None
    label: str = ""


@dataclass(frozen=True)
class MotionSegment:
    """A named segment of motion (e.g. approach, lift, transfer, place)."""

    name: str
    waypoints: tuple[MotionWaypoint, ...]


@dataclass(frozen=True)
class MotionPlan:
    """Complete motion plan for a robot task."""

    task_name: str
    segments: tuple[MotionSegment, ...]


@dataclass(frozen=True)
class GripperAction:
    """Open/close gripper command used by task planning."""

    action: Literal["open", "close"]
    label: str = ""


@dataclass(frozen=True)
class MotionAction:
    """Union-like task action type for motion planning pipeline."""

    kind: Literal["move_to_square", "retreat_from_square", "move_to_pose", "gripper"]
    square: BoardSquareRef | None = None
    pose: Pose | None = None
    gripper: GripperAction | None = None
    label: str = ""


@dataclass(frozen=True)
class RobotTask:
    """Hardware-agnostic manipulation task sequence."""

    name: str
    actions: tuple[MotionAction, ...] = field(default_factory=tuple)
