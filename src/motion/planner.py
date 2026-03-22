"""Facade that turns UCI moves into hardware-agnostic motion plans."""

from src.motion.task_planner import ChessTaskPlanner
from src.motion.trajectory import CartesianTrajectoryPlanner
from src.motion.types import MotionPlan, RobotTask


class MotionPlanner:
    """End-to-end hardware-agnostic motion planner."""

    def __init__(self, task_planner: ChessTaskPlanner, trajectory_planner: CartesianTrajectoryPlanner):
        self.task_planner = task_planner
        self.trajectory_planner = trajectory_planner

    def plan_uci_move(self, uci_move: str, is_capture: bool = False) -> tuple[RobotTask, MotionPlan]:
        task = self.task_planner.plan_move(uci_move, is_capture=is_capture)
        motion_plan = self.trajectory_planner.plan_task(task)
        return task, motion_plan
