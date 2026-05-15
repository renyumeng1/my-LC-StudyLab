"""Development server entrypoints for the backend package."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import uvicorn


def dev() -> None:
    """Run the FastAPI app with uvicorn for local development."""
    project_root = Path(__file__).resolve().parents[1]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    parser = argparse.ArgumentParser(description="Run the backend API server.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8000, type=int)
    parser.add_argument("--reload", action=argparse.BooleanOptionalAction, default=True)
    args = parser.parse_args()

    uvicorn.run("backend.api.app:app", host=args.host, port=args.port, reload=args.reload)


if __name__ == "__main__":
    dev()
