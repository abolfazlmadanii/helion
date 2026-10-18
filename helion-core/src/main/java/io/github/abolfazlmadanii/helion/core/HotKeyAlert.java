package io.github.abolfazlmadanii.helion.core;

import java.io.Serializable;
import java.util.Objects;

public final class HotKeyAlert implements Serializable {

  private static final long serialVersionUID = 1L;

  private final String key;
  private final long estimate;
  private final long error;
  private final long totalEvents;
  private final double phi;

  public HotKeyAlert(String key, long estimate, long error, long totalEvents, double phi) {
    this.key = key;
    this.estimate = estimate;
    this.error = error;
    this.totalEvents = totalEvents;
    this.phi = phi;
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

  public long totalEvents() {
    return totalEvents;
  }

  public double phi() {
    return phi;
  }

  public String toCsv() {
    return key + "," + estimate + "," + error + "," + totalEvents + "," + phi;
  }

  @Override
  public boolean equals(Object o) {
    if (this == o) {
      return true;
    }
    if (!(o instanceof HotKeyAlert that)) {
      return false;
    }
    return estimate == that.estimate
        && error == that.error
        && totalEvents == that.totalEvents
        && Double.compare(that.phi, phi) == 0
        && key.equals(that.key);
  }

  @Override
  public int hashCode() {
    return Objects.hash(key, estimate, error, totalEvents, phi);
  }
}
