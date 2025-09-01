# Implementing Verifiers in Prime Intellect's Environments Hub for RL Training

## Introduction

Prime Intellect's Environments Hub is a new community-driven platform for creating and sharing reinforcement learning (RL) environments (or "verifiers") for Large Language Models (LLMs). An environment defines a task: it includes the "world" (context or dataset), rules of interaction, and a reward function to evaluate model behavior. By open-sourcing these environments, the Hub enables researchers to collaboratively expand the set of RL tasks available for training and evaluating LLMs.

In this guide, we outline how to implement the custom verifiers (tasks proposed in your mini-PRDs) as Environments using Prime Intellect's Verifiers library, publish them on the Environments Hub, and train RL-enabled models (starting with Qwen) against these environments. We cover both local development and using Prime Intellect's cloud infrastructure - from a single-machine test run to full-stack distributed training.

## Setting Up Local Development for Verifiers

To develop a verifier environment, begin by setting up the development tools:

- Install the Verifiers library: Prime Intellect's verifiers is an open-source toolkit for creating RL environments and training LLM agents. You can install it via pip or using the recommended uv tool. For example:

```bash
pip install "verifiers[dev]"  # install verifiers with dev/test support
```

(The uv tool is suggested for managing environments: e.g. uv init to create a venv, then uv add verifiers.)

- Initialize a new Environment module: The Verifiers library provides a CLI to scaffold a new environment. Run vf-init {env-name} to create a boilerplate environment package. This creates a folder (e.g. vf-myenv) with a Python module, a pyproject.toml (for dependencies/metadata), and a template load_environment function. Environments are structured as installable Python packages (distributed as wheels) and must expose a load_environment() function for the hub/trainer to instantiate them.
- Define the environment logic: With the scaffold in place, implement the core components of your verifier:
- Dataset: Prepare a dataset of tasks/prompts. This can be a HuggingFace Dataset or a simple list of prompts. For example, a dataset might have a column "prompt" (containing the input or question) and an "answer" or "info" column with the ground-truth or any info needed for evaluation. You can load or construct this dataset in your environment's code (e.g. using datasets.load_dataset() or a custom loader).
- Rollout / Interaction logic: Decide if the task is single-turn (model produces one answer per prompt) or multi-turn. For a simple Q&A or formatting task where the model gives one response, you can use SingleTurnEnv - you just provide the dataset and a reward function (Rubric). If the task requires multi-turn interactions or tool use (e.g. the model may call functions or require iterative reasoning), use MultiTurnEnv or the provided ToolEnv class for tool-enabled loops. The Verifiers framework supports both /v1/completions and /v1/chat/completions style models via an OpenAI-compatible interface, which means it can accommodate chat models or raw completion models seamlessly.
- Reward functions (Rubric): Implement one or more reward functions to "verify" the model's output. In Verifiers, you encapsulate these in a Rubric. For example, you might have a function reward_correctness(prompt, completion, info) -> float that returns 1.0 if the model's completion is correct (perhaps by comparing to info["solution"] or running test cases) and 0.0 otherwise. You can also define auxiliary rewards or metrics (e.g. format compliance, or other partial credit). Collect these in a vf.Rubric with weights for each sub-reward. The Verifiers library will handle combining these and computing a final reward for each model output.
- Parsers or Tools (if needed): If your task involves parsing the model output or using external tools, implement those as well. For parsing, you can subclass vf.Parser or use built-ins like vf.ThinkParser (for ensuring a certain format). For tool use, ToolEnv allows defining Python functions as tools; the function signatures are automatically converted into tool schemas that the model can invoke during its rollout. For example, if your verifier involves code execution or web search, you might define tools and use vf.ToolRubric to give rewards based on tool usage or outcomes.
- Test the environment locally: Before publishing, run a quick evaluation to verify everything works. The Verifiers CLI makes this easy. For instance, you can do:

```bash
vf-eval <env-name> --model gpt-4.1-mini --num-examples 5
```

This will load your environment and have a small model (or API) attempt a few prompts, then report the average reward. You can also import and test in a Python script:

```python
import verifiers as vf
env = vf.load_environment("<env-name>")
results = env.evaluate(client=vf.OpenAIClient(), model="gpt-4.1-mini", num_examples=5)
print(results.stats) # e.g. average reward
```

Ensure that the environment returns reasonable rewards and that no errors occur during model interaction. If your verifier needs to execute code (for example, to check answers or run test cases), note that Prime Intellect provides Sandboxes - secure execution environments that can be integrated with Verifier environments for safe code running. This can be useful for code-based tasks (you can offload code execution to the sandbox to evaluate correctness without risking the host environment).

- Finalize dependencies: Make sure your environment's pyproject.toml lists any required packages (datasets, libraries for your reward logic, etc.). The Environments Hub treats each environment as a standalone Python package with its own dependencies. This isolation ensures that complex environments with many dependencies remain manageable and versioned.

## Publishing the Environment on Environments Hub

Once your verifier environment is implemented and tested locally, you can publish it to the Environments Hub (so others can discover and use it, and so you can use it in cloud training). The Environments Hub acts as a package registry for environment modules. Here's how to upload your environment: 1. Install and login to Prime CLI: The Prime CLI is a command-line tool for interacting with Prime Intellect's platform, including the environment registry. The recommended installation method is via uv:

```bash
# Install uv first (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install prime using uv
uv tool install prime
```

Alternatively, you can install via pip:

```bash
pip install prime
```

Then authenticate with your Prime Intellect account:

```bash
prime login
```

This will prompt you to enter your API key or credentials (you can also set PRIME_API_KEY as an environment variable). Successful login is required to upload to the Hub.

1. Build your environment wheel: Navigate to your environment project directory (the one with pyproject.toml). Build a Python wheel distribution using uv:

```bash
uv build --wheel
```

Or using the standard Python build module:

```bash
python -m build --wheel
```

This should produce a file like vf_myenv-0.1.0-py3-none-any.whl in the dist/ folder. (Alternatively, if you have Hatch installed, you can use `hatch build -t wheel`, or the Prime CLI may handle building automatically.)

1. Upload to Environments Hub: Use the Prime CLI to upload the wheel to the Hub's registry. For example:

```bash
prime env upload dist/vf_myenv-0.1.0-py3-none-any.whl
```

(If prime env upload is not the exact command, refer to Prime's documentation "Create & Upload Environment" - the CLI provides a command to push your wheel to the hub registry.) This will register the environment under your account on the hub. After a successful upload, you should be able to see your environment listed on the Hub web interface (under Environments at app.primeintellect.ai). Each environment gets a unique identifier, typically in the form `<username>/<env-name>`.

1. Install/Use the environment via Hub: Now that it's published, anyone (or you on another machine) can install the environment by name. For example:

```bash
prime env install vf-myenv
```

will download and install the environment package. Internally this is equivalent to pip-installing the environment wheel from the hub. You can also specify your environment as a dependency in other projects. For instance, Prime's RL training library can fetch it by referring to the wheel URL on the hub. This makes integration very convenient.

At this point, your custom verifier is available on the Environments Hub for others to discover and for you to use in training jobs. Make sure to include documentation or README in your environment package if possible, so users know what the verifier does and how to use it.

## Training an RL Model with Prime Intellect's Tools

With the environment (verifier) in place, the next step is to train a model to perform well on it, demonstrating the environment's effectiveness. Prime Intellect provides an open-source RL training framework called Prime RL (prime-rl) for scalable reinforcement fine-tuning (RFT) of LLMs. We will outline how to use it to train a model (starting with the Qwen model family) on your custom environment. We'll address both local (single-machine) training and full-stack distributed training using Prime's cloud compute.

### Local/Single-Machine Training

For initial experimentation or development, you can train on a single machine (with one or a few GPUs):

- Setup training environment: Make sure you have prime-rl installed (e.g. pip install prime-rl or include it in your uv environment) and that your newly uploaded environment is installed in the environment as well. You can use the CLI to install it as shown above (prime env install...), or add it to your pyproject.toml as an optional dependency. Verify that verifiers and prime-rl can see the environment: for example, vf.load_environment("vf-myenv") should work in Python, and prime env list (if available) should show it.

- Prime RL configuration: Prime RL uses a trainer-orchestrator-inference architecture for RL training. For a simple single-machine run, however, you can use the provided rl entry point which wraps these components together for convenience. You will need to prepare a few configuration files or command-line options:

- A trainer config (specifying the model, training hyperparameters, optimizer, etc.). For example, you'll specify the model name (e.g. a HuggingFace model like "Qwen/Qwen-7B" or "Qwen3-4B"), learning rate, batch size, and RL algorithm settings (Prime RL implements an async policy gradient algorithm, GRPO). You can start from one of Prime's example configs (they have examples for tasks like reverse text, math, etc.) and modify it.

- An orchestrator config, which ties together the environment and how rollouts are conducted. Critical: in the orchestrator config, set your environment's ID. For example:

```toml
[environment]
id = "yourusername/vf-myenv"
```

This tells prime-rl to load your custom environment by that identifier from the Hub. You can also pass environment-specific arguments here if your load_environment expects any (under [environment.args]).

- An inference (model server) config, which describes how to run the model for generating responses. On a single machine, you might combine this with the trainer, but generally Prime RL spins up a separate process (or thread) to handle model inference. You'll specify which model weights to load and any generation parameters (like max tokens, sampling strategy) here.

For instance, a simple run might not even require editing files if you use CLI flags. You could run:

```bash
uv run rl \
 --trainer.model.name "<model-name-or-path>" \
 --trainer.learning_rate 1e-5 \
 --orchestrator.environment.id "yourusername/vf-myenv" \
 --trainer.steps 1000
```

(This is a schematic example — in practice you might use the provided TOML config files and just do uv run rl --trainer @configs/your_train.toml --orchestrator @configs/your_orch.toml for clarity.)

- Choose a base model (Qwen to start): You indicated using Qwen to start. Qwen is a family of open-source LLMs known to integrate well with Prime's stack (PrimeIntellect has used Qwen3 models in their research). Ensure that you have access to the Qwen model weights (e.g. via Hugging Face). In the config, set model.name to the appropriate Hugging Face model ID for Qwen (for example, "Qwen/Qwen-7B" or a smaller variant). The Prime RL trainer, via vLLM, will handle serving this model for RL training. Note that because Prime RL uses a standard OpenAI-compatible interface for inference, you can easily swap in other models later by just changing this config value. The training loop and environment don't need to change for a different model, which leaves room to try new models as they emerge.

- Run the training: Execute the training command (as per above). Prime RL's rl entrypoint will start the trainer (which updates the model with RL rewards), the inference server (which generates model outputs for the environment), and an orchestrator that coordinates the two and applies your environment's reward function. On a single machine, these might run as subprocesses. You'll see logs for training progress - e.g. episodic rewards, policy loss, etc. (By default, logs for the orchestrator and inference might be written to files; using a tool like tmux or the provided logging utilities can help view everything.)

- Monitor and evaluate: As training runs, you should observe the model's performance on your verifier task improving (e.g. average reward per episode increasing). You can periodically run evaluations: for example, using vf-eval vf-myenv --model {yourCheckpoint} to have a separate evaluation of how well the model performs according to the verifier. Prime RL also has an eval entrypoint for running a suite of evaluations on a trained model. Logging to WandB is supported for more advanced monitoring (you can enable it in configs or via CLI flags to track reward curves over time).

- Note on Qwen and multi-turn: If your environment is single-turn, Qwen should work out-of-the-box. If you designed a multi-turn environment, be aware that certain model architectures like Qwen (especially Qwen3 series) have known quirks with the requirement that tokens only ever append during a rollout. Essentially, Verifiers enforces that once a token is generated, it remains in the context for subsequent turns (monotonic context growth). Models that internally reset or reuse position embeddings in a non-standard way might need adaptation. Prime Intellect's documentation notes that Qwen3 and some others needed fixes ("Footguns") to handle multi-turn generation. If you encounter issues (like the model repeating or truncating in multi-turn scenarios), consult the Verifiers documentation for the recommended adjustments or consider limiting to single-turn interaction for that model. This does not affect using other models - you can try a different model if needed, reinforcing that the environment is not tied to one model.

### Scaling Up: Full-Stack Training on Prime's Infrastructure

One of the key advantages of using Prime Intellect's ecosystem is the ability to scale to distributed training with minimal friction. After validating on a single machine, you can run larger experiments on Prime's cloud or even harness volunteered GPUs from the community (as done in their INTELLECT-2 and -3 projects). Here's how you can approach full-stack training:

- Launch cloud instances: Through Prime's platform, you can spin up GPU instances or clusters on demand. For example, using the CLI you can create a pod with a certain number of GPUs (the Quickstart - Deploy a Pod guide shows how to get a GPU in under a minute). You can also request multi-node clusters; Prime supports deploying 16, 32, or 64+ H100 GPUs across multiple nodes if needed. These instances come with the Prime software stack ready, or you can use Docker images to set up the environment.

- Use the Environments Hub and prime-rl on cloud: Once your cloud cluster is up, you can install your environment from the Hub (same prime env install vf-myenv command) and ensure prime-rl is installed. Because the Environments Hub is a centralized registry, your environment is immediately accessible to any machine once uploaded. Then you can run the same training commands as you did locally. If you requested multiple GPUs or multiple nodes, you can leverage them as follows:

- Prime RL allows you to allocate separate GPUs for the trainer and the inference engine. For example, in one of their examples, on an 8-GPU setup they used --trainer-gpus 2 --inference-gpus 6 to dedicate 2 GPUs to model training and 6 to serving the model for rollouts. Adjust these based on your environment's complexity and model size. If your model is large (e.g. 30B+ parameters), you might give more GPUs to inference (or use tensor parallelism).

- If you have multiple nodes, you can run the trainer on one and the inference on another. The orchestrator will communicate over the network (make sure to point the orchestrator config to the inference server's address). Prime RL documentation details how to use torchrun for multi-node training (for distributed data parallel on the trainer side) and how to set up vLLM's inference across nodes (data parallel inference). Essentially, you export a rendezvous endpoint for torch distributed, and run the trainer on each node with the appropriate rank; similarly start the vLLM inference with head and worker nodes. The CLI examples in their docs show the exact commands to run on each node for multi-node setups.

- Leverage Prime's global compute: Instead of manually managing nodes, you might also tap into Prime's community compute pool. They have a system where you can run jobs on volunteer GPU clusters globally (as seen in INTELLECT-2, which used 1,253 GPUs from contributors). This is an advanced use-case, but essentially Prime's orchestrator and protocol can distribute the training workload over the internet with fault tolerance. If you enter that route, you'd package your training job (model + environment) and submit it to Prime's system. The details are beyond this doc, but be aware it's possible - the same environment you wrote can scale from your single GPU all the way to thousands of GPUs in a decentralized training run.

- Monitoring and managing: On the cloud, you'll want to monitor training. Prime's CLI allows streaming logs (for example, using tmux or log files as mentioned). You can also integrate Weights & Biases or another logger to track progress. The platform is designed for long-running jobs, so you can checkpoint models periodically. Prime RL supports checkpointing of both the trainer and orchestrator state so you can resume if needed. Ensure you save checkpoints to a persistent storage (Prime provides ways to attach storage volumes or you can upload to your own cloud bucket).

- Evaluation and Evals Hub: After training, evaluate the model's performance on your verifier environment and possibly other related tasks. The Environments Hub also supports evals - you can create evaluation reports for a model on a given environment and share those results. For example, you might use prime-rl eval or vf-eval to generate a report of your fine-tuned model's score on the environment and compare it to a base model. These eval results can be uploaded or visualized (the Hub has an interface for evaluations). This helps demonstrate that your verifier environment is effective (your model's improvement from pre-training to post-RLFT on the task is evidence the reward is meaningful).

- Generalizing to other models: While Qwen is your starting point, once the environment is in the Hub, any model can be trained on it using the same process. For instance, you could try a Llama2 variant or another emerging model by just specifying a different model.name in the training config. Prime's infrastructure is model-agnostic as long as the model can be served via the OpenAI-compatible API (through vLLM), which is true for most HuggingFace transformer models. This means your verifier environment could become a standard benchmark for multiple models.

## Conclusion and Next Steps

By following this process, you have: (1) defined custom verifier environments locally with the Verifiers library, (2) published them on the Environments Hub for community use, and (3) trained a reference RL-tuned model (Qwen) on each environment using Prime Intellect's RL training stack. You've covered the full stack from development to distributed training.

Moving forward, you can iterate by improving your environments (the verifiers spec allows focusing on task-specific logic while reusing the existing evaluation and training infrastructure ) and by training larger or different models. For example, you might want to try a larger Qwen variant or another model like Llama 2 on the same verifier to compare performance. The Environments Hub will facilitate collaboration - others might try your environment with their models, or you can easily incorporate environments others have shared. This open ecosystem lowers the barrier to Reinforcement Learning research, helping the community collectively push the state-of-the-art with truly open AGI training tasks.

Finally, ensure to document your results: when your reference models are trained, consider releasing them (e.g. on Hugging Face) and writing an evaluation report on the Hub. This will prove the effectiveness of your verifier environments and encourage adoption by others. With tools from Prime Intellect, you can seamlessly go from a creative idea for evaluating an LLM to a fully trained agent excelling at that task - all on open infrastructure. Good luck with your verifier implementations and happy training!

## Sources

- Prime Intellect Team, "Environments Hub: A Community Hub To Scale RL To Open AGI"
- Prime Intellect Docs - Environment Hub Overview
- Verifiers Library - GitHub README
- Prime RL Library - GitHub README and Examples
