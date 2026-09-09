"""5_dataset GT(픽셀 xywh + 타입) → Ultralytics YOLO 형식.
사용: ./venv/bin/python 8_train/to_yolo.py [--out 8_train/yolo]                 # 의미 11종
      ./venv/bin/python 8_train/to_yolo.py --stage1 [--out 8_train/yolo_s1]     # 1단계 생김새 8종 (word·area 제외)
      ... --train-dir 5_dataset/train_v2 --val-dir 5_dataset/holdout_v2            # v2 렌더 사용 시
산출: {out}/images/{train,val,replica}/*.png (심볼릭 링크) + labels/.../*.txt + forms.yaml
"""
import argparse, glob, json, os, struct, sys
TYPES = ["text","number","date","time","phone","email","radio","checkbox","signature","textarea","image"]
SPLITS = {"train":"5_dataset/train", "val":"5_dataset/holdout", "replica":"4_replica/render"}
HTML_DIR = {"replica":"4_replica/html"}          # html 이 렌더 폴더와 다른 곳에 있는 split
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def png_size(p):
    with open(p,"rb") as f: f.seek(16); return struct.unpack(">II", f.read(8))

def convert(split, src, out, stage1=False):
    idir, ldir = f"{out}/images/{split}", f"{out}/labels/{split}"
    os.makedirs(idir, exist_ok=True); os.makedirs(ldir, exist_ok=True)
    n = 0; bad = 0
    if stage1:
        from label_stage1 import fields_from_html, classify_page, CLASSES
        hdir = HTML_DIR.get(split, src)
    for g in sorted(glob.glob(f"{src}/*_gt.json")):
        stem = os.path.basename(g)[:-8]; png = f"{src}/{stem}.png"
        if not os.path.exists(png): continue
        W, H = png_size(png); lines = []; boxes = json.load(open(g))
        if stage1:
            fields = fields_from_html(open(f"{hdir}/{stem}.html", encoding="utf-8").read())
            if len(fields) != len(boxes): print(f"[순서 불일치] {stem}: html {len(fields)} vs gt {len(boxes)}", file=sys.stderr); bad += len(boxes); continue
            cls = classify_page(fields, boxes)
        for i, b in enumerate(boxes):
            if b["w"] <= 0 or b["h"] <= 0: bad += 1; continue
            if stage1:
                if cls[i] not in CLASSES: continue          # word·area 는 1단계 제외
                k = CLASSES.index(cls[i])
            else: k = TYPES.index(b["t"])
            cx, cy = (b["x"] + b["w"]/2)/W, (b["y"] + b["h"]/2)/H
            lines.append(f'{k} {cx:.6f} {cy:.6f} {b["w"]/W:.6f} {b["h"]/H:.6f}')
        link = f"{idir}/{stem}.png"
        if not os.path.lexists(link): os.symlink(os.path.abspath(png), link)
        open(f"{ldir}/{stem}.txt","w").write("\n".join(lines))   # 음성 페이지 = 빈 파일
        n += 1
    return n, bad

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--out"); ap.add_argument("--stage1", action="store_true")
    ap.add_argument("--train-dir", default=SPLITS["train"]); ap.add_argument("--val-dir", default=SPLITS["val"]); a = ap.parse_args()
    SPLITS["train"], SPLITS["val"] = a.train_dir, a.val_dir
    out = a.out or ("8_train/yolo_s1" if a.stage1 else "8_train/yolo")
    names = __import__("label_stage1").CLASSES if a.stage1 else TYPES
    for s, src in SPLITS.items():
        print(s, *convert(s, src, out, a.stage1))
    open(f"{out}/forms.yaml","w").write(
        f"path: {os.path.abspath(out)}\ntrain: images/train\nval: images/val\ntest: images/replica\n"
        f"names:\n" + "".join(f"  {i}: {t}\n" for i, t in enumerate(names)))
    print("→", f"{out}/forms.yaml")
