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
