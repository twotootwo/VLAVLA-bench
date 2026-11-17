"""Download the shared LAPA files and/or model checkpoints listed in models.yaml.

  python scripts/download.py base          # tokenizer.model + vqgan (needed once)
  python scripts/download.py e2_340_s2     # one model (streaming_params ~13.6 GB)
  python scripts/download.py all           # base + every model

Private capstone-vlavla repos need an HF token with read access to the org
(`hf auth login`, or HF_TOKEN).
"""
import sys

from huggingface_hub import hf_hub_download

from common import CKPT_DIR, base_dir, models


def get_base():
    b = models()["base"]
    for f in b["files"]:
        p = hf_hub_download(b["repo"], f, local_dir=base_dir())
        print("ok", p)


def get_model(name):
    m = models()["models"][name]
    for f in ("streaming_params", "metadata.pkl"):
        p = hf_hub_download(m["repo"], f"{m['subdir']}/{f}", local_dir=CKPT_DIR / name)
        print("ok", p)


def main(names):
    if not names:
        sys.exit(__doc__)
    if names == ["all"]:
        names = ["base"] + list(models()["models"])
    for n in names:
        get_base() if n == "base" else get_model(n)


if __name__ == "__main__":
    main(sys.argv[1:])
