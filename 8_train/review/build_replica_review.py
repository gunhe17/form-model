"""실서식 시험지 44장 검토 아티팩트 빌더 — 원본 스캔 | 복제 렌더 + 1단계 클래스별 정답 박스."""
import json, os, glob, base64, io, html as H, collections, sys
from PIL import Image, ImageDraw
ROOT="/Users/gunhee/workspace/codespace/project/form-model"
OUT=sys.argv[2] if len(sys.argv)>2 else '.'   # elements.json 작업 폴더
src=open(os.path.join(os.path.dirname(os.path.abspath(__file__)),'build_cls_review.py')).read().split("random.seed(11)")[0]; ns={}; exec(src, ns)
data=ns['data']
COL={'marker':'#2a78d6','comb':'#7c3aed','cell':'#1baf7a','gap':'#eb6834','underline':'#eda100','placeholder':'#e87ba4','signature':'#b3372e','photo':'#0e7c86','word':'#6b7280','area':'#9ca3af'}
FIX={'1편_서식1_1호_사회보장급여관련_공통서식에_관한_고시_[별지_제1호의3서식]-1':'주민번호 낱칸 6+7 ×4행 복원 (넓은 점선 박스 2개 → 낱칸 13개)',
     '1편_서식12호_장애아돌보미_신분증-1':'사진 아래 원형 ○ 3개: image → text(이름 자리표)',
     '1편_서식8호_장애아돌보미_양성교육신청_접수증-1':'하단 표 깨진 태그 복구(접수번호·성명 셀 분리), 40/20시간 괄호 radio',
     '2편_서식21호_발달재활서비스_제공기관_지정서-1':'지정기간 줄의 20·년·월·일 빈칸 폭 24px 로 통일 (검토 지적 반영)',
     '1편_서식5_2호_범죄경력_조회_동의서-1':'(자국어) 빈칸 폭 200 → 120px, 셀 안으로 (검토 지적 반영)',
     '1편_서식5_1호_범죄경력_조회_요청서-1':'접수번호·접수일·처리일: 셀에 라벨이 인쇄된 경우 박스를 빈 부분만으로 (표시 규약 수정, 검토 지적 반영)'}
fixed20=set()
def b64(im,q=78):
    b=io.BytesIO(); im.save(b,'JPEG',quality=q,optimize=True); return base64.b64encode(b.getvalue()).decode()
secs=[]; tot=collections.Counter()
reps=sorted(p for p in glob.glob(f"{ROOT}/4_replica/render/*.png") if not p.endswith('_labeled.png'))
for i,png in enumerate(reps):
    stem=os.path.basename(png)[:-4]; els=data.get(png)
    im=Image.open(png).convert('RGB'); d=ImageDraw.Draw(im); cnt=collections.Counter()
    if els:
        for e in ns['prep'](els):
            c,r=ns['classify'](e); cnt[c]+=1; box=ns['gt_box'](e,c)
            d.rectangle([box['x'],box['y'],box['x']+box['w'],box['y']+box['h']],outline=COL[c],width=2)
    tot.update(cnt)
    o=Image.open(f"{ROOT}/1_corpus/pages/{stem}.png").convert('RGB'); o=o.resize((1004,int(o.height*1004/o.width)))
    rb=b64(im); ob=b64(o,70)
    chips=''.join(f'<span class="c" style="border-color:{COL[k]}">{k} {v}</span>' for k,v in sorted(cnt.items(), key=lambda x:-x[1]))
    notes=[]
    if stem in FIX: notes.append('정정: '+FIX[stem])
    if stem in fixed20: notes.append('정정: "20 년"의 인쇄 20을 빈칸 밖으로')
    note=''.join(f'<div class="fx">{H.escape(n)}</div>' for n in notes)
    secs.append(f'''<section id="p{i}"><h2>{i+1:02d} · {H.escape(stem)}</h2>
<div class="meta"><span>필드 {sum(cnt.values())}</span>{chips}</div>{note}
<div class="pair"><figure><img src="data:image/jpeg;base64,{ob}" alt="" loading="lazy"><figcaption>원본 스캔 (1_corpus)</figcaption></figure>
<figure><img src="data:image/jpeg;base64,{rb}" alt="" loading="lazy"><figcaption>복제 렌더 + 1단계 정답 박스 (4_replica, 정정본)</figcaption></figure></div>
<div class="rv"><label><input type="radio" name="rv-{i}" value="이상없음">이상 없음</label><label><input type="radio" name="rv-{i}" value="이상있음">이상 있음</label><input class="memo" data-k="{i}" placeholder="어디가 어떻게 (예: 3행 주민번호 칸 누락)"></div></section>''')
legend=''.join(f'<span class="c" style="border-color:{v}">{k}</span>' for k,v in COL.items())
ver=sys.argv[1] if len(sys.argv)>1 else 'v2'
page=f'''<title>실서식 시험지 44장 검토</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Noto+Serif+KR:wght@700&family=Noto+Sans+KR:wght@400;500;700&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
:root{{--paper:#F6F7F5;--ink:#1A1D21;--ink2:#4A525C;--mu:#6F7884;--rule:#C9CFD8;--shade:#EEF1F4;--acc:#2C4C8C;--acc2:#24407A;--wn:#A8701A;--wnbg:#F7EEDB}}
@media (prefers-color-scheme:dark){{:root:not([data-theme=light]){{--paper:#15181C;--ink:#E7E9EC;--ink2:#C0C6CE;--mu:#9AA3AF;--rule:#2E343C;--shade:#1D2126;--acc:#7FA2E8;--acc2:#A9C1F0;--wn:#D9A24C;--wnbg:#3A2E18}}}}
:root[data-theme=dark]{{--paper:#15181C;--ink:#E7E9EC;--ink2:#C0C6CE;--mu:#9AA3AF;--rule:#2E343C;--shade:#1D2126;--acc:#7FA2E8;--acc2:#A9C1F0;--wn:#D9A24C;--wnbg:#3A2E18}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--paper);color:var(--ink);font-family:"Noto Sans KR",system-ui,sans-serif;font-size:14px;line-height:1.65}}
.page{{max-width:1180px;margin:0 auto;padding:36px 24px 80px}}
h1,h2{{font-family:"Noto Serif KR",serif;font-weight:700;margin:0;text-wrap:balance}}h1{{font-size:28px}}h2{{font-size:15px;margin-top:40px;padding-top:10px;border-top:2px solid var(--rule);font-family:"IBM Plex Mono",monospace;font-weight:500;color:var(--acc2)}}
p{{margin:8px 0;max-width:80ch}}.eyebrow{{font-family:"IBM Plex Mono",monospace;font-size:12px;letter-spacing:.08em;text-transform:uppercase;color:var(--mu);margin-bottom:8px}}
.bar{{position:sticky;top:0;z-index:5;background:var(--paper);border-bottom:1px solid var(--rule);padding:8px 0;margin:14px 0;display:flex;gap:8px;align-items:center;flex-wrap:wrap;font-size:12.5px}}
.bar a{{color:var(--acc2);text-decoration:none;font-family:"IBM Plex Mono",monospace;padding:0 3px}}.bar button{{font:inherit;font-size:12px;padding:3px 10px;border:1px solid var(--acc);background:transparent;color:var(--acc2);border-radius:3px;cursor:pointer}}
.c{{display:inline-block;font-family:"IBM Plex Mono",monospace;font-size:11.5px;padding:0 7px;border:2px solid;border-radius:3px;margin:2px 4px 2px 0;background:#fff;color:#1A1D21}}
.meta{{display:flex;flex-wrap:wrap;gap:4px;align-items:center;font-size:12.5px;margin:6px 0;color:var(--ink2)}}.meta>span:first-child{{font-weight:700;margin-right:8px}}
.fx{{border-left:3px solid var(--wn);background:var(--wnbg);padding:4px 10px;margin:6px 0;font-size:13px}}
.pair{{display:grid;grid-template-columns:1fr 1fr;gap:12px}}@media(max-width:800px){{.pair{{grid-template-columns:1fr}}}}
figure{{margin:0;border:1px solid var(--rule);background:#fff;padding:4px}}figure img{{display:block;width:100%;height:auto;cursor:zoom-in}}
figcaption{{font-size:11.5px;color:var(--mu);font-family:"IBM Plex Mono",monospace;margin-top:4px}}
.rv{{margin:8px 0 0;padding:8px 12px;border:1px solid var(--rule);font-size:13px;display:flex;gap:14px;align-items:center;flex-wrap:wrap}}.rv label{{cursor:pointer}}.memo{{flex:1;min-width:220px;font:inherit;padding:3px 8px;border:1px solid var(--rule);background:var(--paper);color:var(--ink)}}
#lb{{position:fixed;inset:0;background:rgba(0,0,0,.85);display:none;overflow:auto;z-index:20;cursor:zoom-out;padding:20px}}#lb img{{display:block;margin:0 auto;max-width:none;width:1004px}}
.tips{{background:var(--shade);border:1px solid var(--rule);padding:10px 14px;margin:12px 0;font-size:13.5px;max-width:86ch}}
</style>
<div class="page">
<div class="eyebrow">form-model · 4_replica · 정정본 검토 {ver} · 2026-09-09</div>
<h1>실서식 시험지 44장 검토</h1>
<p>왼쪽은 실제 서식 스캔, 오른쪽은 손으로 옮긴 복제본을 다시 그린 것에 <b>1단계 정답 박스</b>를 클래스별 색으로 얹은 것입니다. 이미지를 클릭하면 원본 크기로 커집니다. 볼 것은 두 가지입니다. 원본에 있는 입력 칸이 복제본에 빠지거나 다른 모양으로 옮겨지지 않았는지, 그리고 정답 박스가 입력 칸이 아닌 곳(머리글·인쇄 값)에 그려지지 않았는지.</p>
<div class="tips"><b>정정한 곳</b> — 페이지 제목 아래 노란 띠로 표시됩니다. 정답 총수 {sum(tot.values())} (1단계 제외 word·area 포함).</div>
<div class="meta"><span>범례</span>{legend}</div>
<div class="meta"><span>합계</span>{''.join(f'<span class="c" style="border-color:{COL[k]}">{k} {v}</span>' for k,v in sorted(tot.items(), key=lambda x:-x[1]))}</div>
<div class="bar">{''.join(f'<a href="#p{i}">{i+1:02d}</a>' for i in range(len(secs)))}<button id="cp">검토 결과 복사</button><span id="cpmsg"></span></div>
{''.join(secs)}
</div>
<div id="lb"><img id="lbi" src="" alt=""></div>
<script>
(function(){{
 var N={len(secs)};
 function load(){{try{{var s=JSON.parse(localStorage.getItem('rep-review')||'{{}}');for(var k=0;k<N;k++){{var v=s[k];if(!v)continue;if(v.v){{var r=document.querySelector('input[name=rv-'+k+'][value="'+v.v+'"]');if(r)r.checked=true}}if(v.m)document.querySelector('.memo[data-k="'+k+'"]').value=v.m}}}}catch(e){{}}}}
 function save(){{try{{var s={{}};for(var k=0;k<N;k++){{var r=document.querySelector('input[name=rv-'+k+']:checked');s[k]={{v:r?r.value:'',m:document.querySelector('.memo[data-k="'+k+'"]').value}}}}localStorage.setItem('rep-review',JSON.stringify(s))}}catch(e){{}}}}
 document.addEventListener('change',save);document.addEventListener('input',save);load();
 document.getElementById('cp').addEventListener('click',function(){{var out=[];document.querySelectorAll('section').forEach(function(sec,k){{var r=sec.querySelector('input[type=radio]:checked');var m=sec.querySelector('.memo').value;if(r||m)out.push(sec.querySelector('h2').textContent+': '+(r?r.value:'')+(m?' — '+m:''))}});var t=out.join('\\n')||'(검토 표시 없음)';(navigator.clipboard?navigator.clipboard.writeText(t):Promise.reject()).then(function(){{document.getElementById('cpmsg').textContent='복사됨'}},function(){{prompt('복사해 주세요',t)}})}});
 var lb=document.getElementById('lb'),lbi=document.getElementById('lbi');
 document.querySelectorAll('figure img').forEach(function(im){{im.addEventListener('click',function(){{lbi.src=im.src;lb.style.display='block'}})}});
 lb.addEventListener('click',function(){{lb.style.display='none';lbi.src=''}});
 document.addEventListener('keydown',function(e){{if(e.key==='Escape'){{lb.style.display='none'}}}});
}})();
</script>'''
open(f'{OUT}/replica-review.html','w').write(page); print('bytes',len(page)//1024,'KB', dict(tot))
