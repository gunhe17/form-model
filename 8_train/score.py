"""README 채점 3축 — 검출기 트랙. Ultralytics val 표준 출력에 없는 축을 직접 센다.

  놓침   recall@IoU0.5           ≥ 98%
  좌표   매칭 박스 중 IoU≥0.5 비율  ≥ 95%
  종류   매칭 박스의 클래스 정확도   ≥ 97%  (+ 11×11 confusion, background 행/열 포함)

매칭은 **클래스 무관**(IoU만)으로 Hungarian 최적할당한다. 위치는 맞았는데 종류만 틀린 박스를
'놓침'으로 잘못 집계하지 않기 위해서다 — 세 축이 서로 오염되지 않는다.

사용: python 8_train/score.py --model 8_train/runs/ffdnet_1600/weights/best.pt \
        --images 8_train/yolo/images/val --labels 8_train/yolo/labels/val --name val
자가검증: python 8_train/score.py --selftest
"""
import argparse, glob, json, os
import numpy as np
from scipy.optimize import linear_sum_assignment

TYPES = ["text","number","date","time","phone","email","radio","checkbox","signature","textarea","image"]
BG = len(TYPES)   # confusion 의 background 인덱스

def gt_boxes(txt, W, H):
    """정규화 cxcywh → 픽셀 xyxy. 음성 페이지는 빈 배열."""
    if not os.path.exists(txt): return np.zeros((0,4)), np.zeros(0, int)
    rows = [l.split() for l in open(txt).read().strip().splitlines() if l.strip()]
    if not rows: return np.zeros((0,4)), np.zeros(0, int)
    a = np.array(rows, float)
    c, cx, cy, w, h = a[:,0].astype(int), a[:,1]*W, a[:,2]*H, a[:,3]*W, a[:,4]*H
    return np.stack([cx-w/2, cy-h/2, cx+w/2, cy+h/2], 1), c

def iou_matrix(g, p):
    if len(g) == 0 or len(p) == 0: return np.zeros((len(g), len(p)))
    x1 = np.maximum(g[:,None,0], p[None,:,0]); y1 = np.maximum(g[:,None,1], p[None,:,1])
    x2 = np.minimum(g[:,None,2], p[None,:,2]); y2 = np.minimum(g[:,None,3], p[None,:,3])
    inter = np.clip(x2-x1, 0, None) * np.clip(y2-y1, 0, None)
    ag = ((g[:,2]-g[:,0]) * (g[:,3]-g[:,1]))[:,None]
    ap = ((p[:,2]-p[:,0]) * (p[:,3]-p[:,1]))[None,:]
    return inter / np.clip(ag + ap - inter, 1e-9, None)

class Tally:
    """페이지별 (GT, 예측) 쌍을 누적. predict 와 분리해 두어 GPU 없이 자가검증 가능."""
    def __init__(self, match_iou):
        self.match_iou = match_iou
        self.conf = np.zeros((BG+1, BG+1), int)      # 행 GT · 열 예측 · 마지막이 background
        self.n_gt = self.n_pred = self.n_match = self.n_iou50 = self.n_cls_ok = self.n_iou50_cls_ok = 0
        self.per = {t: dict(gt=0, hit=0, m=0, cls_ok=0) for t in TYPES}
        self.pages = []

    def add(self, stem, g, gc, p, pc):
        self.n_gt += len(g); self.n_pred += len(p)
        for c in gc: self.per[TYPES[c]]["gt"] += 1
        M = iou_matrix(g, p)
        gi, pi = linear_sum_assignment(-M) if M.size else (np.zeros(0,int), np.zeros(0,int))
        keep = M[gi, pi] >= self.match_iou if len(gi) else np.zeros(0, bool)
        gi, pi = gi[keep], pi[keep]
        pg_iou50 = 0
        for i, j in zip(gi, pi):
            v = M[i, j]; ok = gc[i] == pc[j]; t = TYPES[gc[i]]
            self.n_match += 1; self.conf[gc[i], pc[j]] += 1; self.per[t]["m"] += 1
            if v >= 0.5:
                self.n_iou50 += 1; pg_iou50 += 1; self.per[t]["hit"] += 1
                if ok: self.n_iou50_cls_ok += 1
            if ok: self.n_cls_ok += 1; self.per[t]["cls_ok"] += 1
        for i in set(range(len(g))) - set(gi.tolist()): self.conf[gc[i], BG] += 1     # 놓침
        for j in set(range(len(p))) - set(pi.tolist()): self.conf[BG, pc[j]] += 1     # 유령
        self.pages.append(dict(page=stem, gt=len(g), pred=len(p), matched=int(keep.sum()), iou50=pg_iou50))

    def summary(self):
        pct = lambda x, y: 100.0 * x / y if y else float("nan")
        return dict(gt=self.n_gt, pred=self.n_pred, matched=self.n_match,
                    recall_iou50=pct(self.n_iou50, self.n_gt), recall_iou50_cls=pct(self.n_iou50_cls_ok, self.n_gt),
                    coord_pass=pct(self.n_iou50, self.n_match), class_acc=pct(self.n_cls_ok, self.n_match),
                    misses=self.n_gt-self.n_match, ghosts=self.n_pred-self.n_match)

def report(T, name, n_imgs, conf_thr, out, model):
    pct = lambda x, y: 100.0 * x / y if y else float("nan")
    S = dict(split=name, model=model, images=n_imgs, conf=conf_thr, match_iou=T.match_iou, **T.summary())
    print(f"\n=== {name} · {n_imgs}장 · GT {S['gt']} · 예측 {S['pred']} (conf={conf_thr}) ===")
    print(f"놓침  recall@IoU0.5      {S['recall_iou50']:6.2f}%   (기준 98%)  {'OK' if S['recall_iou50']>=98 else 'MISS'}")
    print(f"좌표  매칭 중 IoU≥0.5    {S['coord_pass']:6.2f}%   (기준 95%)  {'OK' if S['coord_pass']>=95 else 'MISS'}")
    print(f"종류  매칭 클래스 정확도  {S['class_acc']:6.2f}%   (기준 97%)  {'OK' if S['class_acc']>=97 else 'MISS'}")
    print(f"      놓친 GT {S['misses']} · 유령 예측 {S['ghosts']} · 클래스까지 맞은 recall {S['recall_iou50_cls']:.2f}%")
    print(f"\n--- 클래스별 (recall = IoU≥0.5 매칭 / GT, 종류정확도 = 클래스 일치 / 매칭) ---")
    print(f"{'class':10s} {'GT':>7s} {'recall%':>8s} {'종류정확도%':>11s}")
    for t in TYPES:
        d = T.per[t]; print(f"{t:10s} {d['gt']:7d} {pct(d['hit'],d['gt']):8.2f} {pct(d['cls_ok'],d['m']):11.2f}")
    print(f"\n--- confusion (행 GT · 열 예측 · bg = 놓침/유령) ---")
    hdr = [t[:6] for t in TYPES] + ["bg"]
    print(f"{'':10s}" + "".join(f"{h:>7s}" for h in hdr))
    for i, t in enumerate(TYPES + ["bg(유령)"]):
        print(f"{t:10s}" + "".join(f"{T.conf[i,j]:7d}" for j in range(BG+1)))
    os.makedirs(out, exist_ok=True)
    json.dump(dict(summary=S, per_class=T.per, confusion=T.conf.tolist(), pages=T.pages),
              open(f"{out}/{name}.json","w"), ensure_ascii=False, indent=1)
    print(f"\n→ {out}/{name}.json")

def selftest():
    """GT 4개(완벽1 / IoU0.33 좌표실패1 / IoU0.9 클래스오답1 / 예측없음1) + 유령 1개."""
    g = np.array([[0,0,10,10],[20,0,30,10],[40,0,50,10],[60,0,70,10]], float); gc = np.array([0,1,2,3])
    p = np.array([[0,0,10,10],[15,0,25,10],[40,0,49,10],[80,0,90,10]], float); pc = np.array([0,1,5,0])
    assert np.allclose(iou_matrix(g[:1], p[:3])[0], [1.0, 0.0, 0.0])
    T = Tally(0.10); T.add("t", g, gc, p, pc); S = T.summary()
    assert (S["matched"], T.n_iou50, T.n_cls_ok) == (3, 2, 2), S
    assert abs(S["recall_iou50"]-50) < 1e-9 and abs(S["coord_pass"]-200/3) < 1e-9 and abs(S["class_acc"]-200/3) < 1e-9
    assert S["misses"] == 1 and S["ghosts"] == 1 and T.conf[2,5] == 1 and T.conf[3,BG] == 1 and T.conf[BG,0] == 1
    print("selftest OK")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--model"); ap.add_argument("--images"); ap.add_argument("--labels")
    ap.add_argument("--name", default="split")
    ap.add_argument("--imgsz", type=int, default=1600); ap.add_argument("--conf", type=float, default=0.25)
    ap.add_argument("--nms-iou", type=float, default=0.7); ap.add_argument("--device", default="0")
    ap.add_argument("--match-iou", type=float, default=0.10, help="이 값 미만은 매칭으로 치지 않는다(유령/놓침)")
    ap.add_argument("--out", default="8_train/runs/score"); ap.add_argument("--chunk", type=int, default=16)
    a = ap.parse_args()
    if a.selftest: return selftest()
    assert a.model and a.images and a.labels, "--model --images --labels 필요"

    from ultralytics import YOLO
    model = YOLO(a.model)
    imgs = sorted(glob.glob(f"{a.images}/*.png"))
    assert imgs, f"이미지 없음: {a.images}"
    T = Tally(a.match_iou)
    for k in range(0, len(imgs), a.chunk):   # ponytail: 리스트 통째로 넘기면 GPU 메모리가 쌓여 24GB 에서 OOM
        for r in model.predict(imgs[k:k+a.chunk], imgsz=a.imgsz, conf=a.conf, iou=a.nms_iou, device=a.device, stream=True, verbose=False):
            H, W = r.orig_shape; stem = os.path.basename(r.path)[:-4]
            g, gc = gt_boxes(f"{a.labels}/{stem}.txt", W, H)
            T.add(stem, g, gc, r.boxes.xyxy.cpu().numpy(), r.boxes.cls.cpu().numpy().astype(int))
        if a.device != "cpu":
            import torch; torch.cuda.empty_cache()
    report(T, a.name, len(imgs), a.conf, a.out, a.model)

if __name__ == "__main__":
    main()
