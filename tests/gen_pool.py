import sys, io, json, re
sys.path.insert(0, '.')
import azhum
from azhum import engine, detector
from azhum.textutil import split_sentences
res = azhum.load_resources()
src = io.open('tests/user2.txt', encoding='utf8').read().strip()
def w(name, text):
    io.open('tests/_pool/%s.txt' % name, 'w', encoding='utf8', newline='\n').write(text)
w('orig_plain', src)
w('orig_dash', '\n'.join('– ' + s for s in split_sentences(src)))
for seed in range(1, 9):
    r = engine.humanize_once(res, src, 'max', seed * 31)
    w('max%d_plain' % seed, r.text)
    w('max%d_dash' % seed, '\n'.join('– ' + s for s in split_sentences(r.text)))
print('ok')
