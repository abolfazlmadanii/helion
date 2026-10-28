# Compatibility

Helion targets **Python 3.12**. Core sketch counters use the standard library `array` module (no NumPy required).

Optional **`flink`** extra pins `apache-flink==2.2.1` and `numpy>=1.26,<2.2` for PyFlink. **`helion_flink`** provides the bounded replay job on that stack.

Optional **`quix`** extra pins `quixstreams==3.28.1` for **`helion_quix`**.
