# 조사 C — 학습 시 증강·정규화로 유효 변동 폭 넓히기 (검출기, 문서·소형 밀집 객체)

작성일 2026-09-11. 대상: Ultralytics YOLO(FFDNet-L 초기화, imgsz 1600, batch 4, 기본 증강) / 합성 62k 페이지 → 실서식 recall 90.4, epoch 1 이후 실서식 recall 하락.

## 0. 진단 요약 (문헌 대조 전 전제)

- 픽셀 열화(복사·스캔·폰트) 합성 테스트 99.9 vs 실서식 90.4 → 격차는 **외관(texture)이 아니라 배치·형태 분포(layout/shape)** 에 있다. 아래 3절의 스타일 무작위화 계열은 이미 우리가 오프라인으로 해낸 일이고, 추가 이득이 거의 없다.
- "epoch 1에서 실서식 recall 최고" 는 합성→실전이 전형적으로 보이는 **좁은 소스 분포 암기** 증상(Zoph 2019의 "학습 손실을 올려야 일반화된다"는 해석과 정합). 해법은 (a) 학습 중 기하·구성 변동을 크게 늘리고 (b) 실서식 홀드아웃을 val로 두어 그 기준으로 조기 종료·체크포인트 선택하는 것이다.
- Ultralytics 기본값 중 **문서에 무의미하거나 해로운 것**이 셋 있다: `fliplr=0.5`(거울상 서식은 실세계에 없음), `hsv_s=0.7`(이진 이미지에 채도 변동은 no-op), `erasing=0.4`(분류 전용이라 검출에는 적용조차 안 됨). 또 `label_smoothing`은 검출 loss에 연결돼 있지 않고, `copy_paste`는 폴리곤 라벨을 요구한다.

---

## 1. 학습된·강한 증강 정책

### Learning Data Augmentation Strategies for Object Detection — Zoph, Cubuk, Ghiasi, Lin, Shlens, Le. arXiv:1906.11172 (ECCV 2020)
분류용 AutoAugment를 검출로 확장. 색상 연산·기하 연산(이미지+박스 동시)·**박스 내부만 변형하는 BBox_Only 연산** 세 군을 탐색. 최종 정책은 5개 서브정책(TranslateX+Equalize, BBox_Only_TranslateY+Cutout, ShearY+BBox_Only_TranslateY, Rotate+Color, Equalize+TranslateX)이며 **Rotate가 좋은 정책에 가장 자주 등장**. 핵심 수치: COCO RetinaNet-R50 36.7→39.0(+2.3, 백본을 R101로 바꾼 +2.1보다 큼), VOC 전이 +2.7. **데이터가 적을수록 이득이 크다**: 5k 이미지에서 상대 +70%, 9k 11.8→15.1, 14k 16.4→19.9, 23k 22.6→25.3. **소형 객체**: 증강한 9k 모델이 증강 없는 15k 모델을 앞섬("소형 객체에는 데이터 50% 추가보다 증강이 낫다"). 정규화 해석: 학습 손실이 오르고 가중치 L2 노름이 줄어듦; DropBlock·Input/Manifold Mixup을 얹어도 추가 이득 없음.
- 우리 적용: Ultralytics `auto_augment`는 분류 전용이라 검출엔 정책 자체를 못 쓴다. 대신 정책의 핵심 연산을 하이퍼로 흉내낸다 — `degrees=2`(스캔 기울기 수준; Ultralytics는 회전 후 박스를 외접 직사각형으로 다시 감싸므로 8 px 마커가 회전 3°만 넘어도 박스가 부풀어 GT가 흐려진다. 2° 이하 유지), `shear=1`, `translate=0.15`. Equalize/Color는 이진 문서에 무의미. "추가 정규화는 겹쳐도 이득 없다"는 결과를 근거로 dropout/label smoothing 추가 실험은 우선순위 뒤로.

### RandAugment / TrivialAugment / AugMix — Cubuk 2019 (arXiv:1909.13719), Müller & Hutter 2021 (arXiv:2103.10158), Hendrycks 2019 (arXiv:1912.02781)
셋 모두 분류에서 검증된 정책(단순 무작위 선택·강도 하나로 AutoAugment와 동급, AugMix는 손상 견고성). 검출 적용 보고는 주로 corruption robustness(SimROD, ColMix 등)이며 합성→실 layout 격차에 대한 직접 증거는 없다. Ultralytics의 `auto_augment=randaugment|autoaugment|augmix`는 **classify task에만 동작**.
- 우리 적용: 채택 안 함. 우리는 픽셀 손상 견고성이 이미 99.9이고, 이 계열은 형태·배치 변동을 만들지 않는다.

---

## 2. 기하·구성 증강

### Simple Copy-Paste is a Strong Data Augmentation Method for Instance Segmentation — Ghiasi et al. arXiv:2012.07177 (CVPR 2021)
두 이미지에 각각 **대규모 스케일 지터(LSJ, 0.1–2.0배; 표준 0.8–1.25 대비)** 를 걸고 한쪽 인스턴스를 다른 쪽에 무작위 위치로 붙인다. 블렌딩 불필요, 문맥 불일치(47%)여도 이득 유지. COCO Mask R-CNN EffNet-B7: box +1.5/+1.1/+1.5 AP(640/1024/1280). **데이터 효율**: COCO 10%에서 +10 box AP, 75% 데이터 + Copy-Paste = 100% 데이터 기본 증강. LVIS 희소 클래스 +3.6 mask AP. 소형 객체 APs도 +1 수준. 긴 스케줄(576 ep)에서 과적합 없이 이득 증가.
- 우리 적용: Ultralytics `copy_paste`는 **세그먼트 폴리곤이 있어야 동작**(issues #6590, #18073) → 박스 GT만 있는 우리는 하이퍼로 켤 수 없다. 대신 `7_augment/`에 **골격 수준 copy-paste**: 렌더된 페이지에서 서명란·사진란·□마커 묶음의 crop을 다른 페이지의 빈 여백(transparent gap이 없는 영역)에 IoA<0.3 조건으로 붙이고 GT를 합친다(블렌딩 불필요라는 결과가 구현을 단순하게 함). 우선 대상은 페이지당 빈도가 낮은 signature·photo. LSJ는 `scale` 튜플로 근사 — 아래 참조.

### Augmentation for small object detection — Kisantal, Wojna, Murawski, Naruniec, Cho. arXiv:1902.07296
COCO 소형 AP가 대형의 1/2–1/3인 원인을 (1) 소형 객체 포함 이미지가 적고 (2) 포함해도 개수가 적어 앵커 매칭이 드문 것으로 진단. **소형 객체 포함 이미지 오버샘플링 + 같은 이미지 안에서 소형 객체를 여러 번 복붙**으로 소형 세그 +9.7%, 검출 +7.1% (상대).
- 우리 적용: 우리 페이지는 이미 밀집(중앙값 30)이라 (2)는 충분. 대신 **클래스별 희소성**(signature/photo/placeholder는 페이지당 0–1)에 오버샘플링을 적용: 골격 샘플러에서 해당 부품을 포함하는 골격의 가중치를 올리거나, 데이터 yaml에 그 페이지를 2–3배 중복 등록(Ultralytics는 이미지 리스트 중복을 허용).

### YOLOv4: Optimal Speed and Accuracy of Object Detection — Bochkovskiy, Wang, Liao. arXiv:2004.10934
Mosaic(4장 합성) 도입. 근거는 "정상 문맥 밖에서도 검출" 과 "BN이 4장 통계를 봐서 작은 mini-batch 요구를 줄임". 검출기 ablation(CSPResNeXt50-PANet-SPP, 512): baseline 38.0 → +Mosaic 38.7 AP(+0.7); 전 기법+CIoU 42.4.
- 우리 적용: **batch 4인 우리에게 BN 통계 효과는 실질적**이므로 mosaic을 완전히 끄지 않는다. 다만 문서에서의 부작용 둘 — (a) 캔버스 2×imgsz 후 무작위 crop이 comb box 열이나 표 셀을 잘라 **절단된 부분 박스 GT**를 만든다(Ultralytics는 잘린 박스를 면적 비율로 필터하지만 8–60 px 객체는 임계 근처에서 흔들림), (b) 네 페이지의 배율이 제각각이라 소형 객체가 4 px까지 축소된다. 처방: `mosaic=0.5`, `scale`을 좁혀 축소 하한을 0.7로, `close_mosaic`은 총 epoch의 마지막 30%.

### Select-Mosaic: Data Augmentation Method for Dense Small Object Scenes — arXiv:2406.05412
표준 Mosaic이 **밀집 소형 객체 장면(항공 영상)** 에서 무차별 절단·축소로 성능을 깎는다고 지적, 영역 선택식 Mosaic 제안(구체 수치는 초록에 없음).
- 우리 적용: 위 mosaic 절단 문제의 독립 증거. 자체 구현 대신 `mosaic=0.5`+좁은 `scale`로 흉내내고, 이득이 있으면 골격 단위 2×2 페이지 합성(절단 없는 mosaic)을 `7_augment`에 추가.

### 문서 검출 대회·시스템의 실제 설정
- **WeLayout (ICDAR 2023 DocLayNet 1위, arXiv:2305.06553)**: YOLOv8 전처리에서 **"flip과 mosaic을 불필요한 것으로 제거"**. DINO 쪽은 소형 텍스트를 위해 스케일 데이터+멀티스케일 증강으로 76.8→78.4→79.0 mAP.
- **ICDAR 2023 대회 보고 (arXiv:2305.14962)**: YOLOv8 참가팀 150 epoch, 마지막 20 epoch mosaic 해제.
- **DocLayout-YOLO (arXiv:2410.12628, opendatalab GitHub `assets/script.sh`)**: YOLOv10 기반, DocSynth-300K 사전학습 `--epoch 500 --image-size 1600 --batch-size 128 --optimizer SGD --lr0 0.02`, D4LA 미세조정 `--lr0 0.04`, 증강은 **Ultralytics 기본값 그대로(mosaic 1.0)**. 합성 데이터 자체의 다양성(Mesh-candidate BestFit)에 투자하고 증강 ablation은 보고하지 않음.
- **CommonForms/FFDNet (arXiv:2509.16506)**: YOLO11, 1216 px, 300 epoch, lr0 0.001, 4×V100, from scratch. 증강 명시 없음(=Ultralytics 기본). 해상도 640→1536에서 ~20점 차, **Choice button(□)이 해상도에 가장 민감**.
- 우리 적용: 문서 커뮤니티 컨센서스는 "**flip 제거, mosaic은 약하게 또는 후반 해제, 해상도 최우선**". 우리 imgsz 1600은 이미 상한. `fliplr=0.0` 확정.

### Multi-scale / 스케일 지터 (Ultralytics `scale`, `multi_scale`)
`scale=s`는 1−s~1+s 균등 배율(기본 0.5→0.5–1.5), 튜플 지정 가능. `multi_scale=f`는 배치마다 imgsz 자체를 ±f(stride 반올림)로 바꿈(예: 640, 0.25→480–800). LSJ 논문은 넓은 범위가 데이터 효율 2배를 만든다고 하지만, Ultralytics 문서와 소형 객체 가이드는 "과한 축소는 소형 객체를 지운다"고 경고.
- 우리 적용: 8 px 객체는 stride-8 P3에서 이미 1셀. 축소 하한을 0.7로 묶고 확대는 크게 — `scale=(0.7, 1.6)`(튜플). 이는 "실서식 스캔 배율 차이(A4 200–300 dpi)"를 덮으면서 소형 객체 소실을 막는다. `multi_scale`은 batch 4에서 메모리 피크가 흔들려 OOM 위험, 1600에서는 끈다.

---

## 3. 외관·질감 증강

### ImageNet-trained CNNs are biased towards texture; increasing shape bias improves accuracy and robustness — Geirhos et al. arXiv:1811.12231 (ICLR 2019)
AdaIN 스타일 전이로 만든 Stylized-ImageNet(SIN)으로 학습하면 ResNet-50의 shape bias가 22%→81%. **검출 전이**: Faster R-CNN VOC mAP50 IN 70.7 / SIN 70.6 / SIN+IN 74.0 / SIN+IN→IN 미세조정 75.1(+4.4). 노이즈·대비·위상잡음 등 미학습 왜곡에 사람 수준 견고성.
- 우리 적용: 우리 목표(□·comb·밑줄·셀)는 원래 **형태 정의 객체**이고 배경은 이진이라 질감 단서 자체가 빈약. 이미 폰트 스왑·스캔 열화로 SIN과 같은 효과(질감 무관 학습)를 얻었고 그 결과가 99.9. 스타일 전이 추가는 기대 이득 0에 가깝다. 남은 형태 변동은 **선 두께·박스 크기 비율·간격**이며 이는 생성기(`2_spec/variation.json`)에서 넓혀야 한다(주제 A/B 범위).

### Domain Randomization and Pyramid Consistency: Simulation-to-Real Generalization without Accessing Target Domain Data — Yue et al. arXiv:1909.00889 (ICCV 2019)
합성 이미지를 K개의 실세계 보조 스타일로 무작위 변환(도메인 무작위화)하고, 스타일 간·피라미드 스케일 간 예측 일관성 손실을 건다. GTA5→Cityscapes FCN8s-VGG16 mIoU: baseline 29.81 → DR 34.64 → +PCD 35.47 → +PCI 36.11. **K=15에서 포화**.
- 우리 적용: "스타일 15종에서 포화"는 우리 픽셀 열화 축(복사·스캔·폰트)이 이미 충분하다는 것과 부합. 도입할 만한 것은 **피라미드(스케일) 일관성**의 저비용 대체 — 같은 페이지를 두 배율로 넣어 예측 일치를 강제하는 것인데 Ultralytics 표준 loop 밖이므로 보류. 대신 `scale` 확대 폭으로 스케일 불변성을 데이터 쪽에서 강제.

### 색상·그레이·블러·노이즈 (Ultralytics `hsv_*`, `bgr`, 오프라인 열화)
Ultralytics 기본 `hsv_h=0.015, hsv_s=0.7, hsv_v=0.4`. 이진/회색조 문서에서 hue·saturation 변동은 **수학적으로 no-op** (채도 0 픽셀은 변화 없음) 이면서 연산 비용만 든다. `hsv_v`는 종이 밝기·잉크 농도 차이를 흉내내므로 유효. 블러·노이즈·JPEG는 Ultralytics에 없고 우리 오프라인 파이프라인이 담당(이미 일반화 확인).
- 우리 적용: `hsv_h=0.0, hsv_s=0.0, hsv_v=0.3`. 실서식이 컬러 인쇄(회사 로고·색 배경)라면 `hsv_s`를 0.2 정도만 남긴다.

---

## 4. Ultralytics 하이퍼 정리 (기본값 → 우리 값, 근거)

| 하이퍼 | 기본 | 권고 | 근거 |
|---|---|---|---|
| `imgsz` | 640 | 1600 (유지) | FFDNet: 해상도가 20점, □가 가장 민감 |
| `mosaic` | 1.0 | 0.5 | YOLOv4 BN 효과 vs WeLayout/Select-Mosaic 절단 문제 절충 |
| `close_mosaic` | 10 | 총 epoch의 30% | ICDAR'23 팀 150/20; 우리 epoch가 짧으니 비율로 |
| `scale` | 0.5 | (0.7, 1.6) | LSJ 확대 이득 + 소형 객체 축소 소실 방지 |
| `translate` | 0.1 | 0.15 | Zoph 정책의 TranslateX/Y |
| `degrees` | 0 | 2 | Zoph "Rotate 최다 사용"; 외접박스 팽창 때문에 상한 2° |
| `shear` | 0 | 1 | Zoph ShearY |
| `perspective` | 0 | 0.0002 | 스캔·촬영 원근; 0.0005 이상은 소형 박스 왜곡 |
| `fliplr` | 0.5 | 0.0 | WeLayout 제거; 거울상 서식·글자 없음 |
| `flipud` | 0 | 0 | 동일 |
| `hsv_h/s/v` | .015/.7/.4 | 0/0/0.3 | 회색조에 hue·sat은 no-op |
| `mixup` | 0 | 0 | 두 페이지 반투명 합성은 밑줄·셀 경계를 이중선으로 만들어 GT와 충돌 |
| `cutmix` | 0 | 0 | mosaic 절단과 같은 문제 |
| `copy_paste` | 0 | 0 (하이퍼로 불가) | 폴리곤 필요 → 7_augment에서 골격 수준 구현 |
| `erasing` | 0.4 | 무관 | 분류 전용 — 검출엔 적용 안 됨(문서상 명시) |
| `auto_augment` | randaugment | 무관 | 분류 전용 |
| `multi_scale` | 0 | 0 | batch 4·1600에서 메모리 불안정 |
| `label_smoothing` | 0 | 무관 | 검출 loss에 미연결(issues #2164, #19228, #6059) |
| `dropout` | 0 | 무관 | 분류 헤드 전용 |

---

## 5. 암기 억제 정규화 (합성→실 전이)

### 실도메인 프록시로 조기 종료 — Ultralytics `val`/`patience`/`best.pt`
Ultralytics는 `best.pt`를 val fitness(0.1·mAP50+0.9·mAP50-95)로 고르고 `patience`도 같은 지표를 본다. 우리 val이 합성이면 **best.pt는 정의상 합성 최적점**이며, 실서식 recall이 epoch 1에서 꺾이는 걸 잡을 수 없다. 미세조정 가이드(docs.ultralytics.com/guides/finetuning-guide)는 소형 val에서 `patience=10–20`, epoch 20–50, warmup ≈1 epoch를 권한다.
- 우리 적용: `data.yaml`의 `val:`을 **실서식 홀드아웃(4_replica/render 라벨)** 으로 교체. 실서식 수가 적어 지표가 흔들리면 합성 홀드아웃과 1:1 혼합. `patience=5`, `epochs=30`, `warmup_epochs=1`, `save_period=1`(에폭별 실서식 recall 곡선을 `8_train/score.py`로 그림). 이것이 단독으로 가장 확실한 조치다.

### 백본 동결 vs 전체 미세조정, 백본 LR 하향 — Ultralytics finetuning guide; "Object Detection Using Deep CNNs Trained on Synthetic Images" (arXiv:1706.06782)
가이드: 데이터 적음+유사 도메인 `freeze=10`(백본), 아주 적음 `freeze=23`(헤드만), 도메인 멀면 `freeze=None`; 불안정하면 `optimizer=AdamW, lr0=0.001`; 2단계(동결→해제 후 `lr0=0.001`). 1706.06782는 합성→실 미세조정에서 하위 층을 동결 대신 **LR 1/10**으로 두는 방식을 채택. 별도 관찰(검색 결과의 합성→실 실험): 백본을 풀면 train은 좋아지되 val은 정체, 동결하면 val이 꾸준히 오름. Zoph 2019: 강한 증강 위에 DropBlock/Mixup 등 정규화를 겹쳐도 이득 없음.
- 우리 적용: FFDNet-L은 **같은 문서 도메인의 480k 페이지**로 학습된 백본이므로 "유사 도메인·소량 데이터" 칸에 해당 → `freeze=10`으로 백본 고정, neck+head만 학습. 전체 미세조정이 꼭 필요하면 2단계로 `lr0=0.001`(AdamW). 참고로 Ultralytics는 `weight_decay`를 `batch×accumulate/nbs`로 스케일하므로 batch 4라도 실효 감쇠는 기본과 동일 — 손댈 필요 없음. EMA(decay 0.9999, tau 2000 step)는 기본 활성이라 이미 쓰고 있다; 62k/4=15.5k step/epoch이므로 epoch 1 시점에 EMA는 이미 충분히 평활화되어 "epoch 1 최고"는 EMA 미성숙 탓이 아니다.

### 라벨 스무딩·드롭아웃
YOLOv4 ablation에서 class label smoothing은 BoF 조합의 일부였지만 단독 기여는 작다. Ultralytics 검출 loss에는 `label_smoothing`이 연결돼 있지 않아 값을 줘도 무효, `dropout`은 분류 헤드 전용.
- 우리 적용: 둘 다 사용 불가/불필요. 정규화 예산은 증강(1–2절)과 조기 종료·동결(이 절)에 집중.

---

## 6. 권고 학습 설정

```yaml
# 8_train/forms_v3.yaml 참고용 — 실서식 val + 동결 미세조정 + 문서용 증강
model: weights/FFDNet-L.pt
data: 8_train/forms_realval.yaml   # val: 4_replica/render (실서식), train: 5_dataset/train_v2 + 7_augment/pool
imgsz: 1600
batch: 4
epochs: 30
patience: 5
save_period: 1
freeze: 10                 # 백본 고정; 2단계로 풀 땐 freeze 없이 lr0 0.001
optimizer: AdamW
lr0: 0.001
lrf: 0.05
warmup_epochs: 1
cos_lr: true
# 기하·구성
mosaic: 0.5
close_mosaic: 9            # 30 epoch의 30%
scale: [0.7, 1.6]
translate: 0.15
degrees: 2
shear: 1
perspective: 0.0002
fliplr: 0.0
flipud: 0.0
mixup: 0.0
cutmix: 0.0
copy_paste: 0.0            # 폴리곤 없음 → 7_augment 골격 copy-paste로 대체
# 외관
hsv_h: 0.0
hsv_s: 0.0
hsv_v: 0.3
```

CLI 동치: `yolo detect train model=weights/FFDNet-L.pt data=8_train/forms_realval.yaml imgsz=1600 batch=4 epochs=30 patience=5 save_period=1 freeze=10 optimizer=AdamW lr0=0.001 lrf=0.05 warmup_epochs=1 cos_lr=True mosaic=0.5 close_mosaic=9 scale=0.7,1.6 translate=0.15 degrees=2 shear=1 perspective=0.0002 fliplr=0 hsv_h=0 hsv_s=0 hsv_v=0.3`

파이프라인 보강(하이퍼 밖): (1) `7_augment`에 골격 수준 copy-paste(signature·photo·□군, IoA<0.3, 블렌딩 없음) (2) 희소 부품 포함 골격 오버샘플링 ×2–3 (3) 에폭별 실서식 recall 곡선을 PLAN.md 결과표에 기록.

---

## 7. 우선순위 Top-8

1. **val을 실서식 홀드아웃으로, patience=5, save_period=1** — best.pt 선택 기준을 바꾸지 않으면 다른 모든 것이 합성 지표로 평가된다. (Ultralytics finetuning guide; 우리 "epoch 1 피크" 관찰)
2. **`freeze=10` + AdamW `lr0=0.001`** — 문서 도메인 480k로 학습된 FFDNet 백본을 보존, neck/head만 적응. (Ultralytics finetuning guide; arXiv:1706.06782의 하위층 LR 1/10 관행)
3. **`fliplr=0`, `hsv_h=hsv_s=0`** — 문서에서 무의미·유해한 기본값 제거, 무료. (WeLayout arXiv:2305.06553; 회색조 no-op)
4. **`scale=(0.7,1.6)` 넓은 확대·제한된 축소** — LSJ의 데이터 효율 이득을 소형 객체 소실 없이. (Ghiasi arXiv:2012.07177; Ultralytics 소형 객체 가이드)
5. **골격 수준 copy-paste + 희소 부품 오버샘플링(7_augment)** — 폴리곤 없는 검출에서 Ultralytics `copy_paste`의 대체. 10% 데이터 +10 AP, 소형 +7% 상대의 근거. (Ghiasi 2012.07177; Kisantal 1902.07296)
6. **`degrees=2, shear=1, translate=0.15, perspective=0.0002`** — 학습된 검출 정책의 핵심 연산(Rotate·Shear·Translate)을 소형 박스 팽창 한도 내에서. (Zoph arXiv:1906.11172)
7. **`mosaic=0.5` + `close_mosaic`=30%** — batch 4의 BN 안정성은 살리고 comb/셀 절단·과축소는 줄임. (YOLOv4 arXiv:2004.10934; Select-Mosaic arXiv:2406.05412; ICDAR'23 arXiv:2305.14962)
8. **스타일 무작위화·RandAugment·label smoothing·dropout은 채택하지 않음** — 질감 축은 이미 포화(99.9), 후자 둘은 Ultralytics 검출에 미연결. (Geirhos arXiv:1811.12231; Yue arXiv:1909.00889 K=15 포화; Ultralytics issues #2164/#19228)

## 출처
- https://arxiv.org/abs/1906.11172 · https://arxiv.org/abs/2012.07177 · https://arxiv.org/abs/1902.07296 · https://arxiv.org/abs/2004.10934 · https://arxiv.org/abs/2406.05412
- https://arxiv.org/abs/1811.12231 · https://arxiv.org/abs/1909.00889
- https://arxiv.org/abs/2509.16506 (CommonForms) · https://arxiv.org/abs/2410.12628 + https://github.com/opendatalab/DocLayout-YOLO/blob/main/assets/script.sh · https://arxiv.org/abs/2305.06553 (WeLayout) · https://arxiv.org/abs/2305.14962
- https://docs.ultralytics.com/usage/cfg/ · https://docs.ultralytics.com/guides/yolo-data-augmentation/ · https://docs.ultralytics.com/guides/finetuning-guide/ · https://docs.ultralytics.com/guides/model-training-tips/
- https://github.com/ultralytics/ultralytics/issues/2164 · /issues/19228 · /issues/6590 · /issues/18073
