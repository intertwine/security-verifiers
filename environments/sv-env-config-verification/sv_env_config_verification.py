"""Tool-grounded configuration auditing environment (E2).

This module provides a `verifiers` environment for security configuration auditing.
Models receive raw Kubernetes or Terraform configuration files, optionally call
analysis tools (KubeLinter, Semgrep, OPA), and must return a JSON object with
violations, an optional patch, and a confidence score.
"""

from __future__ import annotations

import json
import ast

# Allow importing shared utilities when developing from the repo
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

# Ensure repository root is on sys.path so `sv_shared` is importable when running from source
# __file__ .../environments/sv-env-config-verification/sv_env_config_verification.py
# parents[2] points to the repository root
sys.path.append(str(Path(__file__).resolve().parents[2]))

# Initialize Weave before importing verifiers for automatic tracing
from sv_shared import weave_init  # type: ignore  # noqa: F401, E402

import verifiers as vf
import yaml  # noqa: F401 - used in run_opa function
from datasets import Dataset
from openai import APIError, APITimeoutError, RateLimitError
from pydantic import BaseModel, ConfigDict
from verifiers.utils.async_utils import maybe_await

from sv_shared import (  # type: ignore  # pylint: disable=wrong-import-position
    DatasetSource,
    RolloutLogger,
    extract_json_from_markdown,
    get_response_text,
    load_dataset_with_fallback,
)

# pylint: disable=wrong-import-position
from adapters.kubelinter_adapter import kubelinter_lint
from adapters.opa_adapter import opa_eval
from adapters.semgrep_adapter import semgrep_scan
from adapters.types import Violation
from mapping import normalize_findings
from patching import try_apply_patch
from reward import final_reward
from schema import parse_model_output


# Pydantic model for tool finding dictionaries
class ToolFindingModel(BaseModel):
    """Pydantic model for tool finding dictionaries."""

    tool: Literal["opa", "kube-linter", "semgrep"]
    rule_id: str
    severity: str
    message: str
    file: Optional[str] = None
    start_line: Optional[int] = None
    end_line: Optional[int] = None

    model_config = ConfigDict(extra="forbid")


DATASET_ROOT = Path(__file__).resolve().parent / "dataset"

JUDGE_PROMPT = """\
You are evaluating a security configuration auditing model's response.

The model was given a Kubernetes or Terraform configuration and asked to return JSON:
{{"violations": [...], "patch": "...", "confidence": 0.0-1.0}}.

Configuration:
```
{question}
```

Ground truth audit metadata:
```
{answer}
```

Model's parsed response:
```
{response}
```

Respond "yes" if the response identifies the relevant security violations, is valid JSON,
and does not invent unsupported findings. Respond "no" otherwise.\
"""


def run_kubelinter(paths: List[str]) -> List[Dict[str, Any]]:
    """Expose ``kubelinter_lint`` as a simple tool."""

    findings = []
    tool_backend = "adapter"
    try:
        raw_findings = kubelinter_lint(paths)
    except Exception:
        tool_backend = "deterministic_fallback"
        raw_findings = []
        for path in paths:
            try:
                content = Path(path).read_text(encoding="utf-8")
            except OSError:
                continue
            if ":latest" in content:
                raw_findings.append(
                    ToolFindingModel(
                        tool="kube-linter",
                        rule_id="latest-tag",
                        severity="med",
                        message="Container image uses the latest tag.",
                        file=path,
                    )
                )
            if "runAsNonRoot: false" in content:
                raw_findings.append(
                    ToolFindingModel(
                        tool="kube-linter",
                        rule_id="run-as-non-root",
                        severity="med",
                        message="Container explicitly disables runAsNonRoot.",
                        file=path,
                    )
                )

    for f in raw_findings:
        # Create dict without extra field to avoid schema issues
        finding_dict = {
            "tool": f.tool,
            "rule_id": f.rule_id,
            "severity": f.severity,
            "message": f.message,
            "file": f.file,
            "start_line": f.start_line,
            "end_line": f.end_line,
            "tool_backend": tool_backend,
        }
        findings.append(finding_dict)
    return findings


def run_semgrep(paths: List[str]) -> List[Dict[str, Any]]:
    """Expose ``semgrep_scan`` as a simple tool."""

    findings: list[dict[str, Any]] = []

    by_ruleset: dict[str, list[str]] = {"p/kubernetes": [], "p/terraform": []}
    for path in paths:
        ruleset = "p/terraform" if path.endswith(".tf") else "p/kubernetes"
        by_ruleset[ruleset].append(path)

    for ruleset, grouped_paths in by_ruleset.items():
        if not grouped_paths:
            continue
        tool_backend = "adapter"
        try:
            raw_findings = semgrep_scan(grouped_paths, rules=ruleset)
        except Exception:
            tool_backend = "deterministic_fallback"
            raw_findings = []
            if ruleset == "p/terraform":
                for path in grouped_paths:
                    try:
                        content = Path(path).read_text(encoding="utf-8")
                    except OSError:
                        continue
                    if 'acl    = "public-read"' in content or 'acl = "public-read"' in content:
                        raw_findings.append(
                            ToolFindingModel(
                                tool="semgrep",
                                rule_id="terraform-acl-public-read",
                                severity="high",
                                message="S3 bucket ACL is public-read.",
                                file=path,
                            )
                        )
        for f in raw_findings:
            # Create dict without extra field to avoid schema issues
            finding_dict = {
                "tool": f.tool,
                "rule_id": f.rule_id,
                "severity": f.severity,
                "message": f.message,
                "file": f.file,
                "start_line": f.start_line,
                "end_line": f.end_line,
                "tool_backend": tool_backend,
            }
            findings.append(finding_dict)
    return findings


def run_opa(paths: List[str]) -> List[Dict[str, Any]]:
    """Expose ``opa_eval`` as a simple tool for configuration files."""

    findings = []
    policy_dir = Path(__file__).resolve().parent / "policies"

    for file_path in paths:
        # Read the configuration file
        try:
            with open(file_path, "r") as f:
                content = f.read()

            # Determine file type and select appropriate policies
            if file_path.endswith((".yaml", ".yml")):
                # Kubernetes YAML - parse to JSON for OPA
                import yaml

                data = yaml.safe_load(content)
                policy_paths = [str(policy_dir / "lib.rego"), str(policy_dir / "kubernetes_security.rego")]
            elif file_path.endswith(".tf"):
                # Terraform - would need HCL parser, skip for now
                continue
            else:
                # Try as JSON
                data = json.loads(content)
                policy_paths = [str(policy_dir / "lib.rego"), str(policy_dir / "kubernetes_security.rego")]

            # Run OPA evaluation
            file_findings = opa_eval(data, policy_paths)
            for f in file_findings:
                # Create dict without extra field to avoid schema issues
                finding_dict = {
                    "tool": f.tool,
                    "rule_id": f.rule_id,
                    "severity": f.severity,
                    "message": f.message,
                    "file": f.file or file_path,
                    "start_line": f.start_line,
                    "end_line": f.end_line,
                }
                findings.append(finding_dict)
        except Exception:
            # Skip files that can't be parsed
            continue

    return findings


class ConfigVerificationParser(vf.Parser):
    """Parser validating the PRD JSON schema."""

    def parse_answer(self, completion: Any) -> Dict[str, Any]:
        text = get_response_text(completion)
        # Try raw JSON first, then extract from markdown code blocks
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            extracted = extract_json_from_markdown(text)
            try:
                data = json.loads(extracted)
            except json.JSONDecodeError:
                return {}
        try:
            violations, patch, confidence = parse_model_output(data)
        except ValueError:  # pragma: no cover - defensive
            return {}
        return {
            "violations": [v.__dict__ for v in violations],
            "patch": patch or "",
            "confidence": confidence,
        }

    def get_format_reward_func(self):  # pragma: no cover - simple
        def format_reward(completion, answer="", **kwargs):  # pylint: disable=unused-argument
            text = get_response_text(completion)
            # Try raw JSON first, then extract from markdown code blocks
            try:
                data = json.loads(text)
            except json.JSONDecodeError:
                extracted = extract_json_from_markdown(text)
                try:
                    data = json.loads(extracted)
                except json.JSONDecodeError:
                    return 0.0
            try:
                parse_model_output(data)
            except ValueError:
                return 0.0
            return 1.0

        return format_reward


async def judge_reward(prompt, completion, answer, state, judge, **kwargs):  # pylint: disable=unused-argument
    """Binary reward from an LLM judge."""

    result = await judge(prompt, completion, answer, state)
    return 1.0 if result.strip().lower().startswith("yes") else 0.0


def format_completion_for_judge(parser: ConfigVerificationParser, completion: Any) -> str:
    """Render structured model output for judge prompts."""

    parsed = parser.parse_answer(completion)
    if parsed:
        return json.dumps(parsed, sort_keys=True)
    return get_response_text(completion)


class _JudgePromptParser:
    """Thin parser wrapper used only when rendering the judge prompt."""

    def __init__(self, base_parser: ConfigVerificationParser) -> None:
        self.base_parser = base_parser

    def parse_answer(self, completion) -> str:
        return format_completion_for_judge(self.base_parser, completion)

    def __getattr__(self, name: str):
        return getattr(self.base_parser, name)


class StructuredConfigJudgeRubric(vf.JudgeRubric):
    """JudgeRubric that passes the full structured config-audit response."""

    def __init__(self, parser: ConfigVerificationParser, **kwargs) -> None:
        super().__init__(parser=parser, **kwargs)
        self._prompt_parser = _JudgePromptParser(parser)

    async def judge(self, prompt, completion, answer, state=None) -> str:
        if isinstance(prompt, list):
            last_msg = prompt[-1]
            question = str(last_msg.get("content", "")) if isinstance(last_msg, dict) else ""
        else:
            question = str(prompt)

        response = self._prompt_parser.parse_answer(completion)
        judge_prompt = self.judge_prompt.format(question=question, answer=answer, response=response)
        cached = state.get("judge_response") if state else None
        if isinstance(cached, dict) and judge_prompt in cached:
            return cached[judge_prompt]

        judge_args = dict(self.judge_sampling_args or {})
        if "max_tokens" in judge_args:
            if judge_args["max_tokens"] is None:
                judge_args.pop("max_tokens")
            else:
                judge_args["max_completion_tokens"] = judge_args.pop("max_tokens")
        if "max_completion_tokens" in judge_args and judge_args["max_completion_tokens"] is None:
            judge_args.pop("max_completion_tokens")
        judge_args = {key: value for key, value in judge_args.items() if value is not None}

        try:
            judge_response = await maybe_await(
                self.judge_client.chat.completions.create,
                model=self.judge_model,
                messages=[{"role": "user", "content": judge_prompt}],
                **judge_args,
            )
            judge_response = str(judge_response.choices[0].message.content)
        except RateLimitError as exc:
            self.logger.warning("Rate limit exceeded when calling judge model %r: %s", self.judge_model, exc)
            raise RuntimeError(f"Judge model rate limit exceeded: {self.judge_model}") from exc
        except APITimeoutError as exc:
            self.logger.warning("Timeout when calling judge model %r: %s", self.judge_model, exc)
            raise RuntimeError(f"Judge model timeout: {self.judge_model}") from exc
        except APIError as exc:
            self.logger.warning("API error when calling judge model %r: %s", self.judge_model, exc)
            raise RuntimeError(f"Judge model API error: {self.judge_model}") from exc

        if state:
            if not isinstance(cached, dict):
                cached = {}
            cached[judge_prompt] = judge_response
            state["judge_response"] = cached
        return judge_response


def _normalize_severity(value: Any) -> str:
    sev = str(value).lower().strip() if value is not None else "med"
    if sev == "medium":
        sev = "med"
    if sev == "critical":
        sev = "high"
    return sev if sev in {"low", "med", "high"} else "med"


def _answer_to_dict(answer: Dict[str, Any] | str | None) -> Dict[str, Any]:
    if isinstance(answer, str):
        try:
            return json.loads(answer)
        except json.JSONDecodeError:
            return {}
    return answer or {}


def _oracle_from_answer(answer_obj: Dict[str, Any], kwargs: Dict[str, Any]) -> tuple[list[Violation], str]:
    fixture_type = answer_obj.get("fixture_type") or kwargs.get("fixture_type") or "k8s"
    fixture_type = str(fixture_type).lower().strip()
    fixture_type = "tf" if fixture_type in {"tf", "terraform"} else "k8s"

    oracle: list[Violation] = []
    if "oracle" in answer_obj:
        oracle_dicts = answer_obj.get("oracle", []) or []
        for v in oracle_dicts:
            if not isinstance(v, dict):
                continue
            vid = v.get("id")
            if vid:
                oracle.append(Violation(id=str(vid), severity=_normalize_severity(v.get("severity"))))  # type: ignore[arg-type]
    else:
        # Hub/build dataset format: oracle findings live under "violations" with tool + rule_id.
        oracle_findings = answer_obj.get("violations", []) or []
        if isinstance(oracle_findings, list):
            for f in oracle_findings:
                if not isinstance(f, dict):
                    continue
                tool = f.get("tool")
                rule_id = f.get("rule_id")
                vid = f.get("id") or (f"{tool}/{rule_id}" if tool and rule_id else None)
                if vid:
                    oracle.append(Violation(id=str(vid), severity=_normalize_severity(f.get("severity"))))  # type: ignore[arg-type]
    return oracle, fixture_type


def _primary_tool_filter(
    predicted: list[Violation],
    oracle: list[Violation],
    fixture_type: str,
) -> tuple[list[Violation], list[Violation]]:
    tool_style = any(v.id.startswith(("kube-linter/", "semgrep/", "opa/")) for v in oracle) or any(
        v.id.startswith(("kube-linter/", "semgrep/", "opa/")) for v in predicted
    )
    if not tool_style:
        return predicted, oracle
    primary_prefix = "kube-linter/" if fixture_type == "k8s" else "semgrep/"
    return (
        [v for v in predicted if v.id.startswith(primary_prefix)],
        [v for v in oracle if v.id.startswith(primary_prefix)],
    )


def _message_value(message: Any, key: str) -> Any:
    if isinstance(message, dict):
        return message.get(key)
    return getattr(message, key, None)


def _parse_tool_content(content: Any) -> Any:
    if not isinstance(content, str):
        return content
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        try:
            return ast.literal_eval(content)
        except (SyntaxError, ValueError):
            return content


def _walk_tool_findings(value: Any) -> list[Violation]:
    if isinstance(value, dict):
        tool = value.get("tool")
        rule_id = value.get("rule_id")
        if tool and rule_id:
            return [
                Violation(
                    id=f"{tool}/{rule_id}",
                    severity=_normalize_severity(value.get("severity")),  # type: ignore[arg-type]
                    message=value.get("message"),
                    file=value.get("file"),
                    start_line=value.get("start_line"),
                    end_line=value.get("end_line"),
                    source_tool=str(tool),
                    native_rule_id=str(rule_id),
                )
            ]
        findings: list[Violation] = []
        for child in value.values():
            findings.extend(_walk_tool_findings(child))
        return findings
    if isinstance(value, list):
        findings = []
        for child in value:
            findings.extend(_walk_tool_findings(child))
        return findings
    return []


def _extract_tool_observation_violations(completion: Any) -> list[Violation]:
    if not isinstance(completion, list):
        return []
    findings: list[Violation] = []
    for message in completion:
        if _message_value(message, "role") != "tool":
            continue
        findings.extend(_walk_tool_findings(_parse_tool_content(_message_value(message, "content"))))

    deduped: dict[str, Violation] = {}
    for finding in findings:
        deduped.setdefault(finding.id, finding)
    return list(deduped.values())


def tool_observation_reward(completion, answer: Dict[str, Any] | str | None = None, **kwargs) -> float:
    """Reward executable evidence surfaced by actual tool observations."""

    observed = _extract_tool_observation_violations(completion)
    if not observed:
        return 0.0

    answer_obj = _answer_to_dict(answer)
    oracle, fixture_type = _oracle_from_answer(answer_obj, kwargs)
    observed, oracle = _primary_tool_filter(observed, oracle, fixture_type)
    if not observed or not oracle:
        return 0.0
    return max(0.0, final_reward(observed, oracle, format_bonus=0.0, invalid_penalty=0.0))


def _build_executable_rubric(parser: ConfigVerificationParser) -> vf.Rubric:
    return vf.Rubric(
        funcs=[reward_config_auditing, parser.get_format_reward_func(), tool_observation_reward],
        weights=[1.0, 0.05, 0.2],
        parser=parser,
    )


def _build_judge_rubric(
    parser: ConfigVerificationParser,
    judge_model: str,
) -> StructuredConfigJudgeRubric:
    rubric = StructuredConfigJudgeRubric(
        parser=parser,
        judge_model=judge_model,
        judge_prompt=JUDGE_PROMPT,
        judge_sampling_args={"max_tokens": 16, "temperature": 0.0},
    )
    rubric.add_reward_func(judge_reward, weight=1.0)
    return rubric


# pylint: disable=unused-argument
def reward_config_auditing(
    completion,
    answer: Dict[str, Any] | str | None = None,
    **kwargs: Dict[str, Any],
) -> float:
    """Reward combining detection accuracy and patch verification.

    In recent verifiers releases, datasets often store `answer` as a string.
    Accept both dict and JSON string forms for compatibility.
    """

    text = get_response_text(completion)
    # Try raw JSON first, then extract from markdown code blocks. Invalid prose
    # should not earn executable reward; early shaped signal comes from actual
    # tool observations via `tool_observation_reward`.
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        extracted = extract_json_from_markdown(text)
        try:
            data = json.loads(extracted)
        except json.JSONDecodeError:
            return 0.0
        else:
            try:
                violations_pred, patch, _ = parse_model_output(data)
            except (ValueError, KeyError):
                return 0.0
    else:
        try:
            violations_pred, patch, _ = parse_model_output(data)
        except (ValueError, KeyError):
            return 0.0

    if not violations_pred:
        return 0.0

    answer_obj = _answer_to_dict(answer)
    oracle, fixture_type = _oracle_from_answer(answer_obj, kwargs)

    # Scoring contract: For k8s, primary oracle is kube-linter; for tf, primary oracle is semgrep.
    # Datasets may include extra tool findings; ignore them for scoring to avoid oracle/tool mismatch.
    violations_pred, oracle = _primary_tool_filter(violations_pred, oracle, fixture_type)

    post: List[Violation] | None = None
    if patch:
        fixture_path = (answer_obj or {}).get("fixture_path") or kwargs.get("fixture_path") or ""
        applied, new_text = try_apply_patch(fixture_path, patch)
        if applied:
            with tempfile.NamedTemporaryFile("w", delete=False) as tmp:
                tmp.write(new_text)
                tmp_path = tmp.name
            try:
                if fixture_type == "k8s":
                    post_findings = kubelinter_lint([tmp_path])
                else:
                    post_findings = semgrep_scan([tmp_path], rules="p/terraform")
                post = normalize_findings(post_findings)
            finally:
                Path(tmp_path).unlink(missing_ok=True)

    return max(0.0, final_reward(violations_pred, oracle, had_valid_json=True, post_patch=post))


def _create_builtin_fixtures() -> Dataset:
    """Create builtin test fixtures for E2.

    Returns:
        Dataset with builtin Kubernetes and Terraform fixtures
    """
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
    for item in fixtures:
        fixture_path = str(item["path"])
        config_text = Path(item["path"]).read_text(encoding="utf-8")
        question = f"File path: {fixture_path}\n\nConfiguration:\n```text\n{config_text}\n```"
        oracle = json.loads(Path(item["oracle"]).read_text(encoding="utf-8"))
        answer_obj = {
            "oracle": oracle,
            "fixture_path": fixture_path,
            "fixture_type": item["type"],
        }
        # Store answer as JSON string for compatibility with recent verifiers schemas
        items.append({"question": question, "answer": json.dumps(answer_obj)})
    return Dataset.from_list(items)


def _convert_e2_format(example: Dict[str, Any]) -> Dict[str, Any]:
    """Convert E2 build format to environment format.

    Supported input formats:
        - Build format: {"prompt": "<config>", "info": {...}, "meta": {...}}
        - Hub format: {"question": "<config>", "info": {...}, "meta": {...}}
        - Env format: {"question": "<config>", "answer": "<json-string>"}

    Output format: {"question": "<config>", "answer": "<json-string>"}
    """
    if "question" in example and "answer" in example:
        # Already in correct format
        return example

    # Convert from build/hub format (has "info" instead of "answer")
    # Hub format uses "question", build format uses "prompt"
    question = example.get("question") or example.get("prompt", "")
    info = example.get("info", {})
    if isinstance(info, dict):
        fixture_path = info.get("fixture_path")
        if fixture_path and "File path:" not in question:
            question = f"File path: {fixture_path}\n\nConfiguration:\n```text\n{question}\n```"
    return {
        "question": question,
        "answer": json.dumps(info),
    }


def load_environment(
    dataset_name: str = "builtin",
    dataset_source: DatasetSource = "auto",
    max_examples: int = 100,
    max_turns: int | None = None,  # pylint: disable=unused-argument
    logger: RolloutLogger | None = None,
    include_tools: bool = True,
    reward_source: str = "executable",
    judge_model: str = "gpt-4.1-nano",
) -> vf.ToolEnv:
    """Load the configuration auditing environment.

    Args:
        dataset_name: Dataset to load. Available options:
            - "builtin" or "fixtures": Hardcoded test fixtures (for testing)
            - "k8s-labeled-v1.jsonl": Kubernetes labeled dataset (N=444)
            - "terraform-labeled-v1.jsonl": Terraform labeled dataset (N=115)
            - "combined" or "all": Both k8s and terraform datasets (N=559)
            - "synthetic": Alias for builtin fixtures
            - Or any local .jsonl file path (absolute or relative to env/data/)
        dataset_source: Where to load the dataset from. Options:
            - "auto" (default): Try local → hub → builtin fixtures
            - "local": Only load from local JSONL files
            - "hub": Only load from HuggingFace Hub (requires HF_TOKEN)
            - "synthetic": Use builtin test fixtures
        max_examples: Maximum number of examples to load from the dataset.
        logger: Optional rollout logger to capture dataset metadata.
        include_tools: Whether to include security tools (can be disabled for testing).
        reward_source: Reward source variant: "executable", "llm_judge", or "hybrid".
        judge_model: LLM model for judge/hybrid reward variants.

    Environment Variables:
        HF_TOKEN: HuggingFace API token (required for Hub datasets)
        E2_HF_REPO: Custom HF repo for E2 datasets (default: intertwine-ai/security-verifiers-e2-private)

    Returns:
        A Verifiers ToolEnv configured for the task.

    Examples:
        # Use auto-loading (local → hub → builtin fallback)
        env = load_environment()

        # Load from local dataset (requires 'make data-e2-local')
        env = load_environment(dataset_name="k8s-labeled-v1.jsonl", dataset_source="local")

        # Load from HuggingFace Hub (requires HF_TOKEN)
        env = load_environment(dataset_source="hub")

        # Use builtin fixtures for quick testing
        env = load_environment(dataset_source="synthetic")

        # Load from user's own HF repo
        import os
        os.environ["E2_HF_REPO"] = "my-org/my-security-verifiers-e2"
        env = load_environment(dataset_source="hub")
    """
    del max_turns  # Accepted for API compatibility but not used by ToolEnv
    reward_source = reward_source.strip().lower()
    if reward_source not in {"executable", "llm_judge", "hybrid"}:
        raise ValueError("reward_source must be executable, llm_judge, or hybrid")
    env_root = Path(__file__).resolve().parent

    # Handle "builtin", "fixtures", or "synthetic" as explicit requests for test data
    if dataset_name in ("builtin", "fixtures", "synthetic") or dataset_source == "synthetic":
        print(f"Using builtin test fixtures (requested: {dataset_name})")
        dataset = _create_builtin_fixtures()
        resolved_name = "synthetic::builtin"
    else:
        # Use shared multi-tiered loader for all other cases
        # Note: E2 has a custom format converter since build scripts produce different schema
        dataset, resolved_name = load_dataset_with_fallback(
            dataset_name=dataset_name,
            env_root=env_root,
            dataset_source=dataset_source,
            max_examples=max_examples,
            field_mapping=None,  # We'll apply format conversion via map
            synthetic_generator=_create_builtin_fixtures,
        )

        # Convert E2 build format to environment format
        dataset = dataset.map(_convert_e2_format)

    # Apply max_examples if not already limited
    if max_examples and len(dataset) > max_examples:
        dataset = dataset.select(range(max_examples))

    dataset_name = resolved_name

    parser = ConfigVerificationParser()
    executable_rubric = _build_executable_rubric(parser)
    if reward_source == "executable":
        rubric = executable_rubric
    elif reward_source == "llm_judge":
        rubric = _build_judge_rubric(parser, judge_model)
    else:
        rubric = vf.RubricGroup([executable_rubric, _build_judge_rubric(parser, judge_model)])
    if logger and logger.enabled:
        logger.log_environment_init(
            environment_name="sv-env-config-verification",
            dataset_name=dataset_name,
            total_examples=len(dataset),
            metadata={
                "max_examples": max_examples,
                "fixture_root": str(DATASET_ROOT),
                "reward_source": reward_source,
                "judge_model": judge_model if reward_source in {"llm_judge", "hybrid"} else None,
            },
        )

    return vf.ToolEnv(
        name="sv-env-config-verification",
        description=("Audit Kubernetes and Terraform configurations using pinned tool outputs."),
        dataset=dataset,
        parser=parser,
        rubric=rubric,
        # Expose only tools whose schemas convert cleanly to strict JSON schema for tool calling
        tools=[run_kubelinter, run_semgrep, run_opa] if include_tools else [],
        system_prompt=(
            "You are a security auditor for Kubernetes and Terraform configurations.\n\n"
            "The task includes a `File path:` line followed by the configuration content.\n"
            "If tools are available, call the relevant tool on that path before your final answer:\n"
            "- For Kubernetes YAML, call run_kubelinter with paths=[the provided file path].\n"
            "- For Terraform, call run_semgrep with paths=[the provided file path].\n"
            "- Use run_opa only as supporting evidence when useful.\n\n"
            "Available tools:\n"
            "- run_kubelinter: Analyze Kubernetes YAML files for security issues\n"
            "- run_semgrep: Scan Terraform and other files for security patterns\n"
            "- run_opa: Evaluate configurations against Open Policy Agent security policies\n\n"
            "For Kubernetes, check for violations like:\n"
            "- kube-linter/run-as-non-root (containers running as root)\n"
            "- kube-linter/latest-tag (using :latest image tags)\n"
            "- kube-linter/no-read-only-root-fs (writable root filesystem)\n"
            "- kube-linter/unset-cpu-requirements (missing CPU limits/requests)\n"
            "- kube-linter/unset-memory-requirements (missing memory limits/requests)\n"
            "- kube-linter/privilege-escalation-container (allowPrivilegeEscalation)\n"
            "- kube-linter/non-existent-service-account (invalid service account)\n"
            "- opa/GEN_001, opa/GEN_002 (OPA policy violations)\n\n"
            "For Terraform, be conservative - only flag clear security issues.\n\n"
            "Return a JSON object with exactly these fields:\n"
            "- violations: array of objects, each with 'id' (string like 'tool/rule-id'), "
            "'severity' ('low', 'med', or 'high')\n"
            "- patch: string containing a *valid unified diff* (optional; use empty string if unsure)\n"
            "- confidence: float between 0 and 1\n\n"
            "Patch requirements (if patch is non-empty):\n"
            "- Must be a unified diff that `patch` can apply.\n"
            "- Include file headers starting with '---' and '+++'.\n"
            "- Include at least one hunk header like '@@ -1,3 +1,4 @@' (with numbers).\n"
            "- Do NOT use apply_patch-style markers like '*** Begin Patch'.\n"
            "- Do NOT include explanations inside the patch; only diff text.\n\n"
            "Example:\n"
            "{\n"
            '  "violations": [\n'
            '    {"id": "kube-linter/run-as-non-root", "severity": "med"},\n'
            '    {"id": "kube-linter/latest-tag", "severity": "med"},\n'
            '    {"id": "opa/GEN_001", "severity": "med"}\n'
            "  ],\n"
            '  "patch": "",\n'
            '  "confidence": 0.9\n'
            "}"
        ),
    )


__all__ = [
    "ConfigVerificationParser",
    "reward_config_auditing",
    "tool_observation_reward",
    "load_environment",
]
