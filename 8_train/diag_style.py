"""HTML 스타일 클래스별 recall — 생성기 분포와 실서식 분포의 어긋남을 잰다.

검출 실패가 '못 본 구성'인지 '아는 구성인데 치수가 다른 것'인지 가른다. GT json 은
querySelectorAll('[data-f]') 순서로 만들어졌고 to_yolo.py 가 순서를 보존하므로,
라벨 i 번째 줄 = HTML 의 i 번째 [data-f] 요소다(길이 불일치 페이지는 건너뛰고 보고).

사용:
  python 8_train/diag_style.py --model best.pt --html-dir 4_replica/html \
      --images 8_train/yolo/images/replica --labels 8_train/yolo/labels/replica \
      --name replica --out 8_train/runs/score/style_replica.json
  python 8_train/diag_style.py --compare style_replica_1차.json style_replica_2차.json

메모리: 모델 1개 + --chunk 장씩만 상주. 학습과 같이 돌릴 땐 대상별로 프로세스를 분리할 것.
"""
import argparse, collections, glob, json, os, sys
import numpy as np
from html.parser import HTMLParser
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from score import gt_boxes, iou_matrix
from scipy.optimize import linear_sum_assignment

BUCKETS = ["gp(투명 빈칸)", "ul(밑줄)", "cg(셀 채움)", "마커(□/○)", "기타"]

def bucket(cl):
    # ponytail: replica·holdout 에서 관측된 class 이름 기준. 새 class 는 '기타'로 떨어지니 그때 갱신.
    if cl == "gp": return BUCKETS[0]
    if cl in ("ul", "ulx"): return BUCKETS[1]
    if cl in ("cg", "cgf"): return BUCKETS[2]
    if cl in ("mk", "mkc", "ck", "circ"): return BUCKETS[3]
    return BUCKETS[4]

class Fields(HTMLParser):
    """[data-f] 요소의 class 를 문서 순서대로."""
    def __init__(self): super().__init__(); self.out = []
    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        if "data-f" in d: self.out.append(d.get("class", "").strip())

def measure(a):
    from ultralytics import YOLO
    cls_of = {}
    for f in sorted(glob.glob(f"{a.html_dir}/*.html")):
        s = os.path.basename(f)[:-5]
        p = Fields(); p.feed(open(f, encoding="utf-8").read()); cls_of[s] = p.out
    imgs = [f"{a.images}/{s}.png" for s in sorted(cls_of) if os.path.exists(f"{a.images}/{s}.png")]
    assert imgs, f"이미지 없음: {a.images}"

    model = YOLO(a.model)
    raw = collections.defaultdict(lambda: dict(gt=0, hit=0, w=[], h=[]))
    skipped = []
    for k in range(0, len(imgs), a.chunk):
        for r in model.predict(imgs[k:k+a.chunk], imgsz=a.imgsz, conf=a.conf, iou=a.nms_iou,
                               device=a.device, stream=True, verbose=False):
            H, W = r.orig_shape; stem = os.path.basename(r.path)[:-4]
            g, _ = gt_boxes(f"{a.labels}/{stem}.txt", W, H); cl = cls_of.get(stem, [])
            if len(cl) != len(g): skipped.append(stem); continue
            p = r.boxes.xyxy.cpu().numpy()
            M = iou_matrix(g, p)
            gi, pi = linear_sum_assignment(-M) if M.size else (np.zeros(0, int), np.zeros(0, int))
            keep = M[gi, pi] >= a.match_iou if len(gi) else np.zeros(0, bool)
            gi, pi = gi[keep], pi[keep]
            hit = {int(i) for i, j in zip(gi, pi) if M[i, j] >= 0.5}
            for i in range(len(g)):
                d = raw[cl[i] or "(none)"]
                d["gt"] += 1; d["w"].append(float(g[i,2]-g[i,0])); d["h"].append(float(g[i,3]-g[i,1]))
                if i in hit: d["hit"] += 1
    med = lambda v: float(np.median(v)) if v else None
    return dict(name=a.name, model=a.model, pages=len(imgs), conf=a.conf, skipped=skipped,
                classes={k: dict(gt=v["gt"], hit=v["hit"], w=med(v["w"]), h=med(v["h"]))
                         for k, v in raw.items()})

def show(R):
    C = R["classes"]
    agg = collections.defaultdict(lambda: [0, 0])
    for k, v in C.items(): b = bucket(k); agg[b][0] += v["gt"]; agg[b][1] += v["hit"]
    print(f"\n=== {R['name']} · {R['pages']}장 · conf={R['conf']} · 정렬불일치 {len(R['skipped'])}장 ===")
    print(f"{'스타일':16s} {'GT':>6s} {'놓침':>6s} {'recall%':>8s}")
    t = [0, 0]
    for b in BUCKETS:
        gt, hit = agg[b]
        if gt: print(f"{b:16s} {gt:6d} {gt-hit:6d} {100*hit/gt:8.2f}")
        t[0] += gt; t[1] += hit
    print(f"{'합계':16s} {t[0]:6d} {t[0]-t[1]:6d} {100*t[1]/max(t[0],1):8.2f}")
    print(f"\n{'class':10s} {'GT':>6s} {'놓침':>6s} {'recall%':>8s} {'w중앙':>7s} {'h중앙':>7s}")
    for k in sorted(C, key=lambda k: -C[k]["gt"]):
        v = C[k]; r = 100*v["hit"]/v["gt"] if v["gt"] else float("nan")
        print(f"{k:10s} {v['gt']:6d} {v['gt']-v['hit']:6d} {r:8.2f} "
              f"{(v['w'] if v['w'] is not None else 0):7.1f} {(v['h'] if v['h'] is not None else 0):7.1f}")

def compare(pa, pb):
    A, B = (json.load(open(p)) for p in (pa, pb))
    ca, cb = A["classes"], B["classes"]
    rec = lambda v: 100*v["hit"]/v["gt"] if v and v["gt"] else None
    print(f"\n=== {A['name']} → {B['name']} ===")
    print(f"{'class':10s} {'A GT':>6s} {'A rec%':>8s} {'B GT':>6s} {'B rec%':>8s} {'Δrec':>7s} "
          f"{'A w×h':>13s} {'B w×h':>13s}")
    for k in sorted(set(ca) | set(cb), key=lambda k: -(ca.get(k, {}).get("gt", 0) + cb.get(k, {}).get("gt", 0))):
        a, b = ca.get(k), cb.get(k)
        ra, rb = rec(a), rec(b)
        d = f"{rb-ra:+7.2f}" if (ra is not None and rb is not None) else "      -"
        f = lambda v: f"{v['w']:.0f}×{v['h']:.0f}" if v and v["w"] is not None else "-"
        print(f"{k:10s} {(a or {}).get('gt',0):6d} {ra if ra is not None else float('nan'):8.2f} "
              f"{(b or {}).get('gt',0):6d} {rb if rb is not None else float('nan'):8.2f} {d} "
              f"{f(a):>13s} {f(b):>13s}")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--compare", nargs=2, metavar=("A.json", "B.json"))
    ap.add_argument("--model"); ap.add_argument("--html-dir"); ap.add_argument("--images"); ap.add_argument("--labels")
    ap.add_argument("--name", default="style"); ap.add_argument("--out")
    ap.add_argument("--imgsz", type=int, default=1600); ap.add_argument("--conf", type=float, default=0.25)
    ap.add_argument("--nms-iou", type=float, default=0.7); ap.add_argument("--device", default="cpu")
    ap.add_argument("--match-iou", type=float, default=0.10)
    ap.add_argument("--chunk", type=int, default=16, help="동시 상주 이미지 수 — 메모리 상한")
    a = ap.parse_args()
    if a.compare: return compare(*a.compare)
    for r in ("model", "html_dir", "images", "labels"):
        if not getattr(a, r): ap.error(f"--{r.replace('_','-')} 필요 (또는 --compare)")
    R = measure(a); show(R)
    if a.out:
        os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
        json.dump(R, open(a.out, "w"), ensure_ascii=False, indent=1); print(f"\n→ {a.out}")

if __name__ == "__main__":
    main()
