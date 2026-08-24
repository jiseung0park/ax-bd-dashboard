"""Shared path config for the pipeline scripts.

All intermediate/derived files (pledges_data.json, anchor_summary.json, ...)
live under OUTPUT_DIR and are regenerated on every pipeline run — nothing
there is meant to be hand-edited or committed as source.

Raw source files (엑셀/DB) live outside this project, in OneDrive, since
they contain PwC client data and are large. Override their location with
the DASHBOARD_RAW_DIR / DASHBOARD_DB_DIR env vars if the OneDrive path
ever changes.
"""
import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend"
INPUT_DIR = BACKEND_DIR / "inputs"
FONT_DIR = INPUT_DIR / "fonts"
OUTPUT_DIR = BACKEND_DIR / "output"
FRONTEND_DIR = REPO_ROOT / "frontend"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

RAW_DIR = Path(os.environ.get(
    "DASHBOARD_RAW_DIR",
    "/mnt/c/Users/jpark790/OneDrive - PwC/개인폴더/한글 saturn 개발/data/raw",
))
DB_DIR = Path(os.environ.get(
    "DASHBOARD_DB_DIR",
    "/mnt/c/Users/jpark790/OneDrive - PwC/개인폴더/한글 saturn 개발/db",
))
