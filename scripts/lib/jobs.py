"""TestHive jobs: runs an agent (Claude Code, headless) or an exploration script in the background for TestHive Studio,
and keeps its progress. One job per module at a time. Every job is saved in runs/agents/<id>/ (git-ignored):
  meta.json        id, module, kind, agent, title, task, status (running, done, failed, stopped, interrupted), times, summary, cost
  progress.txt     one readable line per step (scripts run, files written, messages)
  transcript.jsonl the raw Claude Code event stream (agents only)
Agents run as: claude --agent <name> --permission-mode acceptEdits --allowedTools "Bash(bash scripts/*)" --output-format stream-json
--verbose -p <task>. They cannot answer permission prompts: anything outside bash scripts/* and file edits fails and is reported.
TH_CLAUDE_FAKE=<script.py> replaces Claude Code with a recorded stand-in (demos, selftest and CI spend nothing)."""
import sys, os, re, json, time, shutil, signal, subprocess, threading
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pyrun

DIR = os.path.join("runs", "agents")
MAX_MINUTES = int(os.environ.get("TH_JOB_MAX_MINUTES", "90"))
JOBS, LOCK = {}, threading.RLock()


def now(): return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def save(job):
    d = job.get("_dir") or os.path.join(DIR, job["id"]); os.makedirs(d, exist_ok=True)
    keep = {k: v for k, v in job.items() if not k.startswith("_")}
    with open(os.path.join(d, "meta.json") + ".tmp", "w", encoding="utf-8", newline="\n") as f: json.dump(keep, f, indent=2, ensure_ascii=False)
    os.replace(os.path.join(d, "meta.json") + ".tmp", os.path.join(d, "meta.json"))


def alive(pid):
    """Is this process still running? (os.kill(pid, 0) would end it on Windows.)"""
    try: pid = int(pid)
    except (TypeError, ValueError): return False
    if pid <= 0: return False
    if os.name == "nt":
        import ctypes
        k = ctypes.windll.kernel32
        h = k.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
        if not h: return False
        code = ctypes.c_ulong(); ok = k.GetExitCodeProcess(h, ctypes.byref(code)); k.CloseHandle(h)
        return bool(ok) and code.value == 259  # STILL_ACTIVE
    try: os.kill(pid, 0)
    except PermissionError: return True
    except OSError: return False
    return True


JOB_ID = re.compile(r"\d{8}-\d{6}-[A-Z][A-Z0-9]*-[a-z-]+")  # what start() names a job, and its folder


def load_history():
    """Jobs from disk: earlier Studio sessions, and jobs another Studio on this project runs right now (read again each time).
    A job marked running whose process is gone is 'interrupted'."""
    if not os.path.isdir(DIR): return
    for name in os.listdir(DIR):
        if not JOB_ID.fullmatch(name): continue
        p, mine = os.path.join(DIR, name, "meta.json"), JOBS.get(name)
        if mine and (mine.get("_proc") or mine["status"] != "running") or not os.path.exists(p): continue
        try:
            with open(p, encoding="utf-8") as f: job = json.load(f)
        except ValueError: continue
        if not isinstance(job, dict) or job.get("id") != name: continue  # the folder names the job: a meta.json never points elsewhere
        # shortcut: a reused process number keeps a dead job "running" until that process ends; rare, fine for a desktop tool
        if job.get("status") == "running" and not alive(job.get("pid")):
            job["status"] = "interrupted"; job["summary"] = "Studio was closed while this job ran."; save(job)
        JOBS[job["id"]] = job


def running(module):
    return next((j for j in JOBS.values() if j["module"] == module and j["status"] == "running"), None)


def listing(module=None):
    load_history()
    js = [j for j in JOBS.values() if module is None or j["module"] == module]
    return sorted(({k: v for k, v in j.items() if not k.startswith("_")} for j in js), key=lambda j: j["started"], reverse=True)


def progress(job_id, last=None):
    p = os.path.join(DIR, job_id, "progress.txt")
    if not os.path.exists(p): return []
    with open(p, encoding="utf-8", errors="replace") as f: lines = f.read().splitlines()
    return lines[-last:] if last else lines


def claude_command(agent, task, model=None):
    fake = os.environ.get("TH_CLAUDE_FAKE")
    if fake: base = pyrun.script_cmd(fake)
    else:
        exe = shutil.which("claude")
        if not exe: return None
        base = [exe]
    # the project settings also allow maestro, adb, newman and playwright for the QA team; a background agent gets scripts only
    return base + ["--agent", agent, "--permission-mode", "acceptEdits", "--allowedTools", "Bash(bash scripts/*)",
                   "--disallowedTools", "Bash(maestro *)", "Bash(adb *)", "Bash(newman *)", "Bash(npx *)",
                   "--output-format", "stream-json", "--verbose"] + (["--model", model] if model else []) + ["-p", task]


def describe(event):
    """Readable progress lines from one Claude Code stream-json event."""
    out = []
    if event.get("type") == "assistant":
        for c in (event.get("message") or {}).get("content") or []:
            if c.get("type") == "tool_use":
                i, name = c.get("input") or {}, c.get("name")
                if name == "Bash": out.append("$ " + str(i.get("command", ""))[:200])
                elif name in ("Write", "Edit", "MultiEdit", "NotebookEdit"): out.append(f"writes {i.get('file_path', '')}")
                elif name == "Read": out.append(f"reads {i.get('file_path', '')}")
                elif name in ("Glob", "Grep"): out.append(f"searches {i.get('pattern', '')}")
                else: out.append(f"uses {name}")
            elif c.get("type") == "text" and c.get("text", "").strip():
                out.append("> " + " ".join(c["text"].split())[:240])
    elif event.get("type") == "user":
        for c in (event.get("message") or {}).get("content") or []:
            if isinstance(c, dict) and c.get("type") == "tool_result" and c.get("is_error"):
                txt = c.get("content") if isinstance(c.get("content"), str) else json.dumps(c.get("content"))[:200]
                out.append("  ! " + " ".join(str(txt).split())[:200])
    return out


def _follow(job, proc):
    d = job["_dir"]
    started = time.time()
    with open(os.path.join(d, "progress.txt"), "a", encoding="utf-8", newline="\n") as prog, \
         open(os.path.join(d, "transcript.jsonl"), "a", encoding="utf-8", newline="\n") as raw:
        for line in proc.stdout:
            line = line.rstrip("\n")
            if not line: continue
            if job["kind"] == "agent":
                raw.write(line + "\n")
                try: ev = json.loads(line)
                except ValueError:  # plain text from Claude Code; its folder-trust notice is noise here
                    if not line.startswith("Ignoring "): prog.write(line[:240] + "\n"); prog.flush()
                    continue
                if ev.get("type") == "result" or "total_cost_usd" in ev:
                    job["summary"] = ev.get("result") or job.get("summary", "")
                    if ev.get("total_cost_usd") is not None: job["cost_usd"] = round(float(ev["total_cost_usd"]), 4)
                    if ev.get("is_error"): job["_error"] = True
                for l in describe(ev): prog.write(l + "\n")
            else:
                prog.write(line[:300] + "\n"); job["summary"] = line[:300] or job.get("summary", "")
            prog.flush()
            if time.time() - started > MAX_MINUTES * 60:
                stop(job["id"], f"stopped after {MAX_MINUTES} minutes (TH_JOB_MAX_MINUTES)"); break
    code = proc.wait()
    with LOCK:
        if job["status"] == "running":
            job["status"] = "done" if code == 0 and not job.get("_error") else "failed"
            if job["status"] == "failed" and not job.get("summary"): job["summary"] = f"ended with exit code {code}; see the progress lines"
        job["ended"] = now(); job["exit_code"] = code
        save(job)


def start(module, kind, title, cmd, task="", agent=""):
    """Starts a job unless the module already has one. Returns (job, error)."""
    with LOCK:
        load_history()
        if running(module): return None, f"{running(module)['title']} is still working on {module}. Wait for it or stop it first."
        job = {"id": time.strftime("%Y%m%d-%H%M%S") + f"-{module}-{(agent or kind)}", "module": module, "kind": kind, "agent": agent,
               "title": title, "task": task, "status": "running", "started": now(), "ended": "", "summary": "", "cost_usd": None}
        job["_dir"] = os.path.abspath(os.path.join(DIR, job["id"]))  # stays in this project even if Studio switches project later
        save(job)
        kw = {"start_new_session": True} if os.name != "nt" else {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP}
        env = dict(os.environ, PYTHONIOENCODING="utf-8", TH_JOB=job["id"])  # stage.sh and the hooks treat it as an agent, not a person
        try:
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, text=True,
                                    encoding="utf-8", errors="replace", env=env, **kw)
        except OSError as e:
            job.update(status="failed", ended=now(), summary=f"could not start: {e}"); save(job); JOBS[job["id"]] = job
            return job, None
        job["_proc"], job["pid"] = proc, proc.pid
        JOBS[job["id"]] = job
    threading.Thread(target=_follow, args=(job, proc), daemon=True).start()
    watchdog = threading.Timer(MAX_MINUTES * 60, stop, args=(job["id"], f"stopped after {MAX_MINUTES} minutes (TH_JOB_MAX_MINUTES)"))
    watchdog.daemon = True; watchdog.start()  # also fires when the agent hangs without printing anything
    return job, None


def stop(job_id, why="stopped by the user"):
    with LOCK:  # _follow saves the same job when the process ends: one writer of meta.json at a time
        return _stop(job_id, why)


def _stop(job_id, why):
    job = JOBS.get(job_id)
    if not job or job["status"] != "running": return False
    proc = job.get("_proc")
    if not proc: return False  # started by another Studio window: only that one may stop it (a process number read from a file is never killed)
    job["status"], job["summary"] = "stopped", why
    if proc.poll() is None:
        if os.name == "nt":  # the whole tree: claude.cmd starts node, node starts the tools
            subprocess.run(["taskkill", "/T", "/F", "/PID", str(proc.pid)], capture_output=True)
        else:
            try: os.killpg(proc.pid, signal.SIGTERM)
            except OSError: proc.terminate()
            def finish():
                try: proc.wait(5)
                except subprocess.TimeoutExpired:
                    try: os.killpg(proc.pid, signal.SIGKILL)
                    except OSError: proc.kill()
            threading.Thread(target=finish, daemon=True).start()
    job["ended"] = now(); save(job)
    return True
