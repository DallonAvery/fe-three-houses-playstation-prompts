"""Fire Emblem: Three Houses RomFS archive access (DATA0/DATA1 + patchN overrides).

DATA0.bin: 32-byte records (u64 offset, u64 size, u64 stored size, u64 compressed flag) indexed by entry number.
DATA1.bin: the entry data. patchN/INFO0.bin: 288-byte records (u64 entry, u64 size, u64 stored, u64 compressed,
256-byte "rom:/..." path) that replace entries with loose files. Compressed entries are a chunk table followed by
128-byte-aligned zlib chunks.
"""
import struct
import zlib
from pathlib import Path


def inflate(data):
    _, count, total = struct.unpack_from('<III', data)
    lengths = struct.unpack_from('<%dI' % count, data, 12)
    pos = (12 + 4 * count + 127) & ~127
    out = []
    for length in lengths:
        stored, = struct.unpack_from('<I', data, pos)
        out.append(zlib.decompress(data[pos + 4:pos + 4 + stored]) if stored == length - 4 else data[pos:pos + length])
        pos = (pos + length + 127) & ~127
    res = b''.join(out)
    assert len(res) == total, 'archive decompression failed'
    return res


class RomFS:
    def __init__(self, root):
        self.root = Path(root)
        self.meta = (self.root / 'DATA0.bin').read_bytes()
        self.overrides = {}
        for patch in sorted(self.root.glob('patch*')):
            info = patch / 'INFO0.bin'
            if not info.exists():
                continue
            d = info.read_bytes()
            for pos in range(0, len(d), 288):
                idx, size, stored, comp = struct.unpack_from('<QQQQ', d, pos)
                name = d[pos + 32:pos + 288].split(b'\0')[0].decode()
                self.overrides[idx] = (self.root / name[5:], comp, patch.name)

    def source(self, idx):
        return self.overrides[idx][2] if idx in self.overrides else 'DATA1'

    def read(self, idx):
        if idx in self.overrides:
            path, comp, _ = self.overrides[idx]
            raw = path.read_bytes()
        else:
            off, size, stored, comp = struct.unpack_from('<QQQQ', self.meta, idx * 32)
            with open(self.root / 'DATA1.bin', 'rb') as f:
                f.seek(off)
                raw = f.read(stored)
        return inflate(raw) if comp else raw
