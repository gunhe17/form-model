"""픽셀 증강 — 검출기 트랙용. 라벨은 정규화 좌표라 변하지 않는다(여백 밖에만 그린다).
축: ①dpi 리샘플 ③광학(밝기·대비·조명경사·종이톤) ④노이즈(가우시안·JPEG·줄무늬·먼지) ⑤잉크(팽창/침식·블러) ⑦지면 맥락(러닝헤드·쪽번호·챕터탭)
②기하는 YOLO 온라인 증강(degrees/perspective/translate/scale)에 맡긴다. ⑥서체 스왑은 render_swap.py.

사용: ./venv/bin/python 7_augment/augment.py --tier office   --src 8_train/yolo/images/train --labels 8_train/yolo/labels/train --n 20000
      ./venv/bin/python 7_augment/augment.py --tier degraded --src ... --n 10000 --seed 2
산출: 7_augment/pool/images/{tier}/*.png + 7_augment/pool/labels/{tier}/*.txt
"""
import argparse, glob, io, os, random, shutil
from multiprocessing import Pool
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

FONTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "fonts")
HEADS = ["2026년 장애아동가족지원 사업안내", "발달재활서비스 사업안내", "제2편 발달재활서비스", "제3편 언어발달지원",
         "장애인복지사업안내", "아동분야 사업안내", "Ⅲ. 서식", "붙임 서식"]
TABS = ["서식", "제1편", "제2편", "제3편", "부록", "Ⅲ"]

# 강도 2단. 값은 (min,max) 범위 또는 확률.
TIER = {
  "office":   dict(dpi=(0.70,1.00), bright=(-0.05,0.05), contrast=(0.9,1.1), grad=(0.90,1.0), tone=0.5,
                   gauss=(0,3), jpeg=(70,92), streak=0.15, dust=(0,40), ink=0.3, blur=(0,0.4), ctx=0.5),
  "degraded": dict(dpi=(0.55,0.85), bright=(-0.12,0.10), contrast=(0.75,1.2), grad=(0.72,0.95), tone=0.8,
                   gauss=(4,10), jpeg=(35,65), streak=0.5, dust=(40,220), ink=0.7, blur=(0.2,0.7), ctx=0.6),
}

def U(r, lo_hi): return r.uniform(*lo_hi)

def context(img, r):
    """⑦ 러닝헤드(상단 여백) · 쪽번호(하단 여백) · 챕터탭(우측 여백). 본문 여백: 상 95 좌우 95 하 72px."""
    d = ImageDraw.Draw(img); W, H = img.size
    f13 = ImageFont.truetype(os.path.join(FONTS, "NanumGothic.ttf"), 13)
    if r.random() < 0.8:
        t = r.choice(HEADS); x = r.choice([40, (W - d.textlength(t, font=f13)) / 2, W - 40 - d.textlength(t, font=f13)])
        d.text((x, 28), t, fill=(60, 60, 60), font=f13)
        if r.random() < 0.5: d.line([(40, 50), (W - 40, 50)], fill=(120, 120, 120), width=1)
    if r.random() < 0.8:
        n = str(r.randint(3, 480)); t = r.choice([n, f"- {n} -", f"{n} 쪽"])
        x = r.choice([40, (W - d.textlength(t, font=f13)) / 2, W - 40 - d.textlength(t, font=f13)])
        d.text((x, H - 40), t, fill=(50, 50, 50), font=f13)
    if r.random() < 0.35:
        tab = Image.new("RGB", (120, 26), (200, 200, 200)); td = ImageDraw.Draw(tab)
        td.text((8, 4), r.choice(TABS), fill=(0, 0, 0), font=ImageFont.truetype(os.path.join(FONTS, "NanumGothic-Bold.ttf"), 15))
        tab = tab.rotate(90, expand=True); y = r.randint(120, max(121, H - 300))
        img.paste(tab, (W - 30, y))
    return img

def augment(img, tier, r):
    P = TIER[tier]
    # ① dpi: 축소만(라벨 불변). 학습 시 letterbox가 도로 키우므로 선 굵기·선명도만 남는다
    # ⑤ 잉크 팽창/침식 — 축소 전 원해상도에서, 부분 블렌드(침식은 글자를 지우기 쉬워 약하게)
    if r.random() < P["ink"]:
        g = img.convert("L"); dil = r.random() < 0.5
        g2 = g.filter(ImageFilter.MinFilter(3) if dil else ImageFilter.MaxFilter(3))
        img = Image.blend(g, g2, r.uniform(0.3, 0.6) if dil else r.uniform(0.25, 0.5)).convert("RGB")
    f = U(r, P["dpi"]); W, H = img.size
    if f < 0.995: img = img.resize((max(64, int(W * f)), max(64, int(H * f))), Image.LANCZOS)
    a = np.asarray(img).astype(np.float32) / 255.0
    # ③ 광학
    a = a * U(r, P["contrast"]) + U(r, P["bright"])
    h, w = a.shape[:2]; ang = r.uniform(0, 2 * np.pi)
    ramp = (np.cos(ang) * np.linspace(-0.5, 0.5, w)[None, :] + np.sin(ang) * np.linspace(-0.5, 0.5, h)[:, None]) + 0.5
    a = a * (U(r, P["grad"]) + (1 - U(r, P["grad"])) * ramp)[..., None]
    if r.random() < P["tone"]: a = a * np.array([1.0, r.uniform(0.96, 0.99), r.uniform(0.88, 0.96)])[None, None, :]
    # ④ 노이즈
    s = U(r, P["gauss"])
    if s > 0: a = a + np.random.default_rng(r.randrange(1 << 30)).normal(0, s / 255.0, a.shape)
    if r.random() < P["streak"]:
        for _ in range(r.randint(1, 4)):
            x = r.randrange(w); a[:, x:x + r.randint(1, 3)] *= r.uniform(0.6, 0.9)
    a = np.clip(a, 0, 1); img = Image.fromarray((a * 255).astype(np.uint8))
    nd = r.randint(*P["dust"])
    if nd:
        d = ImageDraw.Draw(img)
        for _ in range(nd):
            x, y, rad = r.randrange(w), r.randrange(h), r.choice([1, 1, 1, 2]); d.ellipse([x, y, x + rad, y + rad], fill=(r.randint(0, 80),) * 3)
    b = U(r, P["blur"])
    if b > 0.1: img = img.filter(ImageFilter.GaussianBlur(b))
    # ⑦ 지면 맥락 (dpi 축소 후 좌표라 여백 비율로 재계산되지만 여백 폭이 충분)
    if r.random() < P["ctx"]: img = context(img, r)
    # ④ JPEG 재부호화
    buf = io.BytesIO(); img.save(buf, "JPEG", quality=r.randint(*P["jpeg"])); img = Image.open(buf).convert("RGB")
    return img

def work(args):
    src, lab, out_i, out_l, tier, seed = args
    stem = os.path.splitext(os.path.basename(src))[0]
    r = random.Random(f"{seed}:{tier}:{stem}")
    img = augment(Image.open(src).convert("RGB"), tier, r)
    img.save(os.path.join(out_i, stem + ".png"), optimize=False)
    shutil.copy(lab, os.path.join(out_l, stem + ".txt"))
    return stem

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--tier", choices=list(TIER), required=True)
    ap.add_argument("--src", nargs="+", required=True, help="이미지 디렉토리(들)")
    ap.add_argument("--labels", nargs="+", required=True, help="같은 순서의 라벨 디렉토리(들)")
    ap.add_argument("--n", type=int, default=0, help="0=전부, 아니면 무작위 n장")
    ap.add_argument("--out", default="7_augment/pool"); ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--name", default=None, help="산출 구분명(기본=tier). 예: stress")
    ap.add_argument("--workers", type=int, default=8)
    a = ap.parse_args()
    items = []
    for sd, ld in zip(a.src, a.labels):
        for p in sorted(glob.glob(f"{sd}/*.png")):
            l = os.path.join(ld, os.path.splitext(os.path.basename(p))[0] + ".txt")
            if os.path.exists(l): items.append((p, l))
    if a.n: random.Random(a.seed).shuffle(items); items = items[:a.n]
    name = a.name or a.tier; oi, ol = f"{a.out}/images/{name}", f"{a.out}/labels/{name}"; os.makedirs(oi, exist_ok=True); os.makedirs(ol, exist_ok=True)
    jobs = [(p, l, oi, ol, a.tier, a.seed) for p, l in items]
    with Pool(a.workers) as pool:
        for i, s in enumerate(pool.imap_unordered(work, jobs, chunksize=16)):
            if i % 2000 == 0: print(i, s, flush=True)
    print(name, len(jobs), "→", oi)
