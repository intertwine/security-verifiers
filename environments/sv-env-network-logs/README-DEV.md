# Development Guide for sv-env-network-logs

This document contains information for developers working on the sv-env-network-logs environment.

## Local Development Setup

To set up the environment for local development and testing, install it in editable mode with the `dev` dependencies. From the repository root, after creating and activating a virtual environment:

```bash
# Install the package and development dependencies
uv pip install -e 'environments/sv-env-network-logs[dev]'
```

This will install all necessary dependencies for running the environment and its tests, including `verifiers[dev]`.

## Local Testing

To test the environment locally, you can use the `vf-eval` command from the `verifiers` library. This will load the environment and run a few examples using a specified model.

```bash
# Evaluate the environment with a small model
vf-eval sv-env-network-logs --model gpt-5-mini --num-examples 3
```

### Configuration Notes

- **API Keys**: The evaluation requires API keys to be set as environment variables. Create a `.env` file in the project root with:

  ```bash
  OPENAI_API_KEY=your-openai-api-key-here
  HF_TOKEN=your-huggingface-token-here  # Optional, for dataset access
  ```

  Then load the environment variables before running `vf-eval`:

  ```bash
  # Load .env file and run evaluation
  set -a && source .env && set +a && vf-eval sv-env-network-logs --model gpt-5-mini --num-examples 3
  ```

- **Hugging Face Authentication**: Loading the `19kmunz/iot-23-preprocessed-minimumcolumns` dataset requires authentication. If you see a `401 Unauthorized` error, you need to log in to Hugging Face or set the `HF_TOKEN` environment variable:

  ```bash
  huggingface-cli login
  ```

- **Model Endpoint**: If you see a `No local endpoint registry found` message, this is expected. The tool will use the default OpenAI endpoint with your API key. For custom endpoints, refer to the Prime Intellect documentation.

## Running Tests

Run the test suite from the environment directory:

```bash
# From environments/sv-env-network-logs/
uv run pytest -q
```

## Building and Publishing

### Building the Environment Wheel

```bash
# From the environments/sv-env-network-logs directory
uv build --wheel
```

This will create a wheel file in the `dist/` directory.

### Publishing to Environments Hub

1. **Login to the Prime CLI**:

   ```bash
   prime login
   ```

2. **Push the environment**:

   ```bash
   # From the environment directory
   prime env push -v PUBLIC
   ```

   The push command will automatically build and upload your environment.

## Project Structure

- `sv_env_network_logs.py`: Contains the environment implementation with:
  - `NetworkLogParser`: Extracts and validates classification responses
  - `reward_accuracy`: Binary reward function from `sv_shared` for classification accuracy
  - `reward_calibration`: Calibration bonus function from `sv_shared`
  - `reward_asymmetric_cost`: Asymmetric cost penalty function from `sv_shared`
  - `load_environment`: Entry point that creates the SingleTurnEnv with multi-criteria rubric
- `sv_env_network_logs_test.py`: Test suite for the environment and reward functions
- `pyproject.toml`: Project configuration with dependencies and build settings
- `README.md`: User-facing documentation for the Environments Hub
- `README-DEV.md`: This file - developer documentation

## Implementation Details

The environment uses the Verifiers framework with:

- **Dataset**: `19kmunz/iot-23-preprocessed-minimumcolumns` from Hugging Face. A synthetic dataset with 10 examples is used as a fallback if the download fails.
- **Parser**: `NetworkLogParser` extracts classification labels from model responses and provides format validation.
- **Rubric**: Multi-criteria evaluation with four reward functions from `sv_shared`:
  - `reward_accuracy`: Binary reward (1.0 for correct classification, 0.0 otherwise)
  - `parser.get_format_reward_func()`: Rewards proper JSON format (1.0 for valid, 0.0 for invalid)
  - `reward_calibration`: Bonuses for well-calibrated confidence scores
  - `reward_asymmetric_cost`: Heavy penalty for false negatives (missed attacks)
- **System Prompt**: Guides the model to act as a network security analyst and respond with a JSON object containing label, confidence, and optional rationale.

## Contributing

When making changes:

1. Follow the existing code style (120-character line length)
2. Add tests for new functionality
3. Run the linter: `uv run ruff check .`
4. Run the formatter: `uv run ruff format .`
5. Ensure all tests pass: `uv run pytest -q`
6. Update both README.md and README-DEV.md if needed
