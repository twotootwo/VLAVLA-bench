# VLAVLA-bench

Benchmark evaluation of the VLAVLA team's LAPA checkpoints
([huggingface.co/capstone-vlavla](https://huggingface.co/capstone-vlavla)) on
[SIMPLER](https://github.com/simpler-env/SimplerEnv) WidowX (Bridge) tasks.

The evaluation code is the **official LAPA code**, used unchanged as a submodule
(`third_party/LAPA`, [LatentActionPretraining/LAPA](https://github.com/LatentActionPretraining/LAPA) @ `46aca51`).
This repo only adds: a model list, the task settings from the official script,
download/run wrappers, and a results summary.

## Layout

```
models.yaml            models to evaluate: name -> HF repo + subfolder
configs/bridge.yaml    4 Bridge tasks; values copied from SimplerEnv/scripts/lapa_bridge.sh
third_party/LAPA/      official LAPA (latent_pretraining/ + SimplerEnv/), pinned commit
patches/               diffs to the official code, if ever needed (none now)
env/install.sh         conda env: LAPA requirements + SimplerEnv
env/check_gpu.py       JAX GPU + SAPIEN render check
scripts/download.py    checkpoints from HF -> checkpoints/
scripts/eval.py        one model x task(s) -> results/<model>/<task>/
scripts/eval_all.sh    all models, then summary
scripts/summarize.py   success table -> results/summary.csv
checkpoints/, results/ git-ignored (except results/summary.csv)
```

## Models

| name | HF repo | subfolder |
|---|---|---|
| e0 | capstone-vlavla/lapa-checkpoints | e0 |
| e2 | capstone-vlavla/e2-checkpoints-for-test | e2 |
| e3 | capstone-vlavla/e3-checkpoints-for-test | e3 |
| e2_340 | capstone-vlavla/lapa-checkpoints-340 | e2_340 |
| e3_340 | capstone-vlavla/lapa-checkpoints-340 | e3_340 |
| e2_340_s2 | capstone-vlavla/lapa-final-e2-object-340 | e2_340_s2 |

`tokenizer.model` and `vqgan` come from the official
[latent-action-pretraining/LAPA-7B-openx](https://huggingface.co/latent-action-pretraining/LAPA-7B-openx).
The action bins (`simpler.csv`) are the official `third_party/LAPA/data/simpler.csv`,
identical to `common/simpler.csv` in the team's HF repos.

## Tasks (SIMPLER Bridge, visual matching, 24 episodes each)

| key | env | max steps |
|---|---|---|
| stack_cube | StackGreenCubeOnYellowCubeBakedTexInScene-v0 | 60 |
| carrot | PutCarrotOnPlateInScene-v0 | 60 |
| spoon | PutSpoonOnTableClothInScene-v0 | 60 |
| eggplant | PutEggplantInBasketScene-v0 | 120 |

## Usage

```bash
git clone --recurse-submodules https://github.com/twotootwo/VLAVLA-bench.git
cd VLAVLA-bench

# 1. environment
bash env/install.sh && conda activate lapa
python env/check_gpu.py

# 2. checkpoints (~13.6 GB per model; private repos need `hf auth login`
#    with read access to the capstone-vlavla org)
export VLAVLA_CKPT_DIR=/big/disk/vlavla_ckpt   # optional, default ./checkpoints
python scripts/download.py base e2_340_s2

# 3. evaluate
export CUDA_VISIBLE_DEVICES=0
python scripts/eval.py --model e2_340_s2 --task carrot --dry-run   # show the command
python scripts/eval.py --model e2_340_s2                           # all 4 tasks
scripts/eval_all.sh                                                # every model

# 4. summary
python scripts/summarize.py
```

Each run directory `results/<model>/<task>/` holds the official evaluator outputs
(episode videos `success_*/failure_*.mp4`, `evaluation_results.txt`) plus
`cmd.txt` and `run.log`.

## Notes

- GPU: SIMPLER renders with Vulkan (SAPIEN). Rasterization works on data-center GPUs
  (A100/H100) but RTX-class GPUs render faster; a 7B model in bf16 needs roughly 24 GB+.
- Adding a model: one entry in `models.yaml`, then download and eval.
- Reported numbers should use `configs/bridge.yaml` unchanged.
