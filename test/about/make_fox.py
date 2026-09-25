# 宇野の名札のアイコン: 一色のシルエット系の、ちびっこ体型の狐(右向きにお座り、尻尾は背中側に巻き上げる)。SVG を手で組む。
#   python test/about/make_fox.py
#     -> test/about/out/fox-inline.svg   about.html の名札(4:3)に差し込む分。できあがっていく動きは about.html の JS が付ける
#     -> assets/about/uno-fox.svg        単体のロゴ(背景は透明)
# 経緯: 本人が見せてくれた一色の狐のロゴの系統で作ったら「中二病感すごい、もっとかわいく」。
#       尖った形・細い目・背後の輪・鋭い光をやめ、頭の大きい丸い形に、丸い目・鼻・ほっぺ・白いあごと胸を足した。
# 形は 400x400 の座標で描く。
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..', '..'))

# ---- 形 ----
HEAD = ('M 240 94 C 288 94 312 124 316 158 C 330 162 346 170 348 184 '
        'C 350 197 338 205 322 206 C 310 232 280 248 240 248 '
        'C 196 248 162 222 162 172 C 162 126 196 94 240 94 Z')
EAR_BACK = 'M 178 126 C 171 100 173 76 183 59 C 187 52 194 52 198 57 C 210 71 220 89 224 104 Z'
EAR_BACK_IN = 'M 188 112 C 185 96 186 82 191 72 C 199 82 206 94 210 106 Z'
EAR_FRONT = 'M 236 100 C 240 81 250 63 264 49 C 269 44 276 46 277 52 C 282 71 284 91 283 112 Z'
EAR_FRONT_IN = 'M 248 100 C 252 86 258 74 266 64 C 270 78 272 92 271 106 Z'
# あご・のど・胸の白。頭と胴の形で切り抜くので、外側は大きめに取ってよい
BIB = ('M 352 188 C 322 204 296 214 268 221 C 255 240 259 288 280 316 '
       'C 292 330 306 318 306 300 C 306 270 330 238 362 198 Z')
BODY = ('M 196 226 C 170 262 162 318 184 348 C 198 366 262 368 292 354 '
        'C 310 346 310 322 303 300 C 296 276 290 252 280 236 Z')
PAWS = [(262, 356, 17, 10), (298, 352, 15, 10)]
TAIL = ('M 196 346 C 134 356 98 316 100 262 C 102 216 130 184 166 182 '
        'C 178 181 184 190 178 198 C 154 212 144 234 146 256 C 150 290 172 318 204 326 Z')
# 尻尾の先の白(尻尾の形で切り抜く)。境目は丸く波打たせる
TIP = ('M 40 130 L 230 130 L 230 200 L 168 206 C 164 216 156 222 146 222 '
       'C 144 232 136 238 126 238 C 122 246 112 250 100 248 L 40 250 Z')
EYE = (288, 164, 12, 13.5)
NOSE = (345, 184, 7, 6)
BLUSH = (284, 200, 13, 7)
HEART = 'M 0 6 C -9 -3 -18 -12 -10 -19 C -5 -23 0 -20 0 -15 C 0 -20 5 -23 10 -19 C 18 -12 9 -3 0 6 Z'

OUTLINES = [TAIL, BODY, HEAD, EAR_BACK, EAR_FRONT]


def wave_path():
    """下から満ちてくる水の形: 上の縁が波打つ帯。translate で上下させる"""
    d = 'M -120 0'
    for i in range(16):
        x = -120 + i * 50
        d += ' Q %d -9 %d 0 T %d 0' % (x + 12.5, x + 25, x + 50)
    return d + ' V 640 H -120 Z'


def svg_inner(uid):
    """uid は id の頭。ページに2つ置いても id がぶつからないように"""
    o = ['<defs>']
    o.append('<clipPath id="%s-tail"><path d="%s" /></clipPath>' % (uid, TAIL))
    o.append('<clipPath id="%s-tipzone"><path d="%s" /></clipPath>' % (uid, TIP))
    o.append('<clipPath id="%s-hb"><path d="%s" /><path d="%s" /></clipPath>' % (uid, HEAD, BODY))
    o.append('<mask id="%s-fill" maskUnits="userSpaceOnUse" x="-120" y="-120" width="700" height="760">'
             '<g class="fl-liquid" transform="translate(0 -40)"><path d="%s" fill="#fff" /></g></mask>' % (uid, wave_path()))
    o.append('</defs>')
    # 1. 輪郭の線(できあがる途中だけ見せる)
    o.append('<g class="fl-lines">' + ''.join('<path class="fl-line" pathLength="1" d="%s" />' % d for d in OUTLINES) + '</g>')
    # 2. 塗り(下から満ちる水で見せていく)
    o.append('<g mask="url(#%s-fill)"><g class="fl-all">' % uid)
    o.append('<g class="fl-tail"><path class="fl-o2" d="%s" /><path class="fl-c" clip-path="url(#%s-tail)" d="%s" />'
             '<path class="fl-tip-edge" clip-path="url(#%s-tipzone)" d="%s" /></g>' % (TAIL, uid, TIP, uid, TAIL))
    o.append('<path class="fl-o" d="%s" />' % BODY)
    o.append(''.join('<ellipse class="fl-o" cx="%s" cy="%s" rx="%s" ry="%s" />' % p for p in PAWS))
    o.append('<g class="fl-head">')
    o.append('<g class="fl-ear-b"><path class="fl-o" d="%s" /><path class="fl-in" d="%s" /></g>' % (EAR_BACK, EAR_BACK_IN))
    o.append('<g class="fl-ear"><path class="fl-o" d="%s" /><path class="fl-in" d="%s" /></g>' % (EAR_FRONT, EAR_FRONT_IN))
    o.append('<path class="fl-o" d="%s" />' % HEAD)
    o.append('<path class="fl-c" clip-path="url(#%s-hb)" d="%s" />' % (uid, BIB))
    o.append('<ellipse class="fl-blush" cx="%s" cy="%s" rx="%s" ry="%s" />' % BLUSH)
    o.append('<g class="fl-eye"><ellipse class="fl-ink" cx="%s" cy="%s" rx="%s" ry="%s" />' % EYE
             + '<circle class="fl-hi" cx="%s" cy="%s" r="4.4" /><circle class="fl-hi" cx="%s" cy="%s" r="2" /></g>'
             % (EYE[0] + 4, EYE[1] - 5, EYE[0] - 4, EYE[1] + 5))
    o.append('<ellipse class="fl-ink" cx="%s" cy="%s" rx="%s" ry="%s" />' % NOSE)
    o.append('</g></g></g>')
    # 3. できあがった時に浮かぶハート(動きがある時だけ)
    o.append('<g class="fl-heart" transform="translate(318 96)"><path d="%s" /></g>' % HEART)
    return ''.join(o)


FIXED_STYLE = ('.fl-o{fill:#f36b2c}.fl-o2{fill:#e2561f}.fl-c{fill:#fff4e6}.fl-in{fill:#ffd9c4}'
               '.fl-ink{fill:#3b2418}.fl-hi{fill:#fff}.fl-blush{fill:#ff9d8f;opacity:.7}'
               '.fl-tip-edge{fill:none;stroke:#e2561f;stroke-width:7}'
               '.fl-lines,.fl-heart{display:none}')

inline = ('<svg class="mark-fox" viewBox="-20 22 500 375" preserveAspectRatio="xMidYMid meet" aria-hidden="true" focusable="false">'
          + svg_inner('fl') + '</svg>')
standalone = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="80 30 290 350" width="290" height="350"><style>%s</style>' % FIXED_STYLE
              + svg_inner('fls') + '</svg>')

os.makedirs(os.path.join(HERE, 'out'), exist_ok=True)
open(os.path.join(HERE, 'out', 'fox-inline.svg'), 'w', encoding='utf-8').write(inline)
open(os.path.join(ROOT, 'assets', 'about', 'uno-fox.svg'), 'w', encoding='utf-8').write(standalone)
print('ok')
