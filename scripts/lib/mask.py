"""TestHive masking. Called by scripts/mask.sh; see the usage there."""
import sys, os, re, json

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
MAP = os.environ.get("TH_MASK_MAP", ".mask-map.json")
TERMS = os.environ.get("TH_MASK_TERMS", ".mask-terms")
ALLOW = os.environ.get("TH_MASK_ALLOW", ".mask-allow")
TOKEN = re.compile(r"\[[A-Z]+_\d{3,}\]")
AR_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")


def digits(s): return re.sub(r"\D", "", s.translate(AR_DIGITS))


def luhn(s):
    d = [int(c) for c in digits(s)][::-1]
    return sum(x if i % 2 == 0 else (x * 2 - 9 if x > 4 else x * 2) for i, x in enumerate(d)) % 10 == 0


def iban_ok(s):
    s = re.sub(r"\s", "", s).upper()
    s = s[4:] + s[:4]
    try: return int("".join(str(int(c, 36)) for c in s)) % 97 == 1
    except ValueError: return False


# (kind, regex, validator). Python's \d also matches Arabic-Indic digits.
PATTERNS = [
    ("EMAIL", r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+", None),
    ("IBAN", r"\b[A-Z]{2}\d{2}(?: ?[A-Z0-9]{4}){4,7}(?: ?[A-Z0-9]{1,3})?\b", iban_ok),
    ("CARD", r"\b\d(?:[ -]?\d){12,18}\b", luhn),
    ("PHONE", r"(?:\+|\b00)\d(?:[ -]?\d){7,13}\b|\b[0٠][5٥]\d{8}\b", None),
    ("NATID", r"\b[12١٢]\d{9}\b", luhn),  # Saudi national ID / iqama: Luhn check digit
]
TITLES_EN = r"(?:Mr|Mrs|Ms|Miss|Dr|Eng|Prof|Customer|Client|User|Manager)\.?"
TITLES_AR = r"(?:السيد|السيدة|الأستاذ|الأستاذة|المهندس|المهندسة|الدكتور|الدكتورة|العميل|العميلة|المستخدم|المدير)"
STOP = {"The", "This", "That", "When", "If", "Module", "Section", "Page", "Screen", "Button", "Step", "Email", "Phone", "Note"}


def die(m): print(m); sys.exit(1)


def read_lines(path):
    if not os.path.exists(path): return []
    with open(path, encoding="utf-8-sig") as f: return [l.strip() for l in f if l.strip() and not l.startswith("#")]


def load_map():
    if os.path.exists(MAP):
        with open(MAP, encoding="utf-8") as f: return json.load(f)
    return {"forward": {}, "counters": {}}


def save_map(mp):
    with open(MAP + ".tmp", "w", encoding="utf-8", newline="\n") as f: json.dump(mp, f, indent=2, ensure_ascii=False)
    os.replace(MAP + ".tmp", MAP)


def allowed():
    exact, rx = set(), []
    for l in read_lines(ALLOW):
        if l.startswith("re:"): rx.append(re.compile(l[3:].strip()))
        else: exact.add(l)
    return lambda v: v in exact or any(r.fullmatch(v) for r in rx)


def find(text):
    """Every value to mask in text: list of (start, end, kind, value), no overlaps, terms first."""
    ok_allow, spans = allowed(), []
    def free(a, b): return all(b <= s or a >= e for s, e, _, _ in spans)
    for t in sorted(set(read_lines(TERMS)), key=len, reverse=True):
        for m in re.finditer(re.escape(t), text, re.IGNORECASE):
            if free(m.start(), m.end()): spans.append((m.start(), m.end(), "TERM", m.group(0)))
    for kind, rx, check in PATTERNS:
        for m in re.finditer(rx, text):
            v = m.group(0)
            if ok_allow(v) or (check and not check(v)) or not free(m.start(), m.end()) or TOKEN.fullmatch(v): continue
            spans.append((m.start(), m.end(), kind, v))
    return sorted(spans)


def summary(spans):
    c = {}
    for _, _, k, _ in spans: c[k] = c.get(k, 0) + 1
    return ", ".join(f"{k} {v}" for k, v in c.items()) or "nothing found"


def read(path):
    with open(path, encoding="utf-8-sig") as f: return f.read()


def write(path, s):
    with open(path, "w", encoding="utf-8", newline="") as f: f.write(s)


def mask_text(src, dst):
    text, mp = read(src), load_map()
    spans, out, last = find(text), [], 0
    for s, e, kind, v in spans:
        if v not in mp["forward"]:
            n = mp["counters"].get(kind, 0) + 1; mp["counters"][kind] = n
            mp["forward"][v] = f"[{kind}_{n:03d}]"
        out += [text[last:s], mp["forward"][v]]; last = e
    write(dst, "".join(out) + text[last:]); save_map(mp)
    print(f"Masked {len(spans)} values ({summary(spans)}) -> {dst}")


def unmask_text(src, dst):
    text, back = read(src), {v: k for k, v in load_map()["forward"].items()}
    unknown = sum(1 for t in TOKEN.findall(text) if t not in back)
    write(dst, TOKEN.sub(lambda m: back.get(m.group(0), m.group(0)), text))
    print(f"Unmasked -> {dst}" + (f" ({unknown} unknown tokens left as they are)" if unknown else ""))


def review(src):
    text = read(src)
    spans = find(text)
    for s, e, kind, v in spans:
        ctx = (text[max(0, s - 30):s] + "<<" + v + ">>" + text[e:e + 30]).replace("\n", " ")
        print(f"{kind:<6} {ctx}")
    print(f"--- {len(spans)} values would be masked ({summary(spans)}). Wrong ones: add them to {ALLOW}.")


def suggest(src):
    text, known = read(src), {t.lower() for t in read_lines(TERMS)}
    found = {}
    for m in re.finditer(rf"\b{TITLES_EN}\s+((?:[A-Z][\w'-]+\s?){{1,3}})", text):
        found.setdefault(m.group(1).strip(), "after a title")
    for m in re.finditer(rf"{TITLES_AR}\s+((?:[\u0600-\u06FF]+\s?){{1,3}})", text):
        found.setdefault(m.group(1).strip(), "after a title")
    for m in re.finditer(r"\b[A-Z][a-z]+(?:[ -](?:Al-|al-)?[A-Z][a-z]+)+\b", text):
        if m.group(0).split()[0] not in STOP: found.setdefault(m.group(0), "capitalised name")
    new = {k: v for k, v in found.items() if k.lower() not in known}
    for k, why in sorted(new.items()): print(f"  {k}    ({why})")
    print(f"--- {len(new)} possible names. Put the real ones in {TERMS}, one per line, then run mask again.")


def mask_image(src, dst, check_only=False):
    try:
        from PIL import Image, ImageDraw
        import pytesseract
    except ImportError: die("Image masking needs Pillow and pytesseract: run scripts/setup.sh --check")
    cmd = os.environ.get("TESSERACT_CMD") or next((p for p in (r"C:\Program Files\Tesseract-OCR\tesseract.exe",
          os.path.expandvars(r"%LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe")) if os.path.exists(p)), None)
    if cmd: pytesseract.pytesseract.tesseract_cmd = cmd
    user_data = os.path.expandvars(r"%LOCALAPPDATA%\TestHive\tessdata")  # where setup.ps1 -Ocr puts Arabic
    if "TESSDATA_PREFIX" not in os.environ and os.path.isdir(user_data): os.environ["TESSDATA_PREFIX"] = user_data
    img = Image.open(src).convert("RGB")
    langs = os.environ.get("TH_OCR_LANGS", "ara+eng")
    try: data = pytesseract.image_to_data(img, lang=langs, output_type=pytesseract.Output.DICT)
    except pytesseract.TesseractNotFoundError: die("Tesseract is not installed: run scripts/setup.sh --check")
    except pytesseract.TesseractError: data = pytesseract.image_to_data(img, lang="eng", output_type=pytesseract.Output.DICT)
    lines = {}
    for i, w in enumerate(data["text"]):
        if w.strip(): lines.setdefault((data["block_num"][i], data["par_num"][i], data["line_num"][i]), []).append(i)
    boxes, kinds = [], []
    for idx in lines.values():
        text, pos = "", []
        for i in idx:
            if text: text += " "
            pos.append((len(text), len(text) + len(data["text"][i]), i)); text += data["text"][i]
        for s, e, kind, _ in find(text):
            kinds.append((0, 0, kind, ""))
            for a, b, i in pos:
                if a < e and b > s: boxes.append(i)
    if check_only: print(f"Would black out: {summary(kinds)}"); return
    draw = ImageDraw.Draw(img)
    for i in set(boxes):
        x, y, w, h = data["left"][i], data["top"][i], data["width"][i], data["height"][i]
        draw.rectangle([x - 2, y - 2, x + w + 2, y + h + 2], fill="black")
    img.save(dst)
    print(f"Blacked out {len(set(boxes))} words ({summary(kinds)}) -> {dst}. Open it and check before sharing.")


IMG = (".png", ".jpg", ".jpeg", ".bmp", ".webp", ".tif", ".tiff")
a = sys.argv[1:]
need = {"mask": 3, "unmask": 3, "check": 2, "review": 2, "suggest": 2}
if not a or a[0] not in need or len(a) != need[a[0]]:
    die("Usage: mask.sh mask|unmask <in> <out>  |  mask.sh check|review|suggest <in>")
cmd, src = a[0], a[1]
if not os.path.isfile(src): die(f"File not found: {src}")
is_img = src.lower().endswith(IMG)
if cmd == "mask": mask_image(src, a[2]) if is_img else mask_text(src, a[2])
elif cmd == "check":
    if is_img: mask_image(src, None, check_only=True)
    else: print(f"Would mask: {summary(find(read(src)))}")
elif is_img: die(f"{cmd} works on text files only")
elif cmd == "unmask": unmask_text(src, a[2])
elif cmd == "review": review(src)
else: suggest(src)
