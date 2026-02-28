#!/usr/bin/env python3
"""Debug script to test E1 reward functions with various completion formats.

Run with: SV_DEBUG=1 python scripts/debug_e1_rewards.py

This simulates what the hosted system does and logs the reward pipeline
to identify why hosted runs get 0.0 reward while local gives 1.79.
"""

import logging
import os
import sys

# Enable debug logging
os.environ["SV_DEBUG"] = "1"
logging.basicConfig(level=logging.WARNING, format="%(name)s | %(message)s")

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sv_shared.parsers import JsonClassificationParser
from sv_shared.rewards import reward_accuracy, reward_calibration, reward_asymmetric_cost

parser = JsonClassificationParser(allowed_labels=["Benign", "Malicious", "Abstain"])

# Test cases: different completion formats that might be seen
test_cases = [
    # Format 1: Raw string (local eval typical)
    {
        "name": "raw_json_string",
        "completion": '{"label": "Malicious", "confidence": 0.95}',
        "answer": "Malicious",
    },
    # Format 2: List of message dicts (verifiers standard)
    {
        "name": "list_of_dicts",
        "completion": [{"role": "assistant", "content": '{"label": "Malicious", "confidence": 0.95}'}],
        "answer": "Malicious",
    },
    # Format 3: Markdown-wrapped JSON
    {
        "name": "markdown_wrapped",
        "completion": [{"role": "assistant", "content": '```json\n{"label": "Malicious", "confidence": 0.95}\n```'}],
        "answer": "Malicious",
    },
    # Format 4: Integer answer (ClassLabel not coerced)
    {
        "name": "int_answer",
        "completion": [{"role": "assistant", "content": '{"label": "Malicious", "confidence": 0.95}'}],
        "answer": 1,  # ClassLabel int
    },
    # Format 5: Empty completion
    {
        "name": "empty_completion",
        "completion": [],
        "answer": "Malicious",
    },
    # Format 6: Thinking model format (with reasoning prefix)
    {
        "name": "thinking_model",
        "completion": [{"role": "assistant", "content": '<think>Let me analyze...</think>\n{"label": "Malicious", "confidence": 0.9}'}],
        "answer": "Malicious",
    },
    # Format 7: Qwen chat template wrapping
    {
        "name": "qwen_wrapped",
        "completion": [{"role": "assistant", "content": 'Based on the network log analysis:\n\n{"label": "Malicious", "confidence": 0.85, "rationale": "Port scan detected"}'}],
        "answer": "Malicious",
    },
]

print("=" * 70)
print("E1 Reward Function Debug Test")
print("=" * 70)

for tc in test_cases:
    print(f"\n--- Test: {tc['name']} ---")
    print(f"  completion type: {type(tc['completion']).__name__}")
    print(f"  answer: {tc['answer']!r} (type={type(tc['answer']).__name__})")

    acc = reward_accuracy(completion=tc["completion"], answer=tc["answer"], parser=parser)
    cal = reward_calibration(completion=tc["completion"], answer=tc["answer"], parser=parser)
    cost = reward_asymmetric_cost(completion=tc["completion"], answer=tc["answer"], parser=parser)

    fmt = parser.get_format_reward_func()(completion=tc["completion"])

    total_real = acc * 1.0 + fmt * 0.1 + cal * 0.2 + cost * 0.5
    print(f"  REWARDS: accuracy={acc:.2f}, format={fmt:.2f}, calibration={cal:.2f}, asymmetric_cost={cost:.2f}")
    print(f"  TOTAL (weighted): {total_real:.2f}")

print("\n" + "=" * 70)
print("Testing dataset loading from Hub...")
print("=" * 70)

try:
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                     "environments", "sv-env-network-logs"))

    # Load .env.secrets if available
    env_secrets = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env.secrets")
    if os.path.exists(env_secrets):
        with open(env_secrets) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, val = line.partition("=")
                    os.environ.setdefault(key.strip(), val.strip())

    from sv_env_network_logs import load_environment
    env = load_environment(max_examples=5)
    print(f"\nEnvironment loaded successfully: {env.name if hasattr(env, 'name') else 'ok'}")
except Exception as e:
    print(f"\nFailed to load environment: {e}")
    import traceback
    traceback.print_exc()
