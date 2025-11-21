"""Pytest configuration for ensuring local packages take precedence."""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure the repository root is first on sys.path so imports use local sources
ROOT_DIR = Path(__file__).resolve().parent
root_str = str(ROOT_DIR)

if root_str in sys.path:
    sys.path.remove(root_str)

sys.path.insert(0, root_str)

