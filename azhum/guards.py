"""Məna-qoruma süzgəcləri: hər mərhələdən sonra nəticə orijinalla yoxlanılır,
uğursuz olarsa mərhələ geri qaytarılır."""
import re
from collections import Counter
from .textutil import az_lower, count_words, is_upper_char, words_of

PH_OPEN, PH_CLOSE = "", ""
_NUM_RE = re.compile(r"\d+(?:[.,]\d+)*")
_PH_RE = re.compile(PH_OPEN + r"\d+" + PH_CLOSE)


def _numbers(text):
    return Counter(_NUM_RE.findall(_PH_RE.sub("", text)))


def _placeholders(text):
    return Counter(_PH_RE.findall(text))


def _mid_caps(text):
    """Cümlə ortasında böyük hərflə başlayan sözlər (xüsusi adlar)."""
    caps = []
    for sent in re.split(r"(?<=[.!?…])\s+", text):
        ws = words_of(sent)
        for w in ws[1:]:
            if is_upper_char(w[0]) and len(w) > 1:
                caps.append(az_lower(w))
    return caps


def dup_words(text):
    lw = [az_lower(w) for w in words_of(text)]
    bad = []
    for a, b in zip(lw, lw[1:]):
        if a == b and len(a) > 1 and a not in ("da", "də"):
            bad.append(a)
    return bad


def _balanced(text):
    depth = 0
    for ch in text:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth < 0:
                return False
    return depth == 0


def check(original: str, candidate: str, max_len_ratio=(0.72, 1.30)):
    """None = keçdi; sətir = uğursuzluq səbəbi."""
    if _numbers(original) != _numbers(candidate):
        return "rəqəmlər dəyişdi"
    if _placeholders(original) != _placeholders(candidate):
        return "qorunan hissə itdi"
    if not _balanced(candidate) and _balanced(original):
        return "mötərizə balansı pozuldu"
    cand_low_words = Counter(az_lower(w) for w in words_of(candidate))
    for w in _mid_caps(original):
        # xüsusi ad (və ya onun şəkilçili forması) yeni mətndə də olmalıdır
        if cand_low_words.get(w, 0) == 0 and not any(k.startswith(w[:max(3, len(w) - 3)]) for k in cand_low_words):
            return "xüsusi ad itdi: " + w
    if dup_words(candidate) and not dup_words(original):
        return "təkrarlanan söz: " + dup_words(candidate)[0]
    ow, nw = count_words(original), count_words(candidate)
    if ow >= 8:
        r = nw / ow
        if r < max_len_ratio[0] or r > max_len_ratio[1]:
            return "uzunluq həddindən artıq dəyişdi"
    if re.search(r"\s[,.;:!?]", candidate) and not re.search(r"\s[,.;:!?]", original):
        return "durğudan əvvəl artıq boşluq"
    if re.search(r"[,;:]{2,}|\.\.(?!\.)|,\.|\.,", candidate) and not re.search(r"[,;:]{2,}|\.\.(?!\.)|,\.|\.,", original):
        return "iki durğu ardıcıl"
    return None


def check_sentence_form(sentence: str):
    s = sentence.strip()
    if not s:
        return "boş cümlə"
    if s[-1] not in ".!?…\"»)”" and not s.endswith(PH_CLOSE):
        return "cümlə sonu durğusu yoxdur"
    if s[0].isdigit():
        return None
    first = next((c for c in s if c.isalpha()), "")
    if first and not is_upper_char(first) and not s[0] in "(\"«“[" and not s.startswith(PH_OPEN):
        return "cümlə kiçik hərflə başlayır"
    return None
