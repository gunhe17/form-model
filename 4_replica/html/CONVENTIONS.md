# 실서식 충실 복제 HTML 규약

## 파일
- 출력: 이 디렉토리에 `{페이지ID}.html` (페이지ID = 원본 파일명에서 .png 제거, 예: `1편_서식10호_수료증-1`)
- 문서 선두에 `<link rel="stylesheet" href="hwp.css">` — 본문 폭 1004px(=A4 210mm), 별지 여백 포함. body 태그 안 내용만 작성해도 됨(<meta charset=utf-8> 포함할 것).

## 라벨(GT) 규약 — data-f 속성이 곧 정답 좌표
입력(사람이 채우는) 영역에만 `data-f="{타입}"`: text·number·date·time·phone·email·radio·checkbox·signature·textarea·image
- 표 셀 전체가 입력이면: `<td><span data-f="text" class="cg"></span></td>` (.cg=셀 채움 블록) 또는 td에 직접 X — td 직접 금지, 반드시 내부 span.
- 글줄 속 빈칸: `<span data-f="text" class="gp" style="width:90px"></span>`(투명) / 밑줄形 `class="ul"`
- 마커(□/[ ]): `<span data-f="checkbox" style="display:inline-flex;width:22px;height:22px;align-items:center;justify-content:center;font-size:15px;line-height:22px">□</span>` — 택일이면 data-f="radio". 마커 크기만 라벨.
- 서명: 이름 빈칸=text, "(서명 또는 인)"/"(인)"/직인 문구·박스=signature (문구 전체가 영역).
- 인쇄 텍스트(라벨·안내문·예시문)는 data-f 없음. 단 prefill(인쇄된 값을 덮어쓰는 칸: ○○○, 20__년, 작성례 값)은 인쇄물 포함 전체에 data-f.
- 같은 행 요소는 `<div class="row">`(flex, 세로 가운데) 안에 배치하면 정렬이 보장됨. j=center는 class="row c".

## 디자인 일치 기준
- 표 구조(행·열·병합 rowspan/colspan), 라벨 문구·위치, 음영 유무, 괘선 두께(외곽 굵음 등), 열 폭 비율, 제목 조판(자간·크기), 별지 머리줄/쪽수 표기, 각주·※문구까지 원본과 일치시킬 것.
- 원본에 있는 인쇄 텍스트는 그대로 옮겨 적기(전사). 읽기 불확실한 글자는 유사 표기로.

## 자가 검증(필수)
./venv/bin/python 로 playwright 렌더(뷰포트 1004px) → 스크린샷을 원본 PNG와 나란히 놓고 육안 비교 → 구조 다르면 수정 반복. 예:
```python
import asyncio
from playwright.async_api import async_playwright
async def shot(html, out):
    async with async_playwright() as pw:
        b=await pw.chromium.launch(); pg=await b.new_page(viewport={"width":1004,"height":1400})
        await pg.goto("file://"+html); await pg.wait_for_timeout(300)
        await pg.screenshot(path=out, full_page=True); await b.close()
```
