# Robot Chess Player System Architecture

## 1. Overview

This repository currently contains two major subsystems that together form a robot chess player stack:

1. Vision + ML + Chess Logic (Python)
2. Robot Actuation / Servo Testing (Python UI + Arduino firmware)

The project is not yet fully integrated end-to-end (camera detection -> move planning -> physical robot move execution), but the core building blocks are present.

## 2. High-Level Architecture

### 2.1 Subsystems

- `Vision/Data Pipeline`: Collect labeled square images, augment them, diagnose dataset quality, train CNN classifiers.
- `Runtime Inference + Game Logic`: Detect board state from camera frames, infer human moves, validate with python-chess, request Stockfish move suggestion.
- `Mechanical Test Stack`: Manual multi-servo control UI over serial to Arduino, with Arduino firmware driving direct servos or a PCA9686 board.
- `Docs/Artifacts`: Design/report assets in `docs/`.

### 2.2 Current System Boundary

The runtime chess pipeline (`main_inference_spacebar.py`) does **not** yet execute robot moves by default, but a mock-first motion/robot integration path exists under `src/motion/`, `src/robot/`, and the new control-centre UI orchestrator.

## 3. Component Map (Repository-Level)

### 3.1 Vision / Inference / Chess Logic

- `main_inference_spacebar.py`
  - Main interactive runtime entry point.
  - Captures webcam frames.
  - Manual corner calibration and perspective warp.
  - Square-by-square CNN classification.
  - Board-state differencing to detect moves.
  - Uses `python-chess` + Stockfish to track legality and suggest Black moves.
- `main_inference.py`
  - Earlier live inference variant (continuous inference cadence).
- `src/vision/testing/evaluate_model.py`
  - Standalone model-quality evaluation script for validating saved `.h5` classifiers on labeled datasets.

### 3.2 Data Collection / Labeling / Augmentation

- `src/vision/labeling/capture/main_label.py`
  - Interactive board capture + manual square labeling workflow.
  - Warps the board, shows each square, saves labeled images.
  - Performs immediate rotation augmentation (90/180/270) on save.
- `apps/labeling/main_label.py`
  - Thin app runner that launches the canonical labeling workflow in `src/vision/labeling/capture/main_label.py`.
- `board_detection.py`
  - Core board corner selection and perspective/grid utilities (prototype/experimental script).
- `src/vision/labeling/augmentation/rotate_images.py`
  - Bulk rotation augmentation across dataset folders.
- Deprecated scripts removed
  - `data_labelling.py` (older overlapping labeling helper)
  - `renameRotatedFIles.py` (legacy filename migration helper)

### 3.3 Model Definition / Training

- `src/vision/models/builders.py`
  - Reusable model builder functions (e.g., baseline and enhanced variants) for the vision classifier.
- `src/vision/training/modelTraining.py`
  - Configurable training runner: loads dataset, selects preprocessing/model variant, trains classifier, and saves a model artifact.
- `src/vision/training/diagnose_dataset.py`
  - Dataset class distribution + brightness/contrast diagnostics used during model iteration.
- `tools/ml/update_inference_for_v6.py`
  - Manual migration helper/instructions for an earlier model version (`v6`).

### 3.4 Mechanical / Servo Testing

- `robot_mech_testing/servo_slider_ui.py`
  - Tkinter UI for 5 joints (base/shoulder/elbow/wrist/gripper).
  - Sends smoothed serial commands to Arduino (`PCA <channel> <angle>`).
- `robot_mech_testing/servo_mixed_serial/servo_mixed_serial.ino`
  - Arduino firmware for PCA9686 serial control using prefixed protocol (`PCA`).
- `robot_mech_testing/servo_pca9686_serial/servo_pca9686_serial.ino`
  - Arduino firmware for PCA9686 using simpler protocol (`<channel> <angle>`).
- `robot_mech_testing/servo_direct_serial/servo_direct_serial.ino`
  - Arduino firmware for direct pin servo control (no PCA9686).
- `robot_mech_testing/i2c_scanner.ino`
  - PCA9686 I2C address discovery utility.
- `robot_mech_testing/README.md`
  - Setup instructions and protocol notes.

### 3.5 Diagnostics / Camera Utilities

- `src/vision/camera/test_camera_interactive.py`
  - Helps identify working camera index.
- `src/vision/camera/fpscheck.py`
  - Simple webcam FPS check script.

### 3.6 Model Artifacts

- `models/`
  - Current trained model artifact(s), e.g. `models/chess_piece_classifier_v7.h5`
- `models/archive/`
  - Older archived model versions (`v1`-`v6`)

### 3.7 Control Centre UI

- `apps/operator_control_centre.py`
  - PySide6 UI entrypoint for orchestrating vision/game/motion/robot flows.
- `src/ui/`
  - UI layout, panels, and rendering (vision panel, robot twin views, game/log panel).
- `src/orchestrator/`
  - Control-centre controller, events, and workers.

## 4. End-to-End Runtime Architecture (Current Main Path)

This describes the primary runtime flow implemented in `main_inference_spacebar.py`.

### 4.1 Startup

1. Load trained CNN model (`models/chess_piece_classifier_v7.h5`).
2. Open webcam (`cv2.VideoCapture(CAMERA_INDEX)`).
3. Initialize `python-chess` board state.
4. Launch Stockfish engine process via local path (`/usr/local/bin/stockfish`).
5. Wait for manual corner calibration.

### 4.2 Board Calibration and Normalization

1. User clicks 4 board corners in a required order (`A1`, `H1`, `H8`, `A8`).
2. Perspective transform matrix is computed.
3. Live frame is warped into a normalized square board image (`400x400`).
4. CLAHE contrast enhancement is applied to improve square classification robustness.
5. The warped board is split into an 8x8 grid via evenly spaced grid points.

This manual calibration step is the current alignment mechanism; there is no automatic board/corner detection in production flow yet.

### 4.3 Square Classification (Vision Inference)

1. User presses spacebar to trigger inference (`run_inference=True`).
2. Each square crop is resized to `64x64`.
3. Preprocessing creates a 5-channel tensor:
   - BGR (3 channels)
   - Canny edges (masked to ignore outer border)
   - Gradient magnitude (Sobel-based)
4. CNN predicts one of 3 classes per square:
   - `empty`
   - `black`
   - `white`
5. Predictions are stored in an `8x8` board-state matrix.

### 4.4 Move Detection and Game State Tracking

1. Current inferred board state is compared with the previous state.
2. A move is inferred by detecting:
   - one departure square (piece -> empty)
   - one arrival square (empty -> piece)
3. Board coordinates are mapped to UCI notation (e.g., `e2e4`), with optional board-flip handling.
4. `python-chess` validates and applies moves.

Current move differencing is a simple delta-based heuristic and may not cover complex cases like captures, castling, promotions, or en passant reliably.

### 4.5 Engine Integration (Black Move Suggestion)

1. After a valid White move is detected, Stockfish is queried (`engine.play(..., time=0.1)`).
2. Suggested Black move is printed and stored.
3. The system waits for a matching detected Black move on the physical board.
4. If detected move matches the suggested move, the chess game state advances.

This is currently a recommendation/verification loop only; no robot motion execution is performed.

## 5. ML/Data Pipeline Architecture

### 5.1 Dataset Generation Flow

1. `src/vision/labeling/capture/main_label.py` captures live board image from webcam.
2. User manually selects 4 corners.
3. Warped board is divided into 64 square crops.
4. User manually labels each square as:
   - `e` = empty
   - `b` = black piece
   - `w` = white piece
5. Images are saved into class folders.
6. Rotated augmentations are generated immediately (90/180/270 degrees).

### 5.2 Dataset Structure (Observed Conventions)

Typical folder conventions used in the repo:

- `chess_dataset/`
- `chess_dataset_v1/`

Class folders:

- `empty/`
- `black_piece/`
- `white_piece/`

File naming convention:

- `square_<row>_<col>_<index>.png`

### 5.3 Training Flow (`src/vision/training/modelTraining.py`)

1. Load labeled images from `chess_dataset_v1`.
2. Apply enhanced preprocessing (5-channel feature representation).
3. One-hot encode labels.
4. Train/validation split with stratification.
5. Compute class weights for imbalance handling.
6. Train CNN (Keras/TensorFlow).
7. Save trained model as `models/chess_piece_classifier_v7.h5`.

### 5.4 Model Versioning Reality

The repo shows iterative model/inference evolution (`v4`, `v6`, `v7`), with helper scripts documenting migration steps. Architecture-wise, preprocessing and inference code are tightly coupled to the selected model version.

## 6. Mechanical Control Architecture (Current Test Stack)

### 6.1 Python UI Layer (`robot_mech_testing/servo_slider_ui.py`)

- Tkinter desktop UI with controls for 5 joints:
  - base
  - shoulder
  - elbow
  - wrist
  - gripper
- Discovers serial ports using `pyserial`.
- Sends target angles over serial.
- Includes simple motion smoothing/ramping:
  - periodic tick loop (`UPDATE_MS`)
  - max step per tick
  - slowdown when close to target

This allows safer/manual servo testing and tuning before integrating autonomous commands.

### 6.2 Serial Protocols

There are multiple firmware protocols in the repo:

- `servo_slider_ui.py` sends: `PCA <channel> <angle>`
- `servo_mixed_serial.ino` expects: `PCA <channel> <angle>` (matches UI)
- `servo_pca9686_serial.ino` expects: `<channel> <angle>` (older simpler protocol)
- `servo_direct_serial.ino` expects: `<pin> <angle>` for direct Arduino servo output

### 6.3 Arduino / Actuation Layer

- Arduino receives serial commands.
- Parses channel/pin and angle.
- For PCA9686 variants:
  - uses `Adafruit_PWMServoDriver`
  - maps `0-180` degrees to PWM pulse range
  - writes PWM to the target channel
- For direct servo variant:
  - uses Arduino `Servo` library
  - attaches/detaches servo by pin as needed

## 7. External Dependencies and Interfaces

### 7.1 Python Libraries (Observed)

- `opencv-python` (`cv2`)
- `numpy`
- `tensorflow` / `keras`
- `scikit-learn`
- `python-chess`
- `pyserial`
- `tkinter` (stdlib)

### 7.2 Native / Local Runtime Dependencies

- Webcam device accessible via OpenCV camera index.
- Local Stockfish binary at `/usr/local/bin/stockfish` (hardcoded in runtime script).
- Arduino connected over serial.
- PCA9686 board (for servo test path).

## 8. Data and Control Flow Summary

### 8.1 Vision-to-Engine Flow (Implemented)

`Camera -> OpenCV Frame -> Perspective Warp -> 8x8 Square Crops -> CNN Classification -> Board State Matrix -> Move Detection -> python-chess Validation -> Stockfish Suggested Move`

### 8.2 Engine-to-Robot Flow (Implemented in Mock/Adapter Form)

Motion integration now exists in the codebase (mock-first) with this path:

`UCI Move -> Motion Planner -> MotionPlan (Cartesian waypoints) -> Robot Executor (IK + joint targets) -> Adapter -> Serial Commands`

The control-centre UI can orchestrate this path end-to-end with the mock robot adapter.

## 9. Architectural Strengths

- Clear separation of dataset generation, training, inference, and mech testing.
- Practical iterative model versioning approach.
- Manual calibration makes the system usable before automatic board localization is solved.
- `python-chess` + Stockfish integration provides legal move validation and engine feedback.
- Servo UI includes motion smoothing, which is useful for hardware safety/tuning.

## 10. Current Architectural Gaps / Risks

### 10.1 Integration Gap

- Vision/game runtime is not yet wired to robot execution (mock demo exists, runtime app still manual).

### 10.2 Board State Representation Limits

- Vision model classifies only `empty/black/white` (not piece types).
- Game state inference relies on differencing, not full piece identity tracking.
- Complex chess moves are likely under-handled.

### 10.3 Calibration and Robustness

- Manual corner selection required each session.
- Grid assumes ideal square board warp and equal cell spacing.
- Lighting and reflections still affect classification despite CLAHE and feature engineering.

### 10.4 Configuration Management

- Hardcoded paths (e.g., Stockfish binary path).
- Multiple script versions and protocol variants can drift.
- Model file names and preprocessing must stay synchronized manually.

## 11. Recommended Next Architecture Step (Pragmatic)

To evolve this into a fully integrated robot chess player, add a thin integration layer:

1. `game_controller.py`
   - Owns chess state, vision inference trigger, and engine interaction.
2. `motion_planner.py`
   - Converts UCI moves to board coordinates and pick/place sequences.
3. `robot_transport.py`
   - Encapsulates serial protocol (`PCA <channel> <angle>`) and reusable motion primitives.
4. `config.py` / YAML config
   - Camera index, model path, Stockfish path, serial port, calibration constants.

This preserves the current scripts as proven prototypes while introducing a production path.

## 12. Suggested File Purpose Grouping (Target State)

- `vision/`: board warp, preprocessing, classifier inference
- `ml/`: training, dataset tools
- `game/`: move detection, python-chess, Stockfish interface
- `robot/`: kinematics, serial transport, motion primitives
- `apps/`: interactive runtime (`play.py`), labeling UI, servo test UI

This is not how the repo is currently organized, but it aligns with the components already present.

## 13. Formal Project Objective

Build a modular, hardware-agnostic autonomous chess-playing system where the software stack can operate with different chessboards, cameras, and robot arms using configuration files and pluggable adapters rather than code rewrites.

## 14. Goals, Non-Goals, and Principles

### 14.1 Core Goals

1. Decouple software logic from hardware implementation.
2. Support multiple board/camera/robot setups through config-driven calibration.
3. Keep perception, game logic, motion planning, and actuation as separate modules.
4. Enable simulation/mock development without hardware connected.
5. Provide stable interfaces so new hardware can be added as adapters.

### 14.2 Non-Goals (Near Term)

1. Universal support for every robot arm/controller out of the box.
2. Zero-touch autonomous calibration for all setups.
3. Full industrial-grade safety/certification.
4. Perfect piece-type recognition in v1 if occupancy/color-based move detection is sufficient for early integration.

### 14.3 Architecture Principles

1. Separate `what to do` from `how to do it`.
2. Keep `src/` code-focused and place hardware/model assets behind config.
3. Prefer adapters at system boundaries and stable interfaces in the core.
4. Make runtime behavior configurable (camera index, paths, serial ports, calibration).
5. Support deterministic logging and replay-friendly debugging where possible.

### 14.4 Modular Boundary Intent (Target)

1. `Vision/Perception`
   - board localization/calibration
   - square inference
   - move observation
2. `Game Core`
   - chess rules/state (`python-chess`)
   - engine integration (Stockfish)
   - turn management/validation
3. `Task Planner`
   - convert chess moves into robot tasks (pick, capture, place, home)
4. `Motion Planner`
   - map board squares to robot poses/trajectories
5. `Robot Control`
   - hardware-agnostic robot interface and execution primitives
6. `Hardware Adapters`
   - camera, board, robot-specific implementations
7. `Config System`
   - board/camera/robot/calibration/runtime profiles

## 15. Success Criteria (v1 Modular Platform)

1. The same software core runs on at least two physical setups with config/adapter changes only.
2. End-to-end pipeline works: detect human move -> validate -> choose engine response -> execute robot response move.
3. Hardware can be tested independently from vision/game logic.
4. Core modules can run in mock/sim mode without camera or robot connected.
5. Runtime-critical paths (model path, Stockfish path, camera, serial, calibration) are not hardcoded in app scripts.

## 16. Phased Roadmap

### Phase 0: Foundation / Refactor

1. Define module interfaces for vision, game, planning, robot, and adapters.
2. Centralize configuration loading and path management.
3. Move hardcoded values (Stockfish path, camera index, model path, serial port) into config.
4. Add run modes (`vision-only`, `game-only`, `robot-test`, `full`) and basic logging.

### Phase 1: Core Software Decoupling

1. Extract current runtime script logic into reusable modules under `src/`.
2. Introduce `CameraInterface` and `RobotArmInterface`.
3. Build mock camera and mock robot adapters.
4. Run the game loop end-to-end in mock mode.

### Phase 2: Config-Driven Physical Setup

1. Define config schema for board geometry, camera setup, robot mapping/limits, and calibration transforms.
2. Implement per-setup profiles (e.g., different board/camera/arm combinations).
3. Add calibration save/load support so setups can be reused.

### Phase 3: Motion + Execution Pipeline

1. Define chess task model for `move`, `capture`, `castle`, and `promotion`.
2. Implement square-to-pose mapping and pick/place primitives.
3. Integrate robot execution through a robot adapter built on the existing servo test path.
4. Add safety constraints (workspace limits, speed limits, home pose, abort handling).

### Phase 4: Robust End-to-End Gameplay (Single Setup)

1. Improve move detection reliability for captures/castling/promotion edge cases.
2. Add post-execution verification (re-check board state after robot move).
3. Add error recovery flows (retry, pause, manual confirm).
4. Run complete autonomous games on one physical setup.

### Phase 5: Portability Validation (Multi-Setup)

1. Add and validate a second board/camera/robot profile.
2. Prove portability with config + adapter changes only (no core logic changes).
3. Document the adapter integration process for new hardware.
4. Freeze v1 modular architecture and interfaces.

### Milestones (Practical)

1. `M1`: Mock end-to-end game loop runs without hardware.
2. `M2`: Config-driven runtime loads and runs one physical setup.
3. `M3`: Robot executes reliable pick/place on board coordinates.
4. `M4`: Full autonomous response move after a human move.
5. `M5`: Same core software works on a second setup.

### Immediate Next Planning Step (Before Coding)

1. Define interface contracts (inputs/outputs) for `Camera`, `VisionPipeline`, `GameController`, `MotionPlanner`, and `RobotArm`.
2. Define config schema and setup profile format.
3. Refactor scripts against those interfaces incrementally.
