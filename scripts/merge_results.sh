#!/usr/bin/env bash
# Build results_merged/ (symlinks) = the analysed set: 7 seeds per model.
#  e0, e2_340, e2_340_s2, e3_340: seeds 1234-1238 from server A (results_vast), 1239-1240 from server B (results_vast2)
#  e2_340_s3, e3_340_s2, e3_340_s3: all seeds from server B
# Server B's seed-1234 reruns of the first four models are the cross-server check, not part of the set.
set -euo pipefail
cd "$(dirname "$0")/.."
A=${A:-results_vast}; B=${B:-results_vast2}; M=${M:-results_merged}
rm -rf "$M"
for m in e0 e2_340 e2_340_s2 e3_340 e2_340_s3 e3_340_s2 e3_340_s3; do
  for t in stack_cube carrot spoon eggplant; do
    mkdir -p "$M/$m/$t"
    for s in 1234 1235 1236 1237 1238 1239 1240; do
      src=$B
      case $m in e0|e2_340|e2_340_s2|e3_340) [ "$s" -le 1238 ] && src=$A ;; esac
      [ -d "$src/$m/$t/seed$s" ] && ln -s "$(realpath "$src/$m/$t/seed$s")" "$M/$m/$t/seed$s"
    done
  done
done
echo "merged runs: $(find -L "$M" -name episodes.jsonl | wc -l)"
