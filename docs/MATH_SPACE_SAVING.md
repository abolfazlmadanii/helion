# Space-Saving

Source: Metwally, Agrawal, Abbadi, *Efficient Computation of Frequent and Top-k Elements in Data Streams*, ICDT 2005 / ACM TODS.

## Structure

At most $m$ counters. Each counter stores a monitored key $x$, a value $\hat{f}(x)$, and an inherited error bound $\varepsilon_x$. Helion’s Java implementation indexes counters by count (`TreeMap`); the Python reference uses a Stream-Summary (doubly linked count buckets) so a replacement is $O(1)$ per unit weight.

## Algorithm

For a key $x$ of weight $1$ (weight $w$ repeats this step $w$ times):

1. If $x$ is monitored, increment its counter by one.
2. If $x$ is not monitored and a slot is free, insert it with count $1$ and $\varepsilon_x = 0$.
3. If the table is full, evict a key whose counter equals the current minimum $c_{\min}$. Insert the new key with value $c_{\min}+1$ and $\varepsilon_x = c_{\min}$.

## Invariants and theorems

Let $N$ be the total weight seen so far and $\hat{f}$ the current counter values.

**Sum invariant.** At every time

$$
\sum_{\text{monitored } x} \hat{f}(x) = N.
$$

Every update adds exactly one to the sum of counters (increment, insert, or replace $c_{\min}$ by $c_{\min}+1$).

**Minimum bound.** From the sum invariant,

$$
c_{\min} = \min_x \hat{f}(x) \le \frac{N}{m}.
$$

**Controlled overestimate.** For every monitored key $x$

$$
f(x) \le \hat{f}(x) \le f(x) + \varepsilon_x \le f(x) + \frac{N}{m}.
$$

Left: a counter is never below the true frequency, because increments are real or inherited from $c_{\min}$, which upper-bounds the frequency of any unmonitored key. Right: the inherited error $\varepsilon_x$ equals $c_{\min}$ at insertion time, and $c_{\min} \le N/m$ at all times.

**Completeness of heavy keys.** If $f(x) > N/m$, then $x$ is monitored. Otherwise its frequency would be at most $c_{\min} \le N/m$, a contradiction.

For an unmonitored key:

$$
f(x) \le c_{\min} \le \frac{N}{m}.
$$

The algorithm is **deterministic**; there is no $\delta$.

## Hot keys

Call a key hot if $f(x) > \varphi N$. Choose $\varepsilon < \varphi$ and $m = \lceil 1/\varepsilon \rceil$. Then $N/m \le \varepsilon N < \varphi N$, so every key with $f(x) > \varphi N$ also satisfies $f(x) > N/m$ and **cannot be a false negative**.

Keys near the threshold may still be reported as hot because of overestimate. Example: $\varphi = 0.01$, $\varepsilon = 0.001$ uses about $1000$ counters, independent of cardinality.

`PhiHotKeyDetector` applies this parameterization.

## Windows

The bounds above are for an unwindowed stream. “Hot in the last 5 minutes” needs a separate tumbling/sliding/decay component in front of Space-Saving. Do not fork the sketch class for that.
