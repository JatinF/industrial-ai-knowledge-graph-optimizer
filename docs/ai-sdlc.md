# How this repository was written

This repository was written in a Grok Build session. It was not written in Claude Code.

The checks that gate a claim are the ones in the repository: pytest, ruff, mypy, the demo script's hand-calculation assertions, and `benchmarks/latest.json`. A passing local command does not by itself prove the GitHub Actions jobs. Those jobs are recorded only from their own runs.

No language-model API is on the decision path. The plan explanation is a deterministic string built from the solver result.
