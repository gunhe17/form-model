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

## 결과 (2026-09-08)

| 런 | 가중치 | 홀드아웃 996 | 실서식 44 | stress 500 | 보고서 |
|---|---|---|---|---|---|
| 1차 clean 20,000 · 6 epoch | `runs/ffdnet_1600/weights/best.pt` | recall 99.97 | **66.56** | 55.01 | `1차_학습_감사.pdf` |
| 2차 +증강 62,000 · 1 epoch (R1 종료) | `runs/ffdnet_1600_aug/weights/last_e1.pt` | 100.00 | 59.64 | **99.94** | `2차_학습_보고.pdf` |

recall@IoU0.5, conf 0.25, `score.py` 기준. 픽셀 축(stress)은 2차로 닫혔고 실서식 축은 학습으로 안 풀린다 — 손실이 cgf(−21.9pt)·cg·dbx 셀 채움 계열에 몰림. 다음은 3_generator 치수·구성 분포 확장(gp 폭 40→100px대, cgf 높이 26→41px대, cg 점유율 77%→실서식 비율, opt·circ·dbx 추가) 후 클린+열화를 한 풀로 3차. 효과 확인은 `diag_style.py --compare`.

도구: `score.py` 3축 채점 · `diag_replica.py` 놓침·유령 해부 · `diag_style.py` 스타일별 recall/치수 · `forms_aug.yaml` 2차 데이터 정의.
