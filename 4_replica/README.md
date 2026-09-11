# 4 복제 — 실서식 충실 복제 (학습 미포함 평가 앵커)
- `html/` : 원본 판독 → HTML 전사 44쪽(1차). 규약은 `html/CONVENTIONS.md`, 공용 CSS `html/hwp.css`
- `render/` : `render_html.py` 산출 — PNG · `_gt.json` · `_labeled.png`, 대조 갤러리 `index.html`(원본|복제|GT)
- 역할 3가지: 부품·문법 채굴 소스 / 생성물↔실물 대조 기준 / 홀드아웃 평가
- 잔여 105쪽(표준·밀집 28·초밀집 13) 확장 대기
- `split_anchor.py` → `split.json` : **서식 단위** 학습/평가 2:1 분할(105 / 52쪽, 85서식, seed 1 고정). 같은 서식의 2·3쪽은 머리글·표 골격을 공유해 쪽 단위로 나누면 템플릿이 누수된다. 전사 진행과 무관하게 매니페스트 157쪽 전량을 미리 갈라 두었으니 **다시 만들지 말 것**. 검증 `python 4_replica/split_anchor.py --check`
