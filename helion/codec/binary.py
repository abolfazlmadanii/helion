from __future__ import annotations

import struct
from array import array
from typing import BinaryIO


class CodecError(RuntimeError):
    pass


def write_string(out: BinaryIO, value: str) -> None:
    data = value.encode("utf-8")
    out.write(struct.pack(">i", len(data)))
    out.write(data)


def read_string(inp: BinaryIO) -> str:
    length = struct.unpack(">i", inp.read(4))[0]
    if length < 0:
        raise CodecError(f"negative string length: {length}")
    return inp.read(length).decode("utf-8")


def write_long_array(out: BinaryIO, values: list[int]) -> None:
    out.write(struct.pack(">i", len(values)))
    for value in values:
        out.write(struct.pack(">q", value))


def read_long_array(inp: BinaryIO) -> list[int]:
    length = struct.unpack(">i", inp.read(4))[0]
    if length < 0:
        raise CodecError(f"negative array length: {length}")
    return [struct.unpack(">q", inp.read(8))[0] for _ in range(length)]


def write_long_matrix(out: BinaryIO, matrix: list[array]) -> None:
    out.write(struct.pack(">i", len(matrix)))
    for row in matrix:
        write_long_array(out, list(row))


def read_long_matrix(inp: BinaryIO) -> list[list[int]]:
    rows = struct.unpack(">i", inp.read(4))[0]
    if rows < 0:
        raise CodecError(f"negative matrix rows: {rows}")
    return [read_long_array(inp) for _ in range(rows)]
