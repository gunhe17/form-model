# 검토 아티팩트 빌더

| 스크립트 | 만드는 것 | 입력 |
|---|---|---|
| `extract_elements.py <work>` | 학습 표본 70장 + 실서식 44장의 요소·계산 스타일 → `<work>/cls/elements.json` | Playwright |
| `build_cls_review.py <work>` | 1단계 클래스 검토판(기준 K1~K5, 규칙 R1~R15, 예시·혼동 후보) → `<work>/cls-review.html` | elements.json |
| `build_replica_review.py <label> <work>` | 실서식 44장 원본 대 복제 렌더 + 클래스별 정답 박스 → `<work>/replica-review.html` | elements.json |
| `build_dataset_review.py <render_dir> <skeleton_dir> <out.html> [label]` | 재구성 데이터셋 검수(유형별·카드별·클래스별 크롭, 분포·격자) | 렌더 폴더 |

게시는 Claude Code Artifact 로. 검토 이력은 `../DECISIONS.md` 4·5·7절.

## results_3rounds.html

1·2·3차 결과 보고 아티팩트 원본(정적 HTML, 빌더 없음 — 수치는 `docs/PLAN.md` 8절·`README.md` 결과표에서 손으로 옮김). PDF는 `docs/3차_학습_보고.pdf`.

## results_round4.html

4차 결과 정밀 보고 원본(정적 HTML, 실서식 크롭 5장 base64 내장). PDF는 `docs/4차_학습_보고.pdf`.
