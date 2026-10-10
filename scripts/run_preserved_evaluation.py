#!/usr/bin/env python3
"""Bounded, resumable Stage B runner; preparation is the default, never paid execution.

Reuse E2's adapter functions without its deterministic fallback. Raw responses are
retained for the common evaluator; no historical reward or completion verdict is
manufactured here. A reservation remains charged after errors or interruption.
"""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import math
import os
import re
import shutil
import signal
import subprocess
import sys
import time
from contextlib import contextmanager
from decimal import Decimal
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


class Blocked(ValueError):
    """An execution prerequisite or envelope is unsatisfied."""


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def encode(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def append(path: Path, row: dict) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(encode(row) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def read_rows(path: Path) -> list[dict]:
    return (
        [json.loads(line) for line in path.read_text().splitlines() if line.strip()] if path.exists() else []
    )


def number(value: Any, name: str) -> Decimal:
    try:
        parsed = Decimal(str(value))
    except Exception as exc:
        raise Blocked(f"{name} must be finite and nonnegative") from exc
    if not parsed.is_finite() or parsed < 0:
        raise Blocked(f"{name} must be finite and nonnegative")
    return parsed


def verify_evidence(evidence: dict, base: Path, kind: str, parse: bool = True) -> Any:
    if not isinstance(evidence, dict) or not evidence.get("path") or not evidence.get("sha256"):
        raise Blocked(f"{kind}: hashed evidence receipt required")
    path = base / evidence["path"]
    if not path.is_file() or digest(path) != evidence["sha256"]:
        raise Blocked(f"{kind}: evidence absent or checksum differs")
    return json.loads(path.read_text()) if parse else path


def fixture_content(row: dict) -> tuple[str, str]:
    """Extract explicit wrappers, otherwise require recognizable raw config."""
    content = row["question"]
    if content.startswith("File path:"):
        match = re.fullmatch(
            r"File path:[^\n]+\n\nConfiguration:\n```(?:text|yaml|hcl)?\n(.*)\n```", content, re.S
        )
        if not match:
            raise Blocked("Ambiguous configuration wrapper")
        content = match.group(1)
    stripped = content.lstrip()
    import yaml

    try:
        documents = list(yaml.safe_load_all(content))
    except yaml.YAMLError:
        documents = []
    if documents and all(
        isinstance(d, dict) and d.get("apiVersion") and d.get("kind") for d in documents if d
    ):
        if any(documents):
            return content, "k8s"
    # Terraform can begin with copyright/annotation comments. Strip only a
    # leading comment prefix for type recognition; preserve original bytes.
    stripped = re.sub(r"\A(?:(?:#[^\n]*|//[^\n]*)\n\s*|/\*.*?\*/\s*)+", "", stripped, flags=re.S)
    if re.match(r"(?:resource|provider|module|variable|locals|data|output|terraform)\b", stripped):
        return content, "tf"
    raise Blocked("Configuration type is ambiguous")


def recognizable_fixture(row: dict) -> bool:
    try:
        fixture_content(row)
        return True
    except Blocked:
        return False


def validate(packet: dict, base: Path, launch: bool = False) -> dict:
    """Validate primary matrix offline; unresolved evidence is an explicit blocker."""
    if packet.get("schema_version") != 1:
        raise Blocked("Unsupported packet schema")
    if set(packet.get("environments", {})) != {"e1", "e2"}:
        raise Blocked("Only primary E1/E2 blocks are permitted")
    expected = {"e1": (200, ["base", "exec", "judge"], 2048), "e2": (100, ["base", "exec"], 4096)}
    episodes = 0
    missing = []
    datasets = {}
    for env, (count, roles, output_cap) in expected.items():
        block = packet["environments"][env]
        if block.get("environment") != env:
            raise Blocked("Environment key differs from block identity")
        if block["case_count"] != count or [p["role"] for p in block["policies"]] != roles:
            raise Blocked(f"{env}: primary matrix must be {count} cases and {roles}")
        limits = block["limits"]
        for key in (
            "input_tokens_per_request",
            "output_tokens_per_episode",
            "requests_per_episode",
            "turns_per_episode",
            "tool_calls_per_episode",
            "tool_seconds",
            "episode_seconds",
            "request_seconds",
        ):
            if not isinstance(limits[key], int) or limits[key] < (
                0 if key == "tool_calls_per_episode" else 1
            ):
                raise Blocked(f"{env}: invalid {key}")
        if limits["output_tokens_per_episode"] != output_cap or limits["requests_per_episode"] > 5:
            raise Blocked(f"{env}: token/request planning bound exceeded")
        if limits["turns_per_episode"] > (1 if env == "e1" else 5):
            raise Blocked(f"{env}: turn cap exceeded")
        if limits["tool_calls_per_episode"] > (0 if env == "e1" else 3):
            raise Blocked(f"{env}: tool cap exceeded")
        if limits["tool_seconds"] > 30 or limits["episode_seconds"] > 120:
            raise Blocked(f"{env}: time planning bound exceeded")
        for key in ("dataset", "manifest", "system_prompt_file"):
            if not block.get(key) or not (base / block[key]).is_file():
                missing.append(f"{env}.{key}")
        if block.get("dataset") and (base / block["dataset"]).is_file():
            path = base / block["dataset"]
            rows = read_rows(path)
            ids = [r.get("case_id") for r in rows]
            if len(rows) != count or len(set(ids)) != count or any(not i for i in ids):
                raise Blocked(f"{env}: case count or identities invalid")
            if any(not isinstance(r.get("question"), str) or "answer" not in r for r in rows):
                raise Blocked(f"{env}: question/answer contract invalid")
            if any(r["case_id"] != hashlib.sha256(r["question"].encode()).hexdigest() for r in rows):
                raise Blocked(f"{env}: case IDs must hash exact prompts")
            datasets[env] = rows
            if env == "e2":
                ambiguous = sum(1 for row in rows if not recognizable_fixture(row))
                if ambiguous:
                    missing.append(f"e2.unsupported_configuration_inputs:{ambiguous}")
            if block.get("manifest") and (base / block["manifest"]).is_file():
                manifest = json.loads((base / block["manifest"]).read_text())
                if manifest["dataset_sha256"] != digest(path):
                    raise Blocked(f"{env}: frozen data checksum mismatch")
                if manifest.get("heldout_verified") is not True:
                    missing.append(f"{env}.verified_train_exclusion")
        for policy in block["policies"]:
            for key in ("model", "base_revision", "identity_evidence"):
                if not policy.get(key):
                    missing.append(f"{env}.{policy['role']}.{key}")
            revision = policy.get("base_revision")
            if revision and not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", revision):
                raise Blocked(f"{env}: base revision must be immutable digest")
            evidence = policy.get("identity_evidence")
            if evidence:
                identity = verify_evidence(evidence, base, "model identity")
                for key in ("model", "base_revision", "adapter_sha256"):
                    if identity.get(key) != policy.get(key):
                        raise Blocked("Identity evidence differs from selected policy")
            if policy["role"] != "base" and not policy.get("adapter_sha256"):
                missing.append(f"{env}.{policy['role']}.adapter_sha256")
        review = block.get("scientific_review_evidence")
        if not review:
            missing.append(f"{env}.scientific_review_evidence")
        else:
            reviewed = verify_evidence(review, base, "scientific review")
            if reviewed.get("status") != "approved" or not reviewed.get("reviewer"):
                raise Blocked("Scientific review has not approved launch")
            if not block.get("dataset") or reviewed.get("dataset_sha256") != digest(base / block["dataset"]):
                raise Blocked("Scientific review dataset identity differs")
            if (
                reviewed.get("heldout_verified") is not True
                or reviewed.get("case_independence_verified") is not True
            ):
                raise Blocked("Scientific review must verify exclusion and case independence")
            membership = verify_evidence(
                reviewed.get("training_membership_evidence"), base, "training membership"
            )
            expected_runs = {p.get("training_run_id") for p in block["policies"] if p["role"] != "base"}
            if None in expected_runs or not expected_runs.issubset(
                set(membership.get("training_run_ids", []))
            ):
                raise Blocked("Training membership does not cover selected adapters")
            train_ids = membership.get("case_ids", [])
            if not train_ids or len(train_ids) != len(set(train_ids)):
                raise Blocked("Full training membership IDs absent or duplicated")
            if any(not isinstance(i, str) or not re.fullmatch(r"[0-9a-f]{64}", i) for i in train_ids):
                raise Blocked("Training membership must use exact prompt digests")
            if set(train_ids).intersection(r["case_id"] for r in datasets.get(env, [])):
                raise Blocked("Training and held-out prompts overlap")
        if block.get("case_independence_verified") is not True:
            missing.append(f"{env}.case_independence_verified")
        revisions = {policy.get("base_revision") for policy in block["policies"]}
        if len(revisions - {None}) > 1:
            raise Blocked(f"{env}: base revisions differ across policies")
        for policy in block["policies"]:
            sha = policy.get("adapter_sha256")
            if sha and not re.fullmatch(r"[0-9a-f]{64}", sha):
                raise Blocked(f"{env}: invalid adapter checksum")
        if env == "e2":
            rules = block.get("semgrep_rules")
            if not rules:
                missing.append("e2.pinned_semgrep_rules")
            else:
                verify_evidence(rules, base, "Semgrep rules", parse=False)
            if set(block.get("tool_versions", {})) != {"kube-linter", "semgrep", "opa"}:
                missing.append("e2.tool_versions")
            elif launch:
                for tool, expected_version in block["tool_versions"].items():
                    if tool not in ("kube-linter", "semgrep", "opa") or not shutil.which(tool):
                        raise Blocked("Required real scanner unavailable")
                    argument = "--version" if tool == "semgrep" else "version"
                    proc = subprocess.run([tool, argument], capture_output=True, timeout=10, check=False)
                    actual = (proc.stdout or proc.stderr).decode().strip()
                    if proc.returncode or actual != expected_version:
                        raise Blocked("Scanner version differs from launch packet")
        episodes += count * len(roles)
    billing = packet["billing"]
    cap = number(billing["hard_cap_usd"], "hard_cap_usd")
    rates = [
        number(billing[k], k)
        for k in ("input_usd_per_million", "output_usd_per_million")
        if billing.get(k) is not None
    ]
    if cap <= 0:
        missing.append("billing.hard_cap_usd")
    for key in ("workspace_id", "quote_source", "quote_checked_at", "endpoint", "api_key_env"):
        if not billing.get(key):
            missing.append(f"billing.{key}")
    if len(rates) != 2:
        missing.append("billing.token_rates")
    if billing.get("fixed_charges_usd") is None:
        missing.append("billing.fixed_charges_usd")
    if billing.get("endpoint") and billing["endpoint"].rstrip("/") != "https://api.pinference.ai/api/v1":
        raise Blocked("Only the official Prime inference endpoint may receive Prime credentials")
    headers = billing.get("request_headers", {})
    if headers.get("X-Prime-Team-ID") != billing.get("workspace_id"):
        missing.append("billing.team_header")
    if set(headers) - {"X-Prime-Team-ID"}:
        raise Blocked("Only explicit team billing header is allowed")
    if billing.get("workspace_scope_verified") is not True:
        missing.append("billing.workspace_scope_verified")
    if not billing.get("token_only_billing_verified"):
        missing.append("billing.token_only_billing_verified")
    if not packet.get("launch_ready"):
        missing.append("launch_ready")
    if launch and missing:
        raise Blocked("Launch blocked: " + ", ".join(missing))
    return {
        "episodes": episodes,
        "output_token_bound": 2048000,
        "launch_blockers": missing,
        "datasets": datasets,
    }


class Ledger:
    """Worst-case accounting: never refund an uncertain or failed request."""

    def __init__(self, path: Path, billing: dict):
        self.path = path
        self.cap = number(billing["hard_cap_usd"], "hard cap")
        self.input_rate = number(billing["input_usd_per_million"], "input rate")
        self.output_rate = number(billing["output_usd_per_million"], "output rate")
        self.spent = sum((Decimal(row["reserved_usd"]) for row in read_rows(path)), Decimal(0))
        if not path.exists():
            self.reserve("fixed", number(billing["fixed_charges_usd"], "fixed charges"))

    def reserve(self, identity: str, cost: Decimal) -> None:
        if self.spent + cost > self.cap:
            raise Blocked("Hard spend envelope exhausted before request")
        append(self.path, {"identity": identity, "reserved_usd": str(cost)})
        self.spent += cost

    def request(self, identity: str, input_cap: int, output_cap: int) -> None:
        self.reserve(identity, (self.input_rate * input_cap + self.output_rate * output_cap) / 1000000)


def input_upper_bound(messages: list, tools: list) -> int:
    """UTF-8 byte upper bound plus conservative chat framing; not a tokenizer estimate."""
    return len(encode({"messages": messages, "tools": tools}).encode()) + 1024 * (len(messages) + 1)


def tool_schema() -> list:
    from scripts.eval_config_verification import convert_tools_to_openai_format
    from sv_env_config_verification import run_kubelinter, run_opa, run_semgrep

    return convert_tools_to_openai_format([run_kubelinter, run_semgrep, run_opa])


def run_tool(name: str, fixture: Path, timeout: float, rules: Path | None = None) -> Any:
    """Kill the complete tool process group on timeout; never execute model-supplied paths."""
    command = [
        sys.executable,
        str(Path(__file__).resolve()),
        "--tool-worker",
        name,
        str(fixture),
        str(rules or ""),
    ]
    proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
    try:
        stdout, _ = proc.communicate(timeout=timeout)
    except BaseException:
        os.killpg(proc.pid, signal.SIGKILL)
        proc.communicate()
        raise Blocked("Tool timeout or interruption") from None
    if proc.returncode:
        raise Blocked("Scanner failed; fallback disabled")
    return json.loads(stdout)


def tool_worker(name: str, fixture: str, rules: str) -> None:
    # Direct adapters: no silent hosted-harness fallback on scanner failure.
    sys.path.insert(0, str(ROOT / "environments/sv-env-config-verification"))
    from adapters.kubelinter_adapter import kubelinter_lint
    from adapters.opa_adapter import opa_eval
    from adapters.semgrep_adapter import semgrep_scan

    functions = {"run_kubelinter": kubelinter_lint, "run_semgrep": semgrep_scan, "run_opa": opa_eval}
    if name not in functions:
        raise Blocked("Unknown tool")
    if name == "run_opa":
        if Path(fixture).suffix == ".tf":
            raise Blocked("OPA Terraform parsing unavailable")
        import yaml

        policies = ROOT / "environments/sv-env-config-verification/policies"
        findings = opa_eval(
            yaml.safe_load(Path(fixture).read_text()),
            [policies / "lib.rego", policies / "kubernetes_security.rego"],
        )
    elif name == "run_semgrep":
        if not rules:
            raise Blocked("Frozen local Semgrep rules required")
        findings = semgrep_scan([fixture], rules=rules)
    else:
        findings = functions[name]([fixture])
    print(encode([f.model_dump() if hasattr(f, "model_dump") else vars(f) for f in findings]))


def episode(
    client: Any, policy: dict, row: dict, block: dict, ledger: Ledger, folder: Path, identity: str
) -> dict:
    limits = block["limits"]
    deadline = time.monotonic() + limits["episode_seconds"]
    prompt = (folder / "system_prompt.txt").read_text()
    question = row["question"]
    tools = []
    fixture = None
    if block["environment"] == "e2":
        content, fixture_type = fixture_content(row)
        fixture = folder.parent / "fixtures" / (row["case_id"] + (".tf" if fixture_type == "tf" else ".yaml"))
        fixture.parent.mkdir(exist_ok=True)
        fixture.write_text(content)
        prompt += f"\n\nFile path: {fixture.resolve()}"
        tools = tool_schema()
        if fixture_type == "tf":
            tools = [t for t in tools if t["function"]["name"] == "run_semgrep"]
    messages = [{"role": "system", "content": prompt}, {"role": "user", "content": question}]
    result = {
        "case_id": row["case_id"],
        "prompt": question,
        "answer": row["answer"],
        "info": row.get("info"),
        "completion": "",
        "tool_interactions": [],
        "responses": [],
        "status": "limits_reached",
    }
    remaining = limits["output_tokens_per_episode"]
    calls = 0
    for turn in range(min(limits["turns_per_episode"], limits["requests_per_episode"])):
        time_left = deadline - time.monotonic()
        if time_left <= 0 or remaining <= 0:
            break
        if input_upper_bound(messages, tools) > limits["input_tokens_per_request"]:
            result["status"] = "input_cap"
            break
        ledger.request(f"{identity}:{turn}", limits["input_tokens_per_request"], remaining)
        kwargs = {
            "model": policy["model"],
            "messages": messages,
            "max_tokens": remaining,
            "temperature": 0,
            "timeout": min(time_left, limits["request_seconds"]),
        }
        if tools:
            kwargs.update(tools=tools, tool_choice="auto")
        response = client.chat.completions.create(**kwargs)
        raw = response.model_dump(mode="json")
        append(folder / "requests.jsonl", {"identity": identity, "turn": turn, "response": raw})
        result["responses"].append(raw)
        usage = raw.get("usage") or {}
        used = usage.get("completion_tokens")
        if not isinstance(used, int) or used < 0 or used > remaining:
            raise Blocked("Provider token usage absent or outside request cap")
        if usage.get("prompt_tokens", math.inf) > limits["input_tokens_per_request"]:
            raise Blocked("Provider input usage exceeded conservative bound")
        remaining -= used
        message = raw["choices"][0]["message"]
        messages.append(message)
        requested = message.get("tool_calls") or []
        if not requested:
            result.update(completion=message.get("content") or "", status="completed", turns_used=turn + 1)
            break
        for call in requested:
            if calls >= limits["tool_calls_per_episode"]:
                result["status"] = "tool_cap"
                return result
            function = call["function"]
            # Validate shape but restrict all paths to the retained fixture.
            args = json.loads(function["arguments"])
            if set(args) != {"paths"} or not isinstance(args["paths"], list):
                raise Blocked("Tool arguments outside paths contract")
            time_left = deadline - time.monotonic()
            if time_left <= 0:
                return result
            allowed = {t["function"]["name"] for t in tools}
            if function["name"] not in allowed:
                raise Blocked("Tool outside fixture capability contract")
            rules = (block.get("semgrep_rules") or {}).get("path")
            observation = run_tool(
                function["name"],
                fixture,
                min(limits["tool_seconds"], time_left),
                ROOT / rules if rules else None,
            )
            calls += 1
            result["tool_interactions"].append(
                {
                    "tool": function["name"],
                    "arguments": {"paths": [str(fixture)]},
                    "observation": observation,
                    "backend": "adapter",
                }
            )
            messages.append({"role": "tool", "tool_call_id": call["id"], "content": encode(observation)})
    return result


@contextmanager
def wall_deadline(seconds: int):
    """Enforce aggregate episode wall time, including networking and tools."""

    def expired(_signum, _frame):
        raise Blocked("Episode wall time exhausted")

    previous = signal.signal(signal.SIGALRM, expired)
    signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)


def source_fingerprints(packet: dict, base: Path) -> dict:
    result = {
        f"{env}.{key}": digest(base / block[key])
        for env, block in packet["environments"].items()
        for key in ("dataset", "manifest", "system_prompt_file")
    }

    def receipts(value, prefix):
        if isinstance(value, dict):
            if "path" in value and "sha256" in value:
                result[prefix] = digest(base / value["path"])
            for key, nested in value.items():
                receipts(nested, f"{prefix}.{key}")
        elif isinstance(value, list):
            for index, nested in enumerate(value):
                receipts(nested, f"{prefix}.{index}")

    receipts(packet, "packet")
    result["evaluator.source"] = digest(Path(__file__).resolve())
    policy_root = ROOT / "environments/sv-env-config-verification"
    for path in sorted(policy_root.rglob("*.py")) + sorted((policy_root / "policies").glob("*.rego")):
        if ".venv" not in path.parts:
            result[str(path.relative_to(ROOT))] = digest(path)
    # Freeze nested membership receipts referenced by the independent review.
    for env, block in packet["environments"].items():
        review = block.get("scientific_review_evidence")
        if review:
            receipts(json.loads((base / review["path"]).read_text()), f"{env}.review")
    return result


def execute(packet: dict, base: Path, output: Path, checked: dict) -> None:
    output.mkdir(parents=True, exist_ok=True)
    with (output / ".lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        fingerprint = hashlib.sha256(encode(packet).encode()).hexdigest()
        meta = output / "packet.json"
        if meta.exists() and json.loads(meta.read_text()) != packet:
            raise Blocked("Resume packet differs from frozen packet")
        source_meta = output / "sources.json"
        current_sources = source_fingerprints(packet, base)
        if source_meta.exists() and json.loads(source_meta.read_text()) != current_sources:
            raise Blocked("Resume source files differ from frozen fingerprints")
        meta.write_text(encode(packet))
        source_meta.write_text(encode(current_sources))
        from openai import OpenAI

        billing = packet["billing"]
        key = os.environ.get(billing["api_key_env"])
        if not key:
            raise Blocked("Required credential unavailable")
        client = OpenAI(
            api_key=key,
            base_url=billing["endpoint"],
            max_retries=0,
            default_headers=billing.get("request_headers", {}),
        )
        ledger = Ledger(output / "budget.jsonl", billing)
        attempts = output / "attempts.jsonl"
        attempted = {r["identity"] for r in read_rows(attempts)}
        for env, block in packet["environments"].items():
            for policy in block["policies"]:
                folder = output / f"{env}-{policy['role']}"
                folder.mkdir(exist_ok=True)
                (folder / "metadata.json").write_text(
                    encode(
                        {
                            "environment": env,
                            "policy": policy,
                            "packet_sha256": fingerprint,
                            "dataset_sha256": digest(base / block["dataset"]),
                            "workspace_id": billing["workspace_id"],
                            "limits": block["limits"],
                            "tool_versions": block.get("tool_versions"),
                        }
                    )
                )
                (folder / "system_prompt.txt").write_text((base / block["system_prompt_file"]).read_text())
                for index, row in enumerate(checked["datasets"][env]):
                    identity = f"{env}:{policy['role']}:{row['case_id']}"
                    if identity in attempted:
                        continue  # Ambiguous interruption remains preserved, never retried automatically.
                    append(attempts, {"identity": identity, "status": "started"})
                    try:
                        with wall_deadline(block["limits"]["episode_seconds"]):
                            result = episode(client, policy, row, block, ledger, folder, identity)
                    except Exception as exc:
                        append(
                            folder / "results.jsonl",
                            {
                                "index": index,
                                "case_id": row["case_id"],
                                "prompt": row["question"],
                                "answer": row["answer"],
                                "completion": "",
                                "status": "failed",
                                "error_type": type(exc).__name__,
                            },
                        )
                        raise Blocked("Evaluation stopped; retained failure and budget reservation") from None
                    result["index"] = index
                    append(folder / "results.jsonl", result)
                    append(attempts, {"identity": identity, "status": "finished"})
                    attempted.add(identity)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet", type=Path)
    parser.add_argument("--output", type=Path, default=ROOT / "outputs/evals/preserved-primary-20261010")
    parser.add_argument(
        "--execute", action="store_true", help="Paid execution; requires complete launch packet"
    )
    parser.add_argument(
        "--tool-worker", nargs=3, metavar=("NAME", "FIXTURE", "RULES"), help=argparse.SUPPRESS
    )
    args = parser.parse_args()
    try:
        if args.tool_worker:
            tool_worker(*args.tool_worker)
            return
        if not args.packet:
            parser.error("--packet required")
        packet = json.loads(args.packet.read_text())
        checked = validate(packet, ROOT, launch=args.execute)
        if args.execute:
            execute(packet, ROOT, args.output, checked)
        print(encode({key: value for key, value in checked.items() if key != "datasets"}))
    except (Blocked, OSError, KeyError, json.JSONDecodeError) as exc:
        # Only our controlled prerequisite messages; do not echo provider exception bodies or credentials.
        message = str(exc) if isinstance(exc, Blocked) else type(exc).__name__
        raise SystemExit(message) from None


if __name__ == "__main__":
    main()
