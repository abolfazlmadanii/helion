package io.github.abolfazlmadanii.helion.core.codec;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

import io.github.abolfazlmadanii.helion.core.HelionEvent;
import io.github.abolfazlmadanii.helion.core.HelionFactory;
import io.github.abolfazlmadanii.helion.core.runtime.HelionRuntime;
import io.github.abolfazlmadanii.helion.core.sketch.CountMinSketch;
import java.util.List;
import org.junit.jupiter.api.Test;

class HelionRuntimeCodecTest {

  @Test
  void roundTripProductionRuntime() {
    HelionRuntime original =
        HelionFactory.production(0.2, 0.1, 0.4, 0.2, 3_000L, 1_000L, List.of());
    original.ingest(HelionEvent.of("hot", 1, 100));
    original.ingest(HelionEvent.of("hot", 1, 1_100));
    byte[] blob = HelionRuntimeCodec.encode(original);
    HelionRuntime restored = HelionRuntimeCodec.decode(blob);
    assertEquals(original.totalWeight(), restored.totalWeight());
    CountMinSketch cms = (CountMinSketch) restored.registry().get("count_min");
    assertEquals(2L, cms.estimate("hot"));
  }

  @Test
  void rejectsUnknownVersion() {
    HelionRuntime runtime = HelionFactory.production(0.2, 0.1, 0.4, 0.2, List.of());
    byte[] blob = HelionRuntimeCodec.encode(runtime);
    blob[7] = (byte) 99;
    assertThrows(HelionCodecException.class, () -> HelionRuntimeCodec.decode(blob));
  }
}
