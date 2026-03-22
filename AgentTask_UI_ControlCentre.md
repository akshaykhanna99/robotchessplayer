# Agent Task: PySide6 Control Centre UI (Full-System Orchestrator)

## Objective

Implement a desktop control-centre UI using **PySide6 / PyQt** that becomes the primary operator interface for the RobotChessPlayer system.

This UI is not only a visualizer; it is the **main orchestration entrypoint** for running the full system:

- vision (camera + board calibration + board-state inference)
- game (move detection + validation + engine suggestions)
- motion (UCI -> motion planning)
- robot (mock and later real execution)

The UI must show all 3 major systems simultaneously in a tile-based layout:

- **Left:** live camera / vision panel
- **Middle:** robot digital twin (top view + side view)
- **Right:** game/chess logs + status

## Design Constraints

1. **Use PySide6 (or PyQt6 if PySide6 unavailable)**
- Prefer `PySide6`
- Do not implement a web UI in this task

2. **UI is the operator control centre**
- Starting/stopping the system and triggering actions should happen through UI controls
- Avoid a separate hidden main loop controlling everything outside the UI

3. **Backend logic stays modular**
- UI should orchestrate via controllers/services
- UI should not directly contain chess logic or robot protocol logic

4. **Mock-first but real integration-ready**
- Must run with a mock robot adapter
- Should be architected to swap in real robot adapter later

5. **Non-destructive**
- Keep existing scripts functional (`apps/runtime/main_inference_spacebar.py` etc.)
- Add new UI path in parallel

## Required UI Layout (Tile-Based)

## Main Layout

Use nested splitters:

- **Horizontal splitter (3 columns)**
  1. `VisionPanel` (left, largest)
  2. `RobotPanelContainer` (middle)
  3. `GamePanel` (right)

- **Vertical splitter inside middle column**
  - Top: `RobotTopViewPanel`
  - Bottom: `RobotSideViewPanel`

Initial splitter sizing target:
- Left: 50%
- Middle: 30%
- Right: 20%

## Panel Requirements

### 1. Vision Panel (Left)

Must include:
- live camera feed display
- corner selection interaction (4 clicks)
- grid overlay rendering
- square-state overlay rendering (`empty/black/white`)
- status text (camera connected, corners selected, grid locked)

Should support:
- raw feed display
- warped board display (either toggle or secondary subview)
- manual reset corners action

### 2. Robot Digital Twin Panel (Middle)

Split into two persistent views:

- **Top View (XY)**
  - board footprint
  - robot base location
  - planned waypoints/path
  - current end-effector position
  - target square highlight

- **Side View (XZ or radial-Z)**
  - height profile of arm movement
  - approach/lift/place phases
  - active waypoint visualization

Must be able to animate:
- mock motion plan execution
- segment/waypoint progression
- gripper open/close state

### 3. Game Panel (Right)

Must include:
- chess/game status summary
  - side to move
  - last detected move
  - suggested engine move
  - current mode (vision-only/mock/full)
- event log stream (timestamped)

Nice to have:
- FEN display
- move list
- mini chessboard widget (optional, not required in first pass)

## Control Centre Behavior (Orchestration)

The UI is the launch/control surface for the system. It should provide controls for:

- Start camera
- Stop camera
- Reset corners
- Run inference (manual trigger, current spacebar equivalent)
- Enable/disable mock robot execution
- Load physical setup config
- Optional: Start full pipeline mode

### System Flow (UI-driven)

User flow in v1 UI:
1. Launch UI
2. Load setup config
3. Start camera
4. Select 4 board corners in Vision panel
5. Press "Run Inference" (manual trigger)
6. Vision produces board state
7. Game subsystem detects/applies move + suggests response
8. Motion planner creates motion plan for suggested move
9. Mock robot executes plan
10. Robot top/side views animate execution
11. Logs and statuses update live

The UI should orchestrate this sequence by invoking backend controllers/services, not by embedding the logic in widget code.

## Architecture (Recommended)

## New App Entry Point

Create:
- `apps/operator_control_centre.py`

This starts the Qt app and main window.

## UI Package (Recommended)

Create:
- `src/ui/`
- `src/ui/main_window.py`
- `src/ui/panels/vision_panel.py`
- `src/ui/panels/game_panel.py`
- `src/ui/panels/robot_top_view_panel.py`
- `src/ui/panels/robot_side_view_panel.py`
- `src/ui/widgets/...` (optional)

## Orchestrator / Controller Layer

Create UI-facing orchestration/controller code (can live under `src/orchestrator/`):

- `src/orchestrator/control_centre_controller.py`
  - coordinates vision, game, motion, robot services
  - exposes high-level actions called by UI (start_camera, reset_corners, run_inference, etc.)
  - emits state/events for UI rendering

- `src/orchestrator/events.py`
  - structured event types / dataclasses (vision/game/motion/robot)

- `src/orchestrator/state.py`
  - optional central state snapshot model used by UI

## Threading / Concurrency Requirements

Do **not** block the UI thread with camera capture, inference, or robot execution.

Use Qt threading patterns:
- `QObject` workers moved to `QThread`
- signals/slots for communication

Likely workers:
- `VisionWorker`
- `RobotExecutionWorker` (mock/real)

Game/motion logic may run in main thread initially if lightweight, but prefer consistency via controller/event pipeline.

## Integration Requirements (Backend Modules)

Wire into existing modules where possible:

- Vision:
  - use existing preprocessing + inference model loading logic
  - reuse board calibration/grid logic (or refactor into reusable vision module if needed)
- Game:
  - `src/game/session.py`
  - `src/game/engine.py`
  - `src/game/move_detection.py`
- Motion:
  - `src/motion/planner.py`
- Robot:
  - mock adapter (from robot integration work)
  - real adapter later

If current runtime logic is too entangled, refactor minimally to create reusable services instead of copying logic into UI.

## Rendering / Visualization Requirements

## Vision Rendering

Implement OpenCV frame -> Qt image conversion:
- BGR numpy array -> RGB -> `QImage` -> `QPixmap`

Overlays may be rendered using:
- Qt `QPainter` (preferred for UI ownership of visuals)
or
- existing OpenCV draw calls initially (acceptable for v1)

## Robot Twin Rendering

Use custom `QWidget.paintEvent()` + `QPainter` for both top and side views.

Must render:
- board rectangle/grid reference
- robot link/joint visualization (even if simplified)
- planned path/waypoints
- current executed position
- current segment/waypoint highlight

Start with 2D projections only (top + side). Do not build full 3D engine in this task.

## Event / Logging Model

Replace or wrap `print()` style runtime messages into structured events for the UI.

Minimum event categories:
- `vision`
- `game`
- `motion`
- `robot`
- `system`
- `error`

Game panel log should display timestamps and category labels.

## Modes (Required)

Provide a mode selector in UI (or config) with at least:

1. `Vision Only`
2. `Vision + Game`
3. `Vision + Game + Mock Robot`
4. `Full System` (hook for real robot, can be disabled if adapter not ready)

## Configuration

UI should be able to load/select a physical setup config:
- from `config/physical_setup.example.json` or a user-specified JSON file

Expose loaded setup info in the UI status area:
- setup name
- robot type
- serial port (if configured)
- square size / board mapping summary

## Phased Delivery (Implement in This Task)

### Phase UI-1 (Required)
- PySide6 app entrypoint and tiled layout
- Vision panel placeholder
- Robot top/side placeholders
- Game log panel
- Control toolbar/buttons

### Phase UI-2 (Required)
- Live camera feed in Vision panel
- Corner click capture in UI
- Grid overlay rendering
- Manual "Run Inference" action wired to current vision inference flow

### Phase UI-3 (Required)
- Integrate `src/game/*` for move processing and engine suggestion
- Game panel status + logs updated from real events

### Phase UI-4 (Required)
- Integrate `src/motion/*` and mock robot adapter
- Render planned and executing motion in robot top/side views
- Animate segment/waypoint progression

### Phase UI-5 (Stretch / Optional if time)
- Hook in real robot adapter execution status
- Pause/Stop/Home controls
- Config file picker dialog

## Deliverables

1. New PySide6 UI app that launches and displays all 3 system tiles simultaneously
2. UI-driven orchestration path for manual inference -> game update -> motion plan -> mock robot execution
3. Robot digital twin top/side visualization for planned/executing motion
4. Structured logging in the Game panel
5. Documentation for running the control centre

## Acceptance Criteria

1. Launching the UI shows:
- left vision tile
- middle top/side robot tiles
- right game/log tile

2. User can:
- start camera
- click 4 corners in the vision tile
- trigger inference from UI

3. After a detected move:
- game subsystem processes it
- engine suggestion appears in logs/status
- motion plan is generated
- mock robot execution animates in robot tiles

4. UI remains responsive during camera feed and mock execution (no blocking main thread)

5. Existing non-UI scripts remain runnable

## Implementation Notes / Guidance

- Prefer `PySide6`
- If using `PyQt6`, keep code compatible where practical
- Use clean widget classes and signals/slots (avoid one giant file)
- Do not overbuild styling initially; focus on correct behavior and observability
- Keep rendering functional and clear; polish can come later

## Suggested Kickoff Sequence for Codex CLI

1. Read:
- `systemarchitecture.md`
- `src/game/*`
- `src/motion/*`
- `src/robot/*`
- `apps/runtime/main_inference_spacebar.py`

2. Implement:
- UI shell + tiled layout + placeholders
- orchestrator/controller + event model
- camera panel integration
- game/motion/mock-robot wiring
- robot twin drawing/animation

3. Validate:
- app launches
- camera feed renders
- no UI thread blocking
- mock end-to-end flow works

