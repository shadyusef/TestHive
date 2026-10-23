"""Builds the single TestHive Studio program for this operating system with PyInstaller (CI does it for Windows, macOS and Linux).
Usage: python scripts/build-studio.py      needs: pip install pyinstaller (plus requirements.txt)
Output: dist/testhive-studio.exe on Windows, dist/testhive-studio elsewhere. The program carries the page (studio/) and every
library in scripts/lib; it works on any TestHive project folder (--project, the folder it starts in, or the last one opened)."""
import sys, os, glob, subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
libs = sorted(os.path.basename(p)[:-3] for p in glob.glob("scripts/lib/*.py") if not p.endswith("studio_app.py"))
cmd = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--onefile", "--console", "--name", "testhive-studio",
       "--paths", "scripts/lib", "--add-data", f"studio{os.pathsep}studio", "--add-data", f"VERSION{os.pathsep}.",
       *[x for m in libs for x in ("--hidden-import", m)], "scripts/lib/studio_app.py"]
print("Building TestHive Studio with:", " ".join(cmd[3:]), flush=True)
sys.exit(subprocess.call(cmd))
