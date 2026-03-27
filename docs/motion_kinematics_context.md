# Motion And Kinematics Context

This document captures the current review findings for the motion-planning and kinematics stack so the work can be tackled incrementally.

## Current Assessment

The existing architecture direction is good:

- board-space task planning is separated from robot-space IK
- physical setup is config-driven
- execution is decoupled from planning through adapters

The current implementation is still a scaffold, not yet a reliable geometric core for a real digital twin or real chess-piece manipulation.

## Findings

### 1. Travel Height Uses An Absolute Z Instead Of Board-Relative Clearance

Current issue:

- `CartesianTrajectoryPlanner` creates travel waypoints with `z = travel_height_mm`
- this ignores `board_z_mm`
- any setup where the board surface is not at `z = 0` will produce incorrect clearances

Impact:

- travel moves may be too low
- path may intersect pieces or the board
- digital twin validation would be misleading

Relevant code:

- `src/motion/trajectory.py`

Recommended direction:

- replace absolute travel height with `travel_clearance_above_board_mm`
- compute travel `z` as `board_z_mm + clearance`

### 2. IK Model Is Too Simplified For A Real 4-DOF Chess Arm

Current issue:

- `SimpleArmKinematics` reduces the problem to a planar 2-link solution plus a scalar wrist reach term
- this is only valid for a narrow class of arm geometries
- it does not explicitly solve for a wrist centre from a desired tool orientation

Impact:

- solver may appear to work for simple targets but be geometrically wrong
- end-effector orientation cannot be trusted
- digital twin and hardware behaviour will diverge

Relevant code:

- `src/robot/kinematics.py`

Recommended direction:

- short term: solve wrist-centre position from desired tool orientation, then solve shoulder/elbow
- longer term: model the robot with explicit joint axes and link transforms, with FK and IK built on that model

### 3. Frame Transform Handles Position But Not Orientation

Current issue:

- `board_pose_to_base()` transforms `x/y/z`
- `yaw_deg` is passed through unchanged
- if the board is rotated relative to the robot base, orientations become inconsistent

Impact:

- tool orientation will be wrong once yaw-sensitive grasping is introduced
- simulation and hardware alignment will drift

Relevant code:

- `src/robot/kinematics.py`

Recommended direction:

- make transforms responsible for both translation and orientation
- introduce a clearer frame model: `board/world`, `robot base`, `tool`

### 4. Planner Targets Board Surface Instead Of Piece Interaction Pose

Current issue:

- `square_center_pose()` resolves to the board plane
- motion planning descends to the board surface rather than a piece-specific grasp height

Impact:

- current pick/place behaviour is not physically correct
- real gripper interactions cannot be modeled accurately
- digital twin cannot evaluate grasp validity

Relevant code:

- `src/motion/board_mapper.py`
- `src/motion/trajectory.py`

Recommended direction:

- separate concepts:
  - board square location
  - piece occupancy
  - grasp pose
  - approach pose
- add piece dimensions and grasp offsets to configuration

### 5. Capture Sequence Is Placeholder Logic

Current issue:

- capture flow closes on the captured piece, lifts, then opens immediately
- capture bin coordinates already exist in config but are not used in the task planner

Impact:

- `is_capture=True` is not valid execution logic
- scene state and motion planning are not aligned

Relevant code:

- `src/motion/task_planner.py`
- `src/motion/board_mapper.py`

Recommended direction:

- route captured pieces to a configured capture tray pose
- make capture planning scene-aware

## Design Principles To Keep

- keep board-space planning separate from robot-base-space IK
- keep setup data externalized in config
- keep execution adapters separate from planner logic

## Immediate Work Queue

### Phase 1. Digital Twin Foundations

- define coordinate frames explicitly
- define board, piece, tool, and obstacle geometry
- define scene state separately from motion planning
- choose a visualization/simulation stack compatible with the current app

### Phase 2. Motion Model Corrections

- fix board-relative travel heights
- introduce grasp poses and piece dimensions
- separate surface pose from manipulation pose

### Phase 3. Kinematics Upgrade

- add forward kinematics
- replace or upgrade the current IK formulation
- make transforms orientation-aware

### Phase 4. Scene-Aware Planning

- model occupancy, captures, and destination interactions
- validate moves against the digital twin before hardware execution

## Proposed Target Architecture

- `board/world frame`: squares, pieces, scene geometry
- `robot base frame`: joint geometry and robot kinematics
- `tool frame`: gripper or pickup point
- `base_to_board transform`: calibrated rigid transform between robot and board

Planning flow:

1. task planner works in board/world space
2. trajectory planner generates board/world waypoints
3. transform layer converts target pose into robot-base space
4. IK converts base-space target into joint commands
5. digital twin validates reach, clearance, and collisions

## Decision For Next Step

Start with the 3D virtual environment before deeper kinematics changes, but keep the simulation interfaces aligned with the target architecture above so later FK/IK upgrades fit cleanly.
