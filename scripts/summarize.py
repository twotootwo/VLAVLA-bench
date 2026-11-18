"""Success / grasp / move counts per model x task from results/<model>/<task>/seed<k>/episodes.jsonl.

Writes results/summary.csv (one row per model x task, plus per-seed success counts).
This is a progress / bookkeeping table. Statistical comparison between conditions
(paired differences, placement-clustered bootstrap CIs) is a separate analysis step,
see docs/experiment_design.md section 7.
"""
import csv
import json

from common import RESULTS_DIR, bridge


def load(task_dir):
    recs = {}
    for log in sorted(task_dir.glob("seed*/episodes.jsonl")):
        seed = log.parent.name
        recs[seed] = [json.loads(l) for l in log.read_text().splitlines() if l.strip()]
    return recs


def main():
    cfg = bridge()
    tasks = list(cfg["tasks"])
    lo, hi = cfg["common"]["obj_episode_range"]
    n_place = hi - lo
    n_seeds = len(cfg["common"]["eval_seeds"])
    rows = []
    for mdir in sorted(p for p in RESULTS_DIR.iterdir() if p.is_dir()):
        for t in tasks:
            if not (mdir / t).is_dir():
                continue
            recs = load(mdir / t)
            allr = [r for rs in recs.values() for r in rs]
            if not allr:
                continue
            n = len(allr)
            k = lambda key: sum(r[key] for r in allr)
            complete = sum(len(rs) == n_place for rs in recs.values())
            rows.append(dict(
                model=mdir.name, task=t, episodes=n,
                seeds_complete=f"{complete}/{n_seeds}",
                success=k("success"), grasped=k("grasped"), moved=k("moved"),
                success_pct=f"{100 * k('success') / n:.1f}",
                per_seed_success=" ".join(f"{s[4:]}:{sum(r['success'] for r in rs)}/{len(rs)}"
                                          for s, rs in recs.items()),
            ))
    out = RESULTS_DIR / "summary.csv"
    cols = ["model", "task", "episodes", "seeds_complete", "success", "grasped", "moved",
            "success_pct", "per_seed_success"]
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)
    print("| " + " | ".join(cols) + " |")
    print("|---" * len(cols) + "|")
    for r in rows:
        print("| " + " | ".join(str(r[c]) for c in cols) + " |")
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
