# Historical damage recovery snapshot

These two implementation snapshots and their measurement records preserve the original comparison used by `pkg_re.die_benchmark`. They are evaluation code, never runtime reconstruction defaults. The source snapshots are intentionally preserved rather than modernized.

Run from the repository root:

```sh
PYTHONPATH=. uv run python benchmarks/baseline/replay_baseline.py
uv run python -m pkg_re.die_benchmark
```

Current plane-dominant fixtures use `uv run python -m pkg_re.weave_benchmark`. Saved-project data and third-party photographs are not required for that benchmark.
