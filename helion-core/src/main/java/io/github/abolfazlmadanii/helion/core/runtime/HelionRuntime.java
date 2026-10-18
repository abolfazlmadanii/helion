package io.github.abolfazlmadanii.helion.core.runtime;

import io.github.abolfazlmadanii.helion.core.HelionEvent;
import io.github.abolfazlmadanii.helion.core.component.Component;
import io.github.abolfazlmadanii.helion.core.component.ComponentRegistry;
import java.io.Serializable;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * Fan-out runtime shared by Flink and Kafka Streams. Task threads in both
 * engines are single-threaded per operator instance, which matches this object.
 */
public final class HelionRuntime implements Serializable {

  private static final long serialVersionUID = 1L;

  private final ComponentRegistry registry = new ComponentRegistry();
  private long totalWeight;

  public HelionRuntime(List<Component> components) {
    if (components != null) {
      for (Component component : components) {
        attach(component);
      }
    }
  }

  public void attach(Component component) {
    registry.register(component);
  }

  public void ingest(HelionEvent event) {
    totalWeight += event.weight();
    for (Component component : registry) {
      component.onEvent(event);
    }
  }

  public ComponentRegistry registry() {
    return registry;
  }

  public long totalWeight() {
    return totalWeight;
  }

  public Map<String, Map<String, Object>> snapshots() {
    Map<String, Map<String, Object>> out = new LinkedHashMap<>();
    for (Component component : registry) {
      out.put(component.name(), component.snapshot());
    }
    return out;
  }
}
