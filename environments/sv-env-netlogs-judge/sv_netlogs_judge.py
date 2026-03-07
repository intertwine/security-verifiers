"""Short-name wrapper for the network logs judge environment.

Prime RL currently truncates environment names to 20 characters when deriving
Kubernetes labels. The original judge env id (`sv-env-network-logs-judge`)
truncates to `sv-env-network-logs-`, which is invalid because it ends with a
hyphen. This wrapper exposes a shorter stable module/env id that avoids the
label bug while reusing the same judge environment implementation.
"""

from __future__ import annotations

from sv_netlogs_judge_impl import load_environment as _load_environment

SHORT_ENV_ID = "sv-netlogs-judge"


def load_environment(**kwargs):
    """Load the short-name alias of the E1 judge environment."""
    kwargs.setdefault("env_name", SHORT_ENV_ID)
    return _load_environment(**kwargs)
