"""Tests for Weave auto-initialization module."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add parent directory to path so we can import sv_shared
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


def test_weave_init_enabled_by_default(monkeypatch):
    """Weave should be initialized by default when available."""
    # Clear any existing initialization state
    monkeypatch.setattr("sv_shared.weave_init._INITIALIZED", False)

    # Mock weave module
    mock_weave = MagicMock()
    with patch.dict("sys.modules", {"weave": mock_weave}):
        # Re-import to trigger initialization
        from sv_shared.weave_init import initialize_weave_if_enabled

        result = initialize_weave_if_enabled()

        assert result is True
        mock_weave.init.assert_called_once_with("security-verifiers")


def test_weave_init_disabled_via_env(monkeypatch):
    """Weave initialization can be disabled via WEAVE_DISABLED env var."""
    monkeypatch.setattr("sv_shared.weave_init._INITIALIZED", False)
    monkeypatch.setenv("WEAVE_DISABLED", "true")

    mock_weave = MagicMock()
    with patch.dict("sys.modules", {"weave": mock_weave}):
        from sv_shared.weave_init import initialize_weave_if_enabled

        result = initialize_weave_if_enabled()

        assert result is False
        mock_weave.init.assert_not_called()


def test_weave_auto_init_can_be_disabled(monkeypatch):
    """Auto-initialization can be disabled via WEAVE_AUTO_INIT env var."""
    monkeypatch.setattr("sv_shared.weave_init._INITIALIZED", False)
    monkeypatch.setenv("WEAVE_AUTO_INIT", "false")

    mock_weave = MagicMock()
    with patch.dict("sys.modules", {"weave": mock_weave}):
        from sv_shared.weave_init import initialize_weave_if_enabled

        result = initialize_weave_if_enabled()

        assert result is False
        mock_weave.init.assert_not_called()


def test_weave_project_name_from_env(monkeypatch):
    """Weave project name can be configured via WEAVE_PROJECT env var."""
    monkeypatch.setattr("sv_shared.weave_init._INITIALIZED", False)
    monkeypatch.setenv("WEAVE_PROJECT", "custom-project")

    mock_weave = MagicMock()
    with patch.dict("sys.modules", {"weave": mock_weave}):
        from sv_shared.weave_init import initialize_weave_if_enabled

        result = initialize_weave_if_enabled()

        assert result is True
        mock_weave.init.assert_called_once_with("custom-project")


def test_weave_init_handles_missing_weave(monkeypatch):
    """Initialization gracefully handles missing Weave package."""
    monkeypatch.setattr("sv_shared.weave_init._INITIALIZED", False)

    # Simulate ImportError when trying to import weave
    with patch("sv_shared.weave_init.initialize_weave_if_enabled") as mock_init:
        mock_init.return_value = False

        from sv_shared.weave_init import initialize_weave_if_enabled

        result = initialize_weave_if_enabled()

        assert result is False


def test_weave_init_is_idempotent(monkeypatch):
    """Multiple calls to initialize should only initialize once."""
    monkeypatch.setattr("sv_shared.weave_init._INITIALIZED", False)

    mock_weave = MagicMock()
    with patch.dict("sys.modules", {"weave": mock_weave}):
        from sv_shared.weave_init import initialize_weave_if_enabled

        # First call
        result1 = initialize_weave_if_enabled()
        assert result1 is True

        # Second call should return True but not re-initialize
        result2 = initialize_weave_if_enabled()
        assert result2 is True

        # Weave.init should only be called once
        assert mock_weave.init.call_count == 1


def test_weave_init_handles_initialization_errors(monkeypatch):
    """Initialization handles errors gracefully."""
    monkeypatch.setattr("sv_shared.weave_init._INITIALIZED", False)

    mock_weave = MagicMock()
    mock_weave.init.side_effect = Exception("Connection error")

    with patch.dict("sys.modules", {"weave": mock_weave}):
        from sv_shared.weave_init import initialize_weave_if_enabled

        result = initialize_weave_if_enabled()

        assert result is False
