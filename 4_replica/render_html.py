"""복제 HTML → PNG + GT. 사용: ./venv/bin/python 4_replica/render_html.py 4_replica/html/*.html --out 4_replica/render"""
import json, os, sys, asyncio
async def main(files, outdir):
    from playwright.async_api import async_playwright
    os.makedirs(outdir, exist_ok=True)
    async with async_playwright() as pw:
        b=await pw.chromium.launch(); pg=await b.new_page(viewport={"width":1004,"height":1400})
        for f in files:
            i=os.path.splitext(os.path.basename(f))[0]
            await pg.goto("file://"+os.path.abspath(f)); await pg.wait_for_timeout(300)
            boxes=await pg.evaluate("""() => [...document.querySelectorAll('[data-f]')].map(e=>{
                const r=e.getBoundingClientRect(); return {t:e.dataset.f,x:r.x,y:r.y,w:r.width,h:r.height}})""")
            await pg.screenshot(path=os.path.join(outdir,i+".png"), full_page=True)
            json.dump(boxes, open(os.path.join(outdir,i+"_gt.json"),"w"))
            print(i, len(boxes))
        await b.close()
if __name__=="__main__":
    files=[a for a in sys.argv[1:] if a.endswith(".html")]
    out=sys.argv[sys.argv.index("--out")+1] if "--out" in sys.argv else "4_replica/render"
    asyncio.run(main(files,out))
