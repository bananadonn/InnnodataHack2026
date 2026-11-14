# Harbor environment — TOY example. The synthetic repo `toycorp/stringkit` has no upstream, so its
# base state (feature ABSENT) is embedded below and decoded at build time — no clone, no network.
# A real task would instead clone a pinned base_commit here. The three files decode to:
#   pyproject.toml, stringkit/__init__.py (slugify only), tests/test_slugify.py (the P2P test).
# The build leaves /app as a git working tree at the base state, so solve.sh and the test patch
# apply with `git apply` and the oracle/nop baselines score 1.0 / 0.0.
FROM python:3.12-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PIP_DISABLE_PIP_VERSION_CHECK=1 PIP_NO_CACHE_DIR=1 DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends git ca-certificates bash && rm -rf /var/lib/apt/lists/*
WORKDIR /app

# --- base repo contents (feature absent), embedded as base64 ---
RUN set -eux; mkdir -p stringkit tests; \
    echo 'W2J1aWxkLXN5c3RlbV0KcmVxdWlyZXMgPSBbInNldHVwdG9vbHM+PTYxIl0KYnVpbGQtYmFja2VuZCA9ICJzZXR1cHRvb2xzLmJ1aWxkX21ldGEiCgpbcHJvamVjdF0KbmFtZSA9ICJzdHJpbmdraXQiCnZlcnNpb24gPSAiMC4xLjAiCmRlc2NyaXB0aW9uID0gIkEgdGlueSBzdHJpbmctdXRpbGl0aWVzIGxpYnJhcnkgKHRveSBleGFtcGxlIGZvciBUcmFjayAxKS4iCnJlcXVpcmVzLXB5dGhvbiA9ICI+PTMuOSIKClt0b29sLnNldHVwdG9vbHNdCnBhY2thZ2VzID0gWyJzdHJpbmdraXQiXQo=' | base64 -d > pyproject.toml; \
    echo 'IiIiQSB0aW55IHN0cmluZy11dGlsaXRpZXMgbGlicmFyeSAodG95IGV4YW1wbGUpLiIiIgppbXBvcnQgcmUKCl9fYWxsX18gPSBbInNsdWdpZnkiXQoKCmRlZiBzbHVnaWZ5KHRleHQpOgogICAgIiIiTG93ZXJjYXNlLCBzdHJpcCwgYW5kIGh5cGhlbmF0ZSBhIHN0cmluZyBmb3IgdXNlIGluIFVSTHMuIiIiCiAgICB0ZXh0ID0gdGV4dC5zdHJpcCgpLmxvd2VyKCkKICAgIHRleHQgPSByZS5zdWIociJbXmEtejAtOV0rIiwgIi0iLCB0ZXh0KQogICAgcmV0dXJuIHRleHQuc3RyaXAoIi0iKQo=' | base64 -d > stringkit/__init__.py; \
    echo 'ZnJvbSBzdHJpbmdraXQgaW1wb3J0IHNsdWdpZnkKCgpkZWYgdGVzdF9zbHVnaWZ5X2Jhc2ljKCk6CiAgICBhc3NlcnQgc2x1Z2lmeSgiSGVsbG8gV29ybGQiKSA9PSAiaGVsbG8td29ybGQiCgoKZGVmIHRlc3Rfc2x1Z2lmeV9zdHJpcHNfcHVuY3R1YXRpb24oKToKICAgIGFzc2VydCBzbHVnaWZ5KCIgIENhZmUgZGVsIE1hciEhICAiKSA9PSAiY2FmZS1kZWwtbWFyIgo=' | base64 -d > tests/test_slugify.py

# --- make /app a git tree at the base state ---
RUN git init --quiet \
    && git config user.email bench@local && git config user.name bench \
    && git config core.autocrlf false \
    && git add -A && git commit --quiet -m "base state" \
    && git config --global --add safe.directory /app

# --- toolchain: install the package + pytest into a venv ---
RUN python -m venv /app/.venv \
    && /app/.venv/bin/pip install -e . "pytest>=8" \
    && /app/.venv/bin/python -c "import stringkit; assert hasattr(stringkit,'slugify'); print('base import ok')"
CMD ["/bin/bash"]
