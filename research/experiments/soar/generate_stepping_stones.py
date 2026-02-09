#!/usr/bin/env python3
"""
Stepping-Stone Generator for SOAR Experiments.

Implements the teacher component of SOAR adapted for security verification:
- E1: Generates synthetic network log classification problems at controlled difficulty
- E2: Generates synthetic config audit problems with known violations

This is a **prototype** for Phase 2 of the SOAR integration path.
It generates teacher-produced stepping stones WITHOUT the full bilevel loop.
Use this to validate that generated problems are structurally well-formed
and that training on them helps before investing in the full meta-RL framework.

Usage:
    # Generate E1 stepping stones (network log classification)
    python research/experiments/soar/generate_stepping_stones.py \
        --env e1 \
        --model gpt-5-mini \
        --num-problems 50 \
        --difficulty easy

    # Generate E2 stepping stones (config audit)
    python research/experiments/soar/generate_stepping_stones.py \
        --env e2 \
        --model gpt-5-mini \
        --num-problems 20 \
        --difficulty medium

    # Validate generated stepping stones
    python research/experiments/soar/generate_stepping_stones.py \
        --env e1 \
        --validate-only \
        --input research/experiments/soar/results/stepping_stones_e1_*.jsonl

Output:
    research/experiments/soar/results/stepping_stones_{env}_{difficulty}_{timestamp}.jsonl
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

# ---------------------------------------------------------------------------
# Teacher Prompt Templates
# ---------------------------------------------------------------------------

E1_TEACHER_SYSTEM_PROMPT = """\
You are a cybersecurity dataset generator. Your task is to generate realistic
network flow log entries for training a network anomaly detection model.

Each generated sample must be a valid JSON object with these fields:
- "question": A realistic network flow log entry (as would appear in IoT-23 or similar datasets)
- "answer": Either "Malicious" or "Benign"
- "metadata": An object with "difficulty" (easy/medium/hard) and "attack_type" (if malicious)

Guidelines for difficulty levels:
- easy: Clear-cut cases. Malicious traffic has obvious indicators (known bad ports,
  high packet counts, suspicious protocols). Benign traffic is clearly normal.
- medium: Ambiguous cases. Malicious traffic uses common ports/protocols but has
  subtle anomalies. Benign traffic may have unusual but legitimate patterns.
- hard: Adversarial cases. Malicious traffic mimics normal patterns. Benign traffic
  has characteristics that look suspicious but are legitimate.

Generate diverse examples covering different protocols (TCP, UDP, ICMP),
attack types (DDoS, PortScan, C&C, FileDownload), and network configurations.

Output ONLY valid JSON, one object per line. No other text."""

E1_TEACHER_USER_PROMPT = """\
Generate {num_problems} network flow log entries at {difficulty} difficulty.
{context}

Output each as a JSON object on a separate line. Every entry must have
"question", "answer", and "metadata" fields."""

E2_TEACHER_SYSTEM_PROMPT = """\
You are a cloud security configuration dataset generator. Your task is to generate
realistic Kubernetes manifests or Terraform configurations with known security
issues for training a configuration auditing model.

Each generated sample must be a valid JSON object with these fields:
- "question": A realistic configuration file (K8s YAML or Terraform HCL)
- "answer": A JSON object describing the expected violations
- "config_type": Either "kubernetes" or "terraform"
- "metadata": An object with "difficulty", "num_violations", and "violation_types"

Guidelines for difficulty levels:
- easy: Single violation, obvious misconfiguration (e.g., container running as root,
  no resource limits, privileged container).
- medium: 2-3 violations across different categories (e.g., missing network policy +
  no security context + overly permissive RBAC).
- hard: Subtle misconfigurations that require domain expertise (e.g., writable root
  filesystem with specific volume mounts, service account token automounting in
  sensitive namespaces, missing pod disruption budgets).

Generate diverse examples covering different resource types and violation categories.

Output ONLY valid JSON, one object per line. No other text."""

E2_TEACHER_USER_PROMPT = """\
Generate {num_problems} cloud security configuration files at {difficulty} difficulty.
Config type: {config_type}
{context}

Output each as a JSON object on a separate line. Every entry must have
"question", "answer", "config_type", and "metadata" fields."""

# ---------------------------------------------------------------------------
# Context Generators (provide real examples to guide teacher)
# ---------------------------------------------------------------------------


def load_real_examples(env: str, num_examples: int = 3) -> str:
    """Load real examples from the dataset to provide context to the teacher."""
    if env == "e1":
        try:
            from sv_env_network_logs import load_environment  # type: ignore

            e = load_environment(dataset_source="synthetic", max_examples=num_examples)
            dataset = e.dataset
            if hasattr(dataset, "to_list"):
                dataset = dataset.to_list()
            examples = []
            for sample in dataset[:num_examples]:
                examples.append(
                    json.dumps(
                        {
                            "question": str(sample.get("question", ""))[:500],
                            "answer": str(sample.get("answer", "")),
                        }
                    )
                )
            return "\nHere are real examples for reference:\n" + "\n".join(examples)
        except Exception:
            logger.debug("Failed to load E1 examples for teacher context", exc_info=True)
            return ""
    elif env == "e2":
        try:
            sys.path.append(str(REPO_ROOT / "environments" / "sv-env-config-verification"))
            from sv_env_config_verification import load_environment  # type: ignore

            e = load_environment(dataset_source="synthetic", max_examples=num_examples)
            dataset = e.dataset
            if hasattr(dataset, "to_list"):
                dataset = dataset.to_list()
            examples = []
            for sample in dataset[:num_examples]:
                examples.append(
                    json.dumps(
                        {
                            "question": str(sample.get("question", ""))[:500],
                            "answer": str(sample.get("answer", ""))[:200],
                        }
                    )
                )
            return "\nHere are real examples for reference:\n" + "\n".join(examples)
        except Exception:
            logger.debug("Failed to load E2 examples for teacher context", exc_info=True)
            return ""
    return ""


# ---------------------------------------------------------------------------
# Generation
# ---------------------------------------------------------------------------


def generate_stepping_stones(
    env: str,
    model: str,
    num_problems: int,
    difficulty: str,
    config_type: str = "kubernetes",
) -> list[dict[str, Any]]:
    """Generate stepping-stone problems using a teacher model."""
    from model_router import get_client_for_model  # noqa: E402

    client, effective_model = get_client_for_model(model)

    context = load_real_examples(env, num_examples=3)

    if env == "e1":
        system_prompt = E1_TEACHER_SYSTEM_PROMPT
        user_prompt = E1_TEACHER_USER_PROMPT.format(
            num_problems=num_problems,
            difficulty=difficulty,
            context=context,
        )
    elif env == "e2":
        system_prompt = E2_TEACHER_SYSTEM_PROMPT
        user_prompt = E2_TEACHER_USER_PROMPT.format(
            num_problems=num_problems,
            difficulty=difficulty,
            config_type=config_type,
            context=context,
        )
    else:
        raise ValueError(f"Unknown environment: {env}")

    print(f"Generating {num_problems} {difficulty} stepping stones for {env} using {model}...")

    resp = client.chat.completions.create(
        model=effective_model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.8,  # Higher temperature for diversity
        max_tokens=4096 * min(num_problems, 10),  # Scale tokens with problem count
    )

    raw_text = resp.choices[0].message.content if resp.choices else ""

    # Parse the response into individual problems
    problems = []
    for line in raw_text.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
            if isinstance(obj, dict) and "question" in obj:
                obj["_generation_metadata"] = {
                    "teacher_model": model,
                    "effective_model": effective_model,
                    "difficulty": difficulty,
                    "env": env,
                }
                problems.append(obj)
        except json.JSONDecodeError:
            continue

    print(f"  Parsed {len(problems)}/{num_problems} valid problems from teacher output")
    return problems


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def validate_e1_problem(problem: dict[str, Any]) -> dict[str, Any]:
    """Validate a generated E1 stepping-stone problem."""
    issues = []

    question = problem.get("question", "")
    answer = problem.get("answer", "")

    if not question:
        issues.append("missing_question")
    elif len(question) < 20:
        issues.append("question_too_short")

    if answer not in ("Malicious", "Benign"):
        issues.append(f"invalid_answer: {answer}")

    # Check for structural quality (the SOAR paper finding: structure > correctness)
    _IPV4_RE = re.compile(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b")
    has_ip = bool(_IPV4_RE.search(question))
    has_port = any(word.isdigit() and 0 < int(word) < 65536 for word in question.split() if word.isdigit())
    has_protocol = any(p in question.upper() for p in ("TCP", "UDP", "ICMP", "HTTP", "DNS"))

    structural_score = sum([bool(has_ip), bool(has_port), bool(has_protocol)]) / 3.0

    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "structural_score": structural_score,
        "question_length": len(question),
    }


def validate_e2_problem(problem: dict[str, Any]) -> dict[str, Any]:
    """Validate a generated E2 stepping-stone problem."""
    issues = []

    question = problem.get("question", "")
    config_type = problem.get("config_type", "")

    if not question:
        issues.append("missing_question")
    elif len(question) < 50:
        issues.append("question_too_short")

    if config_type not in ("kubernetes", "terraform"):
        issues.append(f"invalid_config_type: {config_type}")

    # Check structural quality for K8s
    if config_type == "kubernetes":
        has_apiversion = "apiVersion" in question or "apiversion" in question.lower()
        has_kind = "kind:" in question or "kind :" in question
        has_metadata = "metadata:" in question
        structural_score = sum([has_apiversion, has_kind, has_metadata]) / 3.0
    elif config_type == "terraform":
        has_resource = "resource" in question
        has_block = "{" in question
        has_provider = "provider" in question or "aws" in question or "azurerm" in question
        structural_score = sum([has_resource, has_block, has_provider]) / 3.0
    else:
        structural_score = 0.0

    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "structural_score": structural_score,
        "question_length": len(question),
    }


def validate_stepping_stones(
    problems: list[dict[str, Any]],
    env: str,
) -> dict[str, Any]:
    """Validate a batch of stepping-stone problems."""
    validator = validate_e1_problem if env == "e1" else validate_e2_problem

    results = [validator(p) for p in problems]
    valid_count = sum(1 for r in results if r["valid"])
    structural_scores = [r["structural_score"] for r in results]

    return {
        "total": len(problems),
        "valid": valid_count,
        "valid_fraction": valid_count / len(problems) if problems else 0.0,
        "mean_structural_score": (
            sum(structural_scores) / len(structural_scores) if structural_scores else 0.0
        ),
        "issue_counts": _count_issues(results),
        "per_problem": results,
    }


def _count_issues(results: list[dict[str, Any]]) -> dict[str, int]:
    """Count issue frequencies across all validation results."""
    counts: dict[str, int] = {}
    for r in results:
        for issue in r["issues"]:
            key = issue.split(":")[0]
            counts[key] = counts.get(key, 0) + 1
    return counts


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate SOAR stepping-stone problems")
    parser.add_argument(
        "--env",
        choices=["e1", "e2"],
        required=True,
        help="Environment to generate for",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="gpt-5-mini",
        help="Teacher model for generation",
    )
    parser.add_argument(
        "--num-problems",
        type=int,
        default=20,
        help="Number of problems to generate",
    )
    parser.add_argument(
        "--difficulty",
        choices=["easy", "medium", "hard"],
        default="medium",
        help="Difficulty level of generated problems",
    )
    parser.add_argument(
        "--config-type",
        choices=["kubernetes", "terraform"],
        default="kubernetes",
        help="Config type for E2 (ignored for E1)",
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Only validate existing stepping stones (requires --input)",
    )
    parser.add_argument(
        "--input",
        type=str,
        help="Input JSONL file for validation",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Output directory",
    )
    args = parser.parse_args()

    default_output = REPO_ROOT / "research" / "experiments" / "soar" / "results"
    output_dir = Path(args.output_dir) if args.output_dir else default_output
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.validate_only:
        if not args.input:
            print("Error: --validate-only requires --input")
            sys.exit(1)
        input_path = Path(args.input)
        problems = []
        with input_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    problems.append(json.loads(line))
        print(f"Validating {len(problems)} problems from {input_path}...")
        validation = validate_stepping_stones(problems, args.env)
        print("\nValidation Results:")
        print(f"  Valid: {validation['valid']}/{validation['total']} ({validation['valid_fraction']:.1%})")
        print(f"  Mean structural score: {validation['mean_structural_score']:.3f}")
        if validation["issue_counts"]:
            print(f"  Issues: {validation['issue_counts']}")
        return

    # Check for API key
    has_openai = bool(os.environ.get("OPENAI_API_KEY"))
    has_openrouter = bool(os.environ.get("OPENROUTER_API_KEY"))
    if not has_openai and not has_openrouter:
        print("Error: Set OPENAI_API_KEY or OPENROUTER_API_KEY in .env")
        print("  cp .env.example .env && edit .env")
        sys.exit(1)

    # Generate
    problems = generate_stepping_stones(
        env=args.env,
        model=args.model,
        num_problems=args.num_problems,
        difficulty=args.difficulty,
        config_type=args.config_type,
    )

    if not problems:
        print("No valid problems generated. Check teacher model output.")
        sys.exit(1)

    # Validate
    validation = validate_stepping_stones(problems, args.env)
    print(
        f"\nValidation: {validation['valid']}/{validation['total']} valid "
        f"(structural score: {validation['mean_structural_score']:.3f})"
    )

    # Write output
    ts_short = time.strftime("%Y%m%d-%H%M%S", time.gmtime())
    output_path = output_dir / f"stepping_stones_{args.env}_{args.difficulty}_{ts_short}.jsonl"
    with output_path.open("w", encoding="utf-8") as f:
        for p in problems:
            f.write(json.dumps(p) + "\n")

    # Write validation report
    val_path = output_dir / f"stepping_stones_{args.env}_{args.difficulty}_{ts_short}_validation.json"
    val_path.write_text(json.dumps(validation, indent=2), encoding="utf-8")

    print(f"\nOutput: {output_path}")
    print(f"Validation: {val_path}")


if __name__ == "__main__":
    main()
