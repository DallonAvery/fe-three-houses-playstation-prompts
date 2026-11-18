"""Assemble the Three Houses GameBanana release folder (and archive it with 7-Zip).

  python package_th.py <variants_dir> <readme.txt> <out_dir> [--archive zip|7z]

variants_dir holds the build_th.py outputs named "PS Prompts - <style> [Circle|Cross]".
Files are hard-linked into the release folder when possible (same drive), so it costs no extra space.
"""
import argparse
import hashlib
import os
import shutil
import subprocess
import zipfile
from pathlib import Path

ROOT = 'FE Three Houses - PlayStation Prompts'
STYLES = [('DualSense', 'DualSense'), ('DS4 Light Label', 'DS4 Light, Label'), ('DS4 Light Pill', 'DS4 Light, Pill'),
          ('DS4 Dark Label', 'DS4 Dark, Label'), ('DS4 Dark Pill', 'DS4 Dark, Pill')]
GROUPS = [('Circle', 'Circle confirms (emulator default)'), ('Cross', 'Cross confirms (remapped)')]
SEVEN_ZIP = r'C:\Program Files\7-Zip\7z.exe'


def md5(p):
    h = hashlib.md5()
    with open(p, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def place(src, dst):
    dst.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.link(src, dst)
    except OSError:
        shutil.copy2(src, dst)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('variants', type=Path)
    ap.add_argument('readme', type=Path)
    ap.add_argument('out', type=Path)
    ap.add_argument('--archive', choices=['zip', '7z', 'none'], default='7z')
    a = ap.parse_args()
    a.out = a.out.resolve()     # 7-Zip runs inside out_dir, so every path handed to it must be absolute
    top = a.out / ROOT
    if top.exists():
        shutil.rmtree(top)
    expected = {}
    for tag, group in GROUPS:
        for key, label in STYLES:
            src = a.variants / ('PS Prompts - %s [%s]' % (key, tag))
            assert (src / 'romfs' / 'patch4' / 'INFO2.bin').exists(), src
            dst = top / group / ('PS Prompts - %s [%s]' % (label, tag))
            for f in sorted((src / 'romfs').rglob('*')):
                if f.is_file():
                    d = dst / f.relative_to(src)
                    place(f, d)
                    expected[d.relative_to(a.out).as_posix()] = md5(f)
    place(a.readme, top / 'README.txt')
    expected[(top / 'README.txt').relative_to(a.out).as_posix()] = md5(a.readme)
    for f in sorted((Path(__file__).resolve().parent / 'installer').glob('PS Prompts Installer.*')):
        shutil.copy2(f, top / f.name)
        expected[(top / f.name).relative_to(a.out).as_posix()] = md5(f)
    print('release folder:', len(expected), 'files')

    if a.archive == 'none':
        return
    arc = a.out / (ROOT + '.' + a.archive)
    if arc.exists():
        arc.unlink()
    if a.archive == 'zip':
        with zipfile.ZipFile(arc, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as z:
            for p in sorted(top.rglob('*')):
                if p.is_file():
                    z.write(p, p.relative_to(a.out).as_posix())
    else:
        # one solid LZMA2 stream with a dictionary bigger than a whole variant, so the near-identical
        # archives (12 language copies x 10 variants) are stored once plus their differences
        subprocess.run([SEVEN_ZIP, 'a', '-t7z', '-mx=9', '-m0=lzma2', '-md=256m', '-ms=on', '-mmt=2', '-bd',
                        str(arc), ROOT], cwd=a.out, check=True, stdout=subprocess.DEVNULL)
    print('archive', arc, round(arc.stat().st_size / 1e6, 1), 'MB')

    # verify: extract to a temp folder and compare every file's hash
    check = a.out / '_verify'
    if check.exists():
        shutil.rmtree(check)
    if a.archive == 'zip':
        with zipfile.ZipFile(arc) as z:
            z.extractall(check)
    else:
        subprocess.run([SEVEN_ZIP, 'x', '-bd', '-y', '-o' + str(check), str(arc)], check=True, stdout=subprocess.DEVNULL)
    got = {p.relative_to(check).as_posix(): md5(p) for p in check.rglob('*') if p.is_file()}
    assert got == expected, 'archive contents differ from the release folder'
    shutil.rmtree(check)
    print('verified', len(got), 'files')


if __name__ == '__main__':
    main()
