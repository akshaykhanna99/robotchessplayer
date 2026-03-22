"""Lightweight validation for config loading and mock execution pipeline."""

from __future__ import annotations

from pathlib import Path

from src.motion.board_mapper import BoardMapper
from src.motion.planner import MotionPlanner
from src.motion.task_planner import ChessTaskPlanner
from src.motion.trajectory import CartesianTrajectoryPlanner
from src.robot.adapters.mock_robot import MockRobotArm
from src.robot.config import load_physical_setup_config
from src.robot.kinematics import SimpleArmKinematics


def _run_validation() -> None:
    config_path = Path(__file__).resolve().parents[1] / "config" / "physical_setup.example.json"
    setup = load_physical_setup_config(config_path)

    board_mapper = BoardMapper(setup.board)
    planner = MotionPlanner(
        task_planner=ChessTaskPlanner(),
        trajectory_planner=CartesianTrajectoryPlanner(board_mapper),
    )

    task, plan = planner.plan_uci_move("e2e4")
    assert task.actions, "RobotTask should contain actions"
    assert plan.segments, "MotionPlan should contain segments"

    pose = board_mapper.square_center_pose("e2")
    assert pose.x_mm >= setup.board.origin_x_mm, "Pose should be within board bounds"

    kinematics = SimpleArmKinematics.from_robot_config(setup.robot)
    robot = MockRobotArm(config=setup.robot, kinematics=kinematics)
    robot.connect()
    robot.execute_motion_plan(plan)
    robot.disconnect()

    print("[validate] OK")


def test_motion_pipeline() -> None:
    _run_validation()


def main() -> None:
    _run_validation()


if __name__ == "__main__":
    main()
