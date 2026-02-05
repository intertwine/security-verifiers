# Scoreboards

Scoreboards summarize baseline runs on the public mini datasets.

Update via:
```
make baseline-e1
make baseline-e2
```

Or directly:
```
python scripts/baselines/update_scoreboard.py --env e1 --run-dirs <run_dir...>
python scripts/baselines/update_scoreboard.py --env e2 --run-dirs <run_dir...>
```
