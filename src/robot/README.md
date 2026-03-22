# Robot Control Layer

This package owns hardware-specific execution concerns.

## Current contents

- `config.py`
  - Dataclasses and JSON loader for a physical setup profile (board geometry + robot arm config)
- `interfaces.py`
  - `RobotArmInterface` protocol for concrete robot adapters
- `kinematics.py`
  - Cartesian-to-joint IK for a simple 4-DOF arm
- `executor.py`
  - Walks `MotionPlan` objects and dispatches gripper/waypoint commands
- `adapters/`
  - `MockRobotArm` for dry-run testing
  - `Pca9686SerialRobotArm` scaffold for Arduino serial protocol (`PCA <channel> <angle>`)

## Config schema overview (robot)

Key robot fields in `config/physical_setup.example.json`:

- `kinematics`: link lengths, base height, optional tool offset
- `joint_limits_deg`: min/max per joint
- `calibration`: zero offsets, direction signs, per-joint scaling
- `named_poses`: joint or Cartesian named poses (e.g. `home`, `standby`)
- `base_to_board`: transform from robot base frame to board frame
- `gripper`: open/close angles for the gripper servo

Adapters read this config and execute `MotionPlan` objects produced by `src/motion/`.
