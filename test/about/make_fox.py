# 宇野の名札のアイコン: 一色のシルエットの狐(右向きに座り、尻尾を前に巻く。尻尾の先だけ白)。SVG を手で組む。
#   python test/about/make_fox.py
#     -> test/about/out/fox-inline.svg   about.html の名札(4:3)に差し込む分。形ができあがる動きは about.html の JS が付ける
#     -> assets/about/uno-fox.svg        単体のロゴ(背景は透明)
# 本人が見せてくれた参考(一色の狐のロゴ)は同じ系統というだけで、形はなぞっていない(向きも構図も別)。
# 形は 400x400 の座標で描く。
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..', '..'))

# ---- 形 ----
# 頭から胸・背中・腰・前脚まで。鼻先は右上。耳は別の形にして、手前の耳だけぴくっと動かせるようにする
HEAD = ('M 346 122 C 332 116 314 106 300 99 C 294 92 286 86 276 86 '
        'C 256 86 240 94 230 108 C 218 126 214 150 206 172 '
        'C 190 206 168 236 160 280 C 152 316 166 346 198 354 '
        'L 296 354 C 294 322 292 286 298 252 C 304 226 314 206 312 186 '
        'C 310 168 306 158 314 148 C 322 141 338 133 346 122 Z')
EAR_BACK = 'M 238 100 C 236 80 240 60 248 42 C 258 58 264 76 266 90 Z'
EAR_FRONT = 'M 262 90 C 262 68 266 48 276 28 C 290 46 298 70 298 101 C 290 95 282 91 262 90 Z'
TAIL = ('M 160 296 C 112 300 86 340 114 365 C 150 394 252 394 320 373 '
        'C 352 363 373 341 377 306 C 379 292 377 281 371 272 '
        'C 364 300 344 322 310 334 C 262 350 200 348 176 326 C 168 318 162 306 160 296 Z')
# 尻尾の先の白(尻尾の形で切り抜く)。付け根側へ向いたとがった毛先を3つ
TIP = ('M 318 250 L 420 250 L 420 420 L 314 420 C 322 402 331 388 331 374 '
       'C 323 369 317 363 313 355 C 325 357 335 355 343 351 C 335 345 329 337 327 327 '
       'C 337 331 347 331 357 326 Z')
# 抜き(背景の色で体を切る)。どれも両端がとがった三日月: 尻尾と体の境目、後ろ脚の付け根、耳の内側
GAPS = ['M 166 312 C 192 344 262 352 322 331 C 262 356 190 352 166 312 Z',
        'M 234 246 C 253 272 259 306 254 346 C 250 346 248 346 246 346 C 251 306 248 274 234 246 Z',
        'M 271 86 C 271 70 273 56 278 44 C 283 56 286 70 286 88 C 281 84 276 84 271 86 Z']
EYE = 'M 296 114 C 302 109 311 108 317 112 C 311 117 302 118 296 114 Z'
OUTLINES = [HEAD, EAR_BACK, EAR_FRONT, TAIL]


def svg_inner(uid):
    """uid は id の頭。ページに2つ置いても id がぶつからないように"""
    o = []
    o.append('<defs>')
    o.append('<clipPath id="%s-tail"><path d="%s" /></clipPath>' % (uid, TAIL))
    o.append('<clipPath id="%s-tipzone"><path d="%s" /></clipPath>' % (uid, TIP))
    o.append('<mask id="%s-cut" maskUnits="userSpaceOnUse" x="-100" y="-100" width="600" height="600">' % uid
             + '<rect x="-100" y="-100" width="600" height="600" fill="#fff" />'
             + ''.join('<path class="fl-gap" d="%s" fill="#000" />' % g for g in GAPS)
             + '<path class="fl-eye" d="%s" fill="#000" />' % EYE
             + '</mask>')
    o.append('<mask id="%s-reveal" maskUnits="userSpaceOnUse" x="-100" y="-100" width="600" height="600">'
             '<circle class="fl-reveal" cx="170" cy="330" r="520" fill="#fff" /></mask>' % uid)
    o.append('<clipPath id="%s-shape"><path d="%s" /><path d="%s" /><path d="%s" /><path d="%s" /></clipPath>' % ((uid,) + tuple(OUTLINES)))
    o.append('<linearGradient id="%s-shine" x1="0" y1="0" x2="1" y2="0">'
             '<stop offset="0" stop-color="#fff" stop-opacity="0" /><stop offset=".5" stop-color="#fff" stop-opacity=".55" />'
             '<stop offset="1" stop-color="#fff" stop-opacity="0" /></linearGradient>' % uid)
    o.append('</defs>')
    # 0. できあがった瞬間に後ろで広がる輪(動きがある時だけ)
    o.append('<circle class="fl-ring" cx="256" cy="224" r="150" />')
    # 1. 輪郭の線(できあがる途中だけ見せる)
    o.append('<g class="fl-lines">' + ''.join('<path class="fl-line" pathLength="1" d="%s" />' % d for d in OUTLINES) + '</g>')
    # 2. 塗り(広がる丸で見せていき、抜きの線と目で切る)
    o.append('<g mask="url(#%s-reveal)"><g class="fl-fill" mask="url(#%s-cut)">' % (uid, uid))
    o.append('<g class="fl-tail"><path class="fl-o" d="%s" /><path class="fl-tip" clip-path="url(#%s-tail)" d="%s" /></g>' % (TAIL, uid, TIP))
    o.append('<path class="fl-o" d="%s" />' % HEAD)
    o.append('<path class="fl-o" d="%s" />' % EAR_BACK)
    o.append('<path class="fl-o fl-ear" d="%s" />' % EAR_FRONT)
    o.append('</g></g>')
    # 3. 尻尾の先の白の縁取り
    o.append('<g class="fl-tip-lines"><path class="fl-tip-line" pathLength="1" clip-path="url(#%s-tail)" d="%s" />' % (uid, TIP)
             + '<path class="fl-tip-line fl-tip-edge" pathLength="1" clip-path="url(#%s-tipzone)" d="%s" /></g>' % (uid, TAIL))
    # 4. 仕上げの光(シルエットの中だけを斜めに走る)
    o.append('<g clip-path="url(#%s-shape)"><g class="fl-shine"><rect x="-160" y="0" width="120" height="400" fill="url(#%s-shine)" transform="skewX(-18)" /></g></g>' % (uid, uid))
    return ''.join(o)


FIXED_STYLE = ('.fl-o{fill:#f0602a}.fl-tip{fill:#fff8ef}.fl-tip-line{fill:none;stroke:#f0602a;stroke-width:6;stroke-linejoin:round}.fl-tip-edge{stroke-width:12}'
               '.fl-lines,.fl-shine,.fl-ring{display:none}')

inline = ('<svg class="mark-fox" viewBox="-20 22 500 375" preserveAspectRatio="xMidYMid meet" aria-hidden="true" focusable="false">'
          + svg_inner('fl') + '</svg>')
standalone = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="70 18 330 382" width="330" height="382"><style>%s</style>' % FIXED_STYLE
              + svg_inner('fls') + '</svg>')

os.makedirs(os.path.join(HERE, 'out'), exist_ok=True)
open(os.path.join(HERE, 'out', 'fox-inline.svg'), 'w', encoding='utf-8').write(inline)
open(os.path.join(ROOT, 'assets', 'about', 'uno-fox.svg'), 'w', encoding='utf-8').write(standalone)
print('ok')
