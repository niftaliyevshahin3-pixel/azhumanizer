import sys, json, io
sys.path.insert(0, '.')
from azhum.metrics import analyze
from azhum.phrases import PhraseTable, ai_phrase_regexes
t = PhraseTable.from_text(io.open('data_src/phrases_az.txt', encoding='utf8').read())
rx = ai_phrase_regexes(t)
for f in ['batch30_texts', 'fresh30_texts']:
    d = json.load(io.open('tests/%s.json' % f, encoding='utf8'))
    sc = []
    for x in d:
        r = analyze(x['text'], rx)
        sc.append(r['score'])
    print(f, 'avg', round(sum(sc)/len(sc), 1), 'min', min(sc), 'max', max(sc))
    r = analyze(d[0]['text'], rx)
    print(json.dumps(r, ensure_ascii=True)[:900])
