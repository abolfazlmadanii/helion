from __future__ import annotations

import functools
from typing import TYPE_CHECKING

from quixstreams import Application

from helion_quix.config import HelionQuixConfig
from helion_quix.processor import apply_helion

if TYPE_CHECKING:
    from quixstreams.dataframe import StreamingDataFrame


def build_application(
    broker_address: str,
    *,
    consumer_group: str = "helion",
    cfg: HelionQuixConfig | None = None,
) -> tuple[Application, StreamingDataFrame]:
    """
    Create a Quix Streams application with a stateful Helion pipeline.

    Message keys partition :class:`~helion.codec.runtime_codec.HelionRuntimeCodec`
    state; values are JSON objects with ``key``, ``weight``, and ``event_time_millis``.
    """
    cfg = cfg or HelionQuixConfig()
    app = Application(broker_address=broker_address, consumer_group=consumer_group)
    topic = app.topic(cfg.topic_name, value_deserializer="json")
    sdf = app.dataframe(topic)
    step = functools.partial(apply_helion, cfg=cfg)
    sdf = sdf.apply(step, stateful=True)
    return app, sdf
