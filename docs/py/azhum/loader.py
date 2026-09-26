import glob
import io
import os


def load_resources(data_dir=None):
    """Yerli fayl sistemindən lüğət, ifadə cədvəli və yoxlayıcı modelini yükləyir."""
    from .engine import Resources
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = data_dir or os.path.join(base, "data_src")
    texts = []
    for p in sorted(glob.glob(os.path.join(data_dir, "lex_*.txt"))):
        with io.open(p, encoding="utf8") as fh:
            texts.append(fh.read())
    phrases = ""
    for p in sorted(glob.glob(os.path.join(data_dir, "phrases_*.txt"))):
        with io.open(p, encoding="utf8") as fh:
            phrases += fh.read() + "\n"
    det = None
    dp = os.path.join(data_dir, "detector.json")
    if os.path.exists(dp):
        with io.open(dp, encoding="utf8") as fh:
            det = fh.read()
    return Resources(texts, phrases, det)
