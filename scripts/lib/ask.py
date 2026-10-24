"""TestHive's permission helper for agents started from Studio (phase 7a). Claude Code runs it as a small MCP server (stdio) and,
through --permission-prompt-tool, calls its one tool `approve` whenever the agent wants something its rules do not already allow.
The question is written to the job's folder (asks/<n>.json); Studio shows it, a person answers (asks/<n>.answer.json), and the
answer goes back to Claude Code. No answer within TH_ASK_MINUTES (default 10) is a No. Deny rules, the hooks and the blocked
commands still apply before any question is asked. Started by jobs.py (claude_command); TH_ASK_DIR is the job's folder."""
import sys, os, json, time

DIR = os.path.join(os.environ.get("TH_ASK_DIR", "."), "asks")
WAIT = float(os.environ.get("TH_ASK_MINUTES", "10")) * 60
SHOWN = 4000      # characters of the input Studio shows: a question longer than that is refused, never allowed half-read
MAX_WAITING = 20  # questions waiting at once; more are refused (an agent could flood the page)
POLL = float(os.environ.get("TH_ASK_POLL", "0.5"))
TOOL = {"name": "approve", "description": "Asks the person in TestHive Studio to allow or deny a tool use the agent's rules do not already allow.",
        "inputSchema": {"type": "object", "properties": {"tool_name": {"type": "string"}, "input": {"type": "object"}, "tool_use_id": {"type": "string"}},
                        "required": ["tool_name", "input"]}}


def write(p, data):
    with open(p + ".tmp", "w", encoding="utf-8", newline="\n") as f: json.dump(data, f, ensure_ascii=False, indent=1)
    os.replace(p + ".tmp", p)


def ask(tool_name, inp):
    """Writes the question, waits for the person's answer; returns Claude Code's permission result."""
    os.makedirs(DIR, exist_ok=True)
    if len(json.dumps(inp, ensure_ascii=False, indent=1)) > SHOWN or len(str(tool_name)) > 100:
        return {"behavior": "deny", "message": "Too long to show the person in full, so not allowed: split it into smaller steps."}
    if sum(1 for f in os.listdir(DIR) if f.endswith(".json") and not f.endswith(".answer.json") and not os.path.exists(os.path.join(DIR, f[:-5] + ".answer.json"))) >= MAX_WAITING:
        return {"behavior": "deny", "message": "Too many questions are waiting: not allowed."}
    n = 1 + max((int(f.split(".")[0]) for f in os.listdir(DIR) if f.split(".")[0].isdigit()), default=0)
    q = os.path.join(DIR, f"{n:03d}.json")
    write(q, {"id": f"{n:03d}", "tool": str(tool_name)[:100], "input": inp, "asked_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())})
    a, end = os.path.join(DIR, f"{n:03d}.answer.json"), time.time() + WAIT
    while time.time() < end:
        if os.path.exists(a):
            try:
                with open(a, encoding="utf-8") as f: ans = json.load(f)
            except (OSError, ValueError): time.sleep(POLL); continue
            if ans.get("decision") == "allow": return {"behavior": "allow", "updatedInput": inp}
            return {"behavior": "deny", "message": "The person in TestHive Studio said no" + (f": {ans['note']}" if ans.get("note") else ".")}
        time.sleep(POLL)
    write(a, {"decision": "deny", "by": "TestHive", "note": "no answer in time", "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())})
    return {"behavior": "deny", "message": "No answer from the person in TestHive Studio in time: not allowed. Go on without it, or stop and say what you need."}


def reply(i, result=None, error=None):
    msg = {"jsonrpc": "2.0", "id": i}
    msg.update({"error": error} if error else {"result": result})
    sys.stdout.write(json.dumps(msg) + "\n"); sys.stdout.flush()


def main():
    for line in sys.stdin:  # MCP over stdio: one JSON-RPC message per line
        try: m = json.loads(line)
        except ValueError: continue
        method, i = m.get("method"), m.get("id")
        if i is None: continue  # a notification (initialized, cancelled): nothing to answer
        if method == "initialize":
            reply(i, {"protocolVersion": (m.get("params") or {}).get("protocolVersion", "2024-11-05"), "capabilities": {"tools": {}},
                      "serverInfo": {"name": "testhive", "version": "1"}})
        elif method == "tools/list": reply(i, {"tools": [TOOL]})
        elif method == "tools/call" and (m.get("params") or {}).get("name") == "approve":
            args = (m.get("params") or {}).get("arguments") or {}
            res = ask(args.get("tool_name", ""), args.get("input") or {})
            reply(i, {"content": [{"type": "text", "text": json.dumps(res)}]})
        elif method == "ping": reply(i, {})
        else: reply(i, error={"code": -32601, "message": f"unknown method {method}"})


if __name__ == "__main__":
    main()
