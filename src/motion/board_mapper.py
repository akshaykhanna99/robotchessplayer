"""Map chess squares to physical board coordinates using config."""

from dataclasses import dataclass

from src.motion.types import Pose


FILES = "abcdefgh"
RANKS = "12345678"


@dataclass(frozen=True)
class BoardGeometry:
    """Physical board geometry and origin/orientation configuration."""

    origin_x_mm: float
    origin_y_mm: float
    board_z_mm: float
    square_size_mm: float
    approach_height_mm: float = 40.0
    lift_height_mm: float = 60.0
    capture_bin_x_mm: float | None = None
    capture_bin_y_mm: float | None = None
    capture_bin_z_mm: float | None = None
    file_axis_reversed: bool = False
    rank_axis_reversed: bool = False


class BoardMapper:
    """Converts chess squares into Cartesian target poses."""

    def __init__(self, geometry: BoardGeometry):
        self.geometry = geometry

    def square_to_indices(self, square: str) -> tuple[int, int]:
        if len(square) != 2 or square[0] not in FILES or square[1] not in RANKS:
            raise ValueError(f"Invalid chess square '{square}'")
        file_idx = FILES.index(square[0])
        rank_idx = RANKS.index(square[1])
        if self.geometry.file_axis_reversed:
            file_idx = 7 - file_idx
        if self.geometry.rank_axis_reversed:
            rank_idx = 7 - rank_idx
        return file_idx, rank_idx

    def square_center_pose(self, square: str, z_mm: float | None = None) -> Pose:
        file_idx, rank_idx = self.square_to_indices(square)
        x_mm = self.geometry.origin_x_mm + (file_idx + 0.5) * self.geometry.square_size_mm
        y_mm = self.geometry.origin_y_mm + (rank_idx + 0.5) * self.geometry.square_size_mm
        return Pose(
            x_mm=x_mm,
            y_mm=y_mm,
            z_mm=self.geometry.board_z_mm if z_mm is None else z_mm,
        )

    def approach_pose(self, square: str) -> Pose:
        return self.square_center_pose(square, z_mm=self.geometry.board_z_mm + self.geometry.approach_height_mm)

    def lift_pose(self, square: str) -> Pose:
        return self.square_center_pose(square, z_mm=self.geometry.board_z_mm + self.geometry.lift_height_mm)

    def capture_bin_pose(self) -> Pose:
        g = self.geometry
        if None in (g.capture_bin_x_mm, g.capture_bin_y_mm, g.capture_bin_z_mm):
            raise ValueError("Capture bin pose is not configured in BoardGeometry")
        return Pose(g.capture_bin_x_mm, g.capture_bin_y_mm, g.capture_bin_z_mm)
