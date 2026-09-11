"""확신도 게이지 — 합성/실 분리도(AUROC), 검출 ECE, temperature 1개 보정 후 임계값 재설정.

왜: 4차 e1 에서 저확신(<0.5) 비율이 합성 1.4% vs 실서식 23.9%(17배)였다(DECISIONS 13).
이건 Hendrycks 1610.02136 의 OOD 신호 그대로다 — **conf 분포만으로 합성/실을 가를 수 있으면**
모델이 합성 특유 단서를 외운 것이고, 그 분리도(AUROC)가 에폭마다 오르면 암기가 진행 중이다.
동시에 실서식에서 under-confidence(정확도 > 확신)라면 **임계값 하나로 회수할 recall 이 있다**
(Guo 1706.04599). 비용 0 의 점검이라 학습 전에 먼저 돌린다.

검출 ECE 의 "정답"은 클래스가 아니라 **예측이 GT 와 IoU≥0.5 로 매칭됐는가**(= hit).
temperature 는 p' = σ(logit(p)/T) 의 T 하나만 실서식 덤프에서 맞춘다(파라미터 1개 → 과적합 무시 가능).

입력은 `score.py --dump` 의 miss_dump_*.json.
사용:
  python 8_train/diag_conf.py runs/score/miss_dump_s1v4_real.json --synth runs/score/miss_dump_s1v4_holdout.json
  python 8_train/diag_conf.py --selftest
"""
import argparse, json, os
import numpy as np
from scipy.optimize import minimize_scalar

BINS = [0.0, 0.05, 0.10, 0.25, 0.50, 0.75, 0.90, 1.0]
THRS = [0.05, 0.10, 0.25]
EPS = 1e-6


def preds_from_dump(path):
    """덤프 → (conf[], hit[], n_gt). hit=매칭 IoU≥0.5. 유령과 IoU<0.5 매칭은 hit=0."""
    D = json.load(open(path, encoding="utf-8"))
    conf, hit = [], []
    for g in D["gt"]:
        if g.get("conf") is None:
            continue                      # 아예 예측이 없던 GT — 예측 집합에 없다
        conf.append(g["conf"]); hit.append(1 if g["hit"] else 0)
    for g in D["ghosts"]:
        conf.append(g["conf"]); hit.append(0)
    return np.array(conf, float), np.array(hit, int), len(D["gt"])


def auroc(a, b):
    """두 표본의 분리도 = P(a 무작위 1개 > b 무작위 1개). Mann-Whitney U / (n·m), 동점 0.5."""
    if len(a) == 0 or len(b) == 0:
        return float("nan")
    x = np.concatenate([a, b])
    order = np.argsort(x, kind="mergesort")
    r = np.empty(len(x), float)
    sx = x[order]
    i = 0                                  # 동점 평균 순위
    while i < len(sx):
        j = i
        while j + 1 < len(sx) and sx[j + 1] == sx[i]:
            j += 1
        r[order[i:j + 1]] = (i + j) / 2 + 1
        i = j + 1
    return (r[:len(a)].sum() - len(a) * (len(a) + 1) / 2) / (len(a) * len(b))


def ece(conf, hit, nbin=10):
    """|정확도 − 확신| 표본수 가중 평균 + bin 표."""
    edges = np.linspace(0, 1, nbin + 1)
    b = np.clip(np.digitize(conf, edges[1:-1], right=True), 0, nbin - 1)
    rows, tot = [], 0.0
    for k in range(nbin):
        m = b == k
        if not m.any():
            continue
        c, a = conf[m].mean(), hit[m].mean()
        tot += m.sum() / len(conf) * abs(a - c)
        rows.append((edges[k], edges[k + 1], int(m.sum()), c, a))
    return tot, rows


def fit_T(conf, hit):
    """p' = σ(logit(p)/T). NLL 최소화, T 1개."""
    z = np.log(np.clip(conf, EPS, 1 - EPS) / (1 - np.clip(conf, EPS, 1 - EPS)))
    def nll(logT):
        p = 1 / (1 + np.exp(-z / np.exp(logT)))
        p = np.clip(p, EPS, 1 - EPS)
        return -(hit * np.log(p) + (1 - hit) * np.log(1 - p)).mean()
    r = minimize_scalar(nll, bounds=(np.log(0.05), np.log(20)), method="bounded")
    return float(np.exp(r.x))


def apply_T(conf, T):
    z = np.log(np.clip(conf, EPS, 1 - EPS) / (1 - np.clip(conf, EPS, 1 - EPS)))
    return 1 / (1 + np.exp(-z / T))


def hist(conf, hit, label):
    print(f"\n[{label}] 예측 {len(conf)} · hit {int(hit.sum())} · 유령/오매칭 {int((1-hit).sum())}")
    print(f"  {'구간':>12s} {'hit':>7s} {'유령':>7s} {'hit비율':>8s}")
    for lo, hi in zip(BINS[:-1], BINS[1:]):
        m = (conf >= lo) & (conf < hi if hi < 1.0 else conf <= 1.0)
        if not m.any():
            continue
        h, g = int(hit[m].sum()), int((1 - hit[m]).sum())
        print(f"  [{lo:.2f},{hi:.2f}) {h:7d} {g:7d} {100*h/(h+g):7.1f}%")


def thresholds(conf, hit, n_gt, T, label):
    print(f"\n[{label}] 임계값별 recall / 유령  (T={T:.3f})")
    print(f"  {'thr':>6s} {'recall%':>9s} {'유령':>7s} {'|':>2s} {'보정후 recall%':>15s} {'유령':>7s}")
    cT = apply_T(conf, T)
    for t in THRS:
        m, mT = conf >= t, cT >= t
        print(f"  {t:6.2f} {100*hit[m].sum()/n_gt:9.2f} {int((1-hit[m]).sum()):7d} {'|':>2s} "
              f"{100*hit[mT].sum()/n_gt:15.2f} {int((1-hit[mT]).sum()):7d}")


def report(conf, hit, n_gt, label, synth=None):
    hist(conf, hit, label)
    e, rows = ece(conf, hit)
    T = fit_T(conf, hit)
    eT, _ = ece(apply_T(conf, T), hit)
    print(f"\n[{label}] 검출 ECE {e:.4f} → temperature T={T:.3f} 적용 후 {eT:.4f}"
          f"   ({'과신 (T>1)' if T > 1.05 else '저신 (T<1) — 임계값을 낮추면 회수 가능' if T < 0.95 else '거의 보정됨'})")
    print(f"  {'bin':>12s} {'n':>7s} {'평균conf':>9s} {'실제hit율':>10s} {'차':>7s}")
    for lo, hi, n, c, a in rows:
        print(f"  [{lo:.1f},{hi:.1f}) {n:7d} {c:9.3f} {a:10.3f} {a-c:+7.3f}")
    thresholds(conf, hit, n_gt, T, label)
    if synth is not None:
        sc, sh, _ = synth
        a = auroc(sc, conf)
        print(f"\n[합성 vs 실] conf AUROC {a:.4f}  (0.5=구분 불가, 1.0=합성이 항상 더 확신)")
        print(f"  합성 예측 {len(sc)} 중앙값 {np.median(sc):.3f} · <0.5 비율 {100*(sc<0.5).mean():.1f}%")
        print(f"  실   예측 {len(conf)} 중앙값 {np.median(conf):.3f} · <0.5 비율 {100*(conf<0.5).mean():.1f}%")
        print(f"  합성 ECE {ece(sc, sh)[0]:.4f} · 합성 T {fit_T(sc, sh):.3f}")
    return T


def selftest():
    rng = np.random.default_rng(0)
    # AUROC: 완전 분리 = 1.0, 동일 분포 ≈ 0.5, 뒤집으면 0.0
    assert abs(auroc(np.array([.9, .8, .7]), np.array([.1, .2, .3])) - 1.0) < 1e-9
    assert abs(auroc(np.array([.1, .2, .3]), np.array([.9, .8, .7])) - 0.0) < 1e-9
    assert abs(auroc(np.ones(5), np.ones(5)) - 0.5) < 1e-9          # 전부 동점
    assert abs(auroc(rng.random(4000), rng.random(4000)) - 0.5) < 0.03

    # ECE: 완벽 보정이면 ≈0, 체계적 과신이면 큼
    p = rng.uniform(0.05, 0.95, 40000)
    y = (rng.random(40000) < p).astype(int)
    e0 = ece(p, y)[0]
    assert e0 < 0.02, e0
    e1 = ece(np.clip(p + 0.25, 0, 1), y)[0]
    assert e1 > 0.15, e1

    # temperature: 로짓을 1/T0 배로 부풀린 뒤 되찾는가
    T0 = 2.5
    z = np.log(p / (1 - p))
    pw = 1 / (1 + np.exp(-z * T0))                                   # 과신(로짓 확대) → T ≈ T0 이어야 복원
    T = fit_T(pw, y)
    assert abs(T - T0) / T0 < 0.15, (T, T0)
    assert ece(apply_T(pw, T), y)[0] < e0 + 0.02
    print(f"selftest: ECE 보정 {ece(pw, y)[0]:.4f} → {ece(apply_T(pw, T), y)[0]:.4f} (T={T:.3f}, 참 {T0})")
    print("selftest OK")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dump", nargs="?", help="실서식 miss_dump_*.json")
    ap.add_argument("--synth", help="합성 홀드아웃 miss_dump_*.json (분리도 AUROC 용)")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    assert a.dump, "덤프 경로 필요"
    conf, hit, n_gt = preds_from_dump(a.dump)
    synth = preds_from_dump(a.synth) if a.synth else None
    if synth:
        report(*synth[:2], synth[2], os.path.basename(a.synth))
    report(conf, hit, n_gt, os.path.basename(a.dump), synth)


if __name__ == "__main__":
    main()
