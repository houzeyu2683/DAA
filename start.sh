#!/usr/bin/env bash
# set -euo pipefail

# cd "$(dirname "$0")"
# unset SSL_CERT_FILE

conda run -n DAA chainlit run frontend/application.py -w
