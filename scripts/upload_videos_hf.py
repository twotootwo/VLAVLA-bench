"""Stage failure videos (and per-task index tables) and upload them to an HF dataset repo in one commit.

Layout in the repo:
  README.md                                 # overview, models, failure-type legend, counts
  <task>/README.md                          # placement x model table of failures (type per seed)
  <task>/<model>/seed<k>/p<NN>_fail_<type>.mp4
  episodes/<model>/<task>/seed<k>.jsonl     # all placements (success and failure)

Failure type (from the official episode stats, no extra logging):
  nograsp  - never grasped, source not moved (approach/grasp failure)
  grasped  - grasped at some step but not placed on target
  pushed   - moved >3 cm without a grasp, not placed

usage:
  uv run --with huggingface_hub python scripts/upload_failures_hf.py --stage /tmp/stage \
     --add results_vast:1234-1238 --add results_vast2:1239-1240 \
     --repo capstone-vlavla/vlavla-bench-failures [--upload]
  token: HF_TOKEN env (needs write access to the repo/org)
"""
import argparse, json, os, re, shutil
from pathlib import Path

TASKS = ["stack_cube", "carrot", "spoon", "eggplant"]
LABEL = {"e0": "E0", "e2_340": "O-1", "e2_340_s2": "O-2", "e2_340_s3": "O-3", "e3_340": "H-1", "e3_340_s2": "H-2", "e3_340_s3": "H-3"}
DESC = {"e0": "Stage A 없음 (기준선)", "e2_340": "물체(O), 학습 1회차", "e2_340_s2": "물체(O), 학습 2회차", "e2_340_s3": "물체(O), 학습 3회차",
        "e3_340": "손(H), 학습 1회차", "e3_340_s2": "손(H), 학습 2회차", "e3_340_s3": "손(H), 학습 3회차"}
PAT = re.compile(r"^(success|failure)_obj_episode_(\d+)_")
MARK = {"nograsp": "⚪", "grasped": "🟠", "pushed": "🔵"}


def ftype(r):
    if r["grasped"]:
        return "grasped"
    return "pushed" if r["moved"] else "nograsp"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True)
    ap.add_argument("--add", action="append", required=True, help="results_dir:SEED-SEED")
    ap.add_argument("--models", default="e0,e2_340,e2_340_s2,e2_340_s3,e3_340,e3_340_s2,e3_340_s3")
    ap.add_argument("--repo")
    ap.add_argument("--upload", action="store_true")
    ap.add_argument("--kind", choices=["failure", "success"], default="failure")
    a = ap.parse_args()
    st = Path(a.stage)
    if st.exists():
        shutil.rmtree(st)
    models = a.models.split(",")
    fails, runs = {}, {}  # fails[(t,m,seed,p)] = type ; runs[(t,m,seed)] = (n_success, n)
    for spec in a.add:
        root, rng = spec.rsplit(":", 1)
        lo, hi = map(int, rng.split("-"))
        for m in models:
            for t in TASKS:
                for s in range(lo, hi + 1):
                    d = Path(root) / m / t / f"seed{s}"
                    ep = d / "episodes.jsonl"
                    if not ep.exists():
                        continue
                    recs = {json.loads(l)["obj_episode_id"]: json.loads(l) for l in ep.read_text().splitlines() if l.strip()}
                    if len(recs) < 24:
                        continue
                    (st / "episodes" / m / t).mkdir(parents=True, exist_ok=True)
                    shutil.copy2(ep, st / "episodes" / m / t / f"seed{s}.jsonl")
                    runs[(t, m, s)] = (sum(r["success"] for r in recs.values()), len(recs))
                    for f in d.rglob(f"{a.kind}_*.mp4"):
                        p = int(PAT.match(f.name).group(2))
                        r = recs[p]
                        assert r["success"] == (a.kind == "success"), f
                        ty = ftype(r) if a.kind == "failure" else f"{r['steps']:02d}steps"
                        out = st / t / m / f"seed{s}"
                        out.mkdir(parents=True, exist_ok=True)
                        name = f"p{p:02d}_fail_{ty}.mp4" if a.kind == "failure" else f"p{p:02d}_success_{ty}.mp4"
                        os.link(f, out / name) if os.stat(f).st_dev == os.stat(out).st_dev else shutil.copy2(f, out / name)
                        fails[(t, m, s, p)] = ty
    have = [m for m in models if any(k[1] == m for k in runs)]
    seeds = sorted({k[2] for k in runs})

    if a.kind == "success":
        write_success_readmes(st, fails, runs, have, seeds)
        print(f"staged {len(fails)} success videos, {len(runs)} runs, models={have}, seeds={seeds}")
        upload(a, st, f"Success videos: {len(fails)} clips, {len(runs)} runs")
        return

    for t in TASKS:
        L = [f"# {t} 실패 영상", "",
             "행 = 물건 배치, 열 = 모델. 칸 안의 기호는 시드 순서(" + ", ".join(map(str, seeds)) + "), 누르면 영상.",
             "⚪ 잡기 없음·안 움직임, 🟠 잡았으나 실패, 🔵 잡지 않고 밀기만 함, ✅ 성공(영상 없음), · 실행 없음", "",
             "| 배치 | " + " | ".join(f"{LABEL[m]} `{m}`" for m in have) + " |", "|---|" + "---|" * len(have)]
        for p in range(24):
            cells = []
            for m in have:
                c = []
                for s in seeds:
                    if (t, m, s) not in runs:
                        c.append("·")
                    elif (t, m, s, p) in fails:
                        ty = fails[(t, m, s, p)]
                        c.append(f"[{MARK[ty]}]({m}/seed{s}/p{p:02d}_fail_{ty}.mp4)")
                    else:
                        c.append("✅")
                cells.append(" ".join(c))
            L.append(f"| p{p:02d} | " + " | ".join(cells) + " |")
        L.append("| 실패 수 | " + " | ".join(
            f"**{sum(1 for k in fails if k[0] == t and k[1] == m)}** / {sum(n for (tt, mm, _), (_, n) in runs.items() if tt == t and mm == m)}"
            for m in have) + " |")
        (st / t).mkdir(parents=True, exist_ok=True)
        (st / t / "README.md").write_text("\n".join(L) + "\n")

    L = ["---", "license: other", "tags: [robotics, simpler, lapa]", "---", "", "# VLAVLA-bench 실패 영상",
         "", "LAPA 체크포인트를 SIMPLER WidowX Bridge 4개 과제에서 평가했을 때 **실패한 에피소드** 영상.",
         "평가 코드·설정: GitHub `twotootwo/VLAVLA-bench` (`configs/bridge.yaml`, 공식 LAPA 46aca51 + 패치).",
         "성공 영상과 전체 결과는 GitHub `videos/`, 배치별 기록은 이 저장소 `episodes/`.", "",
         "## 구조", "", "```", "<과제>/<모델>/seed<시드>/p<배치>_fail_<유형>.mp4",
         "episodes/<모델>/<과제>/seed<시드>.jsonl   # 성공 포함 전체 배치 기록", "```", "",
         "- 실패 유형(공식 판정값만 사용): `nograsp` 잡기 없음·안 움직임 / `grasped` 잡았으나 목표에 못 놓음 / `pushed` 잡지 않고 3cm 이상 밀기만 함",
         "- 같은 (배치, 시드)는 모든 모델이 같은 난수로 시작한다(배치마다 시드 고정).",
         "- 시드 1234~1238은 RTX 5090 서버 A(11/18), 1239~1240과 O-3·H-2·H-3의 전 시드는 RTX 5090 서버 B(11/21).",
         "  같은 시드를 두 서버에서 돌리면 배치의 약 92%가 같은 결과(렌더링 미세 차이).", "",
         "## 과제별 실패 수 (누르면 배치 × 모델 표)", "",
         "| 과제 | " + " | ".join(LABEL[m] for m in have) + " |", "|---|" + "---|" * len(have)]
    for t in TASKS:
        row = []
        for m in have:
            n = sum(n for (tt, mm, _), (_, n) in runs.items() if tt == t and mm == m)
            k = [fails[x] for x in fails if x[0] == t and x[1] == m]
            row.append(f"{len(k)}/{n} (⚪{k.count('nograsp')} 🟠{k.count('grasped')} 🔵{k.count('pushed')})")
        L.append(f"| [{t}]({t}/README.md) | " + " | ".join(row) + " |")
    L += ["", "## 모델", "", "| 표기 | 폴더 | 설명 |", "|---|---|---|"] + [f"| {LABEL[m]} | `{m}` | {DESC[m]} |" for m in have]
    (st / "README.md").write_text("\n".join(L) + "\n")
    print(f"staged {len(fails)} failure videos, {len(runs)} runs, models={have}, seeds={seeds}")
    upload(a, st, f"Failure videos: {len(fails)} clips, {len(runs)} runs")


def upload(a, st, msg):
    """One commit; retries on HF 429 (the account-wide API quota is often exhausted)."""
    if not a.upload:
        return
    import time
    from huggingface_hub import HfApi
    from huggingface_hub.utils import HfHubHTTPError
    api = HfApi()

    def retry(fn, what):
        for i in range(60):
            try:
                return fn()
            except HfHubHTTPError as e:
                if getattr(e.response, "status_code", 0) == 429:
                    print(f"{what}: 429, retry {i}", flush=True)
                    time.sleep(30)
                    continue
                raise
        raise SystemExit(f"{what}: gave up")
    retry(lambda: api.create_repo(a.repo, repo_type="dataset", private=True, exist_ok=True), "create")
    retry(lambda: api.upload_folder(repo_id=a.repo, repo_type="dataset", folder_path=str(st), commit_message=msg), "upload")
    print("uploaded to", a.repo)


def write_success_readmes(st, ok, runs, have, seeds):
    """ok[(t,m,seed,p)] = 'NNsteps'. Cells show the step at which success was judged."""
    def n_runs(t, m):
        return sum(n for (tt, mm, _), (_, n) in runs.items() if tt == t and mm == m)
    for t in TASKS:
        L = [f"# {t} 성공 영상", "",
             "행 = 물건 배치, 열 = 모델. 칸 안의 숫자는 시드 순서(" + ", ".join(map(str, seeds)) + ")의 성공 판정 step, 누르면 영상.",
             "❌ 실패(영상은 실패 저장소), · 실행 없음. 영상은 판정 직전 step에서 끝난다(공식 평가 코드가 성공 step 화면을 저장하지 않음).", "",
             "| 배치 | " + " | ".join(f"{LABEL[m]} `{m}`" for m in have) + " |", "|---|" + "---|" * len(have)]
        for p in range(24):
            cells = []
            for m in have:
                c = []
                for s in seeds:
                    if (t, m, s) not in runs:
                        c.append("·")
                    elif (t, m, s, p) in ok:
                        ty = ok[(t, m, s, p)]
                        c.append(f"[{int(ty[:-5])}]({m}/seed{s}/p{p:02d}_success_{ty}.mp4)")
                    else:
                        c.append("❌")
                cells.append(" ".join(c))
            L.append(f"| p{p:02d} | " + " | ".join(cells) + " |")
        L.append("| 성공 수 | " + " | ".join(
            f"**{sum(1 for k in ok if k[0] == t and k[1] == m)}** / {n_runs(t, m)}" for m in have) + " |")
        (st / t).mkdir(parents=True, exist_ok=True)
        (st / t / "README.md").write_text("\n".join(L) + "\n")
    L = ["---", "license: other", "tags: [robotics, simpler, lapa]", "---", "", "# VLAVLA-bench 성공 영상", "",
         "LAPA 체크포인트를 SIMPLER WidowX Bridge 4개 과제에서 평가했을 때 **성공한 에피소드** 영상.",
         "실패 영상은 `capstone-vlavla/vlavla-bench-failures`. 평가 코드·설정: GitHub `twotootwo/VLAVLA-bench`.", "",
         "## 구조", "", "```", "<과제>/<모델>/seed<시드>/p<배치>_success_<판정 step>steps.mp4",
         "episodes/<모델>/<과제>/seed<시드>.jsonl   # 성공·실패 전체 배치 기록", "```", "",
         "- 성공 판정(공식): 물체 중심이 목표 bbox 대각선 절반 안, 높이 2cm 이내, 목표·로봇 외 접촉 없음. **놓지 않고 들고 있어도 성공일 수 있다.**",
         "- 같은 (배치, 시드)는 모든 모델이 같은 난수로 시작한다(배치마다 시드 고정).",
         "- 시드 1234~1238은 RTX 5090 서버 A(11/18), 1239~1240과 O-3·H-2·H-3의 전 시드는 서버 B(11/21).", "",
         "## 과제별 성공 수와 판정 step 중앙값 (누르면 배치 × 모델 표)", "",
         "| 과제 | " + " | ".join(LABEL[m] for m in have) + " |", "|---|" + "---|" * len(have)]
    for t in TASKS:
        row = []
        for m in have:
            st_ = sorted(int(ok[k][:-5]) for k in ok if k[0] == t and k[1] == m)
            med = st_[len(st_) // 2] if st_ else "-"
            row.append(f"{len(st_)}/{n_runs(t, m)} (중앙 {med} step)")
        L.append(f"| [{t}]({t}/README.md) | " + " | ".join(row) + " |")
    L += ["", "## 모델", "", "| 표기 | 폴더 | 설명 |", "|---|---|---|"] + [f"| {LABEL[m]} | `{m}` | {DESC[m]} |" for m in have]
    (st / "README.md").write_text("\n".join(L) + "\n")


if __name__ == "__main__":
    main()
