package io.github.abolfazlmadanii.helion.flink;

import static org.junit.jupiter.api.Assertions.assertArrayEquals;

import io.github.abolfazlmadanii.helion.core.HelionEvent;
import io.github.abolfazlmadanii.helion.core.HotKeyAlert;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;
import java.util.Random;
import org.apache.flink.runtime.testutils.MiniClusterResourceConfiguration;
import org.apache.flink.streaming.api.datastream.DataStream;
import org.apache.flink.streaming.api.environment.StreamExecutionEnvironment;
import org.apache.flink.test.util.MiniClusterWithClientResource;
import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;

class HelionReplayTest {

  private static final MiniClusterWithClientResource MINI_CLUSTER =
      new MiniClusterWithClientResource(
          new MiniClusterResourceConfiguration.Builder()
              .setNumberSlotsPerTaskManager(2)
              .setNumberTaskManagers(1)
              .build());

  @BeforeAll
  static void startMiniCluster() throws Exception {
    MINI_CLUSTER.before();
  }

  @AfterAll
  static void stopMiniCluster() {
    MINI_CLUSTER.after();
  }

  @Test
  void seededInputProducesByteIdenticalOutputAcrossRuns() throws Exception {
    List<String> lines = seededCsvLines(42L, 80);
    byte[] first = runOnMiniCluster(lines);
    byte[] second = runOnMiniCluster(lines);
    assertArrayEquals(first, second);
  }

  private static List<String> seededCsvLines(long seed, int count) {
    Random random = new Random(seed);
    List<String> lines = new ArrayList<>(count);
    for (int i = 0; i < count; i++) {
      String key = "k" + (random.nextInt(12));
      long weight = 1L + random.nextInt(3);
      long time = 1_000L + i * 100L;
      lines.add(key + "," + weight + "," + time);
    }
    return lines;
  }

  private static byte[] runOnMiniCluster(List<String> lines) throws Exception {
    StreamExecutionEnvironment env = StreamExecutionEnvironment.getExecutionEnvironment();
    env.setParallelism(1);
    env.getConfig().setAutoWatermarkInterval(50L);

    DataStream<HelionEvent> events =
        env.fromCollection(lines)
            .map(HelionEvent::parseLineRequired)
            .assignTimestampsAndWatermarks(
                HelionWatermarkStrategy.forEvents(HelionWatermarkStrategy.DEFAULT_MAX_OUT_OF_ORDER_MS));

    DataStream<HotKeyAlert> alerts =
        events.process(new HelionProcessFunction(0.05, 0.01, 0.2, 0.05)).name("helion");

    List<HotKeyAlert> collected = alerts.executeAndCollect(10_000);
    StringBuilder text = new StringBuilder();
    for (HotKeyAlert alert : collected) {
      text.append(alert.toCsv()).append('\n');
    }
    return text.toString().getBytes(StandardCharsets.UTF_8);
  }
}
