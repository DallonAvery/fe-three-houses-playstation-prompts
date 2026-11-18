"""Build the Fire Emblem: Three Houses PlayStation prompt mod from your own 1.2.0 RomFS dump.

  python build_th.py --romfs <romfs> --layout circle-confirm --style dualsense --out "<mod folder>" [--preview png]

What changes (everything else is the game's):
  entry 72          the button-glyph font atlas (prompts inside text)
  entries 0, 1, 3 + battle tip lists  text in all 12 languages: "the A Button" / "Ａボタン" / "bouton A"... -> the
                    inline icon (or, English only, the PlayStation name with --text words)
  entries 6026-6037 texture 9: the button icon sheet (prompt bar, menus); texture 2: the inventory tab badges
The mod uses the game's own override list: romfs/patch4/INFO0.bin gets entries that point at
romfs/mods/ps_ui/<entry>.g1t, and INFO2.bin's count is updated.
"""
import argparse
import hashlib
import struct
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
import g1t  # noqa: E402
import psglyphs  # noqa: E402
import th_archive  # noqa: E402
import th_text  # noqa: E402

INFO0_120 = 'ba4990d33b446bce03450a324345cf0c35fb987efc8ed2a31a2aa14764c2ed31'
ATLAS = 72
TEXT = [0, 1, 3]    # msgdata.bin, scrdata.bin, tuscrdata.bin (Guide pages): button names, all languages
SHEETS = list(range(6026, 6038))

# Font atlas 72: the button row, 48 px cells starting at x = 624. Cell -> the Fortune's Weave code point it matches.
ATLAS_CELLS = {0: 0xE0E0, 1: 0xE0E1, 2: 0xE0E2, 3: 0xE0E3, 4: 0xE0E4, 5: 0xE0E5, 6: 0xE0E6, 7: 0xE0E7,
               14: 0xE0EF, 15: 0xE0F0, 16: 0xE0F1, 17: 0xE0F2}
ATLAS_X0, ATLAS_PITCH, ATLAS_H = 624, 48, 52

# Icon sheet (texture 9, 512x512): 7x7 cells, 68 px pitch. (col, row) -> what it shows.
SHEET_TEX = 9
SHEET_CELLS = {
    (1, 0): ('face', 'A'), (2, 0): ('face', 'B'), (3, 0): ('face', 'X'), (4, 0): ('face', 'Y'),
    (5, 1): ('code', 0xE0E4), (6, 1): ('code', 0xE0E5), (0, 2): ('code', 0xE0E6), (1, 2): ('code', 0xE0E7),
    (4, 2): ('code', 0xE0F1), (5, 2): ('code', 0xE0F2), (2, 6): ('code', 0xE0F1), (3, 6): ('code', 0xE0F2),
    (5, 3): ('letter', 'A'), (6, 3): ('letter', 'A'), (0, 4): ('letter', 'B'), (1, 4): ('letter', 'X'), (2, 4): ('letter', 'Y'),
    (3, 5): ('label', 'L1'), (4, 5): ('label', 'R1'), (5, 5): ('label', 'L2'), (6, 5): ('label', 'R2'),
}
SHEET_RGB = (239, 242, 239)
SHADOW = dict(dy=1, blur=2.5, strength=0.9)

# Inventory tab badges (texture 2): left to right ZL, ZR, L, R.
TAB_TEX = 2
TAB_BOX = (1244, 1930, 1440, 1970)
TAB_LABELS = ['L2', 'R2', 'L1', 'R1']
TAB_FONT = 'C:/Windows/Fonts/palab.ttf'


def bbox(alpha, thr=64):
    ys, xs = np.where(alpha > thr)
    return int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())


def glyph(kind, box, cell, style):
    """(rgb uint8, alpha float) for one icon in the chosen style."""
    if style == 'dualsense':
        alpha, _ = psglyphs.draw(kind, box, cell, outline_px=3)
        if kind[0] == 'symbol':
            pass
        return np.full(alpha.shape + (3,), 255, np.uint8), alpha
    return psglyphs.draw_color(kind, box, cell, 3, style.split('-', 1)[1])


def patch_atlas(data, layout, style, menu):
    buf = bytearray(data)
    t = g1t.read(data)[0]
    img = g1t.decode(data, t)
    old = img.copy()
    plan = psglyphs.plan(layout, menu)
    boxes = {}
    for k, code in ATLAS_CELLS.items():
        x0 = ATLAS_X0 + ATLAS_PITCH * k
        boxes[k] = bbox(img[0:ATLAS_H, x0:x0 + ATLAS_PITCH, 3])
    boxes[17] = boxes[16]          # the bare minus is a thin bar: give Create/Share the bare plus's box
    before, after = {}, {}
    for k, code in ATLAS_CELLS.items():
        x0 = ATLAS_X0 + ATLAS_PITCH * k
        before[k] = img[0:ATLAS_H, x0:x0 + ATLAS_PITCH].copy()
        rgb, alpha = glyph(plan[code], boxes[k], (ATLAS_PITCH, ATLAS_H), style)
        cell = np.dstack([rgb, np.clip(alpha * 255 + 0.5, 0, 255).astype(np.uint8)])
        img[0:ATLAS_H, x0:x0 + ATLAS_PITCH] = cell
        after[k] = cell
    g1t.encode_into(buf, t, img, old)
    return bytes(buf), before, after


def _shadowed(rgb, alpha):
    """Composite the sheet's soft dark halo under an icon (straight alpha)."""
    a = Image.fromarray((alpha * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(SHADOW['blur']))
    sh = np.roll(np.asarray(a, np.float32) / 255, SHADOW['dy'], 0) * SHADOW['strength']
    out_a = alpha + sh * (1 - alpha)
    out_rgb = rgb.astype(np.float32) * (alpha / np.maximum(out_a, 1e-6))[..., None]
    return np.dstack([np.clip(out_rgb + 0.5, 0, 255), np.clip(out_a * 255 + 0.5, 0, 255)]).astype(np.uint8)


def patch_sheet(img, layout, style, menu):
    plan = psglyphs.plan(layout, menu)
    sym = psglyphs.LAYOUTS[layout]
    sheet0 = img.copy()         # measure boxes on the untouched sheet (cells are redrawn as we go)
    before, after = {}, {}
    for (c, r), (what, val) in SHEET_CELLS.items():
        x0, y0 = max(68 * c - 2, 0), 68 * r + 1
        x1, y1 = min(x0 + 68, img.shape[1]), min(y0 + 68, img.shape[0])
        cell = img[y0:y1, x0:x1]
        a = cell[..., 3].astype(np.float32) / 255 * (cell[..., :3].mean(-1) / 239.0)  # the light part, without the halo
        box = bbox((np.clip(a, 0, 1) * 255).astype(np.uint8), 100)
        if what == 'face':
            kind = ('face', sym[val], 'filled')
        elif what == 'code':
            kind = plan[val]
            if val == 0xE0F2:   # bare minus: use the bare plus's square box
                pc, pr = (c - 1, r)
                px0, py0 = max(68 * pc - 2, 0), 68 * pr + 1
                pa = sheet0[py0:py0 + 68, px0:px0 + 68]
                pa = pa[..., 3].astype(np.float32) / 255 * (pa[..., :3].mean(-1) / 239.0)
                box = bbox((np.clip(pa, 0, 1) * 255).astype(np.uint8), 100)
        elif what == 'letter':
            kind = ('symbol', sym[val], 'bare')
        else:
            kind = ('text', val, 'bare')
        rgb, alpha = glyph(kind, box, (x1 - x0, y1 - y0), style)
        # the light colour of this cell in the original sheet (filled buttons are a little greyer than bare marks)
        orig = cell[(cell[..., 3] > 240) & (cell[..., :3].mean(-1) > 150)][:, :3]
        base = np.median(orig, 0).astype(np.uint8) if len(orig) else np.array(SHEET_RGB, np.uint8)
        light = rgb.astype(int).min(-1, keepdims=True) >= 250
        rgb = np.where(light, base, rgb)
        before[(c, r)] = cell.copy()
        new = _shadowed(rgb, alpha)
        img[y0:y1, x0:x1] = new
        after[(c, r)] = new
    return before, after


def patch_tabs(img):
    x0, y0, x1, y1 = TAB_BOX
    region = img[y0:y1, x0:x1]
    a = region[..., 3] > 40
    a[:, :8] = False        # the frame edge at the far left belongs to another element
    cols = np.where(a.any(0))[0]
    groups = np.split(cols, np.where(np.diff(cols) > 2)[0] + 1)
    groups = [g for g in groups if len(g) > 12][:4]
    assert len(groups) == 4, 'expected 4 tab badges, found %d' % len(groups)
    before = region.copy()
    for g, label in zip(groups, TAB_LABELS):
        gx0, gx1 = g[0], g[-1] + 1
        sub = region[:, gx0:gx1]
        badge = sub[..., 3] > 200
        ys = np.where(badge.any(1))[0]
        by0, by1 = ys[0], ys[-1] + 1
        # badge colour: the darkest opaque pixels; letter colour: the lightest
        opaque = sub[badge]
        lum = opaque[:, :3].astype(int).sum(-1)
        disc = np.median(opaque[lum <= np.percentile(lum, 40)][:, :3], 0)
        ink = np.median(opaque[lum >= np.percentile(lum, 92)][:, :3], 0)
        # repaint the badge interior (letters gone), keep its antialiased edge
        inner = np.asarray(Image.fromarray((badge * 255).astype(np.uint8)).filter(ImageFilter.MinFilter(3))) > 0
        sub[inner, :3] = disc.astype(np.uint8)
        # new label, Palatino Bold, light with a dark edge
        S = 4
        h, w = by1 - by0, gx1 - gx0
        txt = Image.new('L', (w * S, h * S), 0)
        dr = ImageDraw.Draw(txt)
        size = h * S * 0.86
        f = ImageFont.truetype(TAB_FONT, int(size))
        l, t, r, b = dr.textbbox((0, 0), label, font=f)
        maxw = w * S * (0.84 if w > h * 1.4 else 0.9)
        if r - l > maxw:
            f = ImageFont.truetype(TAB_FONT, int(size * maxw / (r - l)))
            l, t, r, b = dr.textbbox((0, 0), label, font=f)
        dr.text(((w * S - (l + r)) / 2, (h * S - (t + b)) / 2 + S * 0.3), label, font=f, fill=255)
        ta = np.asarray(txt.resize((w, h), Image.BOX), np.float32) / 255
        edge = np.asarray(Image.fromarray((ta * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(3)), np.float32) / 255
        area = sub[by0:by1]
        col = area[..., :3].astype(np.float32)
        col = col * (1 - edge[..., None] * 0.6) + 0 * edge[..., None] * 0.6
        col = col * (1 - ta[..., None]) + ink * ta[..., None]
        area[..., :3] = np.clip(col + 0.5, 0, 255).astype(np.uint8)
    return before, region.copy()


def build(romfs, layout, style, menu, text='glyphs', icon_test=False):
    fs = th_archive.RomFS(romfs)
    info0 = (Path(romfs) / 'patch4' / 'INFO0.bin').read_bytes()
    if hashlib.sha256(info0).hexdigest() != INFO0_120:
        raise SystemExit('This RomFS is not Three Houses 1.2.0 (patch4/INFO0.bin differs). Dump it with the 1.2.0 update installed.')
    out, previews = {}, {}
    data = fs.read(ATLAS)
    out[ATLAS], b, a = patch_atlas(data, layout, style, menu)
    previews['atlas'] = (b, a)
    previews['text'] = []
    if text != 'off':
        for e in TEXT:
            out[e], ch = th_text.patch(fs.read(e), layout, text, menu,
                                       [th_text.icon_test_rule()] if icon_test else ())
            previews['text'] += ch
        lists = th_text.LISTS if text == 'glyphs' else [th_text.LISTS[b] for b in th_text.ENGLISH]
        for b, e in enumerate(th_text.LISTS):
            if e not in lists:
                continue
            new, ch = th_text.patch_list(fs.read(e), layout, text, menu)
            if ch:
                out[e] = new
                previews['text'] += [(b,) + c for c in ch]
    for e in SHEETS:
        data = fs.read(e)
        buf = bytearray(data)
        ts = g1t.read(data)
        t = ts[SHEET_TEX]
        img = g1t.decode(data, t)
        old = img.copy()
        b, a = patch_sheet(img, layout, style, menu)
        g1t.encode_into(buf, t, img, old)
        t2 = ts[TAB_TEX]
        img2 = g1t.decode(bytes(buf), t2)
        old2 = img2.copy()
        tb, ta = patch_tabs(img2)
        g1t.encode_into(buf, t2, img2, old2)
        out[e] = bytes(buf)
        if e == SHEETS[0]:
            previews['sheet'] = (b, a)
            previews['tabs'] = (tb, ta)
    return out, previews, info0, (Path(romfs) / 'patch4' / 'INFO2.bin').read_bytes()


def write_mod(out_dir, entries, info0, info2):
    romfs = Path(out_dir) / 'romfs'
    files = romfs / 'mods' / 'ps_ui'
    files.mkdir(parents=True, exist_ok=True)
    merged = {struct.unpack_from('<Q', info0, p)[0]: info0[p:p + 288] for p in range(0, len(info0), 288)}
    for idx, data in entries.items():
        fn = '%d.%s' % (idx, 'g1t' if data[:4] == b'GT1G' else 'bin')
        (files / fn).write_bytes(data)
        name = ('rom:/mods/ps_ui/' + fn).encode()
        merged[idx] = struct.pack('<QQQQ', idx, len(data), len(data), 0) + name.ljust(256, b'\0')
    (romfs / 'patch4').mkdir(exist_ok=True)
    (romfs / 'patch4' / 'INFO0.bin').write_bytes(b''.join(merged[i] for i in sorted(merged)))
    count1 = struct.unpack_from('<Q', info2, 8)[0]
    (romfs / 'patch4' / 'INFO2.bin').write_bytes(struct.pack('<QQ', len(merged), count1))


def preview(previews, path):
    bg = (30, 45, 55)
    rows = []
    for key in ('atlas', 'sheet'):
        b, a = previews[key]
        keys = list(b)
        h = max(v.shape[0] for v in b.values())
        w = max(v.shape[1] for v in b.values())
        for src in (b, a):
            im = Image.new('RGBA', (len(keys) * (w + 6) + 6, h + 12), bg + (255,))
            for i, k in enumerate(keys):
                im.alpha_composite(Image.fromarray(src[k], 'RGBA'), (6 + i * (w + 6), 6))
            rows.append(im)
    tb, ta = previews['tabs']
    for src in (tb, ta):
        im = Image.new('RGBA', (src.shape[1] * 3, src.shape[0] * 3), bg + (255,))
        im.alpha_composite(Image.fromarray(src, 'RGBA').resize((src.shape[1] * 3, src.shape[0] * 3), Image.LANCZOS))
        rows.append(im)
    W = max(r.width for r in rows)
    out = Image.new('RGB', (W, sum(r.height for r in rows) + 4 * len(rows)), (0, 0, 0))
    y = 0
    for r in rows:
        out.paste(r.convert('RGB'), (0, y))
        y += r.height + 4
    out.save(path)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--romfs', required=True)
    ap.add_argument('--layout', default='circle-confirm', choices=sorted(psglyphs.LAYOUTS))
    ap.add_argument('--style', default='dualsense', choices=['dualsense', 'dualshock-pale', 'dualshock-dark'])
    ap.add_argument('--menu', choices=['dualsense', 'ds4-label', 'ds4-pill'])
    ap.add_argument('--text', default='glyphs', choices=['glyphs', 'words', 'off'],
                    help='English button names in text: inline icons (default), PlayStation names, or unchanged')
    ap.add_argument('--icon-test', action='store_true', help=argparse.SUPPRESS)
    ap.add_argument('--out', required=True, type=Path)
    ap.add_argument('--preview', type=Path)
    a = ap.parse_args()
    menu = a.menu or ('dualsense' if a.style == 'dualsense' else 'ds4-label')
    entries, previews, info0, info2 = build(a.romfs, a.layout, a.style, menu, a.text, a.icon_test)
    write_mod(a.out, entries, info0, info2)
    print('wrote', a.out, 'with', len(entries), 'archives;', len(previews['text']), 'text lines changed')
    if a.preview:
        preview(previews, a.preview)
        print('preview', a.preview)


if __name__ == '__main__':
    main()
