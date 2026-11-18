#!/usr/bin/env bash
# Create the evaluation environment: LAPA (JAX) + SIMPLER (SAPIEN/ManiSkill2_real2sim).
# Follows the official LAPA README and SimplerEnv README; both live in third_party/LAPA @46aca51.
#   bash env/install.sh            # env name: lapa
#   ENV_NAME=foo bash env/install.sh
set -euo pipefail
cd "$(dirname "$0")/.."
ENV_NAME=${ENV_NAME:-lapa}

git submodule update --init third_party/LAPA
bash scripts/apply_patches.sh   # see patches/README.md

eval "$(conda shell.bash hook)"
conda create -n "$ENV_NAME" python=3.10 -y
conda activate "$ENV_NAME"

# LAPA model code (jax[cuda12]==0.4.23, flax, tux, tensorflow ...)
pip install -r third_party/LAPA/requirements.txt
# SIMPLER: ManiSkill2 real-to-sim envs, then simpler_env (both vendored inside the LAPA repo)
pip install -e third_party/LAPA/SimplerEnv/ManiSkill2_real2sim
pip install -e third_party/LAPA/SimplerEnv
# this repo's scripts
pip install pyyaml huggingface_hub

echo "done. next: conda activate $ENV_NAME && python env/check_gpu.py"
