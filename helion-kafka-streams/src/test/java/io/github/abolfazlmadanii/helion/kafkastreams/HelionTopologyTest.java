package io.github.abolfazlmadanii.helion.kafkastreams;

import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.Properties;
import org.apache.kafka.common.serialization.Serdes;
import org.apache.kafka.streams.StreamsConfig;
import org.apache.kafka.streams.TestInputTopic;
import org.apache.kafka.streams.TestOutputTopic;
import org.apache.kafka.streams.TopologyTestDriver;
import org.junit.jupiter.api.Test;

class HelionTopologyTest {

  @Test
  void emitsHotKeyWhenFrequencyExceedsPhi() {
    Properties props = new Properties();
    props.put(StreamsConfig.APPLICATION_ID_CONFIG, "helion-test");
    props.put(StreamsConfig.BOOTSTRAP_SERVERS_CONFIG, "dummy:9092");
    props.put(StreamsConfig.STATE_DIR_CONFIG, "target/kafka-streams-test");

    try (TopologyTestDriver driver =
        new TopologyTestDriver(
            HelionTopology.hotKeys("in", "out", 0.2, 0.1, 0.4, 0.2), props)) {
      TestInputTopic<String, String> in =
          driver.createInputTopic("in", Serdes.String().serializer(), Serdes.String().serializer());
      TestOutputTopic<String, String> out =
          driver.createOutputTopic(
              "out", Serdes.String().deserializer(), Serdes.String().deserializer());
      for (int i = 0; i < 10; i++) {
        in.pipeInput("hot", "hot");
      }
      in.pipeInput("cold", "cold");
      assertTrue(out.readValuesToList().stream().anyMatch(v -> v.startsWith("hot,")));
    }
  }
}
