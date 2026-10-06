from __future__ import annotations

from collections import Counter

from helion import CountMinSketch, HelionRuntime, SpaceSaving, StreamEvent
from helion.pipeline.hot_keys import PhiHotKeyDetector


def main() -> None:
    cms = CountMinSketch(epsilon=0.2, delta=0.1, name="cms")
    ss = SpaceSaving(capacity=3, name="ss")
    hot = PhiHotKeyDetector(phi=0.25, epsilon=0.2, name="hot")
    runtime = HelionRuntime([cms, ss, hot])

    keys = ["a", "b", "a", "c", "a", "d", "a", "b", "e", "a"]
    runtime.extend(StreamEvent(key=k) for k in keys)

    truth = Counter(keys)
    print("true frequencies:", dict(truth))
    print("CMS estimates:", {k: cms.estimate(k) for k in truth})
    print("Space-Saving monitored:", [(row.key, row.estimate, row.error) for row in ss.monitored()])
    print("hot keys (phi=0.25):", [row.key for row in hot.hot_keys()])
    print("snapshots:", runtime.snapshots())
    runtime.close()


if __name__ == "__main__":
    main()
