"""HWP 질감 테마 — 생성기 렌더 공용.
130dpi 캘리브레이션(1004px=210mm, 4.78px/mm) 기준 환산:
  본문 10pt=3.53mm=17px · 표 9pt=15px · 소자 8pt=13.5px · 제목 16pt=27px · 대제 20pt=34px
HWP 관용: 줄간격 160% · 셀여백 상하1.3px 좌우6px(0.5~1.4mm) · 헤더 회색15%(#E2E2E2) · 괘선 hairline
"""
import os
HERE = os.path.dirname(os.path.abspath(__file__))
F = os.path.join(HERE, "fonts")

DEFAULT_THEME = {"cell_h":34,"shade":"#E2E2E2","shade2":"#EFEFEF","title_ls":0.28,"title_fs":34,"outer":1,
    "ul_th":1.2,"cg_h":26,"inset":3,"sig_off":24,"cell_pad":"3px 7px"}

def css(theme=None):
    T={**DEFAULT_THEME, **(theme or {})}
    return f"""
@font-face{{font-family:'Hahmlet';src:url('file://{F}/Hahmlet.ttf');font-weight:100 900}}
@font-face{{font-family:'NanumMyeongjo';src:url('file://{F}/NanumMyeongjo.ttf');font-weight:400}}
@font-face{{font-family:'NanumMyeongjo';src:url('file://{F}/NanumMyeongjo-Bold.ttf');font-weight:700}}
@font-face{{font-family:'NanumDotum';src:url('file://{F}/NanumGothic.ttf');font-weight:400}}
@font-face{{font-family:'NanumDotum';src:url('file://{F}/NanumGothic-Bold.ttf');font-weight:700}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{width:1004px;background:#fff;color:#000;
 font-family:'Hahmlet','NanumMyeongjo',serif;font-size:17px;line-height:1.6;
 letter-spacing:-0.01em;word-break:keep-all;
 padding:{int(20*4.78)}px {int(20*4.78)}px {int(15*4.78)}px}}  /* HWP 별지 여백 상20 좌우20 하15mm */
.byulji{{font-family:'NanumDotum';font-size:14px;margin-bottom:6px}}          /* [별지 제n호서식] */
.pageside{{float:right;font-family:'NanumDotum';font-size:13px;color:#000}}   /* (앞쪽)·(n쪽 중 n쪽) */
h1.doctitle{{font-family:'NanumMyeongjo';font-weight:700;font-size:{T["title_fs"]}px;text-align:center;
 letter-spacing:{T["title_ls"]}em;margin:26px 0 22px}}
h1.doctitle .tight{{letter-spacing:0}}
table{{border-collapse:collapse;width:100%;table-layout:fixed;margin:0;border:{T["outer"]}px solid #000;
 font-family:'NanumDotum';font-size:15px;line-height:1.45}}
td,th{{border:1px solid #000;padding:{T["cell_pad"]};vertical-align:middle;font-weight:400;height:{T["cell_h"]}px}}
{("td:first-child,th:first-child{{border-left:none}}td:last-child,th:last-child{{border-right:none}}table{{border-left:none!important;border-right:none!important;border-top:2px solid #000;border-bottom:2px solid #000}}" if T.get("open") else "")}
th,.lb{{background:{T["shade"]};text-align:center;font-family:'NanumDotum'}}       /* 회색 15% */
.lb2{{background:{T["shade2"]}}}                                                     /* 회색 8% 보조 */
.vl{{text-align:center}}
.tl{{text-align:left}}
.thick{{border:2.2px solid #000}}
.dashed{{border-style:dashed}}
.ln{{padding:3px 0}}
.indent1{{padding-left:14px}}.indent2{{padding-left:30px}}                    /* 개조식 □→○→- */
.cbx{{display:inline-block;width:14px;height:14px;border:1.6px solid #000;vertical-align:-2px;margin-right:2px}}
.gp{{display:inline-block;width:64px;height:1.15em;vertical-align:middle;position:relative;top:-2px;margin:0 2px}}
.cg{{display:block;height:{T["cg_h"]}px;margin:1px -4px}}
.mkc{{display:inline-block;width:22px;height:22px;vertical-align:middle}}
.row{{display:flex;align-items:center;gap:4px}}
.row.c{{justify-content:center}}
.row.r{{justify-content:flex-end}}
.row [data-f],.row .gp,.row .ul,.sigline [data-f],.sigline .gp,.sigline .ul{{position:static!important;top:auto!important}}
td.fillc{{position:relative}}
.cgf{{position:absolute;top:{T["inset"]}px;bottom:{T["inset"]}px;left:{T["inset"]}px;right:{T["inset"]}px}}
.ul{{display:inline-block;border-bottom:{T["ul_th"]}px solid #000;width:90px;height:1em;margin:0 2px;vertical-align:middle;position:relative;top:-3.3px}}
.sup{{font-size:11px;vertical-align:super}}
.note{{font-family:'NanumDotum';font-size:13.5px}}                            /* ※·각주 */
.sigline{{text-align:right;margin:6px {T["sig_off"]}px 0 0;display:flex;justify-content:flex-end;align-items:center;gap:4px}}
.center{{text-align:center}}
.paper{{font-family:'NanumDotum';font-size:12.5px;text-align:right;margin-top:18px}}
.spread{{letter-spacing:.9em}}                                                /* 자간 벌린 라벨 성    명 */
"""

if __name__ == "__main__":
    print(css()[:400])
