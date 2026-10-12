package io.helion.core.window;

import io.helion.core.HelionEvent;
import io.helion.core.component.Component;
import io.helion.core.sketch.MergeableSketch;
import java.util.ArrayDeque;
import java.util.Iterator;
import java.util.LinkedHashMap;
import java.util.Map;

/**
 * Pane-aligned sliding window over a mergeable sketch (Li et al., SIGMOD Record
 * 2005). The stream is split into disjoint panes of width {@code paneMillis}.
 * The query sketch is the merge of the at most {@code windowMillis/paneMillis}
 * panes whose start lies in
 * {@code [openStart − (k−1)·Δ, openStart]}, where {@code openStart} is the pane
 * containing the maximum event time seen so far.
 *
 * <p>Expiry drops the oldest pane. There is no subtract on the sketch. Late
 * events that still fall in a retained pane update that pane; older events are
 * ignored. The covered interval is pane-aligned, not an exact {@code (t−W, t]}
 * cut.
 */
public final class PaneWindow implements Component {

  private static final long serialVersionUID = 1L;

  private final String name;
  private final long windowMillis;
  private final long paneMillis;
  private final int maxPanes;
  private final MergeableSketch prototype;
  private final ArrayDeque<Pane> panes = new ArrayDeque<>();

  private long maxEventTime = Long.MIN_VALUE;
  private transient MergeableSketch closedMerge;
  private transient boolean closedMergeValid;

  public PaneWindow(String name, MergeableSketch prototype, long windowMillis, long paneMillis) {
    if (name == null || name.isBlank()) {
      throw new IllegalArgumentException("name is required");
    }
    if (prototype == null) {
      throw new IllegalArgumentException("prototype sketch is required");
    }
    if (paneMillis <= 0L) {
      throw new IllegalArgumentException("paneMillis must be positive");
    }
    if (windowMillis < paneMillis || windowMillis % paneMillis != 0L) {
      throw new IllegalArgumentException("windowMillis must be a positive multiple of paneMillis");
    }
    this.name = name;
    this.prototype = prototype;
    this.windowMillis = windowMillis;
    this.paneMillis = paneMillis;
    this.maxPanes = (int) (windowMillis / paneMillis);
  }

  @Override
  public String name() {
    return name;
  }

  @Override
  public void onEvent(HelionEvent event) {
    long t = event.eventTimeMillis();
    if (t > maxEventTime) {
      maxEventTime = t;
      expire();
    }
    long start = paneStart(t);
    long openStart = paneStart(maxEventTime);
    long oldestStart = openStart - (long) (maxPanes - 1) * paneMillis;
    if (start < oldestStart) {
      return;
    }
    Pane pane = paneAt(start);
    if (pane == null) {
      pane = new Pane(start, prototype.emptyCopy());
      insert(pane);
    }
    pane.sketch.update(event.key(), event.weight());
    if (start != openStart) {
      closedMergeValid = false;
    }
  }

  public long estimate(String key) {
    return merged().estimate(key);
  }

  public long windowTotal() {
    return merged().total();
  }

  public MergeableSketch merged() {
    MergeableSketch acc = prototype.emptyCopy();
    if (!closedMergeValid) {
      rebuildClosedMerge();
    }
    if (closedMerge != null) {
      acc.mergeFrom(closedMerge);
    }
    Pane open = openPane();
    if (open != null) {
      acc.mergeFrom(open.sketch);
    }
    return acc;
  }

  public int retainedPaneCount() {
    return panes.size();
  }

  public long coverageStartMillis() {
    if (panes.isEmpty()) {
      return 0L;
    }
    return panes.peekFirst().startMillis;
  }

  public long maxEventTimeMillis() {
    return maxEventTime == Long.MIN_VALUE ? 0L : maxEventTime;
  }

  public long windowMillis() {
    return windowMillis;
  }

  public long paneMillis() {
    return paneMillis;
  }

  public int maxPanes() {
    return maxPanes;
  }

  private void expire() {
    if (maxEventTime == Long.MIN_VALUE) {
      return;
    }
    long oldestStart = paneStart(maxEventTime) - (long) (maxPanes - 1) * paneMillis;
    boolean dropped = false;
    while (!panes.isEmpty() && panes.peekFirst().startMillis < oldestStart) {
      panes.removeFirst();
      dropped = true;
    }
    if (dropped) {
      closedMergeValid = false;
    }
  }

  private Pane paneAt(long start) {
    for (Pane pane : panes) {
      if (pane.startMillis == start) {
        return pane;
      }
    }
    return null;
  }

  private Pane openPane() {
    if (panes.isEmpty() || maxEventTime == Long.MIN_VALUE) {
      return null;
    }
    long openStart = paneStart(maxEventTime);
    Pane last = panes.peekLast();
    return last.startMillis == openStart ? last : null;
  }

  private void insert(Pane pane) {
    if (panes.isEmpty() || pane.startMillis >= panes.peekLast().startMillis) {
      panes.addLast(pane);
      return;
    }
    ArrayDeque<Pane> rest = new ArrayDeque<>();
    while (!panes.isEmpty() && panes.peekLast().startMillis > pane.startMillis) {
      rest.addFirst(panes.removeLast());
    }
    panes.addLast(pane);
    panes.addAll(rest);
    closedMergeValid = false;
  }

  private void rebuildClosedMerge() {
    MergeableSketch acc = prototype.emptyCopy();
    long openStart = maxEventTime == Long.MIN_VALUE ? Long.MIN_VALUE : paneStart(maxEventTime);
    Iterator<Pane> it = panes.iterator();
    while (it.hasNext()) {
      Pane pane = it.next();
      if (pane.startMillis != openStart) {
        acc.mergeFrom(pane.sketch);
      }
    }
    closedMerge = acc;
    closedMergeValid = true;
  }

  private long paneStart(long eventTime) {
    long q = Math.floorDiv(eventTime, paneMillis);
    return q * paneMillis;
  }

  @Override
  public Map<String, Object> snapshot() {
    Map<String, Object> snap = new LinkedHashMap<>();
    snap.put("name", name);
    snap.put("algorithm", "pane_window");
    snap.put("windowMillis", windowMillis);
    snap.put("paneMillis", paneMillis);
    snap.put("maxPanes", maxPanes);
    snap.put("retainedPanes", panes.size());
    snap.put("windowTotal", panes.isEmpty() ? 0L : windowTotal());
    snap.put("maxEventTime", maxEventTimeMillis());
    snap.put("coverageStart", coverageStartMillis());
    snap.put("guarantee", "pane-aligned union of mergeable sketches; drop oldest pane");
    return snap;
  }

  private static final class Pane implements java.io.Serializable {
    private static final long serialVersionUID = 1L;
    private final long startMillis;
    private final MergeableSketch sketch;

    private Pane(long startMillis, MergeableSketch sketch) {
      this.startMillis = startMillis;
      this.sketch = sketch;
    }
  }
}
