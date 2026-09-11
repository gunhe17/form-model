"""골격 샘플러 v1 — mix 결정서(2026-09-04) 구현.
유형 배분 + 온도완화(α=.5) 카드 선택 + IRFS식 부족분 부스트 + 문서변수(글리프 규약·prefill·데코이).
산출: 골격 JSON (렌더 전 단계 — 2번 증강에서 재사용).
  python 3_generator/build_skeleton.py --n 200 --out 5_dataset/skeletons/smoke   # 스모크
"""
import json, random, argparse, os, math, collections

# ── 유형 배분 (합 20000) ──────────────────────────────────────────────
QUOTA = {  # v2.1: 문법 합성 단일 트랙 20,000 (복제는 채굴·검증 자료 — 생산 트랙 아님)
 "신청서":1200,"보고서":650,"동의서":1400,"계획서":650,"대장명부":400,"증서":1100,"계약서":1000,"점검평가":830,"확약서":710,"사정조사지":750,"기록지":760,"안내문":710,"공고문":640,"명세신고":170,"판단서":760,"조회요청서":580,"통지회신":580,"등록카드":850,"접수증":850,"작성요령서":480,"백지":130,
 "사진대지":1100,"서명부":1400,"진술서":900,"작성례":500,   # P1-F: 부족 클래스(photo·signature·underline·placeholder)를 논리적으로 요구하는 유형
 "부품집중":500,   # P1: 부품 집중 페이지 — 드문 클래스의 절대 수·치수 변화폭 채움
 "희소":400}       # v4: 입력 1~3개짜리 희박 페이지 2% (백지·순인쇄 음성 6%와 별개)
assert sum(QUOTA.values())==20000

# ── 블록 클래스 → 호환 카드 (실측빈도 근사 가중치) ────────────────────
CARDS = {  # P1 재가중: cell 계열↓ / gap·marker·comb·underline·placeholder·signature·photo↑
 "인적표":{"text_cell":12,"cell_sublabel":3,"dot_box":2,"split_hyphen":8,"comb_slot":6,
          "ph_cell":4,"em_cell":2,"text_suffix":5,"mix_cell":6,"img_cell":6,"num_unit":7,
          "date_split":6,"date_cell":4,"ph_multi":5,"radio_word":3,"ph_pict":4,"dot_split":2,"inset_label":2,
          "ph_lines":6,"gp_cell":6,"ul_cell":5,"sig_cell":8,"comb_jumin":6,"dbx_cell":3,"inset_label_full":4,"inline_pairs":8},   # v3 inline_pairs
 "선택군":{"cb_row":22,"cb_wrap":10,"cb_col":8,"cb_grid":8,"cb_bracket":10,"radio_yn":10,
          "radio_word":3,"radio_paren":5,"radio_circled":5,"cb_sub":5,"cb_dep":8,
          "cb_inline_parent":5,"cb_parent":5,"cb_prose":4,"header_opts":1},
 "서술":{"ta_cell":8,"ta_free":5,"ta_below":4,"ta_outline":5},
 "격자":{"num_cell":10,"date_cell":5,"grid_diag":3,"cb_matrix":5,"radio_likert":6,
        "radio_grid":3,"cal_grid":2,"date_slash":4,"scale_anchor":5,"scale_words":4,"header_opts":2,
        "stub_input":3,"num_denom":2,"photo_grid":3,"sig_grid":3,"pf_grid":3},
 "금액":{"num_unit":10,"num_both":7,"num_bracket":4,"paren_unit":5,"num_affix":3},
 "날짜줄":{"date_split":10,"date_inline":6,"date_dots":5,"date_range":6,"pf_year20":8,"comb_date":5,"date_tight":7},   # v3 date_tight
 "시각":{"time_split":5,"time_cell":4},
 "서명줄":{"sig_phrase":12,"sig_name":6,"sig_ul":7,"sig_stamp":5,"sig_stamp_paren":5,"sig_bold":2,"stamp_box":3},
 "수신줄":{"text_recipient":8},
 "동의문단":{"consent":6,"consent_check":6,"consent_pair":10},
 "제목":{"평제목":20,"cb_title":6,"title_paren":8},
 "고지표":{"text_cell":10,"cell_sublabel":2},
 "접수밴드":{"text_paren":6,"text_cell":4},
 "글머리서술":{"ta_outline":5,"text_prose":8,"text_colon":9,"text_ul":9,"text_paren":6,"legal_prose":4,"notice_band":3,"ul_lines":6},
 "사진":{"img_cell":6,"img_card":3,"img_circle":3},
}
DECOY = ["처리절차 플로차트","인쇄 수신처 열거","점선 절취선","(단위:) 캡션","인쇄 상수 셀"]  # 렌더 구현 5종만(골격↔렌더 일치)
PF = ["pf_year20","pf_example","pf_sample","pf_filled","pf_mask","pf_note","pf_label","pf_italic","pf_circle"]   # v3 pf_circle

# ── 유형별 블록 문법: (블록클래스, 최소, 최대) ───────────────────────
GRAMMAR = {
 "신청서":[("제목",1,1),("접수밴드",0,1),("인적표",1,2),("선택군",2,3),("격자",0,1),("금액",0,1),
          ("동의문단",0,1),("날짜줄",1,1),("서명줄",1,1),("수신줄",1,1)],
 "동의서":[("제목",1,1),("인적표",0,1),("고지표",1,2),("동의문단",2,4),("선택군",1,2),("날짜줄",1,1),
          ("서명줄",1,2),("수신줄",0,1)],
 "계약서":[("제목",1,1),("인적표",1,2),("선택군",0,1),("글머리서술",2,4),("날짜줄",1,1),("서명줄",2,3)],
 "판단서":[("제목",1,1),("인적표",1,1),("선택군",1,2),("서술",2,3),("인적표",1,1),
          ("날짜줄",1,1),("서명줄",1,1)],
 "통지회신":[("제목",1,1),("인적표",1,1),("선택군",1,2),("격자",0,2),("서술",0,1),
            ("날짜줄",1,1),("서명줄",1,1)],
 "조회요청서":[("접수밴드",1,1),("인적표",2,2),("글머리서술",1,1),("날짜줄",1,1),
             ("서명줄",1,1),("수신줄",1,1)],
 "공고문":[("제목",1,1),("날짜줄",1,1),("글머리서술",3,6),("서명줄",1,1)],
 "증서":[("제목",1,1),("인적표",1,1),("글머리서술",1,1),("날짜줄",1,1),("서명줄",1,1)],
 "확약서":[("제목",1,1),("글머리서술",2,5),("날짜줄",1,1),("서명줄",1,2),("수신줄",0,1)],
 "보고서":[("제목",1,1),("격자",2,6)],
 "대장명부":[("제목",1,1),("격자",1,2)],
 "기록지":[("제목",1,1),("인적표",1,1),("선택군",0,1),("격자",1,2),("금액",0,1),("시각",0,1),("서명줄",1,1)],
 "계획서":[("제목",1,1),("글머리서술",1,3),("격자",1,3),("금액",0,1)],
 "점검평가":[("제목",1,1),("인적표",1,1),("격자",1,2),("서술",1,2)],
 "사정조사지":[("인적표",2,3),("선택군",2,5),("격자",1,2),("서술",2,4),("시각",0,1)],
 "명세신고":[("제목",1,1),("격자",2,3)],
 "등록카드":[("접수밴드",1,1),("인적표",2,2),("사진",1,1),("선택군",0,1),("격자",2,2),("날짜줄",1,1),
           ("서명줄",2,2),("수신줄",1,2)],
 "접수증":[("제목",1,1),("인적표",1,1),("선택군",0,1),("날짜줄",1,1),("수신줄",1,1),
          ("제목",1,1),("인적표",1,1),("날짜줄",1,1)],  # 절취 2회전
 "안내문":[("제목",1,1),("글머리서술",3,6),("격자",0,1)],
 "작성요령서":[("제목",1,1),("글머리서술",4,7)],
 "백지":[],
 "사진대지":[("제목",1,1),("인적표",0,1),("격자",1,2),("날짜줄",0,1),("서명줄",1,1)],
 "서명부":[("제목",1,1),("인적표",0,1),("격자",1,1),("날짜줄",0,1)],
 "진술서":[("제목",1,1),("인적표",1,1),("글머리서술",2,4),("날짜줄",1,1),("서명줄",2,2)],
 "작성례":[("제목",1,1),("인적표",1,1),("격자",1,2),("날짜줄",0,1)],
 "희소":[("제목",1,1),("금액",1,1),("시각",0,1)],   # v4 희박 페이지
 "부품집중":[("인적표",2,3),("선택군",1,3),("격자",1,1),("날짜줄",1,2),("서명줄",1,2),
            ("글머리서술",1,2),("사진",0,1),("금액",0,1),("시각",0,1)],
}
NO_INPUT = {"안내문","작성요령서","백지","공고문"}  # 음성·희박형
GRID_ALLOW = {  # 격자 카드 의미 게이팅 (미기재 유형은 범용 세트만)
 "점검평가":{"radio_likert","scale_anchor","scale_words","num_denom","radio_grid","cb_matrix","num_cell","grid_diag","stub_input","photo_grid"},
 "사정조사지":{"radio_likert","radio_grid","cb_matrix","header_opts","scale_anchor","scale_words","num_cell","stub_input"},
 "부품집중":{"radio_likert","cb_matrix","scale_anchor","scale_words","date_slash","num_cell","date_cell","stub_input"},
 "기록지":{"cal_grid","date_slash","num_cell","date_cell","cb_matrix","sig_grid","photo_grid"},
 "보고서":{"num_cell","date_cell","grid_diag","stub_input"},
 "대장명부":{"num_cell","date_cell","grid_diag","stub_input"},
 "등록카드":{"num_cell","date_cell","stub_input","sig_grid"},
 "접수증":{"num_cell","date_cell","stub_input","sig_grid"},
 "사진대지":{"photo_grid"},"서명부":{"sig_grid"},"작성례":{"pf_grid"},
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
        for c in allc: self.card_target[c] = max(1, round(1200*scale))
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
                if dtype=="희소" and bclass=="제목": card="평제목"   # v4: 희박 페이지 제목은 입력 없는 평제목
                if dtype=="판단서" and card=="split_hyphen": card="text_cell"   # 제3자 문서 주민번호 배제
                if dtype=="증서" and bclass=="글머리서술": card="text_prose"     # 수료 선언문
                if dtype=="진술서" and bclass=="글머리서술":                        # 문장 속 밑줄 위주
                    card=rng.choices(["ul_lines","text_ul","text_prose"],[20,6,4])[0]; self.card_count[card]+=1
                b={"block":bclass,"card":card}
                if bclass in ("선택군",): b["n_options"]=rng.choice([3,4,4,5,6,6,8,10,12,15])
                if bclass=="격자":
                    b["rows"]=rng.randint(2,6); b["cols"]=rng.randint(3,7)
                    if card=="photo_grid": b["rows"]=rng.randint(2,3); b["cols"]=2      # 사진 4~6
                    elif card=="sig_grid": b["rows"]=rng.randint(8,12); b["cols"]=2     # 성명+서명 6~14행
                    elif card=="pf_grid": b["rows"]=rng.randint(4,6); b["cols"]=rng.randint(3,5)
                blocks.append(b)
        if pure_print:   # 음성 클래스: 입력칸 0 문서 (제목+인쇄 문단·고지표만)
            blocks=[{"block":"제목","card":"평제목"},
                    {"block":"동의문단","card":"consent"}]
            if rng.random()<0.6: blocks.append({"block":"고지표","card":"text_cell"})
            if rng.random()<0.5: blocks.append({"block":"동의문단","card":"consent"})
        # prefill: 요소 토막 10% (5~15 균등)
        pf_rate = 0 if pure_print else rng.uniform(0.6,0.9) if dtype=="작성례" else rng.uniform(0.10,0.25)
        pf=[]; used_pf=set()
        for i,b in enumerate(blocks):
            if rng.random()<pf_rate:
                k=rng.choice([p for p in PF if p not in used_pf] or PF)
                used_pf.add(k); pf.append({"target":i,"kind":k})
        # 밀도 상한: 예상 필드 50 초과면 격자 행 축소 (추정치 — 정확할 필요 없음)
        EST={"인적표":8,"선택군":4,"서술":1,"글머리서술":2,"금액":1,"날짜줄":3,"시각":2,
             "서명줄":2,"수신줄":1,"동의문단":1,"제목":1,"고지표":4,"접수밴드":2,"사진":1}
        est=lambda: sum(min(b.get("rows",5),8)*min(b.get("cols",5),7) if b["block"]=="격자"
                        else EST.get(b["block"],2) for b in blocks)
        grids=[b for b in blocks if b["block"]=="격자"]
        while est()>50 and any(b["rows"]>2 for b in grids):
            max(grids,key=lambda x:x["rows"])["rows"]-=1
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
    ap.add_argument("--out",default="5_dataset/skeletons/smoke"); ap.add_argument("--seed",type=int,default=20260904); a=ap.parse_args()
    s=Sampler(a.n, seed=a.seed); pages=s.run(a.out)
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
