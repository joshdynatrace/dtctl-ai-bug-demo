#!/usr/bin/env bash
set -euo pipefail

docker buildx build --platform linux/amd64,linux/arm64 -t arc-backend:latest ./backend
docker buildx build --platform linux/amd64,linux/arm64 -t arc-frontend:latest ./frontend
docker buildx build --platform linux/amd64,linux/arm64 -t arc-load-generator:latest ./load-generator

# example to build and push:
# docker buildx build --platform linux/amd64,linux/arm64 -t jhendrick/arc-backend:latest ./backend --push
# docker buildx build --platform linux/amd64,linux/arm64 -t jhendrick/arc-frontend:latest ./frontend --push
# docker buildx build --platform linux/amd64,linux/arm64 -t jhendrick/arc-load-generator:latest ./load-generator --push
