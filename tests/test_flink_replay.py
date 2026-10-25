from __future__ import annotations

import random
import shutil

import pytest

from helion.core.events import StreamEvent
from helion_flink.job import HelionJobConfig, run_bounded_job
from helion_flink.reference import reference_output

pytestmark = pytest.mark.skipif(
    shutil.which("java") is None,
    reason="PyFlink requires a JDK on PATH",
)


def _seeded_events(seed: int, count: int) -> list[StreamEvent]:
    rng = random.Random(seed)
    events: list[StreamEvent] = []
    for i in range(count):
        key = f"k{rng.randint(0, 11)}"
        weight = 1 + rng.randint(0, 2)
        time = 1_000 + i * 100
        events.append(StreamEvent(key=key, weight=weight, event_time_millis=time))
    return events


@pytest.mark.parametrize("parallelism", [1, 2])
def test_bounded_job_matches_reference(parallelism: int) -> None:
    cfg = HelionJobConfig()
    events = _seeded_events(7, 60)
    expected = reference_output(
        events, cfg.cms_epsilon, cfg.cms_delta, cfg.phi, cfg.ss_epsilon
    )
    actual = run_bounded_job(events, parallelism, cfg)
    assert actual == expected
