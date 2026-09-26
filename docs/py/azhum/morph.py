"""Azərbaycan dili morfologiyası: isim və fel şəkilçilərinin generasiyası.

Məqsəd: mətndəki "araşdırmasının", "göstərməlidirlər" kimi şəkilçili formanı
(lemma + şablon) kimi tanımaq, sonra EYNİ şablonu sinonimə (məs. "tədqiqat")
tətbiq edərək qrammatik cəhətdən düzgün ("tədqiqatının") forma yaratmaq.
Yalnız aşağıdakı şablonlara TAM uyğun gələn formalar əvəzlənir — tanınmayan
forma toxunulmaz qalır (səhv etmək əvəzinə keçmək).
"""
from .textutil import az_lower, VOWELS, BACK_VOWELS, ROUNDED, vowel_count

# ---------------------------------------------------------------- harmony


def last_vowel_of(word: str):
    for ch in reversed(word):
        if ch in VOWELS:
            return ch
    return "ə"


def a2(word: str) -> str:
    """2-variantlı sait: a / ə."""
    return "a" if last_vowel_of(word) in BACK_VOWELS else "ə"


def i4(word: str) -> str:
    """4-variantlı sait: ı / i / u / ü."""
    v = last_vowel_of(word)
    if v in ("a", "ı"):
        return "ı"
    if v in ("e", "i", "ə"):
        return "i"
    if v in ("o", "u"):
        return "u"
    return "ü"


def kq(word: str) -> str:
    return "q" if last_vowel_of(word) in BACK_VOWELS else "k"


def ends_vowel(word: str) -> bool:
    return bool(word) and word[-1] in VOWELS


# ------------------------------------------------------- stem mutation


def mutate_final(word: str):
    """Saitlə başlayan şəkilçidən əvvəl k->y, q->ğ. Qeyri-müəyyən halda None."""
    w = word
    if not w:
        return None
    if w[-1] == "q":
        return w[:-1] + "ğ" if vowel_count(w) >= 2 else w
    if w[-1] == "k":
        if vowel_count(w) < 2:
            return w
        if w.endswith(("lik", "lük", "lık")):
            return w[:-1] + "y"
        if w.endswith(("ək", "ük", "ök")):
            return w[:-1] + "y"
        if w.endswith("ik") or w.endswith("ık"):
            return w  # xarici mənşəli -ik: mutasiya yoxdur (praktiki, texniki)
        return w
    return w


# ------------------------------------------------------------- noun forms
# şablon = (plural, poss, case, copula)
#   plural: 0/1 ; poss: 0 / 3 (3-cü şəxs tək) ; case: '', gen, dat, acc, loc,
#   abl, ins ; copula: 0/1 (-dır)
CASES = ("", "gen", "dat", "acc", "loc", "abl", "ins")


def noun_keys():
    keys = []
    for pl in (0, 1):
        for poss in (0, 3):
            for case in CASES:
                if case == "ins" and poss:
                    continue
                for cop in (0, 1):
                    if cop and (case not in ("", "loc") or poss and case):
                        # copula yalnız çılpaq / hal-siz (və ya sadə) formada
                        if not (case == "" ):
                            continue
                    keys.append((pl, poss, case, cop))
    return keys


NOUN_KEYS = noun_keys()
# çılpaq, ən çox rast gəlinən forma birinci
NOUN_KEYS.sort(key=lambda k: (k != (0, 0, "", 0),))


def realize_noun(word: str, key):
    """word (lemma, son sözün özü) + şablon -> səth forması. Mümkün deyilsə None."""
    pl, poss, case, cop = key
    base = word
    cur = base

    def needs_vowel_suffix():
        return True

    # 1) cəm
    if pl:
        cur = cur + "l" + a2(cur) + "r"
        # cəmdən sonra kök artıq samitlə bitir (r), mutasiya lazım deyil
    # 2) mənsubiyyət (3-cü şəxs tək)
    if poss == 3:
        if not pl:
            if ends_vowel(cur):
                cur = cur + "s" + i4(cur)
            else:
                m = mutate_final(cur)
                if m is None:
                    return None
                cur = m + i4(cur)
        else:
            # ...lArI
            cur = cur + i4(cur)
        after_poss = True
    else:
        after_poss = False
    # 3) hal
    if case == "":
        pass
    elif case == "gen":
        if after_poss:
            cur += "n" + i4(cur) + "n"
        elif ends_vowel(cur):
            cur += "n" + i4(cur) + "n"
        else:
            m = mutate_final(cur)
            if m is None:
                return None
            cur = m + i4(m) + "n"
    elif case == "dat":
        if after_poss:
            cur += "n" + a2(cur)
        elif ends_vowel(cur):
            cur += "y" + a2(cur)
        else:
            m = mutate_final(cur)
            if m is None:
                return None
            cur = m + a2(m)
    elif case == "acc":
        if after_poss:
            cur += "n" + i4(cur)
        elif ends_vowel(cur):
            cur += "n" + i4(cur)
        else:
            m = mutate_final(cur)
            if m is None:
                return None
            cur = m + i4(m)
    elif case == "loc":
        cur += ("n" if after_poss else "") + "d" + a2(cur)
    elif case == "abl":
        cur += ("n" if after_poss else "") + "d" + a2(cur) + "n"
    elif case == "ins":
        if ends_vowel(cur):
            cur += "yl" + a2(cur)
        else:
            cur += "l" + a2(cur)
    # 4) xəbər şəkilçisi -dır
    if cop:
        cur += "d" + i4(cur) + "r"
    return cur


# ------------------------------------------------------------- verb forms
# şablon = ("v", tense, neg, pl, pass)   yaxud   ("vn", pass, noun_key)
TENSES = ("pres", "past", "narr", "narrcop", "fut", "obl", "oblcop", "ib", "arak", "an", "inf")


def verb_keys():
    keys = []
    for ps in (0, 1):
        for t in TENSES:
            for neg in (0, 1):
                for pl in (0, 1):
                    if t in ("ib", "arak", "an", "inf") and pl:
                        continue
                    if t in ("ib", "arak", "inf", "obl", "oblcop") and neg:
                        continue
                    if ps and t in ("ib", "arak"):
                        continue
                    keys.append(("v", t, neg, pl, ps))
    for ps in (0, 1):
        for nk in [(0, 0, "", 0), (0, 3, "", 0), (0, 3, "gen", 0), (0, 3, "dat", 0), (0, 3, "loc", 0),
                   (0, 3, "acc", 0), (0, 3, "abl", 0), (0, 0, "dat", 0), (0, 0, "acc", 0), (0, 0, "gen", 0)]:
            keys.append(("vn", ps, nk))
    return keys


VERB_KEYS = verb_keys()


def _soften_stem(stem: str):
    """Saitlə başlayan şəkilçidən əvvəl: et/get/yet -> ed/ged/yed; çoxhecalı ...t -> ...d
    (yarat -> yarad-ır, qorxut -> qorxud-ur)."""
    last = stem.split(" ")[-1]
    if last in ("et", "get", "yet") or (last.endswith("t") and vowel_count(last) >= 2):
        return stem[:-1] + "d"
    return stem


def passive_stem(stem: str) -> str:
    last = stem.split(" ")[-1]
    if last == "ol":
        return stem[:-2] + "olun"
    sv = _soften_stem(stem)
    if ends_vowel(sv):
        return sv + "n"
    if sv.endswith("l"):
        return sv + i4(sv) + "n"
    return sv + i4(sv) + "l"


def realize_verb(stem: str, key):
    """Fel kökü (məs. 'göstər', 'təmin et') + şablon -> forma, ya None."""
    _, tense, neg, pl, ps = key
    if ps:
        stem = passive_stem(stem)
    vowel_stem = ends_vowel(stem)
    sv = _soften_stem(stem)          # saitlə başlayan şəkilçi üçün kök
    ns = stem + "m" + a2(stem)       # mənfi kök: -mA

    if tense == "pres":
        if neg:
            core = stem + "m" + i4(stem) + "r"
        elif vowel_stem:
            core = stem + "y" + i4(stem) + "r"
        else:
            core = sv + i4(sv) + "r"
    elif tense == "past":
        b = ns if neg else stem
        core = b + "d" + i4(b)
    elif tense in ("narr", "narrcop"):
        b = ns if neg else stem
        core = b + "m" + i4(b) + "ş"
        if tense == "narrcop":
            core += "d" + i4(core) + "r"
    elif tense == "fut":
        if neg:
            core = ns + "y" + a2(ns) + "c" + a2(ns) + kq(ns)
        elif vowel_stem:
            core = stem + "y" + a2(stem) + "c" + a2(stem) + kq(stem)
        else:
            core = sv + a2(sv) + "c" + a2(sv) + kq(sv)
    elif tense in ("obl", "oblcop"):
        if neg:
            return None
        core = ns + "l" + i4(ns)
        if tense == "oblcop":
            core += "d" + i4(core) + "r"
    elif tense == "ib":
        if neg:
            return None
        core = (stem + "y" + i4(stem) + "b") if vowel_stem else (sv + i4(sv) + "b")
    elif tense == "arak":
        core = (stem + "y" + a2(stem) + "r" + a2(stem) + kq(stem)) if vowel_stem else (sv + a2(sv) + "r" + a2(sv) + kq(sv))
    elif tense == "an":
        if neg:
            core = ns + "y" + a2(ns) + "n"
        elif vowel_stem:
            core = stem + "y" + a2(stem) + "n"
        else:
            core = sv + a2(sv) + "n"
    elif tense == "inf":
        core = stem + ("maq" if a2(stem) == "a" else "mək")
    else:
        return None
    if pl:
        core += "l" + a2(core) + "r"
    return core


def realize_verb_nominal(stem: str, key):
    """Fel adı (-mA) + isim şəkilçiləri: göstərmə(si)(nin) və s."""
    _, ps, nk = key
    if ps:
        stem = passive_stem(stem)
    if nk[1] == 0:  # mənsubiyyətsiz: məsdər əsası (oxumağa, göstərməyə)
        base = stem + ("maq" if a2(stem) == "a" else "mək")
    else:           # 3-cü şəxs mənsubiyyət: -mA + sI (oxunması, göstərməsi)
        base = stem + "m" + a2(stem)
    return realize_noun(base, nk)


def verb_stem(infinitive: str):
    """'göstərmək' -> 'göstər'. Tanınmırsa None."""
    w = infinitive.strip()
    if w.endswith("mək") or w.endswith("maq"):
        return w[:-3]
    return None
