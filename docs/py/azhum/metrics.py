"""AI-oxşarlıq üçün daxili (proksi) göstərici.

DİQQƏT: bu, StrikePlagiarism və ya başqa xarici detektorun surəti DEYİL — onların
alqoritmləri açıq deyil. Burada elmi ədəbiyyatda və praktikada AI mətnini ayıran
ən sabit siqnallar (cümlə uzunluğu dəyişkənliyi, başlanğıc təkrarı, klişe
sıxlığı, leksik təkrar, struktur paralellik, durğu monotonluğu) ölçülür.
Skor 0 (insan-oxşar) … 100 (AI-oxşar). Yalnız "əvvəl/sonra" müqayisəsi və
avtomatik variant seçimi üçündür.
"""
import math
import re
from collections import Counter
from .textutil import az_lower, split_sentences, count_words, words_of, is_upper_char
from .phrases import detect_opener

STOPWORDS = set("""və ilə ki da də bu o bir üçün isə kimi görə daha çox olan olaraq həm ya yaxud amma lakin ancaq
her hər çünki əgər nə necə belə elə onun bunun onlar bunlar mən sən biz siz ilə üzrə barədə haqqında
sonra əvvəl zaman artıq yalnız təkcə hələ də dır dir dur dür idi imiş olur olub olmuşdur edir edilir olunur
edən olan etmək olmaq etdi oldu bu gün ən lazım gərək""".split())

ENDING_COPULA = re.compile(r"(dır|dir|dur|dür|mışdır|mişdir|muşdur|müşdür)[.!?…\"»)]*$")
NOMINALIZATION = re.compile(r"\w+(ılması|ilməsi|ulması|ülməsi|ması|məsi)(nın|nin|nun|nün|na|nə|nı|ni|da|də|dan|dən)?(?!\w)")


def _sentences(text):
    out = []
    for line in text.split("\n"):
        line = line.strip()
        if not line:
            continue
        out.extend(split_sentences(line))
    return out


def _clip(x, lo=0.0, hi=1.0):
    return max(lo, min(hi, x))


def analyze(text: str, ai_regexes=None):
    sents = _sentences(text)
    n = len(sents)
    words_total = max(1, count_words(text))
    lens = [count_words(s) for s in sents]
    parts = {}

    if n < 3:
        return {"score": 0.0, "parts": {}, "stats": {"sentences": n, "words": words_total}, "note": "kifayət qədər cümlə yoxdur"}

    mean = sum(lens) / n
    var = sum((l - mean) ** 2 for l in lens) / n
    std = math.sqrt(var)
    cv = std / mean if mean else 0

    # 1. cümlə uzunluğu dəyişkənliyi (burstiness)
    p_cv = _clip((0.60 - cv) / 0.35)
    sorted_l = sorted(lens)
    median = sorted_l[n // 2]
    near_median = sum(1 for l in lens if abs(l - median) <= max(3, 0.25 * median)) / n
    p_med = _clip((near_median - 0.45) / 0.35)
    parts["burstiness"] = (0.65 * p_cv + 0.35 * p_med, 24, f"CV={cv:.2f}, medianətrafı={near_median:.0%}")

    # 2. başlanğıc təkrarı və bağlayıcı sıxlığı
    firsts = [az_lower(words_of(s)[0]) if words_of(s) else "" for s in sents]
    fc = Counter(firsts)
    repeated_first = sum(c for w, c in fc.items() if c >= 3) / n
    bigrams = Counter(" ".join(az_lower(w) for w in words_of(s)[:2]) for s in sents)
    repeated_bi = sum(c for w, c in bigrams.items() if c >= 3) / n
    conn = 0
    conn_seq = 0
    prev = False
    for s in sents:
        d = detect_opener(s)
        is_c = d is not None
        conn += is_c
        if is_c and prev:
            conn_seq += 1
        prev = is_c
    conn_share = conn / n
    parts["openers"] = (_clip(0.6 * repeated_first + 0.4 * repeated_bi) * 1.0, 12, f"təkrar başlanğıc={repeated_first:.0%}")
    parts["connectors"] = (_clip((conn_share - 0.15) / 0.30) * 0.8 + _clip(conn_seq / max(1, n / 4)) * 0.2, 12, f"bağlayıcı ilə başlayan={conn_share:.0%}")

    # 3. klişe sıxlığı
    hits = 0
    if ai_regexes:
        low_text = az_lower(text)
        for rx in ai_regexes:
            hits += len(rx.findall(low_text))
    per100 = hits * 100.0 / words_total
    parts["cliches"] = (_clip(per100 / 2.5), 14, f"{hits} klişe ifadə (100 sözə {per100:.1f})")

    # 4. leksik təkrar
    toks = [az_lower(w) for w in words_of(text)]
    content = [w for w in toks if len(w) >= 5 and w not in STOPWORDS]
    cc = Counter(content)
    top5 = sum(c for _, c in cc.most_common(5)) / max(1, len(content))
    tri = Counter(zip(toks, toks[1:], toks[2:]))
    rep_tri = sum(c for c in tri.values() if c >= 2) / max(1, len(toks))
    stems = Counter(w[:5] for w in content)
    stem_rep = sum(c for _, c in stems.items() if c >= 4) / max(1, len(content))
    parts["repetition"] = (_clip((top5 - 0.06) / 0.10) * 0.4 + _clip(rep_tri / 0.08) * 0.3 + _clip((stem_rep - 0.15) / 0.30) * 0.3, 12, f"top5={top5:.0%}, 3-qram={rep_tri:.1%}")

    # 5. struktur paralellik (ardıcıl cümlələr eyni forma)
    par = 0
    for i in range(n - 2):
        a, b, c = lens[i:i + 3]
        if max(a, b, c) - min(a, b, c) <= 3:
            par += 1
    end_cop = sum(1 for s in sents if ENDING_COPULA.search(az_lower(s.strip()))) / n
    parts["parallelism"] = (_clip(par / max(1, n - 2) / 0.30) * 0.5 + _clip((end_cop - 0.45) / 0.40) * 0.5, 10, f"paralel üçlülər={par}, -dır ilə bitən={end_cop:.0%}")

    # 6. durğu və "və" monotonluğu
    punct_types = sum(1 for ch in ";:—–()?!" if ch in text)
    commas = [s.count(",") for s in sents]
    comma_std = math.sqrt(sum((c - sum(commas) / n) ** 2 for c in commas) / n)
    ve_share = sum(1 for s in sents if s.count(" və ") >= 2) / n
    parts["punctuation"] = (_clip((2 - punct_types) / 2) * 0.4 + _clip((1.1 - comma_std) / 1.1) * 0.35 + _clip(ve_share / 0.25) * 0.25, 8, f"durğu növü={punct_types}, vergül σ={comma_std:.2f}")

    # 7. nominalizasiya sıxlığı (…ılması/…ilməsi)
    nom = sum(len(NOMINALIZATION.findall(az_lower(s))) for s in sents) / n
    parts["nominalization"] = (_clip((nom - 0.35) / 0.9), 8, f"cümləyə {nom:.2f} feli isim")

    score = 0.0
    total_w = 0.0
    for k, (v, w, _) in parts.items():
        score += v * w
        total_w += w
    score = score / total_w * 100.0
    return {
        "score": round(score, 1),
        "parts": {k: {"penalty": round(v, 3), "weight": w, "note": note} for k, (v, w, note) in parts.items()},
        "stats": {"sentences": n, "words": words_total, "mean_len": round(mean, 1), "cv": round(cv, 2)},
    }
