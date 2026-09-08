#!/bin/bash
# 데이터 pool 전체 빌드. 구분: clean(5_dataset 그대로) / swap(⑥ 재렌더) / office / degraded / stress(홀드아웃 열화 500)
# 사용: nohup ./7_augment/build_pool.sh > 7_augment/build_pool.log 2>&1 &
set -e; cd "$(dirname "$0")/.."
PY=./venv/bin/python; A="$PY 7_augment/augment.py"; Y=8_train/yolo
echo "[1/6] office ← clean 20,000";      $A --tier office   --src $Y/images/train --labels $Y/labels/train
echo "[2/6] degraded ← clean 8,000";     $A --tier degraded --src $Y/images/train --labels $Y/labels/train --n 8000 --seed 2
echo "[3/6] stress ← holdout 500 (열화)"; $A --tier degraded --src $Y/images/val   --labels $Y/labels/val   --n 500  --seed 3 --name stress
echo "[4/6] swap 렌더 대기";              until grep -q "^done" 7_augment/render_swap.log; do sleep 30; done
echo "[5/6] swap → yolo 형식";            $PY -c "
import sys; sys.path.insert(0,'8_train'); from to_yolo import convert; print('swap', *convert('swap','7_augment/render_swap','7_augment/pool'))"
echo "[6/6] office/degraded ← swap";     $A --tier office --src 7_augment/pool/images/swap --labels 7_augment/pool/labels/swap --name office_swap
                                         $A --tier degraded --src 7_augment/pool/images/swap --labels 7_augment/pool/labels/swap --n 2000 --seed 4 --name degraded_swap
for d in 7_augment/pool/images/*; do echo "$(basename $d): $(ls $d | wc -l)"; done
echo BUILD_DONE
