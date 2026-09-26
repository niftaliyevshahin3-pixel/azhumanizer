import json, io, re, random, sys
sys.path.insert(0, '.')
from azhum.textutil import az_lower, match_case
d = json.load(io.open('C:/Projects/TezyazBot/docgen/humanizer/dictionaries/az_synonyms.json', encoding='utf8'))['entries']
src = io.open('tests/user2.txt', encoding='utf8').read().strip()
random.seed(2)
cnt = 0
def rep(m):
    global cnt
    w = m.group(0)
    lw = az_lower(w)
    e = table.get(lw)
    if not e: return w
    cnt += 1
    return match_case(w, random.choice(e))
table = {}
for x in d:
    if ' ' not in x['lemma']:
        s = [y for y in x['synonyms'] if ' ' not in y]
        if s: table[az_lower(x['lemma'])] = s
out = re.sub(r"[^\W\d_]+", rep, src)
print(cnt, len(src.split()), file=sys.stderr)
print(out)
