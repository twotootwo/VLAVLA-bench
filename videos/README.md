# 평가 영상

SIMPLER WidowX Bridge 4개 과제 × 모델 4개 × 물건 배치 24개 × 평가 시드 5개 = 영상 1,920개.
RTX 5090 1대(Vast), 2026-11-18 실행. 설정은 `configs/bridge.yaml`, 설계는 `docs/experiment_design.md`.

## 구조

```
videos/<과제>/<모델>/seed<시드>/p<배치번호>_<success|fail>.mp4
data/episodes/<모델>/<과제>/seed<시드>.jsonl   # 배치별 성공·잡기·옮기기·step 수
```

- 같은 (배치, 시드)는 모든 모델이 같은 난수로 시작한다(배치마다 시드 고정). 같은 파일 이름끼리 모델 간 짝지어 비교하면 된다.
- 영상: 640×480, 5 fps, 성공하면 그 step에서 끝난다.

## 과제 (누르면 배치 × 모델 표)

| 과제 | 최대 step | E0 | O-1 | O-2 | H |
|---|---|---|---|---|---|
| [stack_cube](stack_cube/README.md) | 60 | 58/120 | 42/120 | 60/120 | 47/120 |
| [carrot](carrot/README.md) | 60 | 48/120 | 40/120 | 48/120 | 53/120 |
| [spoon](spoon/README.md) | 60 | 69/120 | 52/120 | 70/120 | 63/120 |
| [eggplant](eggplant/README.md) | 120 | 78/120 | 51/120 | 76/120 | 73/120 |

## 모델

| 표기 | 폴더 (HF) | 설명 |
|---|---|---|
| E0 | `e0` | Stage A 없음 (기준선) |
| O-1 | `e2_340` | Stage A = 물체 (HOT3D 340), 학습 1회차 |
| O-2 | `e2_340_s2` | Stage A = 물체 (HOT3D 340), 학습 2회차 |
| H | `e3_340` | Stage A = 손목 (HOT3D 340) |

논문 번호: E0 = `e0`, E1(물체) = `e2_340`·`e2_340_s2`, E2(손) = `e3_340`.
