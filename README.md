# RobotChessPlayer

Modular robot chess player project with:

- vision dataset labeling/training/testing tools
- runtime chessboard inference + Stockfish integration
- robot/servo mechanical test utilities (Arduino + PCA9686)

## Repo Structure (Current)

- `src/vision/` - vision system (camera tools, labeling, preprocessing, model builders, training, testing)
- `apps/runtime/` - interactive runtime apps
- `apps/labeling/` - thin app entrypoint for labeling workflow
- `robot_mech_testing/` - servo test UI + Arduino sketches
- `models/` - trained model artifacts (`.h5`)
- `systemarchitecture.md` - system architecture, objectives, and roadmap

## Quick Start (Recommended)

Run all commands from the repo root.

Note: scripts inside `src/` should be run as Python modules (`python -m ...`) so package imports like `from src.vision...` resolve correctly.

### 1. Create and activate a virtual environment

macOS/Linux:

```bash
python3 -m venv tf_env
source tf_env/bin/activate
```

### 2. Install Python dependencies

Always install using the active environment's interpreter:

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

If `python3` points to a different interpreter on your machine, prefer `python` after activation.

### 3. Verify the environment

```bash
python -c "import tensorflow, cv2, numpy, chess, serial; print('OK')"
```

## Common Workflows

### Train a model (default: `enhanced_v7`)

```bash
python -m src.vision.training.modelTraining
```

Train a different variant:

```bash
python -m src.vision.training.modelTraining --variant baseline
```

### Evaluate a trained model (without running full app)

```bash
python -m src.vision.testing.evaluate_model
```

Example with explicit model + variant:

```bash
python -m src.vision.testing.evaluate_model \
  --variant enhanced_v7 \
  --model models/chess_piece_classifier_v7.h5
```

### Label dataset squares (interactive)

```bash
python apps/labeling/main_label.py
```

### Camera setup/testing tools

```bash
python -m src.vision.camera.test_camera_interactive
python -m src.vision.camera.fpscheck
```

### Run runtime inference app (vision + chess logic)

```bash
python -m apps.runtime.main_inference_spacebar
```

Notes:

- Requires a trained model at `models/chess_piece_classifier_v7.h5`
- Requires Stockfish installed locally (current runtime script uses `/usr/local/bin/stockfish`)
- Requires a webcam and manual board corner selection

### Mock motion/robot integration demo (no hardware)

```bash
python -m apps.runtime.mock_robot_move_demo --uci e2e4
```

Uses `config/physical_setup.example.json` for board geometry, kinematics, and mock execution.

### Control Centre UI (PySide6)

```bash
python -m apps.operator_control_centre
```

This launches the tiled control-centre UI with camera feed, robot twin views, and game/log panel.

## Hardware / Servo Testing (Optional, Separate)

The mechanical test stack is intentionally separate from the vision/runtime app while the project is being modularized.

- Arduino sketches: `robot_mech_testing/`
- Servo desktop UI: `robot_mech_testing/servo_slider_ui.py`

Typical flow:

1. Upload the appropriate Arduino sketch (e.g. PCA9686 serial controller).
2. Connect Arduino and servos.
3. Run:

```bash
python robot_mech_testing/servo_slider_ui.py
```

You may need the Adafruit PCA9686 library in Arduino IDE for PCA-based sketches.

## Troubleshooting

### `ModuleNotFoundError: No module named 'tensorflow'`

This usually means the script is not using your virtual environment interpreter.

Use:

```bash
which python
python -m pip install -r requirements.txt
python -m src.vision.testing.evaluate_model
```

Or explicitly:

```bash
./tf_env/bin/python -m src.vision.testing.evaluate_model
```

## Next Docs

- `systemarchitecture.md` - architecture + roadmap
- `robot_mech_testing/README.md` - hardware test setup details
