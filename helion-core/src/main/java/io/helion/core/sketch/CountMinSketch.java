package io.helion.core.sketch;

import io.helion.core.HelionEvent;
import io.helion.core.component.Component;
import io.helion.core.hashing.CarterWegman;
import java.util.LinkedHashMap;
import java.util.Map;

/**
 * Count-Min Sketch (Cormode, Muthukrishnan 2005).
 *
 * <p>With {@code w = ceil(e/ε)} and {@code d = ceil(ln(1/δ))}, for every key x
 * {@code f(x) ≤ f̂(x) ≤ f(x) + ε N} holds with probability at least {@code 1−δ}.
 * The left inequality is deterministic (one-sided overestimate).
 */
public final class CountMinSketch implements Component {

  private static final long serialVersionUID = 1L;

  private final String name;
  private final double epsilon;
  private final double delta;
  private final int width;
  private final int depth;
  private final long[] a;
  private final long[] b;
  private final long[][] table;
  private long total;

  public CountMinSketch(double epsilon, double delta) {
    this("count_min", epsilon, delta);
  }

  public CountMinSketch(String name, double epsilon, double delta) {
    if (epsilon <= 0.0d) {
      throw new IllegalArgumentException("epsilon must be positive");
    }
    if (delta <= 0.0d || delta >= 1.0d) {
      throw new IllegalArgumentException("delta must lie in (0, 1)");
    }
    this.name = name;
    this.epsilon = epsilon;
    this.delta = delta;
    this.width = (int) Math.ceil(Math.E / epsilon);
    this.depth = (int) Math.ceil(Math.log(1.0d / delta));
    this.a = new long[depth];
    this.b = new long[depth];
    this.table = new long[depth][width];
    for (int i = 0; i < depth; i++) {
      long[] pair = CarterWegman.drawPair();
      a[i] = pair[0];
      b[i] = pair[1];
    }
  }

  @Override
  public String name() {
    return name;
  }

  public void update(String key, long weight) {
    if (weight < 1L) {
      throw new IllegalArgumentException("weight must be a positive integer");
    }
    long x = CarterWegman.keyToField(key);
    for (int row = 0; row < depth; row++) {
      int col = CarterWegman.index(x, a[row], b[row], width);
      table[row][col] += weight;
    }
    total += weight;
  }

  public long estimate(String key) {
    long x = CarterWegman.keyToField(key);
    long min = Long.MAX_VALUE;
    for (int row = 0; row < depth; row++) {
      int col = CarterWegman.index(x, a[row], b[row], width);
      min = Math.min(min, table[row][col]);
    }
    return min;
  }

  public int width() {
    return width;
  }

  public int depth() {
    return depth;
  }

  public long total() {
    return total;
  }

  public double additiveSlack() {
    return epsilon * total;
  }

  @Override
  public void onEvent(HelionEvent event) {
    update(event.key(), event.weight());
  }

  @Override
  public Map<String, Object> snapshot() {
    Map<String, Object> snap = new LinkedHashMap<>();
    snap.put("name", name);
    snap.put("algorithm", "count_min");
    snap.put("epsilon", epsilon);
    snap.put("delta", delta);
    snap.put("width", width);
    snap.put("depth", depth);
    snap.put("total", total);
    snap.put("guarantee", "P(f <= hat <= f + eps*N) >= 1-delta");
    return snap;
  }
}
