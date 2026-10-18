package io.github.abolfazlmadanii.helion.kafkastreams;

import io.github.abolfazlmadanii.helion.core.runtime.HelionRuntime;
import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.ObjectInputStream;
import java.io.ObjectOutputStream;
import java.util.Map;
import org.apache.kafka.common.serialization.Deserializer;
import org.apache.kafka.common.serialization.Serde;
import org.apache.kafka.common.serialization.Serializer;

public final class HelionRuntimeSerde implements Serde<HelionRuntime> {

  @Override
  public Serializer<HelionRuntime> serializer() {
    return new Serializer<>() {
      @Override
      public void configure(Map<String, ?> configs, boolean isKey) {}

      @Override
      public byte[] serialize(String topic, HelionRuntime data) {
        if (data == null) {
          return null;
        }
        try (ByteArrayOutputStream bos = new ByteArrayOutputStream();
            ObjectOutputStream oos = new ObjectOutputStream(bos)) {
          oos.writeObject(data);
          oos.flush();
          return bos.toByteArray();
        } catch (Exception e) {
          throw new IllegalStateException("serialize HelionRuntime", e);
        }
      }
    };
  }

  @Override
  public Deserializer<HelionRuntime> deserializer() {
    return new Deserializer<>() {
      @Override
      public void configure(Map<String, ?> configs, boolean isKey) {}

      @Override
      public HelionRuntime deserialize(String topic, byte[] data) {
        if (data == null) {
          return null;
        }
        try (ObjectInputStream ois = new ObjectInputStream(new ByteArrayInputStream(data))) {
          return (HelionRuntime) ois.readObject();
        } catch (Exception e) {
          throw new IllegalStateException("deserialize HelionRuntime", e);
        }
      }
    };
  }
}
