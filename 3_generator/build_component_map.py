# pool 79키 전수 컴포넌트 맵 카탈로그 — 계열별 그룹, 정본 렌더 + 라벨 영역 오버레이(CSS)
import json
from components import component_map, render_component, PREFILL
from hwp_theme import css as hwp_css

COL = {"text":"#1565C0","date":"#2E7D32","number":"#6A1B9A","radio":"#E65100","checkbox":"#C62828",
       "signature":"#AD1457","textarea":"#00838F","phone":"#4527A0","email":"#00695C",
       "time":"#F9A825","image":"#FF4081"}
SERIES_ORDER = ["표-셀","글줄-인라인","격자-반복","자유-영역"]

PROC = """
<div class="proc"><b>절차(재수립)</b>
<ol>
<li><b>필드 pool</b> (2_spec/pool.json 배정 79키) — 물리 계열×기제로 정규화된 변형 전수.</li>
<li><b>컴포넌트 정의</b> (components.py) — 키마다 정본 HTML 구현 + 라벨 영역(data-f)을 컴포넌트로 고정. 이 카탈로그가 그 정본의 시각 계약서.</li>
<li><b>문서 문법 조립</b> (doc_grammar 20유형 × build_skeleton) — 블록이 아니라 <b>컴포넌트 ID를 직접 참조</b>해 논리 흐름(5막)에 배치.</li>
<li><b>렌더+GT</b> (render_skeleton) — 컴포넌트에 내장된 data-f 영역에서 좌표 자동 추출.</li>
<li><b>증강</b> — 선·테두리·폰트·dpi. 컴포넌트 정본은 불변, 파라미터만 변주.</li>
</ol></div>
"""

def build():
    m = component_map()
    lbl_css = "".join(f'[data-f="{t}"]{{outline:2px solid {c};outline-offset:-1px}}' for t,c in COL.items())
    leg = "".join(f'<span class="lg"><i style="background:{c}"></i>{t}</span>' for t,c in COL.items())
    parts = [f"<style>{hwp_css()}"
             "body{width:auto;max-width:1100px;padding:20px 30px}"
             ".proc{border:1.5px solid #333;padding:10px 16px;font-size:14px;margin-bottom:18px}"
             ".comp{border:1px solid #ccc;margin:14px 0;padding:10px 14px}"
             ".comp .hd{font-family:sans-serif;font-size:13px;margin-bottom:8px}"
             ".comp .hd b{font-size:15px}"
             ".bdg{display:inline-block;font-size:11px;border:1px solid #888;padding:1px 6px;margin-left:6px;border-radius:3px}"
             ".miss{background:#FDECEA;border-color:#C62828}"
             ".lg{font-family:sans-serif;font-size:12px;margin-right:10px}.lg i{display:inline-block;width:10px;height:10px;margin-right:3px}"
             "#vtab{float:right;font-family:sans-serif;font-size:13px;padding:3px 14px;border:1.5px solid #333;border-radius:4px;cursor:pointer;background:#fff}"
             "body.verify #vtab{background:#C62828;color:#fff;border-color:#C62828}"
             "body.verify .row,body.verify .sigline,body.verify td.vl,body.verify h1.doctitle,body.verify p.ln{position:relative}"
             "body.verify .row::after,body.verify .sigline::after,body.verify td.vl::after,body.verify h1.doctitle::after,body.verify p.ln::after"
             "{content:'';position:absolute;left:0;right:0;top:50%;height:1px;background:rgba(230,0,0,.8);pointer-events:none;z-index:99}"
             "body.verify td.vl:has(.row)::after,body.verify td.vl:has(br)::after{display:none}"
             f"{lbl_css}</style>"
             f'<h1 class="doctitle" style="font-size:26px">필드 Pool 컴포넌트 맵 ({len(m)})</h1>'
             f'<div style="position:sticky;top:0;background:#fff;padding:6px 0;border-bottom:1px solid #ddd;z-index:9">{leg}<button id="vtab" onclick="document.body.classList.toggle(&quot;verify&quot;)">정렬 검증</button></div>'
             + PROC]
    stats = {"ok":0,"fallback":0,"miss":0}
    import build_skeleton as BS
    SECOND={}   # 다중 블록 카드: 두 번째 블록도 정본 노출
    order=["인적표","선택군","서술","격자","금액","날짜줄","시각","서명줄","수신줄","동의문단","제목","고지표","접수밴드","글머리서술","사진"]
    for blk in order:
        for card in BS.CARDS.get(blk,{}):
            if card in m and m[card]["block"]!=blk and card not in SECOND: SECOND[card]=blk
    for s in SERIES_ORDER:
        items = sorted((cid,v) for cid,v in m.items() if v["계열"]==s and not cid.startswith("pf_"))
        parts.append(f'<h2 style="font-family:sans-serif;border-bottom:2px solid #333">{s} — {len(items)}종</h2>')
        for cid, v in items:
            head = (f'<div class="hd"><b>{cid}</b>'
                    f'<span class="bdg">{v["기제"]}</span>'
                    f'<span class="bdg">블록: {v["block"] or "-"}</span>')
            if v["status"]=="미배선":
                stats["miss"]+=1
                parts.append(f'<div class="comp miss">{head}<span class="bdg miss">미구현 — 정본 필요</span></div></div>')
                continue
            dt = "증서" if cid in ("sig_stamp","sig_stamp_paren") else "신청서"
            frag, fallback = render_component(cid, v["block"], doctype=dt)
            if fallback: stats["fallback"]+=1; head += '<span class="bdg miss">대체 렌더</span>'
            else: stats["ok"]+=1
            extra=""
            if cid in SECOND:
                f2,_ = render_component(cid, SECOND[cid], doctype=dt)
                extra=f'<div class="hd" style="margin-top:10px"><span class="bdg">블록: {SECOND[cid]} (2차 정본)</span></div>{f2}'
            parts.append(f'<div class="comp">{head}</div>{frag}{extra}</div>')
    # prefill: 직교 상태 섹션 (물리 아님)
    parts.append('<h2 style="font-family:sans-serif;border-bottom:2px solid #333">직교-상태 prefill — 8하위형 (컴포넌트에 겹치는 상태)</h2>')
    from components import render_component as RC
    PFID=["pf_year20","pf_example","pf_sample","pf_filled","pf_mask","pf_note","pf_label","pf_italic"]
    for pf, pid in zip(PREFILL, PFID):
        frag,_ = RC(pid, "prefill")
        parts.append(f'<div class="comp"><div class="hd"><b>{pid}</b><span class="bdg">{pf["이름"]}</span>'
                     f'<span class="bdg">{pf["근거"][:60]}</span></div>{frag}</div>')
    import os; out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "catalog", "index.html")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    open(out,"w").write(f'<!doctype html><meta charset=utf8><title>컴포넌트 맵</title>{"".join(parts)}')
    print(f"정본 {stats['ok']} | 대체 렌더 {stats['fallback']} | 미구현 {stats['miss']} → {out}")

if __name__ == "__main__":
    build()
