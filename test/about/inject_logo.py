"""trace_logo.py が書いた out/logo_defs.html を about.html の目印の間に差し込む。
使い方: python test/about/trace_logo.py && python test/about/inject_logo.py"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
page = os.path.join(ROOT, 'about.html')
defs = open(os.path.join(HERE, 'out', 'logo_defs.html'), encoding='utf-8').read()
s = open(page, encoding='utf-8').read()
a, b = '<!-- logo-defs:start -->', '<!-- logo-defs:end -->'
i, j = s.index(a) + len(a), s.index(b)
s = s[:i] + defs + s[j:]
open(page, 'w', encoding='utf-8', newline='\n').write(s)
print('injected', len(defs), 'bytes')
