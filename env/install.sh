#!/usr/bin/env bash
# Create the evaluation environment: LAPA (JAX) + SIMPLER (SAPIEN/ManiSkill2_real2sim).
# Follows the official LAPA README and SimplerEnv README; both live in third_party/LAPA @46aca51.
#   bash env/install.sh            # creates ./.venv
set -euo pipefail
cd "$(dirname "$0")/.."

git submodule update --init third_party/LAPA
bash scripts/apply_patches.sh   # see patches/README.md

# Python 3.10 venv with uv (tested on RTX 5090, driver 580, Ubuntu 24.04).
# env/requirements-5090.txt = official LAPA requirements.txt with the changes needed for sm_120
# (each marked [5090] with the reason).
command -v uv >/dev/null || pip install uv
uv venv -p 3.10 .venv
uv pip install -p .venv/bin/python -r env/requirements-5090.txt
# SIMPLER: ManiSkill2 real-to-sim envs, then simpler_env (both vendored inside the LAPA repo)
uv pip install -p .venv/bin/python -e third_party/LAPA/SimplerEnv/ManiSkill2_real2sim \
  -e third_party/LAPA/SimplerEnv "numpy<2" "gymnasium==0.29.1" "setuptools<70"
uv pip freeze -p .venv/bin/python > env/freeze-$(hostname).txt

echo "done. next: source .venv/bin/activate && python env/check_gpu.py"
