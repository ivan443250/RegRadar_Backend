"""Runtime path configuration for replaceable local persistence."""

from __future__ import annotations

import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def storage_dir() -> Path:
    configured = os.getenv("REG_RADAR_STORAGE_DIR", "").strip()
    return Path(configured).expanduser() if configured else PROJECT_ROOT / "data" / "storage"


def log_dir() -> Path:
    configured = os.getenv("REG_RADAR_LOG_DIR", "").strip()
    return Path(configured).expanduser() if configured else PROJECT_ROOT / "data" / "logs"
