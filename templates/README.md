# Environment Templates

This directory contains templates for creating new security verifier environments.

## Quick Start

To create a new environment:

1. **Create the environment directory:**

   ```bash
   mkdir environments/sv-env-my-task
   ```

2. **Copy and customize the templates:**

   ```bash
   # Copy main environment file
   cp templates/environment_template.py environments/sv-env-my-task/sv_env_my_task.py

   # Copy test file
   cp templates/environment_test_template.py environments/sv-env-my-task/sv_env_my_task_test.py

   # Copy and customize pyproject.toml
   cp templates/pyproject_template.toml environments/sv-env-my-task/pyproject.toml
   ```

3. **Update the files:**

   - Replace `my-env-name` with your environment name (use dashes)
   - Replace `my_env_module` with your module name (use underscores)
   - Update class names, descriptions, and implementation details
   - Add appropriate dataset loading logic
   - Implement parsing and reward functions

4. **Install and test:**

   ```bash
   # Install in editable mode
   uv pip install -e environments/sv-env-my-task

   # Run tests
   uv run pytest environments/sv-env-my-task/
   ```

## Template Files

### `environment_template.py`

Main environment implementation with:

- Parser class for extracting model responses
- Reward functions for scoring
- `load_environment()` entry point
- Support for both SingleTurnEnv and MultiTurnEnv

### `environment_test_template.py`

Comprehensive test suite including:

- Parser tests
- Reward function tests
- Environment loading tests
- Mock dataset tests

### `pyproject_template.toml`

Project configuration using hatchling:

- Dependencies and metadata
- Entry points for verifiers
- Build configuration
- Development tools setup

## Environment Types

### SingleTurnEnv

For tasks with one prompt → one response:

- Classification tasks (phishing, network logs)
- Single-step analysis

### MultiTurnEnv

For interactive conversations:

- Red team scenarios
- Multi-step verification
- Conversational tasks

### ToolEnv

For environments with tool usage:

- Code analysis with static analyzers
- Configuration verification with parsers
- Any task requiring external tools

## Best Practices

1. **Naming Convention:**

   - Environment name: `sv-env-descriptive-name` (with dashes)
   - Module name: `sv_env_descriptive_name` (with underscores)
   - Keep names consistent across files

2. **Reward Functions:**

   - Always normalize rewards between 0.0 and 1.0
   - Use weighted rubrics for multiple criteria
   - Format rewards should typically have lower weight than correctness

3. **Datasets:**

   - Always provide a synthetic fallback dataset
   - Handle dataset loading failures gracefully
   - Limit dataset size with `max_examples` parameter

4. **Testing:**

   - Test all parser edge cases
   - Use parametrized tests for reward functions
   - Mock external dependencies (datasets, APIs)
   - Ensure 100% test coverage for critical functions

5. **Documentation:**
   - Clear docstrings for all public functions
   - Examples in the module docstring
   - README.md with usage examples and performance metrics
