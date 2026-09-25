# 宇野の名札のアイコン: かわいい狐(胸から上)。SVG を手で組む。
#   python test/about/make_fox.py
#     -> test/about/out/fox-inline.svg   about.html の名札(4:3)に差し込む分。色は CSS 変数、動きは JS/CSS が class を見て付ける
#     -> assets/about/uno-fox.svg        単体のアイコン(正方形・丸い地つき)。SNS のアイコン等にそのまま使える
# 形は 400x400 の座標で描く。名札では viewBox を 4:3 に切り、体の下は札の下辺で切れる。
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..', '..'))


def mirror(d):
    """x を 400 - x に写した path を返す(左半分から右半分を作る)。数字は x y の組で並んでいる前提"""
    out, toks, i = [], d.replace(',', ' ').split(), 0
    xy = 0
    for t in toks:
        if t[0].isalpha():
            out.append(t); xy = 0
        else:
            v = float(t)
            out.append(('%g' % (400 - v)) if xy % 2 == 0 else ('%g' % v))
            xy += 1
    return ' '.join(out)


# ---- 部品(左半分で描いて、右は写す) ----
EAR_L = 'M 116 214 C 98 160 96 112 108 84 C 113 72 124 70 133 78 C 162 104 184 128 198 154 Z'
EAR_IN_L = 'M 128 196 C 118 150 118 118 125 100 C 128 94 134 94 139 99 C 158 118 172 136 182 156 Z'
EAR_TIP_L = 'M 103 116 C 102 98 104 88 108 84 C 113 72 124 70 133 78 C 140 84 147 91 153 97 C 136 98 116 104 103 116 Z'
HEAD = ('M 200 126 C 258 126 300 156 308 204 C 312 224 322 240 342 252 C 320 258 308 262 299 267 '
        'C 286 297 248 316 200 316 C 152 316 114 297 101 267 C 92 262 80 258 58 252 C 78 240 88 224 92 204 '
        'C 100 156 142 126 200 126 Z')
TUFT = 'M 184 131 C 188 118 193 112 199 110 C 199 118 201 124 205 128 C 208 119 213 114 220 112 C 218 120 219 126 222 132 Z'
MASK = ('M 60 252 C 88 246 110 237 126 225 C 144 211 169 214 183 232 C 189 240 195 246 200 250 '
        'C 205 246 211 240 217 232 C 231 214 256 211 274 225 C 290 237 312 246 340 252 C 320 258 308 262 299 267 '
        'C 286 297 248 316 200 316 C 152 316 114 297 101 267 C 92 262 80 258 60 252 Z')
BODY = 'M 104 420 C 104 346 142 298 200 298 C 258 298 296 346 296 420 Z'
BIB = 'M 150 420 C 152 360 172 322 200 314 C 228 322 248 360 250 420 Z'
TAIL = ('M 262 420 C 318 414 376 378 386 318 C 394 270 372 226 340 214 C 322 208 306 220 310 238 '
        'C 318 274 312 306 286 330 C 272 344 262 370 262 420 Z')
# 尻尾の先の白。尻尾の形で切り抜く。境目は小さく波打たせて毛のふわっと感を出す
TAIL_TIP = ('M 280 150 L 420 150 L 420 300 C 410 296 402 290 393 293 C 384 281 374 285 365 278 '
            'C 356 266 346 272 337 264 C 327 253 318 258 300 252 Z')
NOSE = 'M 187 246 C 194 241 206 241 213 246 C 211 256 205 261 200 261 C 195 261 189 256 187 246 Z'
MOUTH = 'M 200 261 L 200 267 M 185 266 C 189 275 197 276 200 267 C 203 276 211 275 215 266'


def fox_group():
    g = ['<g class="fx-all">']
    g.append('<defs><clipPath id="fx-tail-clip"><path d="%s" /></clipPath></defs>' % TAIL)
    g.append('<g class="fx-tail"><path class="fx-o2" d="%s" /><path class="fx-c" clip-path="url(#fx-tail-clip)" d="%s" /></g>' % (TAIL, TAIL_TIP))
    g.append('<path class="fx-o2" d="%s" />' % BODY)
    g.append('<path class="fx-c" d="%s" />' % BIB)
    g.append('<g class="fx-head">')
    for side, sx in (('l', ''), ('r', 'r')):
        e, ei, et = (EAR_L, EAR_IN_L, EAR_TIP_L) if side == 'l' else (mirror(EAR_L), mirror(EAR_IN_L), mirror(EAR_TIP_L))
        g.append('<g class="fx-ear fx-ear-%s"><path class="fx-o" d="%s" /><path class="fx-in" d="%s" /><path class="fx-dk" d="%s" /></g>' % (side, e, ei, et))
    g.append('<path class="fx-o" d="%s" />' % HEAD)
    g.append('<path class="fx-o" d="%s" />' % TUFT)
    g.append('<path class="fx-c" d="%s" />' % MASK)
    g.append('<ellipse class="fx-blush" cx="132" cy="240" rx="15" ry="8" /><ellipse class="fx-blush" cx="268" cy="240" rx="15" ry="8" />')
    g.append('<g class="fx-eyes">')
    for cx in (152, 248):
        g.append('<g class="fx-eye"><ellipse class="fx-ink" cx="%d" cy="205" rx="15" ry="18" />'
                 '<circle class="fx-hi" cx="%d" cy="197" r="5.5" /><circle class="fx-hi" cx="%d" cy="212" r="2.4" /></g>' % (cx, cx + 5, cx - 6))
    g.append('</g>')
    g.append('<path class="fx-ink" d="%s" /><ellipse class="fx-hi" cx="195" cy="246" rx="3.2" ry="1.8" />' % NOSE)
    g.append('<path class="fx-line" d="%s" />' % MOUTH)
    g.append('</g></g>')
    return ''.join(g)


COLORS = {'o': '#f28c3c', 'o2': '#e57a33', 'c': '#fff5e8', 'in': '#ffd8c4', 'dk': '#5c3421', 'ink': '#2b1b14', 'blush': '#ff9f98', 'bg': '#f3e8da'}

STYLE_FIXED = ('.fx-o{fill:%(o)s}.fx-o2{fill:%(o2)s}.fx-c{fill:%(c)s}.fx-in{fill:%(in)s}.fx-dk{fill:%(dk)s}'
               '.fx-ink{fill:%(ink)s}.fx-hi{fill:#fff}.fx-blush{fill:%(blush)s;opacity:.65}'
               '.fx-line{fill:none;stroke:%(ink)s;stroke-width:3.4;stroke-linecap:round;stroke-linejoin:round}') % COLORS

# 名札用: 4:3。耳の先から、体が札の下辺で切れるところまで
inline = ('<svg class="mark-fox" viewBox="-45 45 490 367.5" preserveAspectRatio="xMidYMax meet" aria-hidden="true" focusable="false">'
          + fox_group() + '</svg>')

# 単体のアイコン: 丸い地に胸から上。丸の外は透明
standalone = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 400" width="400" height="400">'
              '<style>%s</style>' % STYLE_FIXED
              + '<defs><clipPath id="fx-round"><circle cx="200" cy="200" r="200" /></clipPath></defs>'
              + '<circle cx="200" cy="200" r="200" fill="%s" />' % COLORS['bg']
              + '<g clip-path="url(#fx-round)"><g transform="translate(0 12)">' + fox_group() + '</g></g></svg>')

os.makedirs(os.path.join(HERE, 'out'), exist_ok=True)
open(os.path.join(HERE, 'out', 'fox-inline.svg'), 'w', encoding='utf-8').write(inline)
open(os.path.join(ROOT, 'assets', 'about', 'uno-fox.svg'), 'w', encoding='utf-8').write(standalone)
print('ok')
