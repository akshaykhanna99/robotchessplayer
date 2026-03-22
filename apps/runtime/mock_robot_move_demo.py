"""Mock end-to-end demo: UCI move -> MotionPlan -> mock robot execution."""

from __future__ import annotations

import argparse
from pathlib import Path

from src.motion.board_mapper import BoardMapper
from src.motion.planner import MotionPlanner
from src.motion.task_planner import ChessTaskPlanner
from src.motion.trajectory import CartesianTrajectoryPlanner
from src.robot.adapters.mock_robot import MockRobotArm
from src.robot.config import load_physical_setup_config
from src.robot.kinematics import SimpleArmKinematics


def main() -> None:
    parser = argparse.ArgumentParser(description="Mock robot motion demo")
    parser.add_argument("--uci", default="e2e4", help="UCI move string, e.g. e2e4")
    parser.add_argument(
        "--config",
        default=str(Path(__file__).resolve().parents[2] / "config" / "physical_setup.example.json"),
        help="Path to physical setup JSON",
    )
    args = parser.parse_args()

    setup = load_physical_setup_config(args.config)
    planner = MotionPlanner(
        task_planner=ChessTaskPlanner(),
        trajectory_planner=CartesianTrajectoryPlanner(BoardMapper(setup.board)),
    )
    task, plan = planner.plan_uci_move(args.uci)

    print("[demo] task:", task)
    print("[demo] plan:", plan)

    kinematics = SimpleArmKinematics.from_robot_config(setup.robot)
    robot = MockRobotArm(config=setup.robot, kinematics=kinematics)
    robot.connect()
    robot.home()
    robot.execute_motion_plan(plan)
    robot.disconnect()


if __name__ == "__main__":
    main()
