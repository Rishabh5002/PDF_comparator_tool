"""Local server runner for the FormDiff FastAPI application."""
from __future__ import annotations

import uvicorn


def run(host: str = "127.0.0.1", port: int = 8000):
    print(f"FormDiff API & Web App running at http://{host}:{port}")
    print("Local-only server: binds to 127.0.0.1 and uses no cloud AI API.")
    uvicorn.run("backend.app:app", host=host, port=port, log_level="info")


if __name__ == "__main__":
    run()
