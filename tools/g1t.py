"""Koei Tecmo G1T (version 0600, Switch) textures as used by Fire Emblem: Three Houses.

Only what the prompt textures use: format 0x5B = BC3, stored linearly (no block-linear swizzle), one mip level.
Pixels are replaced in place; headers and sizes never change.
"""
import struct

import numpy as np

import tegra


class Texture:
    pass


def read(data):
    magic, ver, size, toff, count = struct.unpack_from('<4s4sIII', data, 0)
    assert magic == b'GT1G', 'not a G1T'
    offs = struct.unpack_from('<%dI' % count, data, toff)
    out = []
    for o in offs:
        h = toff + o
        t = Texture()
        t.header = h
        t.mips = data[h] >> 4
        t.format = data[h + 1]
        t.width = 1 << (data[h + 2] & 15)
        t.height = 1 << (data[h + 2] >> 4)
        ext = data[h + 7]
        ext_len = struct.unpack_from('<I', data, h + 8)[0] if ext else 0
        t.data_off = h + 8 + ext_len
        t.size = t.width * t.height  # BC3: 1 byte per pixel
        assert t.format == 0x5B and t.mips == 1, (hex(t.format), t.mips)
        out.append(t)
    return out


def decode(data, t):
    bw, bh = t.width // 4, t.height // 4
    blocks = np.frombuffer(data, np.uint8, bw * bh * 16, t.data_off).reshape(bh, bw, 16)
    return tegra.bc3_decode(blocks)


def encode_into(buf, t, rgba, old=None):
    """Write an RGBA image into texture t of bytearray buf, re-encoding only the 4x4 blocks that changed."""
    bw, bh = t.width // 4, t.height // 4
    old_blocks = np.frombuffer(bytes(buf[t.data_off:t.data_off + t.size]), np.uint8).reshape(bh, bw, 16)
    if old is None:
        old = tegra.bc3_decode(old_blocks)
    changed = (old != rgba).reshape(bh, 4, bw, 4, 4).any(axis=(1, 3, 4))
    if not changed.any():
        return 0
    ys, xs = np.where(changed)
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    sub = np.ascontiguousarray(rgba[y0 * 4:y1 * 4, x0 * 4:x1 * 4])
    new_blocks = tegra.bc3_encode(sub)
    blocks = old_blocks.copy()
    region = blocks[y0:y1, x0:x1]
    region[changed[y0:y1, x0:x1]] = new_blocks[changed[y0:y1, x0:x1]]
    buf[t.data_off:t.data_off + t.size] = blocks.tobytes()
    return int(changed.sum())
