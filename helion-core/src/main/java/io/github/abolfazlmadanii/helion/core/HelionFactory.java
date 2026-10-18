package io.github.abolfazlmadanii.helion.core;

import io.github.abolfazlmadanii.helion.core.component.Component;
import io.github.abolfazlmadanii.helion.core.runtime.HelionRuntime;
import io.github.abolfazlmadanii.helion.core.sketch.CountMinSketch;
import io.github.abolfazlmadanii.helion.core.sketch.PhiHotKeyDetector;
import io.github.abolfazlmadanii.helion.core.sketch.SpaceSaving;
import io.github.abolfazlmadanii.helion.core.window.PaneWindow;
import java.util.ArrayList;
import java.util.List;

/** Default production bundle: CMS + Space-Saving + φ detector. Extra components append. */
public final class HelionFactory {

  private HelionFactory() {}

  public static HelionRuntime production(double cmsEpsilon, double cmsDelta, double phi, double ssEpsilon) {
    return production(cmsEpsilon, cmsDelta, phi, ssEpsilon, List.of());
  }

  public static HelionRuntime production(
      double cmsEpsilon,
      double cmsDelta,
      double phi,
      double ssEpsilon,
      List<Component> extras) {
    List<Component> all = new ArrayList<>();
    all.add(new CountMinSketch(cmsEpsilon, cmsDelta));
    all.add(new SpaceSaving((int) Math.ceil(1.0d / ssEpsilon)));
    all.add(new PhiHotKeyDetector(phi, ssEpsilon));
    all.addAll(extras);
    return new HelionRuntime(all);
  }

  /**
   * Production bundle plus a pane-aligned Count-Min over {@code windowMillis}.
   * Space-Saving and φ remain global (not windowed): their published merge is
   * not the theorem used in Helion.
   */
  public static HelionRuntime production(
      double cmsEpsilon,
      double cmsDelta,
      double phi,
      double ssEpsilon,
      long windowMillis,
      long paneMillis,
      List<Component> extras) {
    List<Component> all = new ArrayList<>();
    if (extras != null) {
      all.addAll(extras);
    }
    all.add(paneCountMin(cmsEpsilon, cmsDelta, windowMillis, paneMillis));
    return production(cmsEpsilon, cmsDelta, phi, ssEpsilon, all);
  }

  public static PaneWindow paneCountMin(
      double cmsEpsilon, double cmsDelta, long windowMillis, long paneMillis) {
    CountMinSketch proto = new CountMinSketch("count_min.window.prototype", cmsEpsilon, cmsDelta);
    return new PaneWindow("count_min.window", proto, windowMillis, paneMillis);
  }
}
