#!/bin/bash
# 데이터 pool 전체 빌드. 구분: clean(5_dataset 그대로) / swap(⑥ 재렌더) / office / degraded / stress(홀드아웃 열화 500)
# 사용: nohup ./7_augment/build_pool.sh > 7_augment/build_pool.log 2>&1 &
set -e; cd "$(dirname "$0")/.."
PY=${PY:-./venv/bin/python}; [ -x "$PY" ] || PY=python
Y=${Y:-8_train/yolo}; POOL=${POOL:-7_augment/pool}; RS=${RS:-7_augment/render_swap}; S1=${S1:-0}   # 1단계 8종: Y=8_train/yolo_s1 POOL=7_augment/pool_s1 RS=7_augment/render_swap_v2 S1=1
A="$PY 7_augment/augment.py --out $POOL"
echo "[1/6] office ← clean 20,000";      $A --tier office   --src $Y/images/train --labels $Y/labels/train
echo "[2/6] degraded ← clean 8,000";     $A --tier degraded --src $Y/images/train --labels $Y/labels/train --n 8000 --seed 2
echo "[3/6] stress ← holdout 500 (열화)"; $A --tier degraded --src $Y/images/val   --labels $Y/labels/val   --n 500  --seed 3 --name stress
echo "[4/6] swap 렌더 대기";              until grep -q "^done" $RS.log; do sleep 30; done
echo "[5/6] swap → yolo 형식";            $PY -c "
import sys; sys.path.insert(0,'8_train'); from to_yolo import convert; print('swap', *convert('swap','$RS','$POOL', stage1=bool($S1)))"
echo "[6/6] office/degraded ← swap";     $A --tier office --src $POOL/images/swap --labels $POOL/labels/swap --name office_swap
                                         $A --tier degraded --src $POOL/images/swap --labels $POOL/labels/swap --n 2000 --seed 4 --name degraded_swap
for d in $POOL/images/*; do echo "$(basename $d): $(ls $d | wc -l)"; done
echo BUILD_DONE
