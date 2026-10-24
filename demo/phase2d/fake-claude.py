"""Recorded stand-in for Claude Code, used by TestHive Studio when TH_CLAUDE_FAKE points to this file (demo, selftest, CI).
It accepts the same arguments as `claude --agent <name> ... -p <task>`, replays the recorded runs of the fictional SIGNUP
module (demo/phase1/recorded, demo/phase2/recorded) and prints Claude Code stream-json events, so Studio's Run buttons,
progress, Stop and the results can be tested without using a Claude plan. It only knows module SIGNUP."""
import sys, os, re, json, time, shutil, subprocess

a = sys.argv[1:]
agent, task = a[a.index("--agent") + 1], a[a.index("-p") + 1]
module = (re.search(r"Module (\w+)", task) or [None, "SIGNUP"])[1]
t = task.lower()  # which recorded run: matched on the phrases of the tasks in scripts/lib/studio.py ACTIONS
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
P1, P2 = os.path.join(ROOT, "demo", "phase1", "recorded"), os.path.join(ROOT, "demo", "phase2", "recorded")
DELAY = float(os.environ.get("TH_FAKE_DELAY", "0.3"))
BASH = os.environ.get("TH_BASH") or "bash"


def emit(ev): print(json.dumps(ev), flush=True); time.sleep(DELAY)
def tool(name, **inp): emit({"type": "assistant", "message": {"content": [{"type": "tool_use", "name": name, "input": inp}]}})
def say(text): emit({"type": "assistant", "message": {"content": [{"type": "text", "text": text}]}})
def sh(cmd):
    tool("Bash", command="bash " + " ".join(cmd))
    subprocess.run([BASH] + cmd, capture_output=True)
def copy(src, dst):
    tool("Write", file_path=dst.replace(os.sep, "/")); os.makedirs(os.path.dirname(dst) or ".", exist_ok=True); shutil.copy(src, dst)


emit({"type": "system", "subtype": "init", "model": "recorded", "tools": ["Bash", "Read", "Write", "Edit"]})
say(f"(recorded {agent} run for {module})")
if os.environ.get("TH_FAKE_ASK") and "--permission-prompt-tool" in a:  # phase 7: ask the person through Studio, as Claude Code does
    srv = json.loads(a[a.index("--mcp-config") + 1])["mcpServers"]["testhive"]
    p = subprocess.Popen([srv["command"]] + srv["args"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, env=dict(os.environ, **srv.get("env", {})))
    def rpc(i, method, params=None):
        p.stdin.write(json.dumps({"jsonrpc": "2.0", "id": i, "method": method, "params": params or {}}) + "\n"); p.stdin.flush()
        return json.loads(p.stdout.readline())
    rpc(1, "initialize", {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "recorded"}})
    outcome = []
    for n, (name, inp) in enumerate((("Bash", {"command": "npx playwright test --headed"}), ("Write", {"file_path": "web/playwright.config.ts", "content": "// changed"})), 2):
        say(f"I need {name}: {json.dumps(inp)}")
        r = json.loads(rpc(n, "tools/call", {"name": "approve", "arguments": {"tool_name": name, "input": inp}})["result"]["content"][0]["text"])
        outcome.append(r["behavior"]); say(f"{name}: {r['behavior']}" + (f" ({r['message']})" if r.get("message") else ""))
    p.stdin.close(); p.wait(timeout=10)
    emit({"type": "result", "is_error": False, "result": "Asked twice: " + ", ".join(outcome), "total_cost_usd": 0.01}); sys.exit(0)
if module != "SIGNUP":
    say("The recorded runs only exist for module SIGNUP."); emit({"type": "result", "is_error": True, "result": "No recording for this module.", "total_cost_usd": 0}); sys.exit(1)
if agent == "business-analyst" and "explore the android app only" in t:  # phase 7: two recorded screens (no phone here)
    out = f"analysis/exploration/{module}/android"; os.makedirs(out, exist_ok=True)
    png = bytes.fromhex("89504e470d0a1a0a0000000d4948445200000001000000010806000000" "1f15c4890000000d4944415478da63f8cfc0f01f0005000201" "a7c9a6b80000000049454e44ae426082")
    sh(["scripts/explore-android.sh", module, "packages"])
    md = ["# Android exploration", "Everything below is OBSERVED behaviour, not confirmed requirements.", ""]
    for n, name in enumerate(("sign-up", "otp"), 1):
        tool("Bash", command=f"bash scripts/explore-android.sh {module} snap {name}")
        with open(f"{out}/{n:02d}-{name}.png", "wb") as f: f.write(png)
        md += [f"## {n:02d} {name}", f"- Screenshot: {n:02d}-{name}.png", ""]
    with open(f"{out}/exploration.md", "w", encoding="utf-8") as f: f.write(chr(10).join(md))
    summary = "Explored the app: 2 screens (sign-up, OTP). Not submitted."
elif agent == "business-analyst" and "answered questions" not in t:
    sh(["scripts/stage.sh", "start", module, "analysis"])
    tool("Read", file_path=f"analysis/sources-text/{module}/prd.pdf.md")
    copy(os.path.join(P1, "first-pass", "requirements.csv"), "analysis/requirements.csv")
    copy(os.path.join(P1, "first-pass", "gaps.csv"), "analysis/gaps.csv")
    sh(["scripts/check-analysis.sh", module]); sh(["scripts/analysis-workbook.sh", module])
    summary = "First pass done: 32 requirements and 35 questions (13 High). Answer them, then run the re-check. Not submitted."
elif agent == "business-analyst":
    sh(["scripts/import-answers.sh", module])
    copy(os.path.join(P1, "recheck-2", "requirements.csv"), "analysis/requirements.csv")
    copy(os.path.join(P1, "recheck-2", "gaps.csv"), "analysis/gaps.csv")
    sh(["scripts/check-analysis.sh", module, "--for-approval"]); sh(["scripts/stage.sh", "submit", module, "analysis"])
    summary = "Re-check done (recorded answers applied): every High question closed, analysis submitted for approval."
elif agent == "manual-tester" and "reviewer wrote" in t:
    copy(os.path.join(P2, "after-review", "TestCases.csv"), "test-cases/TestCases.csv")
    copy(os.path.join(P2, "after-review", "gaps.csv"), "analysis/gaps.csv")
    sh(["scripts/check-design.sh", module, "--set-priority"]); sh(["scripts/design-workbook.sh", module])
    summary = "Fixed the 6 Major findings: 119 active cases, 7 new questions for the business. Not submitted."
elif agent == "manual-tester" and "human reviewed" in t:
    copy(os.path.join(P2, "recheck-1", "TestCases.csv"), "test-cases/TestCases.csv")
    copy(os.path.join(P2, "recheck-1", "requests.csv"), "test-cases/requests.csv")
    copy(os.path.join(P2, "recheck-1", "gaps.csv"), "analysis/gaps.csv")
    sh(["scripts/check-design.sh", module, "--for-approval"]); sh(["scripts/stage.sh", "submit", module, "design"])
    summary = "Review handled (recorded): 121 active cases, design submitted for approval."
elif agent == "manual-tester":
    sh(["scripts/stage.sh", "start", module, "design"])
    copy(os.path.join(P2, "first-pass", "TestCases.csv"), "test-cases/TestCases.csv")
    sh(["scripts/check-design.sh", module, "--set-priority"]); sh(["scripts/design-workbook.sh", module])
    summary = "First design: 104 cases covering 28 of 28 requirements. Ask the reviewer for a pre-review."
elif agent == "qa-reviewer":
    sh(["scripts/check-design.sh", module])
    copy(os.path.join(P2, "DESIGN-SIGNUP-1.md"), "reviews/DESIGN-SIGNUP-1.md")
    summary = "Pre-review written: reviews/DESIGN-SIGNUP-1.md. Verdict: changes required, 6 Major, 10 Minor, 4 Nit."
elif agent in ("web-automation-engineer", "api-backend-test-engineer"):  # phase 4: the smoke tests, written against demo/phase4/app
    kind = "web" if agent.startswith("web") else "api"
    tool("Read", file_path=f"web/tests/{module}/" if kind == "web" else f"api/collections/{module}.postman_collection.json")
    import io, runpy, contextlib
    out, sys.argv = io.StringIO(), ["apply.py", kind, "."]  # in this process: inside the Studio program there is no python to start
    with contextlib.redirect_stdout(out): runpy.run_path(os.path.join(ROOT, "demo", "phase4", "recorded", "apply.py"))
    for f in out.getvalue().split():
        if "/" in f and not f.endswith(":"): tool("Write", file_path=f)
    tool("Bash", command=f"bash scripts/run-{kind}.sh {module} --tag smoke")
    subprocess.run([BASH, f"scripts/run-{kind}.sh", module, "--tag", "smoke"], capture_output=True, env=dict(os.environ, NO_COLLECT="1"))
    tool("Bash", command=f"TH_TAG=smoke bash scripts/stable.sh {kind} {module}")
    r = subprocess.run([BASH, "scripts/stable.sh", kind, module], capture_output=True, text=True, env=dict(os.environ, TH_TAG="smoke", NO_COLLECT="1"))
    n = len(re.findall(r"TC-[A-Z0-9]+-\d{3}", (re.search(r"STABLE[^\n]*", r.stdout) or [""])[0]))
    summary = (f"Wrote the {7 if kind == 'web' else 4} smoke {kind} tests (recorded): {n} pass 3 runs in a row. "
               "The other cases are still placeholders: the recording stops at smoke. Not submitted.")
else:
    summary = f"No recording for {agent}."
say(summary)
emit({"type": "result", "subtype": "success", "is_error": False, "result": summary, "total_cost_usd": 0})
