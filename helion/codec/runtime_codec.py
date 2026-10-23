from __future__ import annotations

import io
import struct
from typing import BinaryIO

from helion.codec.binary import CodecError
from helion.core.component import Component
from helion.pipeline.runtime import HelionRuntime
from helion.sketches.count_min import CountMinSketch
from helion.sketches.space_saving import SpaceSaving

MAGIC = b"HLRN"
CURRENT_VERSION = 1

KIND_COUNT_MIN = 1
KIND_SPACE_SAVING = 2
KIND_PHI_HOT_KEYS = 3
KIND_PANE_WINDOW = 4


class HelionRuntimeCodec:
    @staticmethod
    def encode(runtime: HelionRuntime) -> bytes:
        buf = io.BytesIO()
        buf.write(MAGIC)
        buf.write(struct.pack(">i", CURRENT_VERSION))
        buf.write(struct.pack(">q", runtime.total_weight))
        components = runtime.registry.as_list()
        buf.write(struct.pack(">i", len(components)))
        for component in components:
            _write_component(buf, component)
        return buf.getvalue()

    @staticmethod
    def decode(blob: bytes) -> HelionRuntime:
        inp = io.BytesIO(blob)
        magic = inp.read(len(MAGIC))
        if magic != MAGIC:
            raise CodecError("invalid Helion state magic")
        version = struct.unpack(">i", inp.read(4))[0]
        if version != CURRENT_VERSION:
            raise CodecError(f"unsupported Helion state version: {version}")
        total_weight = struct.unpack(">q", inp.read(8))[0]
        count = struct.unpack(">i", inp.read(4))[0]
        if count < 0:
            raise CodecError("negative component count")
        components = [_read_component(inp) for _ in range(count)]
        return HelionRuntime.rehydrate(total_weight, components)


def _write_component(out: BinaryIO, component: Component) -> None:
    from helion.pipeline.hot_keys import PhiHotKeyDetector
    from helion.window.pane_window import PaneWindow

    if isinstance(component, CountMinSketch):
        out.write(struct.pack(">b", KIND_COUNT_MIN))
        component.encode_state(out)
        return
    if isinstance(component, SpaceSaving):
        out.write(struct.pack(">b", KIND_SPACE_SAVING))
        component.encode_state(out)
        return
    if isinstance(component, PhiHotKeyDetector):
        out.write(struct.pack(">b", KIND_PHI_HOT_KEYS))
        component.encode_state(out)
        return
    if isinstance(component, PaneWindow):
        out.write(struct.pack(">b", KIND_PANE_WINDOW))
        component.encode_state(out)
        return
    raise CodecError(f"unsupported component type: {type(component).__name__}")


def _read_component(inp: BinaryIO) -> Component:
    from helion.pipeline.hot_keys import PhiHotKeyDetector
    from helion.window.pane_window import PaneWindow

    kind = struct.unpack(">b", inp.read(1))[0]
    if kind == KIND_COUNT_MIN:
        return CountMinSketch.decode_state(inp)
    if kind == KIND_SPACE_SAVING:
        return SpaceSaving.decode_state(inp)
    if kind == KIND_PHI_HOT_KEYS:
        return PhiHotKeyDetector.decode_state(inp)
    if kind == KIND_PANE_WINDOW:
        return PaneWindow.decode_state(inp)
    raise CodecError(f"unknown component kind: {kind}")
