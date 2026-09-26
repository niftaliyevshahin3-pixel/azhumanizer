"""İfadə cədvəli (mətn daxili əvəzləmələr) və cümlə-başlanğıc bağlayıcı qrupları."""
import re
from .textutil import az_lower, az_cap, az_uncap, is_capitalized

# --------------------------------------------------------------------------
# Cümlə başlanğıcı bağlayıcıları: qrup -> (üzvlər). Eyni qrupun üzvləri bir-birini
# əvəz edə bilər; "" (boş) = bağlayıcını sil. Yalnız mənası eyni olanlar bir qrupdadır.
# --------------------------------------------------------------------------
OPENER_GROUPS = {
    "addition": [
        "Həmçinin", "Bundan əlavə", "Bundan başqa", "Əlavə olaraq", "Bununla yanaşı", "Üstəlik",
        "Eləcə də", "Habelə", "Bunun yanında", "Bununla birlikdə", "Bir də", "Eyni zamanda",
    ],
    "contrast": ["Lakin", "Amma", "Ancaq", "Bununla belə", "Buna baxmayaraq"],
    "otherside": ["Digər tərəfdən", "Digər yandan", "Başqa cəhətdən"],
    "result": [
        "Buna görə", "Buna görə də", "Bu səbəbdən", "Bu üzdən", "Bunun nəticəsində",
        "Nəticədə", "Ona görə də",
    ],
    "conclusion": [
        "Beləliklə", "Nəticə etibarilə", "Yekun olaraq", "Ümumilikdə", "Bütövlükdə", "Deməli",
        "Sözün qısası", "Bir sözlə",
    ],
    "example": ["Məsələn", "Misal üçün", "Nümunə üçün"],
    "regard": [
        "Bu baxımdan", "Bu mənada", "Bu kontekstdə", "Bu çərçivədə", "Bu nöqteyi-nəzərdən",
        "Bu cəhətdən", "Bu istiqamətdə",
    ],
    "emphasis": ["Xüsusilə", "Xüsusən"],
    "priority": ["İlk növbədə", "Hər şeydən əvvəl", "Öncəliklə"],
    "similarity": ["Eynilə", "Oxşar şəkildə", "Bənzər qaydada", "Buna bənzər olaraq"],
}
# silinə bilən qruplar (mənanı itirmədən): bağlayıcı olmadan da cümlə tam oxunur
DROPPABLE_GROUPS = {"addition", "result", "regard", "emphasis", "similarity", "contrast_soft"}

_OPENER_INDEX = []  # (lower_text, group, original)
for _g, _items in OPENER_GROUPS.items():
    for _it in _items:
        _OPENER_INDEX.append((az_lower(_it), _g, _it))
_OPENER_INDEX.sort(key=lambda t: -len(t[0]))

_OPENER_RE_CACHE = {}


def detect_opener(sentence: str):
    """Cümlə bağlayıcı ilə başlayırsa (group, matched_text, rest, had_comma) qaytarır."""
    low = az_lower(sentence)
    for lower, group, orig in _OPENER_INDEX:
        if low.startswith(lower):
            after = sentence[len(lower):]
            had_comma = after[:1] == ","
            if after[:1] == ",":
                rest = after[1:].lstrip()
            elif after[:1] in (" ",):
                # vergülsüz bağlayıcı ("Lakin bu ...", "Məsələn bu ...")
                nxt = after.lstrip()
                if group in ("contrast",) and orig in ("Lakin", "Amma", "Ancaq"):
                    rest = nxt
                elif group in ("emphasis", "example", "addition") and orig in ("Həmçinin", "Üstəlik", "Habelə"):
                    rest = nxt
                else:
                    continue
            else:
                continue
            if not rest:
                continue
            return group, sentence[:len(lower)], rest, had_comma
    return None


# --------------------------------------------------------------------------
# Mətn-daxili ifadə cədvəli
# --------------------------------------------------------------------------
class PhraseRule:
    __slots__ = ("pattern", "alts", "regex")

    def __init__(self, pattern, alts):
        self.pattern = pattern
        self.alts = alts
        toks = [re.escape(t) for t in pattern.split()]
        self.regex = re.compile(r"(?<!\w)" + r"\s+".join(toks) + r"(?!\w)", re.IGNORECASE | re.UNICODE)


class PhraseTable:
    def __init__(self, rules):
        self.rules = sorted(rules, key=lambda r: -len(r.pattern))

    @classmethod
    def from_text(cls, text):
        rules = []
        for ln in text.split("\n"):
            ln = ln.strip()
            if not ln or ln.startswith("#") or "=>" not in ln:
                continue
            left, right = ln.split("=>", 1)
            alts = [a.strip() for a in right.split("|")]
            alts = [("" if a in ("~", "") else a) for a in alts if a is not None]
            left = az_lower(left.strip())
            if left:
                rules.append(PhraseRule(left, alts))
        return cls(rules)

    def find(self, sentence):
        """Cümlədəki ilk (ən uzun) uyğunluğu qaytarır: (rule, match)."""
        for r in self.rules:
            m = r.regex.search(sentence)
            if m:
                yield r, m


AI_PHRASE_PATTERNS = None


def ai_phrase_regexes(table: "PhraseTable"):
    """Metrika üçün: cədvəldəki sol tərəf ifadələri (AI-klişe siqnalı)."""
    return [r.regex for r in table.rules]
