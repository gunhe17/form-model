# 8 학습 — 검출기 트랙 (1차 시도)

두 갈래 중 검출기를 먼저 간다. 언어 모델은 종류 판별이 미달일 때만 2단계로 붙인다.

## 결정 (2026-09-08)

| 항목 | 결정 | 근거 |
|---|---|---|
| 프레임워크 | Ultralytics YOLO | CommonForms FFDNet이 YOLO11 기반이라 그대로 호환 |
| 시작 가중치 | `weights/FFDNet-L.pt` (HF `jbarrow/FFDNet-L`, YOLO11 25M, 3클래스 textbox/choice_button/signature, 1216px 150 epoch) | 이미 서식 입력칸 검출기. 헤드만 11클래스로 교체(Ultralytics 자동, 스모크 확인) |
| 입력 크기 | **imgsz 1600** | 페이지 94%가 1004×1400이라 축소 없음. 최악(2837px) 스케일 0.56 → 22px 마커 12px. 스케일 후 최소 요소 변 <12px 인 페이지 0.4%. 2048은 0.0%지만 연산 1.6배 — 1600 결과 보고 판단 |
| 증강 | FFDNet 레시피 그대로(mosaic 1.0, scale 0.5) 단 **fliplr=0** | 좌우 반전은 라벨 글자를 뒤집어 종류 판별을 해침. FFDNet은 3클래스라 무관했음 |
| 분할 | train 20,000 / val 996(홀드아웃) / test 44(실서식 복제) | 음성 페이지 1,323장은 빈 라벨 파일 |

해상도 실측(학습 20,000장):

| imgsz | 축소되는 페이지 | 최악 스케일 | 22px 마커 → | 최소 요소 변 <12px 페이지 |
|---|---|---|---|---|
| 1216 (FFDNet 원래) | 100% | 0.43 | 9.4px | 3.1% |
| **1600** | 5.9% | 0.56 | 12.4px | 0.4% |
| 2048 | 1.7% | 0.72 | 15.9px | 0.0% |

## 실행

```bash
pip install ultralytics huggingface_hub
python 8_train/to_yolo.py                       # 5_dataset → yolo/ (심볼릭 링크 + 라벨)
python -c "from huggingface_hub import hf_hub_download as d; d('jbarrow/FFDNet-L','FFDNet-L.pt',local_dir='8_train/weights')"

# 본런 (RTX 3090 ×1) — data/project 는 절대경로로 준다
yolo detect train model=8_train/weights/FFDNet-L.pt data=/work/8_train/yolo/forms.yaml \
  imgsz=1600 epochs=60 batch=4 device=0 fliplr=0 project=/work/8_train/runs name=ffdnet_1600

# 채점: 홀드아웃(val) + 실서식 복제(test)
yolo detect val model=8_train/runs/ffdnet_1600/weights/best.pt data=8_train/yolo/forms.yaml imgsz=1600 split=val
yolo detect val model=8_train/runs/ffdnet_1600/weights/best.pt data=8_train/yolo/forms.yaml imgsz=1600 split=test
```

3090 1장 + imgsz 1600 은 **batch 4 가 상한**(batch 8 은 CUDA OOM, batch 4 에서 21.7/24.5GB · util 83%). 에폭당 약 30분(학습 5,000 iter 약 28분 + val 996장) → 60에폭 약 30시간. `project` 를 상대경로로 주면 Ultralytics 8.4.143 이 자체 `runs_dir` 밑(`runs/detect/8_train/runs/...`)에 써서 위 채점 명령이 `best.pt` 를 찾지 못한다. 로컬(Mac)에서는 `./venv/bin/` 접두어, 컨테이너에서는 시스템 python 그대로.

파일: `to_yolo.py` 변환기 · `yolo/forms.yaml` 데이터 정의 · `yolo_smoke/` 24장 파이프라인 점검용(CPU 1 epoch 통과).

## 채점 기준 (mAP 한 숫자로 보지 않는다)
- 놓침: recall@IoU0.5 ≥ 98%
- 좌표: 매칭된 박스 중 IoU≥0.5 비율 ≥ 95%
- 종류: 매칭된 박스의 클래스 정확도 ≥ 97% — 클래스별 confusion 필수. 예상 약점: checkbox↔radio, text↔number↔date↔phone (모양 동일, 라벨 글자로만 구분)
- 실물 격차: val(합성) 대비 test(복제 44쪽)가 크게 낮으면 합성 과적합

## 다음
종류 정확도 미달 시 2단계: 검출기 박스마다 주변 크롭을 Qwen3-VL에 주고 11종 중 하나만 고르게 한다(좌표 생성 없음 → 유령 없음).

## 결과

| 학습 | 가중치 | 홀드아웃 recall | 실서식 recall | stress recall | 보고서 |
|---|---|---|---|---|---|
| 1차 (의미 11종, clean 20,000 · 6 epoch) | `runs/ffdnet_1600/weights/best.pt` | 99.97 | 69.57 | 55.01 | `docs/1차_학습_감사.pdf` |
| 2차 (11종 + 증강 62,000 · 1 epoch R1) | `runs/ffdnet_1600_aug/weights/last_e1.pt` | 100.00 | 63.36 | 99.94 | `docs/2차_학습_보고.pdf` |
| 3차 (1단계 생김새 8종, v2 · 3 epoch R4, e1 채택) | `runs/ffdnet_s1/weights/last_e1.pt` | 99.96 | 83.85 | 99.88 | `docs/3차_학습_보고.pdf` · `docs/PLAN.md` 8절 |
| 4차 (8종, v3 생성기 · 3 epoch R4, e1 채택) | `runs/ffdnet_s1v3/weights/last_e1.pt` | 99.91 | 90.43 (44장) / **92.09 [87.4, 96.1]** (평가분 52장) | 99.87 | `docs/4차_학습_보고.pdf` · `docs/PLAN.md` 9절 |
| 5차 (8종, v4 변동 폭 · val=실서식 · freeze 10 · 3 epoch R4', e1 채택) | `runs/ffdnet_s1v4_s0/weights/best.pt` | — (val=실서식 105: 93.62 [90.4, 96.5]) | 92.50 [88.0, 96.2] (평가분 52장) | 94.03 | `docs/PLAN.md` 10절 |
| 5차-ft (4차 e1 + 실서식 105장 미세조정 full 1e-4 · 15 epoch 고정 · last.pt) | `runs/ft_full_v3e1/weights/last.pt` | — | 96.49 [92.6, 98.6] (평가분 52장, max_det 1000 보정) | 95.65 (v4 stress) | `docs/PLAN.md` 10.11 |
| ft_full_v4syn (v4 합성 수렴 6 epoch → 실서식 105장 full 미세조정 15 epoch 고정 · last.pt) | `runs/ft_full_v4syn/weights/last.pt` | 합성 val mAP50-95 0.846(베이스) | 96.41 [92.3, 98.6] (평가분 52장, 4차 e1 대비 +2.55 [+0.9, +4.1], max_det 1000) · 좌표 99.16 · 종류 99.51 | 98.36 (v4 stress) | `docs/PLAN.md` 10.11 |
| ft_full_v4syn_x34b (위 + 리플레이 x3 ×3·x4 ×2, 36.6%) | `runs/ft_full_v4syn_x34b/weights/last.pt` | — | 98.26 [97.1, 99.0] (평가분 52장) · 좌표 99.40 · 종류 99.36 | 97.88 (v4 stress, −0.12) | `docs/PLAN.md` 10.15 |
| **최종 채택 · ft_v5e (v5syn 재수렴 베이스 → 실서식 105장 full 미세조정, 리플레이 822+x3×3+x4×1+x6×1+x7×1 = 39.1%)** | **`runs/ft_v5e/weights/last.pt`** | 베이스 합성 val mAP50-95 0.848 | **98.37 ✓** (평가분 52장, 전사 정정 후) · 좌표 99.70 ✓ · 종류 99.51 ✓ | **98.51 ✓** (v4 stress) | `docs/PLAN.md` 10.23 · **4축 전부 통과** |

recall@IoU0.5, `score.py`. 1·2차 실서식은 conf 0.25·11종(GT 999), 3차는 conf 0.05·8종(GT 972, word·area 제외; conf 0.25 로는 80.76). 4차부터 실서식은 157장 중 평가분 52장(서식 단위 분할)·페이지 군집 부트스트랩 95% CI 를 붙인다(`diag_ci.py`). 2026-09-12 이후 채점은 `--max-det 1000`(기본) — 그 전 157장 수치는 밀집 페이지 절단으로 과소(DECISIONS 22). stress 는 풀(v3/v4)을 명기. 3차는 실서식 좌표 96.22·종류 97.17 로 두 축 통과, recall 만 미달(기준 98). 4차(v3: MKC 삭제·inline_pairs·밀착 슬롯·자리표 PH·셀 안 (인)) 는 실서식 90.43·좌표 97.13·종류 97.13, 실서식 mAP50 0.74→0.80(mAP50-95 0.51→0.57), 스타일별 gp +8.9·cg +7.8·cgf +7.0·(none) +11.4. 실서식 mAP50 0.27→0.74.
3차 스타일별(1차 대비): cg 7.8→70.6, cgf 66.8→84.9, gp 59.1→76.6, opt·circ·stamp 0→100. 남은 놓침 125개는 글자 인쇄 척도 선택칸과 폭 ≤20px 밀착 빈칸(학습 0개)이 대부분 → 다음 생성기 보강(`docs/DECISIONS.md` 9절).

도구: `score.py` 3축 채점 · `diag_replica.py` 놓침·유령 해부 · `diag_style.py` 스타일별 recall/치수 · `forms_aug.yaml` 2차 데이터 정의.

- `diag_dump.py` — GT 단위 매칭 덤프 → 놓침 원인 귀속표 (PLAN 9절)

## 5차(P6) 도구와 실행 — 측정 먼저

4차까지의 판정은 전부 **합성 val** 위에서 내려졌고(best.pt·patience·조기 종료), 실서식 수치는 점추정이었다.
5차는 그 둘을 고친다: 판정 기준을 실서식으로 옮기고, 모든 실서식 수치에 CI 를 붙인다.
근거는 `6_research/variation/README.md`(교차 검증)와 `docs/PLAN.md` 10절.

| 도구 | 무엇을 재나 | 자가검증 |
|---|---|---|
| `score.py --dump` | GT 단위 매칭 덤프(miss_dump_*.json) 산출 — 아래 세 도구의 공통 입력 | `--selftest` |
| `diag_ci.py` | 페이지 군집 부트스트랩 95% CI, 페이지 평균 recall, 최악 5쪽, 두 덤프면 짝지은 A−B 차 CI | `--selftest` |
| `diag_conf.py` | conf 히스토그램, 합성 vs 실 AUROC, 검출 ECE, temperature 1개 보정 후 임계 0.05/0.10/0.25 recall·유령 | `--selftest` |
| `diag_coverage.py` | backbone 크롭 임베딩으로 density/coverage(k=5) · Vendi 를 클래스별·전체 | `--selftest` |
| `4_replica/split_anchor.py` | 실서식을 **서식 단위** 2:1 로 분할 → `4_replica/split.json` (105 train / 52 eval, 서식 겹침 0) | `--check` |
| `make_mix_list.py` | 실/합성 혼합 이미지 목록(.txt) — 실 비율에서 반복 등록 횟수를 역산 | `--selftest` |

결과표에 붙일 한 줄은 `diag_ci.py` 가 그대로 찍는다: `90.43 [87.5, 93.1]`.

### 실행 순서 (컨테이너, /work)

```bash
# 0. 앵커 분할 + YOLO 변환 (v4 렌더·풀은 7_augment/README '5차' 절 참조)
python 4_replica/split_anchor.py
python 8_train/to_yolo.py --stage1 --out 8_train/yolo_s1v4 \
  --train-dir 5_dataset/train_v4 --val-dir 5_dataset/holdout_v4 --replica-split

# 1. P6-0 측정 — 4차 가중치로 먼저 기준선을 만든다 (GPU 1장, 학습 전)
python 8_train/score.py --model 8_train/runs/ffdnet_s1v3/weights/last_e1.pt --name v3e1_real --conf 0.05 \
  --images 8_train/yolo_s1v3/images/replica --labels 8_train/yolo_s1v3/labels/replica \
  --dump 8_train/runs/score/miss_dump_v3e1_real.json
python 8_train/score.py --model 8_train/runs/ffdnet_s1v3/weights/last_e1.pt --name v3e1_hold --conf 0.05 \
  --images 8_train/yolo_s1v3/images/val --labels 8_train/yolo_s1v3/labels/val \
  --dump 8_train/runs/score/miss_dump_v3e1_hold.json
python 8_train/diag_ci.py   8_train/runs/score/miss_dump_v3e1_real.json
python 8_train/diag_conf.py 8_train/runs/score/miss_dump_v3e1_real.json --synth 8_train/runs/score/miss_dump_v3e1_hold.json
python 8_train/diag_coverage.py --model 8_train/runs/ffdnet_s1v3/weights/last_e1.pt --max-boxes 2000 --chunk 64 \
  --real  8_train/yolo_s1v3/images/replica:8_train/yolo_s1v3/labels/replica \
  --fake  8_train/yolo_s1v3/images/train:8_train/yolo_s1v3/labels/train

# 2. P6-3 학습 v4 (3시드, 각 시드 끝에 replica_eval 채점 + CI 자동)
nohup ./8_train/train_v4.sh > 8_train/train_v4.log 2>&1 &

# 3. P6-4 실데이터 혼합 — (A) 미세조정 head-only/full, (B) 혼합 5/10/20%
nohup ./8_train/finetune_real.sh > 8_train/finetune_real.log 2>&1 &

# 4. 최종 비교 — 짝지은 페이지 부트스트랩으로 후보 vs v4 기준선
python 8_train/diag_ci.py 8_train/runs/score/miss_dump_ft_head_eval.json 8_train/runs/score/miss_dump_v4_s0_eval.json
```

데이터 정의: `forms_s1v4.yaml`(본학습, **val=replica_train**) · `forms_ft_real.yaml`(A) · `forms_mix.yaml`(B).
학습 스크립트: `train_v4.sh`(3시드) · `finetune_real.sh`(A·B + 채점까지).

## 최종 채택 가중치 재현 (ft_v5e, 2026-09-16)

베이스는 v5syn 재수렴본, 그 위에 실서식 학습분 105장을 full 미세조정한다. 리플레이 목록·yaml 은 생성물(gitignore)이라 아래 절차로 만든다.

**1. 베이스** (v4 렌더 + 카드 x3·x4·x5 600장을 합친 train 64,540, val=합성 홀드아웃)
```
# 렌더·풀 준비는 3_generator/README v4~v4x5 절, 7_augment/README 5차 절
yolo detect train model=weights/FFDNet-L.pt data=8_train/forms_s1v4_syn.yaml   imgsz=1600 batch=4 device=0 epochs=6 patience=0 save_period=1 freeze=0   optimizer=AdamW lr0=0.001 lrf=0.05 warmup_epochs=1 cos_lr=True   mosaic=0.5 close_mosaic=2 scale=0.7,1.6 translate=0.15 degrees=2 shear=1 perspective=0.0002   fliplr=0 flipud=0 mixup=0 cutmix=0 copy_paste=0 hsv_h=0 hsv_s=0 hsv_v=0.3   seed=0 project=8_train/runs name=ffdnet_s1v5_syn        # best.pt(e6) 채택
```

**2. 리플레이 목록** 5,172줄 = 실 3,150(60.9%) + 리플레이 2,022(39.1%)

| 출처 | 배수 | 줄 | 내용 |
|---|---|---|---|
| `yolo_s1v4/images/replica_train` | ×30 | 3,150 | 실서식 학습분 105장 |
| `yolo_s1v4/images/train` + `pool_s1v4/images/office` | ×1 | 822 | 기존 합성 리플레이(`make_mix_list --synth-frac 0.02`) |
| `yolo_s1v4x3/images/train` | ×3 | 600 | hrule_table (세로 괘선 없는 표) |
| `yolo_s1v4x4/images/train` | ×1 | 200 | contract_lines (초장문 gap) |
| `yolo_s1v4x6/images/train` | ×1 | 200 | 17호형 척도표(머리글 행 없음) |
| `yolo_s1v4x7/images/train` | ×1 | 200 | suffix_cell_row·date_dots·num_affix |

```
python 8_train/make_mix_list.py --out 8_train/yolo_s1v4/ft_real.txt --repeat 30 --synth-frac 0.02   --real 8_train/yolo_s1v4/images/replica_train   --synth 7_augment/pool_s1v4/images/office 8_train/yolo_s1v4/images/train
# 위 822줄에 카드 렌더분을 배수대로 덧붙여 ft_real_v5e.txt 를 만든다(절대경로 정렬 순)
```
yaml 은 `forms_ft_real.yaml` 에서 train 만 `ft_real_v5e.txt` 로 바꾼 사본(val=replica_train, test=replica_eval+stress).

**3. 미세조정** (15에폭 고정·last.pt 채택 — val 이 학습분의 부분집합이라 체크포인트 선택 자유도 0)
```
yolo detect train model=8_train/runs/ffdnet_s1v5_syn/weights/best.pt   data=8_train/runs/forms_ft_real_v5e.yaml   imgsz=1600 batch=4 device=0 epochs=15 patience=0 save_period=1   optimizer=AdamW lr0=0.0001 lrf=0.05 warmup_epochs=1 cos_lr=True   mosaic=0.5 close_mosaic=5 scale=0.7,1.6 translate=0.15 degrees=2 shear=1 perspective=0.0002   fliplr=0 flipud=0 mixup=0 cutmix=0 copy_paste=0 hsv_h=0 hsv_s=0 hsv_v=0.3   seed=0 project=8_train/runs name=ft_v5e            # weights/last.pt = 최종
```

**4. 채점** `score.py --max-det 1000`(기본) 로 replica_eval·stress, `diag_ci.py` 로 CI, `diag_dump.py` 로 귀속표.

**보존 대상**: `runs/ft_v5e/weights/last.pt` · `runs/ffdnet_s1v5_syn/weights/best.pt` · `runs/score/{miss_dump_ft_v5e_eval_md1000, ft_v5e_eval_md1000, ft_v5e_stress_md1000}.json`.

## 산출물 정리
- `../7_augment/cleanup_pools.sh` — 종료 라운드의 증강 풀 3경로(pool·pool_s1·pool_s1v3). 2026-09-11 실행, 31GB 회수.
- `cleanup_epochs.sh` — 학습 런의 에폭 스냅샷(`runs/*/weights/epoch*.pt`)만. **last.pt·best.pt 는 전부 보존**, `ft_v5e`·`ffdnet_s1v5_syn` 두 런은 통째로 제외. 둘 다 G1~G5 검사 통과 시에만 지우고 기본은 dry-run(`--yes` 로 실행).

