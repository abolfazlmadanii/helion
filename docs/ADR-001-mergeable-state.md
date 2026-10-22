# ADR-001: Mergeable operator state and Flink serialization

## Status

Accepted (Week 2 — Foundation II: time and state)

## Context

Helion’s Flink operator checkpoints a single `HelionRuntime` holding Count-Min, Space-Saving, φ hot-key detection, and optional pane-windowed Count-Min. Week 1 used Java serialization (`ObjectOutputStream`), which is opaque, brittle across releases, and unsuitable for savepoint compatibility goals.

Week 2 also requires event-time watermarks, explicit handling of late records, and deterministic replay under Flink 2.2.1.

## Decision

### Versioned Flink state codec (Flink-first)

- Operator union list state stores **versioned binary blobs** produced by `HelionRuntimeCodec` (`helion-core`, magic `HLRN`, `CURRENT_VERSION = 1`).
- Component payloads are typed (`count_min`, `space_saving`, `phi_hot_keys`, `pane_window`) with explicit fields (hash coefficients, tables, Space-Saving counters, pane deques).
- Unknown codec versions **fail closed** with `HelionCodecException` (tested via a version bump stub).

**Kafka Streams** continues to use Java serialization in `HelionRuntimeSerde` this week. Aligning Kafka Streams with `HelionRuntimeCodec` is a documented follow-up.

### Event time and lateness

- Production Flink parsing requires `key,weight,eventTimeMillis` (`HelionEvent.parseLineRequired`). No wall-clock fallback on the Flink path.
- `WatermarkStrategy.forBoundedOutOfOrderness` defaults to **5 s** (`HELION_MAX_OUT_OF_ORDER_MS`, overridable).
- Events with `eventTimeMillis < currentWatermark` are emitted to side output tag **`late-records`** and are not ingested into sketches.

### Two-phase local → global merge (parallelism > 1)

**Deferred to Week 3** (stretch goal for Week 2). The job still runs the global operator at parallelism 1 so Space-Saving and φ remain correct. Count-Min and pane Count-Min remain **mergeable in principle** (`MergeableSketch`); a keyed local update plus global merge operator is planned once Misra-Gries / parallel heavy-hitter work lands.

## What is mergeable

| Component | Mergeable across partitions? | Notes |
|-----------|------------------------------|-------|
| Count-Min (lifetime) | Yes | Same hash coefficients; cell-wise sum |
| PaneWindow → Count-Min | Yes (per pane) | Panes merge via `MergeableSketch.mergeFrom` |
| Space-Saving | No (in Helion) | Theorem is for one global table |
| φ hot-key detector | No | Wraps Space-Saving |

## Consequences

- Checkpoints are portable across JVMs that share the same codec version.
- Late events are visible on a side output instead of silently updating global sketches.
- Parallel scale-out for mergeable sketches requires the deferred two-phase topology; until then, document parallelism-1 for the hot-key operator.

## Follow-ups

- Kafka Streams: switch `HelionRuntimeSerde` to `HelionRuntimeCodec`.
- Week 3: two-phase Count-Min / pane merge topology and tests vs parallelism-1 gold.
