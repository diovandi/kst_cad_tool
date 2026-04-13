# Benchmark Tests

This folder contains long-running benchmark tests that are intentionally excluded
from the default `pytest` run (`pyproject.toml` keeps `testpaths = ["tests"]`).

Run benchmarks explicitly when optimization/surrogate code changes:

```bash
pytest benchmarks/test_benchmark_surrogates.py -v -s --no-cov
```

For the heaviest scenarios only:

```bash
pytest benchmarks/test_benchmark_surrogates.py -m slow -v -s --no-cov
```
