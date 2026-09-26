import argparse
import io
import sys

from . import humanize, load_resources


def main():
    ap = argparse.ArgumentParser(description="Azərbaycan mətni üçün humanizer")
    ap.add_argument("file")
    ap.add_argument("--level", default="balanced", choices=["light", "balanced", "strong"])
    ap.add_argument("--variants", type=int, default=8)
    ap.add_argument("--seed", type=int, default=1)
    a = ap.parse_args()
    text = io.open(a.file, encoding="utf8").read()
    r = humanize(load_resources(), text, level=a.level, seed=a.seed, candidates=a.variants)
    sys.stdout.buffer.write(r.text.encode("utf8"))
    sys.stderr.write("\nskor: %s -> %s\n" % (r.before["score"], r.after["score"]))


if __name__ == "__main__":
    main()
