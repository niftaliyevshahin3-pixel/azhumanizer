"""Brauzer (Pyodide) və CLI üçün vahid giriş nöqtəsi. JSON qaytarır."""
import difflib
import json
import re

from . import detector, engine
from .textutil import az_lower

_RES = None
_TOKEN = re.compile(r"\s+|[^\W\d_]+(?:[-’'][^\W\d_]+)*|\d+(?:[.,]\d+)*|.", re.UNICODE)


def init(lexicon_texts_json: str, phrases_text: str, detector_json: str = ""):
    global _RES
    texts = json.loads(lexicon_texts_json)
    _RES = engine.Resources(texts, phrases_text, detector_json or None)
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


def run(text: str, level: str = "strong", seed: int = 1, candidates: int = 6, protected_json: str = "[]", target: float = 10.0, fmt: str = "plain", noise: bool = False):
    protected = json.loads(protected_json)
    out_text, r, history = engine.humanize_to_target(
        _RES, text, target=float(target), level=level, seed=int(seed), protected_terms=protected,
        candidates=int(candidates), max_rounds=4)
    if noise:
        out_text = engine.inject_typing_noise(out_text, seed=int(seed))
    if fmt == "dash":
        from .textutil import split_sentences
        lines = []
        for ln in out_text.split("\n"):
            if ln.strip():
                lines.extend("\u2013 " + x for x in split_sentences(ln))
        out_text = "\n".join(lines)
    kinds = {}
    changes = []
    if r is not None:
        for c in r.changes:
            if not c.kind.startswith("skipped"):
                kinds[c.kind] = kinds.get(c.kind, 0) + 1
        changes = [c.as_dict() for c in r.changes if not c.kind.startswith("skipped")][:500]
    return json.dumps(
        {
            "text": out_text,
            "before": detector.check(text),
            "after": detector.check(out_text),
            "similarity": round(engine._similarity(text, out_text), 3),
            "history": history,
            "kinds": kinds,
            "segments": _diff_segments(text, out_text) if len(text) < 60000 else [],
            "changes": changes,
            "seed": int(seed),
        },
        ensure_ascii=False,
    )


def check_only(text: str):
    return json.dumps(detector.check(text), ensure_ascii=False)
