"""Pytest configuration for ensuring local packages take precedence."""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure the repository root is first on sys.path so imports use local sources
ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

