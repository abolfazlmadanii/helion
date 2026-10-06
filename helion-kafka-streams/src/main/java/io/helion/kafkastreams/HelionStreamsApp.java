package io.helion.kafkastreams;

import java.util.Properties;
import org.apache.kafka.clients.consumer.ConsumerConfig;
import org.apache.kafka.common.serialization.Serdes;
import org.apache.kafka.streams.KafkaStreams;
import org.apache.kafka.streams.StreamsConfig;
import org.apache.kafka.streams.Topology;

/**
 * Production Kafka Streams app. Set {@code NUM_STREAM_THREADS=1} and give the
 * input topic a single partition for global Space-Saving guarantees.
 */
public final class HelionStreamsApp {

  public static void main(String[] args) {
    String brokers = envOr("KAFKA_BOOTSTRAP", "localhost:9092");
    String input = envOr("HELION_INPUT_TOPIC", "helion.events");
    String output = envOr("HELION_OUTPUT_TOPIC", "helion.hot-keys");
    double phi = Double.parseDouble(envOr("HELION_PHI", "0.01"));
    double epsilon = Double.parseDouble(envOr("HELION_EPSILON", "0.001"));
    double cmsEps = Double.parseDouble(envOr("HELION_CMS_EPSILON", "0.01"));
    double cmsDelta = Double.parseDouble(envOr("HELION_CMS_DELTA", "0.0001"));

    Topology topology = HelionTopology.hotKeys(input, output, cmsEps, cmsDelta, phi, epsilon);

    Properties props = new Properties();
    props.put(StreamsConfig.APPLICATION_ID_CONFIG, envOr("HELION_APP_ID", "helion-streams"));
    props.put(StreamsConfig.BOOTSTRAP_SERVERS_CONFIG, brokers);
    props.put(StreamsConfig.DEFAULT_KEY_SERDE_CLASS_CONFIG, Serdes.String().getClass());
    props.put(StreamsConfig.DEFAULT_VALUE_SERDE_CLASS_CONFIG, Serdes.String().getClass());
    props.put(StreamsConfig.NUM_STREAM_THREADS_CONFIG, 1);
    props.put(ConsumerConfig.AUTO_OFFSET_RESET_CONFIG, "latest");
    props.put(StreamsConfig.PROCESSING_GUARANTEE_CONFIG, StreamsConfig.EXACTLY_ONCE_V2);

    KafkaStreams streams = new KafkaStreams(topology, props);
    Runtime.getRuntime().addShutdownHook(new Thread(streams::close));
    streams.start();
  }

  private static String envOr(String key, String fallback) {
    String value = System.getenv(key);
    return value == null || value.isBlank() ? fallback : value;
  }
}
