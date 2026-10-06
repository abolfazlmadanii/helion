package io.helion.flink;

import io.helion.core.HelionEvent;
import io.helion.core.HotKeyAlert;
import org.apache.flink.api.common.eventtime.WatermarkStrategy;
import org.apache.flink.api.common.serialization.SimpleStringSchema;
import org.apache.flink.connector.kafka.sink.KafkaRecordSerializationSchema;
import org.apache.flink.connector.kafka.sink.KafkaSink;
import org.apache.flink.connector.kafka.source.KafkaSource;
import org.apache.flink.connector.kafka.source.enumerator.initializer.OffsetsInitializer;
import org.apache.flink.streaming.api.datastream.DataStream;
import org.apache.flink.streaming.api.environment.StreamExecutionEnvironment;

/**
 * Kafka → Helion (parallelism 1) → Kafka hot-key topic.
 *
 * <p>Input: {@code key} or {@code key,weight}. Extra Flink operators splice onto
 * {@code events} before {@code process}. Additional Helion components go into
 * {@link HelionProcessFunction} via its extras list.
 */
public final class HelionFlinkJob {

  public static void main(String[] args) throws Exception {
    String brokers = envOr("KAFKA_BOOTSTRAP", "localhost:9092");
    String inTopic = envOr("HELION_INPUT_TOPIC", "helion.events");
    String outTopic = envOr("HELION_OUTPUT_TOPIC", "helion.hot-keys");
    String group = envOr("HELION_GROUP", "helion-flink");
    double phi = Double.parseDouble(envOr("HELION_PHI", "0.01"));
    double epsilon = Double.parseDouble(envOr("HELION_EPSILON", "0.001"));
    double cmsEps = Double.parseDouble(envOr("HELION_CMS_EPSILON", "0.01"));
    double cmsDelta = Double.parseDouble(envOr("HELION_CMS_DELTA", "0.0001"));

    StreamExecutionEnvironment env = StreamExecutionEnvironment.getExecutionEnvironment();
    env.enableCheckpointing(10_000L);

    KafkaSource<String> source =
        KafkaSource.<String>builder()
            .setBootstrapServers(brokers)
            .setTopics(inTopic)
            .setGroupId(group)
            .setStartingOffsets(OffsetsInitializer.latest())
            .setValueOnlyDeserializer(new SimpleStringSchema())
            .build();

    DataStream<HelionEvent> events =
        env.fromSource(source, WatermarkStrategy.noWatermarks(), "kafka-events")
            .map(HelionFlinkJob::parse)
            .name("parse-events");

    DataStream<HotKeyAlert> hotKeys =
        events
            .process(new HelionProcessFunction(cmsEps, cmsDelta, phi, epsilon))
            .setParallelism(1)
            .name("helion");

    KafkaSink<String> sink =
        KafkaSink.<String>builder()
            .setBootstrapServers(brokers)
            .setRecordSerializer(
                KafkaRecordSerializationSchema.builder()
                    .setTopic(outTopic)
                    .setValueSerializationSchema(new SimpleStringSchema())
                    .build())
            .build();

    hotKeys.map(HotKeyAlert::toCsv).sinkTo(sink).name("hot-key-sink").setParallelism(1);
    env.execute("helion-flink");
  }

  static HelionEvent parse(String line) {
    String[] parts = line.trim().split(",", 2);
    if (parts.length == 1 || parts[1].isBlank()) {
      return HelionEvent.of(parts[0]);
    }
    return new HelionEvent(
        parts[0], Long.parseLong(parts[1].trim()), System.currentTimeMillis(), java.util.Map.of());
  }

  private static String envOr(String key, String fallback) {
    String value = System.getenv(key);
    return value == null || value.isBlank() ? fallback : value;
  }
}
