package io.helion.flink;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import io.helion.core.HelionEvent;
import io.helion.core.runtime.HelionRuntime;
import org.junit.jupiter.api.Test;

class HelionProcessFunctionCheckpointTest {

  @Test
  void runtimeSurvivesJavaSerializationUsedByFlinkCheckpoints() {
    HelionRuntime original =
        io.helion.core.HelionFactory.production(0.2, 0.1, 0.4, 0.2, 3_000L, 1_000L, java.util.List.of());
    original.ingest(HelionEvent.of("hot", 1, 100));
    original.ingest(HelionEvent.of("hot", 1, 1_100));
    byte[] blob = HelionProcessFunction.serialize(original);
    HelionRuntime restored = HelionProcessFunction.deserialize(blob);
    assertEquals(2, restored.totalWeight());
    assertTrue(restored.registry().contains("count_min"));
    assertTrue(restored.registry().contains("space_saving"));
    assertTrue(restored.registry().contains("phi_hot_keys"));
    assertTrue(restored.registry().contains("count_min.window"));
  }
}
