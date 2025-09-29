"""Weave auto-initialization for Security Verifiers environments.

This module provides automatic Weave initialization for the Verifiers library.
When Weave is initialized BEFORE importing verifiers, it automatically patches
the library to provide comprehensive tracing of all operations.

Usage:
    Import this module before importing verifiers in any environment or script:

    ```python
    from sv_shared import weave_init  # noqa: F401
    import verifiers as vf
    ```

Configuration:
    Set environment variables to control Weave initialization:

    - WEAVE_AUTO_INIT: Set to "true" to enable automatic Weave initialization (default: "true")
    - WEAVE_PROJECT: Set the Weave project name (default: "security-verifiers")
    - WEAVE_DISABLED: Set to "true" to completely disable Weave (overrides WEAVE_AUTO_INIT)

Notes:
    - This module must be imported BEFORE importing verifiers for auto-patching to work
    - The RolloutLogger remains available as a supplementary logging mechanism
    - Weave initialization is idempotent - multiple imports won't reinitialize
"""

from __future__ import annotations

import logging
import os

_LOGGER = logging.getLogger(__name__)
_INITIALIZED = False


def initialize_weave_if_enabled() -> bool:
    """Initialize Weave if enabled via environment configuration.

    Returns:
        True if Weave was successfully initialized, False otherwise.
    """
    global _INITIALIZED

    # Check if already initialized
    if _INITIALIZED:
        return True

    # Check if Weave is disabled
    if os.environ.get("WEAVE_DISABLED", "false").lower() == "true":
        _LOGGER.debug("Weave is disabled via WEAVE_DISABLED environment variable")
        return False

    # Check if auto-init is enabled (default: true)
    auto_init = os.environ.get("WEAVE_AUTO_INIT", "true").lower() == "true"
    if not auto_init:
        _LOGGER.debug("Weave auto-initialization is disabled via WEAVE_AUTO_INIT")
        return False

    try:
        import weave

        # Get project name from environment or use default
        project_name = os.environ.get("WEAVE_PROJECT", "security-verifiers")

        # Initialize Weave
        weave.init(project_name)
        _INITIALIZED = True
        _LOGGER.info(f"Weave initialized for project: {project_name}")
        return True

    except ImportError:
        _LOGGER.debug("Weave is not installed; automatic tracing will be skipped")
        return False
    except Exception as e:
        _LOGGER.warning(f"Failed to initialize Weave: {e}")
        return False


# Automatically initialize when module is imported
initialize_weave_if_enabled()


__all__ = ["initialize_weave_if_enabled"]
