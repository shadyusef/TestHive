"""TestHive contract tests (stage 4): one Postman request per operation of the module's OpenAPI spec, checking that the
status code is one the spec lists and that the body matches the spec's schema for it. Built by code, no agent, no test data:
whatever the API answers must be in the spec. The collection is rebuilt from the spec (never edited by hand) and remembers
the spec's SHA-256, so a changed spec marks it stale. Called by automate.py (scaffold, the gate) and scripts/contract.sh.
Formats: docs/FORMATS.md (automation)."""
import sys, os, re, json, hashlib, time
from urllib.parse import quote
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ingest

MARK = "TESTHIVE:CONTRACT"
METHODS = ("get", "post", "put", "patch", "delete")
PATH = re.compile(r"/[A-Za-z0-9._~!$&'()*+,;=:@%/{}-]*")  # a spec path; anything else could point the request (and its token) at another host
FORMATS = {"date", "time", "date-time", "uri", "email", "hostname", "ipv4", "ipv6", "uuid"}  # the ones Postman's schema check knows
KEYS = ("type", "required", "enum", "minimum", "maximum", "minLength", "maxLength", "pattern", "minItems", "maxItems", "uniqueItems", "multipleOf")


def path(module): return os.path.join("api", "collections", f"{module}.contract.postman_collection.json")
def bugs_path(module): return os.path.join("api", "collections", f"{module}.contract-bugs.txt")


def sha(p):
    with open(p, "rb") as f: return hashlib.sha256(f.read()).hexdigest()


def specs(module):
    """{file: spec} of the OpenAPI files among the module's sources (the same folder ingest reads)."""
    out = {}
    for p in ingest.source_files(ingest.source_dir(module)):
        if os.path.splitext(p)[1].lower() not in (".json", ".yaml", ".yml"): continue
        try: s = ingest.load_structured(p)
        except Exception: continue  # not readable: ingest reports it
        if isinstance(s, dict) and ("openapi" in s or "swagger" in s): out[p.replace(os.sep, "/")] = s
    return out


def schema(spec, s, depth=0):
    """An OpenAPI schema as plain JSON Schema for Postman's check: $refs resolved, nullable as a "null" type, unknown keywords and formats dropped."""
    s = ingest.resolve(spec, s)
    if not isinstance(s, dict) or depth > 20: return {}  # shortcut: a deeper (or recursive) schema is not checked below 20 levels
    out = {k: s[k] for k in KEYS if k in s}
    for k, bound in (("exclusiveMinimum", "minimum"), ("exclusiveMaximum", "maximum")):  # OpenAPI 3.0: true next to minimum; 3.1: a number
        v = s.get(k)
        if v is True and bound in out: out[k] = out.pop(bound)
        elif isinstance(v, (int, float)) and not isinstance(v, bool): out[k] = v
    if s.get("format") in FORMATS: out["format"] = s["format"]
    if "properties" in s: out["properties"] = {n: schema(spec, v, depth + 1) for n, v in s["properties"].items()}
    if "items" in s: out["items"] = schema(spec, s["items"], depth + 1)
    if isinstance(s.get("additionalProperties"), bool): out["additionalProperties"] = s["additionalProperties"]
    elif isinstance(s.get("additionalProperties"), dict): out["additionalProperties"] = schema(spec, s["additionalProperties"], depth + 1)
    for k in ("allOf", "anyOf", "oneOf"):
        if isinstance(s.get(k), list): out[k] = [schema(spec, x, depth + 1) for x in s[k]]
    if s.get("nullable") and "type" in out:
        out["type"] = (out["type"] if isinstance(out["type"], list) else [out["type"]]) + ["null"]
        if "enum" in out: out["enum"] = out["enum"] + [None]
    return out


def example(spec, s, depth=0):
    """A request value from the schema: its example, default or first enum value, else a made-up value of the right type and length."""
    s = ingest.resolve(spec, s)
    if not isinstance(s, dict) or depth > 8: return None
    for k in ("example", "default"):
        if k in s: return s[k]
    if s.get("enum"): return s["enum"][0]
    if s.get("allOf"):
        parts = [example(spec, x, depth + 1) for x in s["allOf"]]
        return {k: v for x in parts for k, v in x.items()} if all(isinstance(x, dict) for x in parts) else parts[0]
    if s.get("oneOf") or s.get("anyOf"): return example(spec, (s.get("oneOf") or s.get("anyOf"))[0], depth + 1)
    t = s.get("type", "object" if "properties" in s else "string")
    t = next((x for x in t if x != "null"), "string") if isinstance(t, list) else t
    if t == "object": return {n: example(spec, v, depth + 1) for n, v in (s.get("properties") or {}).items()}
    if t == "array": return [example(spec, s.get("items", {}), depth + 1)]
    if t in ("integer", "number"): return s.get("minimum", 1)
    if t == "boolean": return True
    v = {"date": "2000-01-15", "date-time": "2000-01-15T10:00:00Z", "email": "test@example.com", "uuid": "00000000-0000-4000-8000-000000000000",
         "uri": "https://example.com"}.get(s.get("format"), "test")
    return (v * (s.get("minLength", 0) // len(v) + 1))[:max(s.get("minLength", 0), len(v))][:s.get("maxLength", 10 ** 6)]


def json_body(spec, obj):
    """The application/json schema of a request body or response, or None."""
    content = (ingest.resolve(spec, obj or {}).get("content") or {})
    m = content.get("application/json") or next((v for k, v in content.items() if k.endswith("+json")), None)
    return (m or {}).get("schema")


def operations(spec):
    """(method, path, operation, parameters) of every operation, path-level parameters included; paths that are not plain paths are skipped."""
    for p, ops in (spec.get("paths") or {}).items():
        if not isinstance(p, str) or not PATH.fullmatch(p) or "//" in p or ".." in p or "{{" in p: continue
        ops = ingest.resolve(spec, ops) or {}
        for m in METHODS:
            if m in ops:
                prm = {(x.get("name"), x.get("in")): x for x in (ingest.resolve(spec, y) for y in ops.get("parameters", []) + ops[m].get("parameters", []))}
                yield m.upper(), p, ops[m], list(prm.values())


def bearer(spec, op):
    """Does the operation take an HTTP bearer token (then the request sends {{TEST_API_TOKEN}})?"""
    sec = op.get("security", spec.get("security")) or []
    schemes = (spec.get("components") or {}).get("securitySchemes") or (spec.get("securityDefinitions") or {})
    return any((ingest.resolve(spec, schemes.get(n)) or {}).get("scheme", "").lower() == "bearer" for req in sec for n in req)


def item(spec, method, p, op, params):
    def val(x): return quote(str(x.get("example", example(spec, x.get("schema", {"type": x.get("type", "string")})))), safe="")  # also keeps {{...}} out of the URL
    url = re.sub(r"\{([^}]+)\}", lambda m: next((val(x) for x in params if x.get("in") == "path" and x.get("name") == m[1]), "1"), p)
    q = [f"{quote(str(x['name']), safe='')}={val(x)}" for x in params if x.get("in") == "query" and x.get("required")]
    req = {"method": method, "url": "{{API_BASE_URL}}" + url + ("?" + "&".join(q) if q else ""), "header": [],
           "description": f"{MARK}: built from the spec by scripts/contract.sh; do not edit (it is rebuilt when the spec changes)."}
    body = json_body(spec, op.get("requestBody"))
    if body is not None:
        req["header"].append({"key": "Content-Type", "value": "application/json"})
        raw = json.dumps(example(spec, body), ensure_ascii=False).replace("{{", "{\\u007b")  # still the same JSON, but no {{variable}} for Postman to fill in
        req["body"] = {"mode": "raw", "raw": raw, "options": {"raw": {"language": "json"}}}
    if bearer(spec, op): req["header"].append({"key": "Authorization", "value": "Bearer {{TEST_API_TOKEN}}"})
    resp = {str(c): json_body(spec, r) for c, r in (op.get("responses") or {}).items()}
    checks = {c: schema(spec, s) for c, s in resp.items() if s is not None}
    return {"name": f"{method} {p}", "request": req, "event": [{"listen": "test", "script": {"type": "text/javascript", "exec": [
        f"// {MARK}: the answer must be one the spec lists, with the body the spec gives for it",
        f"const documented = {json.dumps(sorted(resp))}, schemas = {json.dumps(checks, ensure_ascii=False)};",
        "const code = String(pm.response.code), key = [code, code[0] + 'XX', 'default'].find(k => documented.includes(k));",
        "pm.test('the status is in the spec', () => pm.expect(key, `status ${code} is not in the spec (it lists ${documented.join(', ')})`).to.not.be.undefined);",
        "if (key && schemas[key]) pm.test('the body matches the spec', () => pm.response.to.have.jsonSchema(schemas[key]));"]}}]}


def build(module):
    """The contract collection of the module, or None when it has no OpenAPI spec."""
    sp = specs(module)
    if not sp: return None
    items = [item(s, *op) for f, s in sorted(sp.items()) for op in operations(s)]
    return {"info": {"name": f"{module} contract", "description": f"{MARK}: built from {', '.join(sorted(sp))} by scripts/contract.sh; do not edit.",
                     "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"},
            "item": items, "testhive": {"specs": {f: sha(f) for f in sp}, "built_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}}


def state(module):
    """None (no spec) or {state: missing | stale | current, operations, specs, built_at}."""
    sp = specs(module)
    if not sp: return None
    try:
        with open(path(module), encoding="utf-8") as f: col = json.load(f)
    except (OSError, ValueError): return {"state": "missing", "operations": 0, "specs": sorted(sp), "built_at": ""}
    t = col.get("testhive") or {}
    fresh = t.get("specs") == {f: sha(f) for f in sp}
    return {"state": "current" if fresh else "stale", "operations": len(col.get("item", [])), "specs": sorted(sp), "built_at": t.get("built_at", "")}


def known_bugs(module):
    """{"POST /v1/x": "BUG-12"} from api/collections/<M>.contract-bugs.txt (one "<METHOD> <path> <BUG-ID>" per line, # for notes)."""
    out = {}
    try:
        with open(bugs_path(module), encoding="utf-8") as f:
            for ln in f:
                m = re.match(r"\s*([A-Z]+ \S+)\s+(BUG-[A-Z0-9-]+)", ln)
                if m: out[m[1]] = m[2]
    except OSError: pass
    return out
