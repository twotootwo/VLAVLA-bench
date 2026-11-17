"""Collect success rates from results/<model>/<task>/ into results/summary.csv.

Success is counted from the episode videos the official evaluator writes
(success_obj_episode_*.mp4 / failure_obj_episode_*.mp4), so partial runs show
how many episodes are done.
"""
import csv

from common import RESULTS_DIR, bridge


def count(task_dir):
    vids = list(task_dir.rglob("*.mp4"))
    ok = sum(v.name.startswith("success") for v in vids)
    return ok, len(vids)


def main():
    tasks = list(bridge()["tasks"])
    lo, hi = bridge()["common"]["obj_episode_range"]
    expected = hi - lo
    rows = []
    for mdir in sorted(p for p in RESULTS_DIR.iterdir() if p.is_dir()):
        row = {"model": mdir.name}
        rates = []
        for t in tasks:
            if not (mdir / t).is_dir():
                row[t] = ""
                continue
            ok, n = count(mdir / t)
            row[t] = f"{ok}/{n}" + ("" if n == expected else " (partial)")
            if n == expected:
                rates.append(ok / n)
        # mean over finished tasks only; '*' marks a mean that does not cover all tasks yet
        mean = f"{100 * sum(rates) / len(rates):.1f}" if rates else ""
        row["mean_sr"] = mean + ("*" if rates and len(rates) < len(tasks) else "")
        rows.append(row)

    out = RESULTS_DIR / "summary.csv"
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["model", *tasks, "mean_sr"])
        w.writeheader()
        w.writerows(rows)
    print("| model | " + " | ".join(tasks) + " | mean SR % |")
    print("|---" * (len(tasks) + 2) + "|")
    for r in rows:
        print("| " + " | ".join(r[k] for k in ["model", *tasks, "mean_sr"]) + " |")
    print(f"\nwrote {out}  (* = mean over finished tasks only)")


if __name__ == "__main__":
    main()
