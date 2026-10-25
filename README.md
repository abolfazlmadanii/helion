# Helion

Helion helps data engineers build **stream data pipelines**. Each model is a plug-in operator with a proven error bound, so you can add Count-Min, Space-Saving, pane windows, and later algorithms without rewriting the engine.

| Algorithm | Type | Guarantee |
|---|---|---|
| Count-Min Sketch | `CountMinSketch` | With probability ≥ 1−δ: \(f(x) \le \hat f(x) \le f(x)+\varepsilon N\) |
| Count-Min merge | `MergeableSketch` | Cell-wise sum with shared hash coefficients |
| Space-Saving | `SpaceSaving` | \(f(x) \le \hat f(x) \le f(x)+N/m\) for monitored keys |
| φ hot keys | `PhiHotKeyDetector` | With \(\varepsilon < \varphi\), every key with \(f(x)>\varphi N\) is reported |
| Pane window | `PaneWindow` | At most \(k=W/\Delta\) mergeable sketches; query is merge of retained panes |

Math: [docs/MATH_COUNT_MIN.md](docs/MATH_COUNT_MIN.md), [docs/MATH_SPACE_SAVING.md](docs/MATH_SPACE_SAVING.md), [docs/MATH_PANE_WINDOW.md](docs/MATH_PANE_WINDOW.md). Layout: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md). Stack: [docs/ADR-010-python-stack.md](docs/ADR-010-python-stack.md).

## Install

Python 3.12 and [uv](https://docs.astral.sh/uv/).

```bash
uv sync --all-extras --dev
uv run pytest
```

## Library layout

```
helion/           sketches, PaneWindow, Component SPI, versioned runtime codec
helion_flink/     PyFlink 2.2.1 bounded replay job (watermarks, late routing, CMS merge)
tests/            pytest suite
```

`helion_quix` is planned in a follow-on slice. PyFlink replay tests need a JDK 17 runtime on `PATH` (`uv sync --extra flink`).

## Quick start

```python
from helion import CountMinSketch, HelionRuntime, StreamEvent

runtime = HelionRuntime([CountMinSketch(epsilon=0.01, delta=1e-4)])
runtime.push(StreamEvent("user-1", weight=1, event_time_millis=1_700_000_000_000))
print(runtime.snapshots())
```

Operator checkpoints use `HelionRuntimeCodec.encode(runtime)`—explicit binary layout, not pickle.

## Sliding window

Pane-aligned windows merge Count-Min sketches per pane and drop the oldest pane on expiry. Space-Saving and φ remain lifetime-global. See [docs/MATH_PANE_WINDOW.md](docs/MATH_PANE_WINDOW.md).
