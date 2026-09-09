"""GT 단위 매칭 덤프(miss_dump_*.json) → 놓침 귀속 보고.

덤프 형식: {"meta":{"names":[...]}, "gt":[{page,i,cls,x,y,w,h,hit,iou,pred_cls,conf}], "ghosts":[{page,cls,x,y,w,h,conf}]}
GT 순서는 yolo_s1/labels 줄 순서 = to_yolo --stage1 규칙으로 걸러진 [data-f] 순서. 여기서 같은 규칙으로
복제본 마크업(텍스트·class·표 안·td 인쇄글자)을 붙여 놓친 칸을 원인별로 센다.

사용: python 8_train/diag_dump.py 8_train/runs/score/miss_dump_s1_e1.json [--prev miss_dump_s1_e3.json] \
        --html-dir 4_replica/html --gt-dir 4_replica/render
"""
import argparse, collections, json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from label_stage1 import fields_from_html, classify_page, CLASSES

TD_TEXT = re.compile(r'<td[^>]*>((?:[^<]|<br>)*?)<span data-f="(\w+)" class="(cgf|cg)"')

def aligned_fields(stem, html_dir, gt_dir, n_labels):
    """라벨 줄과 1:1 로 맞춘 (field, box, stage1 class) 리스트. 못 맞추면 None."""
    html = open(f"{html_dir}/{stem}.html", encoding="utf-8").read()
    boxes = json.load(open(f"{gt_dir}/{stem}_gt.json", encoding="utf-8"))
    fields = fields_from_html(html)
    if len(fields) != len(boxes): return None
    cls = classify_page(fields, boxes)
    keep = [i for i, b in enumerate(boxes) if b["w"] > 0 and b["h"] > 0]
    if len(keep) != n_labels:
        keep = [i for i in keep if cls[i] in CLASSES]
    if len(keep) != n_labels: return None
    # td 인쇄글자 + 셀박스 (척도 선택칸) 표식: 문서 순서로 cgf/cg 를 훑어 대응
    td_text = []
    for m in TD_TEXT.finditer(html):
        t = re.sub(r"<br>|&nbsp;|\s", "", m.group(1)); td_text.append(bool(t))
    cg_idx = [i for i, f in enumerate(fields) if set(f["cls"].split()) & {"cgf", "cg"} and f["intable"]]
    has_td_text = {}
    if len(cg_idx) == len(td_text):
        has_td_text = dict(zip(cg_idx, td_text))
    return [(fields[i], boxes[i], cls[i], has_td_text.get(i, False)) for i in keep]

def cause(f, b, c, tdtext):
    w, h = b["w"], b["h"]; t = f["text"]
    if c == "cell" and tdtext: return "A 셀: td 인쇄글자 위 선택칸(척도)"
    if c == "gap" and w <= 20: return "B1 gap: 폭 ≤20 밀착 슬롯"
    if c == "gap" and h <= 18: return "B2 gap: 높이 ≤18 낮은 줄"
    if c == "gap" and 40 < w <= 60: return "B3 gap: 폭 40~60"
    if c == "placeholder" and (len(t) == 1 or h < 20): return "C 자리표: 낱글자 ○ / 높이 <20"
    if c == "signature" and h <= 16: return "D 서명: 높이 ≤16 소형 (인)"
    if c == "cell" and h > 100: return "E1 셀: 세로로 긴 (h>100)"
    if c == "cell" and 60 < w <= 90: return "E2 셀: 폭 60~90"
    if c == "cell" and w <= 30: return "E3 셀: 폭 ≤30 (실서식 낱칸형)"
    return f"F 기타 {c}"

def iou(a, b):
    x1, y1 = max(a["x"], b["x"]), max(a["y"], b["y"])
    x2, y2 = min(a["x"]+a["w"], b["x"]+b["w"]), min(a["y"]+a["h"], b["y"]+b["h"])
    I = max(0, x2-x1) * max(0, y2-y1)
    return I / (a["w"]*a["h"] + b["w"]*b["h"] - I + 1e-9), I

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dump"); ap.add_argument("--prev", help="비교 덤프(같은 라벨)")
    ap.add_argument("--html-dir", default="4_replica/html"); ap.add_argument("--gt-dir", default="4_replica/render")
    a = ap.parse_args()
    D = json.load(open(a.dump, encoding="utf-8")); G = D["gt"]; GH = D["ghosts"]
    by_page = collections.defaultdict(list)
    for g in G: by_page[g["page"]].append(g)
    ghosts_by_page = collections.defaultdict(list)
    for g in GH: ghosts_by_page[g["page"]].append(g)

    ann = {}   # (page,i) -> (field, box, cls, tdtext)
    bad = []
    for p, gs in by_page.items():
        al = aligned_fields(p, a.html_dir, a.gt_dir, len(gs))
        if al is None: bad.append(p); continue
        for g, x in zip(sorted(gs, key=lambda g: g["i"]), al): ann[(p, g["i"])] = x
    n, hit = len(G), sum(g["hit"] for g in G)
    print(f"=== {os.path.basename(a.dump)} · GT {n} · hit {hit} ({100*hit/n:.2f}%) · miss {n-hit} · ghosts {len(GH)} · 정렬실패 {bad}")

    # 1. 클래스별
    C = collections.defaultdict(lambda: [0, 0])
    for g in G: C[g["cls"]][0] += 1; C[g["cls"]][1] += g["hit"]
    print("\n[클래스별] cls gt hit miss recall")
    for k, (t, h) in sorted(C.items(), key=lambda kv: -kv[1][0]): print(f"  {k:12s} {t:4d} {h:4d} {t-h:4d} {100*h/t:6.1f}")

    # 2. 놓침 원인 귀속 + 유령과의 관계
    causes = collections.Counter(); cause_pages = collections.defaultdict(collections.Counter)
    anat = collections.Counter(); cause_anat = collections.defaultdict(collections.Counter)
    for g in G:
        if g["hit"]: continue
        f, b, c, td = ann.get((g["page"], g["i"]), (None, None, g["cls"], False))
        k = cause(f, g, c, td) if f else f"F 기타 {c}"
        causes[k] += 1; cause_pages[k][g["page"][:14]] += 1
        best, kind = 0, "겹침없음"
        for gh in ghosts_by_page[g["page"]]:
            v, I = iou(g, gh)
            if I <= 0: continue
            best = max(best, v)
            if I / (gh["w"]*gh["h"]) > 0.8: kind = "유령이 GT 안(작은 박스)"
            elif I / (g["w"]*g["h"]) > 0.8: kind = "유령이 GT 삼킴"
            elif kind == "겹침없음": kind = "부분겹침"
        if g["iou"] > 0: kind = f"매칭됐으나 IoU<0.5 ({g['iou']:.2f})"[:24]
        anat[kind] += 1; cause_anat[k][kind.split(" (")[0]] += 1
    print(f"\n[놓침 원인 귀속] {n-hit}")
    for k, v in causes.most_common():
        pages = ", ".join(f"{p}×{c}" for p, c in cause_pages[k].most_common(3))
        print(f"  {v:4d}  {k:34s} {dict(cause_anat[k])}  ← {pages}")
    print("\n[놓침 해부 전체]", dict(anat.most_common()))

    # 3. 유령
    gc = collections.Counter(g["cls"] for g in GH); gsize = collections.Counter()
    for g in GH:
        gsize["≤30×30" if g["w"] <= 30 and g["h"] <= 30 else ("w>300" if g["w"] > 300 else "중간")] += 1
    ghost_pages = collections.Counter(g["page"][:14] for g in GH)
    print(f"\n[유령 {len(GH)}] 클래스 {dict(gc)} · 크기 {dict(gsize)} · 페이지 상위 {ghost_pages.most_common(5)}")
    conf_bins = collections.Counter(("<0.10" if g["conf"] < .1 else "<0.25" if g["conf"] < .25 else "≥0.25") for g in GH)
    print(f"  유령 conf 분포 {dict(conf_bins)} · hit conf<0.25 인 GT {sum(1 for g in G if g['hit'] and g['conf'] is not None and g['conf']<0.25)}")

    # 4. 페이지별
    print("\n[페이지별 recall, 나쁜 순]")
    rows = []
    for p, gs in by_page.items():
        t, h = len(gs), sum(g["hit"] for g in gs)
        rows.append((100*h/t, p, t, h, len(ghosts_by_page[p])))
    for r, p, t, h, gh in sorted(rows)[:14]: print(f"  {r:5.1f}  {p[:28]:28s} gt {t:3d} miss {t-h:3d} ghost {gh:3d}")

    # 5. 비교
    if a.prev:
        P = json.load(open(a.prev, encoding="utf-8"))
        prev = {(g["page"], g["i"]): g for g in P["gt"]}
        flip = collections.Counter()
        for g in G:
            q = prev.get((g["page"], g["i"]))
            if q is None: continue
            if g["hit"] != q["hit"]:
                f, b, c, td = ann.get((g["page"], g["i"]), (None, None, g["cls"], False))
                flip[("이번만 hit" if g["hit"] else "이전만 hit", cause(f, g, c, td) if f else c)] += 1
        print(f"\n[대비 {os.path.basename(a.prev)}] hit {sum(g['hit'] for g in P['gt'])} → {hit}")
        for k, v in flip.most_common(): print(f"  {v:4d}  {k[0]}  {k[1]}")

if __name__ == "__main__":
    main()
