"""İsim + edilmək/olunmaq cütlərini və digər fel-birləşmə klasterlərini generasiya edir."""
import sys, io
NOUNS = """istifadə tətbiq qeyd təqdim təşkil təmin əldə hesab qəbul icra müəyyən təsdiq tədqiq təhlil analiz izah
şərh müzakirə tövsiyə təklif aşkar müşahidə nəşr çap tərtib təsvir ifadə təyin təsnif təmsil əhatə istehsal
nəzarət həll sübut təkrar istisna daxil təşviq tənzimləmə ehtimal etiraf ittiham məhdud tələb təsis
tamamla təcrid tərəqqi mühafizə qiymətləndir yekun ölç dəyərləndir""".split()
# yalnız ikinci hissə (adlar) — "tamamla/ölç/..." kimi fel kökləri çıxarılır
NOUNS = [n for n in NOUNS if n not in ("tamamla", "təcrid", "tərəqqi", "qiymətləndir", "yekun", "ölç", "dəyərləndir", "ehtimal", "ittiham", "məhdud", "tənzimləmə")]
lines = []
for n in NOUNS:
    lines.append(f"v: {n} edilmək = {n} olunmaq")
lines += [
    "v: təsir göstərmək = təsir etmək",
    "v: əhəmiyyət kəsb etmək = əhəmiyyət daşımaq",
    "v: önəm kəsb etmək = önəm daşımaq",
    "v: diqqət çəkmək = diqqəti cəlb etmək",
    "v: yer almaq = yer tutmaq",
    "v: mövcud olmaq = var olmaq",
    "v: baş vermək = meydana gəlmək",
    "v: meydana çıxmaq = ortaya çıxmaq = üzə çıxmaq",
    "v: nəzərə çarpmaq = gözə çarpmaq",
    "v: imkan yaratmaq = zəmin yaratmaq = şərait yaratmaq",
    "v: dəstək göstərmək = dəstək vermək",
    "v: yardım göstərmək = yardım etmək = kömək göstərmək",
    "v: hesab olunmaq = sayılmaq",
    "v: hesab edilmək = sayılmaq",
    "v: həyata keçirilmək = icra edilmək",
    "v: izah etmək = şərh etmək",
    "v: müəyyən etmək = müəyyənləşdirmək",
    "v: təsdiq etmək = təsdiqləmək",
    "v: müqayisə etmək = tutuşdurmaq",
    "v: təhlil etmək = analiz etmək",
]
import os
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data_src", "lex_verbs.txt")
with io.open(out, "w", encoding="utf8") as fh:
    fh.write("# Avtomatik generasiya: tools/gen_verbs.py\n" + "\n".join(lines) + "\n")
