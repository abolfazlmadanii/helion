package io.helion.core;

import java.io.Serializable;
import java.util.Collections;
import java.util.Map;
import java.util.Objects;

/** One cash-register observation. Weight must be a positive integer. */
public final class HelionEvent implements Serializable {

  private static final long serialVersionUID = 1L;

  private final String key;
  private final long weight;
  private final long eventTimeMillis;
  private final Map<String, String> attributes;

  public HelionEvent(String key, long weight, long eventTimeMillis, Map<String, String> attributes) {
    if (key == null || key.isEmpty()) {
      throw new IllegalArgumentException("key must be non-empty");
    }
    if (weight < 1L) {
      throw new IllegalArgumentException("weight must be a positive integer");
    }
    this.key = key;
    this.weight = weight;
    this.eventTimeMillis = eventTimeMillis;
    this.attributes = attributes == null ? Map.of() : Map.copyOf(attributes);
  }

  public static HelionEvent of(String key) {
    return new HelionEvent(key, 1L, System.currentTimeMillis(), Map.of());
  }

  public String key() {
    return key;
  }

  public long weight() {
    return weight;
  }

  public long eventTimeMillis() {
    return eventTimeMillis;
  }

  public Map<String, String> attributes() {
    return Collections.unmodifiableMap(attributes);
  }

  @Override
  public boolean equals(Object o) {
    if (this == o) {
      return true;
    }
    if (!(o instanceof HelionEvent that)) {
      return false;
    }
    return weight == that.weight
        && eventTimeMillis == that.eventTimeMillis
        && key.equals(that.key)
        && attributes.equals(that.attributes);
  }

  @Override
  public int hashCode() {
    return Objects.hash(key, weight, eventTimeMillis, attributes);
  }

  @Override
  public String toString() {
    return "HelionEvent{key='" + key + "', weight=" + weight + "}";
  }
}
