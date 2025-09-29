# Logging Authentication FAQ

Common questions about authentication for Security Verifiers logging.

## General Questions

### Q: Do I need a Weights & Biases account to use Security Verifiers?

**A:** No, you have two options:

1. **Without logging**: Set `WEAVE_DISABLED=true` to run without any logging
2. **With logging**: Create a free W&B account at [wandb.ai](https://wandb.ai) for automatic tracing

### Q: Is the W&B account free?

**A:** Yes! W&B offers a generous free tier that includes:

- Unlimited public projects
- 100GB of storage
- Full Weave tracing features

### Q: What data is sent to W&B?

**A:** When Weave is enabled, it sends:

- Environment initialization metadata
- Model evaluation traces
- Input/output pairs
- Reward calculations
- Performance metrics

Your actual model API keys (OpenAI, etc.) are **never** sent to W&B.

## Setup Questions

### Q: How do I get my W&B API key?

**A:** Three simple steps:

1. Sign up at [wandb.ai](https://wandb.ai)
2. Go to [wandb.ai/authorize](https://wandb.ai/authorize)
3. Copy your API key

### Q: Where should I put my API key?

**A:** You have several options:

```bash
# Option 1: Environment variable (recommended for automation)
export WANDB_API_KEY=your-key-here

# Option 2: .env file (recommended for projects)
echo "WANDB_API_KEY=your-key-here" >> .env

# Option 3: Interactive login (for development)
wandb login  # Paste key when prompted
```

### Q: Can I use different W&B accounts for different projects?

**A:** Yes! You can:

- Change `WANDB_API_KEY` per project
- Use different `.env` files
- Run `wandb login` to switch accounts

## Running Without W&B

### Q: How do I disable all logging?

**A:** Set the environment variable:

```bash
export WEAVE_DISABLED=true
```

Or in your `.env` file:

```env
WEAVE_DISABLED=true
```

### Q: Can I run evaluations offline?

**A:** Yes! With `WEAVE_DISABLED=true`, everything runs locally with no network calls to W&B.

### Q: What functionality do I lose without W&B?

**A:** Without W&B/Weave, you won't have:

- Automatic trace visualization
- Performance dashboards
- Token usage tracking
- Error debugging UI
- Team collaboration features

But all core functionality (evaluations, rewards, etc.) works normally.

## CI/CD Questions

### Q: How do I set up authentication in GitHub Actions?

**A:** Add your API key as a secret:

1. Go to Settings → Secrets → Actions
2. Add `WANDB_API_KEY` with your key
3. Use in workflow:

```yaml
jobs:
  test:
    runs-on: ubuntu-latest
    env:
      WANDB_API_KEY: ${{ secrets.WANDB_API_KEY }}
    steps:
      - run: python scripts/eval_network_logs.py
```

### Q: How do I handle authentication in Docker?

**A:** Pass the API key as an environment variable:

```bash
# Build time (not recommended - key gets baked in)
docker build --build-arg WANDB_API_KEY=$WANDB_API_KEY .

# Runtime (recommended)
docker run -e WANDB_API_KEY=$WANDB_API_KEY my-image

# Or use env file
docker run --env-file=.env my-image
```

### Q: What about GitLab CI?

**A:** Add as a CI/CD variable:

1. Go to Settings → CI/CD → Variables
2. Add `WANDB_API_KEY` as a masked variable
3. It's automatically available in pipelines

## Troubleshooting

### Q: I get "Not logged in" errors

**A:** Check these in order:

1. **Is your API key set?**

   ```bash
   echo $WANDB_API_KEY
   ```

2. **Is it valid?**

   ```bash
   wandb login --relogin
   ```

3. **Can you connect to W&B?**

   ```python
   import wandb
   wandb.login()
   ```

### Q: Weave isn't creating traces

**A:** Verify:

1. **API key is set**: `echo $WANDB_API_KEY`
2. **Weave isn't disabled**: `echo $WEAVE_DISABLED` (should be empty or "false")
3. **Auto-init is enabled**: `echo $WEAVE_AUTO_INIT` (should be "true" or empty)

### Q: Can I use a service account?

**A:** Yes! W&B supports service accounts for automation:

1. Create a service account in your team settings
2. Use the service account's API key
3. Set `WANDB_ENTITY=your-team-name`

## Privacy & Security

### Q: Is my data private?

**A:** Depends on your W&B settings:

- **Free tier**: Projects can be public or private (limited private projects)
- **Team/Enterprise**: Unlimited private projects
- **Self-hosted**: Complete control over data

### Q: Can I self-host W&B?

**A:** Yes, W&B offers self-hosted options for enterprises. See [W&B Server](https://docs.wandb.ai/guides/hosting).

### Q: Are my API keys safe?

**A:** Yes:

- OpenAI/HF keys are **never** sent to W&B
- W&B API key is only used for authentication
- Use environment variables or secrets management for production

## Team Collaboration

### Q: How do I share traces with my team?

**A:** Use team projects:

```bash
# Set team/project format
export WEAVE_PROJECT=my-team/security-project

# Team members with access can view at:
# https://wandb.ai/my-team/security-project/weave
```

### Q: Can different team members use different projects?

**A:** Yes! Each person can set their own `WEAVE_PROJECT`:

```bash
# Developer 1
export WEAVE_PROJECT=team/dev-alice

# Developer 2
export WEAVE_PROJECT=team/dev-bob
```

## More Help

- **Full Logging Guide**: [logging-guide.md](logging-guide.md)
- **Quick Reference**: [logging-quick-reference.md](logging-quick-reference.md)
- **W&B Documentation**: [docs.wandb.ai](https://docs.wandb.ai)
- **W&B Support**: [wandb.ai/support](https://wandb.ai/support)
