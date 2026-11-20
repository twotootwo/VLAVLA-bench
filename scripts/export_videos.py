"""Copy run outputs into the git-tracked layout under videos/ and data/.

videos/<task>/<model>/seed<k>/p<NN>_<success|fail>.mp4
videos/README.md, videos/<task>/README.md   (placement x model tables linking every video)
data/episodes/<model>/<task>/seed<k>.jsonl, data/summary.csv

usage: python scripts/export_videos.py [results_dir]
"""
import json, re, shutil, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TASKS = ["stack_cube", "carrot", "spoon", "eggplant"]
MODELS = ["e0", "e2_340", "e2_340_s2", "e3_340"]
LABEL = {"e0": "E0", "e2_340": "O-1", "e2_340_s2": "O-2", "e3_340": "H"}
DESC = {"e0": "Stage A 없음 (기준선)", "e2_340": "Stage A = 물체 (HOT3D 340), 학습 1회차",
        "e2_340_s2": "Stage A = 물체 (HOT3D 340), 학습 2회차", "e3_340": "Stage A = 손목 (HOT3D 340)"}
ENV = {"stack_cube": "StackGreenCubeOnYellowCubeBakedTexInScene-v0", "carrot": "PutCarrotOnPlateInScene-v0",
       "spoon": "PutSpoonOnTableClothInScene-v0", "eggplant": "PutEggplantInBasketScene-v0"}
PAT = re.compile(r"^(success|failure)_obj_episode_(\d+)_")


def main():
    src = Path(sys.argv[1] if len(sys.argv) > 1 else ROOT / "results").resolve()
    vdir, ddir = ROOT / "videos", ROOT / "data"
    table = {}  # (task, model, seed, placement) -> success
    seeds_all = set()
    for m in MODELS:
        for t in TASKS:
            for sd in sorted((src / m / t).glob("seed*")):
                seed = sd.name[4:]
                seeds_all.add(seed)
                recs = [json.loads(l) for l in (sd / "episodes.jsonl").read_text().splitlines() if l.strip()]
                (ddir / "episodes" / m / t).mkdir(parents=True, exist_ok=True)
                shutil.copy2(sd / "episodes.jsonl", ddir / "episodes" / m / t / f"seed{seed}.jsonl")
                ok = {r["obj_episode_id"]: r["success"] for r in recs}
                mp4s = list(sd.rglob("*.mp4"))
                assert len(mp4s) == len(ok) == 24, (sd, len(mp4s), len(ok))
                out = vdir / t / m / f"seed{seed}"
                out.mkdir(parents=True, exist_ok=True)
                for f in mp4s:
                    g = PAT.match(f.name)
                    p, s = int(g.group(2)), g.group(1) == "success"
                    assert s == ok[p], f
                    shutil.copy2(f, out / f"p{p:02d}_{'success' if s else 'fail'}.mp4")
                    table[(t, m, seed, p)] = s
    if (src / "summary.csv").exists():
        shutil.copy2(src / "summary.csv", ddir / "summary.csv")
    seeds = sorted(seeds_all)

    # per-task README: placement x model, each cell = 5 seed links
    for t in TASKS:
        L = [f"# {t} (`{ENV[t]}`)", "",
             "행 = 물건 배치, 열 = 모델. 칸 안의 기호는 시드 " + ", ".join(seeds) + " 순서이고 누르면 영상이 열린다.",
             "✅ 성공, ❌ 실패. 마지막 줄은 모델별 성공 수(/120).", "",
             "| 배치 | " + " | ".join(f"{LABEL[m]} `{m}`" for m in MODELS) + " |",
             "|---|" + "---|" * len(MODELS)]
        for p in range(24):
            cells = []
            for m in MODELS:
                s = []
                for seed in seeds:
                    ok = table[(t, m, seed, p)]
                    s.append(f"[{'✅' if ok else '❌'}]({m}/seed{seed}/p{p:02d}_{'success' if ok else 'fail'}.mp4)")
                cells.append(" ".join(s))
            L.append(f"| p{p:02d} | " + " | ".join(cells) + " |")
        L.append("| 합계 | " + " | ".join(
            f"**{sum(table[(t, m, sd, p)] for sd in seeds for p in range(24))}**" for m in MODELS) + " |")
        (vdir / t / "README.md").write_text("\n".join(L) + "\n")

    # top README
    L = ["# 평가 영상", "",
         "SIMPLER WidowX Bridge 4개 과제 × 모델 4개 × 물건 배치 24개 × 평가 시드 5개 = 영상 1,920개.",
         "RTX 5090 1대(Vast), 2026-11-18 실행. 설정은 `configs/bridge.yaml`, 설계는 `docs/experiment_design.md`.", "",
         "## 구조", "", "```",
         "videos/<과제>/<모델>/seed<시드>/p<배치번호>_<success|fail>.mp4",
         "data/episodes/<모델>/<과제>/seed<시드>.jsonl   # 배치별 성공·잡기·옮기기·step 수",
         "```", "",
         "- 같은 (배치, 시드)는 모든 모델이 같은 난수로 시작한다(배치마다 시드 고정). 같은 파일 이름끼리 모델 간 짝지어 비교하면 된다.",
         "- 영상: 640×480, 5 fps, 성공하면 그 step에서 끝난다.", "",
         "## 과제 (누르면 배치 × 모델 표)", "",
         "| 과제 | 최대 step | " + " | ".join(LABEL[m] for m in MODELS) + " |",
         "|---|---|" + "---|" * len(MODELS)]
    for t in TASKS:
        cnt = [sum(table[(t, m, sd, p)] for sd in seeds for p in range(24)) for m in MODELS]
        L.append(f"| [{t}]({t}/README.md) | {120 if t == 'eggplant' else 60} | "
                 + " | ".join(f"{c}/120" for c in cnt) + " |")
    L += ["", "## 모델", "", "| 표기 | 폴더 (HF) | 설명 |", "|---|---|---|"]
    L += [f"| {LABEL[m]} | `{m}` | {DESC[m]} |" for m in MODELS]
    L += ["", "논문 번호: E0 = `e0`, E1(물체) = `e2_340`·`e2_340_s2`, E2(손) = `e3_340`."]
    (vdir / "README.md").write_text("\n".join(L) + "\n")
    print("videos:", len(table))


if __name__ == "__main__":
    main()
