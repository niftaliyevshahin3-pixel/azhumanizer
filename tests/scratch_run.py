import sys, json, io
sys.path.insert(0, '.')
import azhum
res = azhum.load_resources()
print('lexicon entries', len(res.lexicon.entries), 'forms', res.lexicon.form_count, 'phrases', len(res.phrases.rules))
d = json.load(io.open('tests/batch30_texts.json', encoding='utf8'))
i = int(sys.argv[1]) if len(sys.argv) > 1 else 0
level = sys.argv[2] if len(sys.argv) > 2 else 'balanced'
src = d[i]['text']
r = azhum.humanize(res, src, level=level, seed=11, candidates=6)
out = io.open('tests/_out.txt', 'w', encoding='utf8')
out.write('TITLE: %s\n\nORIGINAL:\n%s\n\nHUMANIZED:\n%s\n\n' % (d[i]['title'], src, r.text))
out.write('SCORE %s -> %s\n' % (r.before['score'], r.after['score']))
for c in r.changes:
    out.write('%s | %s => %s\n' % (c.kind, c.before[:110], c.after[:110]))
out.close()
print('score', r.before['score'], '->', r.after['score'], 'changes', len(r.changes))
