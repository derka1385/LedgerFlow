#!/bin/sh
set -eu
test "$(docker info --format '{{.DefaultRuntime}}')" = runsc
docker image inspect python:3.12-slim >/dev/null
