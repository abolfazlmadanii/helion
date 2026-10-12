# Helion

Helion helps data engineers build **stream data pipelines**. Each model is a plug-in operator with a proven error bound, so you can add Count-Min, Space-Saving, pane windows, and later algorithms without rewriting the engine.

Production is **Java** (`helion-core` plus Flink or Kafka Streams). Both engines run the same `HelionRuntime`.

| Algorithm | Module | Guarantee |
|---|---|---|
| Count-Min Sketch | `CountMinSketch` | With probability ≥ 1−δ: \(f(x) \le \hat f(x) \le f(x)+\varepsilon N\) |
| Count-Min merge | `MergeableSketch` | Cell-wise sum of tables that share hash coefficients is Count-Min of the concatenated streams |
| Space-Saving | `SpaceSaving` | Deterministic: \(f(x) \le \hat f(x) \le f(x)+N/m\) for monitored keys; every key with \(f(x)>N/m\) is stored |
| φ hot keys | `PhiHotKeyDetector` | If \(\varepsilon < \varphi\) and \(m=\lceil 1/\varepsilon\rceil\), every key with \(f(x)>\varphi N\) is reported |
| Pane window | `PaneWindow` | At most \(k=W/\Delta\) mergeable sketches; query \(S_W=\bigoplus S_j\); expiry drops the oldest pane |

Math: [docs/MATH_COUNT_MIN.md](docs/MATH_COUNT_MIN.md), [docs/MATH_SPACE_SAVING.md](docs/MATH_SPACE_SAVING.md), [docs/MATH_PANE_WINDOW.md](docs/MATH_PANE_WINDOW.md). Layout: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Sliding window (production)

Most sketches **merge** and do not **subtract**. Helion therefore does not keep one lifetime t-digest/HLL/Count-Min and hope old mass leaves. It splits the window into disjoint panes (Li et al., 2005).

Let \(T\) be the maximum event time seen, \(W\) the window length, \(\Delta\) the pane width, \(k=W/\Delta\) (so \(W\) is a multiple of \(\Delta\)). The open pane start is \(s_{\mathrm{open}}=\Delta\lfloor T/\Delta\rfloor\). Retained panes satisfy

\[
s_{\mathrm{open}}-(k-1)\Delta \le s \le s_{\mathrm{open}}.
\]

For Count-Min panes that share Carter–Wegman coefficients,

\[
f_W(x) \le \hat f_W(x) \le f_W(x)+\varepsilon N_W
\]

with probability at least \(1-\delta\), where \(N_W\) is the weight **inside the pane-aligned window**, not the lifetime total.

The covered interval is pane-aligned, not a millisecond-exact \((T-W,T]\). Exponential histograms / DGIM (Datar et al., 2002) are a separate bounded-error **counting** algorithm; they are not the container for every sketch.

Space-Saving and φ stay **lifetime-global**. Pane merge is not the Space-Saving theorem Helion ships.

### References

1. Datar, Gionis, Indyk, Motwani, *Maintaining Stream Statistics over Sliding Windows*, SIAM J. Comput. 31(6), 2002.
2. Li, Maier, Tufte, Papadimos, Tucker, *No Pane, No Gain*, SIGMOD Record 34(1), 2005. DOI [10.1145/1058150.1058158](https://doi.org/10.1145/1058150.1058158).
3. Cormode, Muthukrishnan, *The Count-Min Sketch and its Applications*, J. Algorithms 55(1), 2005.
4. Metwally, Agrawal, Abbadi, *Efficient Computation of Frequent and Top-k Elements in Data Streams*, ICDT 2005 / TODS.
5. Flajolet, Fusy, Gandouet, Meunier, *HyperLogLog*, AOFA 2007 (merge by register max; not subtractable).
6. Dunning, *The t-digest*, Software Impacts 7, 2021.
7. Traub et al., *General Stream Slicing*, EDBT 2019; *Scotty*, TODS 2021.
8. Verwiebe, Grulich, Traub, Markl et al., *Survey of window types for aggregation in stream processing systems*, VLDB Journal, 2023.

Flink and Spark already document window aggregation. Helion’s layer is mergeable sketches plus pane expiry as one `Component`, with the Count-Min bound stated on \(N_W\).

## Modules

```
helion-core            sketches, PaneWindow, Component SPI (no Flink/Kafka types)
helion-flink           ProcessFunction, operator state, Kafka source/sink job
helion-kafka-streams   Processor API, changelog store, Streams app
```

Attach extra operators with `io.helion.core.component.Component` on `HelionProcessFunction` or `HelionTopology.hotKeys(...)`.

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

`HelionFlinkJob` reads `HELION_INPUT_TOPIC`, writes `HELION_OUTPUT_TOPIC`. The Helion operator is **parallelism 1** so Space-Saving sees the global stream. Checkpointing serializes the full runtime, including `count_min.window`.

| Env | Default | Role |
|---|---|---|
| `HELION_WINDOW_MS` | `86400000` (24h) | Pane window length |
| `HELION_PANE_MS` | `3600000` (1h) | Pane width; must divide the window |
| `HELION_CMS_EPSILON` / `HELION_CMS_DELTA` | `0.01` / `0.0001` | Lifetime and window Count-Min |
| `HELION_PHI` / `HELION_EPSILON` | `0.01` / `0.001` | Hot-key φ and Space-Saving \(\varepsilon\) |

Input records: `key` or `key,weight` or `key,weight,eventTimeMillis`. Event time is required for a correct window; otherwise the parser uses ingest time.

## Kafka Streams

```bash
mvn -pl helion-kafka-streams -am package
java -jar helion-kafka-streams/target/helion-kafka-streams-0.1.0.jar
```

Same window env vars as Flink. Give the input topic **one partition** (or a one-partition repartition) and `NUM_STREAM_THREADS=1`. Otherwise each task holds a local Space-Saving table and the \(f>N/m\) guarantee is per-partition.

## Extending

```java
new HelionProcessFunction(
    0.01, 1e-4, 0.01, 0.001,
    List.of(HelionFactory.paneCountMin(0.01, 1e-4, 86_400_000L, 3_600_000L)));
```

Or `HelionFactory.production(cmsEps, cmsDelta, phi, ssEps, windowMs, paneMs, extras)`.

Do not edit Count-Min or Space-Saving to wire new code. Implement `MergeableSketch` for a new mergeable summary, then wrap it in `PaneWindow`.

## Reference Python

`reference/python` is an offline copy of Count-Min and Space-Saving math. Production windowing is Java only.
