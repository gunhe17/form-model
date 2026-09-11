"""분포 커버리지 — 합성 박스가 실서식 박스를 얼마나 덮는가(density/coverage + Vendi).

왜: recall 은 "못 찾았다"만 말하고 "무엇이 안 덮였나"는 말하지 않는다. GT 박스 크롭을 검출기
backbone 특징으로 임베딩해 실(real) 분포를 합성(fake) 분포가 덮는 비율을 재면, 생성기 폭을
어느 클래스부터 넓혀야 하는지가 수치로 나온다.

  coverage (Naeem 2002.09797, k=5) — 실 표본 중 자기 k-NN 반경 안에 합성 표본이 하나라도 있는 비율.
                                     이게 우리가 말하는 "덮음". 이상치에 강해 PR 보다 안정적.
  density  — 실 k-NN 구 안에 겹치는 합성 표본 수 / k. ≫1 이면 합성이 실의 좁은 영역에 과밀(모드 과밀).
  Vendi (Friedman & Dieng 2210.02410) — 코사인 커널 K/n 고유값의 섀넌 엔트로피 지수. "유효 종 수".
                                        참조 분포가 필요 없어 합성/실 각각의 절대 다양성을 비교할 수 있다.

임베딩: GT 박스를 잘라 96×96 로 리사이즈 → backbone(layer 0..10, SPPF·C2PSA 까지) → GAP.
       크롭 리사이즈 쪽이 feature map 샘플링보다 구현이 단순하고 박스 크기 편차에 둔감하다.
새 의존성 없음(numpy + torch/ultralytics + PIL). CPU 로 동작, 메모리는 표본 수 상한으로 조절.

사용:
  python 8_train/diag_coverage.py --model 8_train/runs/ffdnet_s1v3/weights/last_e1.pt \
      --real 8_train/yolo_s1v3/images/replica:8_train/yolo_s1v3/labels/replica \
      --fake 8_train/yolo_s1v3/images/train:8_train/yolo_s1v3/labels/train \
      --max-boxes 2000 --chunk 64
  python 8_train/diag_coverage.py --selftest
"""
import argparse, glob, os, sys
import numpy as np

K = 5
CROP = 96


# ── 지표 (numpy 만) ──────────────────────────────────────────────
def pdist(a, b, chunk=512):
    """유클리드 거리 행렬. chunk 로 나눠 메모리 상한을 잡는다."""
    out = np.empty((len(a), len(b)), np.float32)
    bb = (b * b).sum(1)
    for i in range(0, len(a), chunk):
        x = a[i:i + chunk]
        d = (x * x).sum(1)[:, None] + bb[None, :] - 2 * x @ b.T
        out[i:i + chunk] = np.sqrt(np.maximum(d, 0))
    return out


def prdc(real, fake, k=K):
    """density, coverage (Naeem 2020). real 의 k-NN 반경을 기준 구로 쓴다."""
    if len(real) <= k or len(fake) == 0:
        return float("nan"), float("nan")
    rr = pdist(real, real)
    np.fill_diagonal(rr, np.inf)
    radius = np.partition(rr, k - 1, axis=1)[:, k - 1]      # 자기 제외 k번째 최근접 거리
    rf = pdist(real, fake)                                   # (N_real, M_fake)
    inside = rf < radius[:, None]
    return float(inside.sum() / (k * len(fake))), float(inside.any(1).mean())


def vendi(x):
    """코사인 커널 Vendi. x 를 L2 정규화한 그람행렬 / n 의 고유값 엔트로피 지수."""
    if len(x) < 2:
        return float("nan")
    z = x / np.maximum(np.linalg.norm(x, axis=1, keepdims=True), 1e-12)
    lam = np.linalg.eigvalsh((z @ z.T).astype(np.float64) / len(z))
    lam = lam[lam > 1e-12]
    return float(np.exp(-(lam * np.log(lam)).sum()))


# ── 임베딩 ──────────────────────────────────────────────────────
def load_boxes(images, labels, max_boxes, rng):
    """(파일, 클래스, 픽셀 xyxy) 목록을 표본 수 상한까지 무작위로."""
    from PIL import Image
    rows = []
    for png in sorted(glob.glob(f"{images}/*.png")):
        txt = f"{labels}/{os.path.basename(png)[:-4]}.txt"
        if not os.path.exists(txt):
            continue
        for line in open(txt):
            p = line.split()
            if len(p) != 5:
                continue
            c, cx, cy, w, h = int(p[0]), *map(float, p[1:])
            rows.append((png, c, cx, cy, w, h))
    assert rows, f"라벨 없음: {labels}"
    if len(rows) > max_boxes:
        rows = [rows[i] for i in rng.choice(len(rows), max_boxes, replace=False)]
    out = []
    size = {}
    for png, c, cx, cy, w, h in rows:
        if png not in size:
            with Image.open(png) as im:
                size[png] = im.size
        W, H = size[png]
        x1, y1 = (cx - w / 2) * W, (cy - h / 2) * H
        out.append((png, c, x1, y1, x1 + w * W, y1 + h * H))
    return out


def embed(model_path, boxes, chunk, device="cpu"):
    """GT 박스 크롭 → backbone(0..10) → GAP. 같은 페이지는 한 번만 연다."""
    import torch
    from PIL import Image
    from ultralytics import YOLO
    net = YOLO(model_path).model.model[:11].to(device).eval().float()   # backbone: 전부 f=-1 이라 순차 실행 가능
    order = sorted(range(len(boxes)), key=lambda i: boxes[i][0])
    feats = np.zeros((len(boxes), 0), np.float32)
    buf_i, buf_t, outs = [], [], {}
    cur, im = None, None

    def flush():
        if not buf_t:
            return
        with torch.no_grad():
            x = torch.stack(buf_t).to(device)
            for m in net:
                x = m(x)
            v = x.mean((2, 3)).cpu().numpy().astype(np.float32)
        for i, f in zip(buf_i, v):
            outs[i] = f
        buf_i.clear(); buf_t.clear()

    for i in order:
        png, c, x1, y1, x2, y2 = boxes[i]
        if png != cur:
            if im is not None:
                im.close()
            im = Image.open(png).convert("L"); cur = png
        x1, y1 = max(0, int(x1)), max(0, int(y1))
        x2, y2 = max(x1 + 1, int(round(x2))), max(y1 + 1, int(round(y2)))
        crop = im.crop((x1, y1, x2, y2)).resize((CROP, CROP), Image.BILINEAR)
        a = np.asarray(crop, np.float32)[None] / 255.0
        buf_i.append(i); buf_t.append(torch.from_numpy(np.repeat(a, 3, 0)))
        if len(buf_t) >= chunk:
            flush()
    flush()
    if im is not None:
        im.close()
    feats = np.stack([outs[i] for i in range(len(boxes))])
    return feats


def table(real_f, real_c, fake_f, fake_c, names):
    print(f"\n{'class':12s} {'n_real':>7s} {'n_fake':>7s} {'density':>9s} {'coverage':>9s} "
          f"{'Vendi_real':>11s} {'Vendi_fake':>11s}")
    rows = [("(전체)", np.ones(len(real_c), bool), np.ones(len(fake_c), bool))]
    for k, n in enumerate(names):
        rows.append((n, real_c == k, fake_c == k))
    for n, mr, mf in rows:
        R, F = real_f[mr], fake_f[mf]
        if len(R) <= K or len(F) == 0:
            print(f"{n:12s} {len(R):7d} {len(F):7d} {'-':>9s} {'-':>9s} {'-':>11s} {'-':>11s}")
            continue
        d, c = prdc(R, F)
        print(f"{n:12s} {len(R):7d} {len(F):7d} {d:9.3f} {c:9.3f} {vendi(R):11.2f} {vendi(F):11.2f}")
    print("\ncoverage 낮은 클래스 = 합성이 실서식 생김새를 못 덮는 클래스 → 생성기 폭 확장 1순위")
    print("density ≫ 1 = 합성이 실의 좁은 영역에 과밀. Vendi_fake ≪ Vendi_real = 합성 다양성 부족")


def selftest():
    rng = np.random.default_rng(0)
    n, d = 400, 32
    a = rng.normal(0, 1, (n, d))
    # 같은 분포 → coverage 높고 density ≈ 1
    de, co = prdc(a, rng.normal(0, 1, (n, d)))
    assert co > 0.8 and 0.6 < de < 1.6, (de, co)
    # 멀리 떨어진 분포 → coverage ≈ 0
    de2, co2 = prdc(a, rng.normal(50, 1, (n, d)))
    assert co2 < 0.02 and de2 < 0.02, (de2, co2)
    # 한 점에 몰린 합성 → coverage 낮고 density 과밀
    de3, co3 = prdc(a, np.repeat(a[:1], n, 0) + rng.normal(0, 1e-3, (n, d)))
    assert co3 < 0.1 and de3 > 1.0, (de3, co3)
    # Vendi: 동일 벡터 n개 = 1, 직교 기저 d개 = d
    assert abs(vendi(np.repeat(a[:1], 50, 0)) - 1.0) < 1e-6
    assert abs(vendi(np.eye(16)) - 16.0) < 1e-6
    assert vendi(a) > 10
    print(f"selftest: 동분포 (density {de:.2f}, coverage {co:.2f}) · 원거리 ({de2:.2f}, {co2:.2f}) · "
          f"과밀 ({de3:.2f}, {co3:.2f}) · Vendi 무작위 {vendi(a):.1f} / 상수 1.0 / 직교16 16.0")
    print("selftest OK")


def pair(s):
    i, l = s.split(":")
    return i, l


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", help="Ultralytics 가중치 (.pt)")
    ap.add_argument("--real", type=pair, help="images_dir:labels_dir (실서식)")
    ap.add_argument("--fake", type=pair, help="images_dir:labels_dir (합성)")
    ap.add_argument("--max-boxes", type=int, default=2000, help="각 집합의 박스 표본 상한 (2000 이면 메모리 <1GB)")
    ap.add_argument("--chunk", type=int, default=64, help="backbone forward 배치")
    ap.add_argument("--device", default="cpu", help="cpu · cuda:0 · 0(=cuda:0)")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    assert a.model and a.real and a.fake, "--model --real --fake 필요"
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from ultralytics import YOLO
    names = [YOLO(a.model).names[i] for i in range(len(YOLO(a.model).names))]
    rng = np.random.default_rng(a.seed)
    out = {}
    for tag, (img, lab) in (("real", a.real), ("fake", a.fake)):
        bx = load_boxes(img, lab, a.max_boxes, rng)
        print(f"[{tag}] 박스 {len(bx)} · 페이지 {len(set(b[0] for b in bx))} → 임베딩 중")
        dev = f"cuda:{a.device}" if str(a.device).isdigit() else a.device   # Ultralytics 식 '0' 허용
        out[tag] = (embed(a.model, bx, a.chunk, dev), np.array([b[1] for b in bx]))
    print(f"임베딩 차원 {out['real'][0].shape[1]}")
    table(out["real"][0], out["real"][1], out["fake"][0], out["fake"][1], names)


if __name__ == "__main__":
    main()
