"""HWP 질감 테마 — 생성기 렌더 공용.
130dpi 캘리브레이션(1004px=210mm, 4.78px/mm) 기준 환산:
  본문 10pt=3.53mm=17px · 표 9pt=15px · 소자 8pt=13.5px · 제목 16pt=27px · 대제 20pt=34px
HWP 관용: 줄간격 160% · 셀여백 상하1.3px 좌우6px(0.5~1.4mm) · 헤더 회색15%(#E2E2E2) · 괘선 hairline

v4: 모든 축이 연속 구간(R.__init__ 가 샘플). 여기 DEFAULT_THEME 은 카탈로그·단독 호출용 기준값.
"""
import os
HERE = os.path.dirname(os.path.abspath(__file__))
F = os.path.join(HERE, "..", "fonts")

DEFAULT_THEME = {"cell_h":34,"shade":"#E2E2E2","shade2":"#EFEFEF","title_ls":0.28,"title_fs":34,"outer":1,
    "ul_th":1.2,"cg_h":26,"inset":3,"sig_off":24,"cell_pad":"3px 7px",
    # v4 연속 축
    "page_w":1004,"pad_t":95,"pad_x":95,"pad_b":71,
    "body_fs":17,"table_fs":15,"note_fs":13.5,"ls":-0.01,"lh":1.6,"tlh":1.45,
    "rule_th":1,"ink":"#000000","rule":"#000000","bg":"#ffffff",
    "font_body":"Hahmlet","font_table":"NanumDotum","font_title":"NanumMyeongjo",
    "faces":[("Hahmlet","Hahmlet.ttf","100 900"),("NanumMyeongjo","NanumMyeongjo.ttf","400"),
             ("NanumMyeongjo","NanumMyeongjo-Bold.ttf","700"),("NanumDotum","NanumGothic.ttf","400"),
             ("NanumDotum","NanumGothic-Bold.ttf","700")]}

def css(theme=None):
    T={**DEFAULT_THEME, **(theme or {})}
    faces="".join("@font-face{font-family:'%s';src:url('file://%s/%s');font-weight:%s}" % (n, F, fn, w)
                  for n, fn, w in T["faces"])
    fb="'"+T["font_body"]+"',serif"; ft="'"+T["font_table"]+"',sans-serif"; ftl="'"+T["font_title"]+"',serif"
    return faces+f"""
*{{box-sizing:border-box;margin:0;padding:0}}
body{{width:{T["page_w"]}px;background:{T["bg"]};color:{T["ink"]};
 font-family:{fb};font-size:{T["body_fs"]}px;line-height:{T["lh"]};
 letter-spacing:{T["ls"]}em;word-break:keep-all;
 padding:{T["pad_t"]}px {T["pad_x"]}px {T["pad_b"]}px}}  /* HWP 별지 여백 */
.byulji{{font-family:{ft};font-size:{T["note_fs"]+0.5}px;margin-bottom:6px}}        /* [별지 제n호서식] */
.pageside{{float:right;font-family:{ft};font-size:{T["note_fs"]}px}}                 /* (앞쪽)·(n쪽 중 n쪽) */
h1.doctitle{{font-family:{ftl};font-weight:700;font-size:{T["title_fs"]}px;text-align:center;
 letter-spacing:{T["title_ls"]}em;margin:26px 0 22px}}
h1.doctitle .tight{{letter-spacing:0}}
table{{border-collapse:collapse;width:100%;table-layout:fixed;margin:0;border:{T["outer"]}px solid {T["rule"]};
 font-family:{ft};font-size:{T["table_fs"]}px;line-height:{T["tlh"]}}}
td,th{{border:{T["rule_th"]}px solid {T["rule"]};padding:{T["cell_pad"]};vertical-align:middle;font-weight:400;height:{T["cell_h"]}px}}
{("td:first-child,th:first-child{border-left:none}td:last-child,th:last-child{border-right:none}table{border-left:none!important;border-right:none!important;border-top:%spx solid %s;border-bottom:%spx solid %s}" % (round(T["outer"]*1.8,2), T["rule"], round(T["outer"]*1.8,2), T["rule"]) if T.get("open") else "")}
th,.lb{{background:{T["shade"]};text-align:center;font-family:{ft}}}               /* 회색 15% */
.lb2{{background:{T["shade2"]}}}                                                     /* 회색 8% 보조 */
.vl{{text-align:center}}
.tl{{text-align:left}}
.thick{{border:{round(T["rule_th"]*2,2)}px solid {T["rule"]}}}
tr.hdsep th{{border-bottom:{round(T["rule_th"]*1.9,2)}px solid {T["rule"]}}}   /* 무외곽 표 헤더 아래 굵은 구분선 */
.dashed{{border-style:dashed}}
.ln{{padding:3px 0}}
.indent1{{padding-left:14px}}.indent2{{padding-left:30px}}                    /* 개조식 □→○→- */
.cbx{{display:inline-block;width:14px;height:14px;border:{max(1,round(T["rule_th"]*1.6,2))}px solid {T["rule"]};vertical-align:-2px;margin-right:2px}}
.gp{{display:inline-block;width:64px;height:1.15em;vertical-align:middle;position:relative;top:-2px;margin:0 2px}}
.cg{{display:block;height:{T["cg_h"]}px;margin:1px -4px}}
.mkc{{display:inline-block;width:22px;height:22px;vertical-align:middle}}
.row{{display:flex;align-items:center;gap:4px}}
.row.c{{justify-content:center}}
.row.r{{justify-content:flex-end}}
.row [data-f],.row .gp,.row .ul,.sigline [data-f],.sigline .gp,.sigline .ul{{position:static!important;top:auto!important}}
td.fillc{{position:relative}}
.cgf{{position:absolute;top:{T["inset"]}px;bottom:{T["inset"]}px;left:{T["inset"]}px;right:{T["inset"]}px}}
.ul{{display:inline-block;border-bottom:{T["ul_th"]}px solid {T["rule"]};width:90px;height:1em;margin:0 2px;vertical-align:middle;position:relative;top:-3.3px}}
.sup{{font-size:11px;vertical-align:super}}
.note{{font-family:{ft};font-size:{T["note_fs"]}px}}                          /* ※·각주 */
.sigline{{text-align:right;margin:6px {T["sig_off"]}px 0 0;display:flex;justify-content:flex-end;align-items:center;gap:4px}}
.center{{text-align:center}}
.paper{{font-family:{ft};font-size:{T["note_fs"]-1}px;text-align:right;margin-top:18px}}
.spread{{letter-spacing:.9em}}                                                /* 자간 벌린 라벨 성    명 */
.dist{{position:absolute;pointer-events:none}}                                /* v4 비대상 방해물(data-f 없음) */
"""

if __name__ == "__main__":
    print(css()[:400])
