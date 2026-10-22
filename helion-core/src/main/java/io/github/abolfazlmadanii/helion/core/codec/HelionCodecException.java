package io.github.abolfazlmadanii.helion.core.codec;

/** Thrown when a Helion state blob cannot be decoded. */
public final class HelionCodecException extends RuntimeException {

  public HelionCodecException(String message) {
    super(message);
  }

  public HelionCodecException(String message, Throwable cause) {
    super(message, cause);
  }
}
