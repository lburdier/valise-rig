"""Construit le paquet d'extension Blender : dist/valise_rig-X.Y.Z.zip (manifest à la racine du zip)."""
import os
import sys
import tomllib
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXCLUDE_DIRS = {".git", ".github", "tools", "dist", "tests", "__pycache__", ".vscode", ".idea"}
EXCLUDE_EXT = {".zip", ".pyc", ".blend", ".blend1"}

with open(os.path.join(ROOT, "blender_manifest.toml"), "rb") as f:
    man = tomllib.load(f)
out_dir = os.path.join(ROOT, "dist")
os.makedirs(out_dir, exist_ok=True)
out = os.path.join(out_dir, "%s-%s.zip" % (man["id"], man["version"]))

n = 0
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
    for base, dirs, files in os.walk(ROOT):
        dirs[:] = sorted(d for d in dirs if d not in EXCLUDE_DIRS)
        for fn in sorted(files):
            if os.path.splitext(fn)[1] in EXCLUDE_EXT or fn.startswith("."):
                continue
            path = os.path.join(base, fn)
            z.write(path, os.path.relpath(path, ROOT).replace(os.sep, "/"))
            n += 1
print("%s (%d fichiers)" % (out, n))
if "--check" in sys.argv:
    with zipfile.ZipFile(out) as z:
        names = z.namelist()
    assert "blender_manifest.toml" in names and "__init__.py" in names, names
    print("contenu OK")
