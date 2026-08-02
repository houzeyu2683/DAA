#!/usr/bin/env bash
# set -euo pipefail

# cd "$(dirname "$0")"

conda run -n DAA chainlit run frontend/application.py -w
