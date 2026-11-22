#!/usr/bin/env bash
# Build results_merged/ (symlinks) = the analysed set: 7 seeds per model.
#  e0, e2_340, e2_340_s2, e3_340: seeds 1234-1238 from server A (results_vast), 1239-1240 from server B (results_vast2)
#  e2_340_s3, e3_340_s2, e3_340_s3: all seeds from server B
#  e2cb, e3cb: all seeds from server C (results_vast3)
#  e2L, e3L: all seeds from server D (results_vast4, driver 570); its e3cb seed1234 rerun is a cross-server check only
# Server B's seed-1234 reruns of the first four models are the cross-server check, not part of the set.
set -euo pipefail
cd "$(dirname "$0")/.."
A=${A:-results_vast}; B=${B:-results_vast2}; C=${C:-results_vast3}; D=${D:-results_vast4}; M=${M:-results_merged}
rm -rf "$M"
for m in e0 e2_340 e2_340_s2 e3_340 e2_340_s3 e3_340_s2 e3_340_s3 e2cb e3cb e2L e3L; do
  for t in stack_cube carrot spoon eggplant; do
    mkdir -p "$M/$m/$t"
    for s in 1234 1235 1236 1237 1238 1239 1240; do
      src=$B
      case $m in e0|e2_340|e2_340_s2|e3_340) [ "$s" -le 1238 ] && src=$A ;; e2cb|e3cb) src=$C ;; e2L|e3L) src=$D ;; esac
      [ -d "$src/$m/$t/seed$s" ] && ln -s "$(realpath "$src/$m/$t/seed$s")" "$M/$m/$t/seed$s"
    done
  done
done
echo "merged runs: $(find -L "$M" -name episodes.jsonl | wc -l)"
