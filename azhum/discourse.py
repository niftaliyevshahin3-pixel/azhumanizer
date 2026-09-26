"""Sənəd-daxili təkrarların azaldılması: başlanğıc subyekt təkrarı, doldurucu sözlər.

Azərbaycan dili "pro-drop" dilidir: fel şəxs/say uzlaşması mənanı daşıdığı üçün
təkrarlanan subyekt təbii şəkildə buraxıla bilər. AI mətnləri isə mövzu adını
hər cümlədə təkrar çağırmağa meyllidir — detektorlar üçün güclü siqnal.
"""
import re
from .textutil import az_cap, az_lower, az_uncap, count_words, is_upper_char
from . import restructure as rs

DETERMINERS = {"bir", "çox", "hər", "bütün", "bəzi", "digər", "başqa", "bu", "o", "həmin", "belə", "elə", "ən", "daha", "yeni",
               "böyük", "kiçik", "bəzən", "hələ", "artıq", "yalnız", "təkcə", "hətta", "eyni", "iki", "üç", "dörd", "beş", "min"}
PRONOUN_STARTS = {"o", "bu", "onlar", "bunlar", "biz", "siz", "mən", "sən", "həmin", "belə", "hər", "bütün", "bəzi", "digər"}
MAX_LEAD_WORDS = 4
_LEAD_WORD = re.compile(r"^[^\W\d_]+(?:-[^\W\d_]+)*")


def lead_words(sentence: str, n=MAX_LEAD_WORDS):
    words = []
    rest = sentence
    for _ in range(n):
        m = _LEAD_WORD.match(rest)
        if not m:
            break
        words.append(m.group(0))
        rest = rest[m.end():]
        sp = re.match(r"^\s+", rest)
        if not sp:
            break
        rest = rest[sp.end():]
    return words


def _has_predicate(rest: str) -> bool:
    return not rs.has_no_likely_predicate(rest, [])


NOUN_SUFFIXES = ("iya", "ika", "lik", "lıq", "luq", "lük", "çılıq", "çilik", "çuluq", "çülük", "ət", "at", "yat", "izm", "ist", "üzm", "alar", "lər", "lar")
ADJ_LIKE = ("ik", "iv", "al", "el", "li", "lı", "lu", "lü", "sız", "siz", "suz", "süz", "vi", "yi", "ci", "cü", "cu", "cı")


def _lead_is_subject_like(words) -> bool:
    """Lead ifadəsi tam subyekt (ad) kimi görünürmü?"""
    if len(words) >= 2:
        last = az_lower(words[-1])
        return not last.endswith(ADJ_LIKE) or last.endswith(("lik",))
    w = az_lower(words[0])
    if w.endswith(NOUN_SUFFIXES):
        return True
    return len(w) >= 9 and not w.endswith(ADJ_LIKE)


def _continues_np(next_word: str) -> bool:
    """Növbəti söz lead ifadəsi ilə ad birləşməsi/feli isim təşkil edə bilərmi?"""
    w = az_lower(next_word)
    if w.endswith(("maq", "mək", "ması", "məsi", "mağı", "məyi", "ma", "mə")):
        return True
    if len(w) >= 5 and w[-1] in "ıiuü":
        return True
    return False


def diversify_lead_subjects(sess, sents):
    """Paraqrafda eyni başlanğıc mövzu-ifadəsi 3+ dəfə təkrarlanırsa, 2-ci və sonrakıları
    subyekti silməklə (pro-drop) və ya əvəzliklə dəyişir."""
    leads = [lead_words(s) for s in sents]
    out = list(sents)
    handled = set()
    for L in range(MAX_LEAD_WORDS, 0, -1):
        groups = {}
        for i, ld in enumerate(leads):
            if i in handled or len(ld) < L:
                continue
            phrase = " ".join(az_lower(w) for w in ld[:L])
            if len(phrase) < 4 or (L == 1 and phrase in PRONOUN_STARTS) or az_lower(ld[0]) in DETERMINERS:
                continue
            if not _lead_is_subject_like(ld[:L]):
                continue
            groups.setdefault(phrase, []).append(i)
        for phrase, idxs in groups.items():
            if len(idxs) < 3:
                continue
            nexts = [az_lower(leads[k][L]) if len(leads[k]) > L else "" for k in idxs]
            # ortaq növbəti söz => lead daha uzun ifadənin hissəsi (bu L səviyyəsində toxunma)
            if any(nexts.count(x) > 1 for x in nexts if x):
                continue
            for k in idxs[1:]:
                # yalnız BİRBAŞA əvvəlki cümlə də eyni ifadə ilə başlayırsa (mövzu davamlılığı)
                if k - 1 not in idxs:
                    continue
                s = out[k]
                m = re.match(r"^(?:\S+\s+){%d}" % (L - 1) + r"\S+", s)
                if not m:
                    continue
                lead_text = m.group(0)
                nxt_word = leads[k][L] if len(leads[k]) > L else ""
                if not nxt_word or _continues_np(nxt_word):
                    continue
                rest = s[len(lead_text):].lstrip(" ,")
                if not rest or count_words(rest) < 4 or not _has_predicate(rest):
                    continue
                if "" in lead_text or lead_text.rstrip().endswith((",", ";", ":")):
                    continue
                r = sess.rng.random()
                plural = az_lower(leads[k][L - 1]).endswith(("lar", "lər"))
                if r < 0.6:
                    new = az_cap(rest)
                    kind = "subject_drop"
                else:
                    pr = "Onlar" if plural else "O"
                    new = f"{pr}, {az_uncap(rest)}"
                    kind = "subject_pronoun"
                sess.log(kind, s, new)
                out[k] = new
                handled.add(k)
            for k in idxs:
                handled.add(k)
    return out


_ISE_TOPIC = re.compile(r"^((?:\S+\s+){0,3}?\S+(?:də|da|dən|dan|dır|dir|nda|ndə|ndan|ndən|ində|ında|ilə|la|lə))\s+isə\s+", re.IGNORECASE)


def drop_fillers(sess, sentence: str):
    """"Tibb sahəsində isə X" -> "Tibb sahəsində X" (mövzu-işarəsi "isə"nin silinməsi)."""
    if sess.rng.random() > 0.35 * sess.p["struct"] / 0.30:
        return sentence
    s = sentence
    m = _ISE_TOPIC.match(s)
    if m and count_words(s) >= 7 and "," not in s[:m.end()]:
        new = m.group(1) + " " + s[m.end():]
        sess.log("filler_drop", s, new)
        return new
    return sentence
