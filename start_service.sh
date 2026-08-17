#!/bin/bash
set -e

CONDA_BASE=$(conda info --base)
source "$CONDA_BASE/etc/profile.d/conda.sh"
conda activate DAA

python website.py
