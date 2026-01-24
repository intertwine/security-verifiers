# Prime CLI Reference

## Overview

The Prime CLI (`prime`) is a command-line tool for interacting with Prime Intellect's platform, including managing verifiers environments, compute pods, and code sandboxes. This document provides a comprehensive reference for all Prime CLI commands based on version 0.3.21.

## Installation

### Recommended: Using uv

```bash
# Install uv first (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install prime using uv
uv tool install prime
```

### Alternative: Using pip

```bash
pip install prime
```

## Authentication

Before using most Prime CLI commands, you need to authenticate:

```bash
prime login
```

This will prompt you to enter your API key. You can also set the `PRIME_API_KEY` environment variable.

## Command Structure

The Prime CLI uses a hierarchical command structure:

```bash
prime [OPTIONS] COMMAND [SUBCOMMAND] [ARGS]...
```

## Main Commands

### 1. Environment Management (`prime env`)

Manage verifiers environments for reinforcement learning tasks.

#### Initialize a New Environment

```bash
prime env init <name> [OPTIONS]

Options:
  -p, --path TEXT      Path to environments directory [default: ./environments]
  --rewrite-readme     Overwrite README.md with template if it already exists
```

Example:

```bash
prime env init my-verifier -p ./environments
```

#### Push Environment to Registry

```bash
prime env push [OPTIONS]

Options:
  -p, --path TEXT         Path to environment directory [default: .]
  -n, --name TEXT         Override environment name (defaults to pyproject.toml name)
  -t, --team TEXT         Team slug for team ownership
  -v, --visibility TEXT   Environment visibility (PUBLIC/PRIVATE) [default: PUBLIC]
```

Example:

```bash
# Push from current directory
prime env push

# Push with specific settings
prime env push -p ./environments/my-env -v PUBLIC
```

#### Install an Environment

```bash
prime env install <owner/name[@version]> [OPTIONS]

Options:
  --with TEXT    Package manager to use (uv or pip) [default: uv]
```

Examples:

```bash
# Install latest version
prime env install primeintellect/sv-env-network-logs

# Install specific version
prime env install primeintellect/sv-env-network-logs@0.2.3

# Install using pip instead of uv
prime env install primeintellect/sv-env-network-logs --with pip
```

#### List Available Environments

```bash
prime env list
```

#### Get Environment Information

```bash
prime env info <owner/name>
```

#### Pull Environment for Local Inspection

```bash
prime env pull <owner/name[@version]>
```

#### Delete an Environment

```bash
prime env delete <owner/name>
```

#### Version Management

```bash
# List all versions of an environment
prime env version list <owner/name>

# Delete a specific version
prime env version delete <owner/name> <content-hash>
```

### 2. Compute Pods Management (`prime pods`)

Manage GPU compute pods for training and development.

#### Create a Pod

```bash
prime pods create [OPTIONS]

Options:
  --id TEXT                   Short ID from availability list
  --cloud-id TEXT             Cloud ID from cloud provider
  --gpu-type TEXT             GPU type (e.g. A100, V100)
  --gpu-count INTEGER         Number of GPUs
  --name TEXT                 Name for the pod
  --disk-size INTEGER         Disk size in GB
  --vcpus INTEGER             Number of vCPUs
  --memory INTEGER            Memory in GB
  --image TEXT                Image name or 'custom_template'
  --custom-template-id TEXT   Custom template ID
  --team-id TEXT              Team ID to use for the pod
  --env TEXT                  Environment variables (can be specified multiple times)
```

Example:

```bash
# Interactive creation (recommended for first-time users)
prime pods create

# Create with specific configuration
prime pods create --gpu-type A100 --gpu-count 2 --name ml-training \
  --disk-size 100 --vcpus 16 --memory 64 \
  --env CUDA_VISIBLE_DEVICES=0,1 --env PYTHONPATH=/workspace
```

#### List Running Pods

```bash
prime pods list
```

#### Get Pod Status

```bash
prime pods status <pod-id>
```

#### Connect to a Pod

```bash
# SSH into a pod
prime pods ssh <pod-id>

# Alternative command
prime pods connect <pod-id>
```

#### Terminate a Pod

```bash
prime pods terminate <pod-id>
```

### 3. Code Sandboxes (`prime sandbox`)

Manage secure code execution sandboxes.

#### Create a Sandbox

```bash
prime sandbox create <docker-image> [OPTIONS]

Options:
  --name TEXT               Name for the sandbox (auto-generated if not provided)
  --start-command TEXT      Command to run in container [default: tail -f /dev/null]
  --cpu-cores INTEGER       Number of CPU cores [default: 1]
  --memory-gb INTEGER       Memory in GB [default: 2]
  --disk-size-gb INTEGER    Disk size in GB [default: 10]
  --gpu-count INTEGER       Number of GPUs [default: 0]
  --timeout-minutes INTEGER Timeout in minutes [default: 60]
  --team-id TEXT            Team ID (optional)
  --env TEXT                Environment variables (can be specified multiple times)
```

Example:

```bash
# Create a basic Python sandbox
prime sandbox create python:3.11 --name py-sandbox --memory-gb 4

# Create with custom settings and environment variables
prime sandbox create ubuntu:22.04 \
  --name dev-sandbox \
  --cpu-cores 2 \
  --memory-gb 8 \
  --disk-size-gb 20 \
  --env WORKSPACE=/app \
  --env DEBUG=true
```

#### List Sandboxes

```bash
prime sandbox list
```

#### Get Sandbox Information

```bash
prime sandbox get <sandbox-id>
```

#### Execute Command in Sandbox

```bash
prime sandbox run <sandbox-id> <command>
```

Example:

```bash
prime sandbox run my-sandbox "python script.py"
```

#### Get Sandbox Logs

```bash
prime sandbox logs <sandbox-id>
```

#### Update Sandbox Status

```bash
prime sandbox status <sandbox-id>
```

#### Delete a Sandbox

```bash
prime sandbox delete <sandbox-id>
```

### 4. GPU Availability (`prime availability`)

Check GPU availability and pricing information.

#### List Available GPU Resources

```bash
prime availability list
```

#### List Available GPU Types

```bash
prime availability gpu-types
```

### 5. Configuration Management (`prime config`)

Manage Prime CLI configuration and credentials.

#### View Current Configuration

```bash
prime config view
```

#### Set API Key

```bash
prime config set-api-key [<api-key>]
# If API key not provided, will prompt securely
```

#### Set Team ID

```bash
prime config set-team-id <team-id>
```

#### Remove Team ID (Use Personal Account)

```bash
prime config remove-team-id
```

#### Set API Base URL

```bash
prime config set-base-url [<url>]
```

#### Set Frontend URL

```bash
prime config set-frontend-url [<url>]
```

#### Set SSH Key Path

```bash
prime config set-ssh-key-path <path>
```

#### Environment Management

```bash
# Save current config as an environment
prime config save <env-name>

# Switch to a different environment
prime config use <env-name>

# List available environments
prime config envs
```

#### Reset Configuration

```bash
prime config reset
```

## Common Workflows

### 1. Publishing a Verifier Environment

```bash
# 1. Initialize environment
prime env init my-security-verifier -p ./environments

# 2. Develop your environment
cd environments/my-security-verifier
# ... implement your verifier logic ...

# 3. Build the wheel (using uv)
uv build --wheel

# 4. Push to registry
prime env push -v PUBLIC

# 5. Verify it's available
prime env list | grep my-security-verifier
```

### 2. Setting Up a Training Pod

```bash
# 1. Check available GPUs
prime availability list

# 2. Create a pod with desired specs
prime pods create --gpu-type A100 --gpu-count 8 --name training-pod

# 3. Connect to the pod
prime pods ssh training-pod

# 4. Install your environment on the pod
prime env install username/my-security-verifier

# 5. When done, terminate the pod
prime pods terminate training-pod
```

### 3. Running Code in a Sandbox

```bash
# 1. Create a sandbox
prime sandbox create python:3.11 --name test-env --memory-gb 4

# 2. Execute commands
prime sandbox run test-env "pip install numpy pandas"
prime sandbox run test-env "python -c 'import numpy; print(numpy.__version__)'"

# 3. Check logs
prime sandbox logs test-env

# 4. Clean up
prime sandbox delete test-env
```

## Environment Variables

The Prime CLI respects the following environment variables:

- `PRIME_API_KEY`: Your Prime Intellect API key
- `PRIME_BASE_URL`: Override the API base URL
- `PRIME_TEAM_ID`: Default team ID for operations

## Tips and Best Practices

1. **Use `uv` for package management**: The Prime CLI works best with `uv` for managing Python environments and dependencies.

2. **Start with interactive mode**: For commands like `prime pods create`, running without options starts an interactive wizard that guides you through the process.

3. **Check availability first**: Before creating pods, use `prime availability list` to see what resources are available and their pricing.

4. **Version your environments**: When pushing updates to environments, the system automatically versions them. Users can install specific versions using `@version` syntax.

5. **Use teams for collaboration**: If working with a team, set your team ID in the config to ensure resources are properly attributed.

6. **Clean up resources**: Remember to terminate pods and delete sandboxes when done to avoid unnecessary charges.

## Troubleshooting

### Authentication Issues

If you encounter authentication errors:

1. Verify your API key: `prime config view`
2. Re-login if needed: `prime login`
3. Check if `PRIME_API_KEY` environment variable is set correctly

### Environment Installation Failures

If environment installation fails:

1. Ensure you have the correct package manager (uv or pip)
2. Try installing with the alternative: `--with pip` or `--with uv`
3. Check if the environment name and version are correct

### Pod Connection Issues

If you can't connect to a pod:

1. Verify the pod is running: `prime pods status <pod-id>`
2. Check your SSH key configuration: `prime config view`
3. Ensure the SSH key path is correct: `prime config set-ssh-key-path <path>`

## Version Information

This documentation is based on Prime CLI version 0.3.21. To check your version:

```bash
prime --version
```

To update to the latest version:

```bash
# Using uv
uv tool upgrade prime

# Using pip
pip install --upgrade prime
```
