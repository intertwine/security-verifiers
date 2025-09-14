"""Tool-grounded configuration auditing environment (E2).

This package wraps the :mod:`e2_config_auditing` module and exposes it as a
`verifiers` environment. Models receive raw Kubernetes or Terraform
configuration files, optionally call analysis tools, and must return a JSON
object with violations, an optional patch, and a confidence score.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any, Dict, List

import verifiers as vf
from datasets import Dataset

# Allow importing shared utilities when developing from the repo
import sys

sys.path.append(str(Path(__file__).resolve().parents[2]))
from sv_shared.utils import get_response_text  # type: ignore  # pylint: disable=wrong-import-position

from e2_config_auditing.adapters.kubelinter_adapter import kubelinter_lint
from e2_config_auditing.adapters.semgrep_adapter import semgrep_scan
from e2_config_auditing.adapters.types import Violation
from e2_config_auditing.mapping import normalize_findings
from e2_config_auditing.patching import try_apply_patch
from e2_config_auditing.reward import final_reward
from e2_config_auditing.schema import parse_model_output

DATASET_ROOT = Path(__file__).resolve().parents[2] / "e2_config_auditing" / "dataset"


def run_kubelinter(paths: List[str]) -> List[Dict[str, Any]]:
    """Expose ``kubelinter_lint`` as a simple tool."""

    return [f.__dict__ for f in kubelinter_lint(paths)]


def run_semgrep(paths: List[str]) -> List[Dict[str, Any]]:
    """Expose ``semgrep_scan`` as a simple tool."""

    return [f.__dict__ for f in semgrep_scan(paths)]


class ConfigVerificationParser(vf.Parser):
    """Parser validating the PRD JSON schema."""

    def parse_answer(self, completion: Any) -> Dict[str, Any]:
        text = get_response_text(completion)
        try:
            data = json.loads(text)
            violations, patch, confidence = parse_model_output(data)
        except Exception:  # pragma: no cover - defensive
            return {}
        return {
            "violations": [v.__dict__ for v in violations],
            "patch": patch or "",
            "confidence": confidence,
        }

    def get_format_reward_func(self):  # pragma: no cover - simple
        def format_reward(completion, answer="", **kwargs):  # pylint: disable=unused-argument
            text = get_response_text(completion)
            try:
                data = json.loads(text)
                parse_model_output(data)
            except Exception:
                return 0.0
            return 1.0

        return format_reward


def reward_config_auditing(
    completion,
    answer: Dict[str, Any] | None = None,
    **kwargs: Dict[str, Any],  # pylint: disable=unused-argument
) -> float:
    """Reward combining detection accuracy and patch verification."""

    text = get_response_text(completion)
    try:
        data = json.loads(text)
        violations_pred, patch, _ = parse_model_output(data)
    except Exception:
        return 0.0

    oracle_dicts = (answer or {}).get("oracle", [])
    oracle = [Violation(id=v["id"], severity=v["severity"]) for v in oracle_dicts]

    post: List[Violation] | None = None
    if patch:
        fixture_path = (answer or {}).get("fixture_path", "")
        fixture_type = (answer or {}).get("fixture_type", "k8s")
        applied, new_text = try_apply_patch(fixture_path, patch)
        if applied:
            with tempfile.NamedTemporaryFile("w", delete=False) as tmp:
                tmp.write(new_text)
                tmp_path = tmp.name
            if fixture_type == "k8s":
                post_findings = kubelinter_lint([tmp_path])
            else:
                post_findings = semgrep_scan([tmp_path])
            post = normalize_findings(post_findings)
            Path(tmp_path).unlink(missing_ok=True)

    return final_reward(violations_pred, oracle, post_patch=post)


def _load_examples(max_examples: int | None = None) -> List[Dict[str, Any]]:
    fixtures = [
        {
            "type": "k8s",
            "path": DATASET_ROOT / "fixtures" / "k8s" / "bad_pod.yaml",
            "oracle": DATASET_ROOT / "oracle" / "bad_pod.json",
        },
        {
            "type": "tf",
            "path": DATASET_ROOT / "fixtures" / "tf" / "bad.tf",
            "oracle": DATASET_ROOT / "oracle" / "bad_tf.json",
        },
    ]
    items: List[Dict[str, Any]] = []
    for item in fixtures[: max_examples if max_examples else None]:
        question = Path(item["path"]).read_text()
        oracle = json.loads(Path(item["oracle"]).read_text())
        answer = {
            "oracle": oracle,
            "fixture_path": str(item["path"]),
            "fixture_type": item["type"],
        }
        items.append({"question": question, "answer": answer})
    return items


def load_environment(
    dataset_name: str = "builtin",  # pylint: disable=unused-argument
    max_examples: int = 100,
) -> vf.ToolEnv:
    """Load the configuration auditing environment."""

    dataset = Dataset.from_list(_load_examples(max_examples))
    parser = ConfigVerificationParser()
    rubric = vf.Rubric(
        funcs=[reward_config_auditing, parser.get_format_reward_func()],
        weights=[1.0, 0.05],
    )
    return vf.ToolEnv(
        name="sv-env-config-verification",
        description=("Audit Kubernetes and Terraform configurations using pinned tool outputs."),
        dataset=dataset,
        parser=parser,
        rubric=rubric,
        tools=[run_kubelinter, run_semgrep],
        system_prompt=(
            "You audit Kubernetes/Terraform configs. Return JSON with keys 'violations', 'patch', and 'confidence'."
        ),
    )


__all__ = [
    "ConfigVerificationParser",
    "reward_config_auditing",
    "load_environment",
]
