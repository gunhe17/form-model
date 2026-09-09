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
