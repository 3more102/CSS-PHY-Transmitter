#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
python3 "$ROOT/matlab/vector_generation/generate_vectors.py"
python3 "$ROOT/matlab/mse/mse_analysis.py"
python3 -m unittest discover -s "$ROOT/tests" -p 'test_*.py' -v
