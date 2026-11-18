"""Tegra X1 block-linear (de)swizzling and BC4 / RGBA8 texel codecs, numpy based."""
import numpy as np


def block_height_for(height_in_blocks):
    """Default block height (in GOBs) the NX SDK picks for a surface of this height."""
    bh = 16
    while bh > 1 and height_in_blocks <= (bh // 2) * 8:
        bh //= 2
    return bh


def _offsets(width_el, height_el, bpe, block_height):
    """Byte offset of every element (row-major order) inside a block-linear surface."""
    x = np.arange(width_el, dtype=np.int64)[None, :] * bpe
    y = np.arange(height_el, dtype=np.int64)[:, None]
    width_gobs = (width_el * bpe + 63) // 64
    gob = ((y // (8 * block_height)) * 512 * block_height * width_gobs
           + (x // 64) * 512 * block_height
           + (y % (8 * block_height) // 8) * 512)
    return (gob + ((x % 64) // 32) * 256 + ((y % 8) // 4) * 128 + ((y % 4) // 2) * 32
            + ((x % 32) // 16) * 64 + (y % 2) * 16 + (x % 16))


def surface_size(width_el, height_el, bpe, block_height):
    width_gobs = (width_el * bpe + 63) // 64
    rows = (height_el + 8 * block_height - 1) // (8 * block_height)
    return rows * width_gobs * 512 * block_height


def deswizzle(data, width_el, height_el, bpe, block_height):
    off = _offsets(width_el, height_el, bpe, block_height)
    buf = np.frombuffer(data, dtype=np.uint8)
    idx = off[..., None] + np.arange(bpe)
    return buf[idx]  # (h, w, bpe)


def swizzle(elements, block_height, size=None):
    """elements: (h, w, bpe) uint8 -> bytes in block-linear layout."""
    h, w, bpe = elements.shape
    off = _offsets(w, h, bpe, block_height)
    out = np.zeros(size or surface_size(w, h, bpe, block_height), dtype=np.uint8)
    out[off[..., None] + np.arange(bpe)] = elements
    return out.tobytes()


# ---------------------------------------------------------------- BC4

def bc4_decode(blocks):
    """blocks: (bh, bw, 8) uint8 -> (bh*4, bw*4) uint8 image."""
    r0 = blocks[..., 0].astype(np.int32)
    r1 = blocks[..., 1].astype(np.int32)
    bits = np.zeros(blocks.shape[:2], dtype=np.uint64)
    for i in range(6):
        bits |= blocks[..., 2 + i].astype(np.uint64) << np.uint64(8 * i)
    pal = np.zeros(blocks.shape[:2] + (8,), dtype=np.int32)
    pal[..., 0], pal[..., 1] = r0, r1
    big = r0 > r1
    for i in range(1, 7):
        pal[..., 1 + i] = np.where(big, ((7 - i) * r0 + i * r1) // 7, 0)
    for i in range(1, 5):
        pal[..., 1 + i] = np.where(big, pal[..., 1 + i], ((5 - i) * r0 + i * r1) // 5)
    pal[..., 6] = np.where(big, pal[..., 6], 0)
    pal[..., 7] = np.where(big, pal[..., 7], 255)
    bh, bw = blocks.shape[:2]
    out = np.zeros((bh, 4, bw, 4), dtype=np.uint8)
    for t in range(16):
        idx = ((bits >> np.uint64(3 * t)) & np.uint64(7)).astype(np.int64)
        val = np.take_along_axis(pal, idx[..., None], axis=2)[..., 0]
        out[:, t // 4, :, t % 4] = val
    return out.reshape(bh * 4, bw * 4)


def bc4_encode(img):
    """img: (h, w) uint8, h and w multiples of 4 -> (h/4, w/4, 8) blocks.

    Uses the 8-value mode with endpoints = block min/max, which is exact for
    flat blocks and within ~1/14 of range elsewhere.
    """
    h, w = img.shape
    t = img.reshape(h // 4, 4, w // 4, 4).transpose(0, 2, 1, 3).reshape(h // 4, w // 4, 16).astype(np.int32)
    hi = t.max(axis=2)
    lo = t.min(axis=2)
    flat = hi == lo
    r0 = np.where(flat, hi, hi)
    r1 = np.where(flat, np.maximum(lo - 1, 0), lo)
    # if hi == lo == 0 then r0 = 0, r1 = 0 -> 6-value mode, index 0 = r0 = 0; fine.
    r0 = np.where(flat & (hi == 0), 0, r0)
    pal = np.zeros(t.shape[:2] + (8,), dtype=np.int32)
    pal[..., 0], pal[..., 1] = r0, r1
    for i in range(1, 7):
        pal[..., 1 + i] = ((7 - i) * r0 + i * r1) // 7
    big = r0 > r1
    # In 6-value mode (only when both zero) everything maps to index 0.
    err = np.abs(t[..., :, None] - pal[..., None, :])
    idx = err.argmin(axis=3).astype(np.uint64)
    idx = np.where(big[..., None], idx, 0)
    bits = np.zeros(t.shape[:2], dtype=np.uint64)
    for i in range(16):
        bits |= idx[..., i] << np.uint64(3 * i)
    out = np.zeros(t.shape[:2] + (8,), dtype=np.uint8)
    out[..., 0], out[..., 1] = r0, r1
    for i in range(6):
        out[..., 2 + i] = ((bits >> np.uint64(8 * i)) & np.uint64(0xFF)).astype(np.uint8)
    return out


# ---------------------------------------------------------------- BC1 / BC3

def _to565(c):
    c = np.clip(np.rint(c), 0, 255).astype(np.int32)
    return ((c[..., 0] * 31 + 127) // 255) << 11 | ((c[..., 1] * 63 + 127) // 255) << 5 | ((c[..., 2] * 31 + 127) // 255)


def _from565(v):
    r = (v >> 11) & 31
    g = (v >> 5) & 63
    b = v & 31
    return np.stack([(r << 3) | (r >> 2), (g << 2) | (g >> 4), (b << 3) | (b >> 2)], axis=-1).astype(np.float32)


def bc1_encode_colors(rgb, weight):
    """rgb: (n, 16, 3) float, weight: (n, 16) float (0 = pixel does not matter) -> (n, 8) uint8, 4-colour mode."""
    n = rgb.shape[0]
    w = weight + 1e-6
    ws = w.sum(axis=1, keepdims=True)
    mean = (rgb * w[..., None]).sum(axis=1) / ws
    cen = rgb - mean[:, None, :]
    cov = np.einsum('nk,nki,nkj->nij', w, cen, cen)
    axis = np.ones((n, 3), dtype=np.float32)
    for _ in range(8):
        axis = np.einsum('nij,nj->ni', cov, axis)
        axis /= np.linalg.norm(axis, axis=1, keepdims=True) + 1e-9
    t = np.einsum('nki,ni->nk', cen, axis)
    used = weight > 0
    tmax = np.where(used, t, -1e9).max(axis=1)
    tmin = np.where(used, t, 1e9).min(axis=1)
    none = ~used.any(axis=1)
    tmax[none] = 0
    tmin[none] = 0
    c0 = _to565(mean + tmax[:, None] * axis)
    c1 = _to565(mean + tmin[:, None] * axis)
    swap = c0 < c1
    c0, c1 = np.where(swap, c1, c0), np.where(swap, c0, c1)
    eq = c0 == c1
    # 4-colour mode needs c0 > c1; for a flat block nudge c1 down (or c0 up) and use index 0 only.
    c1 = np.where(eq & (c1 > 0), c1 - 1, c1)
    c0 = np.where(eq & (c0 == c1), c0 + 1, c0)
    p0, p1 = _from565(c0), _from565(c1)
    pal = np.stack([p0, p1, (2 * p0 + p1) / 3, (p0 + 2 * p1) / 3], axis=1)  # (n, 4, 3)
    d = ((rgb[:, :, None, :] - pal[:, None, :, :]) ** 2).sum(axis=-1)       # (n, 16, 4)
    idx = d.argmin(axis=2).astype(np.uint32)
    idx = np.where(eq[:, None], 0, idx)
    bits = np.zeros(n, dtype=np.uint32)
    for i in range(16):
        bits |= idx[:, i] << np.uint32(2 * i)
    out = np.zeros((n, 8), dtype=np.uint8)
    out[:, 0], out[:, 1] = c0 & 0xFF, c0 >> 8
    out[:, 2], out[:, 3] = c1 & 0xFF, c1 >> 8
    for i in range(4):
        out[:, 4 + i] = (bits >> np.uint32(8 * i)) & 0xFF
    return out


def bc3_encode(rgba):
    """rgba: (h, w, 4) uint8 -> (h/4, w/4, 16) blocks (BC4-style alpha + BC1 colour)."""
    h, w, _ = rgba.shape
    alpha = bc4_encode(np.ascontiguousarray(rgba[..., 3]))
    t = rgba.reshape(h // 4, 4, w // 4, 4, 4).transpose(0, 2, 1, 3, 4).reshape(-1, 16, 4).astype(np.float32)
    col = bc1_encode_colors(t[..., :3], t[..., 3] / 255.0)
    return np.concatenate([alpha.reshape(-1, 8), col], axis=1).reshape(h // 4, w // 4, 16)


def bc3_decode(blocks):
    """(bh, bw, 16) -> (bh*4, bw*4, 4) uint8."""
    bh, bw, _ = blocks.shape
    a = bc4_decode(blocks[..., :8])
    c = blocks[..., 8:].reshape(-1, 8).astype(np.uint32)
    c0 = c[:, 0] | c[:, 1] << 8
    c1 = c[:, 2] | c[:, 3] << 8
    bits = c[:, 4] | c[:, 5] << 8 | c[:, 6] << 16 | c[:, 7] << 24
    p0, p1 = _from565(c0), _from565(c1)
    pal = np.stack([p0, p1, (2 * p0 + p1) / 3, (p0 + 2 * p1) / 3], axis=1)
    idx = np.stack([(bits >> np.uint32(2 * i)) & 3 for i in range(16)], axis=1).astype(np.int64)
    rgb = np.take_along_axis(pal, idx[..., None], axis=1)  # (n, 16, 3)
    rgb = rgb.reshape(bh, bw, 4, 4, 3).transpose(0, 2, 1, 3, 4).reshape(bh * 4, bw * 4, 3)
    return np.dstack([np.clip(np.rint(rgb), 0, 255).astype(np.uint8), a])
