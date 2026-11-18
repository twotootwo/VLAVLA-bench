#!/usr/bin/env bash
# Full evaluation in comparison-friendly order: for each eval seed, every model x every task.
# After the first seed finishes, all models already have one complete 24-placement pass per task.
# Resumable: scripts/eval.py skips runs whose episodes.jsonl is complete.
#   VLAVLA_CKPT_DIR=/workspace/ckpt nohup scripts/run_all.sh > run_all.log 2>&1 &
#   MODELS="e0 e3_340" SEEDS="1234 1235" scripts/run_all.sh
set -uo pipefail
cd "$(dirname "$0")/.."
PY=${PY:-.venv/bin/python}
MODELS=${MODELS:-$($PY -c "import yaml;print(' '.join(yaml.safe_load(open('models.yaml'))['paper_models']))")}
SEEDS=${SEEDS:-$($PY -c "import yaml;print(' '.join(map(str,yaml.safe_load(open('configs/bridge.yaml'))['common']['eval_seeds'])))")}
TASKS=${TASKS:-$($PY -c "import yaml;print(' '.join(yaml.safe_load(open('configs/bridge.yaml'))['tasks']))")}
echo "models: $MODELS | seeds: $SEEDS | tasks: $TASKS"
fail=0
for s in $SEEDS; do
  for m in $MODELS; do
    for t in $TASKS; do
      echo "[$(date '+%F %T')] start $m/$t/seed$s"
      if ! $PY scripts/eval.py --model "$m" --task "$t" --eval-seed "$s"; then
        echo "[$(date '+%F %T')] FAILED $m/$t/seed$s"; fail=$((fail+1))
      fi
    done
  done
  $PY scripts/summarize.py > /dev/null && echo "[$(date '+%F %T')] seed $s done, results/summary.csv updated"
done
echo "[$(date '+%F %T')] all done, failed runs: $fail"
