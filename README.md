# RobotChessPlayer

Modular robot chess player project with:

- vision dataset labeling/training/testing tools
- web-based chessboard inference + Stockfish integration
- robot/servo mechanical test utilities (Arduino + PCA9686)

## Repo Structure (Current)

- `src/vision/` - vision system (camera tools, labeling, preprocessing, model builders, training, testing)
- `apps/web_control_centre.py` - web command-centre launcher
- `web_control_centre/` - React frontend for the command centre
- `src/web_control_centre/` - backend server for the command centre
- `robot_mech_testing/` - servo test UI + Arduino sketches
- `models/` - trained model artifacts (`.h5`)
- `systemarchitecture.md` - system architecture, objectives, and roadmap

## Quick Start (Recommended)

Run all commands from the repo root.

Note: scripts inside `src/` should be run as Python modules (`python -m ...`) so package imports like `from src.vision...` resolve correctly.

### 1. Create and activate a virtual environment

macOS/Linux:

```bash
python3.10 -m venv tf_env
source tf_env/bin/activate
```

Use Python `3.10` to `3.12` for the TensorFlow training stack. On Intel macOS, this repo targets a pinned TensorFlow-compatible environment from `requirements.txt`.

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

Expected ML stack:

- `tensorflow==2.16.1`
- `numpy<2`

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

### Camera setup/testing tools

```bash
python -m src.vision.camera.test_camera_interactive
python -m src.vision.camera.fpscheck
```

### Run the web command centre

```bash
python apps/web_control_centre.py
```

Notes:

- Requires a trained model at `models/chess_piece_classifier_v7.h5`
- Requires Stockfish installed locally (current runtime script uses `/usr/local/bin/stockfish`)
- Requires a webcam and manual board corner selection

Start the frontend in a second terminal:

```bash
cd web_control_centre
npm install
npm run dev
```

Then open the local Vite URL shown in the terminal.

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
