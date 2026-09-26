import sys, json, io
from collections import Counter
sys.path.insert(0, '.')
import azhum
from azhum.textutil import tokenize, az_lower
res = azhum.load_resources()
cnt = Counter(); cov = Counter()
total = 0
for f in ['batch30_texts', 'fresh30_texts']:
    for x in json.load(io.open('tests/%s.json' % f, encoding='utf8')):
        toks = tokenize(x['text'])
        ms = res.lexicon.find_matches(toks)
        covered = set()
        for m in ms:
            for i in range(m.start, m.end + 1):
                covered.add(i)
        for i, t in enumerate(toks):
            if t[0] == 'w':
                total += 1
                w = az_lower(t[1])
                cnt[w] += 1
                if i in covered:
                    cov[w] += 1
print('total words', total, 'covered', sum(cov.values()), '%.1f%%' % (100.0 * sum(cov.values()) / total))
out = io.open('tests/_freq.txt', 'w', encoding='utf8')
for w, c in cnt.most_common(1200):
    if len(w) >= 5 and cov[w] == 0:
        out.write('%s\t%d\n' % (w, c))
out.close()
