package io.helion.kafkastreams;

import io.helion.core.HelionEvent;
import io.helion.core.HelionFactory;
import io.helion.core.HotKeyAlert;
import io.helion.core.component.Component;
import io.helion.core.runtime.HelionRuntime;
import io.helion.core.sketch.PhiHotKeyDetector;
import io.helion.core.sketch.SpaceSavingEstimate;
import java.util.List;
import org.apache.kafka.streams.processor.api.Processor;
import org.apache.kafka.streams.processor.api.ProcessorContext;
import org.apache.kafka.streams.processor.api.Record;
import org.apache.kafka.streams.state.KeyValueStore;

/**
 * Kafka Streams processor. Put the input topic at 1 partition (or insert a
 * 1-partition repartition topic) so Space-Saving sees the full stream. The
 * runtime is kept in a persistent key-value store under key {@code runtime}.
 */
public final class HelionProcessor implements Processor<String, String, String, String> {

  public static final String STORE_NAME = "helion-runtime-store";
  private static final String STATE_KEY = "runtime";

  private final double cmsEpsilon;
  private final double cmsDelta;
  private final double phi;
  private final double ssEpsilon;
  private final List<Component> extras;

  private ProcessorContext<String, String> context;
  private KeyValueStore<String, HelionRuntime> store;

  public HelionProcessor(double cmsEpsilon, double cmsDelta, double phi, double ssEpsilon) {
    this(cmsEpsilon, cmsDelta, phi, ssEpsilon, List.of());
  }

  public HelionProcessor(
      double cmsEpsilon, double cmsDelta, double phi, double ssEpsilon, List<Component> extras) {
    this.cmsEpsilon = cmsEpsilon;
    this.cmsDelta = cmsDelta;
    this.phi = phi;
    this.ssEpsilon = ssEpsilon;
    this.extras = extras == null ? List.of() : List.copyOf(extras);
  }

  @Override
  @SuppressWarnings("unchecked")
  public void init(ProcessorContext<String, String> context) {
    this.context = context;
    this.store = context.getStateStore(STORE_NAME);
  }

  @Override
  public void process(Record<String, String> record) {
    HelionRuntime runtime = store.get(STATE_KEY);
    if (runtime == null) {
      runtime = HelionFactory.production(cmsEpsilon, cmsDelta, phi, ssEpsilon, extras);
    }
    HelionEvent event = parse(record);
    runtime.ingest(event);
    store.put(STATE_KEY, runtime);

    PhiHotKeyDetector detector = (PhiHotKeyDetector) runtime.registry().get("phi_hot_keys");
    for (SpaceSavingEstimate row : detector.hotKeys()) {
      HotKeyAlert alert =
          new HotKeyAlert(row.key(), row.estimate(), row.error(), row.totalEvents(), phi);
      context.forward(record.withKey(row.key()).withValue(alert.toCsv()));
    }
  }

  private static HelionEvent parse(Record<String, String> record) {
    String key = record.key() != null ? record.key() : record.value();
    String value = record.value();
    if (value != null && value.contains(",")) {
      String[] parts = value.split(",", 2);
      key = parts[0];
      return new HelionEvent(key, Long.parseLong(parts[1].trim()), record.timestamp(), java.util.Map.of());
    }
    if (record.key() != null) {
      return new HelionEvent(record.key(), 1L, record.timestamp(), java.util.Map.of());
    }
    return HelionEvent.of(value);
  }
}
