package io.helion.core.hashing;

import java.math.BigInteger;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.security.SecureRandom;

/**
 * Carter–Wegman 2-universal hashing over the Mersenne prime p = 2^61 − 1.
 * blake2s is only a domain mixer from strings into Z_p; independence of
 * Count-Min rows comes from the affine family h(x) = ((a x + b) mod p) mod w.
 */
public final class CarterWegman {

  public static final long P61 = (1L << 61) - 1L;
  private static final BigInteger P = BigInteger.valueOf(P61);
  private static final SecureRandom RANDOM = new SecureRandom();

  private CarterWegman() {}

  public static long keyToField(String key) {
    try {
      MessageDigest digest = MessageDigest.getInstance("SHA-256");
      byte[] hash = digest.digest(key.getBytes(StandardCharsets.UTF_8));
      BigInteger n = new BigInteger(1, hash).mod(P.subtract(BigInteger.ONE)).add(BigInteger.ONE);
      return n.longValueExact();
    } catch (NoSuchAlgorithmException e) {
      throw new IllegalStateException(e);
    }
  }

  public static long[] drawPair() {
    long a = 1L + (Math.abs(RANDOM.nextLong()) % (P61 - 1L));
    long b = Math.abs(RANDOM.nextLong()) % P61;
    return new long[] {a, b};
  }

  public static int index(long x, long a, long b, int width) {
    BigInteger hashed =
        BigInteger.valueOf(a)
            .multiply(BigInteger.valueOf(x))
            .add(BigInteger.valueOf(b))
            .mod(P);
    return hashed.mod(BigInteger.valueOf(width)).intValueExact();
  }
}
