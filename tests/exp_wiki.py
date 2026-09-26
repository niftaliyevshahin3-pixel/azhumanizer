import sys, io, json
sys.path.insert(0, '.')
import azhum
from azhum import engine
res = azhum.load_resources()
w = json.load(io.open('tests/human/wiki_az.json', encoding='utf8'))
b = [x for x in w if x['title'] == 'Vergi'][0]['paragraphs']
src = ' '.join(b[1:3])
sents = src.split('. ')
src = '. '.join(sents[:8]) + '.'
t, r, h = engine.humanize_to_target(res, src, target=10, level='max', seed=5, candidates=6)
print(engine._similarity(src, t), file=sys.stderr)
print(t)
