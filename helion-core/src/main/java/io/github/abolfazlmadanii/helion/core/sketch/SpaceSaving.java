package io.github.abolfazlmadanii.helion.core.sketch;

import io.github.abolfazlmadanii.helion.core.HelionEvent;
import io.github.abolfazlmadanii.helion.core.component.Component;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;

/**
 * Space-Saving (Metwally, Agrawal, Abbadi 2005).
 *
 * <p>Deterministic invariants: counter sum = N; min ≤ N/m; for every monitored
 * key {@code f(x) ≤ f̂(x) ≤ f(x) + N/m}; every key with {@code f(x) > N/m} is
 * stored.
 */
public final class SpaceSaving implements Component {

  private static final long serialVersionUID = 1L;

  private final String name;
  private final int capacity;
  private final Map<String, Entry> items = new HashMap<>();
  private final TreeMap<Long, LinkedHashSet<String>> byCount = new TreeMap<>();
  private long total;

  public SpaceSaving(int capacity) {
    this("space_saving", capacity);
  }

  public SpaceSaving(String name, int capacity) {
    if (capacity < 1) {
      throw new IllegalArgumentException("capacity must be at least 1");
    }
    this.name = name;
    this.capacity = capacity;
  }

  @Override
  public String name() {
    return name;
  }

  public void update(String key, long weight) {
    if (weight < 1L) {
      throw new IllegalArgumentException("weight must be a positive integer");
    }
    for (long i = 0; i < weight; i++) {
      updateOne(key);
    }
  }

  private void updateOne(String key) {
    total++;
    Entry existing = items.get(key);
    if (existing != null) {
      bump(existing);
      return;
    }
    if (items.size() < capacity) {
      insert(key, 1L, 0L);
      return;
    }
    Map.Entry<Long, LinkedHashSet<String>> min = byCount.firstEntry();
    String victimKey = min.getValue().iterator().next();
    Entry victim = items.get(victimKey);
    long inherited = victim.count;
    remove(victim);
    insert(key, inherited + 1L, inherited);
  }

  public long estimate(String key) {
    Entry entry = items.get(key);
    if (entry != null) {
      return entry.count;
    }
    return minCount();
  }

  public boolean monitored(String key) {
    return items.containsKey(key);
  }

  public long minCount() {
    if (byCount.isEmpty()) {
      return 0L;
    }
    return byCount.firstKey();
  }

  public long counterSum() {
    long sum = 0L;
    for (Entry entry : items.values()) {
      sum += entry.count;
    }
    return sum;
  }

  public List<SpaceSavingEstimate> monitored() {
    List<SpaceSavingEstimate> rows = new ArrayList<>();
    for (Entry entry : items.values()) {
      rows.add(toEstimate(entry.key, true));
    }
    rows.sort(
        Comparator.comparingLong(SpaceSavingEstimate::estimate)
            .reversed()
            .thenComparing(SpaceSavingEstimate::key));
    return rows;
  }

  public List<SpaceSavingEstimate> heavyHitters(double phi) {
    if (phi <= 0.0d || phi >= 1.0d) {
      throw new IllegalArgumentException("phi must lie in (0, 1)");
    }
    double threshold = phi * total;
    List<SpaceSavingEstimate> hot = new ArrayList<>();
    for (SpaceSavingEstimate row : monitored()) {
      if (row.estimate() > threshold) {
        hot.add(row);
      }
    }
    return hot;
  }

  public SpaceSavingEstimate query(String key) {
    return toEstimate(key, items.containsKey(key));
  }

  public int capacity() {
    return capacity;
  }

  public long total() {
    return total;
  }

  @Override
  public void onEvent(HelionEvent event) {
    update(event.key(), event.weight());
  }

  @Override
  public Map<String, Object> snapshot() {
    Map<String, Object> snap = new LinkedHashMap<>();
    snap.put("name", name);
    snap.put("algorithm", "space_saving");
    snap.put("capacity", capacity);
    snap.put("monitored", items.size());
    snap.put("total", total);
    snap.put("minCount", minCount());
    snap.put("counterSum", counterSum());
    snap.put("guarantee", "f <= hat <= f + N/m for monitored keys; f > N/m => monitored");
    return snap;
  }

  private SpaceSavingEstimate toEstimate(String key, boolean isMonitored) {
    if (!isMonitored) {
      long cap = minCount();
      return new SpaceSavingEstimate(key, cap, cap, false, total, capacity);
    }
    Entry entry = items.get(key);
    return new SpaceSavingEstimate(key, entry.count, entry.error, true, total, capacity);
  }

  private void insert(String key, long count, long error) {
    Entry entry = new Entry(key, count, error);
    items.put(key, entry);
    byCount.computeIfAbsent(count, ignored -> new LinkedHashSet<>()).add(key);
  }

  private void bump(Entry entry) {
    LinkedHashSet<String> bucket = byCount.get(entry.count);
    bucket.remove(entry.key);
    if (bucket.isEmpty()) {
      byCount.remove(entry.count);
    }
    entry.count++;
    byCount.computeIfAbsent(entry.count, ignored -> new LinkedHashSet<>()).add(entry.key);
  }

  private void remove(Entry entry) {
    items.remove(entry.key);
    LinkedHashSet<String> bucket = byCount.get(entry.count);
    bucket.remove(entry.key);
    if (bucket.isEmpty()) {
      byCount.remove(entry.count);
    }
  }

  private static final class Entry implements java.io.Serializable {
    private static final long serialVersionUID = 1L;
    private final String key;
    private long count;
    private final long error;

    private Entry(String key, long count, long error) {
      this.key = key;
      this.count = count;
      this.error = error;
    }
  }
}
