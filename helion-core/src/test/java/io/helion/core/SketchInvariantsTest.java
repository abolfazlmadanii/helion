package io.helion.core;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import io.helion.core.runtime.HelionRuntime;
import io.helion.core.sketch.CountMinSketch;
import io.helion.core.sketch.PhiHotKeyDetector;
import io.helion.core.sketch.SpaceSaving;
import io.helion.core.sketch.SpaceSavingEstimate;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;

class SketchInvariantsTest {

  @Test
  void countMinNeverUnderestimates() {
    CountMinSketch cms = new CountMinSketch(0.05, 0.01);
    Map<String, Integer> truth = new HashMap<>();
    String[] stream = new String[65];
    int i = 0;
    for (int n = 0; n < 40; n++) stream[i++] = "a";
    for (int n = 0; n < 15; n++) stream[i++] = "b";
    for (int n = 0; n < 7; n++) stream[i++] = "c";
    for (int n = 0; n < 3; n++) stream[i++] = "d";
    for (String key : stream) {
      cms.update(key, 1);
      truth.merge(key, 1, Integer::sum);
    }
    for (Map.Entry<String, Integer> e : truth.entrySet()) {
      assertTrue(cms.estimate(e.getKey()) >= e.getValue());
    }
  }

  @Test
  void countMinDimensionsMatchTheorem() {
    double eps = 0.01;
    double delta = 1e-4;
    CountMinSketch cms = new CountMinSketch(eps, delta);
    assertEquals((int) Math.ceil(Math.E / eps), cms.width());
    assertEquals((int) Math.ceil(Math.log(1.0 / delta)), cms.depth());
  }

  @Test
  void spaceSavingSumEqualsNAndHeavyKeysStay() {
    SpaceSaving ss = new SpaceSaving(3);
    String[] stream = {
      "hot", "hot", "hot", "hot", "hot", "hot", "hot", "hot", "hot", "hot",
      "hot", "hot", "hot", "hot", "hot", "hot", "hot", "hot", "hot", "hot",
      "a", "a", "b", "b", "c", "c", "d", "d"
    };
    Map<String, Integer> truth = new HashMap<>();
    for (String key : stream) {
      ss.update(key, 1);
      truth.merge(key, 1, Integer::sum);
    }
    assertEquals(stream.length, ss.counterSum());
    assertEquals(stream.length, ss.total());
    assertTrue(ss.minCount() <= ss.total() / (double) ss.capacity());
    double bound = ss.total() / (double) ss.capacity();
    for (Map.Entry<String, Integer> e : truth.entrySet()) {
      if (e.getValue() > bound) {
        assertTrue(ss.monitored(e.getKey()));
      }
    }
    for (SpaceSavingEstimate row : ss.monitored()) {
      long f = truth.getOrDefault(row.key(), 0);
      assertTrue(f <= row.estimate());
      assertTrue(row.estimate() <= f + bound + 1e-9);
    }
  }

  @Test
  void runtimeAcceptsExtraComponent() {
    CountingComponent probe = new CountingComponent();
    HelionRuntime runtime =
        new HelionRuntime(
            List.of(
                new CountMinSketch(0.2, 0.1),
                new SpaceSaving(3),
                new PhiHotKeyDetector(0.3, 0.2),
                probe));
    runtime.ingest(HelionEvent.of("a"));
    runtime.ingest(HelionEvent.of("a"));
    runtime.ingest(HelionEvent.of("b"));
    assertEquals(3, probe.count);
    assertEquals(3, runtime.totalWeight());
    assertTrue(runtime.snapshots().containsKey("probe"));
  }

  private static final class CountingComponent implements io.helion.core.component.Component {
    private static final long serialVersionUID = 1L;
    private int count;

    @Override
    public String name() {
      return "probe";
    }

    @Override
    public void onEvent(HelionEvent event) {
      count++;
    }
  }
}
