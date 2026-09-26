"""Brauzer (Pyodide) və CLI üçün vahid giriş nöqtəsi. JSON qaytarır."""
import difflib
import json
import re

from . import engine, metrics
from .textutil import az_lower

_RES = None
_TOKEN = re.compile(r"\s+|[^\W\d_]+(?:[-’'][^\W\d_]+)*|\d+(?:[.,]\d+)*|.", re.UNICODE)


def init(lexicon_texts_json: str, phrases_text: str):
    global _RES
    texts = json.loads(lexicon_texts_json)
    _RES = engine.Resources(texts, phrases_text)
    return json.dumps({"entries": len(_RES.lexicon.entries), "forms": _RES.lexicon.form_count, "phrases": len(_RES.phrases.rules)})


def _diff_segments(a: str, b: str):
    ta = _TOKEN.findall(a)
    tb = _TOKEN.findall(b)
    sm = difflib.SequenceMatcher(None, [az_lower(x) for x in ta], [az_lower(x) for x in tb], autojunk=False)
    segs = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        new = "".join(tb[j1:j2])
        old = "".join(ta[i1:i2])
        if tag == "equal":
            segs.append(["=", new, ""])
        elif tag == "insert":
            segs.append(["+", new, ""])
        elif tag == "delete":
            segs.append(["-", "", old])
        else:
            segs.append(["~", new, old])
    return segs


def run(text: str, level: str = "balanced", seed: int = 1, candidates: int = 6, protected_json: str = "[]"):
    protected = json.loads(protected_json)
    r = engine.humanize(_RES, text, level=level, seed=int(seed), protected_terms=protected, candidates=int(candidates))
    kinds = {}
    for c in r.changes:
        if not c.kind.startswith("skipped"):
            kinds[c.kind] = kinds.get(c.kind, 0) + 1
    return json.dumps(
        {
            "text": r.text,
            "before": r.before,
            "after": r.after,
            "kinds": kinds,
            "seed": r.seed,
            "segments": _diff_segments(text, r.text) if len(text) < 60000 else [],
            "changes": [c.as_dict() for c in r.changes if not c.kind.startswith("skipped")][:400],
            "skipped": [c.as_dict() for c in r.changes if c.kind.startswith("skipped")][:40],
        },
        ensure_ascii=False,
    )


def score_only(text: str):
    return json.dumps(metrics.analyze(text, _RES.ai_regexes), ensure_ascii=False)
