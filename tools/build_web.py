"""web/ qovluğunu hazırlayır: Python paketi + lüğət faylları + manifest."""
import glob
import io
import json
import os
import shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB = os.path.join(ROOT, "docs")

py_dst = os.path.join(WEB, "py", "azhum")
data_dst = os.path.join(WEB, "data")
for d in (py_dst, data_dst):
    if os.path.isdir(d):
        shutil.rmtree(d)
    os.makedirs(d)

py_files = []
for p in sorted(glob.glob(os.path.join(ROOT, "azhum", "*.py"))):
    name = os.path.basename(p)
    shutil.copy(p, os.path.join(py_dst, name))
    py_files.append("py/azhum/" + name)

data_files = []
for p in sorted(glob.glob(os.path.join(ROOT, "data_src", "*.txt"))):
    name = os.path.basename(p)
    shutil.copy(p, os.path.join(data_dst, name))
    data_files.append("data/" + name)

manifest = {"py": py_files, "data": data_files, "version": "1.0"}
with io.open(os.path.join(WEB, "manifest.json"), "w", encoding="utf8") as fh:
    json.dump(manifest, fh, indent=1)
print("web ready:", len(py_files), "py,", len(data_files), "data")
