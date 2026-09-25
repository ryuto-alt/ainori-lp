"""ロゴ(assets/pilot/brand-logo.png)の輪郭をなぞって SVG の <symbol> にする。about.html の冒頭などで使う。

元の PNG はアルファが 0/255 の二値で縁がギザギザなので、拡大してそのまま使うと粗い。
部品(左の人の頭・体、右の人の頭・体、お椀、湯気3本、文字)ごとに輪郭を取り、
ぼかし → 8倍に拡大 → しきい値 で細かい輪郭を拾い、なめらかな3次ベジェにする。
形は描き直さず元の画素の輪郭をなぞるだけなので、ブランドの形は変わらない。

使い方: python test/about/trace_logo.py  → test/about/out/logo_symbols.svg と比較用の PNG
"""
import json
import math
import os
import sys

import cv2
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
SRC = os.path.join(ROOT, 'assets', 'pilot', 'brand-logo.png')
OUT = os.path.join(HERE, 'out')
UP = 8          # 輪郭を拾う細かさ(元の画素の 1/8)


def load():
    im = cv2.imread(SRC, cv2.IMREAD_UNCHANGED)
    return im, (im[:, :, 3] > 0).astype(np.uint8)


def contours_of(mask):
    """二値マスク → 小数点つき座標の輪郭(外側と穴)。"""
    m = cv2.GaussianBlur(mask.astype(np.float32), (0, 0), 0.9)
    big = cv2.resize(m, None, fx=UP, fy=UP, interpolation=cv2.INTER_CUBIC)
    binm = (big > 0.5).astype(np.uint8)
    cs, _ = cv2.findContours(binm, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)
    out = []
    for c in cs:
        if len(c) < 12:
            continue
        pts = c[:, 0, :].astype(np.float64)
        # 画素の角の分だけずれるので半画素戻す
        pts = (pts + 0.5) / UP - 0.5
        out.append(pts)
    return out


def smooth(pts, sigma):
    """輪郭に沿ってガウスでならす(元の画素の単位で sigma)。ギザギザの名残を消す。閉じた輪なので端は回り込む。"""
    n = len(pts)
    # pts は元の画素単位だが、点は 1/UP 画素ごとに並んでいるので、点の数で見た sigma は UP 倍
    sp = max(1.0, sigma * UP)
    r = int(sp * 3)
    if n < r * 2 + 4:
        return pts
    x = np.arange(-r, r + 1)
    ker = np.exp(-x * x / (2 * sp * sp)); ker /= ker.sum()
    xs = np.convolve(np.r_[pts[-r:, 0], pts[:, 0], pts[:r, 0]], ker, mode='same')[r:-r]
    ys = np.convolve(np.r_[pts[-r:, 1], pts[:, 1], pts[:r, 1]], ker, mode='same')[r:-r]
    return np.stack([xs, ys], 1)


def simplify(pts, eps):
    c = pts.reshape(-1, 1, 2).astype(np.float32)
    s = cv2.approxPolyDP(c, eps, True)[:, 0, :].astype(np.float64)
    return s


def to_path(pts):
    """閉じた点列 → 求心的 Catmull-Rom(Yuksel の係数)を3次ベジェに直した path。
    点の間隔がばらついても膨らみ・尖りが出にくい。"""
    n = len(pts)
    f = lambda v: ('%.2f' % v).rstrip('0').rstrip('.')
    d = ['M%s %s' % (f(pts[0][0]), f(pts[0][1]))]
    for i in range(n):
        p0, p1, p2, p3 = pts[(i - 1) % n], pts[i], pts[(i + 1) % n], pts[(i + 2) % n]
        d1 = max(np.linalg.norm(p1 - p0), 1e-6) ** 0.5
        d2 = max(np.linalg.norm(p2 - p1), 1e-6) ** 0.5
        d3 = max(np.linalg.norm(p3 - p2), 1e-6) ** 0.5
        c1 = (d1 * d1 * p2 - d2 * d2 * p0 + (2 * d1 * d1 + 3 * d1 * d2 + d2 * d2) * p1) / (3 * d1 * (d1 + d2))
        c2 = (d3 * d3 * p1 - d2 * d2 * p3 + (2 * d3 * d3 + 3 * d3 * d2 + d2 * d2) * p2) / (3 * d3 * (d3 + d2))
        d.append('C%s %s %s %s %s %s' % (f(c1[0]), f(c1[1]), f(c2[0]), f(c2[1]), f(p2[0]), f(p2[1])))
    d.append('Z')
    return ''.join(d)


def circle_path(mask):
    """頭は円。輪郭の点から最小二乗で円を当てる。"""
    pts = contours_of(mask)[0]
    x, y = pts[:, 0], pts[:, 1]
    A = np.c_[2 * x, 2 * y, np.ones(len(x))]
    cx, cy, c = np.linalg.lstsq(A, x * x + y * y, rcond=None)[0]
    r = math.sqrt(c + cx * cx + cy * cy)
    f = lambda v: ('%.2f' % v).rstrip('0').rstrip('.')
    return 'M%s %sa%s %s 0 1 0 %s 0a%s %s 0 1 0 %s 0Z' % (f(cx - r), f(cy), f(r), f(r), f(2 * r), f(r), f(r), f(-2 * r)), (cx, cy, r)


def capsule_path(mask):
    """湯気は角の丸い棒。向きと長さと太さを当てる。"""
    pts = contours_of(mask)[0].astype(np.float32)
    (cx, cy), (w, h), ang = cv2.minAreaRect(pts)
    if w < h:
        w, h = h, w; ang += 90
    t = math.radians(ang)
    ux, uy = math.cos(t), math.sin(t)
    half = w / 2 - h / 2
    ax, ay = cx - ux * half, cy - uy * half
    bx, by = cx + ux * half, cy + uy * half
    r = h / 2
    nx, ny = -uy * r, ux * r
    f = lambda v: ('%.2f' % v).rstrip('0').rstrip('.')
    return ('M%s %sL%s %sA%s %s 0 0 0 %s %sL%s %sA%s %s 0 0 0 %s %sZ' % (
        f(ax + nx), f(ay + ny), f(bx + nx), f(by + ny), f(r), f(r), f(bx - nx), f(by - ny),
        f(ax - nx), f(ay - ny), f(r), f(r), f(ax + nx), f(ay + ny)))


def path_for(mask, sigma, eps):
    parts = []
    for pts in contours_of(mask):
        s = smooth(pts, sigma)
        s = simplify(s, eps)
        if len(s) >= 4:
            parts.append(to_path(s))
    return ''.join(parts)


def main():
    im, alpha = load()
    H, W = alpha.shape
    n, lab, st, cen = cv2.connectedComponentsWithStats(alpha, connectivity=8)
    comps = [i for i in range(1, n) if st[i][4] > 30]
    mark = [i for i in comps if cen[i][0] < W * 0.32]
    word = [i for i in comps if cen[i][0] >= W * 0.32]

    def color(i):
        m = lab == i
        return tuple(int(im[:, :, k][m].mean()) for k in (2, 1, 0))

    mx0 = min(st[i][0] for i in mark); mx1 = max(st[i][0] + st[i][2] for i in mark)
    mid = (mx0 + mx1) / 2
    groups = {'head-l': [], 'body-l': [], 'head-r': [], 'body-r': [], 'bowl': [], 'steam': []}
    for i in mark:
        x, y, w, h, area = st[i]
        r, g, b = color(i)
        red = r > 150 and g < 110
        centre = abs(cen[i][0] - mid) < (mx1 - mx0) * 0.2
        if red and centre and cen[i][1] > H / 2:
            groups['bowl'].append(i)
        elif not red and centre and area < 6000:
            groups['steam'].append(i)
        else:
            side = 'l' if cen[i][0] < mid else 'r'
            groups[('head-' if h < 120 and w < 120 else 'body-') + side].append(i)
    groups['steam'].sort(key=lambda i: cen[i][0])
    for k, v in groups.items():
        print(k, [(int(st[i][0]), int(st[i][1]), int(st[i][2]), int(st[i][3])) for i in v], [color(i) for i in v])

    symbols = {}
    circles = {}
    for k in ('head-l', 'head-r'):
        symbols[k], circles[k] = circle_path(np.isin(lab, groups[k]).astype(np.uint8))
    for k in ('body-l', 'body-r', 'bowl'):
        symbols[k] = path_for(np.isin(lab, groups[k]).astype(np.uint8), 2.2, 0.09)
    for j, i in enumerate(groups['steam']):
        symbols['steam-%d' % j] = capsule_path((lab == i).astype(np.uint8))
    print('circles', circles)

    # 文字: 和文(上段)と欧文(下段)に分ける。細い筆の払いがあるので、なめらかにしすぎない
    wy = [cen[i][1] for i in word]
    split_y = 300
    ja = [i for i in word if cen[i][1] < split_y]
    en = [i for i in word if cen[i][1] >= split_y]
    # 文字はなぞらない(筆の細部で点が膨らむ)。縮めて使うので元の PNG で足りる。位置だけ boxes に残す

    # 部品ごとの外接矩形(動かすときの中心に使う)
    boxes = {}
    for k, v in groups.items():
        if k == 'steam':
            for j, i in enumerate(v):
                x, y, w, h, _ = st[i]; boxes['steam-%d' % j] = [int(x), int(y), int(w), int(h)]
        else:
            xs = [st[i][0] for i in v] + [st[i][0] + st[i][2] for i in v]
            ys = [st[i][1] for i in v] + [st[i][1] + st[i][3] for i in v]
            boxes[k] = [int(min(xs)), int(min(ys)), int(max(xs) - min(xs)), int(max(ys) - min(ys))]
    for name, ids in (('word-ja', ja), ('word-en', en)):
        xs = [st[i][0] for i in ids] + [st[i][0] + st[i][2] for i in ids]
        ys = [st[i][1] for i in ids] + [st[i][1] + st[i][3] for i in ids]
        boxes[name] = [int(min(xs)), int(min(ys)), int(max(xs) - min(xs)), int(max(ys) - min(ys))]

    os.makedirs(OUT, exist_ok=True)
    sym = ['<svg xmlns="http://www.w3.org/2000/svg" width="0" height="0" style="position:absolute" aria-hidden="true" focusable="false">']
    for k, d in symbols.items():
        sym.append('<symbol id="lg-%s" viewBox="0 0 %d %d" overflow="visible"><path d="%s"/></symbol>' % (k, W, H, d))
    sym.append('</svg>')
    open(os.path.join(OUT, 'logo_symbols.svg'), 'w', encoding='utf-8').write('\n'.join(sym))
    # about.html に差し込む版: <symbol> ではなく <defs> の <path>。<use> で呼ぶと元の座標(ロゴの画素)のまま置ける
    defs = ['<svg class="logo-defs" width="0" height="0" aria-hidden="true" focusable="false"><defs>']
    for k, d in symbols.items():
        defs.append('<path id="lg-%s" d="%s"/>' % (k, d))
    defs.append('</defs></svg>')
    open(os.path.join(OUT, 'logo_defs.html'), 'w', encoding='utf-8').write(''.join(defs))
    json.dump(boxes, open(os.path.join(OUT, 'logo_boxes.json'), 'w'), indent=1)
    print('symbols bytes', {k: len(d) for k, d in symbols.items()})
    print(json.dumps(boxes))

    # 比較用: 元の PNG と同じ大きさの SVG を HTML に置く(Chrome で撮って差を見る)
    cols = {'head-l': '#c7492e', 'body-l': '#c7492e', 'head-r': '#c4a174', 'body-r': '#c4a174', 'bowl': '#ad3e2c',
            'steam-0': '#c7a67c', 'steam-1': '#c7a67c', 'steam-2': '#c7a67c'}
    uses = ''.join('<path fill="%s" d="%s"/>' % (cols[k], d) for k, d in symbols.items())
    html = ('<!doctype html><html><body style="margin:0;background:#fff">'
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="%d" height="%d" style="display:block">%s</svg>'
            '</body></html>') % (W, H, W * 3, H * 3, uses)
    open(os.path.join(OUT, 'compare.html'), 'w', encoding='utf-8').write(html)


if __name__ == '__main__':
    main()
