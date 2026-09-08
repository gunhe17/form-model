"""5_dataset GT(픽셀 xywh + 타입) → Ultralytics YOLO 형식.
사용: ./venv/bin/python 8_train/to_yolo.py [--out 8_train/yolo]
산출: {out}/images/{train,val,replica}/*.png (심볼릭 링크) + labels/.../*.txt + forms.yaml
"""
import argparse, glob, json, os, struct
TYPES = ["text","number","date","time","phone","email","radio","checkbox","signature","textarea","image"]
SPLITS = {"train":"5_dataset/train", "val":"5_dataset/holdout", "replica":"4_replica/render"}

def png_size(p):
    with open(p,"rb") as f: f.seek(16); return struct.unpack(">II", f.read(8))

def convert(split, src, out):
    idir, ldir = f"{out}/images/{split}", f"{out}/labels/{split}"
    os.makedirs(idir, exist_ok=True); os.makedirs(ldir, exist_ok=True)
    n = 0; bad = 0
    for g in sorted(glob.glob(f"{src}/*_gt.json")):
        stem = os.path.basename(g)[:-8]; png = f"{src}/{stem}.png"
        if not os.path.exists(png): continue
        W, H = png_size(png); lines = []
        for b in json.load(open(g)):
            if b["w"] <= 0 or b["h"] <= 0: bad += 1; continue
            cx, cy = (b["x"] + b["w"]/2)/W, (b["y"] + b["h"]/2)/H
            lines.append(f'{TYPES.index(b["t"])} {cx:.6f} {cy:.6f} {b["w"]/W:.6f} {b["h"]/H:.6f}')
        link = f"{idir}/{stem}.png"
        if not os.path.lexists(link): os.symlink(os.path.abspath(png), link)
        open(f"{ldir}/{stem}.txt","w").write("\n".join(lines))   # 음성 페이지 = 빈 파일
        n += 1
    return n, bad

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--out", default="8_train/yolo"); a = ap.parse_args()
    for s, src in SPLITS.items():
        print(s, *convert(s, src, a.out))
    open(f"{a.out}/forms.yaml","w").write(
        f"path: {os.path.abspath(a.out)}\ntrain: images/train\nval: images/val\ntest: images/replica\n"
        f"names:\n" + "".join(f"  {i}: {t}\n" for i, t in enumerate(TYPES)))
    print("→", f"{a.out}/forms.yaml")
