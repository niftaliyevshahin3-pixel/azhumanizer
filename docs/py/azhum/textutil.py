"""Azərbaycan dili üçün mətn əsasları: hərf registri, tokenləşmə, cümlə bölgüsü.

Python-un standart lower()/upper() metodları "İ/I/ı/i" cütünü Azərbaycan/Türk
qaydası ilə çevirmir ("İ".lower() -> "i̇", iki kod nöqtəsi). Bütün modullar
yalnız buradakı az_lower/az_upper/az_cap funksiyalarından istifadə edir.
"""
import re

_LOWER_MAP = {ord("I"): "ı", ord("İ"): "i"}
_UPPER_MAP = {ord("i"): "İ", ord("ı"): "I"}

LETTER = r"[^\W\d_]"
WORD_RE = re.compile(r"[^\W\d_]+(?:[-’'][^\W\d_]+)*", re.UNICODE)
TOKEN_RE = re.compile(
    r"(?P<w>[^\W\d_]+(?:[-’'][^\W\d_]+)*)"
    r"|(?P<n>\d+(?:[.,]\d+)*)"
    r"|(?P<s>\s+)"
    r"|(?P<p>.)",
    re.UNICODE,
)

VOWELS = set("aeıioöuüə")
BACK_VOWELS = set("aıou")
FRONT_VOWELS = set("eiöüə")
ROUNDED = set("oöuü")


def az_lower(s: str) -> str:
    return s.translate(_LOWER_MAP).lower()


def az_upper(s: str) -> str:
    return s.translate(_UPPER_MAP).upper()


def az_cap(s: str) -> str:
    """Yalnız ilk hərfi böyüdür (qalanına toxunmur)."""
    return (az_upper(s[0]) + s[1:]) if s else s


def az_uncap(s: str) -> str:
    return (az_lower(s[0]) + s[1:]) if s else s


def is_upper_char(ch: str) -> bool:
    return ch.isalpha() and ch == az_upper(ch) and ch != az_lower(ch)


def is_capitalized(word: str) -> bool:
    return bool(word) and is_upper_char(word[0])


def is_all_caps(word: str) -> bool:
    letters = [c for c in word if c.isalpha()]
    return len(letters) >= 2 and all(is_upper_char(c) for c in letters)


def match_case(original: str, replacement: str) -> str:
    """Orijinalın hərf registrini əvəzləməyə tətbiq edir."""
    if not original or not replacement:
        return replacement
    if is_all_caps(original):
        return az_upper(replacement)
    if is_capitalized(original):
        return az_cap(replacement)
    return replacement


def count_words(s: str) -> int:
    return len(WORD_RE.findall(s))


def words_of(s: str):
    return WORD_RE.findall(s)


def tokenize(s: str):
    """[(kind, text)] — kind: w (söz), n (say), s (boşluq), p (durğu/digər)."""
    out = []
    for m in TOKEN_RE.finditer(s):
        out.append((m.lastgroup, m.group()))
    return out


def detokenize(tokens) -> str:
    return "".join(t[1] for t in tokens)


def last_vowel(word: str):
    for ch in reversed(az_lower(word)):
        if ch in VOWELS:
            return ch
    return None


def vowel_count(word: str) -> int:
    return sum(1 for ch in az_lower(word) if ch in VOWELS)


# ----------------------------------------------------------------------
# Cümlə bölgüsü
# ----------------------------------------------------------------------
ABBREVIATIONS = {
    "məs", "bax", "səh", "prof", "dos", "akad", "dr", "ing", "rus", "ml", "mlrd", "mln", "st", "fig",
    "tab", "nr", "red", "tərc", "müəl", "gen", "kap", "ünv", "cild", "hs", "tel", "küç", "pr", "kv", "sm", "mr",
}

_SENT_END_RE = re.compile(r"([.!?…]+[\"»”’')\]]*)(\s+)")


def split_sentences(paragraph: str):
    """Paraqrafı cümlələrə bölür. Ixtisarlar, ondalıq ədədlər və baş hərf
    ilkinləri ("H. Əliyev") cümlə sonu sayılmır. Boşluqlar itirilmir:
    hər elementin sonunda qalan boşluq ayrıca qaytarılmır, cümlələr
    " ".join ilə birləşdirilə bilər."""
    text = paragraph.strip()
    if not text:
        return []
    sentences = []
    start = 0
    for m in _SENT_END_RE.finditer(text):
        end_punct = m.group(1)
        end = m.end(1)
        nxt = text[m.end():m.end() + 1]
        if not nxt:
            continue
        # növbəti simvol böyük hərf / rəqəm / dırnaq / mötərizə olmalıdır
        if not (is_upper_char(nxt) or nxt.isdigit() or nxt in "\"«“('[—–-•"):
            continue
        if end_punct.startswith("."):
            before = text[start:m.start()]
            wm = re.search(r"([^\W\d_]+)$", before)
            if wm:
                w = wm.group(1)
                # ad ilkini ("H. Əliyev") və ya bilinən ixtisarı cümlə sonu saymırıq
                if (len(w) == 1 and is_upper_char(w)) or az_lower(w) in ABBREVIATIONS:
                    continue
            if re.search(r"\d$", before) and nxt.isdigit():
                continue
        sentences.append(text[start:end].strip())
        start = m.end()
    tail = text[start:].strip()
    if tail:
        sentences.append(tail)
    return sentences


def split_paragraphs(text: str):
    """Mətni sətir-sətir saxlayır: [(is_blank, line)]."""
    return [(not ln.strip(), ln) for ln in text.split("\n")]


_HEADING_HINT = re.compile(r"^\s*(?:\d+(?:\.\d+)*[.)]?\s+)?\S.{0,90}$")
_BULLET_RE = re.compile(r"^\s*(?:[-•*–—]|\d+[.)])\s+")


def looks_like_heading(line: str) -> bool:
    s = line.strip()
    if not s:
        return False
    if s[-1] in ".!?…:;":
        return False
    return count_words(s) <= 12


def has_sentence_end(line: str) -> bool:
    return bool(re.search(r"[.!?…][\"»”’')\]]*\s*$", line.strip()))
