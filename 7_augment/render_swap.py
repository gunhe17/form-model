"""⑥ 서체 스왑 재렌더 — 골격 JSON을 다른 서체 매핑으로 다시 렌더해 GT를 재추출한다.
사용: ./venv/bin/python 7_augment/render_swap.py --n 6000 [--out 7_augment/render_swap]
변형: gothic(전체 나눔고딕) / myeongjo(함초롬→나눔명조). 페이지별 결정적(md5 시드).
"""
import argparse, asyncio, glob, hashlib, json, os, random, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "3_generator"))
from render_skeleton import R

SWAP = {
  "gothic":   {"Hahmlet.ttf":"NanumGothic.ttf", "NanumMyeongjo.ttf":"NanumGothic.ttf", "NanumMyeongjo-Bold.ttf":"NanumGothic-Bold.ttf"},
  "myeongjo": {"Hahmlet.ttf":"NanumMyeongjo.ttf"},
}

async def run(files, outdir):
    from playwright.async_api import async_playwright
    os.makedirs(outdir, exist_ok=True)
    async with async_playwright() as pw:
        b = await pw.chromium.launch(); pg = await b.new_page(viewport={"width":1004,"height":1400})
        for i, f in enumerate(files):
            sk = json.load(open(f)); sid = sk["id"]
            v = list(SWAP)[int(hashlib.md5(sid.encode()).hexdigest(), 16) % len(SWAP)]
            html = R(sk).html()
            for a, bfile in SWAP[v].items(): html = html.replace(f"/{a}'", f"/{bfile}'")
            stem = f"{sid}_{v}"; hp = os.path.join(outdir, stem + ".html"); open(hp, "w").write(html)
            await pg.goto("file://" + os.path.abspath(hp)); await pg.wait_for_timeout(200)
            boxes = await pg.evaluate("""() => [...document.querySelectorAll('[data-f]')].map(e=>{
                const r=e.getBoundingClientRect(); return {t:e.dataset.f,x:r.x,y:r.y,w:r.width,h:r.height}})""")
            await pg.screenshot(path=os.path.join(outdir, stem + ".png"), full_page=True)
            json.dump(boxes, open(os.path.join(outdir, stem + "_gt.json"), "w"))
            if i % 500 == 0: print(i, stem, len(boxes), flush=True)
        await b.close()

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--n", type=int, default=6000)
    ap.add_argument("--src", default="5_dataset/skeletons/train"); ap.add_argument("--out", default="7_augment/render_swap")
    a = ap.parse_args()
    files = sorted(glob.glob(f"{a.src}/*.json")); random.Random(20260908).shuffle(files)
    asyncio.run(run(files[:a.n], a.out)); print("done", a.n)
