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

## 학습 데이터 정의
- 1차 `8_train/yolo/forms.yaml`: clean만
- 2차 `8_train/yolo/forms_aug.yaml`: 전 구분, test에 stress 포함
