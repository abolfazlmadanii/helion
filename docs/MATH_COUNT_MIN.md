# Count-Min Sketch — ریاضی

منبع: Cormode, Muthukrishnan, *An Improved Data Stream Summary: The Count-Min Sketch and its Applications*, Journal of Algorithms, 2005.

## مدل جریان

جریان `σ = (x₁, w₁), …` را در نظر بگیرید که هر `x` یک کلید و هر `w` وزن صحیح مثبت است. بگذارید

\[
N = \sum_t w_t, \qquad f(x) = \sum_{t: x_t = x} w_t.
\]

هدف برآورد `f(x)` با حافظهٔ مستقل از تعداد کلیدهای متمایز است.

## ساختار

ماتریس شمارنده `C` با `d` سطر و `w` ستون، همه ابتدا صفر. برای هر سطر `i ∈ {1,…,d}` یک تابع مستقل

\[
h_i : \mathcal{U} \to \{0,\dots,w-1\}
\]

از خانوادهٔ ۲-universal (اینجا Carter–Wegman روی `p = 2^{61}-1`) کشیده می‌شود.

**به‌روزرسانی.** برای رویداد `(x, w)`:

\[
C[i, h_i(x)] \leftarrow C[i, h_i(x)] + w \qquad \text{برای همهٔ } i.
\]

**برآورد.**

\[
\hat f(x) = \min_{1 \le i \le d} C[i, h_i(x)].
\]

## قضیه

اگر

\[
w = \left\lceil \frac{e}{\varepsilon} \right\rceil, \qquad d = \left\lceil \ln\frac{1}{\delta} \right\rceil,
\]

آن‌گاه برای هر کلید ثابت `x`، با احتمال حداقل `1−δ` روی انتخاب hashها:

\[
f(x) \le \hat f(x) \le f(x) + \varepsilon N.
\]

نابرابری چپ **قطعی** است: هر بار که `x` می‌آید، همهٔ سلول‌های `h_i(x)` زیاد می‌شوند، پس هیچ برآوردی نمی‌تواند از فرکانس واقعی کمتر شود. خطا فقط بیش‌برآورد است.

## اثبات

برای سطر ثابت `i` تعریف کنید

\[
X_i = C[i, h_i(x)] - f(x) = \sum_{y \ne x} f(y) \cdot \mathbf{1}[h_i(y)=h_i(x)].
\]

چون خانواده ۲-universal است، `P(h_i(y)=h_i(x)) ≤ 1/w`. بنابراین

\[
\mathbb{E}[X_i] \le \frac{N - f(x)}{w} \le \frac{N}{w}.
\]

با انتخاب `w = ⌈e/ε⌉` داریم `E[X_i] ≤ εN/e`. نامساوی Markov:

\[
P(X_i \ge \varepsilon N) \le \frac{\mathbb{E}[X_i]}{\varepsilon N} \le \frac{1}{e}.
\]

سطرها مستقل‌اند، پس

\[
P\!\left(\bigcap_{i=1}^d \{X_i \ge \varepsilon N\}\right) \le e^{-d} \le \delta
\]

وقتی `d = ⌈ln(1/δ)⌉`. متمم این رویداد همان کران بالای قضیه است.

## محدودیت برای کلید داغ

CMS کلید را ذخیره نمی‌کند. برای Top-K باید ساختار کاندیدا (heap) یا الگوریتم دیگری مثل Space-Saving کنار آن ثبت شود. در Helion این کار با `Component` جدا انجام می‌شود، نه با تغییر خود CMS.

## پارامترهای پیاده‌سازی Helion

کلاس `CountMinSketch(epsilon, delta)` دقیقاً `width = ceil(e/ε)` و `depth = ceil(ln(1/δ))` را می‌سازد. شمارنده‌ها `uint64` هستند.
