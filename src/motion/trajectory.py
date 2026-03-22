"""Convert high-level square tasks into Cartesian waypoint plans."""

from src.motion.board_mapper import BoardMapper
from src.motion.types import MotionAction, MotionPlan, MotionSegment, MotionWaypoint, Pose, RobotTask


class CartesianTrajectoryPlanner:
    """Simple hardware-agnostic waypoint generator for board pick/place tasks."""

    def __init__(self, board_mapper: BoardMapper, travel_height_mm: float = 80.0):
        self.board_mapper = board_mapper
        self.travel_height_mm = travel_height_mm

    def plan_task(self, task: RobotTask) -> MotionPlan:
        segments: list[MotionSegment] = []
        for action in task.actions:
            segments.extend(self._plan_action(action))
        return MotionPlan(task_name=task.name, segments=tuple(segments))

    def _plan_action(self, action: MotionAction) -> list[MotionSegment]:
        if action.kind == "gripper" and action.gripper:
            marker = MotionWaypoint(
                pose=Pose(0, 0, 0),
                label=f"gripper:{action.gripper.action}:{action.label or action.gripper.label}",
            )
            return [MotionSegment(name="gripper", waypoints=(marker,))]

        if action.kind == "move_to_pose" and action.pose:
            return [MotionSegment(name=action.label or "move_to_pose", waypoints=(MotionWaypoint(action.pose),))]

        if action.kind == "move_to_square" and action.square:
            sq = action.square.square
            approach = self.board_mapper.approach_pose(sq)
            surface = self.board_mapper.square_center_pose(sq)
            travel = Pose(surface.x_mm, surface.y_mm, self.travel_height_mm)
            return [
                MotionSegment(
                    name=action.label or f"move_to_{sq}",
                    waypoints=(
                        MotionWaypoint(travel, label=f"{sq}_travel"),
                        MotionWaypoint(approach, label=f"{sq}_approach"),
                        MotionWaypoint(surface, label=f"{sq}_surface"),
                    ),
                )
            ]

        if action.kind == "retreat_from_square" and action.square:
            sq = action.square.square
            lift = self.board_mapper.lift_pose(sq)
            travel = Pose(lift.x_mm, lift.y_mm, self.travel_height_mm)
            return [
                MotionSegment(
                    name=action.label or f"retreat_from_{sq}",
                    waypoints=(
                        MotionWaypoint(lift, label=f"{sq}_lift"),
                        MotionWaypoint(travel, label=f"{sq}_travel_clear"),
                    ),
                )
            ]

        raise ValueError(f"Unsupported motion action: {action}")
