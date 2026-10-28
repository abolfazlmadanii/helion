# ADR-010: Python 3.12 stack (supersedes ADR-001)

## Status

Accepted

## Context

Helion ships proven-bound streaming sketches (Count-Min, Space-Saving, φ hot keys, pane windows) with explicit operator state and event-time semantics. ADR-001 described mergeable state and a versioned binary codec for a JVM operator runtime.

## Decision

- **Language:** Python 3.12 for all library and test code in this repository.
- **Package tooling:** `uv` with a single `pyproject.toml` and lockfile.
- **Quality:** `ruff` for lint/format; `pytest` and `hypothesis` for tests and property checks.
- **Operator state:** `HelionRuntimeCodec` (`HLRN` magic, version 1) using explicit `struct` layouts and `array`-backed counter storage in the core—never `pickle` for checkpoints.
- **Engines:** `helion_flink` on PyFlink 2.2.1 (optional `numpy<2.2` via the `flink` extra); `helion_quix` on quixstreams 3.28.

ADR-001 remains in the tree for historical mergeability notes; operational guidance in new work follows this ADR.

## Consequences

- Sketch math docs (`docs/MATH_*.md`) stay valid; only the runtime binding changes.
- Parallel Count-Min merge in `helion_flink` matches single-task reference totals at tested parallelism.
