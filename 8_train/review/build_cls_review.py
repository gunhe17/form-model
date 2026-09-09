"""1단계 클래스 검토판 빌더 v2 — 마크업 서명 → 클래스 규칙(우선순위 순), 낱칸 run 감지, 보이지 않는 마커→셀 승격, td 내부 박스 규약."""
import json, re, random, base64, io, os, collections, sys, html as H
from PIL import Image
ROOT="/Users/gunhee/workspace/codespace/project/form-model"
OUT=sys.argv[1] if len(sys.argv)>1 else '.'   # elements.json 이 있는 작업 폴더(extract_elements.py 출력)
data=json.load(open(f'{OUT}/cls/elements.json'))
GLY={'□','[ ]','( )','①','②','③','④','⑤','⑥','⑦','⑧','⑨','⑩','☐'}   # ○ 는 마스킹 자리표(20○○년)라 제외
MK_CLS={'ck','mk','mkc','opt','br'}
def has_border(e): return e['bw'] not in ('0px','')
def has_ul(e): return e['bb'] not in ('0px','') and e['bs']=='none'
def square(e,m=30): return e['w']<=m and e['h']<=m and abs(e['w']-e['h'])<=10   # 낱칸 19×26 포함

def prep(els):
    """페이지 단위 전처리: 낱칸 run 감지, 필드를 담는 td 찾기."""
    fields=[e for e in els if e['kind']=='field']
    tds=[e for e in els if e['kind'] in ('td','th')]
    # run: 같은 행(y±3), 같은 크기(±2), 인접(x 간격 ≤8) 으로 이어진 작은 박스 3개 이상
    small=[e for e in fields if square(e) and not e['text']]
    small.sort(key=lambda e:(round(e['y']),e['x']))
    for e in fields: e['run']=1; e['td']=None
    i=0
    while i<len(small):
        j=i; grp=[small[i]]
        while j+1<len(small) and abs(small[j+1]['y']-small[j]['y'])<=3 and abs(small[j+1]['w']-small[j]['w'])<=2 and 0<=small[j+1]['x']-(small[j]['x']+small[j]['w'])<=8:
            grp.append(small[j+1]); j+=1
        for g in grp: g['run']=len(grp)
        i=j+1
    # containing td (최소 면적) + 그 td 안의 필드 수
    for e in fields:
        best=None
        for t in tds:
            if t['x']-1<=e['x'] and t['y']-1<=e['y'] and e['x']+e['w']<=t['x']+t['w']+1 and e['y']+e['h']<=t['y']+t['h']+1:
                if best is None or t['w']*t['h']<best['w']*best['h']: best=t
        e['td']=best
    cnt=collections.Counter(id(e['td']) for e in fields if e['td'])
    for e in fields: e['td_n']=cnt[id(e['td'])] if e['td'] else 0
    return fields

def classify(e):
    """우선순위 순. 반환 (클래스, 규칙 번호)."""
    f,cls,tag,txt=e['f'],set(e['cls'].split()),e['tag'],e['text']
    if f=='image': return 'photo','R1 image 타입'
    if cls & MK_CLS: return 'marker','R2 마커 class(ck·mk·mkc·opt·br)'
    if txt in GLY: return 'marker','R3 글리프 텍스트(□ [ ] ( ) ①…)'
    if f=='signature' and txt: return 'signature','R4 signature + 문구/직인'
    if f=='radio' and re.fullmatch(r'[가-힣A-Za-z]{1,4}',txt or ''): return 'word','R5 radio + 인쇄 단어'
    if 'ul' in cls or 'ulx' in cls or has_ul(e): return 'underline','R6 밑줄(ul·ulx·border-bottom)'
    if 'circ' in cls: return 'placeholder','R6b 인쇄 원형 ○ 자리표(이름 글자 자리)'
    if has_border(e) and square(e) and not txt:
        if e['run']>=2 or f not in ('radio','checkbox'): return 'comb','R7 낱칸(테두리 정사각 run ≥2, 또는 글자 타입)'
        return 'marker','R8 테두리 빈 정사각 단독(radio/checkbox)'
    if txt: return 'placeholder','R9 인쇄 글자 포함(○○○·20__·예시·※)'
    if not has_border(e) and square(e,28) and f in ('radio','checkbox') and e['td'] is not None:
        return 'cell','R10 보이지 않는 마커 → 담는 셀(셀=선택지)'
    if tag=='div' and not e['intable'] and not has_border(e): return 'area','R11 괘선 없는 div 영역'
    if not e['intable'] and tag=='span' and not has_border(e) and not (cls & {'cg','cgf','db','dbx'}) and e['h']>48: return 'area','R11 괘선 없는 큰 span 영역'
    if 'gp' in cls: return 'gap','R12 gp'
    if not has_border(e) and not (cls & {'cg','cgf','db','dbx'}) and e['w']<=60: return 'gap','R13 표시 없는 소형 빈칸(슬롯)'
    if cls & {'cg','cgf','db','dbx'} or has_border(e) or e['intable'] or tag=='td': return 'cell','R14 셀 채움·테두리 박스·표 안 빈 요소'
    return 'gap','R15 나머지 표시 없는 빈칸'

def gt_box(e,c):
    """1단계 박스 규약: cell 은 담는 td 안쪽(td 에 필드 1개일 때). 그 외 요소 박스."""
    if c=='cell' and e['td'] is not None and e['td_n']==1 and not e['td']['text'].strip():   # 셀에 인쇄 라벨이 있으면 요소 박스 유지
        t=e['td']; return dict(x=t['x']+2,y=t['y']+2,w=t['w']-4,h=t['h']-4)
    return dict(x=e['x'],y=e['y'],w=e['w'],h=e['h'])

random.seed(11)
ex=collections.defaultdict(lambda: {'syn':[], 'rep':[]})
look=collections.defaultdict(lambda: {'syn':[], 'rep':[]})
tally={'syn':collections.Counter(),'rep':collections.Counter()}
rules=collections.defaultdict(lambda: {'syn':collections.Counter(),'rep':collections.Counter()})
for png,els in data.items():
    src='rep' if '4_replica' in png else 'syn'
    fields=prep(els)
    for e in fields:
        c,r=classify(e); e['c']=c; e['r']=r; tally[src][c]+=1; rules[c][src][r]+=1; ex[c][src].append((png,e))
    for e in els:
        t=e['text']
        if e['kind']=='th' and 8<e['w']<400 and 12<e['h']<80: look['cell'][src].append((png,e,'머리글 셀(인쇄)'))
        if e['kind']=='td' and t and not e['hasf'] and e['w']<400 and e['h']<80: look['placeholder'][src].append((png,e,'값이 인쇄된 셀')); look['cell'][src].append((png,e,'인쇄 상수 셀'))
        if e['kind']=='prose' and t.startswith('□'): look['marker'][src].append((png,e,'인쇄 □ 글머리'))
        if e['kind']=='prose' and '귀하' in t: look['signature'][src].append((png,e,'인쇄 수신처'))
        if e['kind']=='prose' and 20<len(t)<80 and not e['hasf'] and e['h']<40: look['gap'][src].append((png,e,'입력 없는 문장'))
        if e['kind']=='prose' and re.search(r'\d',t) and not e['hasf'] and e['h']<40: look['underline'][src].append((png,e,'숫자 인쇄 줄'))
        if e['kind']=='td' and t and not e['hasf'] and 60<e['w']<160 and 60<e['h']<200: look['photo'][src].append((png,e,'큰 인쇄 셀'))
        if e['kind']=='prose' and re.search(r'[가-힣]{1,3}(/|·|,)\s*[가-힣]{1,3}',t) and e['h']<40: look['word'][src].append((png,e,'인쇄 단어 나열'))
        if e['kind']=='th' and e['w']<40 and e['h']<40: look['comb'][src].append((png,e,'작은 머리글 셀'))
        if e['kind']=='prose' and t.startswith('□'): look['comb'][src].append((png,e,'인쇄 □ 글머리'))

imgcache={}
def crop(png,box,mx=90,my=34,maxw=470):
    im=imgcache.get(png) or Image.open(png).convert('RGB'); imgcache[png]=im
    W,Hh=im.size; x,y,w,h=box['x'],box['y'],box['w'],box['h']
    x0=max(0,x-mx); x1=min(W,x+w+mx); y0=max(0,y-my); y1=min(Hh,y+h+my)
    if x1-x0>maxw: cx=x+w/2; x0=max(0,cx-maxw/2); x1=min(W,x0+maxw); x0=max(0,x1-maxw)
    c=im.crop((int(x0),int(y0),int(x1),int(y1)))
    if c.width>maxw: c=c.resize((maxw,int(c.height*maxw/c.width)))
    b=io.BytesIO(); c.save(b,'PNG',optimize=True)
    ov=dict(l=100*(x-x0)/(x1-x0), t=100*(y-y0)/(y1-y0), w=100*w/(x1-x0), h=100*h/(y1-y0))
    return base64.b64encode(b.getvalue()).decode(), ov, c.width, c.height
def pick(items,n,key):
    random.shuffle(items); seen_page=set(); seen_key=collections.Counter(); out=[]
    items.sort(key=lambda it: seen_key[key(it)])
    for it in items:
        k=key(it)
        if it[0] in seen_page or seen_key[k]>=max(1,n//3): continue
        seen_page.add(it[0]); seen_key[k]+=1; out.append(it)
        if len(out)>=n: break
    return out
def fig(png,e,label,box=None,extra=''):
    box=box or dict(x=e['x'],y=e['y'],w=e['w'],h=e['h'])
    b64,ov,cw,ch=crop(png,box); page=os.path.basename(png)[:-4]
    return (f'<figure><div class="im" style="width:{cw}px;max-width:100%"><img src="data:image/png;base64,{b64}" width="{cw}" height="{ch}" alt="">'
            f'<i class="gt" style="left:{ov["l"]:.2f}%;top:{ov["t"]:.2f}%;width:{ov["w"]:.2f}%;height:{ov["h"]:.2f}%"></i></div>'
            f'<figcaption>{H.escape(label)} · {H.escape(page[:26])} · {box["w"]:.0f}×{box["h"]:.0f}px{extra}</figcaption></figure>')

CLS=[
 ('marker','marker · 마커','□ [ ] ( ) ①②③ 같은 22px 안팎 글리프, 또는 테두리가 있는 빈 정사각 하나. 체크 표시가 앉을 자리.','글리프(또는 박스) 자체. 생성기 18~26px, 실서식 14~22px.',
  [('K1','충족','글리프·소형 정사각. checkbox/radio 는 같은 모양이라 합침. 낱칸(comb)과는 "연속 run 여부"로 갈림'),('K2','충족','글리프 박스 단일 규약'),('K3','대체로 충족','인쇄 □ 글머리("□ 지원동기")만 혼동 후보'),('K4','충족','합성 6% · 실서식 21%'),('K5','충족','2단계는 radio/checkbox 판별만')]),
 ('comb','comb · 낱칸','주민번호·우편번호·날짜처럼 글자 한 자씩 넣는 테두리 정사각이 3개 이상 이어진 것.','낱칸 하나하나. 이어진 run 전체가 아니라 개별 칸.',
  [('K1','충족','마커와 같은 크기지만 3개 이상 같은 크기로 붙어 있음. 사양이 "체크박스 오검출 최고 위험"으로 적은 바로 그 구분'),('K2','충족','칸 단위'),('K3','충족','인쇄물 중 같은 모양 없음(작은 머리글 셀 정도)'),('K4','약함','합성 0.7% · 실서식 3% → comb_slot 가중치 상향'),('K5','충족','2단계 없이 "자릿수 입력"으로 확정 가능')]),
 ('cell','cell · 괘선 빈 영역','실선·점선·굵은선으로 둘러싸인 비어 있는 영역. 표 칸, 점선 박스, 선택지 셀(마커가 보이지 않는 척도표 칸 포함).','담는 셀의 안쪽 영역(셀에 입력이 하나뿐이고 인쇄 글자가 없을 때). 셀 안에 라벨이 인쇄돼 있으면 빈 부분만(요소 박스). 예시의 붉은 박스는 이 규약을 적용한 것.',
  [('K1','충족','괘선이 경계'),('K2','위반 → 수정','원 GT는 cg 26px 고정 vs cgf 인셋. 셀 안쪽으로 통일(예시에 적용됨)'),('K3','조건부 충족','"비어 있다"가 핵심. 머리글·값 인쇄 셀은 배경. 사진 칸·인쇄 안내문 셀은 여기서 뺌'),('K4','충족','합성 75% · 실서식 40% (합성 과다)'),('K5','충족','치수 분포 실패가 여기 집중')]),
 ('gap','gap · 투명 빈칸','글줄 속에 아무 표시 없이 비어 있는 자리. "위 사람은 ___", 년·월·일 조각, 괄호 안, 표 안의 표시 없는 소형 슬롯.','요소 박스.',
  [('K1','충족','선도 글자도 테두리도 없음'),('K2','충족',''),('K3','약함','문장 사이 공백과 같은 재질. 앞 라벨·좌우 글자 배치가 유일한 단서'),('K4','충족','합성 10% · 실서식 25%'),('K5','충족','실서식 실패의 큰 몫')]),
 ('underline','underline · 밑줄','글줄 속 가로선 위 빈 자리.','선을 포함한 박스, 높이 1em.',
  [('K1','충족','선'),('K2','충족',''),('K3','충족','서식에 인쇄 밑줄은 드묾. 표 괘선과는 길이·위치'),('K4','약함','합성 0.7% · 실서식 2.5%'),('K5','충족','')]),
 ('placeholder','placeholder · 인쇄 자리표','덮어쓸 인쇄 글자가 들어 있는 입력. ○○○ · 20__ · 예시문 · "※ 안내"가 든 셀 · 이름 글자 자리의 원형 ○.','인쇄물을 포함한 전체 영역.',
  [('K1','충족','gap 과는 글리프 유무, cell 과는 내용 유무'),('K2','충족',''),('K3','약함','인쇄 글자와 같은 재질. ○○○·__·예)·※ 같은 고정 글리프가 대비'),('K4','충족','합성 1.2% · 실서식 6%'),('K5','충족','2단계가 "덮어쓰기"를 알아야 함')]),
 ('signature','signature · 서명 문구','(인) · (서명 또는 인) · (직인) 문구 자체, 붉은 직인 박스, 도장 칸.','문구 전체 박스. 서명용 빈 셀·점선 박스·밑줄은 여기가 아니라 cell·underline (모양 기준).',
  [('K1','충족','괄호 문구·붉은 박스'),('K2','충족',''),('K3','충족','고정 문구. 인쇄 수신처("귀하")가 혼동 후보'),('K4','충족','합성 1.3% · 실서식 4%'),('K5','충족','1단계 라벨이 곧 최종')]),
 ('photo','photo · 사진 칸','"사 진 (3.5×4.5cm)" 인쇄가 든 세로 직사각 박스, 원형 변형.','박스 전체.',
  [('K1','충족','고정 문구 + 3.5:4.5 비율'),('K2','충족',''),('K3','충족','cell 에 합치면 cell 의 "비어 있음" 정의가 깨짐'),('K4','위반 → 수정','합성 0.1% · 실서식 0.5% → img_cell·img_card 가중치'),('K5','충족','라벨이 곧 최종(image)')]),
 ('word','word · 글자 택일 (1단계 제외 → 2단계)','"여 / 남", "유 / 무", "am / pm"처럼 인쇄 단어 자체가 선택지.','단어 글리프 박스.',
  [('K1','충족',''),('K2','충족',''),('K3','위반','인쇄 단어와 픽셀이 같음'),('K4','약함','합성 2%(radio 의 대부분) · 실서식 3%'),('K5','약함','2단계가 OCR 로 단어를 쪼갬')]),
 ('area','area · 괘선 없는 영역 (1단계 제외 → 구조 후보)','○ 글머리 뒤 큰 빈 블록. 경계 표시 없음.','블록 박스.',
  [('K1','위반','배경과 같음'),('K2','충족',''),('K3','위반',''),('K4','약함','합성 0.4%'),('K5','—','문단 사이 빈 블록을 구조에서 뽑음')]),
]
V={'충족':'ok','대체로 충족':'ok','조건부 충족':'wn','약함':'wn','위반 → 수정':'wn','위반':'bad','—':'mu'}
sec=[]
for key,name,defi,conv,ks in CLS:
    ks_html=''.join(f'<tr><td class="k">{k}</td><td><span class="chip {V[v]}">{v}</span></td><td>{H.escape(t)}</td></tr>' for k,v,t in ks)
    kf=lambda it: (it[1]['r'], round(it[1]['w']/60), round(it[1]['h']/20))
    figs_s=''.join(fig(p,e,'합성',gt_box(e,key),' · '+e['r'].split()[0]) for p,e in pick(ex[key]['syn'],4,kf))
    figs_r=''.join(fig(p,e,'실서식',gt_box(e,key),' · '+e['r'].split()[0]) for p,e in pick(ex[key]['rep'],4,kf))
    lk=pick(look[key]['syn'],2,lambda it:it[2])+pick(look[key]['rep'],2,lambda it:it[2])
    figs_l=''.join(fig(p,e,lb) for p,e,lb in lk)
    rl=sorted(set(rules[key]['syn'])|set(rules[key]['rep']), key=lambda r:-(rules[key]['syn'][r]+rules[key]['rep'][r]))
    rl_html=''.join(f'<tr><td class="k">{H.escape(r)}</td><td class="n">{rules[key]["syn"][r]}</td><td class="n">{rules[key]["rep"][r]}</td></tr>' for r in rl)
    n_s,n_r=tally['syn'][key],tally['rep'][key]
    sec.append(f'''<section id="{key}"><h2>{H.escape(name)}</h2>
<div class="def"><p><b>정의</b> {H.escape(defi)}</p><p><b>박스 규약</b> {H.escape(conv)}</p><p><b>표본</b> 합성 70장 {n_s}개 · 실서식 44장 {n_r}개</p></div>
<div class="two"><table class="kt"><tr><th>기준</th><th>판정</th><th>근거</th></tr>{ks_html}</table>
<table class="kt"><tr><th>배정 규칙</th><th class="n">합성</th><th class="n">실서식</th></tr>{rl_html}</table></div>
<h3>예시 — 붉은 박스가 1단계 정답 범위 · 캡션 끝은 적용된 규칙</h3><div class="grid">{figs_s}{figs_r}</div>
<h3>혼동 후보 (K3) — 입력이 아닌 것. 붉은 박스는 그 요소의 범위</h3><div class="grid lk">{figs_l or "<p class=mu>해당 없음</p>"}</div>
<div class="rv"><b>검토</b> <label><input type="radio" name="rv-{key}" value="동의">동의</label><label><input type="radio" name="rv-{key}" value="보류">보류</label><label><input type="radio" name="rv-{key}" value="이의">이의</label> <input class="memo" data-k="{key}" placeholder="메모"></div>
</section>''')
RULES=[('R1','data-f=image','photo'),('R2','class 가 ck·mk·mkc·opt·br','marker'),('R3','텍스트가 □ [ ] ( ) ①~⑩','marker'),('R4','data-f=signature 이고 문구/직인 텍스트 있음','signature'),('R5','data-f=radio 이고 텍스트가 인쇄 단어(여·남·am…)','word (제외)'),('R6','class ul·ulx 또는 border-bottom 만 있음','underline'),('R6b','원형 테두리 ○ (이름 글자 자리표, 사용자 확정)','placeholder'),('R7','테두리 있는 빈 정사각(≤30px)이 2개 이상 연속이거나(월·일 2자리), 타입이 radio/checkbox 가 아님','comb'),('R8','테두리 있는 빈 정사각 단독, 타입 radio/checkbox','marker'),('R9','그 외 텍스트 있음(○○○·20·예시·※)','placeholder'),('R10','테두리 없는 빈 정사각(≤28px) radio/checkbox 가 표 안 → 담는 셀로 승격','cell'),('R11','테두리 없는 div 또는 높이 48px 초과 span, 표 밖','area (제외)'),('R12','class gp','gap'),('R13','테두리·채움 class 없고 폭 ≤60px','gap'),('R14','class cg·cgf·db·dbx, 테두리 있음, 또는 표 안','cell'),('R15','나머지','gap')]
rules_html=''.join(f'<tr><td class="k">{a}</td><td>{H.escape(b)}</td><td>{c}</td></tr>' for a,b,c in RULES)
page=f'''<title>1단계 클래스 검토판</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Noto+Serif+KR:wght@700&family=Noto+Sans+KR:wght@400;500;700&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
:root{{--paper:#F6F7F5;--ink:#1A1D21;--ink2:#4A525C;--mu:#6F7884;--rule:#C9CFD8;--shade:#EEF1F4;--acc:#2C4C8C;--acc2:#24407A;--bad:#B3372E;--badbg:#F8E7E5;--ok:#1F7A4D;--okbg:#E4F2EA;--wn:#A8701A;--wnbg:#F7EEDB;--gt:#D8322A}}
@media (prefers-color-scheme:dark){{:root:not([data-theme=light]){{--paper:#15181C;--ink:#E7E9EC;--ink2:#C0C6CE;--mu:#9AA3AF;--rule:#2E343C;--shade:#1D2126;--acc:#7FA2E8;--acc2:#A9C1F0;--bad:#E06A5F;--badbg:#3A2320;--ok:#5CC48E;--okbg:#1B3327;--wn:#D9A24C;--wnbg:#3A2E18;--gt:#FF6B5E}}}}
:root[data-theme=dark]{{--paper:#15181C;--ink:#E7E9EC;--ink2:#C0C6CE;--mu:#9AA3AF;--rule:#2E343C;--shade:#1D2126;--acc:#7FA2E8;--acc2:#A9C1F0;--bad:#E06A5F;--badbg:#3A2320;--ok:#5CC48E;--okbg:#1B3327;--wn:#D9A24C;--wnbg:#3A2E18;--gt:#FF6B5E}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--paper);color:var(--ink);font-family:"Noto Sans KR",system-ui,sans-serif;font-size:14.5px;line-height:1.7}}
.page{{max-width:1040px;margin:0 auto;padding:40px 24px 80px}}
h1,h2,h3{{font-family:"Noto Serif KR",serif;font-weight:700;margin:0;text-wrap:balance}}h1{{font-size:30px}}h2{{font-size:21px;margin-top:56px;padding-top:12px;border-top:3px double var(--mu)}}h3{{font-size:14.5px;color:var(--acc2);margin:22px 0 8px}}
p{{margin:8px 0;max-width:76ch}}.mu{{color:var(--mu)}}
.eyebrow{{font-family:"IBM Plex Mono",monospace;font-size:12px;letter-spacing:.08em;text-transform:uppercase;color:var(--mu);margin-bottom:8px}}
.lede{{font-size:16px;max-width:70ch}}
.bar{{position:sticky;top:0;z-index:5;background:var(--paper);border-bottom:1px solid var(--rule);padding:8px 0;margin:18px 0;display:flex;gap:14px;align-items:center;flex-wrap:wrap;font-size:13px}}
.bar a{{color:var(--acc2);text-decoration:none}}.bar label{{cursor:pointer}}
.bar button{{font:inherit;font-size:12.5px;padding:3px 10px;border:1px solid var(--acc);background:transparent;color:var(--acc2);border-radius:3px;cursor:pointer}}
table{{border-collapse:collapse;font-size:13px;margin:10px 0;width:100%}}th,td{{border:1px solid var(--rule);padding:5px 9px;text-align:left;vertical-align:top}}th{{background:var(--shade);font-weight:500;color:var(--ink2)}}
td.k{{font-family:"IBM Plex Mono",monospace;white-space:nowrap;font-size:12px}}td.n,th.n{{text-align:right;font-family:"IBM Plex Mono",monospace;white-space:nowrap}}
.two{{display:grid;grid-template-columns:3fr 2fr;gap:14px;align-items:start}}@media(max-width:760px){{.two{{grid-template-columns:1fr}}}}
.chip{{display:inline-block;font-family:"IBM Plex Mono",monospace;font-size:11.5px;padding:1px 8px;border-radius:2px;white-space:nowrap}}.ok{{background:var(--okbg);color:var(--ok)}}.wn{{background:var(--wnbg);color:var(--wn)}}.bad{{background:var(--badbg);color:var(--bad)}}.mu.chip{{background:var(--shade);color:var(--mu)}}
.def{{background:var(--shade);border:1px solid var(--rule);padding:8px 14px;margin:10px 0}}.def p{{margin:4px 0}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:12px}}
figure{{margin:0;border:1px solid var(--rule);background:#fff;padding:6px}}
.im{{position:relative;overflow:hidden}}.im img{{display:block;max-width:100%;height:auto}}
.gt{{position:absolute;border:2px solid var(--gt);box-shadow:0 0 0 1px #fff;pointer-events:none}}body.nogt .gt{{display:none}}
.lk figure{{border-style:dashed}}
figcaption{{font-size:11.5px;color:var(--mu);margin-top:4px;font-family:"IBM Plex Mono",monospace;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}
.rv{{margin:14px 0 0;padding:8px 12px;border:1px solid var(--rule);font-size:13px;display:flex;gap:14px;align-items:center;flex-wrap:wrap}}.rv label{{cursor:pointer}}.memo{{flex:1;min-width:200px;font:inherit;padding:3px 8px;border:1px solid var(--rule);background:var(--paper);color:var(--ink)}}
.crit{{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:8px;margin:14px 0}}.crit div{{border:1px solid var(--rule);padding:8px 10px;font-size:13px;background:var(--shade)}}.crit b{{font-family:"IBM Plex Mono",monospace;color:var(--acc2);display:block}}
.sum{{display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:6px;margin:14px 0;font-size:12.5px}}.sum div{{border:1px solid var(--rule);padding:6px 8px}}.sum b{{display:block;font-family:"IBM Plex Mono",monospace;font-size:12px}}
.chg{{border-left:3px solid var(--wn);padding:6px 14px;margin:14px 0;font-size:13.5px;max-width:80ch}}
</style>
<div class="page">
<div class="eyebrow">form-model · 1단계 검출기 클래스 · 검토판 v9</div>
<h1>1단계 클래스 검토판</h1>
<p class="lede">검출기가 맡을 8종 클래스(그리고 제외한 2종)를 다섯 기준으로 판정한 근거와, 학습 이미지·실서식 복제에서 잘라낸 예시입니다. 붉은 박스는 <b>1단계 박스 규약을 적용한 정답 범위</b>이고, 캡션 끝의 R번호는 그 예시에 적용된 배정 규칙입니다. 점선 테두리 그림은 입력이 아닌 혼동 후보입니다.</p>
<div class="chg"><b>v9</b> · cell 박스 규약 보정: 셀에 라벨이 인쇄된 경우(접수번호·접수일 등) 셀 안쪽이 아니라 빈 부분만 박스. · 복제본 정정 2건(5_2호 자국어 빈칸 폭, 2편 21호 지정기간 빈칸 폭).</div>
<div class="chg"><b>v8</b> · 4_replica/lint.py(규약 검사 8항목) 도입, 44장 위반 0(경고 1). · 낱칸 run 기준 3→2개(월·일 2자리 낱칸). · 2편 21호의 6px 퇴화 gap 수정.</div>
<div class="chg"><b>v7</b> · 실서식 placeholder 63건 전수 판정: "20 년"의 인쇄 20 을 필드 박스에 넣은 23건(17쪽)이 생성기 규약(20 은 밖, 빈칸만 필드)과 어긋나 복제본을 정정 → gap. 나머지 40건(○○○·△△△ 마스킹, 20○○년의 ○, 예시문, 원형 ○, 인쇄 예시 전화번호)은 자리표가 맞음.</div>
<div class="chg"><b>v6</b> · 서식8호 접수증의 깨진 span 태그(접수번호 셀이 "40시간( ) 20시간( )" 문단을 통째로 감쌈)를 복구. 그 192×44 placeholder 는 라벨 오류였고, 괄호 안 빈칸 2개는 gap, 택일이라 radio 로. 44장 전수에서 중첩 data-f 는 이 건뿐.</div>
<div class="chg"><b>v5</b> · 신분증의 원형 ○ 3개는 이름 글자 자리표로 확정(사용자) → 복제본 라벨 image→text 정정, R6b 추가로 placeholder. · 낱칸 19×26 이 정사각 판정에서 빠지던 것 수정(허용 차 6→10px).</div>
<div class="chg"><b>v3</b> · 날짜 마스킹 자리표 "20○○년"의 ○ 가 글리프 마커로 가던 것을 placeholder 로 수정(R3 글리프 목록에서 ○ 제외). · 하이픈으로 끊긴 낱칸이 marker 로 가던 것을 comb 으로(R7 에 타입 조건 추가).</div>
<div class="chg"><b>v1에서 고친 것</b> · 주민번호·우편번호 낱칸이 cell로 가던 것을 <b>comb</b> 클래스로 분리(테두리 정사각 3개 이상 연속). · 척도표·요일표의 <b>보이지 않는 마커</b>(빈 22px, 테두리 없음)는 담는 셀로 승격해 cell로. · 서명용 <b>빈 셀·점선 박스·밑줄</b>은 signature가 아니라 모양대로 cell·underline. · cell 박스를 <b>셀 안쪽 영역</b>으로 통일해 표시(셀에 입력이 하나일 때). · 예시를 배정 규칙별로 고르게 뽑고 규칙 번호를 표기.</div>
<div class="crit">
<div><b>K1 분리 가능</b>두 클래스가 주변 픽셀만으로 갈리는가. 글을 읽어야 갈리면 합친다</div>
<div><b>K2 박스 규약 동질</b>한 클래스 안에서 박스 범위 규칙이 하나인가</div>
<div><b>K3 배경과 대비</b>입력 아닌 인쇄물과 픽셀로 구분되는가</div>
<div><b>K4 표본 충분</b>학습에 수천, 실서식에 존재하는가</div>
<div><b>K5 하류 유용</b>나누면 2단계나 평가에 이득이 있는가</div>
</div>
<h3>배정 규칙 (위에서부터 먼저 맞는 것 하나)</h3>
<table><tr><th>규칙</th><th>조건</th><th>클래스</th></tr>{rules_html}</table>
<div class="sum">{''.join(f'<div><b>{k}</b>합성 {tally["syn"][k]} · 실서식 {tally["rep"][k]}</div>' for k,*_ in CLS)}</div>
<div class="bar"><label><input type="checkbox" id="tg" checked> 정답 박스 표시</label>{''.join(f'<a href="#{k}">{k}</a>' for k,*_ in CLS)}<button id="cp">검토 결과 복사</button><span id="cpmsg" class="mu"></span></div>
{''.join(sec)}
<p class="mu" style="margin-top:40px;font-size:12.5px">표본: 합성은 5_dataset/train 무작위 70장, 실서식은 4_replica 44장 전부. 배정은 위 규칙표를 그대로 코드로 옮긴 것이며 1단계 라벨 변환기가 됩니다. 검토 선택은 이 브라우저에만 저장됩니다.</p>
</div>
<script>
(function(){{
 var tg=document.getElementById('tg'); tg.addEventListener('change',function(){{document.body.classList.toggle('nogt',!tg.checked)}});
 var K={json.dumps([k for k,*_ in CLS])};
 function load(){{try{{var s=JSON.parse(localStorage.getItem('cls-review')||'{{}}');K.forEach(function(k){{if(s[k]&&s[k].v){{var r=document.querySelector('input[name=rv-'+k+'][value="'+s[k].v+'"]');if(r)r.checked=true}} if(s[k]&&s[k].m){{document.querySelector('.memo[data-k='+k+']').value=s[k].m}}}})}}catch(e){{}}}}
 function save(){{try{{var s={{}};K.forEach(function(k){{var r=document.querySelector('input[name=rv-'+k+']:checked');s[k]={{v:r?r.value:'',m:document.querySelector('.memo[data-k='+k+']').value}}}});localStorage.setItem('cls-review',JSON.stringify(s))}}catch(e){{}}}}
 document.addEventListener('change',save);document.addEventListener('input',save);load();
 document.getElementById('cp').addEventListener('click',function(){{var out=K.map(function(k){{var r=document.querySelector('input[name=rv-'+k+']:checked');var m=document.querySelector('.memo[data-k='+k+']').value;return k+': '+(r?r.value:'(미검토)')+(m?' — '+m:'')}}).join('\\n');
   (navigator.clipboard?navigator.clipboard.writeText(out):Promise.reject()).then(function(){{document.getElementById('cpmsg').textContent='복사됨'}},function(){{prompt('복사해 주세요',out)}})}});
}})();
</script>'''
open(f'{OUT}/cls-review.html','w').write(page)
print('bytes',len(page)); print('syn',dict(tally['syn'])); print('rep',dict(tally['rep']))
for k,*_ in CLS:
    print(k, dict(rules[k]['syn']), dict(rules[k]['rep']))
