# Architecture

Helion production path is Java. Flink and Kafka Streams are thin engines around `helion-core`.

```
Kafka topic
    │
    ├─ Flink: HelionFlinkJob
    │       parse → HelionProcessFunction (parallelism 1, operator state)
    │                    │
    │                    └─ HelionRuntime
    │                         ├─ CountMinSketch (lifetime)
    │                         ├─ SpaceSaving (lifetime; not pane-merged)
    │                         ├─ PhiHotKeyDetector
    │                         ├─ PaneWindow → Count-Min per pane
    │                         └─ extras (Component)
    │
    └─ Kafka Streams: HelionStreamsApp
            HelionProcessor + persistent KV store (changelog)
                    └─ same HelionRuntime
```

## Why parallelism 1

Space-Saving’s theorems are for **one** table over the whole stream. Splitting by key or by partition makes `N` local. Count-Min cells can be merged (same hash coefficients, cell-wise sum); Space-Saving merge is not the published theorem. Helion therefore pins the sketch operator to a single task.

`PaneWindow` is a `Component` around a `MergeableSketch` prototype. Panes share hash coefficients via `emptyCopy()`. Do not fork Count-Min or Space-Saving to add expiry. Space-Saving stays lifetime-global: pane merge is not its published theorem.

## Adding a component

1. Implement `io.helion.core.component.Component`.
2. Pass it in the extras list of `HelionFactory.production`, `HelionProcessFunction`, or `HelionTopology.hotKeys`.
3. Checkpointing includes extras because they live inside the serialized `HelionRuntime`.

## State

- Flink: `UnionListState<byte[]>` of Java-serialized `HelionRuntime`, restored on checkpoint.
- Kafka Streams: persistent key-value store `helion-runtime-store` with changelog, Serde via Java serialization.
