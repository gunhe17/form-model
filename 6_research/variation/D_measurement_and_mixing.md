# 주제 D — 다양성·격차 측정, 실데이터 혼합, 소규모 평가셋 안정성

작성일 2026-09-11. 대상: 합성 2만 장 학습 YOLO 검출기, 합성 홀드아웃 recall 99.9 / 실서식 44쪽(972 박스) recall 90.4, mAP50-95 0.91→0.57, 저신뢰(<0.5) 예측 1.4%→23.9%, 실서식 recall이 epoch 1에 정점 후 하락, 미검출 93개 중 16개가 한 쪽에 집중. 미전사 실서식 105쪽 + OCR 캐시 보유.

핵심 진단을 먼저 적으면: **(a)** 우리 증상(합성은 계속 오르고 실은 1 epoch에 정점)은 문헌에서 "합성 검증 지표는 실 성능의 예측자가 못 된다"로 반복 보고된 전형적 sim-to-real 과적합이고, **(b)** 44쪽·972박스는 페이지 군집 때문에 유효 표본이 절반 이하로 줄어 ±3pt 안쪽의 변화는 판별 불가이며, **(c)** 실 데이터 5–20%를 섬으로 섞거나 합성 사전학습 후 미세조정하는 것이 가장 재현성 있게 보고된 처방이다.

---

## 1. 데이터셋 다양성·커버리지·격차 측정

### The Vendi Score: A Diversity Evaluation Metric for Machine Learning
Friedman & Dieng, arXiv:2210.02410 (TMLR 2023).
표본 집합 X에 대해 사용자가 정한 유사도 커널 k로 n×n 유사도 행렬 K를 만들고, K/n의 고유값 λ_i 의 섀넌 엔트로피를 지수화한 값 exp(−Σλ_i log λ_i)가 Vendi 점수다. "유효 종(species) 수"로 읽히며(모두 동일하면 1, 모두 직교면 n), 참조 분포·라벨이 필요 없다. 라벨 기준으로 모든 모드를 덮은 GAN조차 원 데이터보다 Vendi가 낮음을 보여 "클래스 커버리지 ≠ 다양성"을 실증했다.
핵심 수치: 값의 범위 [1, n], 참조셋 불필요, O(n³)이나 n≈수천이면 수 초.
**우리 적용:** 학습된 YOLO backbone(예: neck 이전 마지막 stage)에서 GT 박스별 crop 임베딩을 뽑아, (i) 합성 20k 중 무작위 2,000 박스, (ii) 실 972 박스, (iii) 두 집합을 같은 크기로 맞춰 각각 Vendi를 계산한다. 코사인 커널 사용. 클래스별(marker·comb·cell…)로도 계산해 "합성 Vendi ≪ 실 Vendi"인 클래스가 어휘·외형 변이를 넓혀야 하는 클래스다. 페이지 단위로는 OCR 캐시 텍스트의 TF-IDF 커널로 어휘 Vendi를 따로 계산하면 "외형은 다양하나 어휘가 좁다"를 분리해 볼 수 있다.

### Assessing Generative Models via Precision and Recall
Sajjadi et al., arXiv:1806.00035 (NeurIPS 2018).
분포 간 발산을 "품질(precision)"과 "커버리지(recall)"로 분해하는 PRD 곡선을 제안. 두 분포를 같은 특징 공간에서 k-means 군집화한 뒤 히스토그램 비교로 계산한다. 단일 스칼라(FID)가 숨기던 "모드 붕괴 vs 품질 저하"를 구분한다.
**우리 적용:** 실 972 박스 임베딩을 P, 합성 표본을 Q로 두면 recall(Q가 P를 얼마나 덮나)이 우리 문제의 정의 그 자체다. 다만 아래 두 후속 논문이 더 안정적이므로 이 논문은 개념 참조용으로만.

### Improved Precision and Recall Metric for Assessing Generative Models
Kynkäänniemi et al., arXiv:1904.06991 (NeurIPS 2019).
k-NN(k=3) 반경으로 각 분포의 매니폴드를 비모수적으로 근사하고, 생성 표본이 실 매니폴드 안에 들어오는 비율(precision), 실 표본이 생성 매니폴드 안에 들어오는 비율(recall)을 계산. StyleGAN 절단(truncation) 트릭에서 FID가 못 잡는 품질·다양성 교환을 분리해 보였다.
**우리 적용:** "실 박스가 합성 매니폴드 안에 있는가" = recall_{syn→real}. 이 값이 클래스별로 낮으면 그 클래스가 합성 그래머로 덮이지 않은 것. 미검출 박스 93개만 따로 넣어 "매니폴드 밖 비율"을 재면, 미검출이 커버리지 부족인지(밖) 판별 실패인지(안) 갈린다.

### Reliable Fidelity and Diversity Metrics for Generative Models
Naeem et al., arXiv:2002.09797 (ICML 2020).
위 P&R이 (a) 동일 분포도 1을 못 내고, (b) 이상치에 취약함을 보이고, density(실 k-NN 구 안에 생성 표본이 겹치는 개수 평균, 1 초과 가능)와 coverage(실 표본 중 자기 k-NN 구 안에 생성 표본이 하나라도 있는 비율)를 제안. k=5 권장, 실 표본 수 ~1만이면 안정. 공개 코드 `clovaai/generative-evaluation-prdc`.
**우리 적용:** 실무적으로 **이걸 쓴다.** 실 972 박스를 real, 합성 박스 표본을 fake로 두고 `compute_prdc(real, fake, nearest_k=5)`. coverage가 우리 "합성이 실을 덮는 비율"이고 이상치(한 쪽에 몰린 특이 박스)에 덜 흔들린다. 페이지별 coverage를 내면 "미검출 16개 페이지"가 실제로 저커버 페이지인지 확인된다. density ≫ 1이면 합성이 실의 좁은 영역에만 몰린(모드 과밀) 신호.

### Beyond Scale: The Diversity Coefficient as a Data Quality Metric for Variability in Natural Language Data
Miranda et al., arXiv:2306.13840 (ICLR 2024 DMLR 워크숍).
데이터 배치들을 Task2Vec(고정 네트워크 마지막 층 미세조정 후 Fisher 정보 대각)로 임베딩하고 배치 간 기대 거리를 "diversity coefficient"로 정의. 가우시안 합성 벤치마크에서 실제 다양성과 상관을 확인했다.
**우리 적용:** 구현 비용이 크고 LLM 사전학습 맥락. 우리에겐 Vendi/coverage로 충분하므로 **생략** 권고. 단 "배치 단위 거리" 발상은 페이지 단위 Vendi로 대체 가능.

### A Non-Parametric Test to Detect Data-Copying in Generative Models
Meehan, Chaudhuri & Dasgupta, arXiv:2004.05675 (AISTATS 2020).
학습셋·별도 실 표본·생성 표본의 3-표본 검정으로, 생성 표본이 학습 표본에 "지나치게 가까운지"(data-copying)를 Mann-Whitney U로 판정. 특징공간 k-NN 거리 비교라 구현이 쉽다.
**우리 적용:** 방향을 뒤집어 **신규성(novelty) 거리**로 쓴다. 실 박스마다 합성 20k 박스 임베딩까지의 최근접 거리 d_real→syn 분포를, 합성 홀드아웃 박스의 d_syn→syn 분포와 비교. 두 분포가 갈라지는 정도(예: AUROC)가 곧 "생김새 격차" 게이지. 미검출 박스의 d가 검출 박스의 d보다 유의하게 크면 격차가 원인.

### 속성별 커버리지 격자(per-attribute coverage grid)
논문이 아니라 관행. 우리는 `2_spec/variation.json`에 축이 정의돼 있으니, 실 44쪽을 같은 축(폰트 크기 bin, 셀 밀도, 열 수, 언더라인 유무, 사진란 유무…)으로 수동/OCR 태깅하고 합성 20k의 축별 히스토그램과 겹치는 칸/빈 칸을 표로 만든다. Vendi·coverage가 "얼마나"를, 격자가 "어디가"를 답한다.

---

## 2. 합성 과적합·기억 진단

### A Baseline for Detecting Misclassified and Out-of-Distribution Examples in Neural Networks
Hendrycks & Gimpel, arXiv:1610.02136 (ICLR 2017).
max-softmax 확률이 오분류·OOD 표본에서 체계적으로 낮음을 보인 기준선. AUROC/AUPR로 in/out 분리도를 측정한다.
**우리 적용:** 우리가 이미 관찰한 "저신뢰 비율 1.4% vs 23.9%"가 정확히 이 신호다. 이를 **에폭별 곡선**으로 만들어라: 각 epoch 체크포인트에서 합성 홀드아웃과 실 44쪽의 예측 신뢰 히스토그램을 뽑고 AUROC(합성 vs 실 신뢰)를 계산. AUROC가 epoch에 따라 오르면 모델이 합성 특유 단서를 점점 더 "기억"하는 것.

### Energy-based Out-of-distribution Detection
Liu, Wang, Owens & Li, arXiv:2010.03759 (NeurIPS 2020).
softmax 확신 대신 로짓의 logsumexp 에너지 −T·log Σ exp(f_i/T)를 쓰면 OOD 분리가 좋아짐(CIFAR-10 벤치마크에서 FPR95를 softmax 대비 크게 낮춤). 확신도가 포화되는 문제를 피한다.
**우리 적용:** YOLO 클래스 로짓(sigmoid 이전)에 logsumexp를 적용해 박스별 에너지를 얻고, 위 max-conf와 같은 방식으로 합성/실 AUROC를 병기. 신뢰도가 0.99에 포화된 합성에서는 에너지가 더 민감하다.

### On Calibration of Modern Neural Networks
Guo et al., arXiv:1706.04599 (ICML 2017).
ECE(신뢰 bin별 |정확도−신뢰| 가중 평균) 정의, 현대 네트워크의 과신, temperature scaling 단일 파라미터로 대부분 교정 가능.
**우리 적용:** 검출기용 ECE는 "예측 박스가 IoU≥0.5로 GT와 매칭됐는가"를 정답으로 두고 신뢰 bin 10개로 계산. 합성 ECE≈0, 실 ECE가 크고 특히 **저신뢰 구간에서 정확도가 신뢰보다 높다면**(under-confidence) 임계값 0.5를 실서식에서 낮추는 것만으로 recall이 오른다. 반대로 고신뢰 구간에서 over-confidence면 임계값 문제가 아니라 표현 문제다. 실 44쪽에서 temperature 하나를 맞추는 건 과적합 위험이 거의 없다(파라미터 1개).

### Synthetic-to-Real Object Detection using YOLOv11 and Domain Randomization Strategies
arXiv:2509.15045 (2025).
합성 2,106장(양성 1,368 + 음성 738)만으로 YOLOv11 학습, 실 159장 평가. 합성 검증 mAP@50 0.98–0.99인데 실 테스트 0.877–0.952. 저자 결론: "합성 검증 지표는 일관되게 높았지만 실 성능의 예측자로는 부실했다." 수동 라벨 실 테스트셋으로 개발을 이끌었다.
**우리 적용:** 우리 0.999 vs 0.904와 같은 패턴. 모델 선택·early stopping 기준을 **합성 홀드아웃에서 실 검증셋으로 바꾸는 것**이 최우선. 실 149쪽을 train/val/test로 나누되 val은 체크포인트 선택에만 쓰고 test는 최종 한 번만 본다.

### Improving Object Detector Training on Synthetic Data by Starting With a Strong Baseline Methodology
Ruis et al., arXiv:2405.19822 (2024).
합성 학습 시 "사전학습에서 배운 유용 특징을 잊지 않으면서 합성에서 핵심 정보만 뽑기"가 관건. 강한 증강 + Transformer 백본, 다중 합성 환경으로 RarePlanes·DGTA-VisDrone SOTA 갱신. 별도 sim-to-real 기법 없이 기본기(다양한 합성 환경, 증강)로 격차를 좁혔다.
**우리 적용:** 우리 실 recall이 epoch 1에 정점이라는 건 COCO 사전학습 특징이 빠르게 덮여쓰이는(forgetting) 신호. 처방: 학습률 1/3~1/10, backbone 층별 낮은 LR 또는 초반 N epoch backbone freeze, 증강 강화(색·블러·JPEG·스캔 노이즈). 그리고 **가장 싼 실험**: 현재 epoch 1 가중치를 그대로 후보로 두고 실 val로 비교.

### Analysis of Training Object Detection Models with Synthetic Data
arXiv:2211.16066 (2022).
DIMO 데이터셋에서 실의 "정확한 합성 복제본"과 특정 속성만 무작위화한 부분집합을 비교해 어떤 변이가 도움이 되는지 분석. 결론: 타깃 분포에 맞춰 모델링해야 하는 축과 무작위화해야 하는 축이 다르다.
**우리 적용:** 우리 카드 그래머에서 축 하나씩(폰트·행 간격·선 두께·어휘) 변이를 켜고 끈 ablation을 소규모(2k 장)로 돌려 실 val 변화를 보면 "어느 축이 격차의 원인인지" 계량화된다.

---

## 3. 실·합성 혼합

### How much real data do we actually need: Analyzing object detection performance using synthetic and real data
Nowruzi et al., arXiv:1907.07061 (CVPR-W 2019).
SSD-MobileNet, car/person, 실(BDD·KITTI·NuScenes) + 합성(P4B·7D·CARLA). 실 데이터를 100/10/5/2.5%로 줄이며 (a) 실만, (b) 합성+실 혼합, (c) 합성 학습→실 미세조정을 비교. 결론: **실 10%만 미세조정해도 혼합보다 낫고**, 혼합도 합성 단독보다 확실히 낫다; 합성 두 종(P4B+KC) 혼합 + 실 10%로 person은 실 100% 성능을 넘었다. 실 데이터를 90% 제거하는 손실이 그 다음 5% 제거보다 작다(수익 체감의 반대: 마지막 조금이 크다). "사진 사실성보다 다양성이 중요."
**우리 적용:** 실 149쪽 중 100쪽 학습·49쪽 평가로 나눈다면(아래 5절 주의), 1차 처방은 **합성 20k 학습 가중치에서 실 100쪽으로 미세조정**. LR은 합성 학습의 1/10, 5–15 epoch, 실 val로 선택. 실 100쪽만으로는 클래스 불균형(signature·photo 희소)이 심하므로 미세조정 배치에 합성 20–30%를 리플레이로 섞어 forgetting을 막는다.

### Reducing the Amount of Real World Data for Object Detector Training with Synthetic Data
Burdorf, Plum & Hasenklever, arXiv:2202.00632 (2022).
Cityscapes+Synscapes/GANscapes. 합성 25,000 사전학습→실 2,727 미세조정 vs 같은 실을 섞은 혼합 학습을 5 시드로 비교: **유의차 없음**(Nowruzi와 상반). 1−mAP50 = 10^β N^γ 멱법칙으로 적합해 실 데이터 필요량을 최대 70% 절감 가능, **실 비율 5–20%가 절감 효율 최대**. 실에서 희소한 클래스를 합성으로 보강하면 그 클래스가 특히 좋아진다.
**우리 적용:** 두 논문을 합치면 "미세조정 vs 혼합"은 데이터마다 다르고 차이가 작다 → 둘 다 돌려 실 val로 고른다. 혼합 시 실 비율은 **에폭 단위 5–20%**: 실 100쪽을 매 epoch 반복 샘플링(oversample)해 합성 대비 1:10~1:5가 되게 한다(합성 20k 기준 실 2k~4k 장 등가 → 100쪽을 20~40회 반복 또는 합성을 4k로 줄임). 희소 클래스(signature·photo)는 합성에서 오버샘플.

### Cut, Paste and Learn: Surprisingly Easy Synthesis for Instance Detection
Dwibedi, Misra & Hebert, arXiv:1708.01642 (ICCV 2017).
패치 수준 사실성만 있으면 충분하고 경계 아티팩트를 blending 다양화로 무시시킨다. 실 데이터와 합치면 상대 +21%, 교차 도메인에서 **합성 + 실 10%가 실 100%를 능가**.
**우리 적용:** 우리 `7_augment/render_swap.py`가 하는 부품 교체 증강이 이 계열. 실 149쪽(미전사 105쪽 포함)의 **배경/여백 텍스처를 합성 카드 뒤에 깔거나**, OCR 캐시의 실 어휘를 합성 셀에 채우는 "실 텍스처 붙이기"가 라벨 없이 격차를 줄이는 가장 싼 수단.

### Training Deep Networks with Synthetic Data: Bridging the Reality Gap by Domain Randomization
Tremblay et al., arXiv:1804.06516 (CVPR-W 2018).
비사실적 무작위화(조명·텍스처·자세·distractor)로 KITTI 차량 검출; 합성만으로도 경쟁력 있고 **실 미세조정 후 실만 학습보다 우수**. 사실성보다 변이 폭이 중요함을 확인.
**우리 적용:** 우리 변이는 "좁은 외형·어휘"로 진단됨. 폰트 가족 수·자간·행 높이·선 두께·스캔 왜곡(기울기·모아레·JPEG)을 "비사실적으로 과하게" 넓히는 것이 사실성 높이기보다 우선.

### Frustratingly Simple Few-Shot Object Detection
Wang et al., arXiv:2003.06957 (ICML 2020).
기저 클래스로 전체 학습 후, 소수샷 단계에서 **특징 추출기를 고정하고 박스 예측기(마지막 층)만** 균형 잡힌 소표본으로 미세조정하는 TFA가 메타학습 기법들을 능가.
**우리 적용:** 실 100쪽은 few-shot 영역. 2가지 미세조정 변형을 비교: (A) backbone freeze + head만, (B) 전체 미세조정 LR 1/10. 44쪽 규모 실 데이터에서 (B)는 과적합·forgetting 위험이 커 (A)가 안전 기본값. 클래스별 박스 수를 균형화(희소 클래스는 반복)해 head를 학습한다.

### An Annotation Saved is an Annotation Earned: Using Fully Synthetic Training for Object Instance Detection
Hinterstoisser et al., arXiv:1902.09967 (2019).
3D 배경 모델 밀집 렌더 + 전경 완전 무작위화, **커리큘럼**(모든 전경을 모든 자세·조건에서 균등하게, 난이도 점증)으로 합성만으로 실 검출. 
**우리 적용:** "합성→실 커리큘럼"의 원형. 우리에겐 합성 epoch 초반 → 후반에 실 비율을 0→20%로 올리는 스케줄로 번역. 다만 Nowruzi/Burdorf 결과상 큰 이득은 기대치 않음. 우선순위 낮음.

### Improving Document Layout Analysis Using Synthetic Data Generation and Convolutional Models
Applied Sciences 2026 (doi 10.3390/app16063089; 본문 403으로 초록·요약만 확인).
문서 레이아웃 도메인에서 대규모 합성 사전학습 후 **실 83장 미세조정**으로 도메인 특화 성능 확보. 
**우리 적용:** 문서 도메인에서도 "합성 대량 + 실 수십~백 장"이 표준 처방임을 재확인. 우리 실 100쪽은 이 범위 안.

---

## 4. 소규모 평가셋의 안정성

### Accounting for Variance in Machine Learning Benchmarks
Bouthillier et al., arXiv:2103.03098 (MLSys 2021).
벤치마크 전 과정의 분산 원천(데이터 샘플링·초기화·하이퍼파라미터)을 모델링. 데이터 분할 분산이 시드 분산과 동급 이상으로 크며, 여러 분산 원천을 함께 무작위화한 다중 실행이 이상적 추정량에 51배 싼 비용으로 근접. 단일 시드·단일 분할 비교는 대부분 유의하지 않음.
**우리 적용:** 실 val 44쪽 결과를 시드 1개로 비교하지 말 것. 최소 3 시드 × 동일 분할, 결과는 평균±표준편차. "epoch 1이 정점"이라는 관측도 시드 3개에서 재현되는지 먼저 확인.

### Bootstrapping Clustered Data
Field & Welsh, JRSS-B 69(3):369–390, 2007.
군집(우리는 페이지) 데이터에서 개체 재표집은 분산을 과소추정; **군집 단위 재표집(cluster bootstrap)**이 표준 처방이며 군집 수가 적을 때의 한계도 분석.
**우리 적용:** 972박스가 아니라 **44쪽을 복원추출**한다. 스크립트 개요:
```
pages = {page_id: (n_gt, n_tp)}      # 페이지별 GT·TP
for b in range(10000):
    s = rng.choice(page_ids, size=44, replace=True)
    rec[b] = sum(tp[p] for p in s) / sum(gt[p] for p in s)   # 박스 가중 recall
    rec_pg[b] = mean(tp[p]/gt[p] for p in s)                  # 페이지 평균 recall
CI = percentile(rec, [2.5, 97.5])
```
두 모델 비교는 **짝지은(paired) 페이지 부트스트랩**: 같은 페이지 표본으로 모델 A·B recall 차를 계산해 차이의 CI가 0을 포함하는지 본다. 페이지 평균 recall(rec_pg)을 병기하면 16개 미검출 페이지 한 장의 지배가 완화된다.

### 표본 크기 추정(문헌 공식 적용, 우리 수치)
이항 SE로 계산(recall 0.904, 972박스, 44쪽, 페이지당 22박스):
- iid 가정 SE 0.94pt → 95% CI ±1.8pt (과소추정).
- 페이지 내 상관 ICC 0.05/0.1/0.2 ⇒ 설계효과 2.1/3.1/5.2, **95% CI ±2.7 / ±3.3 / ±4.2pt**. 즉 현재 "90.4"는 실제로 87~94 사이 어디쯤이며 **+2pt 개선은 판별 불가**.
- 짝지은 비교에서 페이지별 recall 차의 SD를 0.08~0.15로 보면 +2pt를 80% 검정력으로 잡는 데 **125~440쪽** 필요. 비짝지음 두 표본이면 설계효과 2에서 팔당 ~300쪽.
- 따라서 149쪽 전부를 전사해도 +2pt는 짝지은 설계에서나 겨우 가능; 44쪽으로는 **±5pt급 변화만** 신뢰할 수 있다. 결과 표에는 항상 CI를 붙이고, 페이지 평균 recall과 "최악 5쪽 recall"을 보조 지표로 둔다.

### 데이터 누수 주의(anchor 분할)
같은 사업안내 PDF에서 나온 페이지들은 서식 템플릿을 공유한다. 실 149쪽을 100/49로 나눌 때 **페이지 단위가 아니라 원천 문서(0_source PDF) 단위로** 나눠야 한다. 그렇지 않으면 미세조정 후 실 val 상승의 상당분이 템플릿 기억이다. 미세조정 이후엔 "미세조정에 쓴 문서와 다른 문서"에서만 recall을 보고한다.

---

## 우선순위 상위 8개 실행안

1. **모델 선택 기준을 실 val로 교체 + 페이지 단위 cluster bootstrap CI 부착** — 결과표의 모든 실서식 수치에 95% CI(±3pt 안팎)를 붙이고, epoch별 실 recall 곡선을 3시드로 재확인. [Field & Welsh 2007; Bouthillier 2103.03098; 2509.15045]
2. **실 149쪽을 원천 문서 단위로 100/49 분할(누수 차단)하고, 미전사 105쪽 전사** — 이것 없이는 아래 3·4가 평가 불가. [Bouthillier 2103.03098]
3. **합성 가중치 → 실 100쪽 미세조정, 두 변형(head-only vs 전체 LR 1/10) + 합성 20–30% 리플레이** — 문헌상 가장 큰 단일 이득. [Nowruzi 1907.07061; Wang 2003.06957; Burdorf 2202.00632]
4. **혼합 학습(실 비율 epoch당 5–20%로 oversample, 희소 클래스 합성 오버샘플)** 을 3과 짝지어 비교 — 어느 쪽이 나은지는 데이터 의존. [Burdorf 2202.00632; Dwibedi 1708.01642]
5. **에폭별 격차 게이지: 합성 vs 실 신뢰·에너지 AUROC, 검출 ECE, temperature scaling 후 임계값 재설정** — 임계값 하나로 회수 가능한 recall이 있는지 먼저 확인(비용 거의 0). [Hendrycks 1610.02136; Liu 2010.03759; Guo 1706.04599]
6. **backbone crop 임베딩으로 density/coverage(k=5)와 Vendi를 클래스별·페이지별 계산, 미검출 박스의 최근접 합성 거리 비교** — "어느 클래스·어느 축이 안 덮였나"를 수치화해 그래머 확장 우선순위 결정. [Naeem 2002.09797; Friedman & Dieng 2210.02410; Meehan 2004.05675]
7. **변이 폭 확대(폰트 가족·행높이·선두께·스캔 왜곡) + 실 배경/어휘 붙이기(라벨 불필요, 105쪽 활용)** — 사실성보다 변이. [Tremblay 1804.06516; Dwibedi 1708.01642; Ruis 2405.19822]
8. **변이 축 ablation(축 하나씩 on/off, 2k 장 소규모) → 실 val 변화** — 6에서 의심된 축을 인과적으로 확인. [2211.16066]

주의: 본 보고서의 표본 크기 수치는 표준 이항·설계효과 공식으로 우리 값을 대입한 계산이며 특정 논문 수치가 아니다. Applied Sciences 2026 논문은 본문 접근이 막혀 초록·2차 요약에 의존했다.
