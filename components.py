# 컴포넌트 레이어 — pool.json 물리_분류.배정의 79키 = 컴포넌트 ID.
# 각 컴포넌트: 정본 HTML 조각(입력 라벨 영역 data-f 포함) + 계열·기제 메타.
# 문서 문법(build_skeleton)은 이 ID만 참조하고, 렌더 정본은 여기서 나온다.
import json, random
from render_skeleton import R

POOL = json.load(open("pattern/pool.json"))
ASSIGN = POOL["물리_분류"]["배정"]            # id -> {계열, 기제}
PREFILL = POOL["직교_변형축"][0]["하위형"]     # prefill 8하위형 (물리 아님·직교 상태)

# 카드가 여러 블록에 속할 때의 대표 블록 (앞선 블록이 우선)
_BLOCK_ORDER = ["인적표","선택군","서술","격자","금액","날짜줄","시각","서명줄",
                "수신줄","동의문단","제목","고지표","접수밴드","글머리서술","사진"]

PF_OVERRIDE = {k:"prefill" for k in
    ["pf_example","pf_sample","pf_filled","pf_mask","pf_note","pf_label","pf_italic","pf_year20"]}

def primary_blocks():
    import build_skeleton as BS
    pri = dict(PF_OVERRIDE)
    for blk in _BLOCK_ORDER:
        for card in BS.CARDS.get(blk, {}):
            pri.setdefault(card, blk)
    return pri

_CTX_DEFAULT = {"n_options": 4, "rows": 3, "cols": 5}

def render_component(cid, block, seed=7, glyph="box", doctype="신청서", **ctx):
    """컴포넌트 1개의 정본 렌더. 반환: (html조각, 대체렌더 여부)"""
    sk = {"id": cid, "type": doctype, "glyph_rule": glyph,
          "blocks": [], "prefill": [], "decoys": [], "seed": seed}
    r = R(sk)
    if block == "prefill":
        return r.pf(cid), False
    b = {"block": block, "card": cid, **_CTX_DEFAULT, **ctx}
    frag = getattr(r, "b_" + block)(b)
    return frag, bool(getattr(r, "missing", None))

def component_map():
    """ID -> {계열, 기제, block, status}. pool 배정 전수 + prefill 별도."""
    pri = primary_blocks()
    out = {}
    for cid, meta in ASSIGN.items():
        out[cid] = {**meta, "block": pri.get(cid),
                    "status": "배선됨" if cid in pri else "미배선"}
    return out

if __name__ == "__main__":
    m = component_map()
    wired = sum(1 for v in m.values() if v["status"] == "배선됨")
    print(f"컴포넌트 {len(m)} | 배선 {wired} | 미배선 {len(m)-wired}")
    for cid, v in m.items():
        if v["status"] == "미배선": print("  미배선:", cid, v["계열"], v["기제"])
