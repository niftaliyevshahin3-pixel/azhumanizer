"""Humanizer mühərriki — süni intellektsiz, qayda + lüğət əsaslı.

Bütün mərhələlər deterministikdir (seed-li təsadüfilik): eyni giriş + eyni seed
= eyni nəticə. Hər mərhələdən sonra guards.check ilə məna-qoruma yoxlanır.
"""
import math
import random
import re
from collections import Counter

from . import discourse, guards, metrics, restructure as rs
from .guards import PH_OPEN, PH_CLOSE
from .lexicon import Lexicon
from .phrases import PhraseTable, OPENER_GROUPS, detect_opener, ai_phrase_regexes
from .textutil import (
    az_cap, az_lower, az_uncap, count_words, detokenize, is_all_caps, is_capitalized, is_upper_char,
    looks_like_heading, match_case, split_sentences, tokenize, words_of,
)

# --------------------------------------------------------------- güc səviyyələri
LEVELS = {
    "light": {"lex": 0.40, "phrase": 0.70, "struct": 0.25, "ops": 1, "cv_lo": 0.42, "cv_hi": 0.70, "opener": 0.6, "drop": 0.30, "rhythm_ops": 0.35, "lexcap": 0.6, "merge_min": 11, "merge_sum": 32},
    "balanced": {"lex": 0.70, "phrase": 0.95, "struct": 0.45, "ops": 2, "cv_lo": 0.52, "cv_hi": 0.78, "opener": 0.85, "drop": 0.45, "rhythm_ops": 0.60, "lexcap": 0.85, "merge_min": 13, "merge_sum": 36},
    "strong": {"lex": 0.95, "phrase": 1.00, "struct": 0.70, "ops": 3, "cv_lo": 0.60, "cv_hi": 0.90, "opener": 1.0, "drop": 0.55, "rhythm_ops": 0.90, "lexcap": 1.0, "merge_min": 16, "merge_sum": 44},
}

BRIDGES_VE = [
    "Bundan əlavə", "Bu kontekstdə", "Bu zaman", "Bunun ardınca", "Bu mərhələdə", "Sonrakı mərhələdə", "Bu nöqtədə",
    "Növbəti addımda", "Bu əsnada", "Paralel olaraq", "Bu şəraitdə", "Bu vəziyyətdə", "Bunun davamında",
]

PROTECT_PATTERNS = [
    re.compile(r"https?://\S+|www\.\S+|\b[\w.+-]+@[\w-]+\.[\w.-]+\b"),
    re.compile(r"\[\d+(?:\s*[,–-]\s*\d+)*\]"),
    re.compile(r"\((?:[^()]*\b(?:19|20)\d{2}[a-z]?[^()]*)\)"),      # (Əliyev, 2020)
    re.compile(r"«[^»]{1,400}»|“[^”]{1,400}”|\"[^\"\n]{1,400}\""),  # dırnaqlı mətn
]


NO_COMMA_OK = {"lakin", "amma", "ancaq", "habelə", "həmçinin", "üstəlik"}


class BridgePool:
    def __init__(self, rng):
        self.usage = Counter()
        self.rng = rng

    def pick(self, key):
        options = BRIDGES_VE
        mn = min(self.usage[o] for o in options)
        least = [o for o in options if self.usage[o] == mn]
        ch = least[self.rng.randrange(len(least))]
        self.usage[ch] += 1
        return ch


class Change:
    __slots__ = ("kind", "before", "after")

    def __init__(self, kind, before, after):
        self.kind, self.before, self.after = kind, before, after

    def as_dict(self):
        return {"kind": self.kind, "before": self.before, "after": self.after}


class Resources:
    def __init__(self, lexicon_texts, phrases_text):
        self.lexicon = Lexicon.from_texts(lexicon_texts)
        self.phrases = PhraseTable.from_text(phrases_text)
        self.ai_regexes = ai_phrase_regexes(self.phrases)


class Session:
    """Bir humanize icrası üçün vəziyyət (seed, sayğaclar, dəyişikliklər)."""

    def __init__(self, res: Resources, level: str, seed: int, protected_terms, opts):
        self.res = res
        self.p = LEVELS[level]
        self.rng = random.Random(seed)
        self.protected_terms = [az_lower(t.strip()) for t in (protected_terms or []) if t and t.strip()]
        self.opts = opts
        self.changes = []
        self.syn_usage = Counter()
        self.phrase_usage = Counter()
        self.opener_usage = Counter()
        self.bridge = BridgePool(self.rng)

    def log(self, kind, before, after):
        self.changes.append(Change(kind, before, after))


# ============================================================ mühafizə (placeholder)
def protect(text: str, terms):
    store = []

    def sub(m):
        store.append(m.group(0))
        return f"{PH_OPEN}{len(store) - 1}{PH_CLOSE}"

    for rx in PROTECT_PATTERNS:
        text = rx.sub(sub, text)
    for t in sorted(set(terms), key=lambda x: -len(x)):
        if not t:
            continue
        rx = re.compile(r"(?<!\w)" + r"\s+".join(re.escape(x) for x in t.split()) + r"(?!\w)", re.IGNORECASE | re.UNICODE)
        text = rx.sub(sub, text)
    return text, store


_PH_RESTORE = re.compile(PH_OPEN + r"(\d+)" + PH_CLOSE)


def restore(text: str, store):
    for _ in range(3):
        new = _PH_RESTORE.sub(lambda m: store[int(m.group(1))], text)
        if new == text:
            break
        text = new
    return text


# ============================================================ mərhələ: ifadələr
def apply_phrases(sess: Session, sentence: str):
    if sess.rng.random() > sess.p["phrase"] and sess.p["phrase"] < 1.0:
        return sentence
    changed = False
    out = sentence
    guard = 0
    for rule in sess.res.phrases.rules:
        m = rule.regex.search(out)
        if not m or guard > 6:
            continue
        if m.start() == 0 and detect_opener(out):
            continue  # cümlə başlanğıc bağlayıcılarını ayrıca mərhələ idarə edir
        if any(PH_OPEN in out[max(0, m.start() - 1):m.end() + 1] for _ in (0,)):
            continue
        alts = list(rule.alts)
        if not alts:
            continue
        # ən az istifadə olunanı seç
        usage = [sess.phrase_usage[(rule.pattern, a)] for a in alts]
        mn = min(usage)
        cands = [a for a, u in zip(alts, usage) if u == mn]
        alt = cands[sess.rng.randrange(len(cands))]
        # cümlə başlanğıcında "~" (silmə) etmək olmaz, tək başına cümlə mənasını dəyişə bilər
        matched = m.group(0)
        start = m.start()
        if alt == "":
            after = out[m.end():]
            if after.startswith(","):
                after = after[1:]
            after = after.lstrip()
            if not after:
                continue
            before_txt = out[:start].rstrip()
            new = (before_txt + " " if before_txt else "") + after
            if start == 0 or before_txt == "":
                new = az_cap(new)
            out = new
        else:
            rep = match_case(matched, alt)
            out = out[:start] + rep + out[m.end():]
        sess.phrase_usage[(rule.pattern, alt)] += 1
        guard += 1
        changed = True
    if changed:
        sess.log("phrase", sentence, out)
    return out


# ============================================================ mərhələ: leksik əvəzləmə
NEXT_STOP_FOR_ADJ = {"olaraq", "etibarilə", "isə", "də", "da", "ki", "deyil"}


def lexical_substitute(sess: Session, sentence: str, sent_index_in_par: int):
    lx = sess.res.lexicon
    toks = tokenize(sentence)
    matches = lx.find_matches(toks)
    if not matches:
        return sentence
    widx = [i for i, t in enumerate(toks) if t[0] == "w"]
    first_word_ti = widx[0] if widx else -1
    used_targets = set()
    replaced = 0
    edits = []
    # bir cümlədə həddən çox əvəzləmə etmə
    max_per_sentence = max(1, int(round(len(matches) * sess.p["lexcap"])))
    order = list(range(len(matches)))
    sess.rng.shuffle(order)
    for mi in order:
        if replaced >= max_per_sentence:
            break
        m = matches[mi]
        if sess.rng.random() > sess.p["lex"]:
            continue
        orig_tokens = toks[m.start:m.end + 1]
        orig_text = "".join(t[1] for t in orig_tokens)
        surface_first = toks[m.start][1]
        # xüsusi ad: cümlə ortasında böyük hərf
        if is_capitalized(surface_first) and m.start != first_word_ti:
            continue
        if is_all_caps(surface_first):
            continue
        # qorunan xüsusi terminlər
        low_orig = az_lower(orig_text)
        if any(low_orig in pt or pt in low_orig for pt in sess.protected_terms):
            continue
        # yaxınlıqdakı placeholder
        if PH_OPEN in "".join(t[1] for t in toks[max(0, m.start - 2):m.end + 3]):
            continue
        # tire ilə birləşmiş qonşu söz (sosial-iqtisadi)
        if (m.start > 0 and toks[m.start - 1][1] == "-") or (m.end + 1 < len(toks) and toks[m.end + 1][1] == "-"):
            continue
        # izafet təyini: "məlumat bazası", "təhsil sistemi" — sabit ikili ad, toxunma
        if m.entry.kind == "n" and (0, 0, "", 0) in m.keys:
            nxt_w = next((t[1] for t in toks[m.end + 1:m.end + 3] if t[0] == "w"), None)
            gap_ok = all(t[0] == "s" for t in toks[m.end + 1:m.end + 2])
            if nxt_w and gap_ok and len(nxt_w) >= 5 and az_lower(nxt_w)[-1] in "ıiuü" and not is_capitalized(nxt_w):
                continue
        # izafet başı: "tədiyə balansı", "bazar dəyəri" — sabit termin; yalnız sərbəst birləşmədə
        # (əvvəlində təyin hal / sifət) əvəz olunur
        if m.entry.kind == "n" and any(k[1] == 3 and k[2] in ("", "acc", "dat", "loc", "abl", "gen") for k in m.keys if isinstance(k, tuple) and len(k) == 4) and (0, 0, "", 0) not in m.keys:
            prev_w = None
            for t in reversed(toks[:m.start]):
                if t[0] == "w":
                    prev_w = t[1]
                    break
                if t[0] not in ("s",):
                    break
            if prev_w:
                pl = az_lower(prev_w)
                genitive = pl.endswith(("ın", "in", "un", "ün", "nın", "nin", "nun", "nün"))
                adj_known = (("b", (pl,)) in lx.entries)
                if not (genitive or adj_known or pl in rs._ALWAYS_COMMON):
                    continue
        # sifət: sonrakı söz bağlayıcı/xəbər olmasın
        if m.entry.kind == "b":
            nxt = next((t[1] for t in toks[m.end + 1:] if t[0] == "w"), None)
            between = "".join(t[1] for t in toks[m.end + 1:]) if nxt else ""
            if nxt and az_lower(nxt) in NEXT_STOP_FOR_ADJ:
                continue
        # hədəf seç
        options = []
        for tg in m.entry.targets:
            realized = lx.realize_target(m, tg)
            if not realized:
                continue
            if realized in used_targets:
                continue
            # qonşu sözlə eyni olmasın
            neigh = []
            for j in (m.start - 2, m.end + 2):
                if 0 <= j < len(toks) and toks[j][0] == "w":
                    neigh.append(az_lower(toks[j][1]))
            if az_lower(realized.split()[-1]) in neigh or az_lower(realized.split()[0]) in neigh:
                continue
            options.append(realized)
        if not options:
            continue
        usage = [sess.syn_usage[o] for o in options]
        mn = min(usage)
        cand = [o for o, u in zip(options, usage) if u == mn]
        choice = cand[sess.rng.randrange(len(cand))]
        sess.syn_usage[choice] += 1
        used_targets.add(choice)
        new_text = match_case(surface_first, choice)
        edits.append((m.start, m.end, new_text, orig_text))
        replaced += 1
    if not edits:
        return sentence
    edits.sort(key=lambda e: e[0], reverse=True)
    for s, e, new_text, orig_text in edits:
        toks[s:e + 1] = [("w", new_text)]
    out = detokenize(toks)
    for s, e, new_text, orig_text in sorted(edits):
        sess.log("word", orig_text, new_text)
    return out


# ============================================================ mərhələ: struktur
def structural_variation(sess: Session, sentence: str):
    out = sentence
    ops = [rs.toggle_intro_comma, rs.move_mid_adverbial_front, rs.swap_pair_order, rs.biri_dir_toggle,
           rs.swap_hem_hem_de, rs.permute_list_inner]
    sess.rng.shuffle(ops)
    done = 0
    for op in ops:
        if done >= sess.p["ops"]:
            break
        if sess.rng.random() > sess.p["struct"]:
            continue
        r = op(out, sess.rng)
        if r and r != out:
            sess.log("structure", out, r)
            out = r
            done += 1
    return out


# ============================================================ mərhələ: ritm (böl / birləşdir)
def _cv(lengths):
    n = len(lengths)
    if n < 2:
        return 0.0
    mean = sum(lengths) / n
    if mean == 0:
        return 0.0
    return math.sqrt(sum((l - mean) ** 2 for l in lengths) / n) / mean


def _dist(cv, lo, hi):
    if cv < lo:
        return lo - cv
    if cv > hi:
        return cv - hi
    return 0.0


def shape_rhythm(sess: Session, sents, context_lens):
    """sents: bir paraqrafın cümlələri. Uzunluq dəyişkənliyi hədəf aralığına çatana
    qədər bölmə/birləşdirmə cəhdi. Ən yaxşı vəziyyət seçilir."""
    lo, hi = sess.p["cv_lo"], sess.p["cv_hi"]
    max_ops = max(1, int(math.ceil(len(sents) * sess.p["rhythm_ops"])))

    def total_cv(ss):
        return _cv([count_words(s) for s in ss] + list(context_lens))

    best = list(sents)
    best_d = _dist(total_cv(best), lo, hi)
    cur = list(sents)
    ops_done = 0
    tries = 0
    merged_seen = set()
    while ops_done < max_ops and tries < max_ops * 6 and best_d > 0:
        tries += 1
        cur_cv = total_cv(cur)
        candidates = []
        # bölmə namizədləri
        for i, s in enumerate(cur):
            if count_words(s) >= 17:
                sp = rs.try_split(s, sess.rng, bridge_prob=0.03, bridge_pool=sess.bridge)
                if sp and all(count_words(x) >= 4 for x in sp):
                    candidates.append(("split", i, sp))
        # birləşdirmə namizədləri
        for i in range(len(cur) - 1):
            a, b = cur[i], cur[i + 1]
            if a in merged_seen or b in merged_seen:
                continue
            if min(count_words(a), count_words(b)) <= sess.p["merge_min"]:
                if count_words(a) + count_words(b) <= sess.p["merge_sum"]:
                    mg = rs.try_merge(a, b, sess.rng)
                    if mg:
                        candidates.append(("merge", i, mg))
        if not candidates:
            break
        scored = []
        for kind, i, res in candidates:
            if kind == "split":
                new = cur[:i] + res + cur[i + 1:]
            else:
                new = cur[:i] + [res] + cur[i + 2:]
            scored.append((_dist(total_cv(new), lo, hi), sess.rng.random(), kind, i, res, new))
        scored.sort(key=lambda x: (x[0], x[1]))
        pick = scored[0]
        # yalnız yaxşılaşdıran əməliyyat
        if pick[0] >= _dist(cur_cv, lo, hi) - 1e-9:
            # sıfır yaxşılaşma: təsadüfi kiçik şans
            if sess.rng.random() > 0.15:
                break
        _, _, kind, i, res, new = pick
        if kind == "split":
            sess.log("split", cur[i], " ".join(res))
        else:
            sess.log("merge", cur[i] + " " + cur[i + 1], res)
            merged_seen.add(res)
        cur = new
        ops_done += 1
        d = _dist(total_cv(cur), lo, hi)
        if d < best_d:
            best_d, best = d, list(cur)
    return best


# ============================================================ mərhələ: başlanğıc bağlayıcıları
def diversify_openers(sess: Session, sents, state):
    """state: {'prev_conn': bool} sənəd boyu; sents: paraqraf cümlələri."""
    out = []
    n_total = state["n"]
    for i, s in enumerate(sents):
        d = detect_opener(s)
        if not d:
            state["prev_conn"] = False
            out.append(s)
            continue
        group, matched, rest, had_comma = d
        state["seen"] += 1
        low_matched = az_lower(matched)
        drop_allowed = group in ("addition", "result", "regard", "emphasis", "similarity")
        # zəncirvari bağlayıcılar: əvvəlki cümlə də bağlayıcı ilə idisə, bunu sil
        force_drop = state["prev_conn"] and drop_allowed
        # ümumi payı limitlə: bağlayıcı payı hədəfdən çoxdursa sil
        share = state["kept"] / max(1, state["idx"])
        over_cap = share > 0.18 and drop_allowed
        roll = sess.rng.random()
        if (force_drop or over_cap or (drop_allowed and roll < sess.p["drop"])) and sess.rng.random() < sess.p["opener"]:
            new = az_cap(rest)
            sess.log("opener_drop", s, new)
            out.append(new)
            state["prev_conn"] = False
        elif roll < sess.p["opener"] or state["prev_conn"]:
            pool = [x for x in OPENER_GROUPS[group] if az_lower(x) != low_matched]
            # eyni sözlə başlamamaq: ən az istifadə olunanı seç
            if pool:
                usage = [sess.opener_usage[x] for x in pool]
                mn = min(usage)
                cands = [x for x, u in zip(pool, usage) if u == mn]
                pick = cands[sess.rng.randrange(len(cands))]
                sess.opener_usage[pick] += 1
                sep = "," if (had_comma or az_lower(pick) not in NO_COMMA_OK) else ""
                new = f"{pick}{sep} {rest}"
                sess.log("opener_swap", s, new)
                out.append(new)
                state["prev_conn"] = True
                state["kept"] += 1
            else:
                out.append(s)
                state["prev_conn"] = True
                state["kept"] += 1
        else:
            out.append(s)
            state["prev_conn"] = True
            state["kept"] += 1
        state["idx"] += 1
    return out


# ============================================================ paraqraf emalı
def _fix_spacing(text: str) -> str:
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"\s+([,.;:!?])", r"\1", text)
    text = re.sub(r",{2,}", ",", text)
    text = re.sub(r"([.!?])\1+(?!\.)", r"\1", text)
    text = re.sub(r"([,;:])\s*([.!?])", r"\2", text)
    return text.strip()


def process_paragraph(sess: Session, paragraph: str, doc_state):
    original = paragraph
    text, store = protect(paragraph, sess.protected_terms)
    sents = split_sentences(text)
    if not sents:
        return paragraph

    def stage_ok(prev_text, new_text, name):
        reason = guards.check(prev_text, new_text)
        if reason:
            sess.log("skipped:" + name, prev_text[:60], reason)
            return False
        return True

    base_text = " ".join(sents)
    working = list(sents)
    checkpoint_text = base_text
    log_len = len(sess.changes)

    # 1) ifadələr
    cand = [apply_phrases(sess, s) for s in working]
    if stage_ok(checkpoint_text, " ".join(cand), "phrases"):
        working, checkpoint_text = cand, " ".join(cand)
        log_len = len(sess.changes)
    else:
        del sess.changes[log_len:]

    # 2) leksik
    cand = [lexical_substitute(sess, s, i) for i, s in enumerate(working)]
    if stage_ok(checkpoint_text, " ".join(cand), "lexical"):
        working, checkpoint_text = cand, " ".join(cand)
        log_len = len(sess.changes)
    else:
        del sess.changes[log_len:]

    # 3) struktur variasiyası
    cand = [structural_variation(sess, s) for s in working]
    if stage_ok(checkpoint_text, " ".join(cand), "structure"):
        working, checkpoint_text = cand, " ".join(cand)
        log_len = len(sess.changes)
    else:
        del sess.changes[log_len:]

    # 3b) doldurucu sözlər
    cand = [discourse.drop_fillers(sess, s) for s in working]
    if stage_ok(checkpoint_text, " ".join(cand), "fillers"):
        working, checkpoint_text = cand, " ".join(cand)
        log_len = len(sess.changes)
    else:
        del sess.changes[log_len:]

    # 4) ritm
    cand = shape_rhythm(sess, working, doc_state["context_lens"])
    if all(guards.check_sentence_form(s) is None or s[:1].isdigit() for s in cand) and stage_ok(checkpoint_text, " ".join(cand), "rhythm"):
        working, checkpoint_text = cand, " ".join(cand)
        log_len = len(sess.changes)
    else:
        del sess.changes[log_len:]

    # 4b) təkrarlanan başlanğıc subyekti
    cand = discourse.diversify_lead_subjects(sess, working)
    if stage_ok(checkpoint_text, " ".join(cand), "subjects"):
        working, checkpoint_text = cand, " ".join(cand)
        log_len = len(sess.changes)
    else:
        del sess.changes[log_len:]

    # 5) başlanğıc bağlayıcıları
    cand = diversify_openers(sess, working, doc_state["opener"])
    if all(guards.check_sentence_form(s) is None or s[:1].isdigit() for s in cand) and stage_ok(checkpoint_text, " ".join(cand), "openers"):
        working, checkpoint_text = cand, " ".join(cand)
    else:
        del sess.changes[log_len:]

    result = _fix_spacing(" ".join(working))
    result = restore(result, store)
    doc_state["context_lens"] = [l for l in doc_state["context_lens"]]  # tərkib dəyişmir
    return result


# ============================================================ sənəd
class Result:
    def __init__(self, text, changes, before, after, seed, level):
        self.text, self.changes, self.before, self.after, self.seed, self.level = text, changes, before, after, seed, level


def humanize_once(res: Resources, text: str, level="balanced", seed=1, protected_terms=None, opts=None):
    opts = opts or {}
    sess = Session(res, level, seed, protected_terms, opts)
    _prime_known_lower(res, text)
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    # kontekst uzunluqları: bütün cümlələr (ritm sənəd səviyyəsində hesablanır)
    all_lens = []
    for ln in lines:
        if ln.strip() and not looks_like_heading(ln):
            all_lens.extend(count_words(s) for s in split_sentences(ln))
    doc_state = {"context_lens": [], "opener": {"prev_conn": False, "seen": 0, "kept": 0, "idx": 0, "n": len(all_lens)}}
    out_lines = []
    # paraqraflar arası ritm: hər paraqraf üçün "qalan cümlələrin" uzunluqları kontekst kimi
    par_lens = []
    for ln in lines:
        if ln.strip() and not looks_like_heading(ln) and _is_prose(ln):
            par_lens.append([count_words(s) for s in split_sentences(ln)])
        else:
            par_lens.append(None)
    for i, ln in enumerate(lines):
        if not ln.strip() or looks_like_heading(ln) or not _is_prose(ln):
            out_lines.append(ln)
            continue
        ctx = []
        for j, pl in enumerate(par_lens):
            if pl is not None and j != i:
                ctx.extend(pl)
        doc_state["context_lens"] = ctx
        lead = re.match(r"^\s*", ln).group(0)
        out_lines.append(lead + process_paragraph(sess, ln.strip(), doc_state))
    new_text = "\n".join(out_lines)
    before = metrics.analyze(text, res.ai_regexes)
    after = metrics.analyze(new_text, res.ai_regexes)
    return Result(new_text, sess.changes, before, after, seed, level)


_LEX_LOWER_CACHE = {}


def _prime_known_lower(res, text):
    """Sənəddə kiçik hərflə görünən sözləri + lüğət formalarını 'ümumi söz' kimi işarələ."""
    key = id(res)
    if key not in _LEX_LOWER_CACHE:
        _LEX_LOWER_CACHE[key] = set(res.lexicon.by_prefix.keys())
    lows = set(_LEX_LOWER_CACHE[key])
    for w in words_of(text):
        if w and not is_upper_char(w[0]):
            lows.add(az_lower(w))
    proper = set()
    for sent in re.split(r"(?<=[.!?…])\s+", text):
        for w in words_of(sent)[1:]:
            if w and is_upper_char(w[0]) and len(w) > 1:
                proper.add(az_lower(w))
    rs.set_known_lower(lows, proper)


def _is_prose(line: str) -> bool:
    s = line.strip()
    if re.match(r"^(?:[-•*–—]|\d+[.)])\s+", s):
        return count_words(s) >= 10
    return count_words(s) >= 6


def humanize(res: Resources, text: str, level="balanced", seed=1, protected_terms=None, candidates=6, opts=None):
    """Bir neçə seed ilə işləyir, ən aşağı AI-skorlu (və təhlükəsizlik keçən) variantı seçir."""
    best = None
    for k in range(max(1, candidates)):
        r = humanize_once(res, text, level, seed + k * 7919, protected_terms, opts)
        n_changes = len([c for c in r.changes if not c.kind.startswith("skipped")])
        key = (r.after["score"], -n_changes)
        if best is None or key < best[0]:
            best = (key, r)
    return best[1]
