"""State snapshots for UI rendering."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class VisionStatus:
    camera_connected: bool = False
    corners_selected: int = 0
    grid_locked: bool = False


@dataclass
class GameStatus:
    side_to_move: str = "White"
    last_detected_move: str = "-"
    suggested_move: str = "-"
    fen: str = "-"
    mode: str = "Vision Only"


@dataclass
class RobotStatus:
    executing: bool = False
    gripper_state: str = "open"


@dataclass
class SystemStatus:
    setup_name: str = "-"
    robot_name: str = "-"
    serial_port: str = "-"
    square_size_mm: float = 0.0
