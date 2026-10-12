package io.helion.core.sketch;

import io.helion.core.component.Component;

/**
 * Sketch that forms a semigroup under merge. Sliding windows keep one instance
 * per pane and merge on read; expired panes are dropped rather than subtracted.
 */
public interface MergeableSketch extends Component {

  MergeableSketch emptyCopy();

  void update(String key, long weight);

  void mergeFrom(MergeableSketch other);

  long estimate(String key);

  long total();
}
