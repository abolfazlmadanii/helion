package io.github.abolfazlmadanii.helion.core.component;

import io.github.abolfazlmadanii.helion.core.HelionEvent;
import java.io.Serializable;
import java.util.Map;

/**
 * Pluggable stream operator. Flink and Kafka Streams wrap the same
 * components; new sketches attach here without editing Count-Min or
 * Space-Saving.
 */
public interface Component extends Serializable {

  String name();

  void onEvent(HelionEvent event);

  default Map<String, Object> snapshot() {
    return Map.of("name", name());
  }
}
