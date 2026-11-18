"""PlayStation button icons drawn from simple vector shapes.

Every icon is drawn into the footprint (bounding box) of the Switch glyph it
replaces, so it sits on the same baseline and keeps the same advance width.
Drawing happens at SS x resolution and is box-filtered down for clean edges.

Output of draw(): float32 arrays in 0..1 at cell size:
  alpha  - coverage of the whole icon
  ink    - coverage of the symbol/label part (for colour styles)
"""
import math

import numpy as np
from PIL import Image, ImageDraw, ImageFont

SS = 8
FONT_PATH = 'C:/Windows/Fonts/bahnschrift.ttf'

# Switch code point -> what it is, in both the outlined (E000..) and filled (E0E0..) sets.
FACE_OUTLINE = {0xE000: 'A', 0xE001: 'B', 0xE002: 'X', 0xE003: 'Y'}
FACE_FILLED = {0xE0E0: 'A', 0xE0E1: 'B', 0xE0E2: 'X', 0xE0E3: 'Y'}

LAYOUTS = {
    # EmblemWeave default ([pad] label_abxy = true): Cross is Switch A.
    'cross-confirm': {'A': 'cross', 'B': 'circle', 'X': 'square', 'Y': 'triangle'},
    # Position based (yuzu/Ryujinx default for PlayStation pads): Circle is Switch A.
    'circle-confirm': {'A': 'circle', 'B': 'cross', 'X': 'triangle', 'Y': 'square'},
    # Position based with only confirm/back swapped (emulator remapped A = Cross, B = Circle; Three Houses).
    'cross-swap': {'A': 'cross', 'B': 'circle', 'X': 'triangle', 'Y': 'square'},
}

# DualShock 4 symbol colours.
DS4_COLORS = {
    'cross': (122, 168, 230),
    'circle': (236, 98, 104),
    'square': (220, 140, 200),
    'triangle': (64, 200, 168),
}


def _canvas(w, h):
    return Image.new('L', (w * SS, h * SS), 0)


def _down(img, w, h):
    return np.asarray(img.resize((w, h), Image.BOX), dtype=np.float32) / 255.0


def _font(px, style=b'Bold'):
    f = ImageFont.truetype(FONT_PATH, max(int(px), 1))
    try:
        f.set_variation_by_name(style)
    except Exception:
        pass
    return f


def _symbol(draw, name, cx, cy, d, stroke):
    """Draw a PlayStation face symbol (opaque) centred in a disc of diameter d."""
    if name == 'cross':
        a = 0.235 * d
        for sx in (-1, 1):
            draw.line([(cx - a, cy - sx * a), (cx + a, cy + sx * a)], fill=255, width=int(stroke))
        r = stroke / 2
        for px, py in [(cx - a, cy - a), (cx + a, cy + a), (cx - a, cy + a), (cx + a, cy - a)]:
            draw.ellipse([px - r, py - r, px + r, py + r], fill=255)
    elif name == 'circle':
        r = 0.255 * d + stroke / 2
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=255)
        r -= stroke
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=0)
    elif name == 'square':
        a = 0.225 * d + stroke / 2
        draw.rectangle([cx - a, cy - a, cx + a, cy + a], fill=255)
        a -= stroke
        draw.rectangle([cx - a, cy - a, cx + a, cy + a], fill=0)
    elif name == 'triangle':
        R = 0.385 * d
        cy2 = cy + 0.055 * d

        def tri(rad):
            return [(cx + rad * math.sin(t), cy2 - rad * math.cos(t)) for t in (0, 2 * math.pi / 3, 4 * math.pi / 3)]
        draw.polygon(tri(R), fill=255)
        draw.polygon(tri(R - 2 * stroke), fill=0)
    else:
        raise ValueError(name)


def _symbol_mask(name, w, h, cx, cy, d, stroke):
    img = _canvas(w, h)
    _symbol(ImageDraw.Draw(img), name, cx, cy, d, stroke)
    return img


def _rounded(draw, box, r, fill):
    draw.rounded_rectangle(box, radius=r, fill=fill)


def _trigger(draw, box, fill):
    """Trigger (L2/R2) footprint: big rounded top, small rounded bottom."""
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    rt = 0.42 * w
    rb = 0.16 * h
    draw.rounded_rectangle([x0, y0, x1, y0 + 2 * rt + 1], radius=rt, fill=fill)
    draw.rounded_rectangle([x0, y0 + rt, x1, y1], radius=rb, fill=fill, corners=(False, False, True, True))


def _text(draw, label, cx, cy, height, fill, style=b'Bold Condensed', max_w=None):
    f = _font(height * 1.33, style)
    l, t, r, b = draw.textbbox((0, 0), label, font=f)
    if max_w and r - l > max_w:
        f = _font(height * 1.33 * max_w / (r - l), style)
        l, t, r, b = draw.textbbox((0, 0), label, font=f)
    draw.text((cx - (l + r) / 2, cy - (t + b) / 2), label, font=f, fill=fill)


def _bars(draw, cx, cy, width, thick, gap):
    for k in (-1, 0, 1):
        y = cy + k * gap
        draw.rounded_rectangle([cx - width / 2, y - thick / 2, cx + width / 2, y + thick / 2], radius=thick / 2, fill=255)


def _rays(draw, cx, cy, size, thick):
    """The Create button's mark: three short strokes fanning up and out."""
    base_y = cy + 0.52 * size
    for ang in (-40, 0, 40):
        t = math.radians(ang)
        r0, r1 = 0.50 * size, 0.92 * size
        p0 = (cx + r0 * math.sin(t), base_y - r0 * math.cos(t))
        p1 = (cx + r1 * math.sin(t), base_y - r1 * math.cos(t))
        draw.line([p0, p1], fill=255, width=int(thick))
        for px, py in (p0, p1):
            draw.ellipse([px - thick / 2, py - thick / 2, px + thick / 2, py + thick / 2], fill=255)


def draw(kind, bbox, cell, outline_px=None):
    """Return (alpha, ink) for one icon.

    kind     e.g. ('face', 'cross', 'filled'), ('shoulder', 'L1', 'filled'), ('trigger', 'R2', 'filled'),
             ('options', 'disc'), ('create', 'disc'), ('options', 'bare'), ('create', 'bare')
    bbox     (x0, y0, x1, y1) of the original glyph inside the cell, inclusive pixels
    cell     (w, h)
    """
    w, h = cell
    x0, y0, x1, y1 = [v * SS for v in bbox]
    x1 += SS
    y1 += SS
    bw, bh = x1 - x0, y1 - y0
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    shape = _canvas(w, h)
    ink = _canvas(w, h)
    ds, di = ImageDraw.Draw(shape), ImageDraw.Draw(ink)
    style = kind[-1]
    ol = (outline_px or max(1.0, 0.065 * min(bw, bh) / SS)) * SS

    if kind[0] == 'face':
        d = min(bw, bh)
        box = [cx - d / 2, cy - d / 2, cx + d / 2, cy + d / 2]
        stroke = 0.105 * d if style == 'filled' else 0.085 * d
        sym = _symbol_mask(kind[1], w, h, cx, cy, d * (1.0 if style == 'filled' else 0.95), stroke)
        if style == 'filled':
            ds.ellipse(box, fill=255)
        else:
            ds.ellipse(box, fill=255)
            ds.ellipse([box[0] + ol, box[1] + ol, box[2] - ol, box[3] - ol], fill=0)
        ink.paste(sym)
    elif kind[0] in ('shoulder', 'trigger'):
        box = [x0, y0, x1, y1]
        if kind[0] == 'shoulder':
            _rounded(ds, box, 0.30 * bh, 255)
            if style != 'filled':
                inner = [box[0] + ol, box[1] + ol, box[2] - ol, box[3] - ol]
                _rounded(ds, inner, max(0.30 * bh - ol, 1), 0)
            ty, th = cy + 0.02 * bh, 0.56 * bh
        else:
            _trigger(ds, box, 255)
            if style != 'filled':
                _trigger(ds, [box[0] + ol, box[1] + ol, box[2] - ol, box[3] - ol], 0)
            ty, th = cy + 0.07 * bh, 0.48 * bh
        _text(di, kind[1], cx, ty, th, 255, max_w=0.80 * bw)
    elif kind[0] == 'ds4btn':
        # DualShock 4 Share / Options: ('ds4btn', word, 'pill' | 'label')
        word, look = kind[1], kind[2]
        s = min(bw, bh)
        if look == 'pill':
            pw, ph = 0.30 * s, 0.56 * s
            top = cy - 0.02 * s
            ds.rounded_rectangle([cx - pw / 2, top, cx + pw / 2, top + ph], radius=pw / 2, fill=255)
            _text(ds, word, cx, y0 + 0.5 * (top - y0) - 0.01 * s, 0.24 * s, 255, style=b'Bold Condensed', max_w=0.98 * bw)
        else:
            lh = 0.44 * s
            box = [x0, cy - lh / 2, x1, cy + lh / 2]
            ds.rounded_rectangle(box, radius=0.12 * lh, fill=255)
            _text(di, word, cx, cy, 0.62 * lh, 255, style=b'Bold Condensed', max_w=0.86 * bw)
    elif kind[0] == 'symbol':
        # a PlayStation symbol on its own (no button), filling the box: ('symbol', name, 'bare')
        d = bh / 0.50          # by height: the letters it replaces differ in width (B is narrower than A)
        di.rectangle([0, 0, w * SS, h * SS], fill=0)
        _symbol(di, kind[1], cx, cy, d, 0.085 * d)
    elif kind[0] == 'text':
        # a plain label ('text', 'L1', 'bare'), as tall as the box
        _text(di, kind[1], cx, cy, 0.86 * bh, 255, style=b'Bold', max_w=1.45 * bh)
    elif kind[0] in ('options', 'create'):
        if style == 'disc':
            d = min(bw, bh)
            ds.ellipse([cx - d / 2, cy - d / 2, cx + d / 2, cy + d / 2], fill=255)
            if kind[0] == 'options':
                _bars(di, cx, cy, 0.50 * d, 0.085 * d, 0.165 * d)
            else:
                _rays(di, cx, cy + 0.10 * d, 0.58 * d, 0.095 * d)
        else:
            # Bare marks: no disc; the mark itself is the whole icon.
            s = min(bw, bh)
            if kind[0] == 'options':
                _bars(ds, cx, cy, 0.95 * s, 0.17 * s, 0.33 * s)
            else:
                _rays(ds, cx, cy + 0.12 * s, 0.74 * s, 0.15 * s)
    else:
        raise ValueError(kind)

    a_shape, a_ink = _down(shape, w, h), _down(ink, w, h)
    if kind[-1] in ('filled', 'disc', 'label'):
        alpha = a_shape * (1 - a_ink)          # symbol is cut out of the button
    else:
        alpha = np.maximum(a_shape, a_ink)      # outline + symbol drawn on top
    return alpha, a_ink


def plan(layout, menu='dualsense'):
    """Switch code point -> icon kind, for one face-button layout.

    menu: 'dualsense' (Options = three bars, Create = rays) or 'ds4-pill' / 'ds4-label' (OPTIONS / SHARE buttons).
    """
    m = LAYOUTS[layout]
    p = {}
    for code, btn in FACE_FILLED.items():
        p[code] = ('face', m[btn], 'filled')
    for code, btn in FACE_OUTLINE.items():
        p[code] = ('face', m[btn], 'outline')
    p[0xE0E4] = ('shoulder', 'L1', 'filled')
    p[0xE0E5] = ('shoulder', 'R1', 'filled')
    p[0xE0E6] = ('trigger', 'L2', 'filled')
    p[0xE0E7] = ('trigger', 'R2', 'filled')
    p[0xE004] = ('shoulder', 'L1', 'outline')
    p[0xE005] = ('shoulder', 'R1', 'outline')
    p[0xE0EF] = ('options', 'disc')
    p[0xE0F0] = ('create', 'disc')
    p[0xE0F1] = ('options', 'bare')
    p[0xE0F2] = ('create', 'bare')
    if menu != 'dualsense':
        look = menu.split('-', 1)[1]
        for code in (0xE0EF, 0xE0F1):
            p[code] = ('ds4btn', 'OPTIONS', look)
        for code in (0xE0F0, 0xE0F2):
            p[code] = ('ds4btn', 'SHARE', look)
    return p


# ---------------------------------------------------------------- colour (DualShock 4) styles

# Symbol colours. "deep" reads on a pale disc, "bright" on a dark disc or the game's dark panels.
DS4_DEEP = {'cross': (38, 104, 214), 'circle': (214, 40, 58), 'square': (196, 64, 170), 'triangle': (18, 150, 112)}
DS4_BRIGHT = {'cross': (100, 146, 208), 'circle': (216, 84, 92), 'square': (204, 116, 186), 'triangle': (56, 184, 146)}
DARK_DISC = (14, 15, 17)


def draw_color(kind, bbox, cell, outline_px, variant):
    """Return (rgb uint8 (h, w, 3), alpha float (h, w)) for one icon in a DualShock colour variant.

    variant 'pale': cream disc (white in the texture, tinted by the game), coloured symbol on it.
    variant 'dark': dark disc with a light rim, bright symbol.
    Non face-button icons stay white (the game tints them as before).
    """
    w, h = cell
    white = np.ones((h, w, 3), dtype=np.float32) * 255
    if kind[0] == 'ds4btn' and variant == 'dark':
        return _dark_ds4btn(kind[1], kind[2], bbox, cell, outline_px)
    if kind[0] == 'symbol':
        alpha, sym = draw(kind, bbox, cell, outline_px)
        c = np.array(DS4_BRIGHT[kind[1]], dtype=np.float32)
        rgb = np.ones((h, w, 3), dtype=np.float32) * c
        return np.clip(rgb + 0.5, 0, 255).astype(np.uint8), alpha
    if kind[0] in ('shoulder', 'trigger') and kind[2] == 'filled' and variant == 'dark':
        # Dark button with a light rim and a light label, like the dark face buttons.
        cut, label = draw(kind, bbox, cell, outline_px)
        whole = np.clip(cut + label, 0, 1)
        outline, _ = draw((kind[0], kind[1], 'outline'), bbox, cell, outline_px)
        rim = np.clip(outline - label, 0, 1)
        light = np.clip(rim + label, 0, 1)[..., None]
        rgb = np.array(DARK_DISC, dtype=np.float32) * (1 - light) + 255 * light
        return np.clip(rgb + 0.5, 0, 255).astype(np.uint8), whole
    if kind[0] != 'face':
        alpha, _ = draw(kind, bbox, cell, outline_px)
        return white.astype(np.uint8), alpha
    name, style = kind[1], kind[2]
    disc, sym = draw(('face', name, 'filled'), bbox, cell, outline_px)
    disc = np.maximum(disc, sym)            # whole button (symbol not cut out)
    if style == 'outline':
        ring_and_sym, sym = draw(('face', name, 'outline'), bbox, cell, outline_px)
        c = np.array(DS4_BRIGHT[name], dtype=np.float32)
        rgb = white * (1 - sym[..., None]) + c * sym[..., None]
        return np.clip(rgb + 0.5, 0, 255).astype(np.uint8), ring_and_sym
    if variant == 'pale':
        c = np.array(DS4_DEEP[name], dtype=np.float32)
        rgb = white * (1 - sym[..., None]) + c * sym[..., None]
        return np.clip(rgb + 0.5, 0, 255).astype(np.uint8), disc
    # dark: rim = disc minus the disc shrunk by the outline width
    ring, _ = draw(('face', name, 'outline'), bbox, cell, outline_px)
    ring = np.clip(ring - sym, 0, 1)
    c = np.array(DS4_BRIGHT[name], dtype=np.float32)
    dark = np.array(DARK_DISC, dtype=np.float32)
    rgb = dark * np.ones((h, w, 1), dtype=np.float32)
    rgb = rgb * (1 - ring[..., None]) + 255 * ring[..., None]
    rgb = rgb * (1 - sym[..., None]) + c * sym[..., None]
    return np.clip(rgb + 0.5, 0, 255).astype(np.uint8), disc


def _dark_ds4btn(word, look, bbox, cell, outline_px):
    """Dark SHARE / OPTIONS: dark pill with a cream rim under the word, or a dark label with cream rim and text."""
    w, h = cell
    x0, y0, x1, y1 = [v * SS for v in bbox]
    x1 += SS
    y1 += SS
    bw, bh = x1 - x0, y1 - y0
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    s = min(bw, bh)
    o = (outline_px or max(1.0, 0.065 * s / SS)) * SS
    outer, inner, label = _canvas(w, h), _canvas(w, h), _canvas(w, h)
    do, di, dl = ImageDraw.Draw(outer), ImageDraw.Draw(inner), ImageDraw.Draw(label)
    if look == 'pill':
        pw, ph = 0.34 * s, 0.58 * s
        top = cy - 0.04 * s
        do.rounded_rectangle([cx - pw / 2, top, cx + pw / 2, top + ph], radius=pw / 2, fill=255)
        di.rounded_rectangle([cx - pw / 2 + o, top + o, cx + pw / 2 - o, top + ph - o], radius=max(pw / 2 - o, 1), fill=255)
        _text(dl, word, cx, y0 + 0.5 * (top - y0) - 0.01 * s, 0.24 * s, 255, style=b'Bold Condensed', max_w=0.98 * bw)
    else:
        lh = 0.48 * s
        box = [x0, cy - lh / 2, x1, cy + lh / 2]
        do.rounded_rectangle(box, radius=0.14 * lh, fill=255)
        di.rounded_rectangle([box[0] + o, box[1] + o, box[2] - o, box[3] - o], radius=max(0.14 * lh - o, 1), fill=255)
        _text(dl, word, cx, cy, 0.56 * lh, 255, style=b'Bold Condensed', max_w=0.80 * bw)
    a_out, a_in, a_lab = _down(outer, w, h), _down(inner, w, h), _down(label, w, h)
    rim = np.clip(a_out - a_in, 0, 1)
    if look == 'pill':
        light = np.maximum(rim, a_lab)       # the word sits above the pill
        alpha = np.maximum(a_out, a_lab)
    else:
        light = np.clip(rim + a_lab * a_in, 0, 1)
        alpha = a_out
    rgb = np.array(DARK_DISC, dtype=np.float32) * (1 - light[..., None]) + 255 * light[..., None]
    return np.clip(rgb + 0.5, 0, 255).astype(np.uint8), alpha
