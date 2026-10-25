# Architecture

Helion is a Python library of mergeable sketches and a small component runtime. Stream engines attach in separate packages.

```
Kafka topic (future) / from_collection (tests)
    │
    ├─ helion_flink (PyFlink 2.2.1)
    │     ├─ bounded-out-of-orderness watermarks + late-record routing
    │     ├─ global keyed ValueState → HelionRuntimeCodec bytes
    │     └─ two-phase Count-Min: shard accumulate → global merge
    │
    └─ HelionRuntime (library / in-process)
            ├─ CountMinSketch (lifetime)
            ├─ SpaceSaving (lifetime; not pane-merged)
            ├─ PhiHotKeyDetector
            ├─ PaneWindow → Count-Min per pane
            └─ extras (Component)
```

## Why single-task Space-Saving

Space-Saving’s theorems are for **one** table over the whole stream. Count-Min cells merge when hash coefficients match. Space-Saving does not use the pane merge theorem Helion ships for Count-Min.

`PaneWindow` wraps a `MergeableSketch` prototype. Panes share coefficients via `empty_copy()`. Space-Saving stays lifetime-global.

## Adding a component

1. Implement `helion.core.component.Component`.
2. Register on `HelionRuntime` or pass through `HelionFactory.production`.
3. Checkpointing includes extras inside `HelionRuntimeCodec` blobs.

## State

- **Codec:** `HelionRuntimeCodec` writes `HLRN` v1 bytes (see `helion.codec`).
- **Event time:** `StreamEvent.event_time_millis` drives pane expiry; `helion_flink` assigns bounded-out-of-orderness watermarks and routes late records to a tagged side channel.
- **Merge at scale:** `helion_flink` merges Count-Min in two phases (per-shard keyed state, then a global reduce) so estimates match a single-task reference at parallelism &gt; 1.
