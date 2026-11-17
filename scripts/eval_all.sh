#!/usr/bin/env bash
# Evaluate every model in models.yaml (or the ones given) on all Bridge tasks, then summarize.
#   scripts/eval_all.sh                 # all models
#   scripts/eval_all.sh e0 e2_340_s2    # selected models
# GPU: set CUDA_VISIBLE_DEVICES before running.
set -euo pipefail
cd "$(dirname "$0")/.."
if [ $# -eq 0 ]; then
  set -- $(python -c "import yaml;print(' '.join(yaml.safe_load(open('models.yaml'))['models']))")
fi
for m in "$@"; do
  python scripts/eval.py --model "$m"
done
python scripts/summarize.py
