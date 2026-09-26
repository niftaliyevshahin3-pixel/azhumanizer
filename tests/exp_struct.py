import sys, io
sys.path.insert(0, '.')
import azhum
from azhum import engine, detector
res = azhum.load_resources()
src = io.open('tests/user2.txt', encoding='utf8').read().strip()
engine.LEVELS['structonly'] = dict(engine.LEVELS['max'], lex=0.0, phrase=0.0, opener=1.0)
best = None
for seed in range(1, 30):
    r = engine.humanize_once(res, src, 'structonly', seed)
    c = detector.check(r.text)
    sim = engine._similarity(src, r.text)
    key = c['struct_percent']
    if best is None or key < best[0]:
        best = (key, sim, r.text, seed)
print(best[0], best[1], best[3], file=sys.stderr)
from azhum.textutil import split_sentences, count_words
print([count_words(s) for s in split_sentences(best[2])], file=sys.stderr)
print(best[2])
