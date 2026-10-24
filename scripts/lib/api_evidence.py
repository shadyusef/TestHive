"""Turns a Newman JSON report into one evidence file per request: the request and the response, with Authorization, cookies,
API keys and secret-looking JSON fields masked. Called by scripts/run-api.sh; collect-run.sh links a file to its case by the
TC-ID in its name. Usage: python api_evidence.py <newman.json> <out folder>"""
import sys, os, re, json

SECRET = r"password|passwd|secret|token|jwt|bearer|api[-_]?key|access[-_]?key|private[-_]?key|credential|session|sid|otp|pin"
SECRET_HEADER = re.compile(SECRET + r"|authorization|cookie", re.I)
SECRET_FIELD = re.compile(SECRET, re.I)
PAIR = re.compile(r"((?:" + SECRET + r")[\w-]*[\"']?\s*[=:]\s*[\"']?)([^\s&\"',;]+)", re.I)  # key=value or "key": "value" in any text
MAX_BODY = 20000  # characters of each body kept
# the secret values of the run's environment (run-api.sh exports TEST_*): replaced wherever they appear, even in a check's message
KNOWN = sorted({v for k, v in os.environ.items() if k.startswith("TEST_") and re.search(r"TOKEN|PASSWORD|SECRET|KEY", k) and len(v) >= 4}, key=len, reverse=True)


def scrub(t):
    t = str(t or "")
    for v in KNOWN: t = t.replace(v, "***")
    return PAIR.sub(lambda m: m[1] + "***", t)


def mask(v):
    """JSON: everything under a secret-looking key becomes ***; anything else is kept as it is."""
    if isinstance(v, dict): return {k: "***" if SECRET_FIELD.search(k) else mask(x) for k, x in v.items()}
    if isinstance(v, list): return [mask(x) for x in v]
    return v


def body(text):
    try: return json.dumps(mask(json.loads(text)), indent=2, ensure_ascii=False)[:MAX_BODY]
    except ValueError: return scrub((text or "")[:MAX_BODY])


def headers(hs): return "\n".join(f"{h.get('key')}: {'***' if SECRET_HEADER.search(h.get('key', '')) else h.get('value')}" for h in hs or [] if not h.get("disabled"))


def url(u):
    if isinstance(u, str): return u
    q = "&".join(f"{p.get('key')}={'***' if SECRET_FIELD.search(p.get('key') or '') else p.get('value')}" for p in u.get("query") or [] if not p.get("disabled"))
    return f"{u.get('protocol', 'http')}://{'.'.join(u.get('host') or [])}{':' + str(u['port']) if u.get('port') else ''}/{'/'.join(u.get('path') or [])}" + (f"?{q}" if q else "")


def stream(r):
    s = (r or {}).get("stream")
    if isinstance(s, dict) and isinstance(s.get("data"), list): return bytes(s["data"]).decode("utf-8", "replace")
    return s if isinstance(s, str) else ""


def main():
    src, out = sys.argv[1], sys.argv[2]
    with open(src, encoding="utf-8") as f: run = json.load(f).get("run", {})
    os.makedirs(out, exist_ok=True)
    for n, ex in enumerate(run.get("executions") or [], 1):
        name = (ex.get("item") or {}).get("name", "")
        m = re.search(r"TC-[A-Z0-9]+(?:-[A-Z0-9]+)*-\d{3}", name)
        rq, rs = ex.get("request") or {}, ex.get("response") or {}
        checks = "\n".join(f"{'ok  ' if not a.get('error') else 'FAIL'} {a.get('assertion')}" + (f": {scrub(a['error'].get('message'))}" if a.get("error") else "") for a in ex.get("assertions") or [])
        text = (f"{name}\n\n> {rq.get('method', '')} {url(rq.get('url') or {})}\n{headers(rq.get('header'))}\n\n{body(((rq.get('body') or {}).get('raw')) or '')}\n\n"
                f"< {rs.get('code', '')} {rs.get('status', '')} ({rs.get('responseTime', '')} ms)\n{headers(rs.get('header'))}\n\n{body(stream(rs))}\n\n{checks}\n")
        slug = re.sub(r"[^A-Za-z0-9]+", "-", name)[:60].strip("-") or "request"
        fname = (f"{n:03d}-{m[0]}-{slug}" if m else f"{n:03d}-{slug}")[:116] + ".txt"  # the TC-ID in the name links it to its case
        with open(os.path.join(out, fname), "w", encoding="utf-8", newline="\n") as f: f.write(scrub(text) if KNOWN else text)


if __name__ == "__main__":
    main()
