"""Build every Three Houses variant and the release archive in one go.

  python tools/build_all.py --romfs <your 1.2.0 RomFS dump> [--out build] [--archive 7z|zip|none]

Produces, under --out:
  variants/PS Prompts - <style> [Circle|Cross]/romfs/...   10 complete mods
  FE Three Houses - PlayStation Prompts/  and the .7z      (via package_th.py, with the README and installer)
Each variant is about 220 MB; the solid .7z of all ten is about 6 MB. Needs 7-Zip for --archive 7z.
"""
import argparse
import subprocess
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
REPO = TOOLS.parent
# folder name -> (build_th.py --style, --menu)
STYLES = {
    'DualSense': ('dualsense', 'dualsense'),
    'DS4 Light Label': ('dualshock-pale', 'ds4-label'),
    'DS4 Light Pill': ('dualshock-pale', 'ds4-pill'),
    'DS4 Dark Label': ('dualshock-dark', 'ds4-label'),
    'DS4 Dark Pill': ('dualshock-dark', 'ds4-pill'),
}
# Circle: buttons by position (emulator default). Cross: the same with only A/B swapped.
LAYOUTS = {'Circle': 'circle-confirm', 'Cross': 'cross-swap'}


def run(args):
    print('>', ' '.join(str(a) for a in args[1:]), flush=True)
    subprocess.run([sys.executable] + [str(a) for a in args], check=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--romfs', required=True, help='RomFS dump of Three Houses with the 1.2.0 update')
    ap.add_argument('--out', type=Path, default=REPO / 'build')
    ap.add_argument('--archive', choices=['7z', 'zip', 'none'], default='7z')
    a = ap.parse_args()
    out = a.out.resolve()
    variants = out / 'variants'
    for tag, layout in LAYOUTS.items():
        for name, (style, menu) in STYLES.items():
            run([TOOLS / 'build_th.py', '--romfs', a.romfs, '--layout', layout, '--style', style, '--menu', menu,
                 '--out', variants / ('PS Prompts - %s [%s]' % (name, tag))])
    run([TOOLS / 'package_th.py', variants, REPO / 'release' / 'README.txt', out, '--archive', a.archive])


if __name__ == '__main__':
    main()
