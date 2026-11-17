"""Run the official LAPA SIMPLER evaluation for one model and one or more Bridge tasks.

  python scripts/eval.py --model e2_340_s2 --task carrot
  python scripts/eval.py --model e2_340_s2              # all 4 tasks
  python scripts/eval.py --model e0 --task spoon --dry-run

Arguments are taken from configs/bridge.yaml, which mirrors the official
third_party/LAPA/SimplerEnv/scripts/lapa_bridge.sh. Each run writes videos and
evaluation_results.txt to results/<model>/<task>/. A task whose
evaluation_results.txt already exists is skipped unless --force.
"""
import argparse
import os
import shlex
import subprocess
import sys

from common import LAPA, RESULTS_DIR, ROOT, SIMPLER, base_dir, bridge, model_params, models


def build_cmd(model, task):
    cfg = bridge()
    c, t = cfg["common"], cfg["tasks"][task]
    s = cfg["scenes"][t["scene"]]
    x, y = str(s["robot_init_x"]), str(s["robot_init_y"])
    to_s = lambda v: [str(i) for i in v]
    return [
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
        "--logging-dir", ".",
    ]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", required=True, choices=list(models()["models"]))
    ap.add_argument("--task", action="append", choices=list(bridge()["tasks"]),
                    help="repeatable; default: all tasks")
    ap.add_argument("--force", action="store_true", help="rerun even if results exist")
    ap.add_argument("--dry-run", action="store_true", help="print the command only")
    a = ap.parse_args()

    for p in (model_params(a.model), base_dir() / "tokenizer.model", base_dir() / "vqgan"):
        if not p.exists() and not a.dry_run:
            sys.exit(f"missing {p}\nrun: python scripts/download.py base {a.model}")

    # latent_pretraining (LAPA root) and simpler_env must both be importable.
    env = dict(os.environ, PYTHONPATH=f"{LAPA}:{SIMPLER}:{os.environ.get('PYTHONPATH', '')}")
    for task in a.task or list(bridge()["tasks"]):
        out = RESULTS_DIR / a.model / task
        cmd = build_cmd(a.model, task)
        if a.dry_run:
            print(f"# {a.model}/{task}  (cwd {out})\n" + shlex.join(cmd) + "\n")
            continue
        if (out / "evaluation_results.txt").exists() and not a.force:
            print(f"skip {a.model}/{task}: {out}/evaluation_results.txt exists (use --force)")
            continue
        out.mkdir(parents=True, exist_ok=True)
        (out / "cmd.txt").write_text(shlex.join(cmd) + "\n")
        print(f"== {a.model}/{task} -> {out}", flush=True)
        with open(out / "run.log", "w") as log:
            rc = subprocess.call(cmd, cwd=out, env=env, stdout=log, stderr=subprocess.STDOUT)
        if rc != 0:
            sys.exit(f"{a.model}/{task} failed (rc={rc}), see {out}/run.log")


if __name__ == "__main__":
    main()
