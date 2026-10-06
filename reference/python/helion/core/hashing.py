from __future__ import annotations

import hashlib
import secrets
from typing import Hashable

# Mersenne prime used by Carter–Wegman 2-universal hashing over Z_p.
P61 = (1 << 61) - 1


def key_to_uint(key: Hashable) -> int:
    """Map an arbitrary hashable key to {1, …, P61-1}.

    blake2b is used only as a domain mixer. The Count-Min independence
    guarantee is provided by the subsequent Carter–Wegman family, not by
    treating blake2b as pairwise independent by itself.
    """
    payload = repr(key).encode("utf-8")
    digest = hashlib.blake2b(payload, digest_size=8).digest()
    value = int.from_bytes(digest, "little") % (P61 - 1)
    return value + 1


def draw_cw_pair() -> tuple[int, int]:
    """Draw (a, b) for h(x) = ((a x + b) mod p) mod w with a ≠ 0."""
    a = secrets.randbelow(P61 - 1) + 1
    b = secrets.randbelow(P61)
    return a, b


def carter_wegman(x: int, a: int, b: int, width: int) -> int:
    return ((a * x + b) % P61) % width
