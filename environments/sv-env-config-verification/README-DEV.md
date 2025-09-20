# Development Guide for sv-env-config-verification

This document contains information for developers working on the sv-env-config-verification environment.

## Local Development Setup

To set up the environment for local development and testing, install it in editable mode with the `dev` dependencies. From the repository root, after creating and activating a virtual environment:

```bash
# Install the package and development dependencies
uv pip install -e 'environments/sv-env-config-verification[dev]'
```

This will install all necessary dependencies for running the environment and its tests, including `verifiers[dev]`.

## Local Testing

To test the environment locally, you can use the `vf-eval` command from the `verifiers` library. This will load the environment and run a few examples using a specified model.

```bash
# Evaluate the environment with a small model
vf-eval sv-env-config-verification --model gpt-5-mini --num-examples 1
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
  set -a && source .env && set +a && vf-eval sv-env-config-verification --model gpt-5-mini --num-examples 1
  ```

- **Tool Execution**: The environment executes real security scanners (KubeLinter, Semgrep). These tools must be available in your PATH or the environment will fall back to mock implementations.

- **Model Endpoint**: If you see a `No local endpoint registry found` message, this is expected. The tool will use the default OpenAI endpoint with your API key. For custom endpoints, refer to the Prime Intellect documentation.

## Running Tests

Run the test suite from the environment directory:

```bash
# From environments/sv-env-config-verification/
uv run pytest -q
```

You can also run the broader test suite:

```bash
# Environment-specific tests
make test-env E=config-verification

# Full e2_config_auditing test suite
make e2-test
```

## Building and Publishing

### Building the Environment Wheel

```bash
# From the environments/sv-env-config-verification directory
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

- `sv_env_config_verification/__init__.py`: Contains the main environment implementation with:
  - `ConfigVerificationParser`: Validates and parses JSON responses from models
  - `reward_config_auditing`: Computes rewards based on detection accuracy and patch effectiveness
  - `run_kubelinter`: Wrapper for Kubernetes static analysis
  - `run_semgrep`: Wrapper for Terraform/generic pattern scanning
  - `load_environment`: Entry point that creates the ToolEnv with security tools
- `sv_env_config_verification/e2_config_auditing/`: Core auditing library
  - `adapters/`: Tool wrappers (KubeLinter, Semgrep, OPA)
  - `baselines/`: Example tool baselines and ground truth
  - `ci/`: Version pinning for reproducible builds
  - `dataset/`: Test fixtures and oracle labels
  - `docker/`: Containerization support
  - `env.py`: Environment configuration
  - `mapping.py`: Finding normalization and deduplication
  - `oracle.py`: Ground truth generation
  - `patching.py`: Patch application and validation
  - `reward.py`: Reward computation with severity weighting
  - `schema.py`: Input/output validation schemas
  - `tests/`: Unit tests for all components
- `sv_env_config_verification_test.py`: Integration tests for the environment
- `pyproject.toml`: Project configuration with dependencies and build settings
- `README.md`: User-facing documentation for the Environments Hub
- `README-DEV.md`: This file - developer documentation

## Implementation Details

The environment uses the Verifiers framework with:

- **Dataset**: Built-in fixtures with Kubernetes YAML and Terraform HCL configurations, each with oracle violation labels
- **Parser**: `ConfigVerificationParser` validates JSON responses and extracts violations, patches, and confidence scores
- **Rubric**: Two reward functions with weights [1.0, 0.05]:
  - `reward_config_auditing`: Severity-weighted F1 score plus patch effectiveness bonus
  - `parser.get_format_reward_func()`: JSON format validation (1.0 for valid, 0.0 for invalid)
- **Tools**: Two security scanners accessible to models:
  - `run_kubelinter`: Kubernetes static analysis with detailed findings
  - `run_semgrep`: Terraform and generic pattern matching
- **System Prompt**: Guides models to audit configurations and return JSON with violations, optional patches, and confidence scores

The reward system combines detection accuracy (severity-weighted F1) with patch verification - models get bonus rewards when their patches successfully remove oracle violations from the configuration.

## Contributing

When making changes:

1. Follow the existing code style (120-character line length)
2. Add tests for new functionality
3. Run the linter: `uv run ruff check .`
4. Run the formatter: `uv run ruff format .`
5. Ensure all tests pass: `uv run pytest -q`
6. Update both README.md and README-DEV.md if needed

### Tool Updates

When updating security tools (KubeLinter, Semgrep, OPA):

1. Update versions in `e2_config_auditing/ci/versions.txt`
2. Test tool compatibility with existing fixtures
3. Update baseline outputs if tool behavior changes
4. Run full test suite to ensure reward computation remains stable

### Adding New Fixtures

To add new test fixtures:

1. Add configuration files to `e2_config_auditing/dataset/fixtures/{k8s,tf}/`
2. Generate oracle labels and save to `e2_config_auditing/dataset/oracle/`
3. Update the fixture loading in `sv_env_config_verification/__init__.py`
4. Test that tools correctly identify violations
5. Run reward computation tests to verify scoring
