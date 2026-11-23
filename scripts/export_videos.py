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
MODELS = ["e0", "e2_340", "e2_340_s2", "e2_340_s3", "e3_340", "e3_340_s2", "e3_340_s3", "e2_340_s4", "e3_340_s4", "e2cb", "e3cb", "e2L", "e3L"]
LABEL = {"e0": "E0", "e2_340": "O-1", "e2_340_s2": "O-2", "e2_340_s3": "O-3", "e3_340": "H-1", "e3_340_s2": "H-2", "e3_340_s3": "H-3", "e2_340_s4": "O-4", "e3_340_s4": "H-4", "e2cb": "O-cb", "e3cb": "H-cb", "e2L": "O-L", "e3L": "H-L"}
DESC = {"e0": "Stage A 없음 (기준선)", "e2_340": "Stage A = 물체 (HOT3D 340), 학습 1회차",
        "e2_340_s2": "Stage A = 물체 (HOT3D 340), 학습 2회차", "e2_340_s3": "Stage A = 물체 (HOT3D 340), 학습 3회차",
        "e3_340": "Stage A = 손목 (HOT3D 340), 학습 1회차", "e3_340_s2": "Stage A = 손목 (HOT3D 340), 학습 2회차",
        "e3_340_s3": "Stage A = 손목 (HOT3D 340), 학습 3회차",
        "e2_340_s4": "Stage A = 물체 (HOT3D 340), 학습 4회차 (capstone-vlavla2)",
        "e3_340_s4": "Stage A = 손목 (HOT3D 340), 학습 4회차 (capstone-vlavla2)",
        "e2cb": "물체(O) cb 변형 (11/22 업로드)", "e3cb": "손(H) cb 변형 (11/22 업로드)",
        "e2L": "물체(O) L 변형 (capstone-vlavla2, 11/22 업로드)", "e3L": "손(H) L 변형 (capstone-vlavla2, 11/22 업로드)"}
ENV = {"stack_cube": "StackGreenCubeOnYellowCubeBakedTexInScene-v0", "carrot": "PutCarrotOnPlateInScene-v0",
       "spoon": "PutSpoonOnTableClothInScene-v0", "eggplant": "PutEggplantInBasketScene-v0"}
PAT = re.compile(r"^(success|failure)_obj_episode_(\d+)_")


def main():
    src = Path(sys.argv[1] if len(sys.argv) > 1 else ROOT / "results").resolve()
    vdir, ddir = ROOT / "videos", ROOT / "data"
    for d in (vdir, ddir / "episodes"):  # rebuilt from scratch every time
        shutil.rmtree(d, ignore_errors=True)
    table = {}  # (task, model, seed, placement) -> success
    seeds_all = set()
    for m in MODELS:
        for t in TASKS:
            for sd in sorted((src / m / t).glob("seed*")) if (src / m / t).is_dir() else []:
                seed = sd.name[4:]
                seeds_all.add(seed)
                ep = sd / "episodes.jsonl"
                recs = [json.loads(l) for l in ep.read_text().splitlines() if l.strip()] if ep.exists() else []
                if len(recs) < 24:
                    print("skip incomplete run", sd)
                    continue
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
    have = [m for m in MODELS if any(k[1] == m for k in table)]

    def runs(t, m):
        return sorted({k[2] for k in table if k[0] == t and k[1] == m})

    def cnt(t, m):
        return sum(v for k, v in table.items() if k[0] == t and k[1] == m), 24 * len(runs(t, m))

    # per-task README: placement x model, each cell = one link per seed
    for t in TASKS:
        L = [f"# {t} (`{ENV[t]}`)", "",
             "행 = 물건 배치, 열 = 모델. 칸 안의 기호는 시드 " + ", ".join(seeds) + " 순서이고 누르면 영상이 열린다.",
             "✅ 성공, ❌ 실패, · 실행 없음. 마지막 줄은 모델별 성공 수.", "",
             "| 배치 | " + " | ".join(f"{LABEL[m]} `{m}`" for m in have) + " |",
             "|---|" + "---|" * len(have)]
        for p in range(24):
            cells = []
            for m in have:
                c = []
                for seed in seeds:
                    if (t, m, seed, p) not in table:
                        c.append("·")
                        continue
                    ok = table[(t, m, seed, p)]
                    c.append(f"[{'✅' if ok else '❌'}]({m}/seed{seed}/p{p:02d}_{'success' if ok else 'fail'}.mp4)")
                cells.append(" ".join(c))
            L.append(f"| p{p:02d} | " + " | ".join(cells) + " |")
        L.append("| 합계 | " + " | ".join("**%d** / %d" % cnt(t, m) for m in have) + " |")
        (vdir / t / "README.md").write_text("\n".join(L) + "\n")

    # top README
    L = ["# 평가 영상", "",
         f"SIMPLER WidowX Bridge 4개 과제 × 모델 {len(have)}개 × 물건 배치 24개 × 평가 시드 {len(seeds)}개 = 영상 {len(table):,}개.",
         "RTX 5090(Vast). 시드 1234~1238 중 E0·O-1·O-2·H-1은 서버 A(2026-11-18), 나머지(1239~1240 전부, O-3·H-2·H-3의 전 시드)는 서버 B(2026-11-21), O-cb·H-cb는 서버 C(2026-11-22, 서버 B와 같은 드라이버), O-L·H-L은 서버 D(2026-11-22~23, 드라이버 570), O-4·H-4는 서버 E(2026-11-23~24, 드라이버 595).",
         "같은 시드를 두 서버에서 돌리면 배치의 약 92%가 같은 결과(렌더링 미세 차이, 방향 치우침 없음).",
         "설정은 `configs/bridge.yaml`, 설계는 `docs/experiment_design.md`.", "",
         "## 구조", "", "```",
         "videos/<과제>/<모델>/seed<시드>/p<배치번호>_<success|fail>.mp4",
         "data/episodes/<모델>/<과제>/seed<시드>.jsonl   # 배치별 성공·잡기·옮기기·step 수",
         "```", "",
         "- 같은 (배치, 시드)는 모든 모델이 같은 난수로 시작한다(배치마다 시드 고정). 같은 파일 이름끼리 모델 간 짝지어 비교하면 된다.",
         "- 영상: 640×480, 5 fps. 성공 영상은 판정 직전 step에서 끝난다(공식 평가 코드가 성공 step 화면을 저장하지 않음).", "",
         "## 과제 (누르면 배치 × 모델 표)", "",
         "| 과제 | 최대 step | " + " | ".join(LABEL[m] for m in have) + " |",
         "|---|---|" + "---|" * len(have)]
    for t in TASKS:
        L.append(f"| [{t}]({t}/README.md) | {120 if t == 'eggplant' else 60} | "
                 + " | ".join("%d/%d" % cnt(t, m) for m in have) + " |")
    L += ["", "## 모델", "", "| 표기 | 폴더 (HF) | 설명 |", "|---|---|---|"]
    L += [f"| {LABEL[m]} | `{m}` | {DESC[m]} |" for m in have]
    L += ["", "논문 번호: E0 = `e0`, E1(물체) = `e2_340*`, E2(손) = `e3_340*`. `_s2`, `_s3`는 같은 설정의 재학습."]
    (vdir / "README.md").write_text("\n".join(L) + "\n")
    print("videos:", len(table))


if __name__ == "__main__":
    main()
