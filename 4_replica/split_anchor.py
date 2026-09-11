"""실서식 앵커를 **서식 단위**로 학습/평가 2:1 분할 → 4_replica/split.json.

왜 서식 단위인가: 같은 서식의 2·3쪽은 머리글·표 골격·어휘를 공유한다. 쪽 단위로 나누면
학습에서 본 템플릿을 평가에서 다시 보게 되어(누수) 실서식 점수가 부풀려진다
(6_research/variation/D 2절, PLAN 10절 P6-1).

전사(4_replica/html)는 진행 중이므로 **파일 존재와 무관하게** 1_corpus/page_manifest.json 전량을
미리 가른다. 전사가 늘어도 분할은 그대로다 — split.json 을 다시 만들지 말 것.

사용: python 4_replica/split_anchor.py            # 쓰기
      python 4_replica/split_anchor.py --check    # 기존 split.json 검증만
"""
import argparse, json, os, random

MANIFEST = "1_corpus/page_manifest.json"
OUT = "4_replica/split.json"


def build(seed, ratio):
    man = json.load(open(MANIFEST, encoding="utf-8"))
    forms = {}
    for e in man:
        key = f"{e['편']}/{e['서식']}"                       # 편이 다르면 다른 서식
        forms.setdefault(key, []).append(os.path.splitext(os.path.basename(e["파일"]))[0])
    keys = sorted(forms)
    random.Random(seed).shuffle(keys)
    target = round(len(man) * ratio)                         # 학습 쪽수 목표
    train, n = [], 0
    for k in keys:                                           # 쪽수 많은 서식이 목표를 넘기지 않게 그리디
        if n < target:
            train.append(k); n += len(forms[k])
    ev = [k for k in keys if k not in set(train)]
    pages = lambda ks: sorted(p for k in ks for p in forms[k])
    return dict(seed=seed, ratio=ratio, manifest=MANIFEST,
                train=dict(forms=sorted(train), pages=pages(train)),
                eval=dict(forms=sorted(ev), pages=pages(ev)))


def check(S):
    ft, fe = set(S["train"]["forms"]), set(S["eval"]["forms"])
    pt, pe = set(S["train"]["pages"]), set(S["eval"]["pages"])
    assert not ft & fe, f"서식 겹침: {ft & fe}"
    assert not pt & pe, f"페이지 겹침: {pt & pe}"
    man = json.load(open(S["manifest"], encoding="utf-8"))
    assert len(pt | pe) == len(man), f"쪽수 불일치 {len(pt | pe)} vs {len(man)}"
    # 페이지 stem 에서 서식을 되짚어도 같은 쪽에 있는지 (stem = 편_서식-쪽)
    by = {}
    for e in man:
        by[os.path.splitext(os.path.basename(e["파일"]))[0]] = f"{e['편']}/{e['서식']}"
    for p in pt: assert by[p] in ft, p
    for p in pe: assert by[p] in fe, p
    return ft, fe, pt, pe


def report(S):
    ft, fe, pt, pe = check(S)
    html = {f[:-5] for f in os.listdir("4_replica/html") if f.endswith(".html")}
    print(f"split.json  seed={S['seed']}  목표비 {S['ratio']:.3f}")
    print(f"  train  서식 {len(ft):3d}  페이지 {len(pt):3d}  (전사됨 {len(pt & html):3d})")
    print(f"  eval   서식 {len(fe):3d}  페이지 {len(pe):3d}  (전사됨 {len(pe & html):3d})")
    print(f"  합계   서식 {len(ft)+len(fe):3d}  페이지 {len(pt)+len(pe):3d}  "
          f"실제비 {len(pt)/(len(pt)+len(pe)):.3f}")
    print(f"  서식 겹침 0 · 페이지 겹침 0 — OK")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=1, help="seed 1 고정: 전체 105/52 이면서 현재 전사된 44장도 29/15 로 갈린다")
    ap.add_argument("--ratio", type=float, default=2 / 3, help="학습 쪽수 비율")
    ap.add_argument("--check", action="store_true", help="기존 split.json 검증만")
    a = ap.parse_args()
    if a.check:
        return report(json.load(open(OUT, encoding="utf-8")))
    S = build(a.seed, a.ratio)
    check(S)
    json.dump(S, open(OUT, "w"), ensure_ascii=False, indent=1)
    report(S)
    print(f"→ {OUT}")


if __name__ == "__main__":
    main()
