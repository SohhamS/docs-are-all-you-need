#!/usr/bin/env bash
# Dispatch on the first argument so one image serves every role.
#
#   docker run <image> serve
#   docker run <image> run /docs/guide.md --version v2.3
#   docker run <image> show run_abc123
#
# Any other argument is passed straight through, so `bash` or `dv --help`
# work for debugging.

set -euo pipefail

CONFIG="${DV_CONFIG:-/app/config/default.yaml}"

case "${1:-serve}" in
    serve)
        shift || true
        exec dv serve --config "$CONFIG" "$@"
        ;;
    run)
        shift
        exec dv run --config "$CONFIG" "$@"
        ;;
    show)
        shift
        exec dv show --config "$CONFIG" "$@"
        ;;
    *)
        exec "$@"
        ;;
esac
