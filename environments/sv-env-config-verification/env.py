"""Minimal gym-style environment for config auditing."""

from __future__ import annotations

import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

from adapters.kubelinter_adapter import kubelinter_lint
from adapters.semgrep_adapter import semgrep_scan
from adapters.types import Violation
from mapping import normalize_findings
from oracle import build_oracle_for_k8s, build_oracle_for_tf
from patching import try_apply_patch
from reward import final_reward
from schema import parse_model_output


@dataclass
class ConfigAuditingEnv:
    """Minimal gym-style environment for config auditing."""

    fixture_path: str
    fixture_type: str  # "k8s" or "tf"

    def __post_init__(self) -> None:
        if self.fixture_type == "k8s":
            self.oracle = build_oracle_for_k8s([self.fixture_path])
        else:
            self.oracle = build_oracle_for_tf([self.fixture_path])

    def reset(self) -> Dict[str, Any]:  # pragma: no cover - simple
        """Reset the environment."""
        return {"fixture": self.fixture_path}

    def step(self, model_json: Dict[str, Any]) -> Dict[str, Any]:
        """Step the environment."""
        violations_pred, patch, _confidence = parse_model_output(model_json)
        post: List[Violation] | None = None
        if patch:
            applied, new_text = try_apply_patch(self.fixture_path, patch)
            if applied:
                with tempfile.NamedTemporaryFile("w", delete=False) as tmp:
                    tmp.write(new_text)
                    tmp_path = tmp.name
                if self.fixture_type == "k8s":
                    post_findings = kubelinter_lint([tmp_path])
                else:
                    post_findings = semgrep_scan([tmp_path])
                post = normalize_findings(post_findings)
                Path(tmp_path).unlink(missing_ok=True)
        reward = final_reward(violations_pred, self._oracle_violations(), post_patch=post)
        return {
            "reward": reward,
            "done": True,
            "info": {"oracle": self.oracle, "post": [v.__dict__ for v in (post or [])]},
        }

    def _oracle_violations(self) -> List[Violation]:
        return [Violation(id=v["id"], severity=v["severity"]) for v in self.oracle]


__all__ = ["ConfigAuditingEnv"]
