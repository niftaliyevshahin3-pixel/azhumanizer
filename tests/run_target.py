import sys, io, re
sys.path.insert(0, '.')
import azhum
from azhum import engine, detector
res = azhum.load_resources()
path = sys.argv[1]
level = sys.argv[2] if len(sys.argv) > 2 else 'strong'
src = io.open(path, encoding='utf8').read()
out, r, hist = engine.humanize_to_target(res, src, target=10, level=level, seed=1, candidates=8)
c0 = detector.check(src)
c1 = detector.check(out)
print('history', hist, file=sys.stderr)
print('BEFORE overall %s struct %s content %s | AFTER overall %s struct %s content %s | similarity %.2f' % (
    c0['percent'], c0['struct_percent'], c0['content_percent'], c1['percent'], c1['struct_percent'], c1['content_percent'],
    engine._similarity(src, out)), file=sys.stderr)
io.open('tests/_user_out.txt', 'w', encoding='utf8').write(out)
print(out)
