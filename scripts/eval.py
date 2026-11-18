"""Run the official LAPA SIMPLER evaluation for one model over tasks and evaluation seeds.

  python scripts/eval.py --model e3_340 --task carrot --eval-seed 1234
  python scripts/eval.py --model e3_340                 # 4 tasks x 5 seeds from configs/bridge.yaml
  python scripts/eval.py --model e0 --task spoon --dry-run

One run = one model x one task x one evaluation seed = all 24 object placements.
Task arguments come from configs/bridge.yaml (= official SimplerEnv/scripts/lapa_bridge.sh).
With patches/0001 the sampling RNG is reset to seed*1000+placement before every placement.

Output per run: results/<model>/<task>/seed<k>/
  episodes.jsonl   one record per placement (success, grasped, moved, steps, episode_stats)
  env.json         GPU / driver / package versions / commits
  cmd.txt, run.log, evaluation_results.txt, videos (official evaluator)
A run whose episodes.jsonl already has all placements is skipped unless --force.
"""
import argparse
import json
import os
import platform
import shlex
import subprocess
import sys
import time

from common import LAPA, RESULTS_DIR, ROOT, SIMPLER, base_dir, bridge, model_params, models

# file (relative to SimplerEnv) -> text that only exists once the patch is applied
PATCH_MARKERS = {
    "simpler_env/evaluation/maniskill2_evaluator.py": "reseed_per_placement",  # 0001
    "simpler_env/utils/visualization.py": "imageio.mimwrite",                  # 0002
}


def build_cmd(model, task, seed, episode_log):
    cfg = bridge()
    c, t = cfg["common"], cfg["tasks"][task]
    s = cfg["scenes"][t["scene"]]
    x, y = str(s["robot_init_x"]), str(s["robot_init_y"])
    to_s = lambda v: [str(i) for i in v]
    cmd = [
        sys.executable, str(SIMPLER / "simpler_env" / "main_inference_lapa.py"),
        "--policy-model", "lapa",
        "--ckpt-path", f"params::{model_params(model)}",
        "--robot", s["robot"],
        "--policy-setup", c["policy_setup"],
        "--action-scale-file", str(ROOT / c["action_scale_file"]),
        "--vqgan-checkpoint", str(base_dir() / "vqgan"),
        "--vocab-file", str(base_dir() / "tokenizer.model"),
        "--control-freq", str(c["control_freq"]),
        "--sim-freq", str(c["sim_freq"]),
        "--max-episode-steps", str(t["max_episode_steps"]),
        "--env-name", t["env_name"],
        "--scene-name", s["scene_name"],
        "--rgb-overlay-path", str(SIMPLER / s["rgb_overlay_path"]),
        "--robot-init-x", x, x, "1",
        "--robot-init-y", y, y, "1",
        "--obj-variation-mode", c["obj_variation_mode"],
        "--obj-episode-range", *to_s(c["obj_episode_range"]),
        "--robot-init-rot-quat-center", *to_s(c["robot_init_rot_quat_center"]),
        "--robot-init-rot-rpy-range", *to_s(c["robot_init_rot_rpy_range"]),
        "--load-llama-config", c["load_llama_config"],
        "--update-llama-config", c["update_llama_config"],
        "--tokens-per-action", str(c["tokens_per_action"]),
        "--tokens-per-delta", str(c["tokens_per_delta"]),
        "--seed", str(seed),
        "--episode-log", str(episode_log),
        "--logging-dir", ".",
    ]
    if c.get("reseed_per_placement", True):
        cmd.append("--reseed-per-placement")
    return cmd


def sh(cmd):
    try:
        return subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60).stdout.strip()
    except Exception as e:  # noqa: BLE001
        return f"error: {e}"


def env_info():
    pkgs = {}
    for p in ("jax", "jaxlib", "flax", "tensorflow", "sapien", "mani_skill2_real2sim", "simpler_env", "numpy", "torch"):
        try:
            from importlib.metadata import version
            pkgs[p] = version(p)
        except Exception:  # noqa: BLE001
            pkgs[p] = None
    return dict(
        time=time.strftime("%Y-%m-%d %H:%M:%S"),
        host=platform.node(),
        cuda_visible_devices=os.environ.get("CUDA_VISIBLE_DEVICES"),
        gpu=sh("nvidia-smi --query-gpu=index,name,driver_version,memory.total --format=csv,noheader"),
        cuda=sh("nvcc --version | tail -1"),
        vulkan=sh("vulkaninfo --summary 2>/dev/null | grep -E 'apiVersion|deviceName|driverVersion' | head -6"),
        python=sys.version.split()[0],
        packages=pkgs,
        bench_commit=sh(f"git -C {ROOT} rev-parse HEAD"),
        bench_dirty=bool(sh(f"git -C {ROOT} status --porcelain --ignore-submodules=all -- scripts configs models.yaml patches")),
        lapa_commit=sh(f"git -C {LAPA} rev-parse HEAD"),
        lapa_diff=sh(f"git -C {LAPA} diff --stat"),
    )


def n_done(log, expected):
    if not log.exists():
        return 0
    ids = {json.loads(l)["obj_episode_id"] for l in log.read_text().splitlines() if l.strip()}
    return len(ids & set(expected))


def main():
    cfg = bridge()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", required=True, choices=list(models()["models"]))
    ap.add_argument("--task", action="append", choices=list(cfg["tasks"]), help="repeatable; default: all")
    ap.add_argument("--eval-seed", action="append", type=int,
                    help="repeatable; default: common.eval_seeds in configs/bridge.yaml")
    ap.add_argument("--force", action="store_true", help="rerun even if complete")
    ap.add_argument("--dry-run", action="store_true", help="print the commands only")
    a = ap.parse_args()

    if not a.dry_run:
        for f, marker in PATCH_MARKERS.items():
            if marker not in (SIMPLER / f).read_text():
                sys.exit(f"patch missing in {f}: run scripts/apply_patches.sh")
        for p in (model_params(a.model), base_dir() / "tokenizer.model", base_dir() / "vqgan"):
            if not p.exists():
                sys.exit(f"missing {p}\nrun: python scripts/download.py base {a.model}")

    lo, hi = cfg["common"]["obj_episode_range"]
    placements = list(range(lo, hi))
    env = dict(os.environ, PYTHONPATH=f"{LAPA}:{SIMPLER}:{os.environ.get('PYTHONPATH', '')}")
    for task in a.task or list(cfg["tasks"]):
        for seed in a.eval_seed or cfg["common"]["eval_seeds"]:
            out = RESULTS_DIR / a.model / task / f"seed{seed}"
            log = out / "episodes.jsonl"
            cmd = build_cmd(a.model, task, seed, log)
            if a.dry_run:
                print(f"# {a.model}/{task}/seed{seed}  (cwd {out})\n" + shlex.join(cmd) + "\n")
                continue
            done = n_done(log, placements)
            if done == len(placements) and not a.force:
                print(f"skip {a.model}/{task}/seed{seed}: complete")
                continue
            if out.exists():  # partial or forced: start the run clean (official evaluator restarts at placement 0)
                for f in out.rglob("*"):
                    if f.is_file():
                        f.unlink()
            out.mkdir(parents=True, exist_ok=True)
            (out / "cmd.txt").write_text(shlex.join(cmd) + "\n")
            (out / "env.json").write_text(json.dumps(env_info(), indent=2) + "\n")
            print(f"== {a.model}/{task}/seed{seed} -> {out}", flush=True)
            t0 = time.time()
            with open(out / "run.log", "w") as f:
                rc = subprocess.call(cmd, cwd=out, env=env, stdout=f, stderr=subprocess.STDOUT)
            done = n_done(log, placements)
            print(f"   rc={rc} placements={done}/{len(placements)} {time.time() - t0:.0f}s", flush=True)
            if rc != 0 or done != len(placements):
                sys.exit(f"{a.model}/{task}/seed{seed} failed, see {out}/run.log")


if __name__ == "__main__":
    main()
