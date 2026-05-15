FROM python:3.12-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl jq ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir semgrep==1.140.0 yq

# Install OPA and kube-linter at runtime-pinned versions when building real images.
# The README documents the exact version source and validation command.
WORKDIR /workspace
