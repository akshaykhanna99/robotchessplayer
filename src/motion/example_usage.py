"""Small local demo of motion planning from a UCI move (no hardware required)."""

from src.motion.board_mapper import BoardGeometry, BoardMapper
from src.motion.planner import MotionPlanner
from src.motion.task_planner import ChessTaskPlanner
from src.motion.trajectory import CartesianTrajectoryPlanner


def main():
    geometry = BoardGeometry(
        origin_x_mm=0,
        origin_y_mm=0,
        board_z_mm=0,
        square_size_mm=50,
    )
    planner = MotionPlanner(
        task_planner=ChessTaskPlanner(),
        trajectory_planner=CartesianTrajectoryPlanner(BoardMapper(geometry)),
    )
    task, plan = planner.plan_uci_move("e2e4")
    print(task)
    print(plan)


if __name__ == "__main__":
    main()
