package io.github.abolfazlmadanii.helion.core.sketch;

import java.io.Serializable;

public final class SpaceSavingEstimate implements Serializable {

  private static final long serialVersionUID = 1L;

  private final String key;
  private final long estimate;
  private final long error;
  private final boolean monitored;
  private final long totalEvents;
  private final int capacity;

  public SpaceSavingEstimate(
      String key, long estimate, long error, boolean monitored, long totalEvents, int capacity) {
    this.key = key;
    this.estimate = estimate;
    this.error = error;
    this.monitored = monitored;
    this.totalEvents = totalEvents;
    this.capacity = capacity;
  }

  public String key() {
    return key;
  }

  public long estimate() {
    return estimate;
  }

  public long error() {
    return error;
  }

  public boolean monitored() {
    return monitored;
  }

  public long totalEvents() {
    return totalEvents;
  }

  public int capacity() {
    return capacity;
  }

  public long lowerBound() {
    if (!monitored) {
      return 0L;
    }
    return Math.max(0L, estimate - error);
  }
}
