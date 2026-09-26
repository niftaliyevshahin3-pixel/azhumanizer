# -*- coding: utf-8 -*-
"""Yoxlayıcını təlim etdirir: insan = Azərbaycan Vikipediyası, AI = nümunə AI mətnləri."""
import io
import json
import math
import random
import sys

sys.path.insert(0, ".")
from azhum import detector
from azhum.textutil import count_words

random.seed(7)
wiki = json.load(io.open("tests/human/wiki_az.json", encoding="utf8"))
human = []
for art in wiki:
    cur = []
    for p in art["paragraphs"]:
        cur.append(p)
        if sum(count_words(x) for x in cur) >= 170:
            human.append((art["title"], "\n".join(cur)))
            cur = []
ai = []
for f in ["batch30_texts", "fresh30_texts"]:
    ai += [x["text"] for x in json.load(io.open("tests/%s.json" % f, encoding="utf8"))]
extra = "tests/ai_extra.json"
try:
    ai += json.load(io.open(extra, encoding="utf8"))
except Exception:
    pass
# AI mətnləri üçün alt-parçalar (daha çox nümunə)
ai_all = list(ai)
for t in ai:
    sents = t.split(". ")
    if len(sents) >= 10:
        ai_all.append(". ".join(sents[: int(len(sents) * 0.65)]) + ".")
        ai_all.append(". ".join(sents[int(len(sents) * 0.35):]))
print("human", len(human), "ai", len(ai_all))


def vec(t):
    r = detector.features(t)
    return None if r is None else r[0]


H = [(ti, vec(t)) for ti, t in human]
H = [(ti, v) for ti, v in H if v]
A = [("ai", vec(t)) for t in ai_all]
A = [(ti, v) for ti, v in A if v]
data = [(v, 0, ti) for ti, v in H] + [(v, 1, ti) for ti, v in A]
F = detector.FEATURES
mean = {k: sum(v[k] for v, _, _ in data) / len(data) for k in detector.ALL_FEATURES}
std = {k: math.sqrt(sum((v[k] - mean[k]) ** 2 for v, _, _ in data) / len(data)) or 1.0 for k in detector.ALL_FEATURES}


def z(v):
    return [(v[k] - mean[k]) / std[k] for k in F]


def train(rows, l2=0.08, epochs=1500, lr=0.15):
    w = [0.0] * len(F)
    b = 0.0
    n1 = sum(1 for r in rows if r[1] == 1)
    n0 = len(rows) - n1
    cw = {0: len(rows) / (2.0 * n0), 1: len(rows) / (2.0 * n1)}
    X = [(z(r[0]), r[1]) for r in rows]
    for ep in range(epochs):
        gw = [0.0] * len(F)
        gb = 0.0
        for x, y in X:
            s = b + sum(wi * xi for wi, xi in zip(w, x))
            p = 1 / (1 + math.exp(-max(-30, min(30, s))))
            e = (p - y) * cw[y]
            for i, xi in enumerate(x):
                gw[i] += e * xi
            gb += e
        for i in range(len(F)):
            w[i] -= lr * (gw[i] / len(X) + l2 * w[i])
        b -= lr * gb / len(X)
    return w, b


def predict(w, b, v):
    s = b + sum(wi * xi for wi, xi in zip(w, z(v)))
    return 1 / (1 + math.exp(-max(-30, min(30, s))))


def auc(pos, neg):
    c = 0.0
    for p in pos:
        for n in neg:
            c += 1 if p > n else (0.5 if p == n else 0)
    return c / (len(pos) * len(neg))


# məqalə səviyyəsində 5-qat çarpaz yoxlama (eyni məqalənin parçaları test/train-ə düşməsin)
titles = sorted({r[2] for r in data if r[1] == 0})
random.shuffle(titles)
folds = [titles[i::5] for i in range(5)]
ai_idx = [i for i, r in enumerate(data) if r[1] == 1]
random.shuffle(ai_idx)
aucs = []
fp = []
for k in range(5):
    test_titles = set(folds[k])
    test_ai = set(ai_idx[k::5])
    tr = [r for i, r in enumerate(data) if (r[1] == 0 and r[2] not in test_titles) or (r[1] == 1 and i not in test_ai)]
    te = [(r, i) for i, r in enumerate(data) if (r[1] == 0 and r[2] in test_titles) or (r[1] == 1 and i in test_ai)]
    w, b = train(tr, epochs=500)
    ph = [predict(w, b, r[0]) for r, _ in te if r[1] == 0]
    pa = [predict(w, b, r[0]) for r, _ in te if r[1] == 1]
    aucs.append(auc(pa, ph))
    fp.append(sum(1 for p in ph if p > 0.5) / max(1, len(ph)))
print("CV AUC", [round(a, 3) for a in aucs], "FP@0.5", [round(x, 2) for x in fp])

models = {}
for name, feats in (("struct", detector.FEATURES), ("content", detector.CONTENT_FEATURES), ("full", detector.ALL_FEATURES)):
    F = feats
    w, b = train(data)
    ph = [predict(w, b, v) for v, y, _ in data if y == 0]
    pa = [predict(w, b, v) for v, y, _ in data if y == 1]
    print(name, "train mean human %.3f  ai %.3f" % (sum(ph) / len(ph), sum(pa) / len(pa)))
    models[name] = {"w": dict(zip(F, w)), "bias": b, "mean": {k: mean[k] for k in F}, "std": {k: std[k] for k in F}, "features": list(F)}
    for k, wi in sorted(zip(F, w), key=lambda x: -abs(x[1]))[:8]:
        print("   %-14s %+.2f" % (k, wi))
models["note"] = "Vikipediya (insan) vs AI nümunələri; StrikePlagiarism deyil"
io.open("data_src/detector.json", "w", encoding="utf8").write(json.dumps(models, ensure_ascii=False, indent=1))
