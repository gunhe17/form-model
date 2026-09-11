# 조사 A — 도메인 랜덤화(DR)와 "변이 폭" 방법론: 합성 데이터 객체 검출 문헌 조사

작성일 2026-09-11. 대상: FFDNet-L(YOLO계) + HTML 합성 서식 20,000장, 합성 holdout recall 99.9 vs 실서식 90.4, 실서식 저신뢰(<0.5) 예측 17배, epoch 1 이후 합성 지표만 개선.

핵심 결론 한 줄: 문헌은 일관되게 (1) **텍스처/외형 변이 폭**과 (2) **방해물(distractor)/맥락 변이**가 실도메인 전이의 1·2 요인이고, (3) 합성 검증 점수는 실도메인 성능의 예측자가 못 되며, (4) 변이 폭은 "실도메인 검증이 개선되는 한 계속 넓힌다"(ADR/DORAEMON)가 정석이라고 말한다. 우리 진단("구조는 다양, 외형·어휘·맥락은 좁다")과 정확히 일치한다.

---

## 1. 기초·후속 연구

### 1.1 Domain Randomization for Transferring Deep Neural Networks from Simulation to the Real World
Tobin, Fong, Ray, Schneider, Zaremba, Abbeel — arXiv:1703.06907 (IROS 2017)

랜덤화 축: 방해물 수·형태(0~10개), 모든 물체의 위치·텍스처, 테이블·바닥·스카이박스·로봇 텍스처, 카메라 위치(10×5×10 cm 박스)·방향·FOV, 조명 수·위치·스펙큘러, 이미지 노이즈 종류·양. 텍스처는 **사실적 텍스처가 아닌** 세 종류 절차 텍스처(단색 RGB, 두 색 그라디언트, 두 색 체커)를 균등 샘플. "충분한 변이가 있으면 실세계는 모델에게 또 하나의 변이로 보인다." 핵심 수치: 실물 위치 오차 약 1.5 cm(방해물·부분 가림 조건에서도 ~1.0–1.1 cm), 실이미지 사전학습 없이 시뮬 RGB만으로 학습. "충분한 수의 텍스처가 있으면 실이미지 사전학습이 불필요"함을 보임.
- **우리 적용:** 부품(□, 콤보, 셀)의 선색·배경색·채움을 3~6개 이산값이 아니라 **연속 분포**(예: 선 gray ∈ U(0.05, 0.6), 배경 L* ∈ U(0.85, 1.0), 미세 그라디언트/체커 배경 확률 0.1)로 샘플. Tobin의 교훈은 "사실적일 필요는 없지만 **폭이 넓어야** 한다".

### 1.2 Training Deep Networks with Synthetic Data: Bridging the Reality Gap by Domain Randomization
Tremblay, Prakash, Acuna, Brophy, Jampani, Anil, To, Cameracci, Boochoon, Birchfield — arXiv:1804.06516 (CVPR-W 2018)

검출(KITTI 자동차)에 DR을 처음 본격 적용. 랜덤화 축: 관심 물체·배경 텍스처(**8K 텍스처 풀**, 36개 차 모델), 카메라 팬·틸트·롤·거리, 점광원 1~12개 + 밝기/대비, **비행 방해물**(기하 도형에 랜덤 텍스처), 배경 사진. 결과(AP@0.5, Faster R-CNN): 실KITTI 미세조정 후 DR 98.5 = VKITTI +1.6, 실데이터 단독 +2.1. COCO 초기화에서 DR 83.7 vs VKITTI 79.7. **절제 실험(기준 73.7)**: 조명 고정 → 67.6(−6.1), 텍스처 없음 → 69.0(−4.7), 텍스처 풀 8K→4K → 71.5(−2.2), 데이터 증강 제거 → 72.0(−1.7), 방해물 제거 → −1.1, 밝기/대비 증강만 제거 → 73.6(거의 무영향). 또한 사전학습 특징을 **동결하면 오히려 악화**(Hinterstoisser와 반대 결과) — 비사실적 이미지에서는 특징도 적응해야 함. 사진현실성은 "의도적으로 포기".
- **우리 적용:** 절제 순서가 곧 우선순위다. (1) "조명" 상당물 = **페이지 전역 톤**(스캔 감마·대비·배경 밝기·잉크 농도)을 페이지마다 연속 샘플, (2) "텍스처 풀 크기" 상당물 = 폰트·라벨 어휘·색 팔레트의 **가짓수**를 수 배로, (3) 방해물 = 필드 근처에 검출 대상이 아닌 도장·로고·워터마크·안내문·페이지 번호를 랜덤 배치.

### 1.3 Structured Domain Randomization: Bridging the Reality Gap by Context-Aware Synthetic Data
Prakash, Boochoon, Brophy, Acuna, Cameracci, State, Shapira, Birchfield — arXiv:1810.10093 (ICRA 2019)

DR은 물체를 균등 랜덤 배치해 **맥락을 없앤다**는 점을 문제 삼음. SDR은 3층 계층(시나리오 → 전역 파라미터(도로 곡률, 태양 방위/고도, 차선 수, 차량 최대 수…) → **컨텍스트 스플라인**(차선·보도·중앙선, 각각 랜덤 색·텍스처) → 스플라인 위 객체 배치)을 둬 "구조는 유지, 그 위의 모든 것은 랜덤". 74개 차 모델, 9개 기본 도색+명도·거칠기 변이. 결과(Faster R-CNN, KITTI easy/moderate/hard AP): VKITTI(21k) 70.3/53.6/39.9, Sim200k(200k) 68.0/52.6/42.1, **SDR(25k) 77.3/65.6/52.2**. 실 BDD100K(다른 도메인)보다도 높고, SDR+KITTI > KITTI 단독. 참고로 Mayer et al. "What makes good synthetic training data for optical flow"(2018)의 "realism is overrated"를 인용해 DR의 정당성으로 삼음.
- **우리 적용:** 우리 골격 문법(카드×문서 타입)이 바로 SDR의 "컨텍스트 스플라인"이다 — 구조는 이미 좋다. 부족한 것은 **스플라인 위 객체의 전역 파라미터**: 카드 간 간격, 표 열 폭 비율, 라벨 열 폭, 셀 높이, 여백을 문서 타입별 **연속 분포**로 샘플하고, 각 카드에 색·선굵기 변이를 독립 부여.

### 1.4 Solving Rubik's Cube with a Robot Hand (Automatic Domain Randomization, ADR)
OpenAI (Akkaya et al.) — arXiv:1910.07113 (2019)

수동 DR은 "시뮬 랜덤화 설계 ↔ 로봇 검증의 빡빡한 반복"이 필요했음을 인정하고, 이를 자동화. 알고리즘: 각 파라미터 λ_i를 [φ_i^L, φ_i^H] 균등분포로 샘플, 매 반복 한 차원을 **경계값에 고정(boundary sampling)**해 성능을 버퍼에 쌓고, 평균 성능 > t_H면 그 경계를 넓히고 < t_L이면 좁힘. 변이 폭은 **ADR entropy(nats/dim)**로 정량화. 비전 모델 랜덤화(Table 11): 개별·총 조명 강도, 스포트라이트 각, 조명 수·거리·높이, 재질 hue/saturation 반경, 전체 hue shift·saturation·contrast, 배경 텍스처, 카메라 위치·각도, tf.image hue/saturation/contrast 후처리. **비전 결과(Table 4, 실이미지 오차)**: Manual DR 5.19°/8.53 mm → ADR Large(1.420 npd) 5.09°/7.85 mm; Table 5(루빅스): 기준 7.81°/6.47 mm/15.92° → ADR Large(0.806 npd) 7.48°/6.24 mm/13.83°. "ADR 엔트로피 증가가 실이미지 오차 감소와 잘 상관"하며, **시뮬 오차는 오히려 증가**(더 어려운 합성 과제). 비전은 초기 랜덤화를 0에서 시작해 자동 확장.
- **우리 적용:** 생성기의 축마다 [lo, hi]를 두고, 실서식 검수셋 recall(또는 저신뢰 비율)이 임계 이상이면 폭을 늘리고 미만이면 줄이는 **ADR 루프**를 학습 스크립트 밖의 셸 루프로 구현 가능(축 하나 경계 고정 → 2k장 렌더 → 짧은 학습 → 실서식 평가). 최소 구현: 축별 폭을 배율 1.0→1.25→1.5로 늘리며 실서식 recall 추적.

### 1.5 DeceptionNet: Network-Driven Domain Randomization
Zakharov, Kehl, Ilic — arXiv:1904.02750 (ICCV 2019)

"눈먼 DR"을 적대적으로 유도. 미분 가능한 픽셀 수준 교란 모듈(배경, 왜곡, 노이즈, 조명)을 가진 deception 네트워크가 과제 네트워크에 **가장 파괴적인** 증강을 찾고, 과제 네트워크는 그것에 강건하게 학습(min-max). 타깃 도메인 데이터 없이 소스만 사용, MNIST 변형·Cropped LineMOD·Cityscapes에서 도메인 적응 기법과 동등.
- **우리 적용:** 완전한 적대 학습은 과함. 대신 **실패 유도 샘플링**: 현재 모델의 실서식 저신뢰 사례 분포(어떤 클래스·어떤 배경 톤·어떤 폰트)를 세고, 그 조합의 샘플링 가중치를 높이는 "hard-axis reweighting"으로 90%의 효과를 얻는다.

### 1.6 On Pre-Trained Image Features and Synthetic Images for Deep Learning
Hinterstoisser, Lepetit, Wohlhart, Konolige — arXiv:1710.10710 (2017)

랜덤화: 대량의 잡동사니 실배경 위에 OpenGL Phong 렌더, 배경 채널 스왑·플립·회전, 조명색 교란, 가우시안 노이즈, 물체 경계까지 가우시안 블러, 로그 스케일 샘플링. 핵심 발견: 특징 추출기를 실이미지 사전학습 가중치로 **동결**하면 합성만 학습해도 실데이터 대비 **최대 95%** 성능. 동결 안 하면 합성 학습이 "significantly worse", 특정 카메라(Asus Xtion)에선 완전 실패. 즉 **저수준 통계(센서 노이즈·블러)가 도메인 갭의 큰 부분**.
- **우리 적용:** 두 가지. (a) HTML 렌더 후 **후처리 파이프라인**(가우시안/모션 블러, JPEG 압축, 센서 노이즈, 약한 기울기, 이진화 흔적)은 필수 — 우리 저신뢰 17배의 상당 부분이 여기 있을 가능성. (b) 학습 초반 backbone 동결 + 후반 해제 실험은 Tremblay와 결과가 갈리므로 실서식 recall로 직접 판정.

### 1.7 Meta-Sim: Learning to Generate Synthetic Datasets
Kar, Prakash, Liu, Cameracci, Yuan, Rusiniak, Acuna, Torralba, Fidler — arXiv:1904.11621 (ICCV 2019)

확률 장면 문법의 **속성 분포**(위치·회전·색·개수)를 신경망이 조정해 실데이터 분포와의 거리(MMD)와 하류 과제 성능(메타 목적)을 최소화. 사람 손으로 정한 규칙 대신 분포를 학습. (본 조사에서 KITTI 수치 원문 확보 실패 — 수치 인용 생략.)
- **우리 적용:** 실서식 코퍼스(1_corpus)에서 **측정 가능한 통계**(셀 높이 분포, 선 굵기 분포, 라벨 글자 수, 필드 폭/높이 비, 페이지 내 필드 수)를 뽑아 variation.json의 사전 분포를 그 히스토그램에 **맞추는 것**이 Meta-Sim의 수동판. 분포 폭은 실데이터보다 넓게(SDR·Tobin), 중심은 실데이터에(Meta-Sim).

### 1.8 Kubric: A scalable dataset generator / BlenderProc
Greff et al. — arXiv:2203.03570 (CVPR 2022); Denninger et al. — arXiv:1911.01911 (2019)

절차적 생성기 인프라. 자산·조명·카메라·재질·배경을 모듈 랜덤화, 수천 머신 분산. 이들 자체는 sim2real 정량 증거보다 "**모든 축이 파라미터화되어 재현 가능**"한 설계 원칙을 제공. BlenderProc은 물리 배치·조명·재질 모듈을 조합.
- **우리 적용:** 우리 build_skeleton/render_skeleton 구조는 이미 이 형태. 추가할 것은 **모든 연속 파라미터를 시드에서 결정론적으로 뽑고 GT JSON에 기록**하여, 어떤 축이 실서식 실패와 상관되는지 사후 분석 가능하게 하는 것(Kubric의 메타데이터 원칙).

---

## 2. "어느 축이, 얼마나" — 절제·비교 증거

### 2.1 Object Detection Using Sim2Real Domain Randomization for Robotic Applications
Horváth, Erdős, Istenes, Horváth, Földi — arXiv:2208.04171 (IEEE T-RO 2022)

DR을 5요소로 정리(물체 수·자세·텍스처 / 배경·방해물 / 카메라 / 조명 / 후처리 노이즈·블러). 산업 부품 검출, 합성만 학습(zero-shot) mAP50 86.32%, 실 1장 추가(one-shot) 97.38%. **절제(원본 이미지 기준)**: 전체 86.3 → 텍스처 제거 63.5 → 후처리 제거 55.9 → 둘 다 제거 **10.8**. 합성 검증 mAP는 99.84로 포화 — 실갭(valid−test)이 89.0%p에서 16.7%p로 줄어든 것이 성과. 텍스처 적용 확률 0.8, 랜덤 단색 0.2.
- **우리 적용:** 이 논문의 "합성 valid 99.8 / 실 10.8"은 우리 "합성 99.9 / 실 90.4"의 극단형이다. 처방도 같다: **텍스처(=외형) 변이 + 후처리 노이즈**. 두 축을 동시에 넣어야 하며 하나만 넣으면 절반 효과.

### 2.2 Domain Randomization for Object Detection in Manufacturing Applications using Synthetic Data: A Comprehensive Study
Zhu, Henningsson, Li, Mårtensson, Hanson, Björkman, Maki — arXiv:2506.07539 (2025)

4개 산업 데이터셋(7.5k~18k 합성장)에서 5축 절제(mAP50): Robotics 96.4 → 후처리 제거 90.0, 방해물 제거 88.9, 래스터라이즈(비사실적 렌더) 89.6; U1 94.1 → 92.0 / 90.1 / 92.0. 텍스처: 금속처럼 재질이 고유한 물체는 **사실적 PBR 텍스처가 우세**, 무텍스처 검은 부품은 랜덤=사실적. 결론 순위: 렌더링 방법(path tracing) > 재질 > 후처리(−2~6%p) > 방해물.
- **우리 적용:** "물체 고유 재질" 논리를 서식에 옮기면 — **필드 자체의 외형은 실서식 통계에 가깝게**(선 굵기·□ 크기·콤보 칸 비율은 실측 분포), **필드 밖(배경·주변 텍스트·장식)은 랜덤 폭 넓게**. Eversberg(2.4)와 같은 이분법.

### 2.3 Benchmarking Domain Randomisation for Visual Sim-to-Real Transfer
Alghonaim, Johns — arXiv:2011.07112 (ICRA 2021)

자세 추정에서 DR 설계 선택 벤치마크. 발견: (1) **고품질 소량 > 저품질 대량**, (2) **방해물과 텍스처는 서로 다른 갭을 막으므로 둘 다 필요**.
- **우리 적용:** 20,000장을 더 늘리는 것보다 장당 변이 폭(축 수·범위)을 늘리는 쪽이 문헌 지지. 방해물(비대상 장식)과 텍스처(색·폰트·톤)를 **독립 축**으로.

### 2.4 Generating Images with Physics-Based Rendering for an Industrial Object Detection Task: Realism versus Domain Randomization
Eversberg, Lambrecht — Sensors 2021 (arXiv 미확인)

Faster R-CNN, 합성 5,000장, 실 테스트 AP[.5:.95]. 조명 HDRI 0.642 vs 백색 점광 0.633; **배경 COCO 랜덤 0.642 > 도메인 사진 0.612**; 물체 텍스처 사실 0.653 ≥ 랜덤 0.644 ≥ 회색 0.642; **랜덤 텍스처 큐브 방해물 추가 0.669 > 없음 0.653**. 결론: 물체 관련 축(조명·재질)은 사실성이 소폭 유리, **비물체 축(배경·방해물)은 랜덤이 우세**.
- **우리 적용:** 필드 주변 텍스트·배경·장식은 "그럴듯함"에 집착 말고 폭을 넓힌다. 라벨 어휘 90개는 좁다 — 실서식 라벨 사전 + 무작위 한국어 명사구·숫자·영문 혼합으로 수천 종.

### 2.5 Synthetic-to-Real Object Detection using YOLOv11 and Domain Randomization Strategies
Torquato Niño, Gardi — arXiv:2509.15045 (2025)

YOLO계 검출기 + 합성만. 증강 강도(색 지터·기하·mixup) 조합보다 **데이터셋 자체의 다양성 확장(시점·거리·음성 예제)**이 더 컸다(최고 mAP50 0.910). "합성 검증 0.98~0.99는 실성능의 **나쁜 예측자**".
- **우리 적용:** 우리와 같은 검출기 계열에서 같은 진단. Ultralytics 하이퍼파라미터 증강(hsv, scale, mosaic)만 올리는 것으로는 부족하고 **생성기 쪽 변이**가 필요. 음성 예제(필드 없는 페이지·표만 있는 페이지) 5~10% 추가.

### 2.6 How useful is photo-realistic rendering for visual learning?
Movshovitz-Attias, Kanade, Sheikh — arXiv:1603.08152 (ECCV-W 2016)

시점 추정에서 렌더 품질 3단계: 기본 < 복잡 재질+환경광 < **복잡 재질+랜덤 방향광(색·강도 변이)**. 저품질 렌더는 데이터를 늘리면 오히려 악화. PASCAL 단독 16° → +RenderCar 11° → 3종 결합 5.2°. 사실성이 도움 되는 반례 — 단, 여기서 "사실성"의 실체는 **조명 변이**였음에 주의.
- **우리 적용:** "저품질을 늘리면 악화"는 우리 epoch 1 이후 정체와 부합. 렌더 품질 축 = 폰트 힌팅/앤티에일리어싱 on/off, 서브픽셀, DPI(96~300) 변이.

### 2.7 연속 vs 이산 샘플링
직접 비교한 논문은 찾지 못했다. 간접 증거: Tremblay 텍스처 풀 8K→4K에서 −2.2 AP(가짓수 자체가 성능), ADR/DORAEMON은 모든 축을 **연속 균등분포의 경계 확장**으로 정의, Tobin은 색을 연속 RGB로 샘플. 이산 3~6값은 "풀 크기 3~6"에 해당하므로 Tremblay 기준 가장 취약한 설정이다.

---

## 3. 커리큘럼·적응형 랜덤화

- **ADR**(1.4): 성능이 좋으면 폭 확장. 비전 모델은 폭 0에서 시작해 자동 확장, 엔트로피 ↑ ⇒ 실오차 ↓, 시뮬 오차 ↑.
- **Active Domain Randomization** — Mehta, Diaz, Golemo, Pal, Paull, arXiv:1904.04762 (CoRL 2019): 기준 환경과 랜덤 환경의 롤아웃 차이가 큰(=정보량 많은) 파라미터 영역을 더 자주 샘플. 균등 DR은 분산 크고 최적이 아님.
- **DORAEMON: Domain Randomization via Entropy Maximization** — Tiboni, Klink, Peters, Tommasi, D'Eramo, Chalvatzaki, arXiv:2311.01885 (ICLR 2024): 현재 정책의 성공 확률이 임계 이상인 한 훈련 분포의 **엔트로피를 최대화**. 핵심 경고: **과도한 랜덤화는 보수적(과소적합) 정책**을 만든다 — 폭은 "성능 제약 하에서" 넓혀야 함. 균등 DR·ADR 모두 능가, 제로샷 실로봇 전이.
- **DeceptionNet**(1.5): 적대적 유도.
- 실무 규범: "실도메인 검증이 개선되는 한 비현실적이어도 계속 넓힌다"는 문장은 여러 서베이(예: 추천 시스템 시뮬레이터 서베이 arXiv:2112.11022)에도 명시.

**우리 적용(통합):** 실서식 검수셋을 **유일한 검증**으로 두고(합성 holdout은 회귀 확인용으로만), 축별 폭 스케줄을 "실서식 recall이 떨어지지 않는 한 1.25배씩 확장, 떨어지면 0.8배 축소"로 운영. DORAEMON의 경고에 따라 라벨 가독성·필드 최소 크기 등 **성공 제약**(lint 통과, 최소 8 px 선 굵기 등)을 하한으로 둔다.

---

## 4. 문서·UI·스크린샷 도메인의 DR

### 4.1 Document Domain Randomization for Deep Learning Document Layout Extraction
Ling, Chen, Möller, Isenberg, Isenberg, Sedlmair, Laramee, Shen, Wu, Giles — arXiv:2105.14931 (2021)

렌더된 가짜 논문 페이지만으로 실논문 레이아웃 분할 전이(9클래스). 랜덤화: 폰트(Times/Helvetica) 및 크기 8~18pt, 열 폭·간격·여백·위치, SciGen 무의미 텍스트, 그림·표·수식 개수와 위치, 캡션 거리·열 간격·패딩, 1/2단·초록 위치·섹션 계층. 결과(mAP): 학습 ACL+VIS → 테스트 ACL300 0.90 / VIS300 0.88; 학습 ACL만 → VIS300 0.84; VIS만 → ACL300 0.81. **스타일 불일치 −6~−9%p**, 두 스타일 혼합이 어느 단일 스타일보다 낫거나 동등. 샘플 15K→938장(6.25%)에서 −11%p, 50%에선 −2~3%p. 라벨 노이즈 10%에도 주요 클래스 >80%. 결론: "고충실 의미(semantics)는 불필요, **스타일 분포가 테스트를 덮으면** 전이".
- **우리 적용:** 가장 직접적인 선행. 우리는 3폰트·이산 테마 = 단일 스타일 상황. 실서식 코퍼스에서 관찰되는 폰트군(바탕·돋움·굴림·맑은고딕·HY계·나눔 등) **10종 이상**과 크기 7~14pt 연속, 자간·행간 연속(letter-spacing −0.05~0.1em, line-height 1.0~1.8)으로 "스타일 분포가 실서식을 덮게".

### 4.2 SynthTIGER: Synthetic Text Image GEneratoR
Yim, Kim, Cho, Park — arXiv:2107.09313 (ICDAR 2021)

문자 인식용이지만 **렌더 함수별 절제표(Table 5)**가 문서 도메인에서 유일하게 상세. 총 정확도 82.1 기준: 후처리(블러·노이즈·JPEG) 제거 **−5.2**(불규칙 벤치 −11.9), 텍스처 블렌딩 제거 −3.9, 변환(기울기·원근) −2.6, 여백 랜덤 −1.9, 텍스트 효과(외곽선·그림자) −1.5, 탄성 왜곡 −1.0, 곡선 −0.7, 중경(mid-ground) 잡음 텍스트 −0.7, 컬러맵 −0.2. 길이 분포 증강 p=0.5로 +2%.
- **우리 적용:** 순위 그대로 이식 — (1) 후처리 노이즈, (2) 배경 텍스처(종이 질감·스캔 얼룩 블렌딩), (3) 페이지 미세 기울기·원근(±1~2°, 축소 0.95~1.0), (4) 필드 주변 여백 랜덤, (5) 인쇄 효과(굵기·음영). "길이 분포"는 우리에겐 **라벨 글자 수·필드 폭 분포**를 실서식 히스토그램에 맞추기.

### 4.3 Augraphy: A Data Augmentation Library for Document Images
Groleau, Chee, Larson, Maini, Boarman — arXiv:2208.14558 (ICDAR 2023)

인쇄·스캔·팩스·복사기 오염·잉크 노화·손글씨 표식을 ink/paper/post 3단계 파이프라인으로 재현하는 라이브러리. 정량 개선 수치는 초록에 없음.
- **우리 적용:** 직접 쓸 수 있는 후처리 구현체. 렌더 PNG → Augraphy 파이프라인(BleedThrough, LowInkPeriodicLines, DirtyDrum, Folding, BadPhotoCopy, JPEG)을 확률 0.5~0.7로.

### 4.4 DocLayout-YOLO / DocSynth-300K
Zhao, Kang, Wang, He — arXiv:2410.12628 (2024)

M6Doc 요소 풀(74범주, 희귀 범주 증강)을 2D 빈패킹(Mesh-candidate BestFit)으로 재배치해 300K 합성 문서. **요소 다양성 + 레이아웃 다양성** 강조. 사전학습 효과: D4LA 68.6→69.8, DocLayNet 76.7→79.3(+2.6). 랜덤 배치 레이아웃은 이득 미미, 확산 기반(LACE)은 다양성 한계.
- **우리 적용:** "실 요소 풀 재조합"은 우리 카드 문법과 같은 철학. 추가할 점은 **실서식에서 잘라낸 비대상 요소**(도장, 로고, 안내문 블록, 표 머리)를 풀에 넣어 방해물·맥락 다양성 확장.

### 4.5 UI/스크린샷
- **GUI-Perturbed: Domain Randomization Reveals Systematic Brittleness in GUI Grounding Models** (Wang et al., arXiv:2604.14262, 2026): MHTML 아카이브를 시뮬레이터로 삼아 DOM 조작 후 Playwright 재렌더. 브라우저 **줌 70%만으로 유의한 성능 하락**, 관계 지시에서 27~56%p 붕괴; rank-8 LoRA 증강 미세조정은 오히려 악화. 
- **UIClip** (arXiv:2404.12500, 2024): CSS 속성에 색 스왑·폰트 크기 랜덤·텍스트 잡음·대비·배경색 지터를 최대 3개 균등 샘플해 순차 적용 후 스크린샷.
- **우리 적용:** HTML 생성기의 최저 비용 축 — **`zoom`/DPR(0.8~1.3)과 뷰포트 폭**을 페이지마다 바꾸면 절대 픽셀 크기 분포가 즉시 넓어진다. UIClip식 "CSS 지터 함수 풀에서 k개 뽑아 순차 적용"은 hwp_theme.py에 그대로 이식 가능.

### 4.6 UnrealText: Synthesizing Realistic Scene Text Images from the Unreal World (Long, Yao, 2020)
3D 엔진으로 조명·시점·가림을 사실적으로 렌더 + 환경 조명 랜덤화 모듈. 검출 F1 IC15 +2.6, IC13 +2.3, MLT +2.1(합성 사전학습 후 미세조정). 문서 정면 스캔에는 3D가 과하지만 "조명 랜덤화 모듈"은 스캔 그림자·명암 구배(vignette)로 대응 가능.

---

## 5. 우리 생성기에 추가할 변이 축 — 우선순위 Top 8

| 순위 | 축 | 구체 처방 | 근거 |
|---|---|---|---|
| 1 | **후처리·스캔 노이즈** | 가우시안/모션 블러 σ∈U(0,1.2px), JPEG q∈U(40,95), 가우시안·salt 노이즈, 페이지 기울기 ±1.5°, 이진화/감마 U(0.7,1.4), Augraphy 파이프라인 p=0.6 | 2208.04171(제거 시 86→56), SynthTIGER(−5.2), Hinterstoisser, Tremblay 조명 고정 −6.1 |
| 2 | **전역 톤·색 연속화** | 배경 L* U(0.85,1.0)+종이 질감, 선 gray U(0.05,0.6), 잉크 hue 소폭 ±10°, 대비 U(0.7,1.3) — 이산 3~6값 폐기 | Tobin(연속 RGB), Tremblay 텍스처 풀 8K→4K −2.2, ADR 엔트로피↔실오차 |
| 3 | **폰트 가짓수·크기·자간 연속** | 폰트 ≥10종(실서식 관찰군), 크기 7~14pt 연속, letter-spacing −0.05~0.1em, line-height 1.0~1.8, 굵기 400/700 혼합 | DDR 2105.14931(스타일 불일치 −6~9%p), SynthTIGER 텍스트 효과 |
| 4 | **방해물(비대상 요소)** | 도장·로고·워터마크·안내문·페이지번호·QR·손글씨 표식을 필드 근방에 0~6개 랜덤 배치, 필드와 부분 겹침 허용 | Tremblay(−1.1), Eversberg(0.653→0.669), Alghonaim(텍스처와 별개 갭), 2506.07539 |
| 5 | **레이아웃 연속 지터** | 카드 간격·여백·열 폭 비·셀 높이·라벨 열 폭을 문서 타입별 U/N 분포로, 필드 폭·높이 분포는 실서식 히스토그램에 정렬 | SDR 1810.10093(전역 파라미터), Meta-Sim, DDR |
| 6 | **라벨 어휘 폭** | 90어 → 실서식 라벨 사전 + 무작위 한국어 명사구·숫자·영문 혼합 수천 종, 글자 수 분포를 실서식에 맞춤 | SynthTIGER 길이 분포 +2%, DDR "의미 불필요·분포 중요" |
| 7 | **스케일·DPR·뷰포트** | CSS zoom/DPR U(0.8,1.3), 뷰포트 폭 ±15%, 렌더 DPI 96~300 → imgsz 1600 리사이즈 시 절대 크기 분포 확장 | GUI-Perturbed(줌 70%만으로 유의 하락), 2509.15045(거리 변이) |
| 8 | **음성·희소 페이지 + 적응 폭 스케줄** | 필드 없는 페이지 5~10%, 필드 1~3개 페이지 추가; 축별 폭을 실서식 recall 기준으로 ×1.25 확장/×0.8 축소하는 ADR식 루프, lint·최소 크기를 성공 제약으로 | 2509.15045(음성 예제), ADR 1910.07113, DORAEMON 2311.01885(과도 랜덤화 경고) |

운영 원칙 세 가지: (1) 합성 holdout은 회귀 검사용, **판정은 실서식만**(2208.04171·2509.15045). (2) 데이터 수 증가보다 장당 변이 폭 증가(Alghonaim; Movshovitz-Attias "저품질 대량은 악화"). (3) 필드 자체 외형은 실측 분포에 가깝게, 필드 밖은 넓게(Eversberg·2506.07539의 물체/비물체 이분법).

---

## 출처
- arXiv: 1703.06907, 1804.06516, 1810.10093, 1910.07113, 1904.02750, 1710.10710, 1904.11621, 1904.04762, 2311.01885, 2203.03570, 1911.01911, 2011.07112, 1603.08152, 2105.14931, 2107.09313, 2208.14558, 2410.12628, 2208.04171, 2506.07539, 2509.15045, 2509.16506, 2604.14262, 2404.12500, 2112.11022
- Eversberg & Lambrecht, Sensors 2021 (PMC8659618); Mayer et al. "What makes good synthetic training data for optical flow estimation?" 2018; Long & Yao "UnrealText" 2020; Chociej et al. ORRB 2019.
- 확인 못한 수치: Meta-Sim KITTI AP(원문 HTML 변환 실패), Augraphy 정량 개선.
