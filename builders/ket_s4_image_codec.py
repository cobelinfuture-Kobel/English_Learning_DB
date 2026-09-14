from __future__ import annotations

import hashlib
import math
import struct
import zlib

RENDER_DPI = 144
RENDER_ENGINE = "PyMuPDF"
RENDER_ENGINE_VERSION = "1.26.7"
HASH_TARGET = "DETERMINISTIC_METADATA_FREE_RGB_PNG_BYTES"
PNG_ENCODING = "RGB8_FILTER0_STORED_DEFLATE_NO_ANCILLARY_CHUNKS"


class S4CodecError(ValueError):
    pass


def _chunk(kind: bytes, payload: bytes) -> bytes:
    return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", zlib.crc32(kind + payload) & 0xFFFFFFFF)


def _stored_zlib(raw: bytes) -> bytes:
    out = bytearray(b"\x78\x01")
    pos = 0
    while pos < len(raw) or (not raw and pos == 0):
        part = raw[pos:pos + 65535]
        pos += len(part)
        final = pos >= len(raw)
        out.append(1 if final else 0)
        n = len(part)
        out += struct.pack("<H", n) + struct.pack("<H", 0xFFFF ^ n) + part
        if final:
            break
    out += struct.pack(">I", zlib.adler32(raw) & 0xFFFFFFFF)
    return bytes(out)


def canonical_rgb_png(rgb: bytes, width: int, height: int) -> bytes:
    if width <= 0 or height <= 0 or len(rgb) != width * height * 3:
        raise S4CodecError("PNG_RGB_SHAPE")
    stride = width * 3
    raw = b"".join(b"\x00" + rgb[y * stride:(y + 1) * stride] for y in range(height))
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + _chunk(b"IHDR", ihdr) + _chunk(b"IDAT", _stored_zlib(raw)) + _chunk(b"IEND", b"")


def png_sha256(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def pixel_box(bbox: list[float], page_size: list[float], rw: int, rh: int) -> tuple[int, int, int, int]:
    if len(bbox) != 4 or len(page_size) != 2:
        raise S4CodecError("CROP_SHAPE")
    sw, sh = page_size
    x0, y0, x1, y1 = bbox
    if not (sw > 0 and sh > 0 and 0 <= x0 <= x1 <= sw and 0 <= y0 <= y1 <= sh and rw > 0 and rh > 0):
        raise S4CodecError("CROP_RANGE")
    sx, sy = rw / sw, rh / sh
    box = (
        max(0, min(rw, math.floor(x0 * sx))),
        max(0, min(rh, math.floor(y0 * sy))),
        max(0, min(rw, math.ceil(x1 * sx))),
        max(0, min(rh, math.ceil(y1 * sy))),
    )
    if box[2] <= box[0] or box[3] <= box[1]:
        raise S4CodecError("CROP_EMPTY")
    return box


def crop_rgb(samples: bytes, pix_width: int, box: tuple[int, int, int, int]) -> tuple[bytes, int, int]:
    left, top, right, bottom = box
    width, height = right - left, bottom - top
    stride, row_bytes = pix_width * 3, width * 3
    out = bytearray(row_bytes * height)
    pos = 0
    for y in range(top, bottom):
        start = y * stride + left * 3
        out[pos:pos + row_bytes] = samples[start:start + row_bytes]
        pos += row_bytes
    return bytes(out), width, height
