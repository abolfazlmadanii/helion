# Helion

Helion helps data engineers build **stream data pipelines**. Each model is a plug-in operator with a proven error bound, so you can add Count-Min, Space-Saving, and later algorithms without rewriting the engine.

| Algorithm | Module | Guarantee |
|---|---|---|
|---|---|---|
| Count-Min Sketch | `helion-core` → `CountMinSketch` | With probability ≥ 1−δ: `f(x) ≤ f̂(x) ≤ f(x) + εN` |
| Space-Saving | `helion-core` → `SpaceSaving` | Deterministic: `f(x) ≤ f̂(x) ≤ f(x) + N/m` for monitored keys; every key with `f(x) > N/m` is stored |

Math: [docs/MATH_COUNT_MIN.md](docs/MATH_COUNT_MIN.md), [docs/MATH_SPACE_SAVING.md](docs/MATH_SPACE_SAVING.md). Layout: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Modules

```
helion-core            sketches + Component SPI (no Flink/Kafka types)
helion-flink           ProcessFunction, operator state, Kafka source/sink job
helion-kafka-streams   Processor API, changelog store, Streams app
```

Both engines call the same `HelionRuntime`. New operators implement `io.helion.core.component.Component` and pass a list of extras into `HelionProcessFunction` or `HelionTopology.hotKeys(...)`.

## Build

Java 17+, Maven 3.9+.

```bash
mvn -q test
```

## Flink

```bash
mvn -pl helion-flink -am package
flink run helion-flink/target/helion-flink-0.1.0.jar
```

`HelionFlinkJob` reads `HELION_INPUT_TOPIC`, writes `HELION_OUTPUT_TOPIC`. The Helion operator is **parallelism 1** so Space-Saving sees the global stream. Checkpointing serializes the full runtime.

Input records: `key` or `key,weight`.

## Kafka Streams

```bash
mvn -pl helion-kafka-streams -am package
java -jar helion-kafka-streams/target/helion-kafka-streams-0.1.0.jar
```

Give the input topic **one partition** (or a one-partition repartition) and `NUM_STREAM_THREADS=1`. Otherwise each task holds a local sketch and the `f > N/m` guarantee is per-partition, not global.

## Extending

```java
public final class LatencySink implements Component {
  public String name() { return "latency_sink"; }
  public void onEvent(HelionEvent event) { /* metrics, export, window hook */ }
}

new HelionProcessFunction(0.01, 1e-4, 0.01, 0.001, List.of(new LatencySink()));
```

Do not edit Count-Min or Space-Saving to wire new code.

## Reference Python

`reference/python` is an offline copy of the same math for unit exploration. Production is Java + Flink / Kafka Streams.
