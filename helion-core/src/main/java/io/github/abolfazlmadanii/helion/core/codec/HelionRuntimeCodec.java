package io.github.abolfazlmadanii.helion.core.codec;

import io.github.abolfazlmadanii.helion.core.component.Component;
import io.github.abolfazlmadanii.helion.core.runtime.HelionRuntime;
import io.github.abolfazlmadanii.helion.core.sketch.CountMinSketch;
import io.github.abolfazlmadanii.helion.core.sketch.PhiHotKeyDetector;
import io.github.abolfazlmadanii.helion.core.sketch.SpaceSaving;
import io.github.abolfazlmadanii.helion.core.window.PaneWindow;
import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.DataInputStream;
import java.io.DataOutputStream;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;

/** Versioned binary codec for {@link HelionRuntime} operator state (Flink checkpoints). */
public final class HelionRuntimeCodec {

  public static final int CURRENT_VERSION = 1;

  private static final byte[] MAGIC = "HLRN".getBytes(StandardCharsets.US_ASCII);

  private static final byte KIND_COUNT_MIN = 1;
  private static final byte KIND_SPACE_SAVING = 2;
  private static final byte KIND_PHI_HOT_KEYS = 3;
  private static final byte KIND_PANE_WINDOW = 4;

  private HelionRuntimeCodec() {}

  public static byte[] encode(HelionRuntime runtime) {
    try (ByteArrayOutputStream bos = new ByteArrayOutputStream();
        DataOutputStream out = new DataOutputStream(bos)) {
      out.write(MAGIC);
      out.writeInt(CURRENT_VERSION);
      out.writeLong(runtime.totalWeight());
      List<Component> components = runtime.registry().asList();
      out.writeInt(components.size());
      for (Component component : components) {
        writeComponent(out, component);
      }
      out.flush();
      return bos.toByteArray();
    } catch (IOException e) {
      throw new HelionCodecException("encode HelionRuntime", e);
    }
  }

  public static HelionRuntime decode(byte[] blob) {
    try (DataInputStream in = new DataInputStream(new ByteArrayInputStream(blob))) {
      byte[] magic = new byte[MAGIC.length];
      in.readFully(magic);
      if (!java.util.Arrays.equals(magic, MAGIC)) {
        throw new HelionCodecException("invalid Helion state magic");
      }
      int version = in.readInt();
      if (version != CURRENT_VERSION) {
        throw new HelionCodecException("unsupported Helion state version: " + version);
      }
      long totalWeight = in.readLong();
      int count = in.readInt();
      if (count < 0) {
        throw new HelionCodecException("negative component count");
      }
      List<Component> components = new ArrayList<>(count);
      for (int i = 0; i < count; i++) {
        components.add(readComponent(in));
      }
      return HelionRuntime.rehydrate(totalWeight, components);
    } catch (IOException e) {
      throw new HelionCodecException("decode HelionRuntime", e);
    }
  }

  private static void writeComponent(DataOutputStream out, Component component) throws IOException {
    if (component instanceof CountMinSketch cms) {
      out.writeByte(KIND_COUNT_MIN);
      cms.encodeState(out);
      return;
    }
    if (component instanceof SpaceSaving ss) {
      out.writeByte(KIND_SPACE_SAVING);
      ss.encodeState(out);
      return;
    }
    if (component instanceof PhiHotKeyDetector phi) {
      out.writeByte(KIND_PHI_HOT_KEYS);
      phi.encodeState(out);
      return;
    }
    if (component instanceof PaneWindow pane) {
      out.writeByte(KIND_PANE_WINDOW);
      pane.encodeState(out);
      return;
    }
    throw new HelionCodecException("unsupported component type: " + component.getClass().getName());
  }

  private static Component readComponent(DataInputStream in) throws IOException {
    byte kind = in.readByte();
    return switch (kind) {
      case KIND_COUNT_MIN -> CountMinSketch.decodeState(in);
      case KIND_SPACE_SAVING -> SpaceSaving.decodeState(in);
      case KIND_PHI_HOT_KEYS -> PhiHotKeyDetector.decodeState(in);
      case KIND_PANE_WINDOW -> PaneWindow.decodeState(in);
      default -> throw new HelionCodecException("unknown component kind: " + kind);
    };
  }
}
