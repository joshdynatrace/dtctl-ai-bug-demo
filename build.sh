#!/usr/bin/env bash
set -euo pipefail

docker buildx build --platform linux/amd64,linux/arm64 -t arc-backend:latest ./backend
docker buildx build --platform linux/amd64,linux/arm64 -t arc-frontend:latest ./frontend
docker buildx build --platform linux/amd64,linux/arm64 -t arc-load-generator:latest ./load-generator
