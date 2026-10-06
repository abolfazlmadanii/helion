package io.helion.core;

import io.helion.core.component.Component;
import io.helion.core.runtime.HelionRuntime;
import io.helion.core.sketch.CountMinSketch;
import io.helion.core.sketch.PhiHotKeyDetector;
import io.helion.core.sketch.SpaceSaving;
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
}
