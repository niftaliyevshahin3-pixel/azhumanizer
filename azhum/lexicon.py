"""Lüğət: klasterlər, şəkilçi-şüurlu axtarış və sinonim əvəzləməsi."""
import re
from .textutil import az_lower, match_case, is_capitalized, is_all_caps
from . import morph

BARE = ("bare",)

# leksikallaşmış qoşma/bağlayıcı formalar — heç vaxt əvəzlənmir
STOP_SURFACES = {
    "əsasında", "əsasən", "əsasda", "nəticəsində", "vasitəsilə", "vasitəsi", "sayəsində",
    "çərçivəsində", "haqqında", "barədə", "əsasında", "üzrə", "tərəfindən", "məqsədilə",
    "səbəbindən", "zamanı", "vaxtı",
    "yolu", "yolla", "qismində", "kimi", "üçün", "ilə", "cəhətdən", "baxımından",
    "istiqamətində", "əvəzinə", "əlavə", "nəzərən", "əsasıdır",
}


class Entry:
    __slots__ = ("kind", "words", "last", "targets", "_forms", "stem")

    def __init__(self, kind, words):
        self.kind = kind            # 'n' | 'b' | 'v'
        self.words = tuple(words)   # kiçik hərflə
        self.last = self.words[-1]
        self.targets = []           # [(kind, words)]
        self._forms = None
        self.stem = morph.verb_stem(self.last) if kind == "v" else None

    def forms(self):
        if self._forms is not None:
            return self._forms
        f = {}
        if self.kind == "b":
            f[self.last] = [BARE]
        elif self.kind == "n":
            for k in morph.NOUN_KEYS:
                s = morph.realize_noun(self.last, k)
                if s:
                    f.setdefault(s, [])
                    if k not in f[s]:
                        f[s].append(k)
        elif self.kind == "v" and self.stem:
            for k in morph.VERB_KEYS:
                if k[0] == "v":
                    s = morph.realize_verb(self.stem, k)
                else:
                    s = morph.realize_verb_nominal(self.stem, k)
                if s:
                    f.setdefault(s, [])
                    if k not in f[s]:
                        f[s].append(k)
        self._forms = f
        return f


def realize(kind, last_word, key):
    """Hədəf sözün (son söz) verilən şablona uyğun səth forması."""
    if key == BARE:
        return last_word
    if kind == "n":
        return morph.realize_noun(last_word, key)
    if kind == "v":
        st = morph.verb_stem(last_word)
        if not st:
            return None
        if key[0] == "v":
            return morph.realize_verb(st, key)
        return morph.realize_verb_nominal(st, key)
    return last_word if key == BARE else None


class Match:
    __slots__ = ("start", "end", "entry", "keys", "surface")

    def __init__(self, start, end, entry, keys, surface):
        self.start, self.end, self.entry, self.keys, self.surface = start, end, entry, keys, surface


class Lexicon:
    def __init__(self):
        self.entries = {}   # (kind, words) -> Entry
        self.by_prefix = {}
        self.form_count = 0

    # ------------------------------------------------------------ loading
    def _entry(self, kind, words):
        key = (kind, tuple(words))
        e = self.entries.get(key)
        if e is None:
            e = Entry(kind, words)
            self.entries[key] = e
        return e

    @staticmethod
    def _split_words(s):
        return [w for w in az_lower(s.strip()).split() if w]

    def add_line(self, line):
        line = line.strip()
        if not line or line.startswith("#"):
            return
        m = re.match(r"^(n!|n|a|d|v)\s*:\s*(.+)$", line)
        if not m:
            return
        typ, body = m.group(1), m.group(2)
        kind = {"n": "n", "n!": "b", "a": "b", "d": "b", "v": "v"}[typ]
        if ">" in body and "=" not in body:
            left, right = body.split(">", 1)
            src = self._split_words(left)
            tgts = [self._split_words(x) for x in right.split(",") if x.strip()]
            e = self._entry(kind, src)
            for t in tgts:
                self._add_target(e, kind, t)
            return
        members = [self._split_words(x) for x in body.split("=") if x.strip()]
        for i, a in enumerate(members):
            e = self._entry(kind, a)
            for j, b in enumerate(members):
                if i != j:
                    self._add_target(e, kind, b)

    @staticmethod
    def _add_target(entry, kind, words):
        tup = (kind, tuple(words))
        if tup not in entry.targets and tuple(words) != entry.words:
            entry.targets.append(tup)

    def add_text(self, text):
        for ln in text.split("\n"):
            self.add_line(ln)

    def finalize(self):
        self.by_prefix = {}
        self.form_count = 0
        for e in self.entries.values():
            if not e.targets:
                continue
            forms = e.forms()
            self.form_count += len(forms)
            for surface in forms:
                self.by_prefix.setdefault(surface, []).append(e)
        return self

    @classmethod
    def from_texts(cls, texts):
        lx = cls()
        for t in texts:
            lx.add_text(t)
        return lx.finalize()

    # ------------------------------------------------------------- search
    def find_matches(self, tokens):
        """tokens: textutil.tokenize nəticəsi. Üst-üstə düşməyən uyğunluqlar
        (uzun frazalar əvvəl) qaytarılır."""
        widx = [i for i, t in enumerate(tokens) if t[0] == "w"]
        found = []
        for pos, ti in enumerate(widx):
            surface = az_lower(tokens[ti][1])
            if "-" in surface:
                continue
            cands = self.by_prefix.get(surface)
            if not cands:
                continue
            for e in cands:
                if surface in STOP_SURFACES and e.kind != "b":
                    continue
                n = len(e.words)
                if pos - (n - 1) < 0:
                    continue
                ok = True
                start_ti = ti
                for back in range(1, n):
                    pj = widx[pos - back]
                    # yalnız boşluqla ayrılmış olmalıdır
                    between = tokens[pj + 1:start_ti]
                    if any(t[0] != "s" for t in between):
                        ok = False
                        break
                    if az_lower(tokens[pj][1]) != e.words[n - 1 - back]:
                        ok = False
                        break
                    start_ti = pj
                if not ok:
                    continue
                found.append(Match(start_ti, ti, e, e.forms()[surface], surface))
        # üst-üstə düşənlərdən uzunu saxla
        found.sort(key=lambda m: (-(m.end - m.start), m.start))
        taken = []
        used = set()
        for m in found:
            span = set(range(m.start, m.end + 1))
            if span & used:
                continue
            used |= span
            taken.append(m)
        taken.sort(key=lambda m: m.start)
        return taken

    def realize_target(self, match, target):
        """(kind, words) hədəfi üçün səth forması (son sözə şəkilçi); None: mümkün deyil."""
        kind, words = target
        outs = set()
        for k in match.keys:
            r = realize(kind, words[-1], k)
            if r is None:
                return None
            outs.add(r)
        if len(outs) != 1:
            return None  # qeyri-birmənalı şəkilçi (məs. mənsubiyyət / təsirlik)
        last = outs.pop()
        return " ".join(list(words[:-1]) + [last])
