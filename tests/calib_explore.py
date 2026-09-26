import sys, io, json, math, re
sys.path.insert(0, '.')
import azhum
from azhum.metrics import analyze
from azhum.textutil import count_words
res = azhum.load_resources()
wiki = json.load(io.open('tests/human/wiki_az.json', encoding='utf8'))
human = []
for art in wiki:
    cur = []
    for p in art['paragraphs']:
        cur.append(p)
        if sum(count_words(x) for x in cur) >= 160:
            human.append('\n'.join(cur)); cur = []
ai = []
for f in ['batch30_texts', 'fresh30_texts']:
    ai += [x['text'] for x in json.load(io.open('tests/%s.json' % f, encoding='utf8'))]
ai.append(io.open('tests/user1.txt', encoding='utf8').read())
print('human chunks', len(human), 'ai texts', len(ai))
def feats(t):
    r = analyze(t, res.ai_regexes)
    d = {k: v['penalty'] for k, v in r['parts'].items()}
    d['score'] = r['score']; d['cv'] = r['stats']['cv']; d['mean_len'] = r['stats']['mean_len']
    return d
H = [feats(t) for t in human]; A = [feats(t) for t in ai]
keys = list(H[0].keys())
def mean(xs): return sum(xs) / len(xs)
for k in keys:
    print('%-16s human %.3f  ai %.3f' % (k, mean([h[k] for h in H]), mean([a[k] for a in A])))
def auc(pos, neg):
    c = 0
    for p in pos:
        for n in neg:
            c += 1 if p > n else (0.5 if p == n else 0)
    return c / (len(pos) * len(neg))
print('AUC score', auc([a['score'] for a in A], [h['score'] for h in H]))
for k in keys:
    print('AUC', k, round(auc([a[k] for a in A], [h[k] for h in H]), 3))
