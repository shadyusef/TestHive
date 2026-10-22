"""Plays the human reviewer in the phase 2 demo: fills the design workbook from a CSV, as a person would in Excel.
Usage: python review-workbook.py <SIGNUP-design.xlsx> <sample-review.csv>
CSV columns: Kind (case | new | request), ID, Review, Review Comment, Edit Column, Edit Value, Title, Steps,
Expected Result, Requirements, Tags, Request, Requested By."""
import sys, csv, openpyxl

wb = openpyxl.load_workbook(sys.argv[1])
cs, rq = wb["Cases"], wb["Requests"]
head = [c.value for c in cs[1]]
col = lambda h: head.index(h) + 1
row_of = {cs.cell(r, 1).value: r for r in range(2, cs.max_row + 1)}
rhead = [c.value for c in rq[1]]
with open(sys.argv[2], encoding="utf-8-sig", newline="") as f:
    for d in csv.DictReader(f):
        if d["Kind"] == "case":
            r = row_of[d["ID"]]
            if d["Review"]: cs.cell(r, col("Review")).value = d["Review"]
            if d["Review Comment"]: cs.cell(r, col("Review Comment")).value = d["Review Comment"]
            if d["Edit Column"]: cs.cell(r, col(d["Edit Column"])).value = d["Edit Value"]
        elif d["Kind"] == "new":
            r = cs.max_row + 1
            for h in ("Title", "Steps", "Expected Result", "Requirements", "Tags", "Review Comment"):
                if d[h]: cs.cell(r, col(h)).value = d[h]
        elif d["Kind"] == "request":
            r = rq.max_row + 1
            rq.cell(r, rhead.index("Request") + 1).value = d["Request"]
            rq.cell(r, rhead.index("Requested By") + 1).value = d["Requested By"]
wb.save(sys.argv[1])
print(f"(the reviewer filled {sys.argv[1].replace(chr(92), '/')} in Excel and saved it)")
