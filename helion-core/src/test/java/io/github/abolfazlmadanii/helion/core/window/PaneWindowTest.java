package io.github.abolfazlmadanii.helion.core.window;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import io.github.abolfazlmadanii.helion.core.HelionEvent;
import io.github.abolfazlmadanii.helion.core.HelionFactory;
import io.github.abolfazlmadanii.helion.core.runtime.HelionRuntime;
import io.github.abolfazlmadanii.helion.core.sketch.CountMinSketch;
import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.ObjectInputStream;
import java.io.ObjectOutputStream;
import java.util.List;
import org.junit.jupiter.api.Test;

class PaneWindowTest {

  private static final long PANE = 1_000L;
  private static final long WINDOW = 3_000L;

  @Test
  void mergedWindowEqualsReplayOfRetainedEvents() {
    CountMinSketch proto = new CountMinSketch(0.05, 0.01);
    PaneWindow window = new PaneWindow("w", proto.emptyCopy(), WINDOW, PANE);
    CountMinSketch gold = proto.emptyCopy();

    ingest(window, "old", 1, 100);
    ingest(window, "mid", 1, 1_100);
    ingest(window, "fresh", 1, 2_100);
    ingest(window, "fresh", 1, 3_100);

    gold.update("mid", 1);
    gold.update("fresh", 1);
    gold.update("fresh", 1);

    assertEquals(gold.total(), window.windowTotal());
    assertEquals(gold.estimate("old"), window.estimate("old"));
    assertEquals(gold.estimate("mid"), window.estimate("mid"));
    assertEquals(gold.estimate("fresh"), window.estimate("fresh"));
    assertTrue(window.retainedPaneCount() <= window.maxPanes());
  }

  @Test
  void expiredPaneIsDroppedNotSubtracted() {
    CountMinSketch proto = new CountMinSketch(0.05, 0.01);
    PaneWindow window = new PaneWindow("w", proto.emptyCopy(), WINDOW, PANE);
    ingest(window, "only-old", 5, 50);
    assertEquals(5L, window.windowTotal());
    ingest(window, "keep", 1, 3_050);
    CountMinSketch gold = proto.emptyCopy();
    gold.update("keep", 1);
    assertEquals(gold.total(), window.windowTotal());
    assertEquals(gold.estimate("only-old"), window.estimate("only-old"));
  }

  @Test
  void lateEventInRetainedPaneUpdatesThatPane() {
    CountMinSketch proto = new CountMinSketch(0.05, 0.01);
    PaneWindow window = new PaneWindow("w", proto.emptyCopy(), WINDOW, PANE);
    ingest(window, "a", 1, 2_100);
    ingest(window, "late", 1, 1_100);
    CountMinSketch gold = proto.emptyCopy();
    gold.update("a", 1);
    gold.update("late", 1);
    assertEquals(gold.estimate("late"), window.estimate("late"));
    assertEquals(2L, window.windowTotal());
  }

  @Test
  void eventOlderThanWindowIsIgnored() {
    CountMinSketch proto = new CountMinSketch(0.05, 0.01);
    PaneWindow window = new PaneWindow("w", proto.emptyCopy(), WINDOW, PANE);
    ingest(window, "now", 1, 5_000);
    ingest(window, "too-old", 1, 100);
    CountMinSketch gold = proto.emptyCopy();
    gold.update("now", 1);
    assertEquals(gold.total(), window.windowTotal());
    assertEquals(gold.estimate("too-old"), window.estimate("too-old"));
  }

  @Test
  void countMinMergeEqualsSingleSketchOnSameHashes() {
    CountMinSketch left = new CountMinSketch(0.1, 0.05);
    CountMinSketch right = left.emptyCopy();
    CountMinSketch all = left.emptyCopy();
    left.update("x", 3);
    right.update("y", 2);
    all.update("x", 3);
    all.update("y", 2);
    CountMinSketch merged = left.emptyCopy();
    merged.mergeFrom(left);
    merged.mergeFrom(right);
    assertEquals(all.total(), merged.total());
    assertEquals(all.estimate("x"), merged.estimate("x"));
    assertEquals(all.estimate("y"), merged.estimate("y"));
  }

  @Test
  void mergeRejectsDifferentHashCoefficients() {
    CountMinSketch a = new CountMinSketch(0.1, 0.05);
    CountMinSketch b = new CountMinSketch(0.1, 0.05);
    a.update("x", 1);
    b.update("x", 1);
    assertThrows(IllegalArgumentException.class, () -> a.mergeFrom(b));
  }

  @Test
  void factoryRuntimeExposesWindowAndSurvivesSerialization() throws Exception {
    HelionRuntime runtime =
        HelionFactory.production(0.2, 0.1, 0.4, 0.2, WINDOW, PANE, List.of());
    runtime.ingest(HelionEvent.of("hot", 1, 100));
    runtime.ingest(HelionEvent.of("hot", 1, 1_100));
    runtime.ingest(HelionEvent.of("hot", 1, 4_100));
    PaneWindow window = (PaneWindow) runtime.registry().get("count_min.window");
    assertEquals(1L, window.windowTotal());
    assertTrue(runtime.snapshots().containsKey("count_min.window"));

    ByteArrayOutputStream bos = new ByteArrayOutputStream();
    try (ObjectOutputStream oos = new ObjectOutputStream(bos)) {
      oos.writeObject(runtime);
    }
    HelionRuntime restored;
    try (ObjectInputStream ois =
        new ObjectInputStream(new ByteArrayInputStream(bos.toByteArray()))) {
      restored = (HelionRuntime) ois.readObject();
    }
    PaneWindow restoredWindow = (PaneWindow) restored.registry().get("count_min.window");
    assertEquals(window.windowTotal(), restoredWindow.windowTotal());
    assertEquals(window.estimate("hot"), restoredWindow.estimate("hot"));
  }

  @Test
  void neverUnderestimatesRetainedFrequencies() {
    CountMinSketch proto = new CountMinSketch(0.05, 0.01);
    PaneWindow window = new PaneWindow("w", proto.emptyCopy(), WINDOW, PANE);
    long[] times = {10, 1_010, 2_010, 3_010};
    int[] counts = {4, 3, 2, 7};
    String[] keys = {"a", "b", "c", "d"};
    for (int i = 0; i < times.length; i++) {
      for (int n = 0; n < counts[i]; n++) {
        ingest(window, keys[i], 1, times[i] + n);
      }
    }
    assertTrue(window.estimate("d") >= 7);
    assertTrue(window.estimate("c") >= 2);
    assertEquals(0L, window.estimate("a"));
  }

  private static void ingest(PaneWindow window, String key, long weight, long time) {
    window.onEvent(HelionEvent.of(key, weight, time));
  }
}
