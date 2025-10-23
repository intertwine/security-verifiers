#!/usr/bin/env python3
"""
Multi-turn evaluation harness for sv-env-config-verification with tool calling support.

This script properly handles the ToolEnv's multi-turn nature, allowing models to:
1. Call security analysis tools (kube-linter, semgrep, OPA) when enabled
2. Process tool responses
3. Generate final answers based on tool outputs

Usage:
  python scripts/eval_config_verification.py \
    --models gpt-5-mini \
    --num-examples 2 \
    --include-tools true \
    --max-turns 5
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, cast

# Ensure local repo modules are importable
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
os.environ.setdefault("PYTHONPATH", str(REPO_ROOT))

# Import eval utilities (must be before environment imports to avoid circular deps)
from scripts.eval_utils import EarlyStopError, ErrorTracker  # noqa: E402
from scripts.model_router import get_client_for_model  # noqa: E402

# Initialize Weave before importing environments for automatic tracing
# pylint: disable=wrong-import-position
from sv_env_config_verification import (  # type: ignore[import]  # noqa: E402
    load_environment,
    reward_config_auditing,
)
from sv_shared import weave_init  # type: ignore  # noqa: F401, E402

try:
    from openai import OpenAI
except Exception as exc:  # pragma: no cover
    raise SystemExit(f"The 'openai' package is required: {exc}") from exc


def _git_commit() -> str | None:
    """Get current git commit hash."""
    try:
        res = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
            cwd=str(REPO_ROOT),
        )
        return res.stdout.strip() or None
    except Exception:
        return None


def _cmd_version(cmd: str, args: List[str]) -> str | None:
    """Get version of a command."""
    try:
        res = subprocess.run([cmd, *args], capture_output=True, text=True, check=False)
        return (res.stdout or res.stderr).strip() or None
    except Exception:
        return None


def ensure_dir(path: Path) -> None:
    """Ensure directory exists."""
    path.mkdir(parents=True, exist_ok=True)


def parse_models(s: str) -> List[str]:
    """Parse comma-separated list of models."""
    return [m.strip() for m in s.replace(" ", "").split(",") if m.strip()]


def convert_tools_to_openai_format(tools: List) -> List[Dict[str, Any]]:
    """Convert environment tools to OpenAI function format."""
    openai_tools = []
    for tool in tools:
        # Extract function signature and docstring
        import inspect

        sig = inspect.signature(tool)
        params = {}
        required = []

        for param_name, _ in sig.parameters.items():
            if param_name == "paths":
                params["paths"] = {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of file paths to analyze",
                }
                required.append("paths")

        openai_tools.append(
            {
                "type": "function",
                "function": {
                    "name": tool.__name__,
                    "description": (tool.__doc__ or "").strip().split("\n")[0],
                    "parameters": {"type": "object", "properties": params, "required": required},
                },
            }
        )

    return openai_tools


async def run_multiturn_evaluation(
    client: OpenAI,
    env: Any,
    model: str,
    question: str,
    answer: Any,
    max_turns: int = 5,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
    fixture_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Run a multi-turn evaluation with tool calling support.

    Returns a dictionary with the completion and any tool interactions.
    """
    # Create a temporary file with the configuration content for tools to analyze
    temp_file = None
    temp_path = None
    if question and (question.startswith("apiVersion:") or question.startswith("resource")):
        # Determine file extension based on content
        ext = ".yaml" if "apiVersion:" in question else ".tf"
        temp_file = tempfile.NamedTemporaryFile(mode="w", suffix=ext, delete=False)
        temp_file.write(question)
        temp_file.close()
        temp_path = temp_file.name

    # Initialize conversation with system prompt and user question
    # Include file path hint if we created a temp file
    enhanced_prompt = env.system_prompt
    if temp_path:
        enhanced_prompt += f"\n\nThe configuration to analyze has been saved to: {temp_path}"

    messages = [{"role": "system", "content": enhanced_prompt}, {"role": "user", "content": question}]

    # Convert tools to OpenAI format if available
    openai_tools = []
    if hasattr(env, "tools") and env.tools:
        openai_tools = convert_tools_to_openai_format(env.tools)

    # Track tool calls for debugging
    tool_interactions = []
    final_completion = ""

    for turn in range(max_turns):
        try:
            # Build kwargs for API call
            kwargs = {
                "model": model,
                "messages": messages,
            }

            # Add tools if available
            if openai_tools:
                kwargs["tools"] = openai_tools
                kwargs["tool_choice"] = "auto"

            # Add optional parameters
            # GPT-5 series models don't support custom temperature (only default: 1)
            is_gpt5 = model.startswith("gpt-5")
            if temperature is not None and not is_gpt5:
                kwargs["temperature"] = temperature
            if max_tokens is not None:
                kwargs["max_tokens"] = max_tokens

            # Make API call
            response = client.chat.completions.create(**kwargs)
            assistant_message = response.choices[0].message

            # Add assistant message to conversation
            messages.append(
                {
                    "role": "assistant",
                    "content": assistant_message.content,
                    "tool_calls": (
                        assistant_message.tool_calls if hasattr(assistant_message, "tool_calls") else None
                    ),
                }
            )

            # Check if there are tool calls to process
            if hasattr(assistant_message, "tool_calls") and assistant_message.tool_calls:
                for tool_call in assistant_message.tool_calls:
                    function_name = tool_call.function.name
                    function_args = json.loads(tool_call.function.arguments)

                    # Record tool interaction
                    tool_interactions.append(
                        {"turn": turn, "tool": function_name, "arguments": function_args}
                    )

                    # Find and call the actual tool
                    tool_result = None
                    for tool in env.tools:
                        if tool.__name__ == function_name:
                            try:
                                # Call the tool with the provided arguments
                                if "paths" in function_args:
                                    # Use the fixture path or temp path if provided
                                    paths = function_args["paths"]
                                    if not any(Path(p).exists() for p in paths):
                                        if temp_path:
                                            paths = [temp_path]
                                        elif fixture_path:
                                            paths = [fixture_path]
                                    tool_result = tool(paths)
                                else:
                                    tool_result = tool(**function_args)
                            except Exception as e:
                                tool_result = f"Error calling tool: {str(e)}"
                            break

                    if tool_result is None:
                        tool_result = f"Tool {function_name} not found"

                    # Add tool response to conversation
                    messages.append(
                        {
                            "role": "tool",
                            "content": (
                                json.dumps(tool_result) if not isinstance(tool_result, str) else tool_result
                            ),
                            "tool_call_id": tool_call.id,
                        }
                    )
            else:
                # No tool calls, we have the final answer
                final_completion = assistant_message.content or ""
                break

        except Exception as e:
            # Clean up temp file on error
            if temp_path:
                try:
                    Path(temp_path).unlink(missing_ok=True)
                except Exception:
                    pass
            return {"completion": "", "error": str(e), "tool_interactions": tool_interactions}

    # Clean up temp file if created
    if temp_path:
        try:
            Path(temp_path).unlink(missing_ok=True)
        except Exception:
            pass

    return {"completion": final_completion, "tool_interactions": tool_interactions, "turns_used": turn + 1}


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Multi-turn evaluation for sv-env-config-verification with tool support"
    )
    parser.add_argument(
        "--models",
        required=True,
        help="Comma-separated list of model ids (e.g., gpt-5-mini)",
    )
    parser.add_argument(
        "--num-examples",
        type=int,
        default=2,
        help="Number of examples to evaluate (max 2 in builtin dataset)",
    )
    parser.add_argument(
        "--dataset",
        type=str,
        default="builtin",
        help=(
            "Local dataset to load. Build datasets with 'make data-e2-local'. "
            "Options: builtin (fixtures), k8s-labeled-v1.jsonl (N=444), "
            "terraform-labeled-v1.jsonl (N=115), combined (N=559)"
        ),
    )
    parser.add_argument(
        "--include-tools",
        type=str,
        default="true",
        help="Whether to include tools (true/false)",
    )
    parser.add_argument(
        "--max-turns",
        type=int,
        default=5,
        help="Maximum number of turns for tool interactions",
    )
    parser.add_argument("--temperature", type=float, default=None, help="Sampling temperature (optional)")
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=4096,
        help="Max tokens per completion (E2 needs more for tool interactions)",
    )
    parser.add_argument(
        "--max-consecutive-errors",
        type=int,
        default=3,
        help="Stop evaluation after this many consecutive errors (default: 3). "
        "Set to 0 to disable early stopping.",
    )
    args = parser.parse_args()

    models = parse_models(args.models)
    include_tools = str(args.include_tools).lower() in {"1", "true", "yes"}

    # Load environment
    print(f"Loading environment (tools={'enabled' if include_tools else 'disabled'})...")
    env = load_environment(
        dataset_name=args.dataset, max_examples=args.num_examples, include_tools=include_tools
    )
    dataset = env.dataset  # type: ignore[attr-defined]

    # Convert Dataset to list for iteration
    if hasattr(dataset, "to_list"):
        dataset = dataset.to_list()  # type: ignore[attr-defined]
    assert dataset is not None, "Dataset should not be None"
    dataset = cast(List[Dict[str, Any]], dataset)

    format_reward = env.parser.get_format_reward_func()  # type: ignore[attr-defined]

    # Report available tools
    if hasattr(env, "tools") and env.tools:
        print(f"Available tools: {[t.__name__ for t in env.tools]}")
    else:
        print("Warning: No tools available in environment")

    # Output base
    out_base = REPO_ROOT / "outputs" / "evals"
    ensure_dir(out_base)

    ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    # Tool versions metadata
    kube_linter_ver = _cmd_version("kube-linter", ["version"]) or None
    semgrep_ver = _cmd_version("semgrep", ["--version"]) or None
    opa_ver = _cmd_version("opa", ["version"]) or None

    for model in models:
        print(f"\nEvaluating model: {model}")

        # Get appropriate client for this model
        try:
            client, effective_model = get_client_for_model(model)
        except SystemExit as e:
            print(f"✗ Skipping {model}: {e}")
            continue

        run_id = uuid.uuid4().hex[:8]
        run_dir = out_base / f"sv-env-config-verification--{model}" / run_id
        ensure_dir(run_dir)
        meta_path = run_dir / "metadata.json"
        results_path = run_dir / "results.jsonl"

        metadata: Dict[str, Any] = {
            "environment": "sv-env-config-verification",
            "evaluation_type": "multi-turn",
            "model": model,
            "effective_model": effective_model,  # Track the actual model name used (e.g., OpenRouter path)
            "dataset": args.dataset,
            "timestamp": ts,
            "num_examples": len(dataset),
            "include_tools": include_tools,
            "max_turns": args.max_turns,
            "max_consecutive_errors": args.max_consecutive_errors,
            "git_commit": _git_commit(),
            "tool_versions": {
                "kube_linter": kube_linter_ver,
                "semgrep": semgrep_ver,
                "opa": opa_ver,
            },
        }
        if args.temperature is not None:
            metadata["temperature"] = args.temperature
        if args.max_tokens is not None:
            metadata["max_tokens"] = args.max_tokens

        meta_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

        # Initialize error tracker for early stopping
        error_tracker = None
        if args.max_consecutive_errors > 0:
            window_size = max(5, args.max_consecutive_errors)
            error_tracker = ErrorTracker(
                max_consecutive_errors=args.max_consecutive_errors, window_size=window_size
            )

        with results_path.open("w", encoding="utf-8") as f:
            for i, sample in enumerate(dataset):
                print(f"  Example {i + 1}/{len(dataset)}...")
                question = str(sample.get("question", ""))
                answer = sample.get("answer")  # may be string (JSON) or dict

                record: Dict[str, Any] = {
                    "index": i,
                    "prompt": question,
                    "answer": answer,
                }

                # Get fixture path if available
                fixture_path = None
                if isinstance(answer, str):
                    try:
                        answer_obj = json.loads(answer)
                        fixture_path = answer_obj.get("fixture_path")
                    except json.JSONDecodeError:
                        pass
                elif isinstance(answer, dict):
                    fixture_path = answer.get("fixture_path")

                # Run multi-turn evaluation
                try:
                    result = asyncio.run(
                        run_multiturn_evaluation(
                            client,
                            env,
                            effective_model,  # Use the effective model name (mapped for OpenRouter)
                            question,
                            answer,
                            max_turns=args.max_turns,
                            temperature=args.temperature,
                            max_tokens=args.max_tokens,
                            fixture_path=fixture_path,
                        )
                    )

                    record["completion"] = result["completion"]
                    record["tool_interactions"] = result.get("tool_interactions", [])
                    record["turns_used"] = result.get("turns_used", 0)

                    if "error" in result:
                        record["completion_error"] = result["error"]
                        # Track the error for early stopping
                        if error_tracker:
                            error_tracker.record_error(result["error"], index=i)
                    else:
                        # Track success
                        if error_tracker:
                            error_tracker.record_success()

                except EarlyStopError as e:
                    print(f"\n✗ Early stopping triggered for {model}:")
                    print(f"  {e}")
                    if error_tracker:
                        stats = error_tracker.get_stats()
                        print(f"  Stats: {stats['total_errors']}/{stats['total_samples']} samples failed")
                    break  # Exit the dataset loop

                # Compute rewards
                text = result["completion"]
                try:
                    r_main = float(reward_config_auditing(text, answer))
                except Exception as e:
                    r_main = 0.0
                    record["reward_error"] = str(e)
                try:
                    r_format = float(format_reward(text, answer=answer))
                except Exception:
                    r_format = 0.0

                record["rewards"] = {
                    "reward_config_auditing": r_main,
                    "format_reward": r_format,
                }

                # Report tool usage
                if include_tools and record["tool_interactions"]:
                    tools_used = list(set(t["tool"] for t in record["tool_interactions"]))
                    print(f"    Tools used: {tools_used}")
                    print(f"    Turns: {record['turns_used']}")

                f.write(json.dumps(record) + "\n")

        print(f"✓ Saved artifacts for {model} -> {run_dir}")


if __name__ == "__main__":
    main()
