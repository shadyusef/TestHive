"""Entry point of the single TestHive Studio program (built by scripts/build-studio.py with PyInstaller).
  testhive-studio [--project <folder>] [--port N] [--no-browser]   starts Studio (see scripts/lib/studio.py)
  testhive-studio --lib <name>.py <args>                           runs one of TestHive's libraries (used by Studio itself)
  testhive-studio --script <file.py> <args>                        runs a Python script (the demos' recorded agents)"""
import sys, os, re, runpy
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def main():
    a = sys.argv[1:]
    if a[:1] == ["--lib"] and len(a) > 1:
        if not re.fullmatch(r"[a-z_]+\.py", a[1]): sys.exit(f"Unknown library: {a[1]}")
        sys.argv = [a[1]] + a[2:]
        runpy.run_module(a[1][:-3], run_name="__main__", alter_sys=True)
    elif a[:1] == ["--script"] and len(a) > 1:
        sys.argv = a[1:]
        runpy.run_path(a[1], run_name="__main__")
    else:
        import studio
        studio.main()


if __name__ == "__main__":
    main()
