from __future__ import annotations

from dataclasses import dataclass

CMS_HASH_SEED = 42
RUNTIME_STATE_KEY = b"helion-runtime"
DEFAULT_TOPIC_NAME = "helion-events"


@dataclass(frozen=True, slots=True)
class HelionQuixConfig:
    cms_epsilon: float = 0.05
    cms_delta: float = 0.01
    phi: float = 0.2
    ss_epsilon: float = 0.05
    cms_hash_seed: int = CMS_HASH_SEED
    topic_name: str = DEFAULT_TOPIC_NAME
