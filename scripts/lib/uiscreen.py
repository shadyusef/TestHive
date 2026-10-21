"""Reads an Android UI dump (uiautomator XML) into a short screen summary, and finds elements to tap.
Called by scripts/explore-android.sh."""
import sys, re, json
import xml.etree.ElementTree as ET

sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def nodes(xml_path):
    out = []
    for n in ET.parse(xml_path).getroot().iter("node"):
        a = n.attrib
        m = re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", a.get("bounds", ""))
        if not m: continue
        x1, y1, x2, y2 = map(int, m.groups())
        out.append({"text": a.get("text", ""), "desc": a.get("content-desc", ""), "id": a.get("resource-id", "").split("/")[-1],
                    "class": a.get("class", "").split(".")[-1], "clickable": a.get("clickable") == "true",
                    "editable": a.get("class", "").endswith("EditText"), "password": a.get("password") == "true",
                    "checkable": a.get("checkable") == "true", "checked": a.get("checked") == "true",
                    "enabled": a.get("enabled") == "true", "hint": a.get("hint", ""), "center": [(x1 + x2) // 2, (y1 + y2) // 2]})
    return out


def summary(xml_path, title):
    ns = nodes(xml_path)
    lines = [f"## Screen: {title}", "| Element | id | Kind | Text / hint | State |", "|---|---|---|---|---|"]
    for n in ns:
        label = n["text"] or n["desc"] or n["hint"]
        if not (label or n["editable"] or (n["clickable"] and n["id"])): continue
        kind = "input (password)" if n["password"] else "input" if n["editable"] else "checkbox" if n["checkable"] else "button/link" if n["clickable"] else "text"
        state = ", ".join(s for s, on in (("disabled", not n["enabled"]), ("checked", n["checked"])) if on)
        lines.append(f"| {n['class']} | {n['id']} | {kind} | {label} | {state} |")
    return "\n".join(lines)


def find(xml_path, target):
    """Element whose id, text or content-desc equals target (then: contains it). Prints 'x y'."""
    ns = nodes(xml_path)
    for exact in (True, False):
        for n in ns:
            for v in (n["id"], n["text"], n["desc"]):
                if v and ((v == target) if exact else (target.lower() in v.lower())):
                    print(*n["center"]); return
    print(f"NOT FOUND: {target}", file=sys.stderr); sys.exit(1)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "summary" and len(sys.argv) == 4: print(summary(sys.argv[2], sys.argv[3]))
    elif cmd == "find" and len(sys.argv) == 4: find(sys.argv[2], sys.argv[3])
    elif cmd == "json" and len(sys.argv) == 3: print(json.dumps(nodes(sys.argv[2]), indent=2, ensure_ascii=False))
    else: print("Usage: uiscreen.py summary <dump.xml> <title> | find <dump.xml> <id|text> | json <dump.xml>"); sys.exit(1)
