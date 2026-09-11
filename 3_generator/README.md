# 3 생성기 — 사양 → 골격 → 렌더+GT
```
2_spec/pool.json + doc_grammar.json
  → build_skeleton.py   유형 쿼터·블록 문법·카드 배정 → 골격 JSON (렌더 전, 증강에서 재사용)
  → render_skeleton.py  골격 → HTML → playwright → PNG + GT(data-f 좌표)
```
| 파일 | 역할 |
|---|---|
| `build_skeleton.py` | QUOTA v2.1, 블록 문법, 카드 호환표, 글리프 규약, prefill·데코이 |
| `render_skeleton.py` | 컴포넌트 정본 HTML(클래스 R), ROW 정렬, 문서 테마 샘플, 수직 리듬 |
| `components.py` | pool 79키 ↔ 정본 렌더 매핑 |
| `hwp_theme.py` | HWP 질감 CSS(서체 `../fonts/`, 줄간격, 음영, 별지 여백) |
| `build_component_map.py` | → `catalog/index.html` 전수 카탈로그(정렬 검증 토글 포함) |
| `build_lexicon.py` | 1_corpus OCR 캐시 → `2_spec/lexicon_real.json`(실서식 어휘) |

라벨 규약 v1.8: checkbox/radio = 마커 크기만, 서명줄 = 이름(text)+문구(signature) 분리, 라벨 1 : 입력(군) 1.

## v3 (2026-09-10, 4차 학습용 — PLAN 9.4 보강 6항목)

3차 GT 단위 귀속(PLAN 9절)에서 드러난 "학습에 없거나 규약이 다른" 형태를 채운다.

| # | 변경 | 카드·원자 |
|---|---|---|
| 1 | 표 안 선택칸의 보이지 않는 22px 표식(MKC) **삭제** → 셀 전체 `CGF` 박스. 척도표는 td 인쇄글자 + cgf(실서식 17호 규약) | radio_likert · cb_matrix · scale_words |
| 2 | 한 셀에 라벨·빈칸 쌍 2~4개 나란히 / 라벨 + 잔여 전폭 cg (가로 inset) | 신규 `inline_pairs` |
| 3 | 선택지 뒤 괄호 빈칸 `( __ )`·`약 __ m` (45% 그룹 × 30% 항목) · 문장 글꼴 축 14~17px | cb_row·cb_grid·cb_bracket·cb_wrap · text_colon·text_prose |
| 4 | 밀착 슬롯 `GPT`(폭 10~20, 여백 0): 날짜줄 `date_tight`, 인적표 date_split 35%, 시각 50% | 신규 원자 `GPT` |
| 5 | 인쇄 자리표 `PH`: 박스 = 글자(○·○○·○○○), 낱글자 ○ 고정폭 22~31 · 테마 축 `ph_fs` 12~15 | pf_sample·pf_mask 교체, 신규 prefill `pf_circle` |
| 6 | 셀 안 빈 공간 뒤 소형 (인)/(서명) + `날짜 : __.__.` (sig_cell 50%) · 서명줄 소형 문구 글꼴 12~14 | sig_cell · SIG |

검사: `label_stage1.py --coverage` 가 "보이지 않는 표 안 선택 박스" 수를 출력한다(학습 0 이어야 함).

재생성:
```
python 3_generator/build_skeleton.py --n 20000 --out 5_dataset/skeletons_v3/train   --seed 20260904
python 3_generator/build_skeleton.py --n 1000  --out 5_dataset/skeletons_v3/holdout --seed 20260905   # 999장
# 렌더 (6 프로세스, ls 글롭은 2만 파일에서 인자 한계 → find 사용): 골격 목록을 나눠 render_skeleton.py 에 --out 5_dataset/train_v3 / holdout_v3
find 5_dataset/skeletons_v3/train -name '*.json' | xargs -P 6 -n 800 sh -c 'python 3_generator/render_skeleton.py "$@" --out 5_dataset/train_v3 > /dev/null' _
find 5_dataset/skeletons_v3/holdout -name '*.json' | xargs -P 6 -n 400 sh -c 'python 3_generator/render_skeleton.py "$@" --out 5_dataset/holdout_v3 > /dev/null' _
```

## v4 (2026-09-11, 5차 학습용 — PLAN 10절 P6-2 "변동 폭")

진단: 합성 홀드아웃 99.9 / 실서식 90.4 는 "좁은 합성 분포를 외운" 상태(DECISIONS 13).
문헌 조사(`6_research/variation`)의 처방 — **폭 > 사실성 > 수량**, 이산 3~6값 축은 "풀 크기 3~6"이라
가장 취약 — 을 그대로 구현한다. **라벨 규칙(`8_train/label_stage1.py` R1~R15)과 카드 의미는 불변, 폭만 넓힌다.**

| # | 축 | v3 (이산) | v4 (연속) |
|---|---|---|---|
| 1 | mk(마커) | 18/20/22/24/26 | 16~30 |
| 1 | slot_w · slot_h | 26~46 5값 · 20~28 5값 | 24~56 · 18~30 |
| 1 | cell_h · row_h | 30~44 5값 · 34~72 5값 | 26~48 · 30~74 |
| 1 | lbw(라벨 열 폭) | 92~150 5값 | 84~158 |
| 1 | ul_w · ul_th | 60~160 4값 · 1.0~1.8 4값 | 52~175 · 0.8~2.0 |
| 1 | cg_h · inset | 22/26/30 · 2/3/4/6 | 20~32 · 1.5~6.5 |
| 1 | comb 치수·선굵기 | (w,h) 5쌍 · 1px 고정 | 14~29 × 16~30(장치 픽셀) · 0.8~1.8px |
| 1 | mk_bw · sig_off · ph_fs | 10~14 · 12/24/40 · 12~15 | 8~16 · 6~48 · 11~16 |
| 1 | shade(음영) | 6값 | #d2d2d2~#ffffff 연속 |
| 1 | outer · title_fs · title_ls | 1/1.6/2.2 · 30/32/34 · 4값 | 0.8~2.6 · 26~40 · 0.04~0.45em |
| 1 | cell_pad · col_contrast | 3값 · 0/0.6/1.0 | 상하 1~5 / 좌우 3~10px · 0(30%) 또는 0.2~1.2 |
| 1 | **신규** | — | 본문 글꼴 15~18px · 표 13~16px · 소자 = 표−0.5~2 |
| 1 | **신규** | — | 자간 −0.05~0.10em · 행간 1.3~1.8(표 1.2~1.6) |
| 1 | **신규** | — | 괘선 굵기 0.6~2.0px · 괘선/글자 농도 #000~#666 · 배경 #f2f2f2~#fff |
| 1 | **신규** | — | 페이지 여백 상 40~120 / 좌우 40~120 / 하 30~100px |
| 2 | 글꼴 | 3종(Hahmlet·NanumMyeongjo·NanumGothic) | **50종**(고딕 18·명조 11·손글씨 13·장식 8). 문서마다 본문·표·제목을 계열별 확률로 독립 추출 |
| 3 | 어휘 | th 라벨 90종·선택지 36종(고정 LEX) | `2_spec/lexicon_real.json`(실 OCR 라벨 2,005·문장조각 220)과 혼합, 길이 맞춰 치환. 400장에서 고유 th 라벨 765종 |
| 4 | 비대상 방해물 | 없음 | 도장·로고·워터마크·안내문·페이지번호·접수인란 **0~6개/페이지**. `data-f` 없음 = GT 밖, 필드와 부분 겹침 허용 |
| 5 | 배율·뷰포트 | 1004px · DPR 1 고정 | `device_scale_factor` 0.8~1.3(0.05 단위) · 뷰포트 854~1154px. GT 는 장치 픽셀로 환산(=PNG 픽셀) |
| 6 | 배치 지터 | 카드 간격 8/20/26 × dens 4값 · 폭 상수 | 간격 3~16 / 14~32 × dens 0.55~1.7 · 필드 폭 계수 wjit 0.75~1.35 |
| 7 | 음성·희소 | 입력 0 페이지 약 6% | 그대로 + **희소 유형 2%**(입력 1~3개) |

배율 주의: 낱칸(comb) 치수와 무클래스 빈 슬롯 폭은 **장치 픽셀 기준으로 뽑아 배율로 나눈다**.
그러지 않으면 확대 시 comb(≤30px)·gap(≤60px) 임계를 넘어 클래스가 바뀐다.
방해물은 `position:absolute` 로 흐름에 영향을 주지 않으며 **입력 span 안에는 절대 넣지 않는다**.

렌더는 `{id}_theme.json` 도 함께 저장한다(축별 사후 분석용).

스모크 400장(seed 7) 검증: 대체 렌더 0 · 보이지 않는 표 안 선택 박스 0 · 페이지당 중앙값 29 ·
cell 36.2 / gap 21.4 / marker 13.3 / comb 6.7 / placeholder 7.0 / underline 5.2 / signature 4.3 / photo 1.9%.
커버리지 격자에서 실서식에 있는데 학습에 없는 칸은 4개(각 실서식 1~2개)뿐.

재생성:
```
sh fonts/get_fonts.sh                                   # 글꼴 50종 (약 180MB, 커밋 안 함)
python3 3_generator/build_lexicon.py                    # 2_spec/lexicon_real.json
python3 3_generator/build_skeleton.py --n 20000 --out 5_dataset/skeletons_v4/train   --seed 20260904
python3 3_generator/build_skeleton.py --n 1000  --out 5_dataset/skeletons_v4/holdout --seed 20260905   # 999장
find 5_dataset/skeletons_v4/train   -name '*.json' | xargs -P 6 -n 800 sh -c 'python3 3_generator/render_skeleton.py "$@" --out 5_dataset/train_v4 > /dev/null' _
find 5_dataset/skeletons_v4/holdout -name '*.json' | xargs -P 6 -n 400 sh -c 'python3 3_generator/render_skeleton.py "$@" --out 5_dataset/holdout_v4 > /dev/null' _
python3 8_train/label_stage1.py --train 5_dataset/train_v4 --replica 4_replica --coverage
```
