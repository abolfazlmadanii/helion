package io.github.abolfazlmadanii.helion.flink;

import static org.junit.jupiter.api.Assertions.assertEquals;

import io.github.abolfazlmadanii.helion.core.HelionEvent;
import java.util.ArrayList;
import java.util.List;
import org.apache.flink.streaming.api.operators.ProcessOperator;
import org.apache.flink.streaming.api.watermark.Watermark;
import org.apache.flink.streaming.runtime.streamrecord.StreamRecord;
import org.apache.flink.streaming.util.OneInputStreamOperatorTestHarness;
import org.junit.jupiter.api.Test;

class HelionLateRecordTest {

  @Test
  void lateEventsRouteToSideOutput() throws Exception {
    HelionProcessFunction function = new HelionProcessFunction(0.01, 0.0001, 0.01, 0.001);
    OneInputStreamOperatorTestHarness<HelionEvent, ?> harness =
        new OneInputStreamOperatorTestHarness<>(new ProcessOperator<>(function));
    harness.open();

    harness.processElement(new StreamRecord<>(HelionEvent.of("on-time", 1, 10_000L), 10_000L));
    harness.processWatermark(new Watermark(20_000L));
    harness.processElement(new StreamRecord<>(HelionEvent.of("late", 1, 5_000L), 5_000L));

    List<HelionEvent> late = new ArrayList<>();
    for (StreamRecord<HelionEvent> record : harness.getSideOutput(HelionProcessFunction.LATE_RECORDS_TAG)) {
      late.add(record.getValue());
    }
    assertEquals(1, late.size());
    assertEquals("late", late.get(0).key());
    harness.close();
  }
}
