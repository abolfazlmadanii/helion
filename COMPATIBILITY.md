# Flink compatibility

Helion’s Flink integration (`helion-flink`) is built and tested against **Apache Flink 2.2.1** (Java 17).

| Component | Version |
|-----------|---------|
| Apache Flink (`flink-streaming-java`, `flink-clients`) | 2.2.1 |
| `flink-connector-kafka` | 5.0.0-2.2 |

## Flink 2.3.0

Flink **2.3.0** is exercised in CI on a best-effort basis (`continue-on-error`). The Kafka connector artifact published for Flink 2.2 (`5.0.0-2.2`) is reused when overriding the Flink version to 2.3.0 until a dedicated 2.3 connector release is available on Maven Central.

## Out of scope (roadmap)

Event-time and watermark-driven pane advancement are planned separately; current jobs keep processing-time behavior unchanged (`WatermarkStrategy.noWatermarks()`).
