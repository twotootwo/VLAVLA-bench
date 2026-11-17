"""Shared paths and config loading for the VLAVLA-bench scripts."""
import os
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
LAPA = ROOT / "third_party" / "LAPA"
SIMPLER = LAPA / "SimplerEnv"
# Checkpoints are large (13.6 GB each); point VLAVLA_CKPT_DIR at a big disk if needed.
CKPT_DIR = Path(os.environ.get("VLAVLA_CKPT_DIR", ROOT / "checkpoints"))
RESULTS_DIR = Path(os.environ.get("VLAVLA_RESULTS_DIR", ROOT / "results"))


def load_yaml(name):
    with open(ROOT / name) as f:
        return yaml.safe_load(f)


def models():
    return load_yaml("models.yaml")


def bridge():
    return load_yaml("configs/bridge.yaml")


def base_dir():
    return CKPT_DIR / "base"


def model_params(name):
    """Path of streaming_params for a model in models.yaml."""
    m = models()["models"][name]
    return CKPT_DIR / name / m["subdir"] / "streaming_params"
