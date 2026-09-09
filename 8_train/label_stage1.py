"""1단계(생김새 8종) 라벨 부여 + 커버리지 격자 — 렌더 없이 HTML 마크업 + _gt.json 으로.

클래스: marker comb cell gap underline placeholder signature photo (+ 제외: word area)
규칙은 검토판 R1~R15 와 같되, 계산된 스타일 대신 마크업(class·style·tag·텍스트)과 GT 크기를 쓴다.
요소 순서 = _gt.json 순서(querySelectorAll 문서 순서)이므로 i번째 태그 = i번째 박스.

사용:
  python 8_train/label_stage1.py --train 5_dataset/train --replica 4_replica --coverage     # 격자 보고
  python 8_train/label_stage1.py --train 5_dataset/train --out 8_train/s1_labels.jsonl        # 페이지별 라벨 덤프
"""
import argparse, glob, json, os, re, collections, sys

CLASSES=["marker","comb","cell","gap","underline","placeholder","signature","photo"]
GLY=re.compile(r'^(□|☐|\[\s*\]|\(\s*\)|[①-⑩])$')
WORD=re.compile(r'^[가-힣A-Za-z]{1,4}$')
TAG=re.compile(r'<(/?)(\w+)([^>]*)>')
ATTR=lambda a,k: (re.search(k+r'="([^"]*)"',a) or re.search(k+r"='([^']*)'",a))

def fields_from_html(html):
    """data-f 요소를 문서 순서대로: (tag, f, cls, style, text, intable)"""
    out=[]; td_depth=0; tbl_depth=0; open_stack=[]
    pos=0
    for m in TAG.finditer(html):
        close,tag,attrs=m.group(1),m.group(2).lower(),m.group(3)
        if tag=='table': tbl_depth+= -1 if close else 1
        if tag in('td','th'): td_depth+= -1 if close else 1
        if close or tag in ('br','img','col','meta','link','input'): continue
        df=ATTR(attrs,'data-f')
        if not df: continue
        # 텍스트: 여는 태그 뒤부터 같은 태그의 닫힘까지(중첩 span 1단계 허용)
        rest=html[m.end():]
        endm=re.search(r'</'+tag+r'\s*>', rest); inner=rest[:endm.start()] if endm else ''
        if tag=='span':   # <span data-f><span class=note>..</span></span> 형태면 두 번째 닫힘까지
            opens=len(re.findall(r'<span\b',inner))
            if opens>=1 and endm:
                m2=list(re.finditer(r'</span\s*>', rest))
                if len(m2)>opens: inner=rest[:m2[opens].start()]
        text=re.sub(r'<[^>]+>',' ',inner).replace('&nbsp;',' '); text=re.sub(r'\s+',' ',text).strip()
        out.append(dict(tag=tag,f=df.group(1),cls=(ATTR(attrs,'class') or [None,''])[1] if ATTR(attrs,'class') else '',
                        style=(ATTR(attrs,'style').group(1) if ATTR(attrs,'style') else ''),text=text,intable=tbl_depth>0 and td_depth>0))
    return out

def has_border(e): return bool(re.search(r'(^|;)\s*border\s*:', e['style'])) or e['cls'] in ('db','dbx','circ','mk','stamp') or e['tag']=='i'
def has_ul(e): return 'border-bottom' in e['style'] or e['cls'] in ('ul','ulx')

def classify_page(fields, boxes):
    n=min(len(fields),len(boxes)); res=[]
    # 낱칸 run: 테두리·소형·빈 박스가 같은 행에 같은 크기로 인접
    small=[i for i in range(n) if has_border(fields[i]) and boxes[i]['w']<=30 and boxes[i]['h']<=30 and abs(boxes[i]['w']-boxes[i]['h'])<=10 and not fields[i]['text']]
    small.sort(key=lambda i:(round(boxes[i]['y']),boxes[i]['x'])); run={}
    k=0
    while k<len(small):
        j=k
        while j+1<len(small) and abs(boxes[small[j+1]]['y']-boxes[small[j]]['y'])<=3 and abs(boxes[small[j+1]]['w']-boxes[small[j]]['w'])<=2 and 0<=boxes[small[j+1]]['x']-(boxes[small[j]]['x']+boxes[small[j]]['w'])<=8: j+=1
        for q in range(k,j+1): run[small[q]]=j-k+1
        k=j+1
    for i in range(n):
        e=fields[i]; b=boxes[i]; f=e['f']; cls=set(e['cls'].split()); txt=e['text']; w,h=b['w'],b['h']
        if f=='image': c='photo'
        elif e['tag']=='i': c='comb'
        elif cls & {'ck','mk','mkc','opt','br'}: c='marker'
        elif GLY.match(txt): c='marker'
        elif f=='signature' and txt: c='signature'
        elif f=='radio' and WORD.match(txt): c='word'
        elif has_ul(e): c='underline'
        elif 'circ' in cls: c='placeholder'
        elif has_border(e) and w<=30 and h<=30 and abs(w-h)<=10 and not txt:
            c='comb' if (run.get(i,1)>=2 or f not in ('radio','checkbox')) else 'marker'
        elif txt: c='placeholder'
        elif not has_border(e) and w<=28 and h<=28 and abs(w-h)<=4 and f in ('radio','checkbox') and e['intable']: c='cell'
        elif e['tag']=='div' and not e['intable'] and not has_border(e): c='area'
        elif not e['intable'] and e['tag']=='span' and not has_border(e) and not (cls & {'cg','cgf','db','dbx'}) and h>48: c='area'
        elif 'gp' in cls: c='gap'
        elif not has_border(e) and not (cls & {'cg','cgf','db','dbx'}) and w<=60: c='gap'
        elif (cls & {'cg','cgf','db','dbx'}) or has_border(e) or e['intable'] or e['tag']=='td': c='cell'
        else: c='gap'
        res.append(c)
    return res

WB=[30,60,120,200,400]; HB=[20,30,45,70]
def bucket(v,edges):
    for i,t in enumerate(edges):
        if v<=t: return f"≤{t}"
    return f">{edges[-1]}"

def scan(html_dir, gt_dir=None, limit=None):
    """(page, fields, boxes, classes) 제너레이터"""
    files=sorted(glob.glob(os.path.join(html_dir,'*.html')))[:limit]
    for f in files:
        stem=os.path.basename(f)[:-5]; g=os.path.join(gt_dir or html_dir, stem+'_gt.json')
        if not os.path.exists(g): continue
        boxes=json.load(open(g)); fields=fields_from_html(open(f,encoding='utf-8').read())
        if len(fields)!=len(boxes): print(f"[순서 불일치] {stem}: html {len(fields)} vs gt {len(boxes)}", file=sys.stderr); continue
        yield stem, fields, boxes, classify_page(fields, boxes)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--train', default='5_dataset/train'); ap.add_argument('--replica', default='4_replica')
    ap.add_argument('--limit', type=int); ap.add_argument('--coverage', action='store_true'); ap.add_argument('--out')
    ap.add_argument('--min', type=int, default=200, help='학습에서 이 수 미만이면 "비어 있음"')
    a=ap.parse_args()
    grids={'train':collections.Counter(),'replica':collections.Counter()}; share={'train':collections.Counter(),'replica':collections.Counter()}
    dens={'train':[], 'replica':[]}; outf=open(a.out,'w') if a.out else None
    for name,hd,gd in (('train',a.train,None),('replica',os.path.join(a.replica,'html'),os.path.join(a.replica,'render'))):
        for stem,fields,boxes,cls in scan(hd,gd,a.limit if name=='train' else None):
            dens[name].append(sum(1 for c in cls if c in CLASSES))
            for e,b,c in zip(fields,boxes,cls):
                share[name][c]+=1
                if c in CLASSES: grids[name][(c,bucket(b['w'],WB),bucket(b['h'],HB),'표' if e['intable'] else '글줄')]+=1
            if outf: outf.write(json.dumps(dict(page=stem,cls=cls,types=[e['f'] for e in fields]),ensure_ascii=False)+'\n')
    for name in ('train','replica'):
        tot=sum(share[name].values()); print(f"\n== {name}: 필드 {tot} · 페이지 {len(dens[name])} · 페이지당 중앙값 {sorted(dens[name])[len(dens[name])//2] if dens[name] else 0}")
        print('  '+' · '.join(f"{c} {100*share[name][c]/tot:.1f}%" for c in CLASSES+['word','area'] if share[name][c]))
    if a.coverage:
        print(f"\n== 커버리지 격자: 실서식에 있는데 학습에 {a.min}개 미만인 칸 (클래스, 폭, 높이, 문맥 : 실서식 / 학습)")
        rows=[(k, grids['replica'][k], grids['train'][k]) for k in grids['replica'] if grids['train'][k]<a.min]
        for k,r,t in sorted(rows, key=lambda x:(x[0][0],-x[1])): print(f"  {k[0]:11s} w{k[1]:5s} h{k[2]:5s} {k[3]}  : {r:4d} / {t}")
        print(f"\n== 학습 분포 상위 (클래스, 폭, 높이, 문맥 : 학습 / 실서식)")
        for k,t in grids['train'].most_common(14): print(f"  {k[0]:11s} w{k[1]:5s} h{k[2]:5s} {k[3]}  : {t:6d} / {grids['replica'][k]}")

if __name__=='__main__': main()
