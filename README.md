# Helion

Helion is a **Python 3.12** library for streaming frequency sketches with proven error bounds: Count-Min, Space-Saving, φ hot-key detection, and pane-aligned Count-Min windows. A small component runtime (`HelionRuntime`) composes operators; checkpoints use `HelionRuntimeCodec` (binary HLRN v1, not pickle).

Optional packages wire the same runtime into **PyFlink 2.2.1** (`helion_flink`) and **Quix Streams 3.28** (`helion_quix`).

| Algorithm | Type | Guarantee |
|---|---|---|
| Count-Min Sketch | `CountMinSketch` | With probability ≥ 1−δ: \(f(x) \le \hat f(x) \le f(x)+\varepsilon N\) |
| Count-Min merge | `MergeableSketch` | Cell-wise sum with shared hash coefficients |
| Space-Saving | `SpaceSaving` | \(f(x) \le \hat f(x) \le f(x)+N/m\) for monitored keys |
| φ hot keys | `PhiHotKeyDetector` | With \(\varepsilon < \varphi\), every key with \(f(x)>\varphi N\) is reported |
| Pane window | `PaneWindow` | At most \(k=W/\Delta\) mergeable sketches; query is merge of retained panes |

Further detail: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md), [docs/ADR-010-python-stack.md](docs/ADR-010-python-stack.md), and the math notes under `docs/MATH_*.md`.

## Quickstart with uv

Install [uv](https://docs.astral.sh/uv/), then from the repo root:

```bash
uv sync --all-extras --dev
```

Core library only (no stream engines):

```bash
uv sync
```

PyFlink or Quix only:

```bash
uv sync --extra flink
uv sync --extra quix
```

## Project layout

```
helion/           sketches, PaneWindow, HelionRuntime, HelionRuntimeCodec
helion_flink/     bounded PyFlink job (watermarks, late tagging, CMS merge)
helion_quix/      Quix Streams Application with keyed runtime state
tests/            pytest (library, Flink replay, Quix replay)
```

## Library usage

```python
from helion import CountMinSketch, HelionRuntime, StreamEvent

runtime = HelionRuntime([CountMinSketch(epsilon=0.01, delta=1e-4)])
runtime.push(StreamEvent("user-1", weight=1, event_time_millis=1_700_000_000_000))
print(runtime.snapshots())
```

Pane windows keep Count-Min per pane; Space-Saving and φ stay lifetime-global. See [docs/MATH_PANE_WINDOW.md](docs/MATH_PANE_WINDOW.md).

## PyFlink job (`helion_flink`)

Bounded in-process replay (no Kafka): event-time watermarks, late records tagged `late-records` and excluded from the main pipeline, global `HelionRuntimeCodec` state, and a two-phase Count-Min merge validated at parallelism 1 and 2.

```python
from helion.core.events import StreamEvent
from helion_flink import HelionJobConfig, run_bounded_job

events = [
    StreamEvent(key="k0", weight=2, event_time_millis=1_000),
    StreamEvent(key="k1", weight=1, event_time_millis=1_100),
]
cfg = HelionJobConfig()
result_bytes = run_bounded_job(events, parallelism=2, cfg=cfg)
print(result_bytes.decode())
```

Install with `uv sync --extra flink` (pins `apache-flink==2.2.1`). PyFlink replay tests need the **PyFlink runtime** on `PATH`; they are skipped when it is missing.

## Quix Streams app (`helion_quix`)

Stateful `Application` with JSON values `{"key", "weight", "event_time_millis"}`. Kafka message keys partition `HelionRuntimeCodec` state.

**Broker deployment:**

```python
from helion_quix import build_application

app, sdf = build_application("localhost:9092", consumer_group="helion")
# add sinks or branches on sdf, then:
app.run()
```

**In-process replay (no broker):**

```python
from helion.core.events import StreamEvent
from helion_quix import HelionQuixConfig, replay_events

cfg = HelionQuixConfig()
events = [StreamEvent("k0", weight=1, event_time_millis=1_000)]
hot_lines, runtime_blob = replay_events(events, cfg)
```

Install with `uv sync --extra quix` (pins `quixstreams==3.28.1`).

## Tests

```bash
uv sync --all-extras --dev
uv run ruff check
uv run pytest
```

The suite includes library tests, PyFlink bounded replay (parallelism 1 and 2), and Quix processor replay. CI runs on pushes to `main` and `week2-python-port`, and on pull requests.
