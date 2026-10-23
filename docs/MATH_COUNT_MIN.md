# Count-Min Sketch

Source: Cormode, Muthukrishnan, *An Improved Data Stream Summary: The Count-Min Sketch and its Applications*, Journal of Algorithms, 2005.

## Stream model

Consider a cash-register stream $\sigma = (x_1, w_1), (x_2, w_2), \ldots$ where each $x$ is a key and each $w$ is a positive integer weight. Write

$$
N = \sum_t w_t, \qquad f(x) = \sum_{t: x_t = x} w_t.
$$

The goal is to estimate $f(x)$ with memory independent of the number of distinct keys.

## Structure

A counter matrix $C$ has $d$ rows and $w$ columns, all initially zero. For each row $i \in \{1,\ldots,d\}$ an independent hash

$$
h_i : \mathcal{U} \to \{0,\ldots,w-1\}
$$

is drawn from a 2-universal family (Carter–Wegman over $p = 2^{61}-1$ in Helion).

**Update.** For an event $(x, w)$:

$$
C[i, h_i(x)] \leftarrow C[i, h_i(x)] + w \qquad \text{for all } i.
$$

**Estimate.**

$$
\hat{f}(x) = \min_{1 \le i \le d} C[i, h_i(x)].
$$

## Theorem

If

$$
w = \left\lceil \frac{e}{\varepsilon} \right\rceil, \qquad d = \left\lceil \ln\frac{1}{\delta} \right\rceil,
$$

then for every fixed key $x$, with probability at least $1-\delta$ over the hash draws:

$$
f(x) \le \hat{f}(x) \le f(x) + \varepsilon N.
$$

The left inequality is **deterministic**: every update of $x$ increments every cell $h_i(x)$, so an estimate cannot fall below the true frequency. Error is one-sided (overestimate only).

## Proof

For a fixed row $i$ define

$$
X_i = C[i, h_i(x)] - f(x) = \sum_{y \ne x} f(y) \cdot \mathbf{1}[h_i(y)=h_i(x)].
$$

2-universality gives $P(h_i(y)=h_i(x)) \le 1/w$, so

$$
\mathbb{E}[X_i] \le \frac{N - f(x)}{w} \le \frac{N}{w}.
$$

With $w = \lceil e/\varepsilon \rceil$ we have $\mathbb{E}[X_i] \le \varepsilon N / e$. Markov’s inequality:

$$
P(X_i \ge \varepsilon N) \le \frac{\mathbb{E}[X_i]}{\varepsilon N} \le \frac{1}{e}.
$$

Rows are independent, so

$$
P\left(\bigcap_{i=1}^d \{X_i \ge \varepsilon N\}\right) \le e^{-d} \le \delta
$$

when $d = \lceil \ln(1/\delta) \rceil$. The complement is the upper bound in the theorem.

## Hot-key limitation

Count-Min does not store keys. Top-K needs a candidate structure (heap) or a second algorithm such as Space-Saving. In Helion that is a separate `Component`, not a change inside CMS.

## Helion parameters

`CountMinSketch(epsilon, delta)` sets `width = ceil(e/ε)` and `depth = ceil(ln(1/δ))`. Counters are 64-bit unsigned integers (`array('Q')` in Python).
