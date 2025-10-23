"""Endpoint configurations for vf-eval command."""

ENDPOINTS = {
    # OpenAI models
    "gpt-5-mini": {
        "model": "gpt-5-mini",
        "url": "https://api.openai.com/v1",
        "key": "OPENAI_API_KEY",
    },
    "gpt-5": {
        "model": "gpt-5",
        "url": "https://api.openai.com/v1",
        "key": "OPENAI_API_KEY",
    },
    "gpt-3.5-turbo": {
        "model": "gpt-3.5-turbo",
        "url": "https://api.openai.com/v1",
        "key": "OPENAI_API_KEY",
    },
    # Anthropic models
    "claude-3-opus": {
        "model": "claude-3-opus-20240229",
        "url": "https://api.anthropic.com/v1",
        "key": "ANTHROPIC_API_KEY",
    },
    "claude-3-sonnet": {
        "model": "claude-3-5-sonnet-20241022",
        "url": "https://api.anthropic.com/v1",
        "key": "ANTHROPIC_API_KEY",
    },
    "claude-3-haiku": {
        "model": "claude-3-haiku-20240307",
        "url": "https://api.anthropic.com/v1",
        "key": "ANTHROPIC_API_KEY",
    },
    # DeepSeek models
    "deepseek-chat": {
        "model": "deepseek-chat",
        "url": "https://api.deepseek.com/v1",
        "key": "DEEPSEEK_API_KEY",
    },
    "deepseek-reasoner": {
        "model": "deepseek-reasoner",
        "url": "https://api.deepseek.com/v1",
        "key": "DEEPSEEK_API_KEY",
    },
    # Local models (for self-hosted endpoints)
    "local": {
        "model": "local-model",
        "url": "http://localhost:8000/v1",
        "key": "EMPTY",
    },
}
