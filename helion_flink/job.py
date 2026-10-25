from __future__ import annotations

from dataclasses import dataclass

from pyflink.common import Row, Types, WatermarkStrategy
from pyflink.common.time import Duration
from pyflink.common.watermark_strategy import TimestampAssigner
from pyflink.datastream import StreamExecutionEnvironment
from pyflink.datastream.functions import (
    KeyedProcessFunction,
    ProcessFunction,
    ReduceFunction,
    RuntimeContext,
)
from pyflink.datastream.state import ValueStateDescriptor

from helion.codec.runtime_codec import HelionRuntimeCodec
from helion.core.events import StreamEvent
from helion.factory import HelionFactory
from helion.pipeline.hot_keys import PhiHotKeyDetector
from helion_flink.cms import cms_digest, ingest_into_cms_blob, merge_cms_blobs, shard_for_key
from helion_flink.config import CMS_HASH_SEED, DEFAULT_MAX_OUT_OF_ORDER_MS, LATE_RECORDS_TAG


@dataclass(frozen=True, slots=True)
class HelionJobConfig:
    cms_epsilon: float = 0.05
    cms_delta: float = 0.01
    phi: float = 0.2
    ss_epsilon: float = 0.05
    max_out_of_order_ms: int = DEFAULT_MAX_OUT_OF_ORDER_MS
    cms_hash_seed: int = CMS_HASH_SEED


class _EventTimestampAssigner(TimestampAssigner):
    def extract_timestamp(self, value: Row, record_timestamp: int) -> int:
        return int(value[2])


def _row_to_event(row: Row) -> StreamEvent:
    return StreamEvent(key=row[0], weight=int(row[1]), event_time_millis=int(row[2]))


def _event_to_row(event: StreamEvent) -> Row:
    return Row(event.key, event.weight, event.event_time_millis)


class _RouteLateProcess(ProcessFunction):
    def process_element(self, value: Row, ctx: ProcessFunction.Context):
        event_time = int(value[2])
        watermark = ctx.timer_service().current_watermark()
        channel = LATE_RECORDS_TAG
        if watermark == -(2**63) or event_time >= watermark:
            channel = "main"
        yield Row(channel, value[0], value[1], value[2])


def _main_rows(routed: Row) -> Row:
    return Row(routed[1], routed[2], routed[3])


class _GlobalHelionFunction(KeyedProcessFunction):
    def __init__(self, cfg: HelionJobConfig) -> None:
        self._cfg = cfg

    def open(self, runtime_context: RuntimeContext) -> None:
        descriptor = ValueStateDescriptor("helion-runtime", Types.PRIMITIVE_ARRAY(Types.BYTE()))
        self._runtime_state = runtime_context.get_state(descriptor)

    def process_element(self, value: Row, ctx: KeyedProcessFunction.Context):
        blob = self._runtime_state.value()
        runtime = (
            HelionRuntimeCodec.decode(blob)
            if blob
            else HelionFactory.production(
                self._cfg.cms_epsilon,
                self._cfg.cms_delta,
                self._cfg.phi,
                self._cfg.ss_epsilon,
                cms_hash_seed=self._cfg.cms_hash_seed,
            )
        )
        runtime.push(_row_to_event(value))
        self._runtime_state.update(HelionRuntimeCodec.encode(runtime))
        detector = runtime.registry.get("phi_hot_keys")
        if isinstance(detector, PhiHotKeyDetector):
            for row in detector.hot_keys():
                yield (
                    f"{row.key},{row.estimate},{row.error},{row.total_events},{self._cfg.phi}"
                )


class _CmsShardMap(ProcessFunction):
    def __init__(self, cfg: HelionJobConfig, parallelism: int) -> None:
        self._cfg = cfg
        self._parallelism = parallelism

    def process_element(self, value: Row, ctx: ProcessFunction.Context):
        event = _row_to_event(value)
        shard = shard_for_key(event.key, self._parallelism)
        partial = ingest_into_cms_blob(
            None,
            event,
            self._cfg.cms_epsilon,
            self._cfg.cms_delta,
            self._cfg.cms_hash_seed,
        )
        yield Row(shard, partial, event.event_time_millis)


class _CmsShardAccumulate(KeyedProcessFunction):
    def __init__(self, cfg: HelionJobConfig) -> None:
        self._cfg = cfg

    def open(self, runtime_context: RuntimeContext) -> None:
        bytes_type = Types.PRIMITIVE_ARRAY(Types.BYTE())
        self._blob = runtime_context.get_state(ValueStateDescriptor("cms-shard", bytes_type))
        max_et_desc = ValueStateDescriptor("cms-max-et", Types.LONG())
        self._max_event_time = runtime_context.get_state(max_et_desc)

    def process_element(self, value: Row, ctx: KeyedProcessFunction.Context):
        partial = value[1]
        event_time = int(value[2])
        current = self._blob.value()
        self._blob.update(
            merge_cms_blobs(current, partial) if current else partial
        )
        prev_max = self._max_event_time.value()
        if prev_max is None or event_time > prev_max:
            self._max_event_time.update(event_time)
            fire_at = event_time + self._cfg.max_out_of_order_ms + 1
            ctx.timer_service().register_event_time_timer(fire_at)

    def on_timer(self, timestamp: int, ctx: KeyedProcessFunction.OnTimerContext):
        max_et = self._max_event_time.value()
        if max_et is None:
            return
        deadline = max_et + self._cfg.max_out_of_order_ms + 1
        if timestamp < deadline:
            return
        blob = self._blob.value()
        if blob is not None:
            yield Row(int(ctx.get_current_key()), blob)
        self._blob.clear()
        self._max_event_time.clear()


class _CmsGlobalReduce(ReduceFunction):
    def reduce(self, left: Row, right: Row) -> Row:
        merged = merge_cms_blobs(left[1], right[1])
        return Row(0, merged)


def _on_time_stream(
    env: StreamExecutionEnvironment,
    events: list[StreamEvent],
    cfg: HelionJobConfig,
):
    row_type = Types.ROW([Types.STRING(), Types.LONG(), Types.LONG()])
    stream = env.from_collection([_event_to_row(e) for e in events], type_info=row_type)
    wm = (
        WatermarkStrategy.for_bounded_out_of_orderness(Duration.of_millis(cfg.max_out_of_order_ms))
        .with_timestamp_assigner(_EventTimestampAssigner())
    )
    timed = stream.assign_timestamps_and_watermarks(wm)
    routed_type = Types.ROW([Types.STRING(), Types.STRING(), Types.LONG(), Types.LONG()])
    return (
        timed.process(_RouteLateProcess(), output_type=routed_type)
        .filter(lambda row: row[0] == "main")
        .map(_main_rows, output_type=row_type)
    )


def _run_hot_keys(
    events: list[StreamEvent], parallelism: int, cfg: HelionJobConfig
) -> list[str]:
    del parallelism  # global runtime state requires in-order processing
    env = StreamExecutionEnvironment.get_execution_environment()
    env.set_parallelism(1)
    main = _on_time_stream(env, events, cfg)
    hot_lines = (
        main.key_by(lambda _: 0, key_type=Types.INT())
        .process(_GlobalHelionFunction(cfg), output_type=Types.STRING())
        .set_parallelism(1)
    )
    return list(hot_lines.execute_and_collect(limit=10_000))


def _run_merged_cms(
    events: list[StreamEvent],
    parallelism: int,
    cfg: HelionJobConfig,
) -> bytes | None:
    env = StreamExecutionEnvironment.get_execution_environment()
    env.set_parallelism(parallelism)
    main = _on_time_stream(env, events, cfg)
    bytes_type = Types.PRIMITIVE_ARRAY(Types.BYTE())
    shard_map_type = Types.ROW([Types.INT(), bytes_type, Types.LONG()])
    shard_final_type = Types.ROW([Types.INT(), bytes_type])
    merged = (
        main.process(_CmsShardMap(cfg, parallelism), output_type=shard_map_type)
        .key_by(lambda row: row[0], key_type=Types.INT())
        .process(_CmsShardAccumulate(cfg), output_type=shard_final_type)
        .key_by(lambda _: 0, key_type=Types.INT())
        .reduce(_CmsGlobalReduce())
        .map(lambda row: row[1], output_type=bytes_type)
        .set_parallelism(1)
    )
    collected = list(merged.execute_and_collect(limit=max(10_000, parallelism * parallelism + 1)))
    if not collected:
        return None
    return collected[-1]


def run_bounded_job(
    events: list[StreamEvent],
    parallelism: int,
    cfg: HelionJobConfig | None = None,
) -> bytes:
    cfg = cfg or HelionJobConfig()
    hot_collected = _run_hot_keys(events, parallelism, cfg)
    cms_blob = _run_merged_cms(events, parallelism, cfg)
    keys = sorted({e.key for e in events}, key=lambda k: repr(k))
    lines = list(hot_collected)
    if cms_blob is not None:
        lines.append("CMS:" + cms_digest(cms_blob, keys).rstrip("\n"))
    return ("\n".join(lines) + "\n").encode("utf-8")
