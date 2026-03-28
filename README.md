# RobotChessPlayer

Modular robot chess player project with:

- vision dataset labeling/training/testing tools
- web command centre with digital twin + robot controls
- web-based chessboard inference + Stockfish integration
- robot/servo mechanical test utilities (Arduino + PCA9686)

## Repo Structure (Current)

- `src/vision/` - vision system (camera tools, labeling, preprocessing, model builders, training, testing)
- `apps/web_control_centre.py` - web command-centre launcher
- `web_control_centre/` - React frontend for the command centre
- `src/web_control_centre/` - backend server for the command centre
- `robot_mech_testing/` - servo test UI + Arduino sketches
- `config/` - digital twin + physical setup profiles
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
- If `config/physical_setup_v1.json` exists, the backend will auto-attempt real robot serial connection on startup
- The backend serves the API at `http://127.0.0.1:8765`

Start the frontend in a second terminal:

```bash
cd web_control_centre
npm install
npm run dev
```

Then open the local Vite URL shown in the terminal.

### Current robot control stack

- Digital twin geometry profile: `config/digital_twin_setup_v1.json`
- Physical robot setup profile: `config/physical_setup_v1.json`
- Arduino firmware for the current pulse-driven robot path: `robot_mech_testing/full_robot_serial/full_robot_serial.ino`

Current web control behaviour:

- Joint sliders are angle-based in the UI
- Backend maps joint angles to calibrated pulses
- In `Virtual` mode, wrist is auto-leveled
- In `Real Robot` mode, wrist remains manual
- `Home` / `Save Home` work for the current backend session
- `Actual pulse` in the UI is read back from the Arduino controller via serial `STATUS_JSON`

## Hardware / Servo Testing (Optional, Separate)

The mechanical test stack is still useful for direct calibration and firmware testing.

- Arduino sketches: `robot_mech_testing/`
- Servo desktop UI: `robot_mech_testing/servo_slider_ui.py`
- Full robot raw-pulse tester: `robot_mech_testing/full_robot_test_run.py`

Typical flow:

1. Upload the appropriate Arduino sketch.
2. Connect Arduino and servos.
3. For direct angle-based PCA testing, run:

```bash
python robot_mech_testing/servo_slider_ui.py
```

4. For the current full robot raw-pulse workflow, use:

```bash
python robot_mech_testing/full_robot_test_run.py
```

You may need the Adafruit PCA9686 library in Arduino IDE for PCA-based sketches.

Current firmware / protocol notes:

- `robot_mech_testing/servo_slider_ui.py` expects `PCA <channel> <angle>`
- `robot_mech_testing/full_robot_serial/full_robot_serial.ino` expects `<channel>,<pulse>`
- The web command centre currently uses the `full_robot_serial` pulse protocol via `config/physical_setup_v1.json`

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
