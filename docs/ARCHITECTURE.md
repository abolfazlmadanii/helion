# Architecture

Helion is a Python library of mergeable sketches and a small component runtime. Stream engines attach in separate packages.

```
Kafka topic (future: helion_flink / helion_quix)
    │
    └─ HelionRuntime (in-process today)
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
- **Event time:** `StreamEvent.event_time_millis` drives pane expiry; engines will assign watermarks and late side outputs in `helion_flink`.
- **Merge at scale:** two-phase local→global merge for Count-Min is planned with PyFlink keyed state.
