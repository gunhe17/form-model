# 7 증강 — 구분별 데이터 pool (검출기 트랙)

골격=조판(픽셀 불가침) / 증강=획득 과정(조판 불가침) 계약 유지. 검출기는 라벨이 정규화 좌표라 픽셀 축은 라벨을 건드리지 않는다.

## 7축 → 담당

| 축 | 담당 | 비고 |
|---|---|---|
| ① dpi 리샘플 | `augment.py` (축소만) | 학습 letterbox가 도로 키움 → 선 굵기·선명도 변화만 남음 |
| ② 회전·원근·오프셋 | YOLO 온라인 (`degrees=1.0 perspective=0.0005 translate scale`) | 라벨 자동 변환 |
| ③ 밝기·대비·조명경사·종이톤 | `augment.py` | |
| ④ 가우시안·JPEG·줄무늬·먼지 | `augment.py` | |
| ⑤ 잉크 팽창/침식·블러 | `augment.py` | 축소 전 원해상도에서 부분 블렌드(침식 0.25~0.5, 팽창 0.3~0.6) |
| ⑥ 서체 스왑 | `render_swap.py` (재렌더, GT 재추출) | gothic(전체 나눔고딕) / myeongjo(함초롬→나눔명조), md5 결정적 |
| ⑦ 러닝헤드·쪽번호·챕터탭 | `augment.py` | 여백에만 그림(상 95 좌우 95 하 72px) |

## 구분 (pool)

| 구분 | 장수 | 원천 | 강도 | 용도 |
|---|---|---|---|---|
| clean | 20,000 | 5_dataset/train | 없음 | 1차 학습 (`forms.yaml`) |
| swap | 6,000 | 골격 재렌더 | 서체만 | 2차 학습 |
| office | 20,000 | clean ×1벌 | 사무 스캔: dpi .70~1.0, 경사 ≤10%, JPEG 70~92, 잉크 30% | 2차 학습 |
| office_swap | 6,000 | swap ×1벌 | 〃 | 2차 학습 |
| degraded | 8,000 | clean 표본 | 열화: dpi .55~.85, 경사 ≤28%, JPEG 35~65, 노이즈 σ4~10, 잉크 70% | 2차 학습 |
| degraded_swap | 2,000 | swap 표본 | 〃 | 2차 학습 |
| stress | 500 | 홀드아웃 열화 | 열화 | **평가 전용** (실물 스캔 대용) |

합계 학습 62,000 (클린계 26k 42% · 사무 26k 42% · 열화 10k 16%). 평가: 홀드아웃 996(클린) + 복제 44(클린) + stress 500(열화).

## 실행

```bash
./venv/bin/python 7_augment/render_swap.py --n 6000 > 7_augment/render_swap.log 2>&1 &   # ⑥ 약 1시간
nohup ./7_augment/build_pool.sh > 7_augment/build_pool.log 2>&1 &                        # 나머지 전부, swap 완료 자동 대기
```

검수: 12장 표본 잉크 보존율(종이 톤 적응 임계) 침식 0.73~1.1, 팽창 1.9~3.0, 무처리 1.1~1.5. 대조 시트로 육안 1회 확인 후 침식·블러 완화.

## 플랫폼 간 렌더 차이 (2026-09-08 측정)

`render_swap.py` 를 Mac 이 아닌 컨테이너에서 돌리면 결과가 로컬과 **바이트 동일하지 않다**. 같은 골격 4장(`time_cell` 포함 2장)을 재렌더해 `5_dataset/train` 원본과 비교한 값:

| 항목 | 차이 |
|---|---|
| 요소 개수·타입 | 100% 일치 (type_mismatch 0) |
| 좌표 | 최대 0.52~1.58px |
| PNG 픽셀 | 0.8~1.1% 상이 |
| HTML | 폰트 절대경로만 다름 |

원인은 Chromium 빌드·폰트 래스터화 차이다. 골격 생성과 GT 추출 로직 자체는 결정적이고(시드 고정), GT 를 같은 렌더에서 다시 뽑으므로 라벨-픽셀 정합은 구분 내부에서 완결된다. 따라서 Mac 렌더 clean 26k 와 컨테이너 렌더 swap 14k 가 섞이는 것은 증강 다양성으로 본다. 2차 결과가 이상하면 이 지점을 먼저 의심할 것.

## 학습 데이터 정의
- 1차 `8_train/yolo/forms.yaml`: clean만
- 2차 `8_train/forms_aug.yaml`(추적 파일): 전 구분, test에 stress 포함

## 3차(1단계 8종·v2) 실행
```
python 8_train/to_yolo.py --stage1 --out 8_train/yolo_s1 --train-dir 5_dataset/train_v2 --val-dir 5_dataset/holdout_v2
nohup python 7_augment/render_swap.py --n 6000 --src 5_dataset/skeletons_v2/train --out 7_augment/render_swap_v2 > 7_augment/render_swap_v2.log 2>&1 &
Y=8_train/yolo_s1 POOL=7_augment/pool_s1 RS=7_augment/render_swap_v2 S1=1 nohup ./7_augment/build_pool.sh > 7_augment/build_pool_s1.log 2>&1 &
```
데이터 정의 `8_train/forms_s1.yaml`. build_pool 은 `Y`(YOLO 라벨 폴더)·`POOL`·`RS`(스왑 렌더)·`S1`(1단계 라벨) 환경변수로 v1/v2 를 가른다.

## 4차(1단계 8종·v3) 실행
```
python 8_train/to_yolo.py --stage1 --out 8_train/yolo_s1v3 --train-dir 5_dataset/train_v3 --val-dir 5_dataset/holdout_v3
nohup python 7_augment/render_swap.py --n 6000 --src 5_dataset/skeletons_v3/train --out 7_augment/render_swap_v3 > 7_augment/render_swap_v3.log 2>&1 &
Y=8_train/yolo_s1v3 POOL=7_augment/pool_s1v3 RS=7_augment/render_swap_v3 S1=1 nohup ./7_augment/build_pool.sh > 7_augment/build_pool_s1v3.log 2>&1 &
```
데이터 정의 `8_train/forms_s1v3.yaml`. 3차와 구성 동일, 렌더만 v3.

## 5차(1단계 8종·v4) 실행
```
python 4_replica/split_anchor.py                                    # 실서식 서식 단위 2:1 분할 (한 번만)
python 8_train/to_yolo.py --stage1 --out 8_train/yolo_s1v4 --train-dir 5_dataset/train_v4 --val-dir 5_dataset/holdout_v4 --replica-split
nohup python 7_augment/render_swap.py --n 6000 --src 5_dataset/skeletons_v4/train --out 7_augment/render_swap_v4 > 7_augment/render_swap_v4.log 2>&1 &
Y=8_train/yolo_s1v4 POOL=7_augment/pool_s1v4 RS=7_augment/render_swap_v4 S1=1 nohup ./7_augment/build_pool.sh > 7_augment/build_pool_s1v4.log 2>&1 &
```
`build_pool.sh` 는 v3 와 동일 — `Y`·`POOL`·`RS`·`S1` 환경변수만 v4 경로로 바꾼다(스크립트 수정 없음).
데이터 정의 `8_train/forms_s1v4.yaml`. 4차와 달라진 곳은 **구분 구성이 아니라 val** 이다:
val 이 합성 홀드아웃에서 **실서식 학습분(`images/replica_train`)** 으로 바뀌었다. Ultralytics 가 best.pt·patience 를
val fitness 로 고르기 때문에, val 이 합성이면 "합성만 오르고 실서식은 e1 정점" 을 잡을 수 없다
(6_research/variation/C 5절). test 는 서식 단위로 분리된 `replica_eval` + stress.
