"""Cümlə strukturu: uzun cümlənin bölünməsi, qısaların birləşdirilməsi,
başlanğıc zərflik yerdəyişməsi, uyğun cütlərin sıra dəyişməsi.

Qaydalar sadə heuristikalara əsaslanır (Azərbaycan dili üçün etibarlı sərbəst
sintaktik parser yoxdur). Hər əməliyyat yalnız "fel/predikat" yoxlamasından və
bir sıra təhlükəsizlik süzgəclərindən keçəndə tətbiq olunur. JS mühərrikindəki
(docgen/humanizer/sentence_restructurer.js) sərt test olunmuş məntiq bura
köçürülüb və genişləndirilib.
"""
import re
from .textutil import az_lower, az_cap, az_uncap, count_words, is_capitalized, is_upper_char, words_of

W = r"[^\W\d_]"

# Sənəddə kiçik hərflə rast gəlinən sözlər + lüğət formaları (engine tərəfindən doldurulur):
# cümlə başında böyük yazılmış sözün ümumi ad olduğunu (xüsusi ad DEYİL) təsdiq etmək üçün.
KNOWN_LOWER = set()
_ALWAYS_COMMON = {
    "bu", "o", "onlar", "bunlar", "bizim", "sizin", "onun", "bunun", "həmin", "belə", "elə", "hər", "bütün", "bəzi", "digər",
    "başqa", "lakin", "amma", "ancaq", "həmçinin", "üstəlik", "bundan", "buna", "bunu", "bunda", "ona", "onu", "orada", "burada",
    "bir", "iki", "üç", "çox", "az", "daha", "ən", "artıq", "hələ", "yalnız", "təkcə", "məsələn", "beləliklə", "nəticədə",
    "əvvəlcə", "sonra", "sonradan", "eyni", "yeni", "belə", "necə", "niyə", "nə", "kim", "hansı", "əgər", "çünki", "yəni", "həm",
    "biz", "siz", "mən", "sən", "bəzən", "adətən", "hazırda", "indi", "dünən", "bugün",
}


DOC_PROPER = set()
PROPER_LIST = set("""azərbaycan bakı gəncə sumqayıt naxçıvan şuşa xankəndi lənkəran şəki mingəçevir şirvan qarabağ türkiyə rusiya gürcüstan
iran irak ukrayna almaniya fransa ingiltərə britaniya amerika abş çin yaponiya hindistan avropa asiya afrika avstraliya
şərq qərb mars yupiter saturn venera merkuri neptun uran allah quran bibliya islam xristianlıq atatürk nizami füzuli
nəsimi vaqif səməd ağa əliyev heydər ilham dünya birləşmiş millətlər nato avroparlament aran kür araz xəzər qafqaz""".split())
_SURNAME_SUFFIXES = ("ov", "ova", "ev", "eva", "yev", "yeva", "zadə", "oğlu", "qızı", "ski", "dze", "yan", "ian")


def set_known_lower(words, proper=()):
    global KNOWN_LOWER, DOC_PROPER
    KNOWN_LOWER = set(words)
    DOC_PROPER = set(proper)


def looks_proper(word: str, next_word: str = "") -> bool:
    w = az_lower(word.strip(",.;:!?\"«»()"))
    if not w:
        return True
    if w in DOC_PROPER or w in PROPER_LIST:
        return True
    if any(ch.isdigit() for ch in w) or "-" in w:
        return True
    if len(word) > 1 and word.isupper():
        return True
    if next_word and is_upper_char(next_word[:1]):
        return True
    return w.endswith(_SURNAME_SUFFIXES) and len(w) > 4


def can_lowercase_first(word: str, next_word: str = "") -> bool:
    """Cümlə başındakı sözü kiçik hərflə yazmaq təhlükəsizdirmi (xüsusi ad DEYİL)?"""
    w = az_lower(word.strip(",.;:!?\"«»()"))
    if not w:
        return False
    if w in _ALWAYS_COMMON or w in KNOWN_LOWER:
        return w not in DOC_PROPER
    return not looks_proper(word, next_word)


SPLIT_CONJUNCTIONS = [" və ", ", lakin ", ", amma ", ", ancaq ", ", buna görə ", ", ona görə ki ", ", eləcə də ", ", habelə "]

# Qəti (birmənalı) fel formaları: adlarla qarışdırılmasın deyə (köpür, əsir, nadir...)
_COMMON_STEMS = """et ol ver al gəl get qal bil gör yaz tut qoy çıx düş keç aç yığ sev dur yat qur at çək sür bax san iç ye de vur
sat tap apar gətir yet çat qat saç seç sıx unut yan yıx öl dol gül ağla çal sal dağ say ver qaç soruş oyna başla
danış çalış düşün yaşa ye qazan verə tanı anla uyğunlaş inkişaf et əks et təsir et
yarat artır azalt göstər əmələ gətir istifadə et təmin et""".split()

_TENSE_END = re.compile(r"(mışdır|mişdir|muşdur|müşdür|acaq|əcək|maqdadır|məkdədir|mışlar|mişlər|dılar|dilər|dular|dülər)$")
_PAST_END = re.compile(r"(dı|di|du|dü)(lar|lər)?$")
_COPULA_END = re.compile(r"(dır|dir|dur|dür)(lar|lər)?$")
_PRESENT_END = re.compile(r"(ır|ir|ur|ür)(lar|lər)?$")
_VOWEL_BUFFER = re.compile(r"(yır|yir|yur|yür)(lar|lər)?$")
_DERIV_STEM_END = re.compile(r"(əl|al|laş|ləş|lan|lən|ıl|il|ul|ül|un|ün|an|ən|ın|in|ar|ər|dır|dir|dur|dür|tır|tir|tur|tür|ıt|it|ut|üt|ır|ir|ur|ür|ıx|ik)$")


def _build_common_present():
    from . import morph
    forms = set()
    for st in _COMMON_STEMS:
        for pl in (0, 1):
            f = morph.realize_verb(st, ("v", "pres", 0, pl, 0))
            if f:
                forms.add(f.split(" ")[-1])
    return forms


_COMMON_PRESENT = None


def is_strong_finite(word: str) -> bool:
    """Sözün birmənalı finit fel/xəbər olub-olmadığı (heuristika)."""
    global _COMMON_PRESENT
    w = az_lower(re.sub(r"[^\w]", "", word))
    if len(w) < 4 or w in FALSE_POSITIVES:
        return False
    if _TENSE_END.search(w):
        return True
    if _PAST_END.search(w) and not w.endswith(("ədi", "adi", "şdi")) :
        stem = _PAST_END.sub("", w)
        return len(stem) >= 2 and not stem.endswith(("ı", "i")) or stem.endswith(("a", "ə", "u", "ü", "o", "ö", "e"))
    if _COPULA_END.search(w):
        return True
    if _VOWEL_BUFFER.search(w):
        return True
    m = _PRESENT_END.search(w)
    if m:
        if _COMMON_PRESENT is None:
            _COMMON_PRESENT = _build_common_present()
        if w in _COMMON_PRESENT:
            return True
        stem = w[:m.start()]
        return len(stem) >= 3 and _DERIV_STEM_END.search(stem) is not None
    return False


FALSE_POSITIVES = {
    "müasir", "iqtisadi", "makroiqtisadi", "mikroiqtisadi", "sosialiqtisadi", "adi", "qeyriadi",
    "maddi", "fərdi", "əbədi", "ədədi", "gələcək", "misir", "zəruri", "ilkin", "qadir", "əsir",
    "nadir", "vacib", "kimi", "sahibkar", "vətəndaş", "bir", "idari", "mədəni", "hüquqi",
    "siyasi", "tibbi", "elmi", "milli", "bədii", "dini", "əxlaqi", "tarixi", "sosial", "məntiqi",
    "sənayeləşmiş", "kiçik", "böyük", "yeni", "əsas", "onlar", "yaşıl", "ali", "xarici", "daxili",
    "ictimai", "ekoloji", "texniki", "kütləvi", "orta", "sadə", "əhəmiyyətli", "aktual", "çətin",
    "alimlər", "mütəxəssislər", "tədqiqatçılar", "müəlliflər", "ölkələr", "insanlar", "şirkətlər",
    "hər", "digər", "bütün", "həmin", "belə", "ayrı", "başqa",
}

FRONTED_MARKER_RE = re.compile(r"^" + W + r"[^\W\d_'-]*(?:\s+" + W + r"[^\W\d_]*){0,3},", re.UNICODE)


_OWN_SUBJECT_STARTS = {"bu", "o", "onlar", "bunlar", "həmin", "onun", "bunun", "biz", "siz", "mən", "sən", "belə", "elə"}


def has_unbalanced_open_paren(text_before: str) -> bool:
    depth = 0
    for ch in text_before:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth = max(0, depth - 1)
    return depth > 0


def _has_open_quote(text_before: str) -> bool:
    return (text_before.count('"') % 2 == 1) or (text_before.count("«") > text_before.count("»"))


def trailing_segment(text_before: str, conjunctions=()):
    boundary = -1
    last = max(text_before.rfind(","), text_before.rfind(":"), text_before.rfind(";"))
    if last != -1:
        boundary = last + 1
    for conj in conjunctions:
        start = 0
        while True:
            i = text_before.find(conj, start)
            if i == -1:
                break
            start = i + len(conj)
            boundary = max(boundary, i + len(conj))
    return text_before if boundary == -1 else text_before[boundary:]


def is_short_list_segment(text_before: str) -> bool:
    if not any(text_before.rfind(c) != -1 for c in ",:;"):
        return False
    return count_words(trailing_segment(text_before).strip()) < 4


def strip_false_positive_words(text: str) -> str:
    keep = []
    for w in text.split():
        cleaned = az_lower(re.sub(r"[^\w]", "", w))
        if cleaned in FALSE_POSITIVES:
            continue
        keep.append(w)
    return " ".join(keep)


def has_no_likely_predicate(text_before: str, conjunctions=None) -> bool:
    conjunctions = SPLIT_CONJUNCTIONS if conjunctions is None else conjunctions
    seg = trailing_segment(text_before, conjunctions)
    return not any(is_strong_finite(w) for w in seg.split())


def starts_with_fronted_marker(text: str) -> bool:
    m = FRONTED_MARKER_RE.match(text.strip())
    if not m:
        return False
    lead = m.group(0)[:-1]
    return has_no_likely_predicate(lead)


def ends_with_hedge_verb(text_before: str) -> bool:
    words = text_before.split()
    return bool(words) and is_strong_finite(words[-1])


def collect_split_candidates(sentence: str, conjunctions=None):
    conjunctions = SPLIT_CONJUNCTIONS if conjunctions is None else conjunctions
    cands = []
    for conj in conjunctions:
        start = 0
        while True:
            idx = sentence.find(conj, start)
            if idx == -1:
                break
            start = idx + len(conj)
            if idx <= 10 or idx >= len(sentence) - 10:
                continue
            if sentence[idx + len(conj): idx + len(conj) + 3] == "ya ":
                continue  # "və ya"
            before = sentence[:idx]
            if has_unbalanced_open_paren(before) or _has_open_quote(before):
                continue
            if is_short_list_segment(before):
                continue
            if has_no_likely_predicate(before, conjunctions):
                continue
            if not is_strong_finite(before.split()[-1]):
                continue  # SOV: fel klauzun sonunda olmalıdır
            left = before.strip()
            right = sentence[idx + len(conj):].strip()
            if not left or not right:
                continue
            if starts_with_fronted_marker(right):
                continue
            if az_lower(left.split()[-1].strip(",.")) == "gəlir" and az_lower(right).startswith("xərc"):
                continue
            # sağ tərəfin də öz predikatı olmalıdır
            if has_no_likely_predicate(right, []):
                continue
            if not is_strong_finite(right.rstrip(".!?… ").split()[-1]):
                continue  # sağ klauz da öz felinə malik olmalıdır
            if conj.strip() == "və" and az_lower(right.split()[0].strip(",")) not in _OWN_SUBJECT_STARTS:
                continue  # "və" ilə bölünən sağ klauzun öz subyekti açıq olmalıdır (əks halda subyekt itir)
            cands.append({"conj": conj, "left": left, "right": right, "imb": abs(count_words(left) - count_words(right))})
    return cands


START_CONJ = ["bu isə", "nəticədə", "beləliklə", "həmçinin", "bununla belə", "buna görə də", "ona görə də",
              "eyni zamanda", "bundan başqa", "üstəlik", "habelə", "məsələn", "buna baxmayaraq", "bunun nəticəsində"]


def collect_startconj_candidates(sentence: str):
    """"X edir, bu isə Y edir." -> "X edir. Bu isə Y edir." (bağlayıcı yeni cümləni açır)."""
    cands = []
    for conj in START_CONJ:
        for tail in (" ", ","):
            pat = ", " + conj + tail
            start = 0
            while True:
                idx = sentence.find(pat, start)
                if idx == -1:
                    break
                start = idx + len(pat)
                if idx <= 10 or idx >= len(sentence) - 12:
                    continue
                before = sentence[:idx]
                if has_unbalanced_open_paren(before) or _has_open_quote(before) or is_short_list_segment(before):
                    continue
                if not is_strong_finite(before.split()[-1]):
                    continue
                right = sentence[idx + 2:].strip()
                if has_no_likely_predicate(right, []) or not is_strong_finite(right.rstrip(".!?… ").split()[-1]):
                    continue
                left = before.strip()
                cands.append({"type": "startconj", "left": left, "right": right, "imb": abs(count_words(left) - count_words(right))})
    return cands


def collect_ki_candidates(sentence: str):
    cands = []
    pat = " ki,"
    start = 0
    while True:
        idx = sentence.find(pat, start)
        if idx == -1:
            break
        start = idx + len(pat)
        if idx <= 5 or idx >= len(sentence) - 10:
            continue
        before = sentence[:idx]
        if not ends_with_hedge_verb(before):
            continue
        if has_unbalanced_open_paren(before) or _has_open_quote(before) or is_short_list_segment(before):
            continue
        left = before.strip()
        right = sentence[idx + len(pat):].strip()
        if not left or not right:
            continue
        local = trailing_segment(before, SPLIT_CONJUNCTIONS).strip()
        if count_words(local) < 3:
            continue
        if has_no_likely_predicate(right, []):
            continue
        if starts_with_fronted_marker(right):
            continue
        cands.append({"type": "ki", "left": left, "right": right, "imb": abs(count_words(left) - count_words(right))})
    return cands


def collect_semicolon_candidates(sentence: str):
    cands = []
    start = 0
    while True:
        idx = sentence.find("; ", start)
        if idx == -1:
            break
        start = idx + 2
        before = sentence[:idx]
        if has_unbalanced_open_paren(before) or _has_open_quote(before):
            continue
        left = before.strip()
        right = sentence[idx + 2:].strip()
        if count_words(left) < 4 or count_words(right) < 4:
            continue
        if has_no_likely_predicate(before, []) or has_no_likely_predicate(right, []):
            continue
        cands.append({"type": "semi", "left": left, "right": right, "imb": abs(count_words(left) - count_words(right))})
    return cands


def _end(s: str) -> str:
    return s if s[-1:] in ".!?…" else s + "."


def try_split(sentence: str, rng, bridge_prob=0.0, bridge_pool=None):
    """Ən çox uzunluq kontrastı yaradan etibarlı nöqtədə bölür. [a, b] ya None."""
    cands = (collect_split_candidates(sentence) + collect_ki_candidates(sentence) + collect_semicolon_candidates(sentence)
             + collect_startconj_candidates(sentence))
    if not cands:
        return None
    cands.sort(key=lambda c: -c["imb"])
    # ən böyük kontrastlılardan birini seç (determinizm yox, seed-li təsadüfilik)
    top = [c for c in cands if c["imb"] >= cands[0]["imb"] - 3]
    best = top[rng.randrange(len(top))]
    left = _end(best["left"])
    right = best["right"]
    right_cap = az_cap(right)
    if best.get("type") in ("ki", "semi", "startconj"):
        return [left, _end(right_cap)]
    conj = best["conj"].strip().lstrip(",").strip()
    key = az_lower(conj)
    if key in ("və", "eləcə də", "habelə"):
        if bridge_pool and rng.random() < bridge_prob:
            starter = bridge_pool.pick(key)
            return [left, _end(starter + ", " + az_uncap(right))]
        return [left, _end(right_cap)]
    if key in ("lakin", "amma", "ancaq"):
        return [left, _end(az_cap(conj) + " " + az_uncap(right))] if rng.random() < 0.5 else [left, _end(az_cap(conj) + ", " + az_uncap(right))]
    # "buna görə", "ona görə ki"
    return [left, _end(az_cap(conj) + " " + az_uncap(right))]


def looks_like_proper_noun_list(text: str) -> bool:
    return re.match(r"^\w+,\s*\w", text.strip()) is not None and is_upper_char(text.strip()[0])


def try_merge(a: str, b: str, rng):
    """İki qısa cümləni bir cümləyə birləşdirir (nöqtəli vergül, vergül+lakin və ya "və")."""
    if starts_with_fronted_marker(b):
        return None
    if looks_like_proper_noun_list(b):
        return None
    if has_no_likely_predicate(a, []) or has_no_likely_predicate(b, []):
        return None
    if a.count(" və ") + b.count(" və ") >= 4 or a.count(";") + b.count(";") >= 1:
        return None
    a0 = a.rstrip()
    if a0[-1:] in ".!?…":
        a0 = a0[:-1]
    first = b.split()[0] if b.split() else ""
    low_first = az_lower(first.strip(",."))
    b_low = az_uncap(b)
    if len(first) > 1 and first.isupper():
        b_low = b
    second = b.split()[1] if len(b.split()) > 1 else ""
    if not can_lowercase_first(first, second):
        return None  # xüsusi ad ola bilər — kiçik hərflə yazmaq səhv olar
    if low_first in ("lakin", "amma", "ancaq"):
        rest = b[len(first):].lstrip()
        return a0 + ", " + az_lower(first.strip(",")) + " " + az_uncap(rest)
    if detect_starts_with_connector(b):
        return a0 + "; " + b_low
    if low_first in ("bu", "o", "onlar", "bunlar") and rng.random() < 0.35:
        return a0 + " və " + b_low
    return a0 + "; " + b_low


_CONNECTOR_STARTS = ("həmçinin", "bundan", "üstəlik", "lakin", "amma", "ancaq", "beləliklə", "nəticədə", "buna", "bu səbəbdən")


def detect_starts_with_connector(s: str) -> bool:
    low = az_lower(s.lstrip())
    return low.startswith(_CONNECTOR_STARTS)


# ------------------------------------------------------ zərflik yerdəyişməsi
FRONT_ADVERBIALS = [
    "son illərdə", "hazırda", "bu gün", "müasir dövrdə", "praktikada", "əksər hallarda", "çox vaxt", "adətən",
    "bəzən", "ümumiyyətlə", "əsasən", "xüsusilə", "tədricən", "sonradan", "əvvəlcə", "ilk növbədə",
    "günümüzdə", "bir qayda olaraq", "zaman keçdikcə", "tarixən", "nəzəri baxımdan", "praktik baxımdan",
    "iqtisadi baxımdan", "sosial baxımdan", "eyni zamanda", "getdikcə", "bugünkü dövrdə", "son dövrdə",
    "son illər ərzində", "bu gün də", "əlbəttə", "təbii ki", "çox zaman", "bir çox hallarda",
]
FRONT_ADVERBIALS.sort(key=lambda s: -len(s))
SAFE_MID_TO_FRONT = [
    "son illərdə", "hazırda", "bu gün", "müasir dövrdə", "praktikada", "əksər hallarda", "adətən", "bəzən",
    "ümumiyyətlə", "tədricən", "sonradan", "günümüzdə", "bir qayda olaraq", "zaman keçdikcə", "tarixən",
    "son dövrdə", "son illər ərzində", "çox zaman", "bir çox hallarda", "çox vaxt",
]
SAFE_MID_TO_FRONT.sort(key=lambda s: -len(s))
LIGHT_VERBS = {
    "edir", "edilir", "olunur", "olur", "oynayır", "göstərir", "verir", "yaradır", "çəkir", "tapır", "alır",
    "keçirilir", "aparılır", "edirlər", "edə", "bilər", "etmişdir", "olmuşdur", "edilmişdir", "olunmuşdur",
    "edəcək", "olacaq", "edilə", "oluna", "etdi", "oldu", "qazanır", "daşıyır", "kəsb", "qoyur", "tutur",
    "yaradılır", "yaradır", "yaratmışdır", "göstərmişdir", "verilir", "verilmişdir",
}
MODAL_TAIL = {"bilər", "bilir", "bilməz", "bilərlər", "olar", "olmaz"}


def toggle_intro_comma(sentence: str, rng):
    """Qısa giriş zərfliyindən sonrakı vergülü silir ("Son illərdə, X" -> "Son illərdə X")."""
    s = sentence.strip()
    low = az_lower(s)
    for adv in FRONT_ADVERBIALS:
        if low.startswith(adv + ", "):
            rest = s[len(adv) + 2:]
            if count_words(rest) < 5 or rest[:1] == rest[:1].upper() and rest[:2].isupper():
                return None
            return s[:len(adv)] + " " + rest
    return None


def move_mid_adverbial_front(sentence: str, rng):
    """"X hazırda Y edir." -> "Hazırda, X Y edir." """
    s = sentence.strip()
    if "," in s or ";" in s or ":" in s or "(" in s or '"' in s:
        return None
    body = s[:-1] if s[-1:] in ".!?…" else s
    end = s[-1] if s[-1:] in ".!?…" else "."
    words = body.split(" ")
    if len(words) < 6:
        return None
    from .phrases import detect_opener
    if detect_opener(s):
        return None
    lows = [az_lower(w) for w in words]
    for adv in SAFE_MID_TO_FRONT:
        aw = adv.split(" ")
        n = len(aw)
        for i in range(1, len(words) - n):  # ilk mövqe (i=0) və sonuncu istisna
            if lows[i:i + n] == aw and i >= 2:
                rest = words[:i] + words[i + n:]
                first = rest[0]
                # xüsusi ad / abbreviatura ilk söz olmasın (kiçildilməməlidir)
                if len(first) > 1 and first.isupper():
                    return None
                if is_capitalized(first) and len(rest) > 1 and False:
                    return None
                if not can_lowercase_first(first, rest[1] if len(rest) > 1 else ""):
                    return None
                rest[0] = az_uncap(first)
                return az_cap(adv) + ", " + " ".join(rest) + end
    return None


def _is_proper_like(word, sentence_start=False):
    # cümlə başında böyük hərf adi söz ola bilər; onu ayırd etmək çətindir —
    # yalnız iki və daha çox böyük hərf (abbreviatura) və ya rəqəm/tire olarsa qoruyuruq
    return word.isupper() and len(word) > 1


# --------------------------------------------------- sıra dəyişməsi (A və B)
_PAIR_RE = re.compile(r"(?<![\w-])(" + W + r"{4,}) və (" + W + r"{4,})(?![\w-])", re.UNICODE)
NO_SWAP_WORDS = {"birinci", "ikinci", "üçüncü", "dördüncü", "beşinci", "əvvəl", "sonra", "gecə", "gündüz", "yuxarı", "aşağı"}


def swap_pair_order(sentence: str, rng):
    """"iqtisadi və sosial" -> "sosial və iqtisadi" (eyni sonluqlu cütlər)."""
    matches = list(_PAIR_RE.finditer(sentence))
    rng.shuffle(matches)
    for m in matches:
        a, b = m.group(1), m.group(2)
        la, lb = az_lower(a), az_lower(b)
        if la[-3:] != lb[-3:] or la == lb:
            continue
        if la in NO_SWAP_WORDS or lb in NO_SWAP_WORDS:
            continue
        # xüsusi ad / mövqe-böyük hərf
        if is_upper_char(b[0]):
            continue
        start_of_sentence = m.start() == 0
        if is_upper_char(a[0]) and not start_of_sentence:
            continue
        before = sentence[:m.start()]
        # "həm A və B", say/tarix konteksti
        if re.search(r"(həm|hər|ya|nə)\s*$", az_lower(before)):
            continue
        new_a, new_b = b, a
        if start_of_sentence:
            new_a = az_cap(new_a)
            new_b = az_uncap(new_b)
        return sentence[:m.start()] + new_a + " və " + new_b + sentence[m.end():]
    return None


# ---------------------------------------------------------------- yeni üsullar
_BIRI_RE = re.compile(r"(?<![\w-])(" + W + r"*?(?:lərindən|larından|lərdən|lardan)) biridir(?![\w-])", re.UNICODE)
_DIR_RE = re.compile(r"(?<![\w-])(" + W + r"*?(?:lərindən|larından|lərdən|lardan))(dir|dır)(?![\w-])", re.UNICODE)


def biri_dir_toggle(sentence: str, rng):
    """"əsas sahələrindən biridir" <-> "əsas sahələrindəndir" (eyni mənalı iki forma)."""
    m = _BIRI_RE.search(sentence)
    if m:
        w = m.group(1)
        last_v = [c for c in az_lower(w) if c in "aeıioöuüə"][-1]
        suf = "dır" if last_v in "aıou" else "dir"
        return sentence[:m.start()] + w + suf + sentence[m.end():]
    m = _DIR_RE.search(sentence)
    if m:
        return sentence[:m.start()] + m.group(1) + " biridir" + sentence[m.end():]
    return None


def _canon_suffix(word: str) -> str:
    w = az_lower(word)[-2:]
    return w.replace("ə", "a").replace("ı", "i").replace("u", "i").replace("ü", "i")


_HEM_RE = re.compile(r"(?<![\w-])həm ([^,;:.()]+?), həm də ([^,;:.()]+)", re.IGNORECASE | re.UNICODE)


def swap_hem_hem_de(sentence: str, rng):
    """"həm A, həm də B" -> "həm B, həm də A" (paylaşılan xəbər saxlanılır)."""
    m = _HEM_RE.search(sentence)
    if not m:
        return None
    x = m.group(1).strip()
    rest = m.group(2).split(" ")
    x_words = x.split(" ")
    if len(x_words) > 6:
        return None
    target = _canon_suffix(x_words[-1])
    end = None
    for i, w in enumerate(rest[:8]):
        if _canon_suffix(w) == target and len(w) > 3:
            end = i
            break
    if end is None:
        return None
    y = " ".join(rest[:end + 1])
    tail = " ".join(rest[end + 1:])
    if not tail:
        return None
    if count_words(y) > 7 or is_upper_char(y[0]) or is_upper_char(x[0]):
        return None
    if sentence[m.start():m.start() + 3].lower() != "həm":
        return None
    return sentence[:m.start()] + "həm " + y + ", həm də " + x + " " + tail + sentence[m.end():]


def permute_list_inner(sentence: str, rng):
    """"..., A, B, C, D və E ..." — daxili elementlərin (B, C, D) sırası dəyişir."""
    m = re.search(r"((?:[^,;:()]{2,45}, ){3,7})([^,;:()]{2,45}) və ", sentence)
    if not m:
        return None
    items = [x for x in m.group(1).split(", ") if x != ""]
    if len(items) < 3:
        return None
    inner = items[1:]
    if any(count_words(x) > 3 or count_words(x) < 1 for x in inner):
        return None
    if any(not x or is_upper_char(x[0]) for x in inner):
        return None
    if any(is_strong_finite(w) for x in inner for w in x.split()):
        return None
    if len(set(x.lower() for x in inner)) != len(inner):
        return None
    shuffled = inner[:]
    for _ in range(6):
        rng.shuffle(shuffled)
        if shuffled != inner:
            break
    if shuffled == inner:
        return None
    new_seg = items[0] + ", " + ", ".join(shuffled) + ", "
    return sentence[:m.start(1)] + new_seg + sentence[m.end(1):]
