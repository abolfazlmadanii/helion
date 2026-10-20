package io.github.abolfazlmadanii.helion.core.codec;

import java.io.DataInput;
import java.io.DataOutput;
import java.io.IOException;
import java.nio.charset.StandardCharsets;

public final class BinaryCodec {

  private BinaryCodec() {}

  public static void writeString(DataOutput out, String value) throws IOException {
    byte[] bytes = value.getBytes(StandardCharsets.UTF_8);
    out.writeInt(bytes.length);
    out.write(bytes);
  }

  public static String readString(DataInput in) throws IOException {
    int length = in.readInt();
    if (length < 0) {
      throw new HelionCodecException("negative string length: " + length);
    }
    byte[] bytes = new byte[length];
    in.readFully(bytes);
    return new String(bytes, StandardCharsets.UTF_8);
  }

  public static void writeLongArray(DataOutput out, long[] values) throws IOException {
    out.writeInt(values.length);
    for (long value : values) {
      out.writeLong(value);
    }
  }

  public static long[] readLongArray(DataInput in) throws IOException {
    int length = in.readInt();
    if (length < 0) {
      throw new HelionCodecException("negative array length: " + length);
    }
    long[] values = new long[length];
    for (int i = 0; i < length; i++) {
      values[i] = in.readLong();
    }
    return values;
  }

  public static void writeLongMatrix(DataOutput out, long[][] matrix) throws IOException {
    out.writeInt(matrix.length);
    for (long[] row : matrix) {
      writeLongArray(out, row);
    }
  }

  public static long[][] readLongMatrix(DataInput in) throws IOException {
    int rows = in.readInt();
    if (rows < 0) {
      throw new HelionCodecException("negative matrix rows: " + rows);
    }
    long[][] matrix = new long[rows][];
    for (int row = 0; row < rows; row++) {
      matrix[row] = readLongArray(in);
    }
    return matrix;
  }
}
