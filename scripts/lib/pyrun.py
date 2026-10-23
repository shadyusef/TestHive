"""How TestHive's Python code starts another of its libraries, from source or from the single Studio program (the .exe).
From source: python scripts/lib/<name>. In the program, sys.executable is the program itself, so it is started again with
--lib <name> (scripts/lib/studio_app.py runs that library). TH_LAUNCHER=<path to studio_app.py> makes source runs take the
program's route, so the tests cover it without building the program."""
import sys, os

HERE = os.path.dirname(os.path.abspath(__file__))
FROZEN = bool(getattr(sys, "frozen", False))


def lib_cmd(name, *args):
    """The command that runs scripts/lib/<name> with the given arguments."""
    if FROZEN: return [sys.executable, "--lib", name, *args]
    if os.environ.get("TH_LAUNCHER"): return [sys.executable, os.environ["TH_LAUNCHER"], "--lib", name, *args]
    return [sys.executable, os.path.join(HERE, name), *args]


def script_cmd(path, *args):
    """The command that runs a Python script file (the recorded stand-in for Claude Code in the demos)."""
    if FROZEN: return [sys.executable, "--script", path, *args]
    return [sys.executable, path, *args]


def bundle_dir(*parts):
    """A folder shipped with Studio: inside the program, or the repository's own when run from source."""
    base = getattr(sys, "_MEIPASS", None) or os.path.join(HERE, "..", "..")
    return os.path.join(base, *parts)
