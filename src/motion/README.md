# Motion Planning Layer

Hardware-agnostic planning from chess moves to Cartesian waypoint plans.

## Current contents

- `task_planner.py`
  - Converts UCI chess moves into high-level manipulation tasks (pick/place actions)
- `board_mapper.py`
  - Maps board squares to physical coordinates using board geometry config
- `trajectory.py`
  - Generates simple Cartesian waypoints for task actions
- `planner.py`
  - Facade that returns `(RobotTask, MotionPlan)` from a UCI move
- `types.py`
  - Shared dataclasses (`Pose`, `MotionPlan`, etc.)
- `example_usage.py`
  - Local no-hardware demo

## Scope

This layer should not depend on serial ports, Arduino protocols, or servo channel
details. It produces hardware-agnostic motion intent for the `src/robot/` layer.

The robot layer is responsible for:

- converting `Pose` waypoints into joint targets (IK)
- enforcing joint limits and calibration
- dispatching commands to hardware adapters
