"""Rewrite Nintendo button names in Fire Emblem: Three Houses text, in every language.

Text archives (msgdata.bin = entry 0, scrdata.bin = entry 1, tuscrdata.bin = entry 3, the Guide pages) are:
  u32 count, then count x (u32 offset, u32 size)  -> one block per language:
    0 JP, 1 EN (US), 2 EN (EU), 3 DE, 4 FR (EU), 5 FR (CA), 6 ES (EU), 7 ES (LA), 8 IT, 9 KO, 10 ZH-T, 11 ZH-S
  a block is the same container again, holding "XL" tables
  XL table: "XL" u16 ver, u16 size&0xffff, u16 ?, u16 rows, u16 row size, u32 header size (0x14), u32,
            rows x u32 string offset (relative to the end of the header), then the NUL-terminated UTF-8 strings.
Only tables with 4-byte rows (plain string lists) are touched. Strings are edited in place in the pool and every
row offset is moved by the size change before it, so nothing else in the table shifts meaning.
The battle tips are separate small string lists, one entry per language (see LISTS and patch_list).

Two text styles:
  glyphs  "the A Button" -> "the <icon> Button", "Ａボタン" -> "<icon>ボタン", "bouton A" -> "bouton <icon>"...
          ESC 'P' <code> draws a button icon from font atlas 72, which the mod has already redrawn as
          PlayStation icons. Codes (read off an in-game test page):
            0-3 A B X Y, 4-6 d-pad, 7 8 9 A left right up down, B C D E L R ZL ZR, F G stick press,
            H I + -, J K sticks, L capture, M N SL SR, O HOME, P Q play/pause; R and up are not icons.
  words   English only: "the A Button" -> "the Circle Button" etc. (depends on the confirm layout)
"""
import re
import struct

import psglyphs

LANGS = ['JP', 'EN', 'EN-EU', 'DE', 'FR', 'FR-CA', 'ES', 'ES-LA', 'IT', 'KO', 'ZH-T', 'ZH-S']
ENGLISH = (1, 2)
# battle tips, one string list per language in LANGS order (Japanese sits apart from the others)
LISTS = [8641] + [10754 + 1803 * k for k in range(11)]
CODE = {'A': '0', 'B': '1', 'X': '2', 'Y': '3', 'L': 'B', 'R': 'C', 'ZL': 'D', 'ZR': 'E', '+': 'H', '-': 'I'}
FULLWIDTH = {'Ａ': 'A', 'Ｂ': 'B', 'Ｘ': 'X', 'Ｙ': 'Y', 'Ｌ': 'L', 'Ｒ': 'R', 'ＺＬ': 'ZL', 'ＺＲ': 'ZR',
             '＋': '+', '－': '-'}
WORDS = {'cross': 'Cross', 'circle': 'Circle', 'square': 'Square', 'triangle': 'Triangle'}
SHOULDER = {'L': 'L1', 'R': 'R1', 'ZL': 'L2', 'ZR': 'R2'}

_W = 'A-Za-z0-9Ａ-Ｚａ-ｚÀ-ɏ'
BTN = r'(?<![%s])(ZL|ZR|ＺＬ|ＺＲ|[ABXYLR]|[ＡＢＸＹＬＲ])(?![%s])' % (_W, _W)
CJK_WORD = r'(ボタン|按鍵|按键|鍵|键|버튼)'


DS4_WORDS = {'+': 'Options', '-': 'Share'}   # title case: all caps dominated the line in-game


def _icon(btn, menu='dualsense'):
    """Inline icon. DS4 menus spell OPTIONS / SHARE instead: their icons (a word on a tiny button) are
    unreadable at text size, and those are the names printed on the controller."""
    btn = FULLWIDTH.get(btn, btn)
    if menu != 'dualsense' and btn in DS4_WORDS:
        return DS4_WORDS[btn]
    return '\x1bP' + CODE[btn]


def _name(btn, layout, text):
    btn = FULLWIDTH.get(btn, btn)
    if text == 'glyphs':
        return _icon(btn)
    if btn in SHOULDER:
        return SHOULDER[btn]
    return WORDS[psglyphs.LAYOUTS[layout][btn]]


def _english(layout, text, menu):
    minus = 'Create' if menu == 'dualsense' else 'Share'
    btn = r'\b(ZL|ZR|A|B|X|Y|L|R)'

    def n(b):
        return _icon(b, menu) if text == 'glyphs' else _name(b, layout, text)

    return [
        (re.compile(btn + r'/' + btn + r' Buttons\b'), lambda m: n(m[1]) + '/' + n(m[2]) + ' Buttons'),
        (re.compile(btn + r'( Button\b)'), lambda m: n(m[1]) + m[2]),      # "the A Button" (not "A button that")
        (re.compile(r'\bPress A( to )'), lambda m: 'Press ' + n('A') + m[1]),
        (re.compile(r'^(ZL|ZR)(: )'), lambda m: n(m[1]) + m[2]),
        (re.compile(r'\+/- Buttons\b'), lambda m: (n('+') + '/' + n('-') if text == 'glyphs'
                                                   else 'Options/' + minus) + ' Buttons'),
        (re.compile(r'\bR Stick\b'), lambda m: 'Right Stick'),
        (re.compile(r'\bL Stick\b'), lambda m: 'Left Stick'),
    ]


def _other_languages(menu):
    def i(b):
        return _icon(b, menu)
    return [
        # Japanese / Chinese / Korean: "Ａボタン", "按Ａ鍵", "A 버튼", "Ｂ／Ｙボタン", "＋／－鍵", "+ / - 버튼"
        (re.compile(BTN + r'(\s*[/／]\s*)' + BTN + r'(\s?)' + CJK_WORD),
         lambda m: i(m[1]) + m[2] + i(m[3]) + m[4] + m[5]),
        (re.compile(r'([+＋])(\s*[/／]\s*)([-－])(\s?)' + CJK_WORD),
         lambda m: i(m[1]) + m[2] + i(m[3]) + m[4] + m[5]),
        (re.compile(BTN + r'(\s?)' + CJK_WORD), lambda m: i(m[1]) + m[2] + m[3]),
        (re.compile(r'(?<![RL])([RＲ])(スティック|操控搖桿|操控摇杆)'), lambda m: '右' + m[2]),
        (re.compile(r'(?<![RL])([LＬ])(スティック|操控搖桿|操控摇杆)'), lambda m: '左' + m[2]),
        (re.compile(r'(?<![A-Za-z])R 스틱'), lambda m: '오른쪽 스틱'),
        (re.compile(r'(?<![A-Za-z])L 스틱'), lambda m: '왼쪽 스틱'),
        # German: "A-Knopf", "L-Taste", "Plus-Knopf/Minus-Knopf"
        (re.compile(BTN + r'-(Knopf|Knopfes|Knöpfe|Taste|Tasten)\b'), lambda m: i(m[1]) + '-' + m[2]),
        (re.compile(r'\bPlus-(Knopf|Taste)\b'), lambda m: i('+') + '-' + m[1]),
        (re.compile(r'\bMinus-(Knopf|Taste)\b'), lambda m: i('-') + '-' + m[1]),
        # French / Spanish / Italian: "bouton A", "Boutons B ou Y", "Botones + y -", "Pulsanti B/Y"
        (re.compile(r'\b(Boutons|boutons|Botones|botones|Pulsanti|pulsanti)(\s+)' + BTN +
                    r'(\s*/\s*|\s+(?:ou|o|e|y)\s+)' + BTN),
         lambda m: m[1] + m[2] + i(m[3]) + m[4] + i(m[5])),
        (re.compile(r'\b(Boutons|boutons|Botones|botones|Pulsanti|pulsanti)(\s+)\+(\s*/\s*|\s+(?:ou|o|e|y)\s+)-'),
         lambda m: m[1] + m[2] + i('+') + m[3] + i('-')),
        (re.compile(r'\b(bouton|Bouton|botón|Botón|pulsante|Pulsante)(\s+)' + BTN), lambda m: m[1] + m[2] + i(m[3])),
        (re.compile(r'\b([Aa]ppuyez(?: à nouveau)?\s+sur\s+)' + BTN), lambda m: m[1] + i(m[2])),
        # menu hints that start with the button: "ZL: ...", "ZL : ...", "ZL：..."
        (re.compile(r'^' + BTN + r'(\s?[:：])'), lambda m: i(m[1]) + m[2]),
    ]


def rules(layout, text, menu, everywhere=True):
    rs = _english(layout, text, menu)
    if text == 'glyphs' and everywhere:
        rs += _other_languages(menu)
    return rs


def _apply(s, rs):
    u = s.decode('utf-8', 'surrogateescape')
    new = u
    for rx, fn in rs:
        new = rx.sub(fn, new)
    return s if new == u else new.encode('utf-8', 'surrogateescape')


def _container(data):
    n, = struct.unpack_from('<I', data, 0)
    v = struct.unpack_from('<%dI' % (2 * n), data, 4)
    return n, [data[v[2 * k]:v[2 * k] + v[2 * k + 1]] for k in range(n)]


def _pack(parts, first):
    """Rebuild a container: offsets start at `first` and each part is 4-byte aligned."""
    head = struct.pack('<I', len(parts))
    pos = first
    body = b''
    table = []
    for p in parts:
        pad = (-pos) % 4
        body += b'\0' * pad
        pos += pad
        table += [pos, len(p)]
        body += p
        pos += len(p)
    return head + struct.pack('<%dI' % len(table), *table) + body


def _first_offset(data):
    return struct.unpack_from('<I', data, 4)[0]


def _patch_table(t, rs):
    assert t[:2] == b'XL'
    rows, rowsize = struct.unpack_from('<HH', t, 8)
    hdr, = struct.unpack_from('<I', t, 12)
    if rowsize != 4:
        return t, []
    offs = list(struct.unpack_from('<%dI' % rows, t, hdr))
    pool_start = hdr + 4 * rows
    pool = t[pool_start:]
    base = pool_start - hdr                     # row offsets are relative to the header end
    starts = sorted(set(offs))
    new_pool = bytearray()
    remap = {}
    changes = []
    pos = 0
    for o in starts:
        s0 = o - base
        if s0 < pos:                            # shares a tail with an earlier string; keep it pointing there
            continue
        new_pool += pool[pos:s0]
        end = pool.index(b'\0', s0)
        s = pool[s0:end]
        new = _apply(s, rs)
        remap[o] = base + len(new_pool)
        new_pool += new
        if new != s:
            changes.append((s, new))
        pos = end
    new_pool += pool[pos:]
    if not changes:
        return t, []

    def moved(o):
        if o in remap:
            return remap[o]
        # an offset into the middle of a string: shift by the growth before that string
        prev = max(k for k in remap if k <= o)
        return remap[prev] + (o - prev)

    out = bytearray(t[:hdr]) + struct.pack('<%dI' % rows, *[moved(o) for o in offs]) + new_pool
    struct.pack_into('<H', out, 4, len(out) & 0xffff)
    return bytes(out), changes


def icon_test_rule():
    """Diagnostic: turn the Danger Radius guide page into a table of every ESC P code."""
    def row(chars):
        return '  '.join(c + ':\x1bP' + c for c in chars)
    test = 'Icon code test\n' + '\n'.join([row('0123456789'), row('ABCDEFGHI'), row('JKLMNOPQ'), row('RSTUVWXYZ')])
    return (re.compile(r'^Press the ZR Button to toggle a danger area for all enemy units\.$'), lambda m: test)


def patch(data, layout='circle-confirm', text='glyphs', menu='dualsense', extra=()):
    """Return (new archive bytes, [(language block, old, new)])."""
    rs = list(extra) + rules(layout, text, menu)
    n, blocks = _container(data)
    all_changes = []
    for b in (range(n) if text == 'glyphs' else ENGLISH):
        bn, tables = _container(blocks[b])
        new_tables = []
        for t in tables:
            nt, ch = _patch_table(t, rs)
            new_tables.append(nt)
            all_changes += [(b,) + c for c in ch]
        blocks[b] = _pack(new_tables, _first_offset(blocks[b]))
    return _pack(blocks, _first_offset(data)), all_changes


def strings(data, block=1):
    """All strings of one language block, for checking."""
    out = []
    _, tables = _container(_container(data)[1][block])
    for t in tables:
        rows, rowsize = struct.unpack_from('<HH', t, 8)
        hdr, = struct.unpack_from('<I', t, 12)
        if rowsize != 4:
            out.append(None)
            continue
        offs = struct.unpack_from('<%dI' % rows, t, hdr)
        out.append([t[hdr + o:t.index(b'\0', hdr + o)] for o in offs])
    return out


def patch_list(data, layout='circle-confirm', text='glyphs', menu='dualsense'):
    """Small per-language string lists (e.g. entries 10754/12557, battle tips):
    u32 1, u32 1, u32 table offset (0x20), u32 table size padded to 16, u32 string count n, then at the table
    offset n+1 u32 offsets (the last is the pool size) relative to the pool, which follows the padded table."""
    rs = rules(layout, text, menu)
    one, _, toff, tsize, n = struct.unpack_from('<5I', data, 0)
    assert one == 1 and toff == 0x20, 'unexpected string list header'
    offs = struct.unpack_from('<%dI' % (n + 1), data, toff)
    base = toff + tsize
    pool = data[base:]
    assert offs[-1] == len(pool) and list(offs) == sorted(offs)
    new_pool, new_offs, changes = b'', [], []
    for k in range(n):
        s = pool[offs[k]:offs[k + 1]]
        body = s.rstrip(b'\0')
        new = _apply(body, rs)
        if new != body:
            changes.append((body, new))
        new_offs.append(len(new_pool))
        new_pool += new + s[len(body):]
    new_offs.append(len(new_pool))
    head = bytearray(data[:base])
    struct.pack_into('<%dI' % (n + 1), head, toff, *new_offs)
    return bytes(head) + new_pool, changes
