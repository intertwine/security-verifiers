"""Template for creating a new security verifier environment.

Copy this file to environments/<env-name>/<env_name_with_underscores>.py
and fill in the implementation details.
"""

# pylint: disable=fixme
from __future__ import annotations

import verifiers as vf
from datasets import Dataset


class MyParser(vf.Parser):
    """Parser to extract and validate model responses."""

    def parse_answer(self, completion: str) -> str:
        """Extract the answer from the model's response.

        Args:
            completion: The raw model completion/response.

        Returns:
            The extracted answer in standard format.
        """
        # TODO: Implement parsing logic
        # Example: extract classification label, code fix, etc.
        cleaned = completion.strip()
        return cleaned

    def get_format_reward_func(self):
        """Return a format reward function that checks response format."""

        def format_reward(
            completion,
            answer="",  # pylint: disable=unused-argument
            **kwargs,  # pylint: disable=unused-argument
        ):
            """Reward proper response format."""
            # Extract response text from completion
            if isinstance(completion, list):
                response = completion[-1]["content"] if completion else ""
            else:
                response = str(completion)

            # TODO: Implement format checking logic using 'response' variable
            # Return 1.0 for perfect format, 0.5 for partial, 0.0 for poor
            _ = response  # Use response variable (to be implemented)
            return 1.0

        return format_reward


def reward_correct_answer(
    completion,
    answer: str = "",
    parser: vf.Parser | None = None,
    **kwargs,  # pylint: disable=unused-argument
) -> float:
    """Reward function that checks if the parsed answer is correct.

    Args:
        completion: The model's response.
        answer: The ground truth answer from the dataset.
        parser: The parser instance to extract the answer.
        **kwargs: Additional arguments (prompt, state, etc).

    Returns:
        Reward value between 0.0 and 1.0.
    """
    # Extract the response text from completion
    if isinstance(completion, list):
        response = completion[-1]["content"] if completion else ""
    else:
        response = str(completion)

    # Use parser to extract answer if available
    if parser:
        predicted = parser.parse_answer(response)
    else:
        predicted = response.strip()

    # TODO: Implement correctness checking logic
    # This could be exact match, semantic similarity, etc.
    if not predicted or not answer:
        return 0.0
    return 1.0 if predicted.lower() == answer.lower() else 0.0


def load_environment(
    dataset_name: str = "synthetic",  # pylint: disable=unused-argument
    max_examples: int = 100,
) -> vf.SingleTurnEnv:  # or vf.MultiTurnEnv for multi-turn tasks
    """Load the environment.

    This is the main entry point that will be called by the verifiers framework.

    Args:
        dataset_name: Name of the dataset to use.
        max_examples: Maximum number of examples to use from the dataset.

    Returns:
        A configured verifiers environment.
    """
    # Load or create dataset
    try:
        # Try to load from HuggingFace or other source
        dataset = Dataset.from_list([])  # TODO: Load actual dataset
    except (FileNotFoundError, ConnectionError, ValueError) as e:
        print(f"Failed to load dataset: {e}")
        print("Using synthetic dataset for testing.")

        # Create synthetic dataset for testing
        examples = [
            {"question": "Example input 1", "answer": "Expected output 1"},
            {"question": "Example input 2", "answer": "Expected output 2"},
            # TODO: Add more synthetic examples
        ]
        dataset = Dataset.from_list(examples[:max_examples])

    # Create parser
    parser = MyParser()

    # Create rubric with multiple reward functions and weights
    rubric = vf.Rubric(
        funcs=[
            reward_correct_answer,
            parser.get_format_reward_func(),
        ],
        weights=[1.0, 0.2],  # Adjust weights based on importance
    )

    # Return configured environment
    return vf.SingleTurnEnv(
        name="my-environment-name",
        description="Brief description of what this environment tests.",
        dataset=dataset,
        parser=parser,
        rubric=rubric,
        system_prompt=("You are a helpful assistant. TODO: Add specific instructions for the task."),
    )
