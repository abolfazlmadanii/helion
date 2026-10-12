# Pane-aligned sliding windows

Helion does not subtract from a sketch. Mergeable sketches (Count-Min today) are
kept per disjoint pane and merged on read. Expired panes are dropped.

## Stream and window

Let the cash-register stream be \((x_i, w_i, t_i)\) with \(w_i \ge 1\). Write
\(T\) for the maximum event time seen so far. A logical window of length \(W\)
would be \(\{i : T - W < t_i \le T\}\).

Sketches such as Count-Min, HyperLogLog, and t-digest are **mergeable** but not
generally **invertible**: from \(\mathrm{Sketch}(A \cup B)\) one cannot recover
\(\mathrm{Sketch}(A)\) by “subtracting” \(B\).

## Panes (Li et al., 2005)

Fix a pane width \(\Delta\) that divides \(W\), and set \(k = W / \Delta\). Pane
starts are \(\Delta \mathbb{Z}\). The open pane start is

\[
s_{\mathrm{open}} = \Delta \bigl\lfloor T / \Delta \bigr\rfloor.
\]

Helion retains every pane whose start \(s\) satisfies

\[
s_{\mathrm{open}} - (k-1)\Delta \le s \le s_{\mathrm{open}}.
\]

At most \(k\) sketches are stored. The covered interval is pane-aligned:

\[
\bigl(s_{\mathrm{open}} - (k-1)\Delta,\; T\bigr]
\quad\text{up to empty interior panes}.
\]

That interval has length between \(W - \Delta\) and \(W + \Delta\) relative to a
strict \((T-W, T]\) cut. Queries are therefore **pane-aligned**, not
millisecond-exact.

For pane \(P_j\), store \(S_j = \mathrm{Sketch}(P_j)\). The window sketch is

\[
S_W = \bigoplus_{P_j \subseteq W} S_j.
\]

When the oldest pane leaves the range, drop \(S_j\). Do not subtract it from
\(S_W\).

Closed panes are merged into a cache. A query merges that cache with the open
pane, so query time does not scan every pane on every read.

## Count-Min merge

If two Count-Min tables share width, depth, \(\varepsilon\), \(\delta\), and the
same Carter–Wegman coefficients \((a_r, b_r)\), cell-wise sum is the Count-Min of
the concatenated streams. The theorem of Cormode and Muthukrishnan then holds
with \(N\) equal to the **window** total weight, not the lifetime total:

\[
f_W(x) \le \hat f_W(x) \le f_W(x) + \varepsilon N_W
\quad\text{with probability at least } 1-\delta.
\]

Helion’s global `CountMinSketch` (lifetime) and `count_min.window` (pane union)
are separate components. Hash coefficients of window panes are copied from one
prototype so merge is valid.

## What is not in this layer

- **Space-Saving** is not pane-merged. The published bound is for one table over
  one stream; Helion does not treat merge as the theorem.
- **Exponential Histograms / DGIM** (Datar, Gionis, Indyk, Motwani 2002) are a
  different algorithm: geometrically sized buckets for approximate *counts* in
  \(O(\varepsilon^{-1} \log^2 N)\) bits. They are not a container for arbitrary
  sketches.
- **HLL / t-digest** fit the same pane API once implemented (`max` of registers
  for HLL; digest merge for t-digest). Subtract remains undefined.

## References

1. Mayur Datar, Aristides Gionis, Piotr Indyk, Rajeev Motwani, *Maintaining
   Stream Statistics over Sliding Windows*, SIAM Journal on Computing 31(6),
   1794–1813, 2002. Exponential histograms / DGIM for sliding-window counts.
2. Jin Li, David Maier, Kristin Tufte, Vassilis Papadimos, Peter A. Tucker,
   *No Pane, No Gain: Efficient Evaluation of Sliding-Window Aggregates over
   Data Streams*, SIGMOD Record 34(1), 39–44, 2005.
   DOI: [10.1145/1058150.1058158](https://doi.org/10.1145/1058150.1058158).
3. Graham Cormode, S. Muthukrishnan, *An Improved Data Stream Summary: The
   Count-Min Sketch and its Applications*, Journal of Algorithms 55(1), 58–75,
   2005.
4. Philippe Flajolet, Éric Fusy, Olivier Gandouet, Frédéric Meunier,
   *HyperLogLog: the analysis of a near-optimal cardinality estimation
   algorithm*, AOFA 2007. Merge by register-wise max; not subtractable.
5. Ted Dunning, *The t-digest: Efficient estimates of distributions*, Software
   Impacts 7, 2021. Mergeable quantile digests for short time windows.
6. Jonas Traub et al., *Efficient Window Aggregation with General Stream
   Slicing*, EDBT 2019; *Scotty: General and Efficient Open-source Window
   Aggregation*, TODS 2021.
7. Verwiebe, Grulich, Traub, Markl et al., *Survey of window types for
   aggregation in stream processing systems*, The VLDB Journal, 2023.

Flink and Spark already document window aggregation. Helion’s gap is a single
component that attaches an **arbitrary mergeable sketch** plus pane expiry, with
the Count-Min theorem stated on the window total.
