from __future__ import annotations

import verifiers as vf
from datasets import Dataset, load_dataset


def reward_label_match(prompt: str, completion: str, answer: str, **kwargs) -> float:
    """Reward function for exact classification match."""
    predicted = completion.strip().lower()
    actual = answer.strip().lower()
    return 1.0 if predicted == actual else 0.0


def transform_dataset(raw_dataset: Dataset, max_examples: int | None) -> Dataset:
    """Transform raw dataset to SingleTurnEnv format."""

    def transform_example(example):
        # The IoT-23 dataset has many columns. We'll create a simple
        # string representation of the most relevant ones for the prompt.
        # This can be refined to be more descriptive.
        prompt_text = (
            f"Log Entry: id.orig_h={example.get('id.orig_h')}, "
            f"id.orig_p={example.get('id.orig_p')}, "
            f"id.resp_h={example.get('id.resp_h')}, "
            f"id.resp_p={example.get('id.resp_p')}, "
            f"proto={example.get('proto')}, "
            f"service={example.get('service')}, "
            f"detailed-label={example.get('detailed-label')}"
        )

        # The 'label' column is 'Malicious' or 'Benign'
        return {
            "prompt": prompt_text,
            "answer": example.get("label", "Benign"),
        }

    transformed = raw_dataset.map(transform_example)

    if max_examples and len(transformed) > max_examples:
        transformed = transformed.select(range(max_examples))

    return transformed


def load_environment(
    dataset_name: str = "19kmunz/iot-23-preprocessed-minimumcolumns",
    max_examples: int = 1000,
) -> vf.SingleTurnEnv:
    """Load the Network Logs Anomaly Detection environment.

    This environment is a single-turn classification task where the model
    inspects a network log entry and determines whether it is malicious or benign.

    Args:
        dataset_name: HuggingFace dataset name for network logs.
        max_examples: Maximum number of examples to use from the dataset.

    Returns:
        A Verifiers SingleTurnEnv configured for the task.
    """
    try:
        # The `load_dataset` function with a `split` argument returns a `Dataset` object.
        # We assert the type to satisfy the linter and ensure correctness.
        dataset = load_dataset(dataset_name, split="train")
        assert isinstance(dataset, Dataset), "Loaded dataset is not of type Dataset"
        dataset = transform_dataset(dataset, max_examples)
    except Exception as e:
        print(f"Failed to load dataset '{dataset_name}': {e}")
        print("Falling back to a small synthetic dataset.")
        examples = [
            {
                "prompt": (
                    "Log Entry: id.orig_h=192.168.1.103, id.orig_p=52089, "
                    "id.resp_h=192.168.1.1, id.resp_p=53, proto=udp, service=dns, "
                    "detailed-label=Benign"
                ),
                "answer": "Benign",
            },
            {
                "prompt": (
                    "Log Entry: id.orig_h=192.168.1.103, id.orig_p=44331, "
                    "id.resp_h=192.168.1.1, id.resp_p=443, proto=tcp, service=https, "
                    "detailed-label=Benign"
                ),
                "answer": "Benign",
            },
            {
                "prompt": (
                    "Log Entry: id.orig_h=192.168.1.104, id.orig_p=37356, "
                    "id.resp_h=192.168.1.1, id.resp_p=80, proto=tcp, service=http, "
                    "detailed-label=Attack"
                ),
                "answer": "Malicious",
            },
        ]
        dataset = Dataset.from_list(examples)

    rubric = vf.Rubric(
        funcs=[reward_label_match],
        weights=[1.0],
    )

    return vf.SingleTurnEnv(
        dataset=dataset,
        rubric=rubric,
        system_prompt=(
            "You are a network security analyst. Analyze the provided network log entry "
            "and classify it as either 'Malicious' or 'Benign'. Respond with only the "
            "classification label."
        ),
    )
