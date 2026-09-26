import sys, io, json
sys.path.insert(0, '.')
import azhum
from azhum import engine, detector
res = azhum.load_resources()
src = io.open('tests/user2.txt', encoding='utf8').read().strip()
out = []
for i, seed in enumerate([1, 2, 3, 4, 5, 6]):
    t, r, h = engine.humanize_to_target(res, src, target=10, level='max', seed=seed * 17, candidates=6)
    c = detector.check(t)
    out.append({'seed': seed * 17, 'struct': c['struct_percent'], 'sim': round(engine._similarity(src, t), 2), 'text': t})
    print(i, seed * 17, c['struct_percent'], round(engine._similarity(src, t), 2), file=sys.stderr)
io.open('tests/_variants.json', 'w', encoding='utf8').write(json.dumps(out, ensure_ascii=False, indent=1))
