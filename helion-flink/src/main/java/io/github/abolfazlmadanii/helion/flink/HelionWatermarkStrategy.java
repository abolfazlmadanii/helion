package io.github.abolfazlmadanii.helion.flink;

import io.github.abolfazlmadanii.helion.core.HelionEvent;
import java.time.Duration;
import org.apache.flink.api.common.eventtime.WatermarkStrategy;

/** Event-time watermarks for {@link HelionEvent} streams. */
public final class HelionWatermarkStrategy {

  public static final long DEFAULT_MAX_OUT_OF_ORDER_MS = 5_000L;

  private HelionWatermarkStrategy() {}

  public static WatermarkStrategy<HelionEvent> forEvents(long maxOutOfOrderMillis) {
    if (maxOutOfOrderMillis < 0L) {
      throw new IllegalArgumentException("maxOutOfOrderMillis must be non-negative");
    }
    return WatermarkStrategy.<HelionEvent>forBoundedOutOfOrderness(
            Duration.ofMillis(maxOutOfOrderMillis))
        .withTimestampAssigner((event, previousTimestamp) -> event.eventTimeMillis());
  }
}
