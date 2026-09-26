# -*- coding: utf-8 -*-
"""Azərbaycan Vikipediyasından insan yazısı nümunələri (kalibrasiya üçün)."""
import io, json, re, sys, urllib.parse, urllib.request
TITLES = ["İqtisadiyyat", "Makroiqtisadiyyat", "İnflyasiya", "İşsizlik", "Ümumi daxili məhsul", "Bank", "Vergi", "Pul", "Bazar iqtisadiyyatı",
          "Azərbaycan tarixi", "Bakı", "Gəncə", "Xəzər dənizi", "Nizami Gəncəvi", "Fizuli", "Riyaziyyat", "Fizika", "Kimya", "Biologiya",
          "Coğrafiya", "Fəlsəfə", "Psixologiya", "Sosiologiya", "Ekologiya", "İqlim", "Enerji", "İnternet", "Kompüter", "Təhsil", "Musiqi",
          "Ədəbiyyat", "Tibb", "Kənd təsərrüfatı", "Nəqliyyat", "Turizm", "Dil", "Mədəniyyət", "Hüquq", "Siyasət", "Demokratiya"]
import os, time
PATH = "tests/human/wiki_az.json"
out = json.load(io.open(PATH, encoding="utf8")) if os.path.exists(PATH) else []
have = {o["title"] for o in out}
for t in TITLES:
    if t in have:
        continue
    time.sleep(4)
    url = "https://az.wikipedia.org/w/api.php?action=query&prop=extracts&explaintext=1&exsectionformat=plain&format=json&titles=" + urllib.parse.quote(t)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "AzHumanizerCalibration/1.0"})
        data = json.loads(urllib.request.urlopen(req, timeout=30).read().decode("utf8"))
        page = list(data["query"]["pages"].values())[0]
        text = page.get("extract", "")
    except Exception as e:
        print("fail", t, e); continue
    text = re.sub(r"\n{2,}", "\n", text)
    paras = [p.strip() for p in text.split("\n") if len(p.strip().split()) >= 25]
    out.append({"title": t, "paragraphs": paras})
    print(t, len(paras), sum(len(p.split()) for p in paras))
io.open("tests/human/wiki_az.json", "w", encoding="utf8").write(json.dumps(out, ensure_ascii=False, indent=0))
