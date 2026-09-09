"""놓침·유령 해부 — 실물 격차의 원인이 미검출인지 라벨 규약 불일치인지 가른다.

score.py 와 같은 매칭(클래스 무관 Hungarian, --match-iou)을 쓰고, 그 결과 매칭되지 않은
GT(놓침)와 예측(유령)만 따로 분해한다.

놓침 분류: 겹치는 예측이 아예 없으면 '진짜 미검출'. 있으면 규약 불일치를 의심한다 —
  쪼개짐  GT 하나 안에 예측이 2개 이상 (예측 면적의 절반 넘게 GT 안)
  삼킴    예측 하나가 GT 를 80% 이상 덮음 (표 셀 통째로 잡는 경우)
  부분    그 외 부분 겹침

사용: python 8_train/diag_replica.py --model <best.pt> --images ... --labels ... --device cpu
"""
import argparse, glob, os, sys, collections
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from score import TYPES, gt_boxes, iou_matrix
from scipy.optimize import linear_sum_assignment

def bucket(w, h):
    if max(w, h) < 30: return "작음<30px"
    if w > 300: return "넓음 w>300"
    return "중간"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True); ap.add_argument("--images", required=True)
    ap.add_argument("--labels", required=True); ap.add_argument("--imgsz", type=int, default=1600)
    ap.add_argument("--conf", type=float, default=0.25); ap.add_argument("--nms-iou", type=float, default=0.7)
    ap.add_argument("--device", default="cpu"); ap.add_argument("--match-iou", type=float, default=0.10)
    a = ap.parse_args()

    from ultralytics import YOLO
    model = YOLO(a.model)
    global TYPES; TYPES = [model.names[i] for i in range(len(model.names))]
    imgs = sorted(glob.glob(f"{a.images}/*.png"))

    miss_cls = collections.Counter(); miss_size = collections.Counter(); miss_kind = collections.Counter()
    miss_cross = collections.Counter()          # (원인, 클래스)
    ghost_kind = collections.Counter(); ghost_cls = collections.Counter()
    n_gt = n_pred = n_match = 0

    for r in model.predict(imgs, imgsz=a.imgsz, conf=a.conf, iou=a.nms_iou,
                           device=a.device, stream=True, verbose=False):
        H, W = r.orig_shape
        stem = os.path.basename(r.path)[:-4]
        g, gc = gt_boxes(f"{a.labels}/{stem}.txt", W, H)
        p = r.boxes.xyxy.cpu().numpy(); pc = r.boxes.cls.cpu().numpy().astype(int)
        n_gt += len(g); n_pred += len(p)

        M = iou_matrix(g, p)
        gi, pi = linear_sum_assignment(-M) if M.size else (np.zeros(0,int), np.zeros(0,int))
        keep = M[gi, pi] >= a.match_iou if len(gi) else np.zeros(0, bool)
        gi, pi = gi[keep], pi[keep]; n_match += len(gi)

        # --- 교차 면적 (GT × 예측) ---
        if len(g) and len(p):
            x1 = np.maximum(g[:,None,0], p[None,:,0]); y1 = np.maximum(g[:,None,1], p[None,:,1])
            x2 = np.minimum(g[:,None,2], p[None,:,2]); y2 = np.minimum(g[:,None,3], p[None,:,3])
            I = np.clip(x2-x1, 0, None) * np.clip(y2-y1, 0, None)
        else:
            I = np.zeros((len(g), len(p)))
        ga = np.clip((g[:,2]-g[:,0]) * (g[:,3]-g[:,1]), 1e-9, None) if len(g) else np.zeros(0)
        pa = np.clip((p[:,2]-p[:,0]) * (p[:,3]-p[:,1]), 1e-9, None) if len(p) else np.zeros(0)

        for i in set(range(len(g))) - set(gi.tolist()):          # 놓친 GT
            t = TYPES[gc[i]]; w, h = g[i,2]-g[i,0], g[i,3]-g[i,1]
            miss_cls[t] += 1; miss_size[bucket(w, h)] += 1
            ov = I[i] > 0
            if not ov.any(): kind = "겹침없음(진짜 미검출)"
            elif (I[i] / pa > 0.5).sum() >= 2: kind = "쪼개짐(예측 2개↑)"
            elif (I[i] / ga[i] > 0.8).any(): kind = "삼킴(예측이 GT 포함)"
            else: kind = "부분겹침"
            miss_kind[kind] += 1; miss_cross[(kind, t)] += 1

        for j in set(range(len(p))) - set(pi.tolist()):          # 유령 예측
            t = TYPES[pc[j]]; ghost_cls[t] += 1
            ov = I[:, j] > 0
            if not ov.any(): ghost_kind["순수 유령(GT 무접촉)"] += 1
            elif (I[:, j] / pa[j] > 0.8).any(): ghost_kind["GT 안에 들어감(중복 검출)"] += 1
            else: ghost_kind["GT 와 부분 겹침"] += 1

    n_miss = n_gt - n_match; n_ghost = n_pred - n_match
    print(f"=== conf={a.conf} · GT {n_gt} · 예측 {n_pred} · 매칭 {n_match} · 놓침 {n_miss} · 유령 {n_ghost} ===")
    print(f"\n[놓침 {n_miss} — 원인]")
    for k, v in miss_kind.most_common(): print(f"  {k:24s} {v:4d}  ({100*v/max(n_miss,1):5.1f}%)")
    print(f"\n[놓침 — 크기]")
    for k, v in miss_size.most_common(): print(f"  {k:14s} {v:4d}  ({100*v/max(n_miss,1):5.1f}%)")
    print(f"\n[놓침 — 클래스]")
    for k, v in miss_cls.most_common(): print(f"  {k:12s} {v:4d}")
    print(f"\n[유령 {n_ghost} — 원인]")
    for k, v in ghost_kind.most_common(): print(f"  {k:24s} {v:4d}  ({100*v/max(n_ghost,1):5.1f}%)")
    print(f"\n[유령 — 예측 클래스]")
    for k, v in ghost_cls.most_common(): print(f"  {k:12s} {v:4d}")
    print(f"\n[놓침 원인 × 클래스 상위]")
    for (k, t), v in miss_cross.most_common(10): print(f"  {k:24s} {t:12s} {v:4d}")

if __name__ == "__main__":
    main()
