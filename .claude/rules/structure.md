# 저장소 구조와 기록 규칙

구조 = 절차. 폴더 번호가 단계이고, 각 단계는 앞 단계의 산출만 입력으로 받는다. 새 파일은 아래 자리에만 둔다.

## 단계 폴더

| 단계 | 폴더 | 안에 두는 것 | 추적 |
|---|---|---|---|
| 0 원천 | `0_source/` | 사업안내 PDF | O |
| 1 코퍼스 | `1_corpus/` | 실서식 페이지 PNG, OCR 캐시, 서지 | O |
| 2 사양 | `2_spec/` | pool.json(부품 79종·물리 분류), doc_grammar.json, variation.json 등 | O |
| 3 생성기 | `3_generator/` | build_skeleton.py(골격 샘플러), render_skeleton.py(부품 함수·카드 렌더), hwp_theme.py(CSS), components.py, catalog/ | O |
| 4 복제 | `4_replica/` | `html/`(손 전사), `render/`(PNG·GT), render_html.py, **lint.py**(규약 검사), CONVENTIONS.md | O |
| 5 데이터셋 | `5_dataset/` | `skeletons*/`(골격 JSON, 추적), `train*/`·`holdout*/`(렌더, v1만 추적·v2 이후 gitignore) | 골격 O / 렌더 X |
| 6 조사 | `6_research/` | 문헌 보고서 원문 + 교차 검증 README | O |
| 7 증강 | `7_augment/` | augment.py, render_swap.py, build_pool.sh, README(축·구분 정의). 산출 `pool/`·`render_swap/` 은 gitignore | 스크립트 O |
| 8 학습 | `8_train/` | 아래 참조 | 스크립트·문서 O |
| 인프라 | `docker/` | 격리 학습 컨테이너(compose, Dockerfile, .env.example) | O |

## 8_train 내부

| 위치 | 내용 |
|---|---|
| `README.md` | 폴더 지도 + 학습 실행 명령 + 결과표(런별 한 줄) |
| `docs/PLAN.md` | 현재 계획: 결정과 근거, 클래스 정의, 목표 분포, 단계·합격 기준, 단계별 결과 절(P0, P1, v2.x …) |
| `docs/DECISIONS.md` | **시간순 의사결정·시행착오 로그.** 결정마다 "무엇을·왜·무엇이 틀렸었나" |
| `docs/*.pdf` | 보고서(학습 감사·결과 보고) |
| `to_yolo.py`, `label_stage1.py`, `score.py`, `diag_*.py`, `forms*.yaml` | 실행 스크립트·데이터 정의. **경로를 옮기지 말 것**(컨테이너·문서가 참조) |
| `review/` | 검토 아티팩트 빌더(클래스 검토판·실서식 검수·데이터셋 검수) + README |
| `runs/`, `yolo*/`, `weights/` | 산출물, gitignore. 서버(컨테이너)에서 생성 |

## 기록 규칙

1. **결정이 생기면 `8_train/docs/DECISIONS.md`에 한 항목** — 날짜, 결정, 근거(수치·논문·검수 지적), 틀렸던 판단이 있으면 그것도. 커밋 메시지만으로 끝내지 않는다.
2. **수치 결과는 `docs/PLAN.md`의 해당 단계 결과 절에 표로.** 학습 런은 `8_train/README.md` 결과표에 한 줄 추가(가중치 경로, 홀드아웃·실서식·stress recall, 보고서).
3. **각 단계 README는 그 단계의 "무엇을·왜"만.** 변경이 그 단계의 동작을 바꾸면(새 카드, 새 검사, 규약 변경) 그 README에 한 절 추가.
4. **데이터 정정은 원인과 처리를 남긴다** (`4_replica/README.md` 정정 이력 + DECISIONS). 손 전사 데이터는 `4_replica/lint.py` 통과가 커밋 조건.
5. **검토 아티팩트는 빌더를 `8_train/review/`에 둔다.** 게시 URL은 대화에만 남으므로 재현은 빌더로.
6. **보고서**는 HTML 아티팩트 + PDF(`docs/`)로 두 벌. PDF는 저장소에 커밋.
7. 큰 산출물(렌더 PNG, 풀, 가중치, runs)은 커밋하지 않고 **골격·스크립트·시드로 재생성**한다. 재생성 명령은 해당 README에 있어야 한다.
8. 스크래치는 세션 scratchpad에만. 저장소에 임시 파일을 만들지 않는다. `.claude/worktrees/`, `.DS_Store`, `*.log`는 gitignore.

## 라벨·클래스 규약 (요약, 정본은 docs/PLAN.md 1절)

- 의미 타입 11종(`data-f`)은 GT에 그대로. 1단계 검출기용 생김새 8종(marker·comb·cell·gap·underline·placeholder·signature·photo)은 `8_train/label_stage1.py` 규칙 R1~R15로 마크업에서 유도. word·area는 1단계 제외.
- 생성기 부품 함수가 마크업 규약을 강제한다. 복제본(손 전사)은 같은 규약을 lint로 검사한다.
