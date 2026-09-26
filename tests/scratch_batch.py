import sys, json, io, time
sys.path.insert(0, '.')
import azhum
res = azhum.load_resources()
level = sys.argv[1] if len(sys.argv) > 1 else 'balanced'
cands = int(sys.argv[2]) if len(sys.argv) > 2 else 4
tot_b = tot_a = 0; n = 0; t0 = time.time()
skips = 0; changes = 0
rows = []
for f in ['batch30_texts', 'fresh30_texts']:
    for x in json.load(io.open('tests/%s.json' % f, encoding='utf8')):
        r = azhum.humanize(res, x['text'], level=level, seed=3, candidates=cands)
        tot_b += r.before['score']; tot_a += r.after['score']; n += 1
        skips += sum(1 for c in r.changes if c.kind.startswith('skipped'))
        changes += sum(1 for c in r.changes if not c.kind.startswith('skipped'))
        rows.append((x['title'], r))
print(level, 'avg before %.1f after %.1f  (n=%d)  changes/text %.1f  skipped-stages %d  time %.1fs' % (tot_b / n, tot_a / n, n, changes / n, skips, time.time() - t0))
import pickle
io.open('tests/_batch_out.json', 'w', encoding='utf8').write(json.dumps([{'title': t, 'text': r.text, 'changes': [c.as_dict() for c in r.changes], 'before': r.before['score'], 'after': r.after['score']} for t, r in rows], ensure_ascii=False, indent=1))
