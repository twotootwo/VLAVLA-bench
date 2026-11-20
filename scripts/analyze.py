"""Per-task analysis of results/<model>/<task>/seed<k>/episodes.jsonl.

- Success / grasp / move rates per model x task (5 seeds x 24 placements = 120).
- 95% CI: bootstrap over placements (the 5 seeds of a placement stay together).
- Paired differences A-B on the same (placement, seed), same placement bootstrap.
Tasks are never pooled (the 4-task mean is shown only for reference).

usage: python scripts/analyze.py [results_dir] [--boot 10000]
"""
import argparse, json, sys
from pathlib import Path
import numpy as np

TASKS = ["stack_cube", "carrot", "spoon", "eggplant"]
MODELS = ["e0", "e2_340", "e2_340_s2", "e3_340"]
LABEL = {"e0": "E0", "e2_340": "O-1", "e2_340_s2": "O-2", "e3_340": "H"}
PAIRS = [("e3_340", "e2_340"), ("e3_340", "e2_340_s2"), ("e3_340", "e0"),
         ("e2_340", "e0"), ("e2_340_s2", "e0"), ("e2_340_s2", "e2_340")]
METRICS = ["success", "grasped", "moved"]


def load(root):
    """-> {model: {task: {metric: array[placement, seed]}}}"""
    out = {}
    for m in MODELS:
        for t in TASKS:
            recs = []
            for f in sorted((root / m / t).glob("seed*/episodes.jsonl")):
                recs += [json.loads(l) for l in f.read_text().splitlines() if l.strip()]
            if not recs:
                continue
            seeds = sorted({r["eval_seed"] for r in recs})
            pls = sorted({r["obj_episode_id"] for r in recs})
            arr = {k: np.full((len(pls), len(seeds)), np.nan) for k in METRICS + ["steps"]}
            for r in recs:
                i, j = pls.index(r["obj_episode_id"]), seeds.index(r["eval_seed"])
                for k in METRICS + ["steps"]:
                    arr[k][i, j] = float(r[k])
            out.setdefault(m, {})[t] = arr
    return out


def boot_ci(x, rng, B):
    """x: [placement, seed]. Mean and 95% CI resampling placements."""
    n = x.shape[0]
    pm = x.mean(1)
    idx = rng.integers(0, n, size=(B, n))
    bs = pm[idx].mean(1)
    return pm.mean(), np.percentile(bs, 2.5), np.percentile(bs, 97.5)


def pct(v):
    return f"{100 * v:5.1f}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root", nargs="?", default="results")
    ap.add_argument("--boot", type=int, default=10000)
    a = ap.parse_args()
    data = load(Path(a.root))
    rng = np.random.default_rng(0)

    for metric in METRICS:
        print(f"\n## {metric} rate, % [95% CI, placement bootstrap]  (n = placements x seeds)")
        print(f"{'model':10s}" + "".join(f"{t:>24s}" for t in TASKS) + f"{'mean4(ref)':>12s}")
        for m in MODELS:
            row, means = f"{LABEL[m]:10s}", []
            for t in TASKS:
                x = data[m][t][metric]
                mu, lo, hi = boot_ci(x, rng, a.boot)
                means.append(mu)
                row += f"  {pct(mu)} [{pct(lo)},{pct(hi)}] "
            print(row + f"{pct(np.mean(means)):>10s}")

    print("\n## per-seed success count (/24)")
    for t in TASKS:
        print(f"{t:11s}" + "  ".join(
            f"{LABEL[m]:>4s}: " + ",".join(str(int(v)) for v in data[m][t]["success"].sum(0))
            for m in MODELS))

    print("\n## paired success difference A-B, %p [95% CI]; * = CI excludes 0")
    print(f"{'A - B':12s}" + "".join(f"{t:>24s}" for t in TASKS))
    for A, B in PAIRS:
        row = f"{LABEL[A] + ' - ' + LABEL[B]:12s}"
        for t in TASKS:
            d = data[A][t]["success"] - data[B][t]["success"]
            mu, lo, hi = boot_ci(d, rng, a.boot)
            star = "*" if lo > 0 or hi < 0 else " "
            row += f" {100*mu:+6.1f} [{100*lo:+5.1f},{100*hi:+5.1f}]{star}"
        print(row)

    print("\n## placements by #successes over 5 seeds (0..5), success")
    for t in TASKS:
        print(t)
        for m in MODELS:
            c = np.bincount(data[m][t]["success"].sum(1).astype(int), minlength=6)
            print(f"  {LABEL[m]:4s} " + " ".join(f"{v:3d}" for v in c))

    print("\n## outcome breakdown, % of 120 episodes")
    print("  fail&no-grasp&no-move | fail&grasp | fail&no-grasp&moved | success")
    for t in TASKS:
        print(t)
        for m in MODELS:
            s, g, mv = (data[m][t][k].astype(bool) for k in METRICS)
            n = s.size
            cats = [(~s & ~g & ~mv), (~s & g), (~s & ~g & mv), s]
            print(f"  {LABEL[m]:4s} " + " ".join(f"{pct(c.sum()/n):>7s}" for c in cats))


if __name__ == "__main__":
    sys.exit(main())
