"""Redaktor AI-yoxlayıcısı — stilometrik siniflədirici.

DİQQƏT: bu StrikePlagiarism (və ya digər kommersiya detektorlarının) surəti DEYİL — onların
alqoritmi açıq deyil. Bu, aşağıdakı əlamətlərə görə hesablanan logistik modeldir və real
insan mətni (Azərbaycan Vikipediyası) ilə AI mətn nümunələri üzərində təlim edilib
(tools/train_detector.py). Nəticə "bu mətn AI-yə xas struktur əlamətlərə nə qədər
bənzəyir" göstəricisidir və başqa detektorun nəticəsini GARANTİYA ETMİR.
"""
import json
import math
import re
from collections import Counter

from .textutil import az_lower, count_words, split_sentences, words_of
from .phrases import detect_opener

FEATURES = [
    "cv", "share_short", "share_long", "near_median", "mean_len", "comma_per", "comma_std", "semi_rate",
    "paren_rate", "dash_rate", "colon_rate", "conn_share", "rep_first", "rep_bigram", "par_share", "end_cop",
    "ve_density", "nominal", "ai_markers", "top5", "rep_tri", "avg_word_len", "ttr",
]
# məzmun-konkretliyi əlamətləri: yalnız yenidən yazmaqla düzəlmir (rəqəm/ad/fakt lazımdır)
CONTENT_FEATURES = ["digit_rate", "proper_rate", "abstract_rate", "quote_rate"]
ALL_FEATURES = FEATURES + CONTENT_FEATURES
ABSTRACT_STEMS = ["fəaliyyət", "proses", "sahə", "inkişaf", "əhəmiyyət", "sistem", "məsələ", "istiqamət", "imkan", "amil", "təsir",
                  "nəticə", "yanaşma", "mühit", "cəmiyyət", "səviyyə", "potensial", "strategiya", "mexanizm", "konsepsiya", "prinsip",
                  "xüsusiyyət", "göstərici", "şərait", "vəziyyət", "problem", "məqsəd", "funksiya", "keyfiyyət", "effektiv", "səmərə",
                  "qabiliyyət", "bacarıq", "davamlı", "qlobal", "müasir", "mühüm", "vacib", "əsas", "ümumi"]

AI_MARKERS = [
    "qeyd etmək lazımdır", "vurğulamaq lazımdır", "nəzərə almaq lazımdır", "diqqət yetirmək lazımdır", "müasir dövrdə",
    "hazırkı dövrdə", "böyük əhəmiyyət", "mühüm əhəmiyyət", "xüsusi əhəmiyyət", "əhəmiyyət kəsb edir", "mühüm rol oynayır",
    "əsas rol oynayır", "həlledici rol", "əvəzolunmaz", "əvəzsiz", "danılmaz", "şübhəsiz ki", "bir sözlə", "nəticə etibarilə",
    "yekun olaraq", "bəşəriyyət", "sürətlə inkişaf", "getdikcə artan", "ayrılmaz hissəsi", "ayrılmaz", "hər bir insan",
    "zəngin irs", "sivilizasiya", "qlobal", "təməl daşı", "açar rolu", "yeni üfüqlər", "sıçrayış", "inqilabi", "möhtəşəm",
    "nəhəng", "eyni zamanda", "bununla yanaşı", "bundan əlavə", "digər tərəfdən", "beləliklə", "əslində", "məhz",
    "önəm daşıyır", "ön plana çıxır", "çoxşaxəli", "hərtərəfli", "dərindən", "dinamik", "davamlı inkişaf", "unikal",
    "qarşılıqlı əlaqə", "əhəmiyyətli rol", "vacib rol", "başlıca rol", "ciddi şəkildə", "geniş şəkildə",
]
_AI_RE = [re.compile(r"(?<!\w)" + re.escape(m), re.I | re.U) for m in AI_MARKERS]
_COP = re.compile(r"(dır|dir|dur|dür|mışdır|mişdir|muşdur|müşdür)[.!?…\"»)]*$")
_NOM = re.compile(r"\w+(ılması|ilməsi|ulması|ülməsi|ması|məsi)(nın|nin|nun|nün|na|nə|nı|ni|da|də|dan|dən)?(?!\w)")
_STOP = set("""və ilə ki da də bu o bir üçün isə kimi görə daha çox olan olaraq həm ya yaxud amma lakin ancaq hər çünki əgər
nə necə belə elə onun bunun onlar bunlar üzrə barədə haqqında sonra əvvəl zaman artıq yalnız təkcə hələ dır dir dur dür
idi olur olub olmuşdur edir edilir olunur edən etmək olmaq etdi oldu ən""".split())

_MODEL = None


def load_model(data):
    global _MODEL
    _MODEL = json.loads(data) if isinstance(data, str) else data


def _clip(x, lo=0.0, hi=1.0):
    return max(lo, min(hi, x))


def _sentences(text):
    out = []
    for line in text.split("\n"):
        line = line.strip()
        if line:
            out.extend(split_sentences(line))
    return out


def features(text: str):
    sents = _sentences(text)
    n = len(sents)
    if n < 3:
        return None
    lens = [count_words(s) for s in sents]
    mean = sum(lens) / n
    std = math.sqrt(sum((l - mean) ** 2 for l in lens) / n)
    cv = std / mean if mean else 0.0
    med = sorted(lens)[n // 2]
    low = az_lower(text)
    toks = [az_lower(w) for w in words_of(text)]
    total = max(1, len(toks))
    commas = [s.count(",") for s in sents]
    cmean = sum(commas) / n
    cstd = math.sqrt(sum((c - cmean) ** 2 for c in commas) / n)
    firsts = Counter(az_lower(words_of(s)[0]) if words_of(s) else "" for s in sents)
    bis = Counter(" ".join(az_lower(w) for w in words_of(s)[:2]) for s in sents)
    conn = sum(1 for s in sents if detect_opener(s))
    par = sum(1 for i in range(n - 2) if max(lens[i:i + 3]) - min(lens[i:i + 3]) <= 3)
    content = [w for w in toks if len(w) >= 5 and w not in _STOP]
    cc = Counter(content)
    tri = Counter(zip(toks, toks[1:], toks[2:]))
    hits = sum(len(rx.findall(low)) for rx in _AI_RE)
    f = {
        "cv": cv,
        "share_short": sum(1 for l in lens if l <= 8) / n,
        "share_long": sum(1 for l in lens if l >= 28) / n,
        "near_median": sum(1 for l in lens if abs(l - med) <= max(3, 0.25 * med)) / n,
        "mean_len": mean / 20.0,
        "comma_per": cmean,
        "comma_std": cstd,
        "semi_rate": text.count(";") / n,
        "paren_rate": text.count("(") / n,
        "dash_rate": (text.count("—") + text.count("–")) / n,
        "colon_rate": text.count(":") / n,
        "conn_share": conn / n,
        "rep_first": sum(c for c, in [(v,) for v in firsts.values()] if c >= 3) / n,
        "rep_bigram": sum(c for c in bis.values() if c >= 3) / n,
        "par_share": par / max(1, n - 2),
        "end_cop": sum(1 for s in sents if _COP.search(az_lower(s.strip()))) / n,
        "ve_density": low.count(" və ") / n,
        "nominal": sum(len(_NOM.findall(az_lower(s))) for s in sents) / n,
        "ai_markers": hits * 100.0 / total,
        "top5": sum(c for _, c in cc.most_common(5)) / max(1, len(content)),
        "rep_tri": sum(c for c in tri.values() if c >= 2) / total,
        "avg_word_len": sum(len(w) for w in toks) / total / 8.0,
        "ttr": len(set(toks[:200])) / max(1, len(toks[:200])),
    }
    raw_words = words_of(text)
    proper = 0
    for sent in sents:
        ws = words_of(sent)
        proper += sum(1 for w in ws[1:] if w[:1].isupper() and len(w) > 1)
    f["digit_rate"] = sum(1 for t in re.findall(r"\w+", text) if any(ch.isdigit() for ch in t)) * 100.0 / total
    f["proper_rate"] = proper * 100.0 / total
    f["abstract_rate"] = sum(1 for w in toks if any(w.startswith(st) for st in ABSTRACT_STEMS)) * 100.0 / total
    f["quote_rate"] = (text.count('"') + text.count("«") + text.count("“")) * 100.0 / total
    return f, sents, lens


def _prob(f, which="struct"):
    m = _MODEL[which]
    z = m["bias"]
    for k in m["features"]:
        z += m["w"][k] * ((f[k] - m["mean"][k]) / (m["std"][k] or 1.0))
    z = max(-30.0, min(30.0, z))
    return 1.0 / (1.0 + math.exp(-z)), z


def check(text: str):
    """AI-oxşarlıq yoxlaması. struct_percent: cümlə ritmi/üslub (yenidən yazmaqla düzəlir);
    percent: konkretlik (rəqəm, ad, fakt) də daxil olmaqla tam göstərici."""
    r = features(text)
    if r is None:
        return {"percent": None, "note": "Ən azı 3 cümlə lazımdır"}
    f, sents, lens = r
    ps, zs = _prob(f, "struct")
    pf, zf = _prob(f, "full")
    pc, zc = _prob(f, "content")
    m = _MODEL["struct"]
    contrib = []
    for k in m["features"]:
        c = m["w"][k] * ((f[k] - m["mean"][k]) / (m["std"][k] or 1.0))
        contrib.append((c, k))
    contrib.sort(reverse=True)
    reasons = [{"feature": k, "value": round(f[k], 3), "push": round(c, 2)} for c, k in contrib[:4] if c > 0.15]
    mf = _MODEL["full"]
    content_push = sum(mf["w"][k] * ((f[k] - mf["mean"][k]) / (mf["std"][k] or 1.0)) for k in CONTENT_FEATURES)
    med = sorted(lens)[len(lens) // 2]
    out = []
    for s, l in zip(sents, lens):
        low = az_lower(s)
        risk = 0.0
        risk += 0.35 * min(3, sum(len(rx.findall(low)) for rx in _AI_RE)) / 3
        risk += 0.2 if detect_opener(s) else 0.0
        risk += 0.2 if abs(l - med) <= max(3, 0.25 * med) else 0.0
        risk += 0.15 if _COP.search(low.strip()) else 0.0
        risk += 0.1 if low.count(" və ") >= 2 else 0.0
        out.append({"text": s, "risk": round(min(1.0, risk), 2)})
    return {"percent": round(max(ps, pc) * 100, 1), "full_percent": round(pf * 100, 1), "struct_percent": round(ps * 100, 1),
            "content_percent": round(pc * 100, 1),
            "content_push": round(content_push, 2),
            "features": {k: round(v, 3) for k, v in f.items()},
            "reasons": reasons, "sentences": out}


def percent(text: str, default=50.0, which="struct") -> float:
    r = features(text)
    if r is None:
        return default
    return _prob(r[0], which)[0] * 100.0
