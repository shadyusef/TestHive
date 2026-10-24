"""Puts the recorded phase 4 engineer work into a demo project (used by demo/phase2d/fake-claude.py and demo/phase4/run.sh).
Usage: python apply.py web|api <project folder>
web: copies the page objects and the written smoke specs over their placeholders. api: replaces the placeholder requests of
api/collections/SIGNUP.postman_collection.json with the written ones, matched by case ID. Prints each file it writes."""
import sys, os, re, json, shutil

HERE = os.path.dirname(os.path.abspath(__file__))
kind, root = sys.argv[1], sys.argv[2]
if kind == "web":
    src = os.path.join(HERE, "web")
    for d, _, files in os.walk(src):
        for f in files:
            rel = os.path.relpath(os.path.join(d, f), src)
            dst = os.path.join(root, "web", rel); os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy(os.path.join(d, f), dst); print("web/" + rel.replace(os.sep, "/"))
else:
    col_path = os.path.join(root, "api", "collections", "SIGNUP.postman_collection.json")
    with open(col_path, encoding="utf-8") as f: col = json.load(f)
    with open(os.path.join(HERE, "api", "SIGNUP-smoke-items.json"), encoding="utf-8") as f: done = json.load(f)
    by_id = {re.match(r"\[(TC-[A-Z0-9-]+)\]", it["name"])[1]: it for it in done}
    col["item"] = [by_id.get((re.match(r"\[(TC-[A-Z0-9-]+)\]", it.get("name", "")) or [None, None])[1], it) for it in col["item"]]
    with open(col_path, "w", encoding="utf-8", newline="\n") as f: json.dump(col, f, indent=2, ensure_ascii=False); f.write("\n")
    print(f"api/collections/SIGNUP.postman_collection.json: {len(by_id)} requests written")
