"""Kombinator ifadə qaydaları (data_src/phrases_gen.txt) — əl ilə yoxlanmış komponentlərdən."""
import io
import itertools
import os

lines = ["# Avtomatik generasiya: tools/gen_phrases.py (əl ilə yoxlanmış komponentlərdən)"]


def add(pattern, alts):
    alts = [a for a in alts if a != pattern]
    if alts:
        lines.append("%s => %s" % (pattern, " | ".join(alts)))


# --- əhəmiyyət / önəm ailəsi
adjs = ["mühüm", "böyük", "xüsusi", "həlledici", "vacib", "əhəmiyyətli"]
nouns = ["əhəmiyyət", "önəm"]
verbs = [("kəsb edir", "daşıyır"), ("kəsb etmişdir", "daşımışdır"), ("daşıyır", "kəsb edir"), ("daşımışdır", "kəsb etmişdir")]
seen = set()
for a, n, (v1, v2) in itertools.product(adjs, nouns, verbs):
    pat = "%s %s %s" % (a, n, v1)
    if pat in seen:
        continue
    seen.add(pat)
    alts = []
    for a2 in adjs[:5]:
        for n2 in nouns:
            alts.append("%s %s %s" % (a2, n2, v2))
            alts.append("%s %s %s" % (a2, n2, v1))
    # yalnız bir neçə təsadüfi olmayan variant
    alts = [x for x in alts if x != pat][:8]
    add(pat, alts)

# --- rol ailəsi
role_adj = ["mühüm", "əsas", "böyük", "həlledici", "vacib", "aparıcı", "əhəmiyyətli"]
for a in role_adj:
    for v_a, v_b in (("oynayır", "oynayır"), ("oynamışdır", "oynamışdır"), ("oynaya bilər", "oynaya bilər")):
        pat = "%s rol %s" % (a, v_a)
        alts = ["%s rol %s" % (b, v_b) for b in role_adj if b != a and (a, b) not in (("əsas", "aparıcı"),)]
        add(pat, alts[:4])

# --- "təsir" ailəsi
for pat, alt in [("təsir göstərməsini", "təsir etməsini"), ("təsir göstərməsi", "təsir etməsi"),
                 ("təsir göstərərək", "təsir edərək"), ("təsir göstərən", "təsir edən"),
                 ("təsir etməsini", "təsir göstərməsini"), ("təsir edərək", "təsir göstərərək"),
                 ("təsir edən", "təsir göstərən"), ("təsir göstərməsi", "təsir etməsi")]:
    add(pat, [alt])

# --- "olunur / edilir" xəbər cütləri (isim + fel) — ən çox rast gəlinənlər
for noun in ["hesab", "qəbul", "təşkil", "təmin", "müəyyən", "tətbiq", "həyata keçir", "icra", "aşkar", "qeyd", "əldə", "istifadə", "tədqiq", "təhlil"]:
    if noun == "həyata keçir":
        continue
    for v1, v2 in (("olunur", "edilir"), ("edilir", "olunur"), ("olunub", "edilib"), ("edilib", "olunub"),
                   ("olunmuşdur", "edilmişdir"), ("edilmişdir", "olunmuşdur"), ("olunmalıdır", "edilməlidir"),
                   ("edilməlidir", "olunmalıdır"), ("olunması", "edilməsi"), ("edilməsi", "olunması"),
                   ("olunan", "edilən"), ("edilən", "olunan")):
        add("%s %s" % (noun, v1), ["%s %s" % (noun, v2)])

# --- bağlayıcı sözlər (cümlə daxili)
add("eyni zamanda", ["həm də", "bununla birlikdə"])
add("bundan başqa", ["həmçinin", "eləcə də"])
add("həmçinin", ["eləcə də", "bundan başqa", "eyni zamanda"])
add("davamlı şəkildə", ["fasiləsiz şəkildə", "ardıcıl şəkildə", "durmadan"])
add("uzunmüddətli dövrdə", ["uzun müddət ərzində", "uzun dövr ərzində"])
add("qısamüddətli dövrdə", ["qısa müddət ərzində", "qısa dövr ərzində"])
add("müəyyən dövr ərzində", ["müəyyən müddət ərzində", "müəyyən zaman kəsiyində"])
add("nəticə etibarilə", ["yekun olaraq", "beləliklə", "ümumilikdə"])
add("ilə xarakterizə olunur", ["ilə səciyyələnir", "ilə xarakterizə edilir"])
add("ilə xarakterizə edilir", ["ilə səciyyələnir", "ilə xarakterizə olunur"])
add("ilə səciyyələnir", ["ilə xarakterizə olunur"])
add("səbəb ola bilər", ["gətirib çıxara bilər"])
add("səbəb olur", ["gətirib çıxarır"])
add("səbəb olmuşdur", ["gətirib çıxarmışdır"])
add("baş verir", ["meydana gəlir"])
add("baş verən", ["meydana gələn"])
add("baş verdi", ["meydana gəldi"])
add("baş vermişdir", ["meydana gəlmişdir"])
add("həyata keçirilir", ["icra olunur", "reallaşdırılır", "yerinə yetirilir"])
add("həyata keçirilmişdir", ["icra olunmuşdur", "reallaşdırılmışdır"])
add("həyata keçirilməsi", ["icra olunması", "reallaşdırılması"])
add("həyata keçirmək", ["icra etmək", "reallaşdırmaq"])
add("əhəmiyyətli rol oynayır", ["mühüm rol oynayır", "önəmli rol oynayır"])

out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data_src", "phrases_gen.txt")
with io.open(out, "w", encoding="utf8") as fh:
    fh.write("\n".join(lines) + "\n")
print(len(lines) - 1, "rules")
