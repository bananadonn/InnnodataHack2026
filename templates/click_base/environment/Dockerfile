# Base environment for every pallets/click task package.
# Self-contained: public base image, upstream clone pinned to click 8.5.1.
# /app is left as a git working tree at base_commit (solve.sh and the grader use `git apply`).
FROM python:3.12-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends git ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN git clone https://github.com/pallets/click.git . \
    && git checkout cf19179e8e2fd54c601378cec9e0d21bb12b6fb1

RUN pip install --no-cache-dir -e . pytest==9.0.2
