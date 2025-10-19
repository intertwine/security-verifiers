#!/usr/bin/env python3
"""
Robust model routing for OpenAI and OpenRouter.

Handles model name resolution with:
- OpenRouter API model list fetching (with caching)
- Fuzzy matching for common shortcuts
- Fallback to hardcoded mappings
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

try:
    import requests
except ImportError:
    requests = None  # type: ignore[assignment]


# Hardcoded fallback mappings (used if API is unavailable)
FALLBACK_MODEL_MAP = {
    "qwen-2.5-7b": "qwen/qwen-2.5-7b-instruct",
    "qwen-2.5-72b": "qwen/qwen-2.5-72b-instruct",
    "qwen-2.5-coder-32b": "qwen/qwen-2.5-coder-32b-instruct",
    "qwen3-14b": "qwen/qwen3-14b",
    "qwen3-8b": "qwen/qwen3-8b",
    "llama-3.1-8b": "meta-llama/llama-3.1-8b-instruct",
    "llama-3.1-70b": "meta-llama/llama-3.1-70b-instruct",
    "claude-3.5-sonnet": "anthropic/claude-3.5-sonnet",
    "claude-3-opus": "anthropic/claude-3-opus",
}

# Cache directory for OpenRouter model list
CACHE_DIR = Path(__file__).parent.parent / ".cache"
CACHE_FILE = CACHE_DIR / "openrouter_models.json"
CACHE_DURATION = 86400  # 24 hours in seconds


def fetch_openrouter_models() -> list[str] | None:
    """
    Fetch list of available models from OpenRouter API.

    Returns:
        List of model IDs or None if fetch fails
    """
    if requests is None:
        return None

    try:
        response = requests.get(
            "https://openrouter.ai/api/v1/models",
            timeout=5,
        )
        response.raise_for_status()
        data = response.json()
        return [model["id"] for model in data.get("data", [])]
    except Exception:
        return None


def get_cached_models() -> list[str] | None:
    """
    Get cached OpenRouter models if cache is valid.

    Returns:
        List of model IDs or None if cache is invalid/missing
    """
    if not CACHE_FILE.exists():
        return None

    try:
        # Check cache age
        cache_age = time.time() - CACHE_FILE.stat().st_mtime
        if cache_age > CACHE_DURATION:
            return None

        with CACHE_FILE.open() as f:
            data = json.load(f)
            return data.get("models", [])
    except Exception:
        return None


def cache_models(models: list[str]) -> None:
    """
    Cache OpenRouter models to disk.

    Args:
        models: List of model IDs to cache
    """
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        with CACHE_FILE.open("w") as f:
            json.dump({"models": models, "cached_at": time.time()}, f)
    except Exception:
        pass  # Silently fail if caching doesn't work


def find_best_match(shorthand: str, available_models: list[str]) -> str | None:
    """
    Find the best matching model ID for a shorthand name.

    Uses fuzzy matching to find models that contain the shorthand.
    Prioritizes exact matches and shorter model IDs.

    Args:
        shorthand: Short model name (e.g., "qwen3-14b")
        available_models: List of full model IDs from OpenRouter

    Returns:
        Best matching model ID or None if no match found
    """
    shorthand_lower = shorthand.lower()

    # First try exact match
    if shorthand in available_models:
        return shorthand

    # Try fuzzy matching
    matches = []
    for model_id in available_models:
        model_lower = model_id.lower()

        # Check if shorthand is in the model ID
        if shorthand_lower in model_lower:
            # Prioritize non-free models (no ":free" suffix)
            is_free = model_id.endswith(":free")
            # Prefer shorter model IDs (they're usually the canonical versions)
            priority = (0 if not is_free else 1, len(model_id))
            matches.append((priority, model_id))

    if matches:
        # Sort by priority (non-free first, then by length)
        matches.sort()
        return matches[0][1]

    return None


def resolve_openrouter_model(model: str) -> str:
    """
    Resolve a model shorthand to an OpenRouter model ID.

    Strategy:
    1. Check if model is already a full path (contains "/")
    2. Try cached OpenRouter model list with fuzzy matching
    3. Try fetching fresh model list from OpenRouter API
    4. Fall back to hardcoded mappings
    5. Return original model name if all else fails

    Args:
        model: Model shorthand or full ID

    Returns:
        Resolved OpenRouter model ID
    """
    # If already a full path, return as-is
    if "/" in model:
        return model

    # Try hardcoded mapping first (fastest)
    if model in FALLBACK_MODEL_MAP:
        return FALLBACK_MODEL_MAP[model]

    # Try cached models
    cached = get_cached_models()
    if cached:
        match = find_best_match(model, cached)
        if match:
            return match

    # Try fetching fresh models
    fresh = fetch_openrouter_models()
    if fresh:
        # Update cache
        cache_models(fresh)
        match = find_best_match(model, fresh)
        if match:
            return match

    # No match found, return original
    # (OpenRouter will give a clear error if it's invalid)
    return model


def get_client_for_model(model: str) -> tuple:
    """
    Get appropriate OpenAI-compatible client for the given model.

    Returns:
        tuple: (client, effective_model_name)

    Routing logic:
    - OpenAI models (gpt-*, o1-*): Use OpenAI directly
    - Other models: Use OpenRouter as proxy (requires OPENROUTER_API_KEY)

    Environment variables:
    - OPENAI_API_KEY: For OpenAI models
    - OPENROUTER_API_KEY: For non-OpenAI models via OpenRouter
    """
    from openai import OpenAI

    # Check if this is an OpenAI model
    openai_prefixes = ("gpt-", "o1-", "text-davinci", "text-curie", "text-babbage", "text-ada")
    is_openai = model.startswith(openai_prefixes)

    if is_openai:
        # Use standard OpenAI client
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise SystemExit("OPENAI_API_KEY not set in environment")
        return OpenAI(api_key=api_key), model
    else:
        # Use OpenRouter for non-OpenAI models
        openrouter_key = os.environ.get("OPENROUTER_API_KEY")
        if not openrouter_key:
            raise SystemExit(
                f"Model '{model}' is not an OpenAI model. "
                "Please set OPENROUTER_API_KEY to use OpenRouter as a proxy.\n"
                "Get your key at: https://openrouter.ai/keys"
            )

        # Resolve model name to OpenRouter format
        openrouter_model = resolve_openrouter_model(model)

        client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=openrouter_key,
        )

        return client, openrouter_model
