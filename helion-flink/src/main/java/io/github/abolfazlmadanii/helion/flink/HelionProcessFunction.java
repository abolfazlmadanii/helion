package io.github.abolfazlmadanii.helion.flink;

import io.github.abolfazlmadanii.helion.core.HelionEvent;
import io.github.abolfazlmadanii.helion.core.HelionFactory;
import io.github.abolfazlmadanii.helion.core.HotKeyAlert;
import io.github.abolfazlmadanii.helion.core.codec.HelionRuntimeCodec;
import io.github.abolfazlmadanii.helion.core.component.Component;
import io.github.abolfazlmadanii.helion.core.runtime.HelionRuntime;
import io.github.abolfazlmadanii.helion.core.sketch.PhiHotKeyDetector;
import io.github.abolfazlmadanii.helion.core.sketch.SpaceSavingEstimate;
import java.util.Collections;
import java.util.List;
import org.apache.flink.api.common.state.ListState;
import org.apache.flink.api.common.state.ListStateDescriptor;
import org.apache.flink.api.common.typeinfo.PrimitiveArrayTypeInfo;
import org.apache.flink.runtime.state.FunctionInitializationContext;
import org.apache.flink.runtime.state.FunctionSnapshotContext;
import org.apache.flink.streaming.api.checkpoint.CheckpointedFunction;
import org.apache.flink.streaming.api.functions.ProcessFunction;
import org.apache.flink.util.Collector;
import org.apache.flink.util.OutputTag;

/**
 * Global hot-key operator. Run at parallelism 1 so Space-Saving sees the full
 * stream. Operator union list state checkpoints the versioned runtime codec.
 */
public final class HelionProcessFunction extends ProcessFunction<HelionEvent, HotKeyAlert>
    implements CheckpointedFunction {

  private static final long serialVersionUID = 1L;

  public static final OutputTag<HelionEvent> LATE_RECORDS_TAG =
      new OutputTag<>("late-records") {};

  private final double cmsEpsilon;
  private final double cmsDelta;
  private final double phi;
  private final double ssEpsilon;
  private final List<Component> extras;

  private transient HelionRuntime runtime;
  private transient ListState<byte[]> checkpoint;

  public HelionProcessFunction(double cmsEpsilon, double cmsDelta, double phi, double ssEpsilon) {
    this(cmsEpsilon, cmsDelta, phi, ssEpsilon, List.of());
  }

  public HelionProcessFunction(
      double cmsEpsilon, double cmsDelta, double phi, double ssEpsilon, List<Component> extras) {
    this.cmsEpsilon = cmsEpsilon;
    this.cmsDelta = cmsDelta;
    this.phi = phi;
    this.ssEpsilon = ssEpsilon;
    this.extras = extras == null ? List.of() : List.copyOf(extras);
  }

  @Override
  public void initializeState(FunctionInitializationContext context) throws Exception {
    ListStateDescriptor<byte[]> descriptor =
        new ListStateDescriptor<>("helion-runtime", PrimitiveArrayTypeInfo.BYTE_PRIMITIVE_ARRAY_TYPE_INFO);
    checkpoint = context.getOperatorStateStore().getUnionListState(descriptor);
    runtime = HelionFactory.production(cmsEpsilon, cmsDelta, phi, ssEpsilon, extras);
    if (context.isRestored()) {
      for (byte[] blob : checkpoint.get()) {
        runtime = deserialize(blob);
        break;
      }
    }
  }

  @Override
  public void snapshotState(FunctionSnapshotContext context) throws Exception {
    checkpoint.update(Collections.singletonList(serialize(runtime)));
  }

  @Override
  public void processElement(HelionEvent event, Context ctx, Collector<HotKeyAlert> out) {
    long watermark = ctx.timerService().currentWatermark();
    if (watermark != Long.MIN_VALUE && event.eventTimeMillis() < watermark) {
      ctx.output(LATE_RECORDS_TAG, event);
      return;
    }
    runtime.ingest(event);
    PhiHotKeyDetector detector = (PhiHotKeyDetector) runtime.registry().get("phi_hot_keys");
    for (SpaceSavingEstimate row : detector.hotKeys()) {
      out.collect(new HotKeyAlert(row.key(), row.estimate(), row.error(), row.totalEvents(), phi));
    }
  }

  static byte[] serialize(HelionRuntime runtime) {
    return HelionRuntimeCodec.encode(runtime);
  }

  static HelionRuntime deserialize(byte[] blob) {
    return HelionRuntimeCodec.decode(blob);
  }
}
