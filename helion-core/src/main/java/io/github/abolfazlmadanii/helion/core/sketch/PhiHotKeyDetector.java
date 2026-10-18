package io.github.abolfazlmadanii.helion.core.sketch;

import io.github.abolfazlmadanii.helion.core.HelionEvent;
import io.github.abolfazlmadanii.helion.core.component.Component;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * Keys with {@code f̂(x) > φ N}. Requires {@code ε < φ} and {@code m = ceil(1/ε)}
 * so every true hot key with {@code f(x) > φ N} is stored (no false negatives).
 */
public final class PhiHotKeyDetector implements Component {

  private static final long serialVersionUID = 1L;

  private final String name;
  private final double phi;
  private final double epsilon;
  private final SpaceSaving sketch;

  public PhiHotKeyDetector(double phi, double epsilon) {
    this("phi_hot_keys", phi, epsilon);
  }

  public PhiHotKeyDetector(String name, double phi, double epsilon) {
    if (phi <= 0.0d || phi >= 1.0d) {
      throw new IllegalArgumentException("phi must lie in (0, 1)");
    }
    if (epsilon <= 0.0d || epsilon >= phi) {
      throw new IllegalArgumentException("epsilon must satisfy 0 < epsilon < phi");
    }
    this.name = name;
    this.phi = phi;
    this.epsilon = epsilon;
    this.sketch = new SpaceSaving(name + ".ss", (int) Math.ceil(1.0d / epsilon));
  }

  @Override
  public String name() {
    return name;
  }

  @Override
  public void onEvent(HelionEvent event) {
    sketch.update(event.key(), event.weight());
  }

  public List<SpaceSavingEstimate> hotKeys() {
    return sketch.heavyHitters(phi);
  }

  public SpaceSaving sketch() {
    return sketch;
  }

  @Override
  public Map<String, Object> snapshot() {
    Map<String, Object> snap = new LinkedHashMap<>();
    snap.put("name", name);
    snap.put("phi", phi);
    snap.put("epsilon", epsilon);
    snap.put("capacity", sketch.capacity());
    snap.put("hotKeyCount", hotKeys().size());
    snap.put("inner", sketch.snapshot());
    return snap;
  }
}
