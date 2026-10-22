"""Claude Code hook (PostToolUse on Edit|Write|MultiEdit): checks a file right after Claude changed it, so a broken edit is
caught at once instead of minutes later in a failing run. Registered in .claude/settings.json; tested by scripts/selftest.sh.
Checks: shell syntax (bash -n), Python syntax, JSON, JavaScript (node --check), PowerShell parse (Windows), and no carriage
returns in files that must use LF (.gitattributes). Exit 2 = Claude sees the message on stderr and fixes the file."""
import sys, os, json, subprocess, shutil

try: data = json.load(sys.stdin)
except ValueError: sys.exit(0)
path = (data.get("tool_input") or {}).get("file_path") or ""
if not path or not os.path.isfile(path): sys.exit(0)
ext = os.path.splitext(path)[1].lower()
LF_ONLY = (".sh", ".py", ".mjs", ".js", ".ts", ".json", ".yml", ".yaml")  # CSV may come from Excel with CRLF
problems = []
raw = open(path, "rb").read()
if ext in LF_ONLY and b"\r" in raw:
    problems.append(f"contains a carriage-return byte (line {raw[:raw.index(b'\r')].count(b'\n') + 1}); "
                    "this file must use LF only. A \\r was probably written as a real character: write it as an escape or use [:cntrl:]")
try:
    if ext == ".sh" and shutil.which("bash"):
        r = subprocess.run(["bash", "-n", path], capture_output=True, text=True)
        if r.returncode: problems.append("bash syntax error: " + r.stderr.strip()[:400])
    elif ext == ".py":
        compile(raw.decode("utf-8-sig"), path, "exec")  # syntax only, nothing written
    elif ext == ".json":
        json.loads(raw.decode("utf-8-sig"))
    elif ext in (".mjs", ".js") and shutil.which("node"):
        r = subprocess.run(["node", "--check", path], capture_output=True, text=True)
        if r.returncode: problems.append("JavaScript syntax error: " + r.stderr.strip()[:400])
    elif ext == ".ps1" and shutil.which("powershell.exe"):
        ps = ("$e=$null; [void][System.Management.Automation.Language.Parser]::ParseFile('" + os.path.abspath(path).replace("'", "''") +
              "',[ref]$null,[ref]$e); if($e){$e[0].Extent.StartLineNumber.ToString() + ': ' + $e[0].Message}")
        r = subprocess.run(["powershell.exe", "-NoProfile", "-Command", ps], capture_output=True, text=True)
        if r.stdout.strip(): problems.append("PowerShell parse error at line " + r.stdout.strip()[:300])
except SyntaxError as e: problems.append(f"Python syntax error at line {e.lineno}: {e.msg}")
except ValueError as e: problems.append(f"invalid JSON: {e}")
if problems:
    print(f"Edit check failed for {path}:\n- " + "\n- ".join(problems), file=sys.stderr)
    sys.exit(2)
