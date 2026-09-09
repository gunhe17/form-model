"""검토판용 요소 추출 — 학습 표본 HTML + 4_replica 44쪽을 Playwright 로 렌더해 [data-f]·th·td·prose 의 계산된 스타일과 박스를 elements.json 에 저장.
사용: ./venv/bin/python 8_train/review/extract_elements.py <out_dir> [학습 표본 수=70]
"""
import asyncio, glob, json, os, random, sys
ROOT=os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
JS = """() => {
  const q=(sel,kind)=>[...document.querySelectorAll(sel)].map(e=>{const r=e.getBoundingClientRect();const cs=getComputedStyle(e);
    return {kind, f:e.dataset.f||null, tag:e.tagName.toLowerCase(), cls:(e.getAttribute('class')||'').trim(), disp:cs.display,
      w:r.width,h:r.height,x:r.x,y:r.y, bw:cs.borderTopWidth, bs:cs.borderTopStyle, bb:cs.borderBottomWidth,
      text:(e.textContent||'').replace(/\\s+/g,' ').trim().slice(0,30), intable:!!e.closest('table'),
      hasf:!!e.querySelector('[data-f]')}});
  return q('[data-f]','field').concat(q('th','th'), q('td:not([data-f])','td'), q('p.ln, p.note, .note, p.sigline','prose'));
}"""
async def main(out, n):
    from playwright.async_api import async_playwright
    random.seed(3); syn=sorted(glob.glob(f'{ROOT}/5_dataset/train_v2/*.html')) or sorted(glob.glob(f'{ROOT}/5_dataset/train/*.html')); random.shuffle(syn)
    pages=[(h,h[:-5]+'.png') for h in syn[:n]]+[(h,f'{ROOT}/4_replica/render/'+os.path.basename(h)[:-5]+'.png') for h in sorted(glob.glob(f'{ROOT}/4_replica/html/*.html'))]
    data={}
    async with async_playwright() as pw:
        b=await pw.chromium.launch(); pg=await b.new_page(viewport={"width":1004,"height":1400})
        for html,png in pages:
            await pg.goto('file://'+os.path.abspath(html)); await pg.wait_for_timeout(120); data[png]=await pg.evaluate(JS)
        await b.close()
    os.makedirs(f'{out}/cls',exist_ok=True); json.dump(data,open(f'{out}/cls/elements.json','w'),ensure_ascii=False); print('pages',len(data))
if __name__=='__main__':
    asyncio.run(main(sys.argv[1], int(sys.argv[2]) if len(sys.argv)>2 else 70))
