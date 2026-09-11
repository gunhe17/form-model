"""골격 JSON → HWP 테마 페이지 렌더러 v0.5 + data-f 정답 좌표.
라벨링 규약 v1.2: 마커=체크 크기만 / 서명줄=이름(text)+문구(signature) 분리.
  python 3_generator/render_skeleton.py <골격.json ...> --out 5_dataset/render_check

v4(2026-09-11, P6-2 "변동 폭"): 테마 축 전부 연속 · 글꼴 풀 50+ · 실코퍼스 어휘 · 비대상 방해물 ·
배율(device_scale_factor)·뷰포트 폭 · 배치 지터. 라벨 규칙(8_train/label_stage1.py)은 그대로 — 폭만 넓힌다.
"""
import json, os, sys, random, asyncio
from hwp_theme import css as hwp_css

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

def _load_fonts():
    """fonts/MANIFEST.json → 계열별 글꼴 목록 (없으면 빈 dict → 기존 5종 기본 테마)"""
    try: fs = json.load(open(os.path.join(ROOT, "fonts", "MANIFEST.json")))["fonts"]
    except Exception: return {}
    by = {}
    for f in fs:
        if os.path.exists(os.path.join(ROOT, "fonts", f["file"])): by.setdefault(f["family"], []).append(f)
    return by
FONTS = _load_fonts()
FAM_P = {"본문": {"고딕": .45, "명조": .45, "손글씨": .05, "장식": .05},     # 실서식은 고딕·명조가 사실상 전부,
         "표":   {"고딕": .60, "명조": .30, "손글씨": .05, "장식": .05},     # 손글씨·장식은 폭 확장용 소수
         "제목": {"고딕": .30, "명조": .45, "손글씨": .05, "장식": .20}}

def _load_lex():
    """2_spec/lexicon_real.json → 길이별 라벨 사전 + 문장 조각 (build_lexicon.py 산출)"""
    try: d = json.load(open(os.path.join(ROOT, "2_spec", "lexicon_real.json")))
    except Exception: return {}, []
    by = {}
    for w, _c in d["labels"]: by.setdefault(len(w), []).append(w)
    return by, [w for w, _c in d["phrases"]]
LEX_LEN, LEX_PHRASE = _load_lex()

# ── 라벨 어휘 ─────────────────────────────────────────────────────────
LEX = {
 "인적": [("성명","text"),("생년월일","date"),("연락처","phone"),("주소","text"),
         ("전자우편","email"),("성별","radio"),("나이","number"),("소속기관","text")],
 "옵션": ["자폐성장애","지적장애","뇌병변장애","시각장애","청각장애","언어장애","정서장애",
         "한부모가족","기초생활수급","차상위계층","해당없음","기타"],
 "격자헤더": ["연번","성명","생년월일","연락처","주소","신청일","선정일","활동시간","금액","비고",
            "구분","교육내용","강사","소속","수료여부"],
 "서술라벨": ["지원동기","추천사유","판단근거","특이사항","확인 내용","조치 계획","의견"],
 "제목어": ["장애아가족 양육지원사업","발달재활서비스","언어발달지원 서비스","장애아돌보미"],
 "문서어": {"신청서":"이용 신청서","동의서":"개인정보 수집·이용 동의서","계약서":"서비스 제공(이용) 계약서",
   "판단서":"추천서","통지회신":"결정 통지서","조회요청서":"범죄경력 조회 요청서","공고문":"제공기관 지정 공모",
   "증서":"수료증","확약서":"서약서","보고서":"실적 보고서","대장명부":"등록 대장","기록지":"제공 기록지",
   "계획서":"사업계획서","점검평가":"점검표","사정조사지":"이용가정 정보지","명세신고":"서비스 내용 요약서",
   "등록카드":"제공 인력 정보","접수증":"교육신청 접수증","안내문":"이용 안내문","작성요령서":"사업계획서"},
}

OPTSETS = [
 ("희망대상", ["자폐성장애","지적장애","뇌병변장애","시각장애","청각장애","언어장애","정서장애","모두"]),
 ("신청 급여", ["한부모가족지원","장애아동수당","보육료 지원","양육수당","아동수당","기초생활보장","차상위 지원","기타"]),
 ("법인성격", ["공공","비영리","민간"]),
 ("가족유형", ["일반가정","한부모가정","조손가정","다문화가정","기타"]),
 ("서비스 형태", ["기관방문형","가정방문형","혼합형"]),
 ("보호자 상황", ["결혼","사망","출산","입원","군복무","기타"]),
 ("신청 구분", ["신규","재발급","변경","분실","훼손","기타"]),
]
ALT_LABEL = {"text":["성명","보호자 성명","대상자 성명","기관명","신청인"],
 "phone":["연락처","전화번호","휴대전화","긴급 연락처","보호자 연락처"],"email":["전자우편","이메일","전자우편 주소"],
 "date":["생년월일","신청일","등록일"],"number":["나이","연령","만 나이"],"radio":["성별","장애 유무","동거 여부","수급 여부"]}
RADIO_PAIR = {"성별":("여","남"),"장애 유무":("유","무"),"동거 여부":("유","무"),"수급 여부":("유","무")}
CARD_TYPE = {"ph_cell":"phone","ph_multi":"phone","ph_pict":"phone","em_cell":"email",
 "date_cell":"date","date_split":"date","num_unit":"number","radio_word":"radio",
 "ph_lines":"phone","ul_cell":"phone","sig_cell":"text","gp_cell":"text"}
CARD_COVERS = {"dot_split":{"연락처","전자우편","전화번호"},"ph_multi":{"전화번호","연락처","휴대전화"},
 "ph_lines":{"전화번호","연락처","휴대전화"},"ul_cell":{"전화번호","연락처","휴대전화"},
 "mix_cell":{"주소","전화번호","연락처"},"ph_pict":{"문의처","전화번호","연락처"}}
CARD_LABEL = {"ph_cell":"연락처","em_cell":"전자우편","date_cell":"생년월일","date_split":"생년월일",
 "num_unit":"나이","radio_word":"성별","split_hyphen":"주민등록번호","comb_slot":"우편번호",
 "comb_jumin":"주민등록번호","comb_date":"생년월일",
 "cell_sublabel":"성명","mix_cell":"주소","text_suffix":"관계","ph_multi":"전화번호",
 "ph_pict":"문의처","dot_box":"성명","dbx_cell":"계좌번호","dot_split":"연락처","text_cell":"성명","img_cell":"성명",
 "ph_lines":"연락처","gp_cell":"접수번호","ul_cell":"전화번호","sig_cell":"성명"}
HEADER_TYPE = {"연번":"number","순번":"number","금액":"number","단가":"number","횟수":"number",
 "합계":"number","계":"number","신규":"number","연속":"number","종결":"number","교육시간":"number",
 "활동시간":"time","일자":"date","생년월일":"date","신청일":"date","선정일":"date","연락처":"phone"}
GRID_THEMES = [
 ["연번","성명","생년월일","연락처","주소","비고"],
 ["연번","교육내용","강사","소속","교육시간","비고"],
 ["연번","일자","활동시간","금액","확인","비고"],
 ["구분","신규","연속","종결","계","비고"],
 ["순번","서비스명","단가","횟수","합계","비고"],
]

THEME = {}   # 문서 테마 (R.__init__가 문서마다 샘플, 순차 렌더 전제)
def _T(k,d): return THEME.get(k,d)
_W = lambda w: max(6, int(round(w*_T("wjit",1.0))))   # v4 폭 지터 (문서 단위 연속 계수)
def SLOT(t="date",txt="",w=None):
    # 무클래스 빈 슬롯 = gap 규칙(w≤60). 배율까지 포함해 장치 픽셀 56 이하로 묶는다(label_stage1 R 유지)
    w=min(_W(w or _T("slot_w",34)), max(12,int(56/_T("dsf",1.0))))
    return (f'<span data-f="{t}" style="display:inline-flex;width:{w}px;height:{_T("slot_h",24)}px;align-items:center;'
            f'justify-content:center;font-size:{_T("ph_fs",14)}px;letter-spacing:normal">{txt}</span>')
GP = lambda t,w=64: f'<span data-f="{t}" class="gp" style="width:{_W(w)}px"></span>'
GPT = lambda t,w=16: f'<span data-f="{t}" class="gp" style="width:{_W(w)}px;margin:0"></span>'   # v3 밀착 슬롯: 글자 사이 10~20px, 여백 0 (실서식 1편 2호·17호)
def PH(t,txt,fs=None,w=None):
    """v3 인쇄 자리표: 박스 = 글자 자체(○·○○○). 폭 w 를 주면 실서식처럼 고정폭 inline-flex"""
    fs=fs or _T("ph_fs",14)
    if w: return f'<span data-f="{t}" style="display:inline-flex;width:{w}px;height:1.1em;align-items:center;justify-content:center;font-size:{fs}px;vertical-align:middle">{txt}</span>'
    return f'<span data-f="{t}" style="display:inline-block;font-size:{fs}px;line-height:1.25;vertical-align:middle">{txt}</span>'
CG = lambda t: f'<span data-f="{t}" class="cg"></span>'  # 셀 핏 입력: 셀 전폭-일정 여백
CGF = lambda t: f'<span data-f="{t}" class="cgf"></span>'  # 셀 채움 입력: 행 높이 무관 3px 균일 인셋
def TDC(t,h,cls="vl",extra=""):
    """행 높이 h 인 입력 셀 td — 높은 행(≥41)은 td 를 채우는 cgf, 낮은 행은 기존 cg"""
    if h>=41: return f'<td class="{cls} fillc" style="height:{h}px{extra}">{CGF(t)}</td>'
    return f'<td class="{cls}" style="height:{h}px{extra}">{CG(t)}</td>'
# v3: MKC 보이지 않는 22px 표식 삭제 — 픽셀 근거 없는 박스 2.1만 개가 척도표 25칸 전멸의 원인(PLAN 9절). 표 안 선택칸은 셀 전체 CGF.
DBX = lambda t,w: (f'<span data-f="{t}" class="dbx" style="display:inline-block;border:{_T("rule_th",1.4)}px dashed {_T("rule","#000")};'
    f'height:{_T("cg_h",26)}px;width:{_W(w)}px;vertical-align:middle"></span>')  # 실서식 .dbx 점선 인라인 박스
UL = lambda t,w=None: f'<span data-f="{t}" class="ul" style="width:{_W(w or _T("ul_w",90))}px"></span>'
def CBX(t="text"):   # 낱칸(comb) 하나 — 치수·선 스타일은 문서 테마 (치수는 배율 보정된 장치 픽셀 기준)
    w,h,st=_T("comb",(22,24,"solid"))
    return f'<span data-f="{t}" style="display:inline-block;width:{w}px;height:{h}px;border:{_T("comb_bw",1)}px {st} {_T("rule","#000")}"></span>'
COMB_DATE=lambda: [CBX("date")]*3+["년"]+[CBX("date")]*2+["월"]+[CBX("date")]*2+["일"]
def MK(ch, kind="checkbox"):   # 마커 v1.6: 글리프 박스 고정 + kind(택일=radio)
    m=_T("mk",22); w=m+_T("mk_bw",12) if ch.startswith("[") else m   # 대괄호는 가로로 넓음
    return (f'<span data-f="{kind}" style="display:inline-flex;width:{w}px;height:{m}px;align-items:center;'
            f'justify-content:center;vertical-align:middle;font-size:{max(12,m-7)}px;letter-spacing:normal;line-height:{m}px;position:relative;top:-2px;margin:0 3px 0 0">{ch}</span>')
def RMK(kind="radio"):
    m=_T("mk",22)
    return (f'<span data-f="{kind}" style="display:inline-flex;width:{m}px;height:{m}px;align-items:center;'
            f'justify-content:center;vertical-align:middle;font-size:{max(12,m-7)}px;letter-spacing:normal;line-height:{m}px;position:relative;top:-2px;margin:0 3px">(&nbsp;&nbsp;)</span>')

def WORD(w, kind="radio"):
    h=_T("slot_h",24)
    return (f'<span data-f="{kind}" style="display:inline-block;min-width:{h+6}px;height:{h}px;line-height:{h}px;'
            f'text-align:center;vertical-align:middle;position:relative;top:-2.5px;margin:0 2px">{w}</span>')

def ROW(*xs, j="l", style=""):
    """행 컴포넌트: 자식(텍스트·입력 원자)을 flex 세로 가운데로 같은 행 배치."""
    cls={"l":"row","c":"row c","r":"row r"}[j]
    st=f' style="{style}"' if style else ""
    return f'<div class="{cls}"{st}>'+"".join(str(x) for x in xs)+"</div>"

def kv_table(rows, hf=None):   # [(라벨,셀html)...] 2열×n, hf() = 행 높이
    out=["<table>"]
    for i in range(0,len(rows),2):
        pair=rows[i:i+2]; tr=""
        for lb,cell in pair:
            tdc="vl fillc" if 'class="cgf"' in cell else "vl"
            tr+=f'<th style="width:118px">{lb}</th><td class="{tdc}">{cell}</td>'
        if len(pair)==1:
            tr=tr.replace('<td class=','<td colspan="3" class=',1)
        out.append(f'<tr style="height:{hf()}px">{tr}</tr>' if hf else f"<tr>{tr}</tr>")
    out.append("</table>"); return "".join(out)

COLW = {"연번":0.5,"순번":0.5,"구분":0.8,"성명":0.9,"주소":2.2,"비고":0.8,"계":0.6,"확인":0.6,
        "일자":0.9,"금액":1.0,"단가":1.0,"횟수":0.7,"합계":1.0,"연락처":1.3,"교육내용":1.6,"서비스명":1.5}
def _fam(r,key):
    fams=[f for f in FAM_P[key] if FONTS.get(f)]
    return r.choices(fams,[FAM_P[key][f] for f in fams])[0] if fams else None

def sample_theme(r):
    """v4: 모든 축을 연속 구간에서 샘플 (이산 3~6값 → 균등/절단 분포). 정수 필요한 것만 반올림."""
    g=lambda v: "#%02x%02x%02x"%(v,v,v)
    dsf=round(round(r.uniform(0.8,1.3)/0.05)*0.05,2)   # 0.05 단위 양자화: 렌더 시 배율별 컨텍스트 11개로 재사용
    cw=r.randint(14,29); ch=max(16,min(30,cw+r.randint(-5,7)))   # 낱칸은 "장치 픽셀" 기준으로 뽑고 배율로 나눈다
    tfs=round(r.uniform(13,16),1)
    sh=r.randrange(0xD2,0x100) if r.random()<0.82 else 0xFF
    th={"dsf":dsf,"page_w":int(round(1004*r.uniform(0.85,1.15))),
        "mk":r.randint(16,30),"slot_w":r.randint(24,56),"slot_h":r.randint(18,30),
        "cell_h":r.randint(26,48),"lbw":r.randint(84,158),
        "ul_w":r.randint(52,175),"ul_th":round(r.uniform(0.8,2.0),2),
        "cg_h":r.randint(20,32),"row_h":r.randint(30,74),
        "comb":(round(cw/dsf,1),round(ch/dsf,1),r.choice(["solid","solid","solid","dashed","dotted"])),
        "comb_bw":round(r.uniform(0.8,1.8),2),"mk_bw":r.randint(8,16),
        "inset":round(r.uniform(1.5,6.5),1),
        "shade":g(sh),"shade2":g(min(0xFF,sh+r.randrange(3,20))),
        "outer":round(r.uniform(0.8,2.6),2),"rule_th":round(r.uniform(0.6,2.0),2),
        "title_ls":round(r.uniform(0.04,0.45),3),"title_fs":r.randint(26,40),
        "sig_off":r.randint(6,48),"ph_fs":round(r.uniform(11,16),1),
        "cell_pad":"%dpx %dpx"%(r.randint(1,5),r.randint(3,10)),
        "col_contrast":0 if r.random()<0.3 else round(r.uniform(0.2,1.2),2),
        "open":r.random()<0.35,
        "body_fs":round(r.uniform(15,18),1),"table_fs":tfs,"note_fs":round(tfs-r.uniform(0.5,2.0),1),
        "ls":round(r.uniform(-0.05,0.10),3),"lh":round(r.uniform(1.3,1.8),2),"tlh":round(r.uniform(1.2,1.6),2),
        "ink":g(r.randrange(0,0x67)),"rule":g(r.randrange(0,0x67)),"bg":g(r.randrange(0xF2,0x100)),
        "pad_t":r.randint(40,120),"pad_x":r.randint(40,120),"pad_b":r.randint(30,100),
        "wjit":round(r.uniform(0.75,1.35),3),"dens":round(r.uniform(0.55,1.7),2)}
    if FONTS:   # 문서마다 본문·표·제목 글꼴을 계열별 확률로
        faces={}
        for slot,key in (("font_body","본문"),("font_table","표"),("font_title","제목")):
            f=r.choice(FONTS[_fam(r,key)]); th[slot]=f["name"]; faces[(f["name"],f["file"],f["weight"])]=1
        th["faces"]=[list(k) for k in faces]
    return th

def grid(rng, rows, cols, headers, cellfn, disp=None):
    hs="".join(f"<th>{h}</th>" for h in (disp or headers)[:cols])
    k=_T("col_contrast",0)
    if k>0:
        ws=[1+(COLW.get(h,1)-1)*k for h in headers[:cols]]
        tot=sum(ws)
        cg="<colgroup>"+"".join(f'<col style="width:{max(3,round(w/tot*100,1))}%">' for w in ws)+"</colgroup>"
    else: cg=""
    body="".join("<tr>"+"".join(cellfn(r,c) for c in range(cols))+"</tr>" for r in range(rows))
    sep=' class="hdsep"' if _T("open",False) and rng.random()<0.6 else ""   # 무외곽 표: 헤더 아래 2px (실서식 5_1호)
    return f"<table>{cg}<tr{sep}>{hs}</tr>{body}</table>"

class R:
    def __init__(self, sk):
        self.sk=sk; self.rng=random.Random(sk["seed"]); self.g=sk["glyph_rule"]
        self.missing=set()
        self.used_labels=set()   # 문서 수준 라벨 중복 방지 (인적표 다중 조합)
        r=self.rng
        self.theme=sample_theme(r)
        self.lex_rate=r.uniform(0.25,0.75)   # 문서마다 실코퍼스 어휘 치환 비율
        global THEME; THEME=self.theme
        self.doc_marker = self.rng.choice(["□","[&nbsp;&nbsp;]"])   # 문서 단위 규약
        if any(b.get("card") in ("cb_bracket","cb_prose") for b in sk.get("blocks",[])):
            self.doc_marker="[&nbsp;&nbsp;]"   # 대괄호 기제 카드 존재 시 문서 규약 고정
    def marker(self):
        """블록 진입 시 1회 호출 — mixed 문서만 블록 간 변경 허용, 그룹 내부 불변"""
        if self.g=="mixed": return self.rng.choice(["□","[&nbsp;&nbsp;]"])
        return self.doc_marker
    def rowhs(self,n):
        """표 단위 행 높이: 한 표 안은 균일(실서식 규약), 15% 확률로 한 행만 1.8~2.2배"""
        h=self.rowh(); hr=[h]*n
        if n>1 and self.rng.random()<0.15: hr[self.rng.randrange(n)]=int(h*self.rng.choice([1.8,2.2]))
        return hr
    def rowh(self):
        """행 높이 축: 문서 테마값 기준 + 표마다 변주(가끔 2배 높이)"""
        h=_T("row_h",34); r=self.rng.random()
        if r<0.18: h=int(h*self.rng.choice([1.8,2.2]))
        elif r<0.45: h=self.rng.choice([34,41,48,56,72])
        return h
    def L(self,s,p=None):
        """v4 어휘 주입: 실코퍼스 라벨로 치환 — 길이가 비슷한 토큰으로. 뜻이 맞을 필요는 없다(DDR)."""
        if not LEX_LEN or self.rng.random() >= (self.lex_rate if p is None else p): return s
        for k in (len(s),len(s)+1,len(s)-1,len(s)+2,len(s)-2):
            if LEX_LEN.get(k): return self.rng.choice(LEX_LEN[k])
        return s
    def P(self,lo=8,hi=30,p=0.5):
        """실코퍼스 문장 조각 (없거나 확률 미달이면 빈 문자열)"""
        if not LEX_PHRASE or self.rng.random()>=p: return ""
        c=[x for x in LEX_PHRASE if lo<=len(x)<=hi]
        return self.rng.choice(c) if c else ""
    def optset(self,n):
        fits=[p for p in OPTSETS if len(p[1])>=n and p[0] not in self.used_labels]
        if not fits: fits=[p for p in OPTSETS if p[0] not in self.used_labels] or OPTSETS
        lb,pool=self.rng.choice(fits)
        self.used_labels.add(lb)
        return lb,pool[:n]
    def opts(self,n):
        return self.optset(n)[1]
    # ── 블록 렌더 (카드 분기) ──
    def b_제목(self,b):
        t=self.rng.choice(LEX["제목어"]); doc=LEX["문서어"].get(self.sk["type"],"신청서")
        if self.sk.get("title"):   # 실서식 복제: 명칭 오버라이드
            num=f'<div class="byulji">[{self.sk.get("byulji","별지 서식")}] </div>'
            return num+f'<h1 class="doctitle">{self.sk["title"]}</h1>' 
        c=b["card"]
        if c=="title_paren":
            slot=('<span data-f="number" style="display:inline-flex;width:34px;height:30px;align-items:center;'
                  'justify-content:center;vertical-align:middle;font-size:20px;letter-spacing:normal;position:relative;top:-3.3px"></span>')
            inner=f'{t} <span style="letter-spacing:normal;display:inline-flex;align-items:center;vertical-align:middle;position:relative;top:-2px">(&nbsp;{slot}&nbsp;)</span>월 {doc}'
        elif c=="cb_title":
            tm=_T("mk",22)+8; g=self.marker()
            TMK=(f'<span data-f="checkbox" style="display:inline-flex;width:{tm}px;height:{tm}px;align-items:center;'
                 f'justify-content:center;vertical-align:middle;font-size:{tm-10}px;letter-spacing:normal;line-height:{tm}px;position:relative;top:-2px;margin:0 4px">{g}</span>')
            inner=f'{t} {TMK}지정 {TMK}변경 {doc}'
        else: inner=f"{t} {doc}"
        pg=self.rng.choice(["(앞쪽)","","(4쪽 중 1쪽)","(2쪽 중 1쪽)",""])
        ps=f'<span class="pageside">{pg}</span>' if pg else ''
        num = f'<div class="byulji">[별지 제{self.rng.randint(1,29)}호서식] {ps}</div>'
        return num+f'<h1 class="doctitle">{inner}</h1>'
    def b_인적표(self,b):
        c=b["card"]; rng=self.rng
        cells={
         "text_cell":CGF("text"),"ph_cell":CGF("phone"),"em_cell":CGF("email"),
         "date_cell":CGF("date"),"date_split":(ROW(GPT("date",rng.randint(12,20)),"년",GPT("date",rng.randint(10,18)),"월",GPT("date",rng.randint(10,18)),"일",j="c",style="gap:1px") if rng.random()<0.35   # v3 밀착
                       else ROW(GP("date",30),"년",GP("date",24),"월",GP("date",24),"일",j="c")),
         "num_unit":ROW("만",GP("number",40),"세",j="c"),
         "split_hyphen":ROW(GP("text",64),"–",GP("text",76),j="c"),
         "comb_slot":ROW(*[CBX()]*5,j="c",style="gap:2px"),
         "comb_jumin":ROW(*([CBX("number")]*6+["-"]+[CBX("number")]*7),j="c",style="gap:2px;flex-wrap:wrap;row-gap:2px"),
         "comb_date":ROW(*COMB_DATE(),j="c",style="gap:2px;flex-wrap:wrap;row-gap:2px"),
         "cell_sublabel":ROW('<span class="note">(한글)</span>',GP("text",90),'<span class="note">(한자)</span>',GP("text",70),j="c"),
         "mix_cell":ROW('<span data-f="text" class="cg" style="flex:1;margin:1px 0"></span>','<span class="note" style="flex:none">(전화번호 :</span>','<span data-f="phone" class="gp" style="width:70px"></span>','<span class="note">)</span>'),

         "text_suffix":ROW(GP("text",70),"의",GP("text",70),j="c"),'ph_multi':ROW("자택:",GP("phone",70),j="c")+ROW("휴대:",GP("phone",70),j="c"),
         "ph_pict":ROW("(☎",GP("phone",80),")",j="c",style="gap:2px"),
         "dot_box":f'<span data-f="text" class="cgf" style="border:1.4px dashed #555"></span>',

         "ph_lines":ROW("집 :",GP("phone",rng.randint(120,200)))+ROW("휴대전화 :",GP("phone",rng.randint(120,200))),
         "gp_cell":(ROW('<span class="note" style="flex:none">(전화번호 :</span>','<span data-f="phone" class="gp" style="flex:1"></span>','<span class="note" style="flex:none">)</span>')
            if rng.random()<0.5 else
            ROW('<span class="note" style="flex:none">'+rng.choice(["접수번호","관리번호","정리번호"])+'</span>','<span data-f="number" class="gp" style="flex:1"></span>')),
         "ul_cell":((ROW("자택:",UL("phone",rng.randint(90,140)))+ROW("휴대:",UL("phone",rng.randint(90,140))))
            if rng.random()<0.5 else ROW(UL("phone",rng.randint(90,200)),j="c")),
         "sig_cell":(ROW(GP("text",rng.randint(100,160)),
            '<span data-f="signature" style="display:inline-block;line-height:'+rng.choice(["1","1.45"])+'">(인)</span>',j="c") if rng.random()<0.5 else
            ROW(GP("text",rng.randint(110,170)),f'<span data-f="signature" style="font-size:{rng.choice([12,13,14])}px;line-height:1.3">{rng.choice(["(인)","(인)","(서명)"])}</span>',
                '<span style="width:24px"></span>','<span style="white-space:nowrap">날짜 :</span>',GPT("date",rng.randint(24,40)),".",GPT("date",rng.randint(18,28)),".",style="gap:4px;white-space:nowrap")),   # v3: 빈 공간 뒤 소형 (인) + 날짜 (실서식 15호)

         "dot_split":(ROW('<span class="note" style="font-size:11px;width:58px;flex:none;text-align:left">(전화)</span>','<span data-f="phone" class="cg" style="flex:1;margin:1px 0"></span>')
            +'<div style="border-top:1.2px dotted #555;margin:1px -4px"></div>'
            +ROW('<span class="note" style="font-size:11px;width:58px;flex:none;text-align:left">(전자우편)</span>','<span data-f="email" class="cg" style="flex:1;margin:1px 0"></span>')),
        }
        rows=[]
        self.used_labels |= (CARD_COVERS.get(c,set()) - {CARD_LABEL.get(c,"")})
        lead=CARD_LABEL.get(c,"성명")
        if lead in self.used_labels:   # 문서 내 리드 중복 → 같은 타입의 대체 라벨
            for alt in ALT_LABEL.get(CARD_TYPE.get(c,"text"),[]):
                if alt not in self.used_labels: lead=alt; break
        self.used_labels |= CARD_COVERS.get(c,set())
        picks=[p for p in LEX["인적"] if p[0]!=lead and p[0] not in self.used_labels]
        rng.shuffle(picks)
        self.used_labels.add(lead)
        dl=self.L(lead)   # v4: 표시 문구만 실코퍼스 어휘로 (타입·중복관리는 원래 라벨 기준)
        first=f'<span class="spread">{dl}</span>' if len(dl)==2 else dl
        if c=="radio_word":
            a,b2=RADIO_PAIR.get(lead,("여","남"))
            cells["radio_word"]=ROW(WORD(a),WORD(b2),j="c")
        if c=="dbx_cell":   # 점선 인라인 박스 1~2개(하이픈 분할)
            cells[c]=(ROW(DBX("number",rng.randint(60,200)),j="c") if rng.random()<0.5
                      else ROW(DBX("number",rng.randint(60,110)),"–",DBX("text",rng.randint(60,110)),j="c",style="gap:4px"))
        rows.append((first, cells.get(c, CGF("text"))))
        for lb,t in picks[:3]:
            rows.append((self.L(lb), ROW(WORD("여"),WORD("남"),j="c") if t=="radio" else CGF(t)))
            self.used_labels.add(lb)
        html=kv_table(rows, self.rowh)
        if c=="inset_label":
            items=[p for p in [("주민등록번호","number"),("외국인등록번호","text"),("주소","text"),("연락처","phone"),("전자우편","email"),("소속기관","text")] if p[0] not in self.used_labels]
            rng.shuffle(items)
            tds="".join(f'<td class="tl fillc" style="height:56px;vertical-align:top">{lb}<span data-f="{t}" class="cgf" style="top:26px"></span></td>' for lb,t in items[:2])
            tds2="".join(f'<td class="tl fillc" style="height:56px;vertical-align:top">{lb}<span data-f="{t}" class="cgf" style="top:26px"></span></td>' for lb,t in items[2:4])
            for lb,_ in items: self.used_labels.add(lb)
            return f'<table><tr>{tds}</tr><tr>{tds2}</tr></table>'
        if c=="inset_label_full":   # 라벨 상단 인쇄 + 셀 잔여 전폭 입력 (실서식 2편 13호)
            items=[p for p in picks if p[1]!="radio"]+[("주소","text"),("소속기관","text"),("전자우편","email"),("연락처","phone")]
            top=rng.choice([22,24,26]); hh=top+rng.choice([28,34,42])
            tds=[f'<td class="tl fillc" style="height:{hh}px;vertical-align:top">{lb}<span data-f="{t}" class="cgf" style="top:{top}px"></span></td>'
                 for lb,t in items[:4]]
            for lb,_t in items[:4]: self.used_labels.add(lb)
            if rng.random()<0.5:
                return f'<table><tr>{"".join(tds[:2])}</tr><tr>{"".join(tds[2:])}</tr></table>'
            return f'<table><tr>{"".join(tds)}</tr></table>'
        if c=="inline_pairs":   # v3: 한 셀에 라벨·빈칸 쌍 2~4개 나란히, 또는 라벨 + 잔여 전폭 cg (실서식 2편 1_1호·17호)
            items=[p for p in picks if p[1]!="radio"][:rng.randint(2,4)]
            for lb,_t in items: self.used_labels.add(lb)
            LB=lambda lb: f'<span style="flex:none">{lb}</span>'
            CGI=lambda t: f'<span data-f="{t}" class="cg" style="flex:1;margin:1px 0"></span>'
            if rng.random()<0.4:   # 가로 inset: 셀마다 라벨 + cg flex:1
                tds="".join(f'<td class="tl">{ROW(LB(lb),CGI(t),style="gap:4px")}</td>' for lb,t in items[:3])
                return f'<table><tr><th style="width:118px">{lead}</th>{tds}</tr></table>'
            parts=[]
            for lb,t in items:
                if t=="phone" and rng.random()<0.6: parts+=[LB(lb),GPT("phone",rng.randint(40,56)),"-",GPT("phone",rng.randint(40,56))]
                else: parts+=[LB(lb),GP(t,rng.randint(60,150))]
            return f'<table><tr><th style="width:118px">{lead}</th><td class="tl">{ROW(*parts,style="gap:2px;flex-wrap:wrap;row-gap:4px")}</td></tr></table>'
        if c=="img_cell":
            html=html.replace("</table>",'<tr><td class="vl" rowspan="1" data-f="image" style="width:110px;height:120px">사 진<br><span class="note">(3.5×4.5cm)</span></td><td colspan="3" class="tl fillc" style="vertical-align:top"><span class="note">특이사항</span><span data-f="textarea" class="cgf" style="top:24px"></span></td></tr></table>')
        return html
    def b_선택군(self,b):
        c=b["card"]; rng=self.rng; n=b.get("n_options",4); olb,o=self.optset(n); g=self.g
        olb=self.L(olb); o=[self.L(x,0.4) for x in o]   # v4 어휘 주입 (표시 문구만)
        ch=self.marker()
        kind="radio" if c in ("cb_row","cb_col","cb_wrap","cb_grid","cb_bracket") and rng.random()<0.5 else "checkbox"
        M=lambda: MK(ch, kind)   # 그룹 안은 전부 같은 kind
        SFX=((lambda: (rng.choice([f"(&nbsp;{GP('text',rng.randint(36,70))}&nbsp;)",f"약 {GP('number',rng.randint(30,50))} m"]) if rng.random()<0.3 else ""))
             if rng.random()<0.45 else (lambda: ""))   # v3: 선택지 뒤 괄호 빈칸 (실서식 15호 "기타 ( )"·"약 __ m")
        if c in("cb_row","cb_grid","cb_bracket","header_opts"):
            item=lambda x: f'<span style="display:inline-flex;align-items:center;gap:3px;white-space:nowrap">{M()}{x}{SFX()}</span>'
            inner=ROW(*[item(x) for x in o],style="gap:12px;flex-wrap:wrap;row-gap:4px")
            return f'<table><tr><th style="width:118px">{olb}</th><td class="tl">{inner}</td></tr></table>'
        if c=="cb_col":
            inner="".join(ROW(M(),x,style="gap:3px") for x in o[:4])
            return f'<table><tr><th style="width:118px">{olb}</th><td class="tl">{inner}</td></tr></table>'
        if c=="cb_wrap":
            half=(len(o)+1)//2
            item=lambda x: f'<span style="display:inline-flex;align-items:center;gap:3px;white-space:nowrap">{M()}{x}{SFX()}</span>'
            r1=ROW(*[item(x) for x in o[:half]],style="gap:12px;flex-wrap:wrap;row-gap:4px")
            r2=ROW(*[item(x) for x in o[half:]],style="gap:12px;flex-wrap:wrap;row-gap:4px")
            return f'<table><tr><th style="width:118px">{olb}</th><td class="tl">{r1}{r2}</td></tr></table>'
        if c=="radio_yn": return ROW("결격사유 해당 여부 &nbsp;",MK(ch,"radio"),"예 &nbsp;",MK(ch,"radio"),"아니오",style="margin:6px 0")
        if c=="radio_word":
            lb="성별"
            if lb in self.used_labels:
                for alt in ALT_LABEL["radio"]:
                    if alt not in self.used_labels: lb=alt; break
            self.used_labels.add(lb)
            a,b2=RADIO_PAIR.get(lb,("여","남"))
            return f'<table><tr><th style="width:118px">{lb}</th><td class="vl">{ROW(WORD(a),WORD(b2),j="c")}</td></tr></table>'
        if c=="radio_paren":
            lb2="교육과정" if "교육과정" not in self.used_labels else "이수과정"
            self.used_labels.add(lb2)
            return f'<table><tr><th style="width:118px">{lb2}</th><td class="vl">{ROW("40시간",RMK(),"&nbsp; 20시간",RMK(),j="c")}</td></tr></table>'
        if c=="radio_circled":
            o=["자택","직장","읍·면·동 주민센터"]
            m=_T("mk",22)+2
            return ROW("수령지 &nbsp;",*sum([[f'<span data-f="radio" style="display:inline-flex;width:{m}px;height:{m}px;align-items:center;justify-content:center">{"①②③④⑤"[i]}</span>',x] for i,x in enumerate(o[:3])],[]),style="margin:6px 0")
        if c=="cb_sub":
            LR=lambda: ["(",WORD("L","radio"),",",WORD("R","radio"),")"]
            return ROW(M(),"눈",*LR(),"&nbsp;",M(),"귀",*LR(),"&nbsp;",M(),"팔",*LR(),style="margin:6px 0;gap:2px")
        if c=="cb_dep":
            return ROW(M(),f"{o[0]}(",GP("text",44),") &nbsp;",M(),f"{o[1]}(",GP("text",44),") &nbsp;",M(),"기타(",GP("text",44),")",style="margin:6px 0;gap:2px")
        if c=="cb_inline_parent":
            return ROW(M(),"보호자일시부재(",M(),"결혼 &nbsp;",M(),"사망 &nbsp;",M(),"출산 &nbsp;",M(),"입원 ) &nbsp;",M(),"기타",style="margin:6px 0;gap:2px")
        if c=="cb_parent":
            o=["거주지 이전","이용기관 변경","서비스 형태 변경"]
            rowsh="".join(f'<tr><td class="tl">{ROW(M(),x,style="gap:3px")}</td></tr>' for x in o[:3])
            return f'<table><tr><th style="width:118px" rowspan="3">{ROW(M(),"변 경",j="c",style="gap:3px")}<span class="note">사유</span></th>'+rowsh[4:]+"</table>"
        if c=="cb_prose":
            o=OPTSETS[1][1][:n]
            inner=" ".join(f'{M()} {x}' for x in o)
            if self.sk["type"]=="통지회신":
                return f'<p class="ln">1. 귀하가 신청한 급여에 대한 조사·심의 결과 {inner} 급여대상자로 결정되었음을 알려드립니다.</p>'
            return f'<p class="ln">1. 본인은 다음 급여 중 해당하는 항목을 선택하여 {inner} 위와 같이 신청합니다.</p>'
        self.missing.add(c); return f'<p class="ln">{M()} {o[0]} &nbsp; {M()} {o[1]}</p>'
    def b_서술(self,b):
        c=b["card"]
        cand=[x for x in LEX["서술라벨"] if x not in self.used_labels] or LEX["서술라벨"]
        lb=self.rng.choice(cand); self.used_labels.add(lb); lb=self.L(lb)
        h=self.rowh()*2
        if c=="ta_cell": return f'<table><tr><th style="width:118px">{lb}</th>{TDC("textarea",h,cls="")}</tr></table>'
        if c=="ta_below": return f'<table><tr><td class="tl lb2">{lb} <span class="note">(구체적으로 기술)</span></td></tr><tr>{TDC("textarea",h,cls="")}</tr></table>'
        if c=="ta_outline": return (f'<p class="ln">□ {lb}</p>'
            f'<div class="indent1" style="display:flex;align-items:flex-start">○&nbsp;'
            f'<div data-f="textarea" style="flex:1;height:56px"></div></div>')
        return f'<p class="ln">{lb} :</p><div data-f="textarea" style="height:70px"></div>'  # ta_free
    def b_격자(self,b):
        c=b["card"]; rng=self.rng
        rows=min(b.get("rows",5),8); cols=min(b.get("cols",5),7)
        theme=rng.choice(GRID_THEMES)
        hs=(theme+[h for h in ("담당","확인","결과","점검") if h not in theme])[:cols]
        if c=="photo_grid":   # 사진대지: 2열 × 2~3행, 사진 박스 + 촬영일 캡션 (페이지당 4~6장)
            nr=rng.randint(2,3); pw=rng.randint(260,380); ph=rng.randint(180,300)
            named=rng.random()<0.5; body=""; k=0
            for _r in range(nr):
                ps=""; cs=""
                for _ in range(2):
                    k+=1
                    lab="현장 사진 "+str(k) if named else "사 진"
                    ps+=(f'<td class="vl" style="height:{ph+12}px"><span data-f="image" style="display:inline-block;'
                         f'width:{pw}px;height:{ph}px;border:1px solid #000;line-height:{ph}px;color:#555">{lab}</span></td>')
                    cs+=f'<td class="vl note">{ROW("사진 "+str(k)+" · 촬영일 :",GP("date",60),j="c")}</td>'
                body+=f"<tr>{ps}</tr><tr>{cs}</tr>"
            return f"<table>{body}</table>"
        if c=="sig_grid":   # 참석자 서명부: 행마다 서명 문구 (표 안 소형 signature)
            n=max(6,min(12,b.get("rows",9))); comb4=rng.random()<0.35   # 행 수는 골격을 따름(밀도 상한)
            cw=["7%","20%","31%","22%","20%"]
            hs2=["연번","성명","소속(기관)",
                 "연락처"+('<br><span class="note">(뒤 4자리)</span>' if comb4 else ""),"서명"]
            sm=rng.random()   # 서명 열 규약은 표 단위 (실서식은 한 장에 한 형태)
            SIGSZ=(("(인)",11,rng.randint(24,30),rng.randint(18,22)) if sm<0.62 else
                   ("(서명)",12,rng.randint(40,56),rng.randint(18,26)) if sm<0.88 else
                   ("(서명 또는 인)",11,rng.randint(84,116),rng.randint(18,26)))
            h=rng.randint(34,48); telw=rng.randint(90,140)   # 행 높이·연락처 폭도 표 단위
            def sig_td():
                if sm<0.30: return f'<td class="vl">{CG("signature")}</td>'
                txt,fs,sw,sh=SIGSZ
                return (f'<td class="vl"><span data-f="signature" style="display:inline-block;width:{sw}px;'
                        f'height:{sh}px;line-height:{sh}px;font-size:{fs}px;'
                        f'white-space:nowrap;overflow:hidden">{txt}</span></td>')
            body=""
            for i in range(n):
                tel=(ROW(*[CBX("phone")]*4,j="c",style="gap:2px") if comb4 else GP("phone",telw))
                body+=(f'<tr style="height:{h}px"><td class="vl note">{i+1}</td>'
                       f'{TDC("text",h)}{TDC("text",h)}'
                       f'<td class="vl">{tel}</td>{sig_td()}</tr>')
            cg2="<colgroup>"+"".join(f'<col style="width:{w}">' for w in cw)+"</colgroup>"
            return f'<table>{cg2}<tr>'+"".join(f"<th>{x}</th>" for x in hs2)+f"</tr>{body}</table>"
        if c=="pf_grid":   # 작성례 표: 셀마다 마스킹된 예시값이 회색 소자로 인쇄
            prows=max(4,min(6,b.get("rows",5))); pcols=rng.randint(4,6)
            hs=(rng.choice(GRID_THEMES)+[h for h in ("담당","확인","결과","점검") if h not in theme])[:pcols]
            EX={"number":["00","0","12","3","00"],"date":["20○○.○○.○○","20○○-○○-○○","○○.○○.○○"],
                "phone":["010-○○○○-○○○○","○○○-○○○-○○○○"],"time":["○○:○○~○○:○○","09:00~10:00"],
                "text":["○○○","홍길동","○○기관","○○동 ○○길","예) ○○○","○○○ 외 ○명"]}
            hr=[rng.choice([30,34,41,48])]*prows
            def cf(r,cn):
                t=HEADER_TYPE.get(hs[cn],"text")
                v=str(r+1) if hs[cn] in ("연번","순번") else rng.choice(EX[t])
                fs=13 if len(v)<=8 else 11
                return (f'<td class="vl" style="height:{hr[r]}px"><span data-f="{t}" class="cg" '
                        f'style="line-height:{_T("cg_h",26)}px"><span class="note" '
                        f'style="font-size:{fs}px;color:#666">{v}</span></span></td>')
            return f'<p class="note" style="margin-bottom:3px">〈작성례〉</p>'+grid(rng,prows,pcols,hs,cf,disp=[self.L(h,0.4) for h in hs])
        if c=="radio_likert":
            hs=["문 항","매우만족","만족","보통","불만족","매우불만족"]; cols=6
            QS=["서비스 전반에 만족하십니까?","제공 인력은 친절하였습니까?","서비스 시간은 적절하였습니까?","재이용 의향이 있으십니까?"]
            def cf(r,cn):
                if cn==0: return f'<td class="tl">{r+1}. {QS[r%4]}</td>'
                return f'<td class="vl fillc">{CGF("radio")}</td>'   # v3: 빈 선택 셀 = 셀 전체 (실서식 17호 규약)
            return grid(rng,min(rows,4),cols,hs,cf)
        if c=="scale_words":   # 글자 인쇄 셀 자체가 선택지 (실서식 1편 17호·16-1호)
            hs=["문 항","매우만족","만족","보통","불만족","매우불만족"]; cols=6
            QS=["서비스 전반에 만족하십니까?","제공 인력은 친절하였습니까?","서비스 시간은 적절하였습니까?",
                "재이용 의향이 있으십니까?","서비스 내용을 충분히 안내받으셨습니까?","불편사항이 신속히 처리되었습니까?"]
            circled=rng.random()<0.5
            def cf(r,cn):
                if cn==0: return f'<td class="tl" style="font-size:14.5px">{r+1}. {QS[r%len(QS)]}</td>'
                if circled:
                    op=(f'<span data-f="radio" style="display:inline-flex;width:22px;height:22px;align-items:center;'
                        f'justify-content:center;font-size:15px;line-height:22px;vertical-align:middle">{"①②③④⑤"[cn-1]}</span>')
                    return f'<td class="vl" style="font-size:13.5px;line-height:1.3">{op}{hs[cn]}</td>'
                lab=hs[cn] if len(hs[cn])<5 or rng.random()<0.4 else hs[cn][:2]+"<br>"+hs[cn][2:]   # 매우<br>불만족
                return f'<td class="vl fillc" style="font-size:13.5px;line-height:1.3;height:{hh}px">{lab}{CGF("radio")}</td>'   # v3: 글자 인쇄 셀 전체가 선택 박스
            hh=rng.choice([34,38,41,44])
            return grid(rng,rng.randint(4,6),cols,hs,cf)
        if c=="scale_anchor":
            m=_T("mk",22)+2
            cells="".join(f'<td class="vl" style="width:34px"><span data-f="radio" style="display:inline-flex;width:{m}px;height:{m}px;align-items:center;justify-content:center">{"①②③④⑤⑥⑦⑧⑨⑩"[i]}</span></td>' for i in range(10))
            return f'<table><tr>{cells}</tr></table><p class="note">← 심각 &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; 양호 →</p>'
        if c=="radio_grid":
            def cf(r,cn):
                if cn==0: return f'<td class="lb">{["부","모","조부모","형제자매"][r%4]}</td>'
                return f'<td class="vl">{ROW(WORD("유"),WORD("무"),j="c")}</td>'
            return grid(rng,min(rows,4),3,["구분","동거 여부","장애 유무"],cf)
        if c=="cb_matrix":
            def cf(r,cn):
                if cn==0: return f'<td class="lb">{["오전","오후","저녁","심야"][r%4]}</td>'
                return f'<td class="vl fillc">{CGF("checkbox")}</td>'   # v3
            return grid(rng,4,6,["구분","월","화","수","목","금"],cf)
        if c=="date_slash":
            cells="".join(f'<td class="vl">{ROW(SLOT("date","",30)," / ",SLOT("date","",30),j="c",style="gap:2px")}</td>' for _ in range(cols-1))
            return f'<table><tr><th>월, 일</th>{cells}</tr><tr><th>시작시간</th>'+"".join('<td class="vl"><span data-f="time" class="cg"></span></td>' for _ in range(cols-1))+"</tr></table>"
        if c=="sig_bold":
            if getattr(self,"sig_bold_used",False): c="sig_phrase"
            else:
                self.sig_bold_used=True
                return ('<table><tr><th style="width:130px">관리자 서명</th><td class="thick"><span data-f="signature" class="cg"></span></td></tr>'
                        '<tr><th>보호자 서명</th><td class="thick"><span data-f="signature" class="cg"></span></td></tr></table>')
        if c=="stub_input":
            items=[("사업명","text"),("수행기관","text"),("담당자","text"),("연락처","phone"),("신청일","date"),("연번","number"),("소재지","text")]
            hr=self.rowhs(rows)
            def cf(r,cn):
                if cn==0:
                    return f'<td class="lb">{ROW("기타(",GP("text",40),")",style="gap:2px")}</td>' if r==rows-1 else f'<td class="lb">{items[r%7][0]}</td>'
                t="text" if r==rows-1 else items[r%7][1]
                return TDC(t,hr[r],cls="")
            return grid(rng,rows,min(cols,3),["구분","내용","비고"],cf,disp=[self.L(h,0.4) for h in ["구분","내용","비고"]])
        if c=="num_denom":
            return f'<table><tr><th style="width:118px">합 계</th><td class="vl">{GP("number",56)}/100점</td></tr></table>'
        if c=="header_opts":
            return f'<table><tr><th>서비스구분<br><span class="note">(기관내/방문)</span></th></tr>'+"".join(f'<tr><td class="vl">{ROW(WORD("기관내"),WORD("방문"),j="c")}</td></tr>' for _ in range(3))+"</table>"
        if c=="cal_grid":
            d=[0]; ch=max(44,self.rowh()+14)
            def cf(r,cn):
                d[0]+=1
                num=f'<div class="note" style="font-size:11px;text-align:left;line-height:1">{d[0]}</div>' if d[0]<=31 else '<div style="height:11px"></div>'
                inp='<span data-f="text" class="cgf" style="top:16px"></span>' if d[0]<=31 else ''
                return f'<td class="fillc" style="height:{ch}px;vertical-align:top">{num}{inp}</td>'
            return grid(rng,5,7,["일","월","화","수","목","금","토"],cf)
        if c=="grid_diag":
            diag=('<th style="width:110px;background:linear-gradient(to top right,#E2E2E2 49.5%,#000 49.5%,#000 50.5%,#E2E2E2 50.5%)">'
                  '<div style="text-align:right;font-size:12px;line-height:1.1">항목</div>'
                  '<div style="text-align:left;font-size:12px;line-height:1.1">구분</div></th>')
            hs2="".join(f"<th>{self.L(h,0.4)}</th>" for h in hs[1:cols])
            rlbs=["신규","연속","종결","변경","중단","재개","이관","기타"]
            hr=self.rowhs(rows)
            body="".join('<tr>'+f'<td class="lb">{rlbs[r%8]}</td>'
                         +"".join(TDC(HEADER_TYPE.get(hs[i+1],"text"),hr[r]) for i in range(cols-1))+'</tr>' for r in range(rows))
            return f'<table><tr>{diag}{hs2}</tr>{body}</table>'
        # generic: 열 헤더 라벨이 입력 타입을 결정 (라벨 1:입력 1 규칙)
        if c=="num_cell": theme=GRID_THEMES[4]
        if c=="date_cell": theme=GRID_THEMES[2]
        if c in ("num_cell","date_cell"): hs=(theme+[h for h in ("담당","확인","결과","점검") if h not in theme])[:cols]
        if c not in ("num_cell","date_cell"): self.missing.add(c)
        hr=self.rowhs(rows)
        def cf(r,cn):
            return TDC(HEADER_TYPE.get(hs[cn],"text"),hr[r])
        return grid(rng,rows,cols,hs,cf,disp=[self.L(h,0.4) for h in hs])
    def b_금액(self,b):
        c=b["card"]
        m={"num_unit":f'<table><tr><th style="width:130px">월 이용액</th><td class="vl">{ROW(GP("number",90),"원",j="c")}</td></tr></table>',
           "num_both":ROW("나이 &nbsp; 만",UL("number",60),"세",style="margin:8px 0"),
           "num_bracket":f'<table><tr><th style="width:150px">서비스이용시간</th><td class="vl">{ROW("[",GP("number",56),"] 시간",j="c",style="gap:2px")}</td></tr></table>',
           "paren_unit":ROW("자 격 증 &nbsp; (",GP("text",70),"급 )",style="margin:8px 0"),
           "num_affix":ROW("제",GP("number",70),"호",style="margin:8px 0;font-size:20px")}
        return m.get(c) or m["num_unit"]
    def b_날짜줄(self,b):
        c=b["card"]
        m={"date_split":ROW(GP("date",36),"년",GP("date",28),"월",GP("date",28),"일",j="c",style="margin-top:20px"),
           "date_inline":ROW(GP("date",36),"년 &nbsp;",GP("date",28),"월 &nbsp;",GP("date",28),"일",j="c"),
           "date_dots":ROW("20",GP("date",30),".",GP("date",24),".",GP("date",24),".",j="c",style="gap:2px"),
           "date_range":ROW("○ "+({"계약서":"계약기간","등록카드":"위촉기간","통지회신":"지원기간"}.get(self.sk["type"],"신청기간"))+" :",GP("date",30),"년",GP("date",24),"월",GP("date",24),"일 ~",GP("date",30),"년",GP("date",24),"월",GP("date",24),"일",style="margin:6px 0"),
           "comb_date":ROW(*COMB_DATE(),j="c",style="margin-top:20px;gap:2px"),
           "date_tight":ROW("20",GPT("date",self.rng.randint(12,20)),"년",GPT("date",self.rng.randint(10,18)),"월",GPT("date",self.rng.randint(10,18)),"일",
                            *(["~ 20",GPT("date",self.rng.randint(12,20)),"년",GPT("date",self.rng.randint(10,18)),"월",GPT("date",self.rng.randint(10,18)),"일"] if self.rng.random()<0.5 else []),
                            j="c",style="margin-top:14px;gap:1px"),   # v3 밀착 (실서식 1편 2호)
           "pf_year20":ROW("20",SLOT(),"년",SLOT(),"월",SLOT(),"일",j="c",style="margin-top:20px")}
        return m.get(c) or m["date_split"]
    def b_시각(self,b):
        if b["card"]=="time_cell":
            sp='<span data-f="time" class="cg" style="flex:1;margin:1px 0"></span>'  # 3.11 호환: f-string 안 백슬래시 금지
            return (f'<table><tr><th style="width:118px">사고시간</th><td class="vl">'
                    f'{ROW(sp,WORD("am"),"/",WORD("pm"),style="gap:6px")}</td></tr></table>')
        if self.rng.random()<0.5:   # v3 밀착 시각 (실서식 17호: 26px 슬롯)
            w=self.rng.randint(18,28)
            return ROW(GPT("date",w),"일",GPT("time",w),"시",GPT("time",w),"분 ~",GPT("time",w),"시",GPT("time",w),"분",j="c",style="gap:1px")
        return ROW(SLOT("time"),"시",SLOT("time"),"분",j="c")
    def b_서명줄(self,b):  # v1.3: 이름/서명 분리 + 직인은 발신형 전용 + ○○ 발신명의 비입력
        c=b["card"]
        if c in ("sig_stamp","sig_stamp_paren","stamp_box") and self.sk["type"] not in ("증서","통지회신","공고문"):
            c="sig_phrase"
        elif self.sk["type"] in ("증서","통지회신","공고문") and c not in ("sig_stamp","sig_stamp_paren","stamp_box"):
            c=self.rng.choice(["sig_stamp","sig_stamp_paren","stamp_box"])
        if c=="sig_bold":
            if getattr(self,"sig_bold_used",False): c="sig_phrase"
            else:
                self.sig_bold_used=True
                return ('<table><tr><th style="width:130px">관리자 서명</th><td class="thick"><span data-f="signature" class="cg"></span></td></tr>'
                        '<tr><th>보호자 서명</th><td class="thick"><span data-f="signature" class="cg"></span></td></tr></table>')
        self.sig_n=getattr(self,"sig_n",0)
        ROLES={"계약서":["갑 (이용자)","을 (제공기관)"],"등록카드":["기관 대표","본인"]}
        seq=ROLES.get(self.sk["type"])
        who=seq[self.sig_n%len(seq)] if seq else self.rng.choice(["신청인","보호자","작성자","동의자"])
        self.sig_n+=1
        SIG=lambda t: (f'<span data-f="signature" style="font-size:{self.rng.choice([12,13,14])}px;line-height:1.2">{t}</span>' if self.rng.random()<0.5   # 글줄 속 소형 문구(높이 14~17, v3: 실서식 h≤16 28%)
                       else f'<span data-f="signature" style="vertical-align:middle;display:inline-block">{t}</span>')
        if c=="sig_name": return f'<p class="sigline">{who} 성명 : {GP("text",110)} {SIG("(인)")}</p>'
        if c=="sig_ul":   return f'<p class="sigline">{UL("text",100)}<span data-f="signature" style="vertical-align:middle;display:inline-block">(인)</span></p>'
        OO='<span data-f="text" style="display:inline-block;width:44px;text-align:center">○○</span>'
        if c=="stamp_box":   # 도장칸 (실서식 2편 14호)
            z=self.rng.randint(90,120); col=self.rng.choice(["#000","#000","#B02B25"])
            ch=self.rng.choice(["인","직인",""])
            box=(f'<span data-f="signature" style="display:inline-block;width:{z}px;height:{z}px;'
                 f'border:1.2px solid {col};color:{col};text-align:center;line-height:{z-3}px;'
                 f'font-size:{16 if len(ch)>1 else 20}px">{ch}</span>')
            return f'<p class="sigline">{OO} 시장·군수·구청장 &nbsp;{box}</p>'
        if c=="sig_stamp": return f'<p class="sigline">{OO} 시장·군수·구청장 <span data-f="signature" style="vertical-align:middle;display:inline-block;border:2.2px solid #B02B25;color:#B02B25;padding:6px 10px">직인</span></p>'
        if c=="sig_stamp_paren": return f'<p class="sigline">{OO} 시장·군수·구청장 &nbsp; <span data-f="signature" style="vertical-align:middle;display:inline-block">(직인)</span></p>'
        return f'<p class="sigline">{who} : {GP("text",110)}{SIG("(서명 또는 인)")}</p>'
    def b_수신줄(self,b):
        return ROW(GP("text",150),"&nbsp;<b>귀하</b>",style="margin-top:12px")
    def b_동의문단(self,b):
        if b["card"]=="consent_pair":   # 절마다 "□ 동의 □ 미동의" 쌍 (택일 → radio). 실서식 1_2호·3호·2편 7호
            ch=self.marker(); rng=self.rng
            SECS=["개인정보의 수집·이용","고유식별정보의 처리","민감정보의 처리","개인정보의 제3자 제공","홍보·안내 목적의 연락"]
            out=[]
            for t in rng.sample(SECS, rng.randint(4,5)):
                out.append(f'<p class="ln note" style="margin:8px 0 2px">□ {t} 내역<br>귀하는 위와 같은 {t}에 대해 동의를 거부할 수 있으며, 거부 시 서비스 이용이 제한될 수 있습니다.</p>'
                           +ROW(f"위와 같이 {t}에 동의하십니까?",MK(ch,"radio"),"동의",MK(ch,"radio"),"미동의",j="r",style="gap:6px;margin:2px 0 6px"))
            return "".join(out)
        if b["card"]=="consent_check":
            ch=self.marker()
            return ('<table><tr><th class="tl" style="padding-left:10px">내 용</th>'
                    '<th style="width:88px">확 인<br><span class="note">(√ 체크)</span></th></tr>'
                    f'<tr><td class="tl note">본인은 위 신청과 관련한 안내를 받았음을 확인합니다.</td><td class="vl">{MK(ch)}</td></tr>'
                    f'<tr><td class="tl note">신청 내용 변동 시 지체 없이 신고하겠습니다.</td><td class="vl">{MK(ch)}</td></tr></table>')
        return '<p class="ln note" style="margin:10px 0">본인은 위 목적을 위하여 개인정보를 수집·이용하는 것에 동의합니다.</p>'
    def b_고지표(self,b):
        ROWS=[("성명·연락처·주소","서비스 대상자 선정","5년"),
            ("주민등록번호","자격 확인 및 중복수혜 방지","이용 종료 후 5년"),
            ("소득·재산 정보","본인부담금 산정","3년"),
            ("건강상태·장애유형","서비스 제공 계획 수립","이용 종료 시까지")]
        if not hasattr(self,"notice_used"): self.notice_used=set()
        avail=[r for i,r in enumerate(ROWS) if i not in self.notice_used] or ROWS
        row=self.rng.choice(avail)
        self.notice_used.add(ROWS.index(row))
        hdr='' if len(self.notice_used)>1 else f'<tr><th style="width:120px">항목</th><th>목적</th><th style="width:170px">보유기간</th></tr>'
        return (f'<table>{hdr}'
                f'<tr><td class="tl note">{row[0]}</td><td class="tl note">{row[1]}</td><td class="vl note">{row[2]}</td></tr></table>')
    def b_접수밴드(self,b):
        if b.get("card")=="text_paren":
            return ROW("(접수번호 :",GP("number",90),") &nbsp; (접수일 :",GP("date",90),")",style="margin:4px 0;gap:2px")
        return ('<table><tr><th style="width:100px">접수번호</th><td class="vl"><span data-f="number" class="cg"></span></td>'
                '<th style="width:100px">접수일</th><td class="vl"><span data-f="date" class="cg"></span></td>'
                '<th style="width:100px">처리기간</th><td class="vl lb2">즉시</td></tr></table>')
    def b_글머리서술(self,b):
        c=b["card"]; rng=self.rng
        cand=[x for x in LEX["서술라벨"] if x not in self.used_labels] or LEX["서술라벨"]
        lb=rng.choice(cand); self.used_labels.add(lb); lb=self.L(lb)
        LAWS=["장애아동 복지지원법","사회보장급여의 이용·제공 및 수급권자 발굴에 관한 법률","아동복지법","장애인복지법","형의 실효 등에 관한 법률"]
        if c=="legal_prose":
            n=rng.randint(2,4)
            lines="".join(f'<p class="ln" style="padding-left:14px">{"①②③④⑤"[i]} 「{rng.choice(LAWS)}」 제{rng.randint(2,60)}조제{rng.randint(1,8)}항에 따른 {rng.choice(["결격사유에 해당하는 사람","지원 대상자","조회 대상 범죄경력","서비스 제공 기준"])}</p>' for i in range(n))
            return f'<p class="ln"><b>{rng.choice(["결격사유","관련 근거","지원 근거"])}</b></p>{lines}'
        if c=="notice_band":
            return ('<div style="background:#DDD;font-weight:700;text-align:center;padding:5px 0;border-top:2px solid #000">유의사항</div>'
                    f'<div class="note" style="padding:10px 16px;border-bottom:1px solid #000">1. {rng.choice(["본 서식은 사실대로 기재하여야 하며, 허위 기재 시 지원이 제한될 수 있습니다.","기재 내용이 변동된 경우 지체 없이 신고하여야 합니다."])}<br>2. {rng.choice(["담당 공무원 확인에 동의하지 않는 경우 해당 서류를 제출하여야 합니다.","문의는 관할 시·군·구 또는 읍·면·동 주민센터로 하시기 바랍니다."])}</div>')
        if c=="ul_lines":   # 진술·확약 문장: 글줄 문맥 문장마다 밑줄 빈칸 1~3개
            U=lambda t,a,b2: UL(t,rng.randint(a,b2))
            SENT=[lambda: f'본인은 {U("text",120,260)} 에 거주하는 {U("text",70,120)} 로서 아래 사항이 사실과 다름없음을 확인합니다.',
             lambda: f'20{U("date",60,90)} 년 {U("date",60,90)} 월 {U("date",60,90)} 일 {U("text",120,220)} 에서 발생한 사안에 대하여 다음과 같이 진술합니다.',
             lambda: f'본인은 {U("text",90,160)} 사업의 제공인력으로서 관계 법령과 업무상 비밀유지 의무를 준수할 것을 확약합니다.',
             lambda: f'통지는 연락처 {U("phone",120,200)} 로 받기를 원하며, 변동이 있는 경우 지체 없이 신고하겠습니다.',
             lambda: f'위 진술이 사실과 다를 경우 {U("text",100,180)} 에 따른 어떠한 처분도 감수하겠습니다.',
             lambda: f'본인은 총 {U("number",60,90)} 회, {U("number",60,90)} 시간의 교육을 이수하였음을 확인합니다.',
             lambda: f'제출 서류 중 {U("text",140,260)} 항목은 {U("date",90,150)} 을(를) 기준으로 작성하였습니다.',
             lambda: f'상기 본인 {U("text",90,150)} 은(는) {U("text",150,260)} 에 관하여 위와 같이 진술합니다.']
            rng.shuffle(SENT)
            head=rng.choice(["진 술 내 용","확 약 사 항","확인 사항"])
            lines="".join(f'<p class="ln" style="margin:6px 0">{i+1}. {s()}</p>' for i,s in enumerate(SENT[:rng.randint(3,6)]))
            return f'<p class="ln"><b>{head}</b></p>{lines}'
        fs=rng.choice([17,17,15,14])   # v3: 문장 글꼴 축 → gap 높이 16~19.5 (실서식 h≤18 44%)
        m={"text_colon":ROW(f"{lb} :",GP("text",rng.choice([180,260,340,460])),style=f"margin:6px 0;font-size:{fs}px"),   # 폭 400 초과 문장 빈칸 포함
           "text_ul":ROW(f"{lb} :",UL("text",120),",",UL("text",120),style="margin:6px 0"),
           "text_paren":ROW(f"({lb} :",GP("text",100),")",style="margin:6px 0;gap:2px"),
           "text_prose":ROW("위 사람은",GP("text",rng.choice([150,220,320,420])),"과정을 이수하였음을 확인합니다.",style=f"margin:6px 0;font-size:{fs}px"),
           "ta_outline":(f'<p class="ln">□ {lb}</p>'
            f'<div class="indent1" style="display:flex;align-items:flex-start">○&nbsp;'
            f'<div data-f="textarea" style="flex:1;height:40px"></div></div>')}
        return m.get(c) or m["ta_outline"]
    def b_사진(self,b):
        if b["card"]=="img_circle":   # 원형 사진·로고 칸 (실서식 1편 12호 신분증)
            d=self.rng.choice([26,32,40,48,60]); n=self.rng.randint(2,3)
            circ=f'<span data-f="image" style="display:inline-block;width:{d}px;height:{d}px;border:1.4px solid #000;border-radius:50%"></span>'
            return f'<div style="display:flex;justify-content:center;gap:34px;margin:14px 0">{circ*n}</div>'
        if b["card"]=="img_card":
            return '<div style="border:2px solid #000;padding:20px;text-align:center"><div data-f="image" style="border:1.4px solid #000;width:96px;height:118px;margin:0 auto;line-height:118px">사 진</div></div>'
        return '<table><tr><td class="vl" data-f="image" style="width:110px;height:130px">사 진<br><span class="note">(3.5×4.5cm)</span></td></tr></table>'
    # ── v4 비대상 방해물: data-f 없음 = GT 에 안 들어감. 필드와 부분 겹침 허용(입력 span 안에는 절대 넣지 않는다) ──
    def _float(self, inner, x, y):
        """흐름에 영향 없는 절대배치 조각 (height:0 래퍼 → 위/아래 요소와 겹칠 수 있다)"""
        return f'<div style="position:relative;height:0">{inner.replace("@X",str(x)).replace("@Y",str(y))}</div>'
    def distractors(self):
        r=self.rng; out=[]
        n=r.choices([0,1,2,3,4,5,6],[16,20,20,16,12,9,7])[0]
        W=self.theme["page_w"]
        for _ in range(n):
            k=r.choices(["stamp","logo","watermark","notice","pageno","receipt"],[26,16,10,20,16,12])[0]
            org=r.choice(["○○시","○○군","○○구청","한국사회보장원","○○복지관","중앙지원단","○○교육원"])
            if k=="stamp":
                z=r.randint(52,112); col=r.choice(["#B02B25","#C0392B","#8E1B18","#7a1f1c","#555"])
                rad="50%" if r.random()<0.6 else f"{r.randint(0,8)}px"
                txt=r.choice(["직인","인","접수","확인","○○시장","담당"])
                inner=(f'<span class="dist" style="left:@Xpx;top:@Ypx;width:{z}px;height:{z}px;border:{round(r.uniform(1.6,4),1)}px solid {col};'
                       f'border-radius:{rad};color:{col};display:flex;align-items:center;justify-content:center;text-align:center;'
                       f'font-size:{max(11,int(z/(2 if len(txt)>2 else 2.6)))}px;font-weight:700;opacity:{round(r.uniform(.5,.95),2)};'
                       f'transform:rotate({r.randint(-25,25)}deg)">{txt}</span>')
                out.append(self._float(inner, r.randint(int(W*.45),max(int(W*.45)+1,W-140)), r.randint(-70,20)))
            elif k=="logo":
                z=r.randint(22,46); col=r.choice(["#1F4E79","#2E6B3E","#7a1f1c","#444","#8a6d1f"])
                sh=r.choice([f'border-radius:50%',f'border-radius:4px',f'transform:rotate(45deg)'])
                inner=(f'<span class="dist" style="left:@Xpx;top:@Ypx;display:flex;align-items:center;gap:6px">'
                       f'<span style="width:{z}px;height:{z}px;background:{col};{sh};display:inline-block"></span>'
                       f'<span style="font-size:{r.randint(12,20)}px;color:{col};font-weight:700">{org}</span></span>')
                out.append(self._float(inner, r.randint(10,max(11,int(W*.35))), r.randint(-40,10)))
            elif k=="watermark":
                fs=r.randint(52,120)
                inner=(f'<span class="dist" style="left:@Xpx;top:@Ypx;font-size:{fs}px;color:#{r.choice(["c9","d4","dd","bf"])*3};'
                       f'opacity:{round(r.uniform(.25,.6),2)};white-space:nowrap;letter-spacing:.2em;font-weight:700;'
                       f'transform:rotate({r.choice([-35,-30,-25,25,30,35])}deg)">{r.choice(["견 본","사 본","SAMPLE","대외비","예 시"])}</span>')
                out.append(self._float(inner, r.randint(0,max(1,int(W*.35))), r.randint(-120,40)))
            elif k=="notice":
                out.append(f'<div class="note" style="border:1px {r.choice(["dotted","dashed","solid"])} #888;padding:{r.randint(4,9)}px {r.randint(6,14)}px;'
                           f'margin:{r.randint(4,14)}px 0;background:{r.choice(["transparent","#f7f7f7"])}">※ '
                           +(self.P(8,34,1.0) or "기재 사항이 사실과 다른 경우 지원이 제한될 수 있습니다")+'</div>')
            elif k=="pageno":
                out.append(f'<div class="note" style="text-align:{r.choice(["center","right","left"])};margin:{r.randint(4,16)}px 0;color:#444">'
                           +r.choice([f"- {r.randint(1,9)} -",f"{r.randint(1,9)} / {r.randint(2,12)}",f"({r.randint(1,9)}쪽)"])+'</div>')
            else:   # 접수인란
                w=r.randint(70,130); h=r.randint(46,86)
                inner=(f'<span class="dist" style="left:@Xpx;top:@Ypx;width:{w}px;height:{h}px;border:{round(r.uniform(.8,1.8),1)}px solid #333;'
                       f'display:flex;align-items:flex-start;justify-content:center;padding-top:3px;font-size:{r.randint(10,13)}px;color:#333">'
                       +r.choice(["접수인","접수","수 신 인","확인란"])+'</span>')
                out.append(self._float(inner, r.randint(max(0,W-200),max(1,W-120)), r.randint(-30,10)))
        return out
    # ── 데코이 ──
    def decoys(self):
        out=[]; D=self.sk["decoys"]
        if "인쇄 수신처 열거" in D: out.append('<p class="ln" style="margin-top:10px"><b>특별자치시장·특별자치도지사·시장·군수·구청장</b> 귀하</p>')
        if "점선 절취선" in D: out.append('<div style="border-top:1.6px dashed #000;margin:20px 0 4px"></div><p class="note center">〈 절취선 〉</p>')
        if "(단위:) 캡션" in D: out.append('<p class="note" style="text-align:right">(단위 : 명)</p>')
        if "처리절차 플로차트" in D:
            box='<span style="display:inline-block;border:1px solid #000;padding:4px 12px;font-size:13px">%s</span>'
            out.append('<p class="center" style="margin:14px 0">'+ " → ".join(box%x for x in ["신청서 작성","접수","검토","결과 통보"])+'</p>')
        if "인쇄 상수 셀" in D: pass  # 접수밴드의 '즉시'가 담당
        return out
    def pf(self,k):
        """prefill 직교상태: 인쇄된 내용을 무시하고 덮어쓰는 입력 — 인쇄물 포함 전체가 라벨 영역"""
        n='<span class="note">'
        m={"pf_example":f'<table><tr><td class="tl lb2">관찰 내용 {n}(예시를 참고하여 기재)</span></td></tr>'
             f'<tr><td style="height:56px"><span data-f="textarea" class="cg" style="height:48px">{n}예) 아동이 먼저 인사말을 건네고 착석하였습니다.</span></span></td></tr></table>',
           "pf_sample":ROW("담당자 성명 :",PH("text","○○○"),f'{n}(</span>',PH("text","○○○"),'<span class="note">기관)</span>',style="margin:6px 0"),   # v3: 박스 = 글자
           "pf_filled":(lambda tv,mv: f'<table><tr><th style="width:118px">활동시간</th><td class="vl"><span data-f="time" class="cg" style="line-height:26px">{tv}</span></td>'
             f'<th style="width:118px">금액</th><td class="vl"><span data-f="number" class="cg" style="line-height:26px">{mv}</span></td></tr></table>')(
             self.rng.choice(["17:00 ~ 17:50","09:30 ~ 11:20","14:00 ~ 15:40","10:00 ~ 12:00"]),
             self.rng.choice(["27,500원","41,300원","15,000원","33,800원"])),
           "pf_mask":ROW("20",PH("date","○○"),"년",PH("date","○○"),"월",PH("date","○○"),"일",j="c",style="gap:2px"),
           "pf_circle":(lambda r: ROW(*r.choice([
               ["○ 교육일시 : 20",PH("date","○○"),".",PH("date","○",w=r.randint(22,31)),".",PH("date","○",w=r.randint(22,31)),". &nbsp; 장소 :",PH("text","○○○"),"교육장"],
               ["○ 기간 : 20",PH("date","○○"),"년",PH("date","○",w=r.randint(22,31)),"월 ~ 20",PH("date","○○"),"년",PH("date","○",w=r.randint(22,31)),"월"],
               ["○ 대상 :",PH("text","○○○"),"외",PH("number","○",w=r.randint(20,28)),"명 &nbsp; 담당 :",PH("text","○○○"),"(☎",PH("phone","○○○-○○○○"),")"]]),
               style="margin:6px 0;gap:2px;font-size:"+str(r.choice([14,15,16]))+"px"))(self.rng),   # v3 낱글자 ○ 자리표 (실서식 21_x호·2편 16호)
           "pf_note":f'<table><tr><th style="width:130px">처리기한<br>경과사유</th><td style="height:48px">'
             f'<span data-f="textarea" class="cg" style="height:40px">{n}※ 처리기한 경과 시 사유를 기재합니다</span></span></td></tr></table>',
           "pf_label":f'<table><tr><th style="width:118px">대상 아동</th><td><span data-f="text" class="cg" style="line-height:26px">{n}※ 개인별 성명 전체 명시</span></span></td></tr></table>',
           "pf_italic":f'<table><tr><td class="tl lb2">의견</td></tr><tr><td style="height:48px">'
             f'<span data-f="textarea" class="cg" style="height:40px"><i class="note">예) 서비스 확대가 필요합니다.</i></span></td></tr></table>',
           "pf_year20":ROW("20",SLOT(),"년",SLOT(),"월",SLOT(),"일",j="c",style="margin-top:16px"),
        }
        return m.get(k,"")
    def cert_html(self):
        """상장형 레이아웃(수료증·지정서) — 복제유래_확장풀 cert_layout"""
        r=self.rng
        SET=r.choice([("수 료 증","과정을 수료하였으므로 이 증서를 수여합니다.","장"),
                      ("지 정 서","기관으로 지정하였음을 증명합니다.","시장·군수·구청장"),
                      ("위 촉 장","위원으로 위촉합니다.","기관장")])
        title=SET[0]
        no=f'제 {r.randint(1,99)}-{r.randint(1,999)} 호'
        fields="".join(ROW(f'<span style="letter-spacing:.4em">{lb}</span> :',
                           f'<span data-f="{t}" class="gp" style="width:220px"></span>',style="margin:6px 0;justify-content:flex-start;padding-left:180px")
                       for lb,t in [("성명","text"),("생년월일","date"),("소속","text")][:r.randint(2,3)])
        decl=ROW("위 사람은",'<span data-f="text" class="gp" style="width:170px"></span>',
                 SET[1],
                 j="c",style="margin:56px 0 40px;font-size:19px")
        date=ROW(SLOT(),"년",SLOT(),"월",SLOT(),"일",j="c",style="margin:64px 0 40px;font-size:19px")
        issuer=ROW('<span data-f="text" style="display:inline-flex;width:70px;height:30px;align-items:center;justify-content:center;font-size:22px">○○○</span>',
                   f'<span style="font-size:26px;font-weight:700;letter-spacing:.3em">{SET[2]}</span>',
                   '<span data-f="signature" style="display:inline-flex;border:2.2px solid #B02B25;color:#B02B25;padding:8px 12px;margin-left:14px">직인</span>',
                   j="c",style="margin-top:30px")
        body=(f'<div class="byulji">[별지 제{r.randint(1,29)}호서식]</div>'
              f'<h1 class="doctitle" style="font-size:44px;letter-spacing:.9em;margin:70px 0 30px">{title}</h1>'
              f'<p style="margin:0 0 40px 40px">{no}</p>{fields}{decl}{date}{issuer}'
              '<p class="paper">210mm×297mm[백상지(80g/㎡) 또는 중질지(80g/㎡)]</p>')
        return f"<!doctype html><meta charset=utf8><style>{hwp_css(self.theme)}</style><body>{body}</body>"

    def html(self):
        if self.sk["type"]=="증서" and self.rng.random()<0.6:
            return self.cert_html()
        F={"제목":self.b_제목,"인적표":self.b_인적표,"선택군":self.b_선택군,"서술":self.b_서술,
           "격자":self.b_격자,"금액":self.b_금액,"날짜줄":self.b_날짜줄,"시각":self.b_시각,
           "서명줄":self.b_서명줄,"수신줄":self.b_수신줄,"동의문단":self.b_동의문단,
           "고지표":self.b_고지표,"접수밴드":self.b_접수밴드,"글머리서술":self.b_글머리서술,"사진":self.b_사진}
        ACT={"제목":"식별","접수밴드":"식별",
             "인적표":"본문","선택군":"본문","서술":"본문","격자":"본문","금액":"본문","사진":"본문",
             "고지표":"본문","동의문단":"본문","글머리서술":"본문","시각":"본문",
             "날짜줄":"작성","서명줄":"작성","수신줄":"수신"}
        dens=self.theme["dens"]   # v4: 밀도 프로파일 연속 0.55~1.7
        PF_ALLOW={"pf_filled":{"기록지","명세신고","보고서","접수증","작성례"},"pf_note":{"판단서","통지회신","조회요청서","점검평가","작성례"},
                  "pf_example":{"사정조사지","기록지","점검평가","작성례"},"pf_label":{"안내문","신청서","동의서","작성례"},
                  "pf_italic":{"점검평가","기록지","사정조사지","작성례"}}
        items=[(F[b["block"]](b), ACT.get(b["block"],"본문"), b["block"]) for b in self.sk["blocks"] if b["block"] in F]
        body_idx=[i for i,(_,a,_n) in enumerate(items) if a=="본문"]
        for k in self.sk.get("prefill",[]):
            tgt=None
            if isinstance(k,dict): tgt=k.get("target"); k=k.get("kind")
            allow=PF_ALLOW.get(k)
            if allow is not None and self.sk["type"] not in allow: continue
            f=self.pf(k)
            if f and body_idx:
                pos=(min(body_idx,key=lambda i:abs(i-tgt)) if isinstance(tgt,int) else self.rng.choice(body_idx))+1
                items.insert(pos,(f,"본문","prefill")); body_idx=[i for i,(_,a,_n) in enumerate(items) if a=="본문"]
        parts=[]; prev_act=None; prev_tbl=False; prev_blk=None
        for frag,act,blk in items:
            is_tbl=frag.lstrip().startswith("<table")
            if prev_act is None: gap=0
            elif act!=prev_act: gap=int(self.rng.uniform(14,32)*dens)   # v4 연속 지터
            elif is_tbl and prev_tbl and blk==prev_blk and self.rng.random()<0.5: gap=-1   # 같은 의미군 표만 괘선 공유
            else: gap=int(self.rng.uniform(3,16)*dens)
            if blk=="제목" and prev_act is not None and self.sk["type"]=="접수증":   # 2회전 절취선
                parts.append('<div style="border-top:1.6px dashed #000;margin:22px 0 4px"></div><p class="note center">〈 절취선 〉</p>')
            parts.append(f'<div style="margin-top:{gap}px">{frag}</div>' if gap else frag)
            prev_act, prev_tbl, prev_blk = act, is_tbl, blk
        parts+=self.decoys()
        for d in self.distractors():   # v4 비대상 방해물: 흐름 곳곳에 섞는다(부분 겹침 허용)
            parts.insert(self.rng.randint(0,len(parts)), d)
        parts.append('<p class="paper">210mm×297mm[백상지(80g/㎡) 또는 중질지(80g/㎡)]</p>')
        html=f"<!doctype html><meta charset=utf8><style>{hwp_css(self.theme)}</style><body>{''.join(parts)}</body>"
        return html.replace("width:118px", f"width:{self.theme['lbw']}px")

async def render_all(files, outdir):
    from playwright.async_api import async_playwright
    os.makedirs(outdir, exist_ok=True)
    results=[]
    async with async_playwright() as pw:
        b=await pw.chromium.launch(); pages={}
        for f in files:
            sk=json.load(open(f)); r=R(sk); html=r.html()
            # v4 ⑤ 배율·뷰포트: device_scale_factor 는 컨텍스트 옵션이라 배율별로 페이지를 재사용한다
            dsf=round(r.theme["dsf"],2); vw=r.theme["page_w"]
            if dsf not in pages:
                ctx=await b.new_context(device_scale_factor=dsf, viewport={"width":vw,"height":1400})
                pages[dsf]=await ctx.new_page()
            pg=pages[dsf]
            await pg.set_viewport_size({"width":vw,"height":1400})
            hp=os.path.join(outdir, sk["id"]+".html"); open(hp,"w").write(html)
            await pg.goto("file://"+os.path.abspath(hp)); await pg.wait_for_timeout(250)
            # GT 는 장치 픽셀(=PNG 픽셀). getBoundingClientRect 는 CSS 픽셀이라 devicePixelRatio 를 곱한다.
            boxes=await pg.evaluate("""() => {const s=window.devicePixelRatio;
                return [...document.querySelectorAll('[data-f]')].map(e=>{
                const r=e.getBoundingClientRect();
                return {t:e.dataset.f,x:r.x*s,y:r.y*s,w:r.width*s,h:r.height*s}})}""")
            png=os.path.join(outdir, sk["id"]+".png")
            await pg.screenshot(path=png, full_page=True)
            json.dump(boxes, open(os.path.join(outdir, sk["id"]+"_gt.json"),"w"))
            json.dump(r.theme, open(os.path.join(outdir, sk["id"]+"_theme.json"),"w"), ensure_ascii=False)   # v4 사후 분석용
            results.append((sk["id"], len(boxes), sorted(r.missing)))
        await b.close()
    return results

if __name__=="__main__":
    files=[a for a in sys.argv[1:] if a.endswith(".json")]
    out="5_dataset/render_check"
    if "--out" in sys.argv: out=sys.argv[sys.argv.index("--out")+1]
    res=asyncio.run(render_all(files,out))
    for rid,n,miss in res:
        print(f"{rid}: 요소 {n}개" + (f" | 대체 렌더: {miss}" if miss else ""))
