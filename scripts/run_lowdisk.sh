#!/usr/bin/env bash
# Model-major runner for servers whose disk cannot hold every checkpoint (~13.6 GB each):
# for each model: download -> all seeds x tasks -> delete the checkpoint.
# Resumable (eval.py skips complete runs). Seeds run in the given order, so put the
# reproducibility seed first, e.g.
#   SEEDS="1234 1239 1240" VLAVLA_CKPT_DIR=/workspace/ckpt nohup scripts/run_lowdisk.sh > run_lowdisk.log 2>&1 &
set -uo pipefail
cd "$(dirname "$0")/.."
PY=${PY:-.venv/bin/python}
MODELS=${MODELS:-$($PY -c "import yaml;print(' '.join(yaml.safe_load(open('models.yaml'))['paper_models']))")}
SEEDS=${SEEDS:?set SEEDS}
TASKS=${TASKS:-$($PY -c "import yaml;print(' '.join(yaml.safe_load(open('configs/bridge.yaml'))['tasks']))")}
CKPT=${VLAVLA_CKPT_DIR:?set VLAVLA_CKPT_DIR}
echo "models: $MODELS | seeds: $SEEDS | tasks: $TASKS | ckpt: $CKPT"
$PY scripts/download.py base || { echo "base download failed"; exit 1; }
fail=0
for m in $MODELS; do
  echo "[$(date '+%F %T')] download $m"
  if ! $PY scripts/download.py "$m"; then echo "[$(date '+%F %T')] DOWNLOAD FAILED $m"; fail=$((fail+1)); continue; fi
  for s in $SEEDS; do
    for t in $TASKS; do
      echo "[$(date '+%F %T')] start $m/$t/seed$s"
      if ! $PY scripts/eval.py --model "$m" --task "$t" --eval-seed "$s"; then
        echo "[$(date '+%F %T')] FAILED $m/$t/seed$s"; fail=$((fail+1))
      fi
    done
  done
  rm -rf "${CKPT:?}/$m" && echo "[$(date '+%F %T')] removed checkpoint $m"; df -h / | tail -1
  $PY scripts/summarize.py > /dev/null
done
echo "[$(date '+%F %T')] all done, failed runs: $fail"
