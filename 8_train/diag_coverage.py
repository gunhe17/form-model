"""분포 커버리지 — 합성 박스가 실서식 박스를 얼마나 덮는가(density/coverage + Vendi).

왜: recall 은 "못 찾았다"만 말하고 "무엇이 안 덮였나"는 말하지 않는다. GT 박스 크롭을 검출기
backbone 특징으로 임베딩해 실(real) 분포를 합성(fake) 분포가 덮는 비율을 재면, 생성기 폭을
어느 클래스부터 넓혀야 하는지가 수치로 나온다.

  coverage (Naeem 2002.09797, k=5) — 실 표본 중 자기 k-NN 반경 안에 합성 표본이 하나라도 있는 비율.
                                     이게 우리가 말하는 "덮음". 이상치에 강해 PR 보다 안정적.
  density  — 실 k-NN 구 안에 겹치는 합성 표본 수 / k. ≫1 이면 합성이 실의 좁은 영역에 과밀(모드 과밀).
  Vendi (Friedman & Dieng 2210.02410) — 코사인 커널 K/n 고유값의 섀넌 엔트로피 지수. "유효 종 수".
                                        참조 분포가 필요 없어 합성/실 각각의 절대 다양성을 비교할 수 있다.

임베딩: GT 박스 + 주변 여백 20%(테두리·괘선 문맥) → **종횡비 보존 letterbox** 긴 변 96, 흰 패딩
       → backbone 얕은 층(0..4)과 깊은 층(0..10) 두 곳에서 [GAP, GMP] → 블록별 L2 정규화 후 concat
       → 박스 폭·높이(로그 정규화) 2차원을 덧붙인다.
       정사각 강제 리사이즈는 폭 50~650·높이 10~60 인 cell 을 한 점으로 뭉개 coverage 를 0 으로 만든다
       (검증: 실서식끼리 대조군도 0.04 였다). letterbox + 크기 차원이 그 붕괴를 막는다
       (대조군 0.042 → 0.713, Vendi_real cell 1.14 → 2.25).
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
MARGIN = 0.20      # 박스 주변 여백 비율(테두리·괘선 문맥)
SIZE_DIM_W = 1.0   # 크기 2차원의 가중치 (L2 정규화된 특징 블록과 같은 규모)
MIN_N = 30         # 이보다 적으면 '표본 부족'


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
    """density, coverage (Naeem 2020). real 의 k-NN 반경을 기준 구로 쓴다.
    k 는 호출자가 표본 수에 맞춰 max(5, round(√n)) 로 준다(클래스마다 n 이 100배 차이 나므로)."""
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


def letterbox(im, x1, y1, x2, y2):
    """박스 + 여백 20% → 종횡비 보존, 긴 변 CROP, 흰(255) 패딩."""
    from PIL import Image
    W, H = im.size
    bw, bh = max(1.0, x2 - x1), max(1.0, y2 - y1)
    mx, my = bw * MARGIN, bh * MARGIN
    cx1, cy1 = max(0, int(x1 - mx)), max(0, int(y1 - my))
    cx2, cy2 = min(W, int(round(x2 + mx))), min(H, int(round(y2 + my)))
    cx2, cy2 = max(cx1 + 1, cx2), max(cy1 + 1, cy2)
    crop = im.crop((cx1, cy1, cx2, cy2))
    w, h = crop.size
    sc = CROP / max(w, h)
    nw, nh = max(1, int(round(w * sc))), max(1, int(round(h * sc)))
    crop = crop.resize((nw, nh), Image.BILINEAR)
    canvas = Image.new("L", (CROP, CROP), 255)
    canvas.paste(crop, ((CROP - nw) // 2, (CROP - nh) // 2))
    return canvas


def embed(model_path, boxes, chunk, device="cpu"):
    """GT 박스 letterbox 크롭 → backbone 얕은/깊은 층 [GAP,GMP] → 블록별 L2 정규화 concat + 크기 2차원.
    같은 페이지는 한 번만 연다."""
    import torch
    from PIL import Image
    from ultralytics import YOLO
    net = YOLO(model_path).model.model[:11].to(device).eval().float()   # backbone: 전부 f=-1 이라 순차 실행 가능
    TAP = 4   # model[:5] 의 마지막 인덱스(얕은 층)
    order = sorted(range(len(boxes)), key=lambda i: boxes[i][0])
    buf_i, buf_t, outs = [], [], {}
    cur, im = None, None

    def flush():
        if not buf_t:
            return
        with torch.no_grad():
            x = torch.stack(buf_t).to(device)
            shallow = None
            for idx, m in enumerate(net):
                x = m(x)
                if idx == TAP:
                    shallow = x
            def pool(t):
                return torch.cat([t.mean((2, 3)), t.amax((2, 3))], 1)
            blocks = []
            for t in (shallow, x):
                b = pool(t)
                b = b / b.norm(dim=1, keepdim=True).clamp_min(1e-6)   # 블록별 L2 정규화 — 스케일 차이 제거
                blocks.append(b)
            v = torch.cat(blocks, 1).cpu().numpy().astype(np.float32)
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
        crop = letterbox(im, x1, y1, x2, y2)
        a = np.asarray(crop, np.float32)[None] / 255.0
        buf_i.append(i); buf_t.append(torch.from_numpy(np.repeat(a, 3, 0)))
        if len(buf_t) >= chunk:
            flush()
    flush()
    if im is not None:
        im.close()
    feats = np.stack([outs[i] for i in range(len(boxes))])
    # 크기 2차원: 로그 정규화한 폭·높이. 정사각 리사이즈로 잃어버리는 축을 명시적으로 되돌린다.
    wh = np.array([[b[4] - b[2], b[5] - b[3]] for b in boxes], np.float32)
    wh = np.log1p(np.maximum(wh, 1.0)) / np.log1p(2000.0)
    return np.hstack([feats, SIZE_DIM_W * wh.astype(np.float32)])


def table(real_f, real_c, fake_f, fake_c, names, seed=0):
    """클래스마다 real/fake 를 같은 수(작은 쪽)로 맞추고 k = max(5, round(√n)) 로 잰다.
    표본 수가 100배씩 차이 나면 k 고정은 클래스 간 비교를 무의미하게 만든다."""
    rng = np.random.default_rng(seed)
    print(f"\n{'class':12s} {'n_real':>7s} {'n_fake':>7s} {'n_use':>6s} {'k':>4s} "
          f"{'density':>9s} {'coverage':>9s} {'Vendi_real':>11s} {'Vendi_fake':>11s}")
    rows = [("(전체)", np.ones(len(real_c), bool), np.ones(len(fake_c), bool))]
    for k, n in enumerate(names):
        rows.append((n, real_c == k, fake_c == k))
    for n, mr, mf in rows:
        R, F = real_f[mr], fake_f[mf]
        nr, nf = len(R), len(F)
        use = min(nr, nf)
        if use < MIN_N:
            note = "표본 부족" if use > 0 else "-"
            print(f"{n:12s} {nr:7d} {nf:7d} {use:6d} {'-':>4s} {note:>9s} {'-':>9s} {'-':>11s} {'-':>11s}")
            continue
        if nr > use: R = R[rng.choice(nr, use, replace=False)]
        if nf > use: F = F[rng.choice(nf, use, replace=False)]
        kk = max(K, int(round(use ** 0.5)))
        d, c = prdc(R, F, kk)
        print(f"{n:12s} {nr:7d} {nf:7d} {use:6d} {kk:4d} {d:9.3f} {c:9.3f} {vendi(R):11.2f} {vendi(F):11.2f}")
    print("\ncoverage 낮은 클래스 = 합성이 실서식 생김새를 못 덮는 클래스 → 생성기 폭 확장 1순위")
    print("density ≫ 1 = 합성이 실의 좁은 영역에 과밀. Vendi_fake ≪ Vendi_real = 합성 다양성 부족")
    print("읽기: 절대값이 아니라 대조군(실↔실, 2026-09-11 기준 전체 0.713 · cell 0.728 · marker 0.313) 대비로 본다")


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
    # letterbox: 가로로 긴 박스가 종횡비를 유지한 채 긴 변 CROP 에 맞는지
    from PIL import Image
    im = Image.new("L", (400, 100), 0)
    lb = letterbox(im, 10, 40, 210, 60)      # 200×20 박스 → 여백 포함 240×28 → 96×11 안팎
    assert lb.size == (CROP, CROP)
    col = np.asarray(lb).min(0); row = np.asarray(lb).min(1)
    assert (col < 255).sum() >= CROP - 2 and 6 <= (row < 255).sum() <= 16, ((col < 255).sum(), (row < 255).sum())
    print(f"selftest: 동분포 (density {de:.2f}, coverage {co:.2f}) · 원거리 ({de2:.2f}, {co2:.2f}) · "
          f"과밀 ({de3:.2f}, {co3:.2f}) · Vendi 무작위 {vendi(a):.1f} / 상수 1.0 / 직교16 16.0 · letterbox OK")
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
    table(out["real"][0], out["real"][1], out["fake"][0], out["fake"][1], names, a.seed)


if __name__ == "__main__":
    main()
