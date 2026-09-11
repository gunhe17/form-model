"""실/합성 혼합 이미지 목록(.txt) 생성 — Ultralytics 는 data yaml 의 train 에 .txt 목록을 받고
같은 경로가 여러 줄이면 그만큼 반복 등록한다(ultralytics/data/base.py get_img_files).

왜 목록이 필요한가: 실서식은 29~105장, 합성은 62,000장이다. 그냥 합치면 실 비율이 0.2% 라
에폭당 한 번도 안 보일 수 있다. 문헌 처방은 **실 5~20% 오버샘플**(Burdorf 2202.00632,
Dwibedi 1708.01642)이고 미세조정 쪽은 **합성 리플레이 20~30%**(Nowruzi 1907.07061) — 둘 다
"목록에 몇 번 적을까"로 환원된다.

사용:
  # (B) 혼합 학습: 실 10% 가 되도록 실서식을 반복 등록, 합성 전량
  python 8_train/make_mix_list.py --out 8_train/yolo_s1v4/mix_real10.txt --real-frac 0.10 \
     --real 8_train/yolo_s1v4/images/replica_train \
     --synth 8_train/yolo_s1v4/images/train 7_augment/pool_s1v4/images/office ...

  # (A) 미세조정: 실 전량 ×30, 합성은 리플레이 25% 만큼만 무작위 표집
  python 8_train/make_mix_list.py --out 8_train/yolo_s1v4/ft_real.txt --repeat 30 --synth-frac 0.25 \
     --real 8_train/yolo_s1v4/images/replica_train --synth 7_augment/pool_s1v4/images/office

  python 8_train/make_mix_list.py --selftest
"""
import argparse, glob, os
import numpy as np


def listdir(dirs):
    f = []
    for d in dirs:
        f += sorted(glob.glob(f"{os.path.abspath(d)}/*.png"))
    return f


def build(real, synth, real_frac=None, repeat=None, synth_frac=1.0, seed=0):
    """(목록, 통계). real_frac 이면 반복수를 역산, repeat 이면 그대로 쓴다."""
    assert real, "실서식 이미지가 없다"
    rng = np.random.default_rng(seed)
    if synth_frac < 1.0 and synth:
        n = max(1, round(len(synth) * synth_frac))
        synth = [synth[i] for i in sorted(rng.choice(len(synth), n, replace=False))]
    if repeat is None:
        assert real_frac is not None and 0 < real_frac < 1, "--real-frac 0<f<1 또는 --repeat 필요"
        repeat = max(1, round(real_frac / (1 - real_frac) * len(synth) / len(real)))
    lines = real * repeat + synth
    frac = len(real) * repeat / len(lines)
    return lines, dict(real=len(real), repeat=repeat, real_rows=len(real) * repeat,
                       synth_rows=len(synth), total=len(lines), real_frac=frac)


def selftest():
    real = [f"/i/images/r/{i}.png" for i in range(10)]
    synth = [f"/i/images/s/{i}.png" for i in range(1000)]
    _, st = build(real, synth, real_frac=0.10)
    assert st["repeat"] == 11 and abs(st["real_frac"] - 0.10) < 0.01, st      # 0.1/0.9*1000/10 = 11.1
    _, st = build(real, synth, real_frac=0.20)
    assert abs(st["real_frac"] - 0.20) < 0.01, st
    lines, st = build(real, synth, repeat=30, synth_frac=0.25)
    assert st["repeat"] == 30 and st["synth_rows"] == 250 and len(lines) == 550, st
    assert sum(l.startswith("/i/images/r/") for l in lines) == 300
    # 같은 seed → 같은 합성 표본
    a, _ = build(real, synth, repeat=1, synth_frac=0.3, seed=5)
    b, _ = build(real, synth, repeat=1, synth_frac=0.3, seed=5)
    assert a == b
    print("selftest OK")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--real", nargs="+", default=[], help="실서식 images 폴더(들)")
    ap.add_argument("--synth", nargs="+", default=[], help="합성 images 폴더(들)")
    ap.add_argument("--real-frac", type=float, help="목표 실서식 비율(0~1) — 반복수를 역산")
    ap.add_argument("--repeat", type=int, help="실서식 반복 등록 횟수(직접 지정)")
    ap.add_argument("--synth-frac", type=float, default=1.0, help="합성 리플레이 비율(표집)")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    assert a.out, "--out 필요"
    lines, st = build(listdir(a.real), listdir(a.synth), a.real_frac, a.repeat, a.synth_frac, a.seed)
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    open(a.out, "w").write("\n".join(lines) + "\n")
    print(f"실 {st['real']}장 ×{st['repeat']} = {st['real_rows']}줄 · 합성 {st['synth_rows']}줄 "
          f"· 합계 {st['total']} · 실 비율 {100*st['real_frac']:.1f}%")
    print(f"→ {a.out}   (data yaml 의 train 에 이 경로를 그대로 적는다)")
    print("주의: 라벨은 경로의 /images/ 를 /labels/ 로 바꿔 찾는다 — 목록에 /images/ 가 들어 있어야 한다")


if __name__ == "__main__":
    main()
