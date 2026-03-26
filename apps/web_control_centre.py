"""Launch the lightweight web command-centre app."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.web_control_centre.server import HOST, PORT, run_server


def main() -> None:
    parser = argparse.ArgumentParser(description="Launch the lightweight web command-centre app.")
    parser.add_argument("--host", default=None, help="Host/interface to bind. Defaults to WEB_CONTROL_CENTRE_HOST or 127.0.0.1.")
    parser.add_argument("--port", type=int, default=None, help="Port to bind. Defaults to WEB_CONTROL_CENTRE_PORT or 8765.")
    args = parser.parse_args()
    run_server(
        host=args.host if args.host is not None else HOST,
        port=args.port if args.port is not None else PORT,
    )


if __name__ == "__main__":
    main()
