#!/bin/bash
# P6-4 실데이터 혼합 — (A) v4 가중치 미세조정 head-only vs full, (B) 혼합 학습.
# 사용: nohup ./8_train/finetune_real.sh > 8_train/finetune_real.log 2>&1 &
#       W=.../best.pt MODE=A ./8_train/finetune_real.sh
#
# freeze 값(Ultralytics 8.4.143 에서 확인): freeze=N 은 model.0 ~ model.(N-1) 을 동결한다.
# YOLO11 은 0~10 backbone(10 = C2PSA), 11~22 neck(PAN), 23 Detect head.
#   freeze=10 → 백본 대부분 동결 (5차 본학습에서 쓴 값)
#   freeze=23 → 백본+neck 동결 = **head-only**  ← (A) 1안
#   freeze 없음 + lr0 1e-4 → 전체 미세조정      ← (A) 2안
# 실 100장 규모에서는 head-only 가 안전하다(TFA 2003.06957). 둘 다 돌려 replica_eval 로 고른다.
set -e
cd "$(dirname "$0")/.."
ROOT=$(pwd)
PY=${PY:-yolo}
W=${W:-$ROOT/8_train/runs/ffdnet_s1v4_s0/weights/best.pt}
MODE=${MODE:-AB}
RT=$ROOT/8_train/yolo_s1v4/images/replica_train
EV=$ROOT/8_train/yolo_s1v4/images/replica_eval
COMMON="imgsz=1600 batch=4 device=0 epochs=15 patience=5 save_period=1 \
  optimizer=AdamW lrf=0.05 warmup_epochs=1 cos_lr=True \
  mosaic=0.5 close_mosaic=5 scale=0.7,1.6 translate=0.15 degrees=2 shear=1 perspective=0.0002 \
  fliplr=0 flipud=0 mixup=0 cutmix=0 copy_paste=0 hsv_h=0 hsv_s=0 hsv_v=0.3 \
  project=$ROOT/8_train/runs"

SYNTH="$ROOT/7_augment/pool_s1v4/images/office $ROOT/8_train/yolo_s1v4/images/train"
ALL_SYNTH="$ROOT/8_train/yolo_s1v4/images/train \
  $ROOT/7_augment/pool_s1v4/images/swap $ROOT/7_augment/pool_s1v4/images/office \
  $ROOT/7_augment/pool_s1v4/images/office_swap $ROOT/7_augment/pool_s1v4/images/degraded \
  $ROOT/7_augment/pool_s1v4/images/degraded_swap"

if [[ $MODE == *A* ]]; then
  # 실 전량 ×30 + 합성 리플레이 ~25% (make_mix_list 출력의 '실 비율' 로 확인)
  python 8_train/make_mix_list.py --out $ROOT/8_train/yolo_s1v4/ft_real.txt \
    --repeat 30 --synth-frac 0.02 --real $RT --synth $SYNTH
  echo "=== A1 head-only (freeze=23, lr0 1e-3) ==="
  $PY detect train model=$W data=$ROOT/8_train/forms_ft_real.yaml $COMMON \
    freeze=23 lr0=0.001 seed=0 name=ft_head
  echo "=== A2 full (freeze 없음, lr0 1e-4) ==="
  $PY detect train model=$W data=$ROOT/8_train/forms_ft_real.yaml $COMMON \
    lr0=0.0001 seed=0 name=ft_full
fi

if [[ $MODE == *B* ]]; then
  for F in 0.05 0.10 0.20; do
    T=$ROOT/8_train/yolo_s1v4/mix_real${F#0.}.txt
    python 8_train/make_mix_list.py --out $T --real-frac $F --real $RT --synth $ALL_SYNTH
    echo "=== B 혼합 학습 실 $F ==="
    sed "s|mix_real10.txt|$(basename $T)|" $ROOT/8_train/forms_mix.yaml > $ROOT/8_train/runs/forms_mix_${F}.yaml
    $PY detect train model=$ROOT/8_train/weights/FFDNet-L.pt data=$ROOT/8_train/runs/forms_mix_${F}.yaml \
      $COMMON epochs=30 close_mosaic=9 freeze=10 lr0=0.001 seed=0 name=mix_real${F#0.}
  done
fi

# 판정: replica_eval 에서 짝지은 부트스트랩. v4 기준선과 각 변형을 A−B 로 비교한다
for N in ft_head ft_full mix_real05 mix_real10 mix_real20; do
  B=$ROOT/8_train/runs/$N/weights/best.pt
  [ -f "$B" ] || continue
  python 8_train/score.py --model $B --name ${N}_eval --images $EV \
    --labels $ROOT/8_train/yolo_s1v4/labels/replica_eval --conf 0.05 \
    --dump $ROOT/8_train/runs/score/miss_dump_${N}_eval.json
  python 8_train/diag_ci.py $ROOT/8_train/runs/score/miss_dump_${N}_eval.json \
    $ROOT/8_train/runs/score/miss_dump_v4_s0_eval.json
done
echo FINETUNE_DONE
