# Web Control Centre

React + TypeScript frontend for the robot command-centre UI.

## Run

1. Start the Python backend API:

```bash
python3 apps/web_control_centre.py
```

2. In a separate terminal, start the React dev server:

```bash
cd web_control_centre
npm install
npm run dev
```

The Vite dev server proxies `/api/*` requests to `http://127.0.0.1:8765`.

## Notes

- The board preview starts in the standard chess opening layout until all four live board corners are selected.
- After the corners are locked, the board preview switches to a live warped feed from `src/web_control_centre/server.py`.
- The `Robot Kinematics` tile is a placeholder for a future real 3D robot view.
- The intended next upgrade is React Three Fiber or Three.js once the arm geometry config is stable.
