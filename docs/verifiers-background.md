# CyberSec Verifiers

## History of the Verifiers RL Library

The Verifiers RL library is an open-source toolkit developed primarily by Will Brown (@willccbb) for building reinforcement learning (RL) environments and training large language model (LLM) agents, with a focus on verifiable rewards and agentic reasoning tasks. It originated as an independent project by Brown, with early updates appearing in February 2025, including features like removing dependencies on the TRL library fork, adding custom multi-step tool calling, and integrating simple search agents inspired by "Deep Research." These initial developments emphasized modularity for tasks like math, coding, and open-ended STEM questions. By May 2025, Brown joined Prime Intellect (@PrimeIntellect), a company focused on decentralized AI compute, which integrated Verifiers into its ecosystem for large-scale RL applications. This integration aligned with Prime Intellect's mission to open-source AGI through collaborative compute, data, and models.

Key milestones include:

- **February 2025**: Early updates focused on core functionality, such as asynchronous verifiers and environment modules for synthetic data generation.
- **May 2025**: Brown announced his move to Prime Intellect, expressing excitement about advancing open-source agentic RL at scale.
- **June 2025**: Brown highlighted Verifiers as a "performant, hackable, easy-to-use, scalable, and agentic" RL framework, and collaborated on a course teaching agents and RL, incorporating Verifiers alongside other tools.
- **July 2025**: Release of version 0.1.2, which included optimizations like retiring dynamic batching in vLLM, full response objects in environments/trainers, better async rollouts/rewards, and bug fixes. Dependencies were streamlined to essentials like `datasets`, `openai`, `transformers`, and `vllm`. Brown also shared example scripts for tool-use data generation and RL training.

The library draws from Brown's research, including his 2025 paper "Verifiers: Reinforcement learning with LLMs in verifiable environments," which explores format rewards and credit assignment in RL. It has been referenced in Prime Intellect's projects, such as the INTELLECT-2 model (a 32B-parameter reasoning model trained via decentralized RL) and SYNTHETIC datasets, where Verifiers provides modular components for tasks and rewards. The GitHub repository (willccbb/verifiers) serves as the central hub, with full documentation at [verifiers.readthedocs.io](http://verifiers.readthedocs.io/), emphasizing its flexibility beyond RL for LLM evaluations and agent harnesses.

### Current Use of the Verifiers RL Library

Verifiers is currently used as a modular framework for creating RL environments (e.g., SingleTurnEnv for one-shot tasks, ToolEnv for tool-calling, MultiTurnEnv for interactive agents) and training with algorithms like async GRPO (Group Relative Policy Optimization). It supports integration with OpenAI-compatible clients, Hugging Face's Transformers Trainer, and Prime Intellect's prime-rl for decentralized, large-scale training on heterogeneous GPUs. Key applications include:

- **Synthetic Data Generation**: Used in Prime Intellect's SYNTHETIC-1 (1.4M verified reasoning traces for math, coding, and science) and SYNTHETIC-2 (4M traces from global compute contributors), enabling crowdsourced datasets with programmatic verifiers.
- **Decentralized RL Training**: Powers models like INTELLECT-2, decoupling rollout generation, training, and weight broadcasting for fault-tolerant, async RL across global networks. It incorporates verifiers like toploc for cryptographic proofs of inference integrity.
- **Agentic Reasoning and Evaluations**: Facilitates multi-turn tool calling, rubric-based rewards (e.g., weighted functions for scoring completions), and quick evals via CLI commands like `vf-eval`. Users can install environments as modules with custom dependencies, making it extensible for tasks like PubMedQA with reasoning traces.
- **Scalability and Integration**: For small-scale use, it runs on CPUs/APIs; for GPUs, it leverages Accelerate/DeepSpeed and vLLM. Prime-rl extends it for FSDP (Fully Sharded Data Parallel) training, supporting MoE (Mixture of Experts) and LoRA soon.

The library's "Environments Hub" (in private beta as of August 2025) acts as an "App Store" for verifiable rewards, allowing sharing of recipes, datasets, and rubrics—fostering an open-source RL ecosystem. Others have praised it for enabling agent-to-RL loops, with users contributing PRs, exploring Prime-rl integrations, and adapting harnesses. For instance, it's been used for multi-turn preference RL experiments and compared favorably to setups requiring human annotations for verifiers.

| Feature           | Description                                                                          | Example Use Case                                                              |
| ----------------- | ------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------- |
| Environments      | Modular modules with datasets, protocols, and rewards; installable via `vf-install`. | Building a Wordle solver or PubMedQA evaluator with rubrics.                  |
| Trainer           | GRPOTrainer for full-parameter finetuning on 2-16 GPUs; async rollouts.              | Training Qwen-32B models on synthetic traces for reasoning.                   |
| Rewards/Verifiers | Rubric class for weighted functions; supports LLM judges, code tests.                | Verifying math solutions or code outputs in decentralized setups.             |
| Integration       | OpenAI/vLLM clients; prime-rl for distributed training.                              | Global RL runs like INTELLECT-2 without Ray for multi-datacenter scalability. |

### What Will Brown Has Said About It

Will Brown has frequently posted about Verifiers on X, emphasizing its role in democratizing agentic RL. In May 2025, he described it as a framework that's "performant and hackable and easy-to-use and scalable and agentic." After joining Prime Intellect, he highlighted its alignment with open-source incentives, stating, "there is a dire shortage of labs who are truly embracing open-source research... my own goal is to continue... advancing open research and infrastructure for agentic RL." In June 2025, he teamed up for a course on agents and RL, noting Verifiers' utility for training custom agents. Recent updates (July-August 2025) include excitement about v0.1.2's reliability ("it's gotten a lot more fun and reliable to use") and its portability ("environments are their own modules... you don't need to PR"). He positions it orthogonally to tools like DSPy, as "a toolkit for doing RL research," not automated optimization. Brown also stresses efficient RL ("optimizing both your trainer and your inferencer") and shares resources like his paper and example scripts for tool-use RL. In a July 2025 talk, he discussed RL algorithms like GRPO, environment design, and open-source tradeoffs, likely referencing Verifiers' ecosystem.

### How Others Are Using It

Community adoption has grown, with users leveraging Verifiers for open-source RL experiments. One user noted it "just clicked" due to the Environments Hub for sharing recipes, calling it essential for open-source progress. Another explored it alongside Prime-rl, submitting PRs and praising its RL environment potential. In a meme-style post, a developer humorously lauded it as solving fragmentation in the RL ecosystem by acting as an "App Store for Verifiable Rewards." Researchers have used it for GRPO training tips, multi-turn setups, and adapting to models like Qwen-30B, achieving strong results on tasks like PubMedQA. Prime Intellect incorporates it into global runs like SYNTHETIC-2 and INTELLECT-2 for verified reasoning traces. Excitement centers on its open-source ecosystem potential, with one user joining Prime Intellect specifically for Verifiers' role in jump-starting RL collaboration. It's also referenced in papers like RL^V and VeriFree for verifier-inspired approaches, though not always directly used.

User: I am interested in using the verifiers library to improve modeling tasks in cybersecurity (I'm a principal dev at Expel cybersecurity). Can you help research if anyone has started this kind of work using the verifiers library, and can you suggest good first projects that I could create using the library? I'd like to start helping Will Brown and the community fill domain-specific gaps in the availability of RL verifiers for security and perhaps for model safety and alignment.

### Research on Use of Verifiers Library in Cybersecurity (version 1)

Based on extensive searches across X (using semantic and keyword queries targeting mentions of "verifiers" in conjunction with cybersecurity, security, model safety, or alignment, including posts from @willccbb and @PrimeIntellect), web searches for related terms, and direct browsing of the Verifiers GitHub repository and documentation, there is no direct evidence of anyone publicly starting or documenting work using the Verifiers RL library specifically for cybersecurity tasks as of August 24, 2025.

- **Key Findings from Searches**:

  - No X posts, papers, or repos explicitly link Verifiers to cybersecurity applications. General cybersecurity discussions (e.g., vulnerability checklists, IoT security systems, or malware forensics) appear, but they use other RL frameworks like custom DRL setups or libraries such as VeRLPy (for hardware design verification) or IoTWarden (for IoT defense). For instance, projects like "IoTWarden-Deep-RL-based-Security-System" use RL for real-time IoT defense but do not reference Verifiers.
  - Broader RL applications in cybersecurity exist, such as using DRL for adaptive threat detection, cyber-attack simulation, or anomaly detection in networks. Examples include frameworks for enhancing malware forensics with RL or verifying digital designs, but these predate or are unrelated to Verifiers.
  - On model safety and alignment: The Verifiers README highlights potential alignment issues during training, such as non-increasing chat templates in models like Qwen3 or DeepSeek-R1, which can violate multi-turn GRPO requirements and affect agent reliability. Will Brown provides modified models (e.g., on Hugging Face) to fix these, emphasizing their role in stable RL training. This indirectly touches on model safety by ensuring consistent reasoning traces, but no cybersecurity-specific adaptations are mentioned.
  - Community contributions: The repo invites bug reports and environment additions, with no existing PRs or issues related to security domains. The "Environments Hub" (in beta) could be a venue for sharing security-focused verifiers, but none are listed yet.

While no one appears to have pioneered this yet, this represents an opportunity for you to lead, especially given your expertise at Expel. Verifiers' modular design (e.g., rubrics for verifiable rewards, async GRPO training) aligns well with cybersecurity needs like simulating attacks or verifying defenses, and contributing could fill the gaps you mentioned.

### Suggested Good First Projects Using Verifiers

Verifiers is ideal for your goals because it emphasizes verifiable rewards (e.g., via rubrics combining code execution, LLM judges, or custom parsers) and modular environments (installable as packages). You can start small by creating SingleTurnEnv or MultiTurnEnv setups for security tasks, then scale to full RL training with GRPOTrainer. Focus on domains like threat detection, policy verification, or model safety to address gaps.

Here are three beginner-friendly project ideas, tailored to cybersecurity and alignment. Each includes steps to implement, estimated scope (assuming basic Python/RL knowledge), and how it helps the community. Start by installing Verifiers (pip install verifiers) and exploring example scripts on GitHub.

1. **Anomaly Detection Environment for Network Logs (Cybersecurity Focus)**
   - **Description**: Build a SingleTurnEnv where an LLM agent analyzes synthetic network logs (e.g., from datasets like CIC-IDS-2017) to detect anomalies like intrusions. Use verifiers to score detections against ground-truth labels, rewarding accuracy in identifying threats (e.g., DDoS, SQL injection). This fills a gap in RL verifiers for real-time security monitoring.
   - **Why a Good First Project**: Simple to prototype—no multi-turn needed initially. Extends to tool-use (e.g., integrating search APIs for threat intel).
   - **Implementation Steps**:
     - Create a custom environment module: Define a dataset loader for logs, a protocol for agent prompts (e.g., "Classify this log as benign/malicious"), and a Rubric verifier (e.g., weighted functions: 70% for correct classification via regex matching, 30% for explanation quality via LLM judge).
     - Install as a module: vf-install your-env-name.
     - Train: Use GRPOTrainer on a small model like Qwen-7B with async rollouts. Example script: Adapt the math verifier example, replacing math problems with log samples.
     - Scope: 1-2 weeks part-time; generate synthetic data via Verifiers' tools.
   - **Community Impact**: Submit as a PR to the environments/ directory. This could jumpstart RL for intrusion detection, aligning with Prime Intellect's open-source ethos.
2. **Policy Verification Agent for Security Configurations (Model Safety/Alignment Focus)**
   - **Description**: Develop a ToolEnv where the agent verifies cybersecurity policies (e.g., firewall rules or access controls) against simulated configs. Verifiers check for compliance (e.g., "Does this config block unauthorized ports?") using code execution (e.g., Python scripts simulating network flows) or rubric-based scoring. Extend to alignment by rewarding agents that avoid "unsafe" actions like bypassing rules.
   - **Why a Good First Project**: Leverages Verifiers' tool-calling strengths (e.g., multi-step tools inspired by Deep Research). Ties into model safety by ensuring agents produce verifiable, non-harmful outputs.
   - **Implementation Steps**:
     - Define the env: Use datasets like synthetic policy files; protocol prompts agent to "Audit this config for vulnerabilities."
     - Verifiers: Combine code tests (e.g., exec a sim script) with safety checks (e.g., penalize if output suggests exploits).
     - Train: Fine-tune on 1-2 GPUs with prime-rl for decentralized scaling if needed.
     - Scope: 2-3 weeks; start with CLI evals (vf-eval) before full training.
   - **Community Impact**: Share via Environments Hub as a "security-policy-verifier" recipe. This addresses alignment gaps by providing verifiable rewards for safe reasoning in security contexts, potentially inspiring red-teaming for LLMs.
3. **Red-Teaming Simulator for LLM Safety in Cyber Scenarios (Alignment and Security Focus)**
   - **Description**: Create a MultiTurnEnv simulating adversarial interactions, like an agent probing for vulnerabilities in a mock system (e.g., web app). Verifiers score based on ethical bounds (e.g., reward discovery but penalize harmful exploits) using rubrics for alignment (e.g., check for jailbreak attempts). This bridges cybersecurity with model safety, filling gaps in verifiable RL for ethical hacking.
   - **Why a Good First Project**: Builds on Verifiers' multi-turn support; scalable from single-turn evals to full agents.
   - **Implementation Steps**:
     - Env setup: Use PubMedQA-style traces but for cyber (e.g., CTF challenges as datasets); add tools for "attacks" like SQL queries.
     - Verifiers: Rubric with functions for success (e.g., flag captured) and safety (e.g., LLM judge for harm).
     - Train: Use async GRPO for interactive rollouts; integrate with SYNTHETIC datasets for verified traces.
     - Scope: 3-4 weeks; prototype with example tool-use scripts from the repo.
   - **Community Impact**: Fork the repo, add your env, and PR. This could catalyze open-source RL for alignment in security, e.g., by contributing to Prime Intellect's INTELLECT models.

To contribute broadly: Reach out to Will Brown (@willccbb) on X about your ideas—he's active and encourages hackable extensions. Focus on creating shareable rubrics/datasets for security verifiers, as the library lacks domain-specific ones. If you generate synthetic data (e.g., via Verifiers' generation tools), upload to Hugging Face for community use. This aligns with filling gaps in RL for security and safety, potentially leading to collaborations with Prime Intellect. If you share progress, it could inspire others!

### Research on Use of Verifiers Library in Cybersecurity (version 2)

Based on extensive searches across X (using both semantic and keyword-based queries targeting terms like "verifiers library" combined with "cybersecurity," "security," "safety," or "alignment"), web searches focused on GitHub repositories and related discussions, and direct browsing of the Verifiers GitHub issues, documentation, and the integrated Prime-rl repository, there is no publicly documented evidence of anyone using the Verifiers RL library specifically for cybersecurity tasks as of August 24, 2025.

- **X Searches**: No posts from key accounts like or mention Verifiers in the context of security domains. Broader semantic searches returned general cybersecurity content (e.g., checklists, frameworks like NIST, or tools like Scapy), but none linked to Verifiers. One post referenced the Verifiers GitHub repo in a discussion about open-source RL tools, but it was unrelated to security.
  @willccbb
  @PrimeIntellect
- **Web and GitHub Searches**: Results highlighted Verifiers' use in general RL tasks (e.g., math reasoning, calculator agents, or procedural datasets), but no repositories, papers, or projects applied it to cybersecurity, model safety, or alignment. Related RL libraries (e.g., for RLHF or verifier-free methods) were mentioned, but not in security contexts.
- **Repository and Docs Review**: The Verifiers issues and pull requests contain no discussions on security applications. The documentation emphasizes modular environments for tasks like math, coding, and STEM questions, with no security examples. Prime-rl's README focuses on decentralized training without security-specific use cases.

This suggests a genuine gap in domain-specific applications for cybersecurity—aligning perfectly with your goal to contribute. Verifiers' modular design (e.g., environments as installable modules with custom rubrics and verifiers) makes it well-suited for extension, and the community (including Will Brown) has encouraged contributions via the Environments Hub for sharing verifiable rewards and tasks.

### Suggested Good First Projects Using Verifiers (version 2)

As a principal developer at Expel, you could leverage your expertise in cybersecurity to create verifiable RL environments that simulate security scenarios. Verifiers excels at tasks with programmatic rewards (e.g., rubrics for scoring outputs against ground truth), making it ideal for security where outcomes can be verified via simulations, datasets, or rules. Start small: Fork the repo, build a custom environment module, test it locally with GRPOTrainer, and submit a PR or share via the Environments Hub (in private beta, but Brown has invited contributions).

Here are three beginner-friendly project ideas, progressing from simple to more complex. Each includes implementation steps using Verifiers' components (e.g., SingleTurnEnv for one-shot tasks, MultiTurnEnv for interactive ones, ToolEnv for tool integration). Assume you have the library installed (pip install verifiers-rl) and access to datasets like those from Kaggle or NIST.

1. **Phishing Email Detection Environment (Single-Turn, Classification Task)**
   - **Why it's a good first project**: Phishing is a core cybersecurity issue with verifiable ground truth (e.g., labeled datasets). This fills a gap in RL for binary/multiclass security classification, helping train LLMs to reason about threats without human labels.
   - **Project Goal**: Train an LLM agent to classify emails as phishing or benign, with rewards based on accuracy against known labels.
   - **Implementation Steps**:
     - Use SingleTurnEnv as the base: Load a dataset (e.g., Enron-Spam or UCI Phishing) via Hugging Face's datasets.
     - Define a Rubric for rewards: Weighted functions like exact match on labels (e.g., +1 for correct, -0.5 for false positives) or similarity scores for explanations.
     - Add a custom parser for outputs (e.g., extract "phishing" or "benign" from agent responses).
     - Train with GRPO: Use GRPOTrainer on a small GPU setup, starting with a base model like Qwen-7B. Example script: Adapt the library's examples/tool_use_rl.py to generate synthetic phishing traces.
     - **Contribution Angle**: Package as a module (vf-install expel-phishing-env) and share rubrics for threat indicators (e.g., URL checks). This could extend to model safety by verifying non-harmful classifications.
     - **Time Estimate**: 1-2 days for a prototype; test on CPU first.
2. **Vulnerability Assessment in Code Snippets (Multi-Turn, Reasoning Task)**
   - **Why it's a good first project**: Builds on Verifiers' strength in coding tasks but applies to security (e.g., detecting CWE vulnerabilities). This addresses gaps in RL for code security, useful for alignment by rewarding safe code suggestions.
   - **Project Goal**: Create a multi-turn environment where the agent queries code snippets, identifies vulnerabilities (e.g., SQL injection), and suggests fixes, verified against static analysis tools.
   - **Implementation Steps**:
     - Use MultiTurnEnv for interactive reasoning: Agent takes turns analyzing code, with episode limits (e.g., 5 turns).
     - Integrate tools via ToolEnv: Simulate calls to mock security tools (e.g., Bandit for Python vulns) or use APIs like OpenAI for initial proxies.
     - Verifiers/Rewards: Rubric with code execution tests (e.g., +1 if fix passes unit tests, penalties for unpatched vulns). Use datasets like Big-Vul or CWE samples.
     - Training: Async rollouts with GRPOTrainer; generate synthetic data via the library's CLI (vf-generate).
     - **Contribution Angle**: Add to Environments Hub as a security rubric pack (e.g., for OWASP Top 10). This could tie into model alignment by penalizing outputs that introduce new risks. PR to the repo for a "security" example in docs.
     - **Time Estimate**: 3-5 days; scale up with prime-rl for distributed training if needed.
3. **Red-Teaming for Model Safety/Alignment (Interactive Game Environment)**
   - **Why it's a good first project**: Directly targets safety and alignment gaps, using Verifiers' verifiable rewards to train LLMs against adversarial prompts (e.g., jailbreaks). This is timely for cybersecurity in AI systems, like detecting prompt injections.
   - **Project Goal**: Simulate a red-team/blue-team game where one agent attacks (generates harmful prompts) and another defends (verifies safety), with rewards for alignment adherence.
   - **Implementation Steps**:
     - Build on InteractiveEnv (or custom multi-agent setup): Agent interacts with a simulated "system" to test responses.
     - Rewards: Use rubric-based verifiers like keyword checks for harmful content (e.g., from Llama Guard) or LLM judges for nuanced safety (e.g., +1 for safe refusals). Datasets: Use Anthropic's red-teaming sets or HarmBench.
     - Add multi-step tool calling: Agent uses "safety check" tools (e.g., mock filters).
     - Training: Full RL loop with GRPOTrainer; start with offline data, then online rollouts. Example: Adapt Verifiers' Wordle solver for a "jailbreak puzzle."
     - **Contribution Angle**: Share as an open rubric for alignment verifiers (e.g., cryptographic proofs via toploc integration). This could help Prime Intellect's ecosystem for safe decentralized AI. Reach out to on X to collaborate on integration.
       @willccbb
     - **Time Estimate**: 4-7 days; focus on verifier reliability to avoid drift.

These projects are hackable and scalable—start with local evals (vf-eval) to verify setups. To contribute: Join the Prime Intellect Discord or X discussions for feedback; Brown has emphasized open-source collaboration. If successful, they could seed larger efforts like SYNTHETIC-3 with security traces. Let me know if you'd like code snippets or help refining these!
