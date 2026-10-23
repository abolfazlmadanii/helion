# ADR-001: Mergeable operator state

> Superseded for stack choices by [ADR-010](ADR-010-python-stack.md). Mergeability rules below still apply.

## Status

Accepted (historical)

## Context

Helion checkpoints a single `HelionRuntime` holding Count-Min, Space-Saving, φ hot-key detection, and optional pane-windowed Count-Min. Operator state must survive restarts with an explicit, versioned binary codec.

## Decision

- Operator state uses **versioned binary blobs** (`HelionRuntimeCodec`, magic `HLRN`, version 1).
- Component payloads are typed (`count_min`, `space_saving`, `phi_hot_keys`, `pane_window`) with explicit fields.
- Unknown codec versions **fail closed** with `CodecError`.

## What is mergeable

| Component | Mergeable across partitions? | Notes |
|-----------|------------------------------|-------|
| Count-Min (lifetime) | Yes | Same hash coefficients; cell-wise sum |
| PaneWindow → Count-Min | Yes (per pane) | Panes merge via `merge_from` |
| Space-Saving | No (in Helion) | Theorem is for one global table |
| φ hot-key detector | No | Wraps Space-Saving |

## Follow-ups

- Two-phase local→global merge for Count-Min at parallelism > 1 (with PyFlink keyed state).
