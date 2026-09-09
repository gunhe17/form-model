"""재구성 데이터셋 검수 아티팩트 — 렌더 폴더(html+png+_gt.json)와 골격 폴더(json)에서
문서 유형별·신규 카드별 페이지 예시(1단계 클래스 색 박스), 클래스별 크롭, 분포·커버리지 표를 한 페이지로.
사용: python build_dataset_review.py <render_dir> <skeleton_dir> <out.html> [label]
"""
import sys, os, glob, json, base64, io, html as H, collections, random, subprocess
from PIL import Image, ImageDraw
ROOT="/Users/gunhee/workspace/codespace/project/form-model"
sys.path.insert(0, f"{ROOT}/8_train")
from label_stage1 import fields_from_html, classify_page, CLASSES, bucket, WB, HB
RD, SK, OUT = sys.argv[1], sys.argv[2], sys.argv[3]; LABEL = sys.argv[4] if len(sys.argv)>4 else ''
COL={'marker':'#2a78d6','comb':'#7c3aed','cell':'#1baf7a','gap':'#eb6834','underline':'#eda100','placeholder':'#e87ba4','signature':'#b3372e','photo':'#0e7c86','word':'#6b7280','area':'#9ca3af'}
NEW_CARDS=['ph_lines','gp_cell','ul_cell','sig_cell','comb_jumin','comb_date','scale_words','img_circle','dbx_cell','stamp_box','inset_label_full','photo_grid','sig_grid','ul_lines','pf_grid']
random.seed(5)
pages={}
for g in sorted(glob.glob(f"{RD}/*_gt.json")):
    stem=os.path.basename(g)[:-8]
    if not os.path.exists(f"{RD}/{stem}.html"): continue
    fields=fields_from_html(open(f"{RD}/{stem}.html",encoding='utf-8').read()); boxes=json.load(open(g))
    if len(fields)!=len(boxes): continue
    cls=classify_page(fields,boxes)
    sk=json.load(open(f"{SK}/{stem}.json")) if os.path.exists(f"{SK}/{stem}.json") else {}
    cards=[b.get('card') for b in sk.get('blocks',[])]+[p.get('kind') if isinstance(p,dict) else p for p in sk.get('prefill',[])]
    pages[stem]=dict(fields=fields,boxes=boxes,cls=cls,type=sk.get('type',stem.rsplit('_',1)[0]),cards=cards)
tot=collections.Counter(); dens=[]; grid=collections.Counter()
for p in pages.values():
    dens.append(sum(1 for c in p['cls'] if c in CLASSES))
    for f,b,c in zip(p['fields'],p['boxes'],p['cls']):
        tot[c]+=1
        if c in CLASSES: grid[(c,bucket(b['w'],WB),bucket(b['h'],HB),'표' if f['intable'] else '글줄')]+=1
N=sum(tot.values()); dens.sort()
def b64(im,q=72):
    b=io.BytesIO(); im.save(b,'JPEG',quality=q,optimize=True); return base64.b64encode(b.getvalue()).decode()
def page_img(stem,scale=0.62):
    p=pages[stem]; im=Image.open(f"{RD}/{stem}.png").convert('RGB'); d=ImageDraw.Draw(im)
    for b,c in zip(p['boxes'],p['cls']): d.rectangle([b['x'],b['y'],b['x']+b['w'],b['y']+b['h']],outline=COL[c],width=2)
    full=b64(im,74); sm=im.resize((int(im.width*scale),int(im.height*scale))); return b64(sm,70), full, sm.width
def crop(stem,b,m=70,maxw=440):
    im=Image.open(f"{RD}/{stem}.png").convert('RGB'); W,Hh=im.size
    x0=max(0,b['x']-m); x1=min(W,b['x']+b['w']+m); y0=max(0,b['y']-30); y1=min(Hh,b['y']+b['h']+30)
    if x1-x0>maxw: cx=b['x']+b['w']/2; x0=max(0,cx-maxw/2); x1=min(W,x0+maxw); x0=max(0,x1-maxw)
    c=im.crop((int(x0),int(y0),int(x1),int(y1))); d=ImageDraw.Draw(c); d.rectangle([b['x']-x0,b['y']-y0,b['x']-x0+b['w'],b['y']-y0+b['h']],outline='#D8322A',width=2)
    return b64(c,80), c.width, c.height
full_store=[]
def fig_page(stem,cap):
    sm,full,w=page_img(stem); full_store.append(full); i=len(full_store)-1
    p=pages[stem]; cnt=collections.Counter(c for c in p['cls'])
    chips=''.join(f'<span class="c" style="border-color:{COL[k]}">{k} {v}</span>' for k,v in cnt.most_common())
    return f'<figure><img src="data:image/jpeg;base64,{sm}" width="{w}" data-i="{i}" alt=""><figcaption>{H.escape(cap)} · {H.escape(stem)}<br>{chips}</figcaption></figure>'
# 섹션 1: 문서 유형별 2장
types=collections.defaultdict(list)
for s,p in pages.items(): types[p['type']].append(s)
sec_types=''.join(f'<h3>{H.escape(t)} <span class="mu">({len(v)}장)</span></h3><div class="grid">'+''.join(fig_page(s,t) for s in random.sample(v,min(2,len(v))))+'</div>' for t,v in sorted(types.items(), key=lambda x:-len(x[1])))
# 섹션 2: 신규 카드별 3장
sec_cards=''
for cd in NEW_CARDS:
    v=[s for s,p in pages.items() if cd in p['cards']]
    if not v: sec_cards+=f'<h3>{cd} <span class="mu">(0장 — 이 표본에 없음)</span></h3>'; continue
    sec_cards+=f'<h3>{cd} <span class="mu">({len(v)}장)</span></h3><div class="grid">'+''.join(fig_page(s,cd) for s in random.sample(v,min(3,len(v))))+'</div>'
# 섹션 3: 클래스별 크롭 8개
sec_cls=''
for c in CLASSES:
    items=[(s,b) for s,p in pages.items() for b,k in zip(p['boxes'],p['cls']) if k==c]
    random.shuffle(items); seen=set(); pick=[]
    for s,b in items:
        key=(s,round(b['w']/60),round(b['h']/20))
        if s in seen: continue
        seen.add(s); pick.append((s,b))
        if len(pick)>=8: break
    figs=''.join((lambda r: f'<figure class="cr"><img src="data:image/jpeg;base64,{r[0]}" width="{r[1]}" height="{r[2]}" alt=""><figcaption>{b["w"]:.0f}×{b["h"]:.0f} · {H.escape(s[:22])}</figcaption></figure>')(crop(s,b)) for s,b in pick)
    sec_cls+=f'<h3><span class="c" style="border-color:{COL[c]}">{c}</span> {tot[c]}개 · {100*tot[c]/N:.1f}%</h3><div class="grid cr">{figs}</div>'
# 표
share=''.join(f'<tr><td>{c}</td><td class="n">{tot[c]}</td><td class="n">{100*tot[c]/N:.1f}%</td></tr>' for c in CLASSES+['word','area'])
med=dens[len(dens)//2] if dens else 0; p90=dens[int(len(dens)*0.9)] if dens else 0
try:
    cov=subprocess.run([f"{ROOT}/venv/bin/python",f"{ROOT}/8_train/label_stage1.py","--train",RD,"--coverage","--min","5"],capture_output=True,text=True,cwd=ROOT).stdout
    cov=cov.split('== 커버리지')[1].split('== 학습 분포')[0] if '== 커버리지' in cov else cov
except Exception as e: cov=str(e)
page=f'''<title>재구성 데이터셋 검수</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Noto+Serif+KR:wght@700&family=Noto+Sans+KR:wght@400;500;700&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
:root{{--paper:#F6F7F5;--ink:#1A1D21;--ink2:#4A525C;--mu:#6F7884;--rule:#C9CFD8;--shade:#EEF1F4;--acc:#2C4C8C;--acc2:#24407A}}
@media (prefers-color-scheme:dark){{:root:not([data-theme=light]){{--paper:#15181C;--ink:#E7E9EC;--ink2:#C0C6CE;--mu:#9AA3AF;--rule:#2E343C;--shade:#1D2126;--acc:#7FA2E8;--acc2:#A9C1F0}}}}
:root[data-theme=dark]{{--paper:#15181C;--ink:#E7E9EC;--ink2:#C0C6CE;--mu:#9AA3AF;--rule:#2E343C;--shade:#1D2126;--acc:#7FA2E8;--acc2:#A9C1F0}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--paper);color:var(--ink);font-family:"Noto Sans KR",system-ui,sans-serif;font-size:14px;line-height:1.65}}
.page{{max-width:1240px;margin:0 auto;padding:36px 24px 80px}}
h1,h2,h3{{font-family:"Noto Serif KR",serif;font-weight:700;margin:0;text-wrap:balance}}h1{{font-size:28px}}h2{{font-size:20px;margin-top:48px;padding-top:12px;border-top:3px double var(--mu)}}h3{{font-size:14px;margin:26px 0 8px;font-family:"IBM Plex Mono",monospace;font-weight:500;color:var(--acc2)}}
p{{margin:8px 0;max-width:80ch}}.mu{{color:var(--mu);font-weight:400}}
.eyebrow{{font-family:"IBM Plex Mono",monospace;font-size:12px;letter-spacing:.08em;text-transform:uppercase;color:var(--mu);margin-bottom:8px}}
.bar{{position:sticky;top:0;z-index:5;background:var(--paper);border-bottom:1px solid var(--rule);padding:8px 0;margin:14px 0;display:flex;gap:14px;align-items:center;flex-wrap:wrap;font-size:13px}}.bar a{{color:var(--acc2);text-decoration:none}}
.bar button{{font:inherit;font-size:12px;padding:3px 10px;border:1px solid var(--acc);background:transparent;color:var(--acc2);border-radius:3px;cursor:pointer}}
.c{{display:inline-block;font-family:"IBM Plex Mono",monospace;font-size:11.5px;padding:0 7px;border:2px solid;border-radius:3px;margin:2px 4px 2px 0;background:#fff;color:#1A1D21}}
table{{border-collapse:collapse;font-size:13px;margin:10px 0}}th,td{{border:1px solid var(--rule);padding:5px 10px;text-align:left}}th{{background:var(--shade);font-weight:500}}td.n{{text-align:right;font-family:"IBM Plex Mono",monospace}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:12px}}.grid.cr{{grid-template-columns:repeat(auto-fill,minmax(230px,1fr))}}
figure{{margin:0;border:1px solid var(--rule);background:#fff;padding:4px}}figure img{{display:block;max-width:100%;height:auto;cursor:zoom-in}}figure.cr img{{cursor:default}}
figcaption{{font-size:11px;color:var(--mu);font-family:"IBM Plex Mono",monospace;margin-top:4px;line-height:1.5}}
pre{{background:var(--shade);border:1px solid var(--rule);padding:10px 12px;font-family:"IBM Plex Mono",monospace;font-size:12px;overflow-x:auto}}
.rv{{margin:10px 0;padding:8px 12px;border:1px solid var(--rule);font-size:13px;display:flex;gap:14px;align-items:center;flex-wrap:wrap}}.memo{{flex:1;min-width:240px;font:inherit;padding:3px 8px;border:1px solid var(--rule);background:var(--paper);color:var(--ink)}}
#lb{{position:fixed;inset:0;background:rgba(0,0,0,.85);display:none;overflow:auto;z-index:20;cursor:zoom-out;padding:20px}}#lb img{{display:block;margin:0 auto;max-width:none;width:1004px}}
</style>
<div class="page">
<div class="eyebrow">form-model · 3_generator 재구성 · 데이터셋 검수 {H.escape(LABEL)}</div>
<h1>재구성 데이터셋 검수</h1>
<p>표본 {len(pages)}장, 필드 {N}개. 정답 박스는 1단계 클래스별 색. 페이지 이미지를 클릭하면 원본 크기로 커집니다. 볼 것: 각 서식 유형이 실제 행정서식처럼 보이는가, 새 카드가 의도한 모양인가, 정답 박스가 입력 칸에만 있는가, 클래스 점유율·밀도가 목표 안인가.</p>
<div class="bar"><a href="#dist">분포</a><a href="#types">유형별</a><a href="#cards">신규 카드별</a><a href="#cls">클래스별 크롭</a><button id="cp">검수 메모 복사</button><span id="cpmsg" class="mu"></span></div>
<h2 id="dist">분포</h2>
<div style="display:grid;grid-template-columns:auto 1fr;gap:24px;align-items:start">
<table><tr><th>클래스</th><th class="n">개수</th><th class="n">점유율</th></tr>{share}<tr><th>합계</th><th class="n">{N}</th><th></th></tr></table>
<div><p>페이지당 필드: 중앙값 <b>{med}</b> · p90 {p90} · 최대 {dens[-1] if dens else 0} (목표 중앙값 20~30, 상한 50)</p>
<p>범례: {''.join(f'<span class="c" style="border-color:{v}">{k}</span>' for k,v in COL.items())}</p>
<p><b>커버리지 격자 — 실서식에 있는데 이 표본에 5개 미만인 칸</b></p><pre>{H.escape(cov.strip()) or '(없음)'}</pre></div></div>
<div class="rv"><b>분포 검수</b><label><input type="radio" name="rv-dist" value="OK">OK</label><label><input type="radio" name="rv-dist" value="수정">수정</label><input class="memo" data-k="dist" placeholder="메모"></div>
<h2 id="types">문서 유형별 예시 (유형당 2장)</h2>{sec_types}
<div class="rv"><b>유형 검수</b><label><input type="radio" name="rv-types" value="OK">OK</label><label><input type="radio" name="rv-types" value="수정">수정</label><input class="memo" data-k="types" placeholder="유형 이름과 문제"></div>
<h2 id="cards">신규 카드별 예시 (카드당 3장)</h2>{sec_cards}
<div class="rv"><b>카드 검수</b><label><input type="radio" name="rv-cards" value="OK">OK</label><label><input type="radio" name="rv-cards" value="수정">수정</label><input class="memo" data-k="cards" placeholder="카드 이름과 문제"></div>
<h2 id="cls">클래스별 크롭 (클래스당 8개, 붉은 박스 = 정답)</h2>{sec_cls}
<div class="rv"><b>클래스 검수</b><label><input type="radio" name="rv-cls" value="OK">OK</label><label><input type="radio" name="rv-cls" value="수정">수정</label><input class="memo" data-k="cls" placeholder="클래스와 문제"></div>
</div>
<div id="lb"><img id="lbi" src="" alt=""></div>
<script>
(function(){{
 var F={json.dumps(full_store)};
 var lb=document.getElementById('lb'),lbi=document.getElementById('lbi');
 document.querySelectorAll('figure:not(.cr) img').forEach(function(im){{im.addEventListener('click',function(){{lbi.src='data:image/jpeg;base64,'+F[+im.dataset.i];lb.style.display='block'}})}});
 lb.addEventListener('click',function(){{lb.style.display='none';lbi.src=''}});document.addEventListener('keydown',function(e){{if(e.key==='Escape')lb.style.display='none'}});
 var K=['dist','types','cards','cls'];
 function load(){{try{{var s=JSON.parse(localStorage.getItem('ds-review')||'{{}}');K.forEach(function(k){{var v=s[k];if(!v)return;if(v.v){{var r=document.querySelector('input[name=rv-'+k+'][value="'+v.v+'"]');if(r)r.checked=true}}if(v.m)document.querySelector('.memo[data-k='+k+']').value=v.m}})}}catch(e){{}}}}
 function save(){{try{{var s={{}};K.forEach(function(k){{var r=document.querySelector('input[name=rv-'+k+']:checked');s[k]={{v:r?r.value:'',m:document.querySelector('.memo[data-k='+k+']').value}}}});localStorage.setItem('ds-review',JSON.stringify(s))}}catch(e){{}}}}
 document.addEventListener('change',save);document.addEventListener('input',save);load();
 document.getElementById('cp').addEventListener('click',function(){{var out=K.map(function(k){{var r=document.querySelector('input[name=rv-'+k+']:checked');var m=document.querySelector('.memo[data-k='+k+']').value;return k+': '+(r?r.value:'(미검수)')+(m?' — '+m:'')}}).join('\\n');(navigator.clipboard?navigator.clipboard.writeText(out):Promise.reject()).then(function(){{document.getElementById('cpmsg').textContent='복사됨'}},function(){{prompt('복사해 주세요',out)}})}});
}})();
</script>'''
open(OUT,'w').write(page); print('pages',len(pages),'fields',N,'bytes',len(page)//1024,'KB')
