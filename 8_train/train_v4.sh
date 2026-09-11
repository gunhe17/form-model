#!/bin/bash
# 5차 학습 (1단계 8종 · v4 생성기 · 실서식 val) — 3시드.
# 사용: nohup ./8_train/train_v4.sh > 8_train/train_v4.log 2>&1 &
#       SEEDS="0" ./8_train/train_v4.sh          # 1시드만
#
# 하이퍼 근거는 6_research/variation/C_train_augmentation.md 4절, PLAN 10절 P6-3.
#   fliplr 0                거울상 서식은 없고 라벨 글자를 뒤집는다
#   hsv_h/s 0, hsv_v 0.3    회색조 문서에서 hue·채도는 no-op(연산만 듦), 밝기만 유효
#   mosaic 0.5 + close_mosaic 9   batch 4 의 BN 통계 이득은 남기되, 절단된 부분 박스를 줄인다(30 의 30%)
#   scale 0.7,1.6           축소 하한 0.7 (8px 마커 소실 방지) · 확대는 크게(LSJ)
#   degrees 2               Ultralytics 는 회전 후 외접 사각형으로 재포장 → 3° 넘으면 소형 박스가 부푼다
#   freeze 10               model.0~9 동결. FFDNet-L 백본은 같은 문서 도메인 48만 장 출신
#   patience 5 · save_period 1   val 이 실서식이므로 조기 종료가 비로소 의미를 갖는다. 에폭별 가중치로 recall 곡선
#   mixup/cutmix/copy_paste 0    copy_paste 는 폴리곤 라벨 필요 → 7_augment 골격 수준으로 대체
#   label_smoothing·dropout·erasing·auto_augment 는 검출에 미연결/분류 전용 — 주지 않는다
set -e
cd "$(dirname "$0")/.."
ROOT=$(pwd)
PY=${PY:-yolo}
DATA=${DATA:-$ROOT/8_train/forms_s1v4.yaml}
MODEL=${MODEL:-$ROOT/8_train/weights/FFDNet-L.pt}
SEEDS=${SEEDS:-"0 1 2"}

for S in $SEEDS; do
  echo "=== seed $S ==="
  $PY detect train \
    model=$MODEL data=$DATA \
    imgsz=1600 batch=4 epochs=30 patience=5 save_period=1 device=0 \
    freeze=10 optimizer=AdamW lr0=0.001 lrf=0.05 warmup_epochs=1 cos_lr=True \
    mosaic=0.5 close_mosaic=9 scale=0.7,1.6 translate=0.15 degrees=2 shear=1 perspective=0.0002 \
    fliplr=0 flipud=0 mixup=0 cutmix=0 copy_paste=0 \
    hsv_h=0 hsv_s=0 hsv_v=0.3 \
    seed=$S project=$ROOT/8_train/runs name=ffdnet_s1v4_s$S
done

# 채점 — 판정은 test(replica_eval)에서만. 에폭별 가중치는 weights/epoch*.pt
for S in $SEEDS; do
  W=$ROOT/8_train/runs/ffdnet_s1v4_s$S/weights/best.pt
  python 8_train/score.py --model $W --name v4_s${S}_eval \
    --images $ROOT/8_train/yolo_s1v4/images/replica_eval --labels $ROOT/8_train/yolo_s1v4/labels/replica_eval \
    --conf 0.05 --dump $ROOT/8_train/runs/score/miss_dump_v4_s${S}_eval.json
  python 8_train/diag_ci.py $ROOT/8_train/runs/score/miss_dump_v4_s${S}_eval.json
done
echo TRAIN_V4_DONE
