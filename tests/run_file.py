import sys, io
sys.path.insert(0, '.')
import azhum, difflib, re
res = azhum.load_resources()
path = sys.argv[1]; level = sys.argv[2] if len(sys.argv) > 2 else 'strong'
src = io.open(path, encoding='utf8').read()
r = azhum.humanize(res, src, level=level, seed=1, candidates=8)
out = r.text
tok = lambda s: re.findall(r"\s+|\w+|[^\w\s]", s)
a, b = tok(src), tok(out)
sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
changed = sum(max(i2 - i1, j2 - j1) for t, i1, i2, j1, j2 in sm.get_opcodes() if t != 'equal')
words = len(re.findall(r"\w+", src))
print('score', r.before['score'], '->', r.after['score'], 'changed-token-ratio %.0f%%' % (100.0 * sm.ratio()), file=sys.stderr)
io.open('tests/_user_out.txt', 'w', encoding='utf8').write(out)
print(out)
