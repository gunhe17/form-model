"""페이지 군집 부트스트랩 CI — 실서식 recall 에 95% 신뢰구간을 붙인다.

왜: 실서식은 44~157쪽뿐이고 한 쪽 안의 박스는 서로 닮았다(군집). 박스를 개체로 재표집하면
분산이 과소추정되므로 **페이지를 복원추출**한다(Field & Welsh 2007). 44쪽·972박스에서
설계효과 2~5 ⇒ 95% CI ±2.7~4.2pt — 즉 "90.4" 는 87~94 어디쯤이고 ±2pt 차이는 판별 불가.
두 모델 비교는 **같은 페이지 표본**으로 A−B 를 계산하는 짝지은 부트스트랩이라야 페이지 난이도
분산이 상쇄된다(6_research/variation/D_measurement_and_mixing.md 4절).

입력은 GT 단위 덤프 `miss_dump_*.json` (`score.py --dump` 산출):
  {"meta":{"names":[...]}, "gt":[{page,i,cls,x,y,w,h,hit,iou,pred_cls,conf}], "ghosts":[...]}

사용:
  python 8_train/diag_ci.py 8_train/runs/score/miss_dump_s1v4_e1.json
  python 8_train/diag_ci.py A.json B.json          # A−B 짝지은 차이의 CI
  python 8_train/diag_ci.py --selftest
"""
import argparse, json, os
import numpy as np


def pages_from_dump(path):
    """miss_dump → {page: (n_gt, n_hit)}. 페이지가 군집 단위."""
    D = json.load(open(path, encoding="utf-8"))
    agg = {}
    for g in D["gt"]:
        n, h = agg.get(g["page"], (0, 0))
        agg[g["page"]] = (n + 1, h + bool(g["hit"]))
    assert agg, f"gt 없음: {path}"
    return agg


def arrays(agg, pages=None):
    pages = pages if pages is not None else sorted(agg)
    gt = np.array([agg[p][0] for p in pages], float)
    hit = np.array([agg[p][1] for p in pages], float)
    return pages, gt, hit


def boot_idx(n, n_boot, rng):
    return rng.integers(0, n, size=(n_boot, n))


def recalls(gt, hit, idx):
    """(박스 가중 recall, 페이지 평균 recall) — 부트스트랩 표본별."""
    G, H = gt[idx].sum(1), hit[idx].sum(1)
    per = hit / np.maximum(gt, 1e-9)
    return 100 * H / np.maximum(G, 1e-9), 100 * per[idx].mean(1)


def ci(v, lo=2.5, hi=97.5):
    return float(np.percentile(v, lo)), float(np.percentile(v, hi))


def one(path, n_boot, rng):
    agg = pages_from_dump(path)
    pages, gt, hit = arrays(agg)
    idx = boot_idx(len(pages), n_boot, rng)
    box, pg = recalls(gt, hit, idx)
    pt = 100 * hit.sum() / gt.sum()
    pt_pg = 100 * (hit / np.maximum(gt, 1e-9)).mean()
    b, p = ci(box), ci(pg)
    print(f"\n=== {os.path.basename(path)} · {len(pages)}쪽 · GT {int(gt.sum())} · hit {int(hit.sum())} ===")
    print(f"recall@IoU0.5 (박스 가중)  {pt:6.2f}  95% CI [{b[0]:.2f}, {b[1]:.2f}]  (±{(b[1]-b[0])/2:.2f}pt)")
    print(f"페이지 평균 recall         {pt_pg:6.2f}  95% CI [{p[0]:.2f}, {p[1]:.2f}]")
    worst = sorted(zip(100 * hit / np.maximum(gt, 1e-9), pages, gt, hit))[:5]
    print("최악 5쪽:")
    for r, pg_, g_, h_ in worst:
        print(f"  {r:6.2f}  {pg_[:44]:44s} gt {int(g_):3d} miss {int(g_-h_):3d}")
    print(f"\n결과표용 → {pt:.2f} [{b[0]:.1f}, {b[1]:.1f}]")
    return agg


def paired(aggA, aggB, n_boot, rng, nameA, nameB):
    common = sorted(set(aggA) & set(aggB))
    assert common, "두 덤프에 공통 페이지가 없다"
    only = (set(aggA) ^ set(aggB))
    _, gA, hA = arrays(aggA, common)
    _, gB, hB = arrays(aggB, common)
    idx = boot_idx(len(common), n_boot, rng)
    bA, pA = recalls(gA, hA, idx)
    bB, pB = recalls(gB, hB, idx)
    d, dp = bA - bB, pA - pB
    ptA, ptB = 100 * hA.sum() / gA.sum(), 100 * hB.sum() / gB.sum()
    c, cp = ci(d), ci(dp)
    print(f"\n=== 짝지은 페이지 부트스트랩 · 공통 {len(common)}쪽" + (f" (한쪽에만 있는 쪽 {len(only)} 제외)" if only else "") + " ===")
    print(f"A {os.path.basename(nameA)}  {ptA:.2f}")
    print(f"B {os.path.basename(nameB)}  {ptB:.2f}")
    print(f"A−B (박스 가중)   {ptA-ptB:+6.2f}  95% CI [{c[0]:+.2f}, {c[1]:+.2f}]  "
          f"{'유의 (0 미포함)' if c[0]*c[1] > 0 else '판별 불가 (0 포함)'}")
    print(f"A−B (페이지 평균) {np.mean(dp):+6.2f}  95% CI [{cp[0]:+.2f}, {cp[1]:+.2f}]")
    print(f"\n결과표용 → {ptA:.2f} vs {ptB:.2f}, Δ{ptA-ptB:+.2f} [{c[0]:+.1f}, {c[1]:+.1f}]")


def selftest():
    """모집단(페이지 300쪽, 참 recall θ)에서 44쪽을 뽑아 CI 를 만들고, θ 를 덮는 비율이 명목 95% 근처인지."""
    rng = np.random.default_rng(0)
    NP, K, TRIALS, NB = 300, 44, 300, 400
    gtP = rng.integers(8, 40, NP).astype(float)                      # 페이지별 GT 수
    rP = np.clip(rng.beta(9, 1, NP), 0, 1)                           # 페이지별 recall (군집 상관의 원천)
    hitP = np.round(gtP * rP)
    theta = 100 * hitP.sum() / gtP.sum()
    cov = 0
    for _ in range(TRIALS):
        s = rng.integers(0, NP, K)
        gt, hit = gtP[s], hitP[s]
        box, _ = recalls(gt, hit, boot_idx(K, NB, rng))
        lo, hi = ci(box)
        cov += lo <= theta <= hi
    c = cov / TRIALS
    print(f"selftest: 참 recall {theta:.2f} · {TRIALS}회 중 CI 포함 {cov} ({100*c:.1f}%, 명목 95%)")
    assert 0.85 <= c <= 1.0, f"군집 부트스트랩 커버리지 이상: {c}"

    # 짝지은 차이: B 를 A 에서 페이지마다 1개씩 더 놓치게 만들면 차이 CI 가 0 을 넘지 않아야 한다
    A = {f"p{i}": (int(gtP[i]), int(hitP[i])) for i in range(K)}
    B = {k: (g, max(0, h - 1)) for k, (g, h) in A.items()}
    _, gA, hA = arrays(A); _, gB, hB = arrays(B)
    idx = boot_idx(K, 2000, np.random.default_rng(1))
    d = recalls(gA, hA, idx)[0] - recalls(gB, hB, idx)[0]
    lo, hi = ci(d)
    assert lo > 0, f"명백한 차이를 못 잡음: [{lo}, {hi}]"
    print(f"selftest: 짝지은 차이 CI [{lo:+.2f}, {hi:+.2f}] — 0 미포함 OK")
    print("selftest OK")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dumps", nargs="*", help="miss_dump_*.json 하나 또는 둘(A B → A−B)")
    ap.add_argument("--boot", type=int, default=10000)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    assert 1 <= len(a.dumps) <= 2, "덤프 1개 또는 2개"
    rng = np.random.default_rng(a.seed)
    aggs = [one(p, a.boot, rng) for p in a.dumps]
    if len(aggs) == 2:
        paired(aggs[0], aggs[1], a.boot, rng, a.dumps[0], a.dumps[1])


if __name__ == "__main__":
    main()
