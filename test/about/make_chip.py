# 宇野の名札(ENGINEER)の絵: 「U」の字を配線にした半導体チップ。名札の枠(4:3)を基板に見立てる。
#   python test/about/make_chip.py            -> test/about/out/chip-inline.svg(about.html に差し込む分) と assets/about/uno-chip.svg(単体)
# 色は class で塗る。about.html 側は CSS 変数で(明るい/暗い画面の両方)、単体の SVG は <style> に明るい画面の色を書く。
# 配線は pathLength="1" にしてあるので、JS は stroke-dashoffset 1 -> 0 で「引かれていく」動きにできる。
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..', '..'))

W, H = 400, 300
BX, BY, BS = 130, 80, 140          # チップの胴(正方形)
PITCH, NPIN, PL = 20, 6, 12        # ピンの間隔・本数・長さ
pins = [BX + BS / 2 + (i - (NPIN - 1) / 2) * PITCH for i in range(NPIN)]    # 上下のピンの x: 150..250
pins_y = [BY + BS / 2 + (i - (NPIN - 1) / 2) * PITCH for i in range(NPIN)]  # 左右のピンの y: 100..200


def f(v):
    return ('%.1f' % v).rstrip('0').rstrip('.')


def path(pts):
    return 'M' + ' L'.join('%s %s' % (f(x), f(y)) for x, y in pts)


traces, vias, sigs = [], [], []

# 上下: ピンからまっすぐ出て、外側のピンほど大きく斜めに振って、枠の外へ
for side, y0, dy in (('t', BY - PL, -1), ('b', BY + BS + PL, 1)):
    for i, x in enumerate(pins):
        s = (i - (NPIN - 1) / 2) * 30
        yb = y0 + dy * 12
        pts = [(x, y0), (x, yb), (x + s, yb + dy * abs(s)), (x + s, (-12 if dy < 0 else H + 12))]
        traces.append(pts)
        if i in (1, 4) and side == 't' or i in (0, 3) and side == 'b':
            sigs.append(pts)

# 左右: ピンから横へ出て、上下に振って、枠の外へ。2本は途中のビアで止める
for side, x0, dx in (('l', BX - PL, -1), ('r', BX + BS + PL, 1)):
    for i, y in enumerate(pins_y):
        k = i - (NPIN - 1) / 2
        s = k * 26
        xb = x0 + dx * 14
        end_x = -12 if dx < 0 else W + 12
        if (side, i) in (('l', 1), ('r', 4)):
            stop = xb + dx * (abs(s) + 30)
            pts = [(x0, y), (xb, y), (xb + dx * abs(s), y + s), (stop, y + s)]
            vias.append(pts[-1])
        else:
            pts = [(x0, y), (xb, y), (xb + dx * abs(s), y + s), (end_x, y + s)]
        traces.append(pts)
        if (side, i) in (('l', 0), ('l', 4), ('r', 1), ('r', 5)):
            sigs.append(pts)

# 胴の上の「U」: 太い線と、内側に細い線をもう1本(45度の角で曲げる)
cx = BX + BS / 2


def u_path(half, top, bottom, ch):
    return [(cx - half, top), (cx - half, bottom - ch), (cx - half + ch, bottom),
            (cx + half - ch, bottom), (cx + half, bottom - ch), (cx + half, top)]


U_OUT = u_path(32, 110, 184, 18)
U_IN = u_path(17, 118, 168, 10)

pin_rects = []
for x in pins:
    pin_rects.append((x - 4, BY - PL, 8, PL))
    pin_rects.append((x - 4, BY + BS, 8, PL))
for y in pins_y:
    pin_rects.append((BX - PL, y - 4, PL, 8))
    pin_rects.append((BX + BS, y - 4, PL, 8))


def svg(extra_attrs='', style=''):
    o = []
    o.append('<svg class="mark-chip" viewBox="0 0 %d %d" preserveAspectRatio="xMidYMid slice"%s>' % (W, H, extra_attrs))
    if style:
        o.append('<style>%s</style>' % style)
    o.append('<defs><filter id="chip-glow" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="6" /></filter></defs>')
    o.append('<g class="pcb-g">' + ''.join('<path class="pcb" pathLength="1" d="%s" />' % path(p) for p in traces) + '</g>')
    o.append('<g class="via-g">' + ''.join('<circle class="via" cx="%s" cy="%s" r="4.5" />' % (f(x), f(y)) for x, y in vias) + '</g>')
    o.append('<g class="sig-g">' + ''.join(
        '<path class="sig" pathLength="1" style="--d:%.1fs;--delay:%.2fs" d="%s" />' % (2.2 + (i * 0.37) % 1.4, (i * 0.61) % 2.4, path(p))
        for i, p in enumerate(sigs)) + '</g>')
    o.append('<g class="chip-pins">' + ''.join('<rect class="chip-pin" x="%s" y="%s" width="%s" height="%s" />' % tuple(f(v) for v in r) for r in pin_rects) + '</g>')
    o.append('<g class="chip-core">')
    o.append('<rect class="chip-body" x="%d" y="%d" width="%d" height="%d" />' % (BX, BY, BS, BS))
    o.append('<rect class="chip-die" x="%d" y="%d" width="%d" height="%d" />' % (BX + 12, BY + 12, BS - 24, BS - 24))
    o.append('<circle class="chip-dot" cx="%d" cy="%d" r="4" />' % (BX + 22, BY + 22))
    o.append('<path class="chip-u-glow" d="%s" filter="url(#chip-glow)" />' % path(U_OUT))
    o.append('<path class="chip-u" pathLength="1" d="%s" />' % path(U_OUT))
    o.append('<path class="chip-u2" pathLength="1" d="%s" />' % path(U_IN))
    for (x, y) in (U_OUT[0], U_OUT[-1]):
        o.append('<circle class="chip-pad" cx="%s" cy="%s" r="8" /><circle class="chip-hole" cx="%s" cy="%s" r="3" />' % (f(x), f(y), f(x), f(y)))
    o.append('</g>')
    o.append('</svg>')
    return ''.join(o)


# 単体の SVG(明るい画面の色で固定。背景は透明)
STANDALONE_STYLE = '''
.pcb{fill:none;stroke:#b8a794;stroke-width:3;stroke-linecap:round;stroke-linejoin:round}
.via{fill:#f6ecdd;stroke:#b8a794;stroke-width:2.5}
.sig{fill:none;stroke:#ff7a45;stroke-width:3.4;stroke-linecap:round;stroke-dasharray:.07 .93;stroke-dashoffset:1;animation:sig var(--d) linear var(--delay) infinite}
.chip-pin{fill:#8a7663}
.chip-body{fill:#251a16}
.chip-die{fill:none;stroke:#f6ecdd;stroke-opacity:.18;stroke-width:1.5}
.chip-dot{fill:#f6ecdd;fill-opacity:.35}
.chip-u,.chip-u-glow{fill:none;stroke:#ff7a45;stroke-width:11;stroke-linejoin:miter;stroke-linecap:butt}
.chip-u-glow{stroke-width:18;opacity:.35;animation:glow 2.8s ease-in-out infinite}
.chip-u2{fill:none;stroke:#ff7a45;stroke-width:3;stroke-opacity:.7}
.chip-pad{fill:#ff7a45}.chip-hole{fill:#251a16}
@keyframes sig{from{stroke-dashoffset:1}to{stroke-dashoffset:0}}
@keyframes glow{0%,100%{opacity:.18}50%{opacity:.5}}
@media (prefers-reduced-motion:reduce){.sig{animation:none;opacity:0}.chip-u-glow{animation:none}}
'''.replace('\n', '')

os.makedirs(os.path.join(HERE, 'out'), exist_ok=True)
open(os.path.join(HERE, 'out', 'chip-inline.svg'), 'w', encoding='utf-8').write(svg(' aria-hidden="true" focusable="false"'))
open(os.path.join(ROOT, 'assets', 'about', 'uno-chip.svg'), 'w', encoding='utf-8').write(
    svg(' xmlns="http://www.w3.org/2000/svg"', STANDALONE_STYLE).replace('<svg class="mark-chip"', '<svg'))
print('traces', len(traces), 'vias', len(vias), 'signals', len(sigs))
