"""골격 샘플러 v1 — mix 결정서(2026-09-04) 구현.
유형 배분 + 온도완화(α=.5) 카드 선택 + IRFS식 부족분 부스트 + 문서변수(글리프 규약·prefill·데코이).
산출: 골격 JSON (렌더 전 단계 — 2번 증강에서 재사용).
  python build_skeleton.py --n 200 --out runs/skeletons_smoke   # 스모크
"""
import json, random, argparse, os, math, collections

# ── 유형 배분 (합 20000) ──────────────────────────────────────────────
QUOTA = {  # v2.1: 문법 합성 단일 트랙 20,000 (복제는 채굴·검증 자료 — 생산 트랙 아님)
 "신청서":2990,"보고서":2490,"동의서":2340,"계획서":1210,"대장명부":930,"증서":930,"계약서":780,"점검평가":830,"확약서":760,"사정조사지":800,"기록지":610,"안내문":760,"공고문":640,"명세신고":480,"판단서":610,"조회요청서":580,"통지회신":580,"등록카드":410,"접수증":610,"작성요령서":530,"백지":130}
assert sum(QUOTA.values())==20000

# ── 블록 클래스 → 호환 카드 (실측빈도 근사 가중치) ────────────────────
CARDS = {
 "인적표":{"text_cell":30,"cell_sublabel":4,"dot_box":3,"split_hyphen":6,"comb_slot":3,
          "ph_cell":8,"em_cell":3,"text_suffix":3,"mix_cell":4,"img_cell":4,"num_unit":6,
          "date_split":6,"date_cell":8,"ph_multi":3,"radio_word":5,"ph_pict":2,"dot_split":2,"inset_label":3},
 "선택군":{"cb_row":22,"cb_wrap":10,"cb_col":6,"cb_grid":8,"cb_bracket":8,"radio_yn":10,
          "radio_word":6,"radio_paren":4,"radio_circled":4,"cb_sub":4,"cb_dep":8,
          "cb_inline_parent":4,"cb_parent":5,"cb_prose":3,"header_opts":2},
 "서술":{"ta_cell":16,"ta_free":5,"ta_below":4,"ta_outline":5},
 "격자":{"num_cell":20,"date_cell":8,"grid_diag":3,"cb_matrix":4,"radio_likert":5,
        "radio_grid":4,"cal_grid":2,"date_slash":3,"scale_anchor":2,"header_opts":3,
        "stub_input":3,"num_denom":2},
 "금액":{"num_unit":10,"num_both":4,"num_bracket":3,"paren_unit":4,"num_affix":2},
 "날짜줄":{"date_split":10,"date_inline":6,"date_dots":4,"date_range":5,"pf_year20":6},
 "시각":{"time_split":5,"time_cell":4},
 "서명줄":{"sig_phrase":12,"sig_name":6,"sig_ul":5,"sig_stamp":3,"sig_stamp_paren":3,"sig_bold":3},
 "수신줄":{"text_recipient":8},
 "동의문단":{"consent":8,"consent_check":5},
 "제목":{"평제목":30,"cb_title":4,"title_paren":6},
 "고지표":{"text_cell":10,"cell_sublabel":2},
 "접수밴드":{"text_paren":6,"text_cell":4},
 "글머리서술":{"ta_outline":8,"text_prose":5,"text_colon":6,"text_ul":6,"text_paren":4,"legal_prose":4,"notice_band":3},
 "사진":{"img_cell":6,"img_card":3},
}
DECOY = ["처리절차 플로차트","인쇄 수신처 열거","점선 절취선","(단위:) 캡션","인쇄 상수 셀"]  # 렌더 구현 5종만(골격↔렌더 일치)
PF = ["pf_year20","pf_example","pf_sample","pf_filled","pf_mask","pf_note","pf_label","pf_italic"]

# ── 유형별 블록 문법: (블록클래스, 최소, 최대) ───────────────────────
GRAMMAR = {
 "신청서":[("제목",1,1),("접수밴드",0,1),("인적표",1,2),("선택군",1,3),("격자",0,1),("금액",0,1),
          ("동의문단",0,1),("날짜줄",1,1),("서명줄",1,1),("수신줄",1,1)],
 "동의서":[("제목",1,1),("인적표",0,1),("고지표",1,2),("동의문단",1,2),("선택군",0,2),("날짜줄",1,1),
          ("서명줄",1,1),("수신줄",0,1)],
 "계약서":[("제목",1,1),("인적표",1,2),("글머리서술",2,4),("날짜줄",1,1),("서명줄",2,2)],
 "판단서":[("제목",1,1),("인적표",1,1),("선택군",1,1),("서술",2,3),("인적표",1,1),
          ("날짜줄",1,1),("서명줄",1,1)],
 "통지회신":[("제목",1,1),("인적표",1,1),("선택군",1,2),("격자",0,2),("서술",0,1),
            ("날짜줄",1,1),("서명줄",1,1)],
 "조회요청서":[("접수밴드",1,1),("인적표",2,2),("글머리서술",1,1),("날짜줄",1,1),
             ("서명줄",1,1),("수신줄",1,1)],
 "공고문":[("제목",1,1),("날짜줄",1,1),("글머리서술",3,6),("서명줄",1,1)],
 "증서":[("제목",1,1),("인적표",1,1),("글머리서술",1,1),("날짜줄",1,1),("서명줄",1,1)],
 "확약서":[("제목",1,1),("글머리서술",2,5),("날짜줄",1,1),("서명줄",1,1),("수신줄",0,1)],
 "보고서":[("제목",1,1),("격자",2,6)],
 "대장명부":[("제목",1,1),("격자",1,2)],
 "기록지":[("제목",1,1),("인적표",1,1),("격자",1,2),("금액",0,1),("시각",0,1),("서명줄",1,1)],
 "계획서":[("제목",1,1),("글머리서술",1,3),("격자",1,3),("금액",0,1)],
 "점검평가":[("제목",1,1),("인적표",1,1),("격자",1,2),("서술",1,2)],
 "사정조사지":[("인적표",2,3),("선택군",2,4),("격자",1,2),("서술",2,4),("시각",0,1)],
 "명세신고":[("제목",1,1),("격자",2,3)],
 "등록카드":[("접수밴드",1,1),("인적표",2,2),("사진",1,1),("격자",2,2),("날짜줄",1,1),
           ("서명줄",2,2),("수신줄",1,2)],
 "접수증":[("제목",1,1),("인적표",1,1),("날짜줄",1,1),("수신줄",1,1),
          ("제목",1,1),("인적표",1,1),("날짜줄",1,1)],  # 절취 2회전
 "안내문":[("제목",1,1),("글머리서술",3,6),("격자",0,1)],
 "작성요령서":[("제목",1,1),("글머리서술",4,7)],
 "백지":[],
}
NO_INPUT = {"안내문","작성요령서","백지","공고문"}  # 음성·희박형
GRID_ALLOW = {  # 격자 카드 의미 게이팅 (미기재 유형은 범용 세트만)
 "점검평가":{"radio_likert","scale_anchor","num_denom","radio_grid","cb_matrix","num_cell","grid_diag","stub_input"},
 "사정조사지":{"radio_likert","radio_grid","cb_matrix","header_opts","scale_anchor","num_cell","stub_input"},
 "기록지":{"cal_grid","date_slash","num_cell","date_cell","cb_matrix"},
 "보고서":{"num_cell","date_cell","grid_diag","stub_input"},
 "대장명부":{"num_cell","date_cell","grid_diag","stub_input"},
 "등록카드":{"num_cell","date_cell","stub_input"},
 "계획서":{"num_cell","date_cell","grid_diag","stub_input"},
 "명세신고":{"num_cell","date_cell","grid_diag"},
 "통지회신":{"num_cell","date_cell","stub_input"},
 "신청서":{"num_cell","stub_input"},
 "안내문":{"num_cell","stub_input"},
}
GENERIC_GRID = {"num_cell","date_cell","grid_diag","stub_input"}

class Sampler:
    def __init__(self, n_total, seed=20260904):
        self.rng = random.Random(seed)
        self.n_total = n_total
        scale = n_total/20000
        self.quota = {t: max(1,round(q*scale)) for t,q in QUOTA.items()}
        self.card_count = collections.Counter()
        self.card_target = {}  # IRFS 목표: 총 요소수 비례 균형 하한
        allc = {c for m in CARDS.values() for c in m}
        for c in allc: self.card_target[c] = max(1, round(800*scale))
    def w(self, block):
        """온도완화(√실측가중) × IRFS 부족분 부스트"""
        out={}
        for c,f in CARDS[block].items():
            base = math.sqrt(f)
            need = self.card_target[c]; have = self.card_count[c]
            boost = math.sqrt(max(1.0, need/max(have,1)))
            out[c] = base*boost
        return out
    def pick(self, block):
        w=self.w(block); cs=list(w); ws=[w[c] for c in cs]
        c=self.rng.choices(cs,ws)[0]; self.card_count[c]+=1; return c
    def page(self, dtype, idx):
        rng=self.rng
        glyph = rng.choices(["marker_only","bullet_only","mixed"],[50,30,20])[0]
        variant = rng.random()<0.12   # 5막 이탈 변주
        blocks=[]
        pure_print = dtype in NO_INPUT and dtype!="백지" and rng.random()<0.6
        for bclass,lo,hi in GRAMMAR[dtype]:
            for _ in range(rng.randint(lo,hi)):
                card = self.pick(bclass)
                if bclass=="격자":
                    allow=GRID_ALLOW.get(dtype,GENERIC_GRID)
                    tries=0
                    while card not in allow and tries<12: card=self.pick(bclass); tries+=1
                    if card not in allow: card=rng.choice(sorted(allow))
                if dtype=="판단서" and card=="split_hyphen": card="text_cell"   # 제3자 문서 주민번호 배제
                if dtype=="증서" and bclass=="글머리서술": card="text_prose"     # 수료 선언문
                b={"block":bclass,"card":card}
                if bclass in ("선택군",): b["n_options"]=rng.choice([2,2,3,3,4,4,5,6,8,10,15])
                if bclass=="격자": b["rows"]=rng.randint(3,12); b["cols"]=rng.randint(3,9)
                blocks.append(b)
        if pure_print:   # 음성 클래스: 입력칸 0 문서 (제목+인쇄 문단·고지표만)
            blocks=[{"block":"제목","card":"평제목"},
                    {"block":"동의문단","card":"consent"}]
            if rng.random()<0.6: blocks.append({"block":"고지표","card":"text_cell"})
            if rng.random()<0.5: blocks.append({"block":"동의문단","card":"consent"})
        # prefill: 요소 토막 10% (5~15 균등)
        pf_rate = 0 if pure_print else rng.uniform(0.05,0.15)
        pf=[]; used_pf=set()
        for i,b in enumerate(blocks):
            if rng.random()<pf_rate:
                k=rng.choice([p for p in PF if p not in used_pf] or PF)
                used_pf.add(k); pf.append({"target":i,"kind":k})
        # 데코이 0~3
        nd = rng.choices([0,1,2,3],[30,40,20,10])[0]
        decoys = rng.sample(DECOY, nd)
        return {"id":f"{dtype}_{idx:05d}","type":dtype,"glyph_rule":glyph,
                "five_act_variant":variant,"blocks":blocks,"prefill":pf,"decoys":decoys,
                "seed":rng.randrange(2**31)}
    def run(self, outdir):
        os.makedirs(outdir,exist_ok=True)
        pages=[]
        order=[t for t,q in self.quota.items() for _ in range(q)]
        self.rng.shuffle(order)
        for i,t in enumerate(order):
            pages.append(self.page(t,i))
        for p in pages:
            json.dump(p, open(os.path.join(outdir,p["id"]+".json"),"w"), ensure_ascii=False)
        return pages

if __name__=="__main__":
    ap=argparse.ArgumentParser(); ap.add_argument("--n",type=int,default=200)
    ap.add_argument("--out",default="runs/skeletons_smoke"); a=ap.parse_args()
    s=Sampler(a.n); pages=s.run(a.out)
    tc=collections.Counter(p["type"] for p in pages)
    print(f"골격 {len(pages)}장 → {a.out}")
    print("유형 분포:", dict(tc))
    cc=s.card_count
    print(f"카드 종수 사용: {len(cc)} | 총 요소블록 {sum(cc.values())}")
    print("최다 5:", cc.most_common(5))
    rare=sorted(cc.items(), key=lambda x:x[1])[:8]
    print("최소 8:", rare)
    zero=[c for c in s.card_target if cc[c]==0]
    print("미사용 카드:", zero if zero else "없음")
