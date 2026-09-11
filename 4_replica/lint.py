"""복제 HTML 규약 검사 — 생성기(3_generator/render_skeleton.py 부품 함수)가 강제하는 규약을 사람이 쓴 복제본에 적용한다.

사용: ./venv/bin/python 4_replica/lint.py [4_replica/html/*.html]   (인자 없으면 전체)
출력: 페이지별 위반 목록. 종료코드 = 위반 건수(0이면 통과).

검사 항목
  L1 중첩      data-f 요소 안에 다른 data-f 요소 (태그 훼손·이중 라벨)
  L2 인쇄글자  필드 안에 마스킹(○△0_)·예시(예)·※)·서명 문구·사 진 이외의 인쇄 글자 → 인쇄 접두어가 박스에 들어간 것
  L3 낱칸단독  테두리 있는 빈 소형 박스가 run(2개 이상)이 아닌데 타입이 radio/checkbox 도 아님 (월·일 2자리 낱칸 허용)
  L4 낱칸단순화 주민등록번호·우편번호 라벨 행의 넓은 테두리 빈 박스 (원본은 자릿수 낱칸인데 넓은 박스로 줄인 전사)
  L5 th라벨    th 요소에 data-f
  L6 미라벨마커 □ [ ] ○ ①~⑩ 글리프 텍스트가 data-f 밖에 있음 (글머리·조항번호처럼 뒤에 글이 이어지면 제외)
  L7 퇴화박스  폭 또는 높이 < 8px, 또는 화면 밖
  L8 빈셀누락  같은 행의 다른 td 에는 필드가 있는데 비어 있고 data-f 없는 td (경고)
"""
import asyncio, glob, os, re, sys, collections

JS = r"""() => {
  const rect=e=>{const r=e.getBoundingClientRect();return {x:r.x,y:r.y,w:r.width,h:r.height}};
  const F=[...document.querySelectorAll('[data-f]')].map((e,i)=>({i, f:e.dataset.f, tag:e.tagName.toLowerCase(),
     cls:(e.getAttribute('class')||'').trim(), text:(e.textContent||'').replace(/\s+/g,' ').trim(),
     bw:getComputedStyle(e).borderTopWidth, nested:!!e.querySelector('[data-f]'),
     parent:(e.parentElement&&e.parentElement.tagName.toLowerCase())||'', ...rect(e)}));
  const TH=[...document.querySelectorAll('th[data-f]')].length;
  // 글리프 텍스트 노드가 data-f 밖에 있는지
  const walker=document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT); const loose=[]; let n;
  while((n=walker.nextNode())){ const t=n.textContent.replace(/\s+/g,' ').trim(); if(!t) continue;
    if(/^(□|\[\s*\]|○|◯|[①-⑩])$/.test(t) && !n.parentElement.closest('[data-f]')){
      const p=n.parentElement; const blk=p.closest('div,p,td,li,h1,h2')||p; const pt=(blk.textContent||'').replace(/\s+/g,' ').trim(); loose.push({t, ctx:pt.slice(0,40), hasField:!!blk.querySelector('[data-f]'), ...rect(p)});}
  }
  // 빈 td 누락: 같은 tr 의 td 중 필드 있는 게 있고, 이 td 는 비어 있고 필드 없음
  const wide=[];
  for(const tr of document.querySelectorAll('tr')){ const t=(tr.textContent||'');
    if(!/주민등록번호|주민번호|우편번호/.test(t)) continue;
    for(const e of tr.querySelectorAll('[data-f]')){ const cs=getComputedStyle(e); const r=rect(e);
      if(cs.borderTopWidth!=='0px' && r.w>40 && !(e.textContent||'').trim()) wide.push({f:e.dataset.f, cls:(e.getAttribute('class')||''), ...r}); } }
  const empt=[];
  for(const tr of document.querySelectorAll('tr')){ const tds=[...tr.children].filter(c=>c.tagName==='TD');
    if(!tds.some(td=>td.querySelector('[data-f]'))) continue;
    for(const td of tds){ if(!td.querySelector('[data-f]') && !(td.textContent||'').trim()) empt.push({...rect(td)}); } }
  return {F, TH, loose, empt, wide, W:document.body.scrollWidth, H:document.body.scrollHeight};
}"""
GLY=re.compile(r'^(□|\[\s*\]|\(\s*\)|○|◯|[①-⑩])$')
MASK=re.compile(r'^[○◯△0-9_\s.\-~:]+$|^20(○○|__)?$|^(예\)|※|\*)|^\(?(인|서명 또는 인|직인|서명)\)?$|^직인$|^사\s*진')
WORD=re.compile(r'^[가-힣A-Za-z]{1,4}$')   # 글자 택일(여/남·am/pm·L/R) — 생성기 WORD 규약

async def run(files):
    from playwright.async_api import async_playwright
    total=0; report=[]
    async with async_playwright() as pw:
        b=await pw.chromium.launch(); pg=await b.new_page(viewport={"width":1004,"height":1400})
        for f in files:
            await pg.goto('file://'+os.path.abspath(f)); await pg.wait_for_timeout(120)
            R=await pg.evaluate(JS); F=R['F']; out=[]
            small=[e for e in F if e['bw'] not in ('0px','') and e['w']<=30 and e['h']<=30 and not e['text']]
            small.sort(key=lambda e:(round(e['y']),e['x']))
            run_id={}; i=0
            while i<len(small):
                j=i
                while j+1<len(small) and abs(small[j+1]['y']-small[j]['y'])<=3 and abs(small[j+1]['w']-small[j]['w'])<=2 and 0<=small[j+1]['x']-(small[j]['x']+small[j]['w'])<=8: j+=1
                for k in range(i,j+1): run_id[small[k]['i']]=j-i+1
                i=j+1
            for e in F:
                where=f"{e['f']} {e['tag']}.{e['cls'] or '-'} @({e['x']:.0f},{e['y']:.0f}) {e['w']:.0f}×{e['h']:.0f}"
                if e['nested']: out.append(('L1 중첩', where, e['text'][:30]))
                if e['text'] and not GLY.match(e['text']) and not MASK.match(e['text']) and e['f'] not in ('signature','image') and not (e['f']=='radio' and WORD.match(e['text'])):
                    out.append(('L2 인쇄글자', where, e['text'][:30]))
                if e['i'] in run_id and run_id[e['i']]<2 and e['f'] not in ('radio','checkbox') and 'circ' not in e['cls']:
                    out.append(('L3 낱칸단독', where, ''))
                if e['w']<8 or e['h']<8 or e['x']<0 or e['y']<0 or e['x']+e['w']>R['W']+1: out.append(('L7 퇴화박스', where, ''))
            for e in R['wide']: out.append(('L4 낱칸단순화', f"{e['f']} span.{e['cls'] or '-'} @({e['x']:.0f},{e['y']:.0f}) {e['w']:.0f}×{e['h']:.0f}", '주민번호·우편번호 행'))
            if R['TH']: out.append(('L5 th라벨', f"{R['TH']}개", ''))
            for l in R['loose']:
                if l.get('hasField'): continue   # 글머리 ○/□ 뒤에 입력 요소가 오는 줄(기록 자리)은 마커가 아님 — 2편 22호·NEW_PATTERNS 2
                if not re.match(r'^(□|○|◯|[①-⑩])\s*\S', l['ctx']) or l['ctx']==l['t']: out.append(('L6 미라벨마커', f"@({l['x']:.0f},{l['y']:.0f})", l['ctx']))
            for t in R['empt']: out.append(('L8 빈셀누락(경고)', f"@({t['x']:.0f},{t['y']:.0f}) {t['w']:.0f}×{t['h']:.0f}", ''))
            hard=[o for o in out if not o[0].endswith('(경고)')]; total+=len(hard)
            report.append((os.path.basename(f)[:-5], len(F), out))
        await b.close()
    return total, report

if __name__=='__main__':
    files=[a for a in sys.argv[1:] if a.endswith('.html')] or sorted(glob.glob(os.path.join(os.path.dirname(__file__),'html','*.html')))
    total,report=asyncio.run(run(files))
    cnt=collections.Counter()
    for page,n,out in report:
        if out:
            print(f"\n== {page}  (필드 {n})")
            for rule,where,txt in out: print(f"  {rule:14s} {where}  {txt}"); cnt[rule]+=1
    print("\n합계:", dict(cnt), "| 위반(경고 제외)", total, "| 페이지", len(files))
    sys.exit(min(total,255))
