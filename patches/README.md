# Patches to the official LAPA code

Applied by `scripts/apply_patches.sh` (also run by `env/install.sh`). They change logging and
RNG seeding only; policy outputs, action sampling and success/grasp/move rules are unchanged.

| patch | files | what |
|---|---|---|
| `0001-reseed-per-placement-and-episode-log.diff` | `SimplerEnv/simpler_env/evaluation/{argparse.py, maniskill2_evaluator.py}` | `--reseed-per-placement`: before each object placement k, reset the sampling RNG (`tux.set_random_seed`) to `seed*1000+k`. Officially the seed is set once per run and the 24 placements share one RNG stream, so placement k's random numbers depend on how many steps placements 0..k-1 used. `--episode-log FILE`: append one JSON record per placement (placement id, seeds, success, grasped, moved, steps, all `episode_stats`). Both flags are off by default, so the official behaviour is unchanged unless they are passed. |
