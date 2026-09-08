# 한국 행정서식 Fillable Field Detection — 문헌 조사 보고서

조사일 2026-09-08 · 웹검색 17회 + 개별 논문 fetch 8회 · 모든 URL은 curl로 HTTP 200 확인 완료.
표기: (A) = 초록/서치 스니펫 수준만 확인, (F) = 본문/초록 직접 fetch로 내용 검증.

---

## 1. VLM 파인튜닝 · dense grounding · 박스를 텍스트 토큰으로 뱉는 계열

**1. Qwen2.5-VL Technical Report** (2025, arXiv:2502.13923) (A)
https://arxiv.org/abs/2502.13923
Naive Dynamic Resolution ViT + Window Attention으로 native 해상도를 그대로 먹는다. 결정적으로 bbox/point를 **정규화하지 않은 절대 픽셀 좌표**로 표현하며, "모델이 스케일 정보를 내재적으로 학습하게 한다"고 명시.
왜 우리 문제와 관련 있나: 우리 베이스가 상속한 좌표 규약 그 자체. 절대좌표 = 해상도가 바뀌면 좌표 분포가 통째로 이동한다는 뜻이라, 학습/추론 해상도를 고정하지 않으면 25px 체크박스 localization이 무너지는 근본 원인이다.

**2. Qwen3-VL Technical Report** (2025-12, arXiv:2511.21631) (A)
https://arxiv.org/abs/2511.21631
7M PDF 파싱 데이터 + 합성 long-doc VQA로 문서 능력을 크게 키웠고, grounding은 COCO/Objects365/RefCOCO 계열 + 자동합성으로 구성. interleaved-MRoPE로 공간·시간 모델링의 스펙트럼 불균형을 수정했다고 주장.
왜 관련 있나: 우리 베이스 모델의 grounding 데이터 분포가 "자연영상 + RefCOCO 단일 객체"에 치우쳐 있음을 확인시켜 준다. 페이지당 수십~수백 박스를 뱉는 dense 서식 태스크는 사전학습 분포 밖 → SFT가 필수라는 근거.

**3. Florence-2: Advancing a Unified Representation for a Variety of Vision Tasks** (CVPR 2024, arXiv:2311.06242) (A)
https://arxiv.org/abs/2311.06242
좌표를 1,000 bin으로 양자화한 **location token**을 tokenizer vocab에 추가해 detection/grounding/segmentation을 하나의 seq2seq로 통합. FLD-5B(1.26억 이미지, 54억 어노테이션)로 학습.
왜 관련 있나: "박스 1개 = 4 토큰"이라 dense 출력에서 토큰 예산이 Qwen식 텍스트 숫자 대비 3~5배 절약된다. 페이지당 100+ 필드를 뱉어야 하는 우리에겐 시퀀스 길이가 곧 ghost tail 위험이므로 직접적인 대안 설계.

**4. PaliGemma: A versatile 3B VLM for transfer** (2024, arXiv:2407.07726) (A)
https://arxiv.org/abs/2407.07726
`<loc0000>`~`<loc1023>` 1024개 위치 토큰(정규화 좌표 binning) + `<seg000>`~`<seg127>` 마스크 토큰을 vocab에 추가. 40여 태스크로 transfer 성능을 검증한 3B급 베이스.
왜 관련 있나: 3~4B급에서 loc-token 방식이 실제로 transfer가 잘 된다는 레퍼런스. 우리가 Qwen3-VL 4B에 loc token을 추가(임베딩 확장)하는 변형을 고려할 때 가장 가까운 선례.

**5. KOSMOS-2.5: A Multimodal Literate Model** (2023, arXiv:2309.11419) (A)
https://arxiv.org/abs/2309.11419
텍스트 집약 이미지에 대해 (1) 공간좌표가 붙은 text block 생성, (2) markdown 구조 생성 두 태스크를 하나의 decoder-only로 처리.
왜 관련 있나: "문서에서 다수의 (bbox, 내용) 페어를 autoregressive로 뱉는" 우리 출력 형식의 원형. 라인 단위 수백 개 박스를 안정적으로 뱉는 프롬프트/포맷 설계 참고.

**6. Griffon: Spelling out All Object Locations at Any Granularity with LLMs** (ECCV 2024, arXiv:2311.14552) (A)
https://arxiv.org/abs/2311.14552
특수 토큰·전문가 모델·detection head 없이 순수 LVLM만으로 dense detection을 시도한 baseline. 데이터 포맷 통일 + end-to-end 학습.
왜 관련 있나: "CV 없이 VLM만으로 다객체 detection"이 우리 1안인데, 그 1안의 최초 정직한 baseline. 무엇이 필요한지(데이터 규모, 포맷 통일) 체크리스트로 쓸 수 있다.

**7. Griffon v2: High-Resolution Scaling and Visual-Language Co-Referring** (2024, arXiv:2403.09333) (A)
https://arxiv.org/abs/2403.09333
고해상도 스케일링을 도입해 REC/phrase grounding SOTA, detection·counting에서 전문가 모델을 능가한 최초의 LVLM이라 주장.
왜 관련 있나: 우리의 "3x zoom 없으면 작은 글리프를 못 잡는다"는 관찰의 정답지 중 하나 — 해상도 스케일링이 dense·소형 객체 성능을 지배한다는 실증.

**8. Griffon-G: Bridging Vision-Language and Vision-Centric Tasks** (2024, arXiv:2410.16163) (A)
https://arxiv.org/abs/2410.16163
REC(단일 객체)부터 dense detection까지 데이터를 통합 수집해 vision-centric과 VL 태스크를 동시에 잘 하도록 학습.
왜 관련 있나: LoRA SFT 시 "detection만 몰빵하면 일반 능력이 죽는다"는 문제를 데이터 믹싱으로 푸는 레시피. 우리 20k 합성 데이터에 섞을 anchor 데이터 비율 설계 참고.

**9. ChatRex: Taming Multimodal LLM for Joint Perception and Understanding** (2024, arXiv:2411.18363) (A)
https://arxiv.org/abs/2411.18363 · 코드 https://github.com/IDEA-Research/ChatRex
Qwen2-VL이 COCO recall 43.9%에 그친다는 진단에서 출발. LLM이 좌표를 **회귀하지 않고**, universal proposal network가 낸 박스들을 입력받아 **인덱스만 출력**하는 retrieval 방식으로 전환. dual-encoder + gate conv로 고/저해상도 토큰 융합.
왜 관련 있나: 우리 대안 아키텍처 "CV가 제안하고 VLM이 분류한다"의 정확한 레퍼런스 구현. recall은 proposal network가 책임지고(≥98% 달성 가능), 11-type 분류는 VLM이 책임지는 분업 구조 — 우리 목표치와 지표 분해가 그대로 맞아떨어진다.

**10. LMM-Det: Make Large Multimodal Models Excel in Object Detection** (ICCV 2025, arXiv:2507.18300) (A)
https://arxiv.org/abs/2507.18300 · 코드 https://github.com/360CVGroup/LMM-Det
detection head 없이 순수 LMM으로. 핵심은 **학습 데이터 분포 재조정 + 추론 프롬프트 재구성 + pseudo-label로 proposal-rich supervision**을 주어 recall을 끌어올린 것.
왜 관련 있나: "박스는 세는데 못 찍는다 / 다 못 찍는다"는 recall 병리를 아키텍처 변경 없이 데이터·프롬프트만으로 고친 사례. LoRA만 쓰는 우리 제약과 정확히 호환된다.

**11. Shikra: Unleashing Multimodal LLM's Referential Dialogue Magic** (2023, arXiv:2306.15195) (A)
https://arxiv.org/abs/2306.15195
좌표를 특수 vocab 없이 **자연어 숫자 그대로** 표현. 동일 REC 데이터로 bin token 방식과 비교했을 때 숫자 직접 표기가 더 좋았다고 보고.
왜 관련 있나: 좌표 포맷 논쟁의 반대편 근거. 단, "숫자 표기는 dense 예측 시 토큰 수가 늘어 계산 비용이 커진다"는 트레이드오프도 같은 맥락에서 지적되어, 우리처럼 박스가 많은 경우엔 결론이 뒤집힐 수 있음을 시사.

**12. GutenOCR: A Grounded Vision-Language Front-End for Documents** (2026-01, arXiv:2601.14490) (F)
https://arxiv.org/abs/2601.14490
Qwen2.5-VL-3B/7B를 파인튜닝해 line/paragraph 단위 bbox + localized reading + "where is x?" 질의를 통합. 비즈니스 문서·논문 + **합성 grounding 데이터**로 학습. 7B에서 grounded OCR 종합점수 0.40 → 0.82로 2배 이상 향상(10.5K holdout). 단, page linearization과 수식 문서에서는 트레이드오프 발생.
왜 관련 있나: 우리와 가장 조건이 비슷한 최근 연구 — 같은 베이스 계열, 같은 크기(3B), 문서 grounding, 합성 데이터. "베이스의 grounding이 약해도 SFT로 2배는 오른다"는 정량적 기대치와, "다른 능력은 일부 희생된다"는 경고를 동시에 준다.

**13. InternVL3: Advanced Training and Test-Time Recipes** (2025, arXiv:2504.10479) (A)
https://arxiv.org/abs/2504.10479
Native Multimodal Pre-Training으로 언어·비전을 단일 스테이지에서 동시 학습. grounding·OCR·문서·GUI를 학습 도메인에 포함.
왜 관련 있나: Qwen3-VL 4B가 막힐 경우의 동급 대체 베이스. grounding 데이터 구성이 문서·GUI 쪽으로 더 치우쳐 있어 서식 도메인 transfer가 유리할 가능성.

**14. mPLUG-DocOwl2: High-resolution Compressing for OCR-free Multi-page DU** (ACL 2025, arXiv:2409.03420) (A)
https://arxiv.org/abs/2409.03420
High-resolution DocCompressor로 고해상도 문서 1장을 324 토큰으로 압축, 시각 토큰 20% 미만으로 동급 성능 + first-token latency 50% 감소.
왜 관련 있나: 우리가 3x zoom을 쓰면 시각 토큰이 폭증한다. "고해상도는 유지하되 토큰은 압축"이라는 방향의 대표 사례 — 단, 압축은 소형 글리프 localization과 상충할 수 있어 반례로도 읽어야 함.

**15. VLM-R1: A Stable and Generalizable R1-style Large Vision-Language Model** (2025, arXiv:2504.07615) (A)
https://arxiv.org/abs/2504.07615 · 코드 https://github.com/om-ai-lab/VLM-R1
GRPO를 REC/OVD처럼 **결정론적 GT가 있는** 태스크에 적용. SFT 대비 out-of-domain 일반화가 우수하다고 보고.
왜 관련 있나: 우리 GT는 HTML에서 나오므로 완전 결정론적 = IoU/recall을 그대로 reward로 쓸 수 있다. SFT 후 2단계로 GRPO를 얹어 recall 98%·IoU 임계 통과율을 직접 최적화하는 경로가 열린다.

**16. Object Detection with Multimodal Large Vision-Language Models: An In-depth Review** (2025, arXiv:2508.19294) (A)
https://arxiv.org/abs/2508.19294
LVLM 기반 detection의 아키텍처·학습 패러다임·출력 형식(좌표 텍스트 vs 토큰 vs 인덱스)을 체계적으로 정리한 리뷰.
왜 관련 있나: 1안(VLM 직접) vs 2안(CV proposal + VLM 분류)의 장단을 비교할 때 인용 가능한 최신 서베이. 설계 문서의 배경 절을 통째로 채울 수 있다.

---

## 2. 서식 이해 · form field detection · CV 디텍터 baseline

**17. CommonForms: A Large, Diverse Dataset for Form Field Detection** (2025-09, arXiv:2509.16506) (F)
https://arxiv.org/abs/2509.16506 · 코드/모델 https://github.com/jbarrow/commonforms
Common Crawl 800만 PDF에서 fillable widget이 있는 것만 필터링해 **55k 문서 / 450k+ 페이지** 구축. 태스크를 순수 object detection으로 정식화, 타입은 Text Input / Choice Button / Signature 3종. FFDNet-Small/Large를 **모델당 $500 미만**으로 학습해 상용 PDF 리더를 상회. 어블레이션에서 **"고해상도 입력이 form field detection 품질에 결정적"**임을 확인. 1/3이 비영어, 14개 도메인 중 어느 것도 25%를 넘지 않음.
왜 관련 있나: **이 조사에서 가장 중요한 단일 논문.** 우리 문제와 입출력이 거의 동일하며, (a) GT가 공짜인 데이터 소스 아이디어(PDF AcroForm 위젯 = 무료 라벨)를 제공하고, (b) 사전학습 코퍼스로 바로 쓸 수 있고, (c) 고해상도가 지배 변수라는 우리 관찰을 독립적으로 검증한다. 우리 11-type은 이 3-type의 세분화로 볼 수 있어 계층적 라벨 매핑이 가능하다.

**18. AcroMELD: Recovering Interactive PDF Forms with Structure-Aware Graph Set Transformers** (2026-08, arXiv:2608.22338) (F)
https://arxiv.org/abs/2608.22338
39.4M 파라미터 디텍터. 고해상도 ViT + label-free PDF primitive를 결합하고, **896 쿼리(시각 제안 384 + 구조 시드 제안 384 + 학습형 recovery 쿼리 128)** + geometry-biased sparse neighborhood를 쓰는 4층 graph-set 레이어. same-field relation linking과 **localization-quality head**를 별도로 학습. 지표는 containment micro-F1 / IoU-0.5 F1 / COCO mAP. 내부 테스트 0.9344, 외부 holdout 0.8477(95% CI 0.8339–0.8605). "dense page는 수백 개 필드를 가질 수 있다"를 명시적 동기로 삼음.
왜 관련 있나: 우리와 동일한 dense-form 문제를 **set prediction(고정 쿼리 수)** 으로 푼 최신 사례. ghost tail이 구조적으로 불가능한 아키텍처이며, 쿼리 수 상한(896)·localization quality head·containment 지표 등 우리가 그대로 베낄 만한 설계 결정이 많다. 40M 파라미터로 이 정도가 나온다는 건 4B VLM의 비용 정당화를 다시 묻게 만든다.

**19. Unchecked and Overlooked: Addressing the Checkbox Blind Spot in LLMs with CheckboxQA** (2025, arXiv:2504.10419) (A)
https://arxiv.org/abs/2504.10419 · https://github.com/Snowflake-Labs/CheckboxQA · https://huggingface.co/datasets/mturski/CheckboxQA
DocumentCloud 공개 서브셋에서 약 90개 멀티페이지 문서를 수집해 체크박스 해석 능력을 평가(ANLS*). LVLM들이 checkable content 해석에 광범위하게 실패함을 보임.
왜 관련 있나: "체크박스는 VLM의 구조적 맹점"이라는 우리 가설의 독립적 근거. 체크박스만 별도 커리큘럼/가중치로 다뤄야 한다는 정당화이자, 타입 정확도 97% 목표에서 체크박스가 병목이 될 것이라는 예고.

**20. FUNSD / XFUND / RFUND** (2019 / 2022 / ACM MM 2024) (A)
FUNSD https://guillaumejaume.github.io/FUNSD/ · RFUND https://github.com/SCUT-DLVCLab/RFUND
FUNSD 199장(header/question/answer/other), XFUND 7개 언어 1,393장. RFUND는 FUNSD/XFUND의 라벨·링크 불일치를 재라벨링한 버전.
왜 관련 있나: **채워진** 서식의 엔티티 추출 벤치마크로, 우리의 **빈** 서식 필드 검출과는 태스크가 다르다는 점을 명확히 해야 한다. 우리 문제에 FUNSD를 쓰지 말아야 할 이유의 근거이자, 한/중/일 CJK 서식 레이아웃 통계 참고용. RFUND는 "인기 벤치마크의 GT가 실제로 얼마나 더러운가"의 교훈.

**21. A survey of recent approaches to form understanding in scanned documents** (AI Review 2024, Springer) (A)
https://link.springer.com/article/10.1007/s10462-024-11000-0
스캔 서식 이해 계열(레이아웃, KIE, 엔티티 링킹) 방법론 정리.
왜 관련 있나: 서식 도메인 전반의 용어·지표·데이터셋 지도. 우리 태스크가 기존 form understanding 문헌에서 왜 빈칸인지(대부분 "채워진 서식의 값 추출"이지 "빈 서식의 입력칸 검출"이 아님) 논거를 세울 때 유용.

**22. DocLayout-YOLO** (2024, arXiv:2410.12628) (A)
https://arxiv.org/abs/2410.12628 · https://github.com/opendatalab/DocLayout-YOLO
YOLO-v10 기반. **Mesh-candidate BestFit**(문서 합성을 2D bin packing으로 정식화)으로 DocSynth-300K를 만들어 사전학습 + Global-to-Local Controllable 모듈로 다양한 스케일 대응.
왜 관련 있나: 2안 아키텍처의 proposal 디텍터 1순위 후보이자, 3절 합성 데이터 전략의 대표 사례. "합성 사전학습 → 소량 실데이터 파인튜닝"이 우리 파이프라인과 동일.

**23. PP-DocLayout** (2025, arXiv:2503.17213) (A)
https://arxiv.org/abs/2503.17213
RT-DETR-L 기반 PP-DocLayout-L이 mAP@0.5 90.4%. 대규모 데이터 구축 가속을 목표로 한 통합 레이아웃 디텍터 패밀리(L/M/S).
왜 관련 있나: proposal 단계 후보 #2. 실시간·CPU 예산까지 커버하는 패밀리라 온프레미스 배포 제약이 있을 때 유리.

**24. RT-DocLayout: Real-Time End-to-End DLA with Reading Order in the Wild** (2026-06, arXiv:2606.23344) (A)
https://arxiv.org/abs/2606.23344
33M 파라미터 단일 아키텍처로 분류·검출·픽셀 세그멘테이션·**reading order 예측**을 통합(RT-DETR 확장).
왜 관련 있나: 우리 출력의 **박스 순서(deterministic output 요건)** 문제를 모델이 직접 배우게 하는 방법. reading order를 별도 헤드/보조 태스크로 두는 설계 참고.

**25. DocLayNet** (KDD 2022, arXiv:2206.01062) (A)
https://arxiv.org/abs/2206.01062
80,863장 수작업 라벨, 11개 클래스, 다양한 문서 출처(브로슈어·비즈니스 레터·기술문서 포함).
왜 관련 있나: 우연히도 클래스 수가 우리와 같은 11개이고, 관공서 문서에 가까운 비즈니스 레터/양식이 포함. 일반화 평가용 OOD 세트로 재활용 가능.

**26. LayoutLMv3** (ACM MM 2022, arXiv:2204.08387) (A)
https://arxiv.org/abs/2204.08387
MLM + MIM + word-patch alignment로 텍스트/이미지 마스킹 목적을 통일. CNN/Faster R-CNN 백본 제거.
왜 관련 있나: OCR 텍스트 + 좌표를 함께 쓰는 전통적 강자. 우리가 HWP/PDF에서 텍스트 레이어를 얻을 수 있는 경우 "이미지-only VLM"보다 저렴하게 필드 위치를 잡을 수 있는 baseline.

**27. SAHI: Slicing Aided Hyper Inference and Fine-tuning for Small Object Detection** (2022, arXiv:2202.06934) (A)
https://arxiv.org/abs/2202.06934
겹치는 타일로 잘라 추론 후 병합. 어떤 디텍터에도 무학습으로 얹을 수 있으며 AP +5~7%p, slicing-aided fine-tuning까지 하면 누적 +12.7~14.5%p.
왜 관련 있나: "25px 체크박스는 3x zoom 없이는 못 잡는다"에 대한 가장 저렴하고 검증된 해법. VLM에도 동일 원리(페이지를 2x2/3x3 타일로 나눠 각각 grounding → 좌표 역매핑 → NMS)를 적용할 수 있으며, 타일 경계 필드 처리를 위한 overlap 비율 근거도 여기서 가져온다.

**28. Signature detection 실무 자원: SignverOD / Tobacco-800 / YOLOv8 signature detector** (A)
https://datasetninja.com/signver-od · https://huggingface.co/tech4humans/yolov8s-signature-detector
SignverOD는 스캔 문서 2,576장 / 7,103 bbox / 4클래스(signature, initials, redaction, date). Tobacco-800 기반 YOLOv5/v8 서명 검출기 다수 공개.
왜 관련 있나: 우리 11-type 중 signature 클래스의 외부 데이터·사전학습 가중치 공급원. 다만 이들은 "이미 서명된" 것을 찾고, 우리는 "서명할 빈 줄"을 찾는다는 차이가 있어 그대로 쓰기보다 negative/positive 대비 학습용으로 유용.

---

## 3. 합성 문서 데이터 생성 (GT 공짜)

**29. Donut + SynthDoG** (ECCV 2022) (A)
https://github.com/clovaai/donut
OCR-free 문서 이해 트랜스포머와, 그 사전학습용 합성 문서 생성기 SynthDoG. 다국어 확장이 쉬운 것이 핵심 장점(한국어 포함).
왜 관련 있나: 한국어 렌더링·배경/노이즈 증강 파이프라인의 사실상 표준 구현. 우리 HTML 렌더 파이프라인에 종이 질감·스캔 왜곡·잉크 번짐을 얹을 때 그대로 참조.

**30. Nougat: Neural Optical Understanding for Academic Documents** (2023, arXiv:2308.13418) (A)
https://arxiv.org/abs/2308.13418
arXiv 1,748,201편의 소스+PDF 쌍을 LaTeXML → HTML5 → Markdown으로 변환해 **8.2M 페이지** 학습 데이터를 GT 비용 0으로 확보.
왜 관련 있나: "렌더 가능한 마크업이 있으면 GT는 공짜"라는 우리 전략의 원조 규모 사례. 특히 HTML 중간 표현을 거치는 점이 우리 파이프라인과 동일하며, 8.2M vs 우리 20k~60k라는 스케일 갭이 recall 98% 달성 가능성에 주는 시사점이 크다.

**31. DocSynth-300K (DocLayout-YOLO 내부)** (2024, arXiv:2410.12628) (A)
문서 합성을 2D bin packing으로 보고 Mesh-candidate BestFit으로 30만 장 생성. 이 합성 사전학습이 다양한 실문서 도메인에서 파인튜닝 성능을 유의하게 올림.
왜 관련 있나: 합성 데이터의 **다양성 설계**를 알고리즘화한 사례. 우리 HTML 생성기가 "비슷한 표만 반복 생성"하는 mode collapse에 빠지지 않도록 레이아웃 다양성을 명시적으로 최대화하는 방법론.

**32. Enhancing Document AI Data Generation Through Graph-Based Synthetic Layouts** (2024, arXiv:2412.03590) (A)
https://arxiv.org/abs/2412.03590
문서 요소를 노드, 공간 관계를 엣지로 보고 GNN으로 레이아웃 생성. local(문단-제목 정렬)과 global(보고서 계층) 패턴을 동시에 포착.
왜 관련 있나: 우리 합성 서식의 구조적 현실성을 높이는 대안. 다만 우리는 실제 정부 서식 HTML 템플릿을 시드로 쓸 수 있으므로, 생성 모델보다 "실템플릿 + 파라메트릭 변형"이 더 싸다는 판단의 비교 대상.

**33. DocSynth: A Layout Guided Approach for Controllable Document Image Synthesis** (ICDAR 2021, arXiv:2107.02638) (A)
https://arxiv.org/abs/2107.02638
레이아웃을 조건으로 문서 이미지를 생성하는 초기 controllable synthesis 연구.
왜 관련 있나: 레이아웃→이미지 조건부 생성 계열의 출발점. 우리처럼 레이아웃(=GT)을 먼저 정하고 픽셀을 나중에 만드는 방향이 옳다는 계보상의 근거.

**34. Beyond Human Annotation: Recent Advances in Data Generation Methods for Document Intelligence** (2026-01, arXiv:2601.12318) (A)
https://arxiv.org/abs/2601.12318
Document Intelligence 데이터 생성의 첫 종합 서베이. 데이터/라벨 가용성 기준으로 Data Augmentation, Generation from Scratch, Automated Annotation, Self-Supervised Signal Construction 4패러다임 분류 + 내재 품질/외재 효용 2단 평가 프레임.
왜 관련 있나: 우리 방식(Generation from Scratch + 무료 GT)이 스펙트럼 어디에 있는지, 그리고 합성 데이터 품질을 어떻게 **평가**할지에 대한 프레임을 제공. 20k를 60k로 늘릴 가치가 있는지 판단하는 기준을 여기서 가져올 수 있다.

**35. Fine-tuning Florence-2 on Object Detection Dataset (Roboflow)** (2024, 실무 가이드) (A)
https://blog.roboflow.com/fine-tune-florence-2-object-detection/
LoRA로 Florence-2를 커스텀 detection 데이터에 파인튜닝하고 mAP로 평가하는 end-to-end 노트북(L4 GPU 기준).
왜 관련 있나: loc-token 계열 VLM을 LoRA로 detection 파인튜닝하는 최소 재현 코드. 우리 1주차 baseline을 Qwen 대신 Florence-2로 빠르게 세워 "좌표 포맷이 문제인가, 데이터가 문제인가"를 분리 실험하는 데 최적.

---

## 4. 병리 대응 기법

### (a) 좌표 토크나이제이션

**36. Pix2seq: A Language Modeling Framework for Object Detection** (ICLR 2022, arXiv:2109.10852) (A)
https://arxiv.org/abs/2109.10852
Detection을 이산 토큰 시퀀스 생성으로 정식화. 핵심은 **sequence augmentation** — 실제 객체 토큰 뒤에 noise 클래스 라벨을 단 가짜 토큰을 붙여 학습시켜, 모델이 EOS를 조기에 내지 않고 최대 길이까지 생성한 뒤 noise/real을 분류하게 만든다. 이로써 recall이 오르면서도 중복 예측이 늘지 않고, 고정 길이 객체 리스트를 얻는다. 저자들은 이 기법이 사전학습보다 **파인튜닝 단계에서 주로 유효**하다고 명시.
왜 관련 있나: **우리 "ghost tail"과 조기 종료 문제의 정확한 해법.** 우리 증상은 Pix2Seq의 반대 방향(EOS를 못 내는 쪽)이지만 처방은 동일한 메커니즘 — 시퀀스 뒤쪽에 명시적 "noise/none" 클래스를 학습시키면 모델이 "여기서부터는 진짜가 아니다"를 스스로 표시하게 되고, 후처리에서 잘라낼 수 있다. LoRA만으로 구현 가능하며 아키텍처 변경이 필요 없다.

**37. Grounding Everything in Tokens for Multimodal LLMs (GETok)** (2025-12, arXiv:2512.10554) (F, 초록 수준)
https://arxiv.org/abs/2512.10554
이미지 평면을 구조적 spatial anchor로 분할하는 **grid token** + 반복적 정밀화를 위한 **offset token**을 도입. 아키텍처 변경 없이 autoregressive 안에서 2D 공간 추론을 가능하게 함. SFT/RL 양쪽에서 referring 태스크 성능 향상. (검색 스니펫 기준) Qwen2.5-VL-7B에서 동일 instruction-tuning 데이터로 text / bin / grid 포맷을 비교했을 때 grid token이 명확히 우세.
왜 관련 있나: 좌표 포맷 A/B 테스트를 우리가 다시 할 필요 없이 근거를 제공. 특히 "grid로 거친 위치 → offset으로 미세조정"의 2단 구조는 25px 체크박스처럼 **거친 앵커는 쉬운데 미세 좌표가 어려운** 우리 케이스에 딱 맞는다.

**38. Mitigating Coordinate Prediction Bias from Positional Encoding Failures (VPSG)** (2025-10, arXiv:2510.22102) (F)
https://arxiv.org/abs/2510.22102
고해상도에서 visual positional encoding이 열화되며 좌표 오차가 랜덤이 아니라 **방향성 있는 편향**으로 나타남을 규명(grounding 신호가 약해지면 모델이 학습된 공간 prior로 회귀). Vision-PE Shuffle Guidance로 재학습 없이 추론 시점에 좌표 드리프트를 교정, ScreenSpot-Pro에서 개선.
왜 관련 있나: "체크박스 개수는 맞는데 위치를 못 찍는다"는 우리 증상의 메커니즘적 설명 — 모델이 실제 위치가 아니라 학습된 레이아웃 prior를 뱉고 있을 가능성. 재학습 없는 진단·교정 도구로 즉시 실험 가능.

**39. Improving GUI Grounding with Explicit Position-to-Coordinate Mapping (RULER tokens + I-MRoPE)** (2025-10, arXiv:2510.03230) (F)
https://arxiv.org/abs/2510.03230
지도의 격자선처럼 **RULER 토큰**을 명시적 좌표 마커로 이미지에 주입해, 모델이 좌표를 맨바닥에서 생성하는 대신 마커 기준으로 보정하게 함. + I-MRoPE로 width/height 표현 균형. ScreenSpot/V2/Pro에서 일관된 향상, **고해상도 인터페이스에서 이득이 가장 큼**.
왜 관련 있나: 학습 데이터 렌더 단계에서 페이지에 눈금/격자 오버레이를 넣는 것만으로 개선 가능한, 구현 비용이 가장 싼 아이디어. 고해상도(우리 3x zoom)에서 이득이 가장 크다는 점이 결정적.

### (b) 다객체 자기회귀 · 정지 · hallucination

**40. Propose and Attend: Training-free MLLM Grounding Confidence via Multi-Token Localized Attention (MTLA)** (2026-07, arXiv:2607.05978) (F)
https://arxiv.org/abs/2607.05978
예측 토큰들이 자기가 주장하는 영역에 얼마나 강하게 attend하는지를 집계해 **학습 없이 박스별 신뢰도**를 산출. 8B 오픈모델의 COCO detection AP를 재랭킹만으로 **20.4 → 37.0**으로 개선. (연관 서치 스니펫: SOTA MLLM이 뱉는 영역의 58~68%가 실제 객체에 대응하지 않으며, Qwen3-VL은 68.1%가 GT와 매칭 실패)
왜 관련 있나: **ghost tail의 즉효 처방.** 우리는 후처리에서 가짜 박스를 버려야 하는데 autoregressive 출력에는 confidence가 없다 — MTLA가 그 결여를 학습 없이 메운다. AP 20→37은 우리 recall/precision 트레이드오프를 재설정할 만한 크기.

**41. Hallucination-Free GUI Grounding via Regression-Free Layout-Aware Matching** (2026-08, arXiv:2608.09654) (F)
https://arxiv.org/abs/2608.09654
좌표 회귀를 **완전히 제거**. frozen MLLM이 지시를 레이아웃 단서가 풍부한 구조적 시각 서술로 파싱 → 별도 grounding 모델이 layout-prior 후보들과 매칭해 선택. 좌표 회귀 파라미터 없이 Text/Icon 이진 라벨만으로 학습. ScreenSpot-Pro 정확도 +20%p 초과, Mind2Web 성공률 +15%p 초과.
왜 관련 있나: ChatRex와 함께 2안(CV proposes, VLM classifies)의 가장 강한 근거. "좌표 hallucination은 회귀를 안 하면 원천적으로 발생하지 않는다"는 논지가 우리 IoU 목표(95% of boxes ≥0.5)와 deterministic output 요건 양쪽을 동시에 해결한다.

**42. GroundingME: Exposing the Visual Grounding Gap in MLLMs** (CVPR 2026, arXiv:2512.17495) (A)
https://arxiv.org/abs/2512.17495
4개 축으로 grounding을 압박하는 벤치마크: Discriminative(유사 객체 구별), Spatial(관계 서술), **Limited(가림·초소형 객체)**, **Rejection(grounding 불가 질의 거부)**.
왜 관련 있나: Limited는 우리 25px 체크박스, Rejection은 우리 ghost tail에 대응. 평가 프로토콜 설계 시 "존재하지 않는 필드를 요구했을 때 거부하는가"를 명시적 평가 축으로 넣는 근거.

### (c) 소형 객체 · zoom · 타일링

**43. Towards Perceiving Small Visual Details in Zero-shot VQA with MLLMs (ViCrop)** (2023/2025, arXiv:2310.16033) (A)
https://arxiv.org/abs/2310.16033
MLLM의 zero-shot 정확도가 시각 대상 크기에 극도로 민감(크기에 따라 최대 **45.91%p** 하락)함을 보이고, 자동 visual cropping으로 완화.
왜 관련 있나: "3x zoom이 필요하다"는 우리 경험칙의 정량적 근거. 45.91%p라는 숫자는 zoom 파이프라인 투자를 정당화하기에 충분하다.

**44. MLLMs Know Where to Look: Training-free Perception of Small Visual Details** (ICLR 2025, arXiv:2502.17422) (A)
https://arxiv.org/abs/2502.17422
MLLM은 작은 디테일에 대해 **틀린 답을 하면서도 attention/gradient는 올바른 위치를 가리킨다**는 관찰. 이를 이용해 학습 없이 crop 영역을 자동 선정.
왜 관련 있나: "체크박스 개수는 세는데 좌표는 못 찍는다"의 직접적 설명 — 내부 표현에는 위치 정보가 있으나 출력 좌표로 디코딩되지 않는다. attention 기반으로 위치를 직접 읽어내는 우회로(40번 MTLA와 동일 계열)를 제시.

**45. CropVLM: Learning to Zoom for Fine-Grained Vision-Language Perception** (CVPRW 2026, arXiv:2511.19820) (A)
https://arxiv.org/abs/2511.19820
타깃 VLM은 **frozen**으로 두고, 정보량 높은 영역을 동적으로 고르는 별도 crop 모델을 학습.
왜 관련 있나: 베이스 grounding 능력을 파괴하지 않으면서(=catastrophic forgetting 회피) zoom 능력만 추가하는 구조. LoRA 예산이 빠듯할 때 유효한 분업.

**46. MEGA-GUI: Multi-stage Enhanced Grounding Agents for GUI Elements** (2025-11, arXiv:2511.13087) (A)
https://arxiv.org/abs/2511.13087 · https://github.com/samsungsds-research-papers/mega-gui
coarse ROI 선택 + fine-grained grounding으로 분리, **bidirectional ROI zoom**으로 spatial dilution 완화. ROI Zoom이 **공간적으로 조밀한 인터페이스에서 +28.47%p**(ScreenSpot-Pro)로 최대 이득.
왜 관련 있나: 조밀한 표 = 조밀한 UI. "coarse→fine 2단 파이프라인 + 양방향 zoom"이라는 구체적 알고리즘과, dense한 곳에서 이득이 가장 크다는 실측치가 우리 설계에 그대로 이식 가능.

**47. Zoom Consistency: A Free Confidence Signal in Multi-Step Visual Grounding Pipelines** (2026-04, arXiv:2604.15376) (A)
https://arxiv.org/abs/2604.15376
2단 zoom 파이프라인에서 step-2 예측과 crop 중심의 거리 = step-1 공간 오차의 선형 추정량이며 정답 여부와 유의하게 상관(p<10⁻⁶). 학습·추가 연산 불필요, 캘리브레이션 없이 모델 간 비교 가능한 기하량.
왜 관련 있나: zoom 파이프라인을 쓰기로 했다면 신뢰도가 **공짜로 딸려 온다**. ghost tail 필터링·선택적 재계산(저신뢰 필드만 재zoom)의 트리거로 즉시 활용.

**48. ScreenSpot-Pro: GUI Grounding for Professional High-Resolution Computer Use** (2025, arXiv:2504.07981) (A)
https://arxiv.org/abs/2504.07981
고해상도 전문 소프트웨어 화면에서의 grounding 벤치마크. 기존 모델들이 급격히 무너짐을 보임.
왜 관련 있나: 우리 문제(고해상도 페이지 + 미세 타깃)와 난이도 프로파일이 가장 유사한 공개 벤치마크. 기법의 사전 스크리닝 장소로 쓸 수 있다.

**49. UGround / Navigating the Digital World as Humans Do** (ICLR 2025, arXiv:2410.05243) (A)
https://arxiv.org/abs/2410.05243 · https://osu-nlp-group.github.io/UGround/
1.3M 스크린샷에서 10M 요소로 학습한 범용 GUI visual grounding 모델. 관련 문헌에서 **타깃 bbox가 작아질수록 모든 모델의 정확도가 보편적으로 하락**함이 확인됨.
왜 관련 있나: 데이터 스케일의 벤치마크(10M 요소 vs 우리 20k 페이지 × N필드). "요소 수" 기준으로 우리 데이터가 충분한지 계산해 볼 기준점.

**50. Can Multimodal Large Language Models Truly Understand Small Objects? (SOUBench)** (2026-04, arXiv:2604.22884) (A)
https://arxiv.org/abs/2604.22884
18,204 VQA, 6개 서브태스크, 15개 SOTA MLLM 평가 — 최고 모델도 인간 대비 23.53%p 뒤짐. SOU-Train(11,226쌍) 공개.
왜 관련 있나: 소형 객체 이해가 아키텍처 수준의 미해결 문제임을 확인. 우리 recall 98% 목표가 순수 VLM 단독으로는 위험하다는 리스크 근거.

---

## 5. Qwen-VL LoRA/PEFT 실전

**51. Qwen2.5-VL default `max_pixels` is 12× the training resolution; degrades grounding accuracy** (mlx-vlm Issue #1175) (A)
https://github.com/Blaizzy/mlx-vlm/issues/1175
Qwen2.5-VL-7B의 `preprocessor_config.json`이 `max_pixels`를 12,845,056(아키텍처 상한)으로 두고 있는데 이는 권장 기본값이 아니며, 권장치의 12배로 돌리면 **공간 추론·레이아웃 태스크의 grounding이 열화**된다는 보고. 권장은 대략 min ~262K px, max ~1.3M px.
왜 관련 있나: **당장 확인해야 할 설정 버그 후보.** 우리가 "3x zoom 해야만 잡힌다"고 관찰한 것이 사실은 max_pixels가 학습 분포 밖으로 튀어 좌표 편향(38번 VPSG의 메커니즘)이 생긴 결과일 수 있다. 학습·추론 해상도를 동일한 좁은 범위로 고정하는 것이 우선 조치.

**52. Qwen-VL-Series-Finetune (2U1)** (오픈소스 레시피) (A)
https://github.com/2U1/Qwen-VL-Series-Finetune
Qwen-VL 계열 파인튜닝 구현. ViT / merger / LLM을 각각 freeze·LoRA·full로 조합 가능. 통용되는 기본 권고는 **ViT와 merger는 freeze, LLM만 LoRA** — 메모리 절약 + 시각 표현 불안정화 회피.
왜 관련 있나: 우리 LoRA 타깃 결정의 출발점. 다만 우리 태스크는 "언어"가 아니라 "지각"이 병목이므로, ViT freeze 기본값이 오히려 병목일 수 있다 — merger만 추가로 여는 중간안을 반드시 어블레이션해야 한다.

**53. Investigating the Catastrophic Forgetting in Multimodal Large Language Models (EMT)** (2024, PMLR v234) (A)
https://proceedings.mlr.press/v234/zhai24a/zhai24a.pdf · https://yx-s-z.github.io/emt/
한 데이터셋 파인튜닝이 다른 데이터셋 성능을 파괴하며, **LoRA가 linear fine-tuning보다 더 심하게 망각**한다. 열화는 **단 1 epoch 후**에도 유의하게 나타남.
왜 관련 있나: "LoRA는 가벼우니 안전하다"는 통념을 정면 반박. 우리가 20k 합성 페이지에 여러 epoch 돌리면 zero-shot grounding 능력이 사라질 수 있다 — epoch 수를 보수적으로 잡고 매 epoch마다 grounding 리그레션 스위트를 돌려야 한다는 근거.

**54. TWIST & SCOUT: Grounding Multimodal LLM-Experts by Forget-Free Tuning** (ICCV 2025) (A)
https://openaccess.thecvf.com/content/ICCV2025/papers/Bhowmik_TWIST__SCOUT_Grounding_Multimodal_LLM-Experts_by_Forget-Free_Tuning_ICCV_2025_paper.pdf
기존 능력을 잃지 않으면서 grounding 능력을 주입하는 튜닝 기법.
왜 관련 있나: 53번이 문제라면 이것이 처방. grounding SFT의 표준 실패 모드에 대한 대응책 카탈로그.

**55. 실무 파인튜닝 가이드: Roboflow / Datature Qwen2.5-VL** (2025) (A)
https://blog.roboflow.com/fine-tune-qwen-2-5/ · https://datature.io/blog/how-to-fine-tune-qwen2-5-vl
LoRA + 4bit 양자화로 12GB VRAM(RTX 4070)급에서도 학습 가능. grounding 태스크 파인튜닝 시 **낮은 학습률(1e-5) + cosine 스케줄**로 기존 능력 보존, dynamic resolution은 784~50,176 px 범위 사용 사례.
왜 관련 있나: 하이퍼파라미터 출발점(lr, 스케줄, 해상도 범위)을 문헌 뒤지지 않고 그대로 채택 가능.

---

## 6. 평가 프로토콜

**56. OmniDocBench** (CVPR 2025, arXiv:2412.07626) (A)
https://arxiv.org/abs/2412.07626 · https://github.com/opendatalab/OmniDocBench
1,651 PDF 페이지, 10개 문서 타입 / 5 레이아웃 / 5 언어. **28개 block-level + 4개 span-level 요소의 위치 정보**와 19개 레이아웃 라벨 / 14개 속성 라벨. 요소 분할·매칭 기반 평가로 텍스트·표·수식·reading order를 모듈별로 채점.
왜 관련 있나: "요소를 매칭한 뒤 모듈별로 채점"하는 구조가 우리 요구(IoU 매칭 → 타입 정확도 별도 산출)와 동일. 평가 코드를 재사용 가능하고, 속성 라벨(예: 언어·레이아웃 유형)별 분해 리포팅이 우리 회귀 추적에 유용.

**57. The COTe score: A decomposable framework for evaluating Document Layout Analysis models** (2026-03, arXiv:2603.12718) (A)
https://arxiv.org/abs/2603.12718
DLA 평가를 분해 가능한 구성요소(검출/분류/위치)로 나누는 프레임워크.
왜 관련 있나: 우리 목표가 recall / IoU 통과율 / 타입 정확도 3개로 이미 분해되어 있는데, mAP 단일 숫자에 뭉개지 않고 이렇게 보고하는 것이 정당하다는 방법론적 뒷받침.

**58. CommonForms 평가 방식 + AcroMELD 지표 세트** (2025/2026) (F)
CommonForms는 COCO AP 계열, AcroMELD는 **containment micro-F1 / IoU-0.5 F1 / COCO mAP**를 병기하고 외부 holdout에 95% CI까지 보고.
왜 관련 있나: 서식 필드에서 "박스가 필드를 포함하는가(containment)"가 IoU보다 실용적으로 중요할 수 있다는 통찰. 입력칸은 가늘고 길어서 IoU가 작은 세로 오차에 과민하다 — containment를 보조 지표로 병기할 것을 강력 권장. 외부 holdout + CI 보고 관행도 우리 996장 holdout에 그대로 적용.

**59. Roboflow100-VL: A Multi-Domain Object Detection Benchmark for VLMs** (2025, arXiv:2505.20612) (A)
https://arxiv.org/abs/2505.20612
VLM을 다도메인 detection에서 평가하는 벤치마크(few-shot 적응 포함).
왜 관련 있나: "VLM을 detection 지표(mAP)로 평가한다"는 프로토콜의 최신 표준. 우리가 VLM 출력을 COCO 평가기에 넣을 때의 매칭·중복 처리 관행을 여기서 확인.

**60. DetToolChain: A New Prompting Paradigm to Unleash Detection Ability of MLLM** (ECCV 2024, arXiv:2403.12488) (A)
https://arxiv.org/abs/2403.12488
프롬프트 툴체인(자·격자·확대 등 시각 프롬프트)으로 학습 없이 MLLM detection 능력을 끌어올림.
왜 관련 있나: 39번 RULER 토큰의 무학습 버전. 파인튜닝 전에 "프롬프트만으로 얼마나 가는가"의 상한을 재는 저비용 실험이며, 실패하면 SFT 투자 근거가 된다.

---

## Top 8 must-read (우리 문제 기준 순위)

1. **CommonForms** (arXiv:2509.16506) — 우리 태스크와 사실상 동일. 55k 문서/450k 페이지 무료 GT + $500 학습 + "고해상도가 결정적" 어블레이션. 읽고 바로 데이터로 쓸 것.
2. **AcroMELD** (arXiv:2608.22338) — dense form을 fixed-query set prediction으로 푼 최신 SOTA. ghost tail이 구조적으로 불가능한 대안 아키텍처 + containment 지표.
3. **Pix2seq** (arXiv:2109.10852) — sequence augmentation. ghost tail / 조기 EOS 문제의 교과서적 해법이며 LoRA로 구현 가능.
4. **ChatRex** (arXiv:2411.18363) — "CV proposes, VLM classifies"의 표준 구현. Qwen2-VL COCO recall 43.9%라는 진단 수치까지 제공.
5. **Propose and Attend / MTLA** (arXiv:2607.05978) — 무학습 박스 신뢰도. 재랭킹만으로 AP 20.4→37.0. ghost tail 필터의 즉시 적용 가능한 답.
6. **Hallucination-Free GUI Grounding** (arXiv:2608.09654) — 좌표 회귀 제거 = 좌표 hallucination 제거. ScreenSpot-Pro +20%p.
7. **GETok** (arXiv:2512.10554) — grid + offset 토큰. 좌표 포맷 선택(text vs bin vs grid)에 대한 최신 근거와 coarse→fine 좌표 구조.
8. **mlx-vlm Issue #1175 + VPSG** (arXiv:2510.22102) — 해상도 설정 오류가 grounding을 망가뜨리는 메커니즘. 다른 무엇보다 먼저 확인할 것. 비용 0, 효과 잠재적 최대.

---

## 우리 설계에 바로 적용할 수 있는 것

**해상도·전처리 (오늘 당장)**
- `min_pixels`/`max_pixels`를 학습·추론에서 **동일한 좁은 범위**로 고정하고, Qwen 권장 대역(대략 26만~130만 px)을 벗어나지 말 것. 기본 config의 12.8M px는 아키텍처 상한이지 권장값이 아니며 grounding을 열화시킨다(#51). "3x zoom이 필요하다"는 관찰의 절반은 여기서 나올 수 있다.
- zoom은 임의 배율이 아니라 **SAHI식 고정 타일링**(2x2 또는 3x3, overlap 15~20%)으로 결정론화 → 타일별 grounding → 좌표 역매핑 → NMS. 결정론적 출력 요건과도 맞는다(#27, #46).
- MEGA-GUI식 coarse ROI → fine grounding 2단 구조를 채택하면 조밀 영역에서 최대 이득(+28%p 사례)이고, 부산물로 zoom-consistency 신뢰도가 공짜로 생긴다(#46, #47).

**좌표 포맷**
- Qwen의 절대 픽셀 좌표를 그대로 쓰되 **입력 해상도를 고정**하거나, 아니면 grid+offset 형태로 재정의(#37). 박스가 100개면 텍스트 숫자 좌표는 토큰 예산을 잡아먹고 시퀀스가 길어질수록 ghost tail 위험이 커진다 — 토큰 절약 자체가 병리 완화책이다.
- 렌더 단계에서 페이지에 **눈금/격자 오버레이(RULER)** 를 넣는 실험은 구현 30분, 잠재 이득 큼. 고해상도에서 이득이 가장 크다고 보고됨(#39).

**Ghost tail (최우선)**
- 학습 타깃 시퀀스 끝에 Pix2Seq식 **noise 필드 토큰**을 붙여 "실제/가짜"를 명시적으로 분류하게 학습. 고정 길이(예: 128 필드)까지 항상 생성하고 noise로 표시된 것을 잘라낸다. AcroMELD의 896 쿼리와 발상이 동일하다(#36, #18).
- 동시에 무학습 안전망으로 **MTLA 신뢰도 재랭킹**을 후처리에 넣는다(#40). 학습 없이 붙일 수 있고 효과가 크다.
- 평가에 **Rejection 축**(존재하지 않는 필드 요구 시 거부)을 넣어 ghost tail을 지표로 만든다(#42).

**박스 순서**
- reading order를 명시적 보조 태스크/헤드로 두거나(#24), 최소한 GT 시퀀스 순서를 **엄격한 결정론적 규칙**(표 단위 → 행 → 열, top-left 기준 tie-break)으로 고정. 합성 GT라 순서를 완전히 통제할 수 있는 것이 우리 강점 — 이 강점을 낭비하지 말 것.

**LoRA 타깃**
- 기본은 ViT/merger freeze + LLM LoRA이지만(#52), 우리 병목은 언어가 아니라 지각이므로 **{LLM만} / {LLM + merger} / {LLM + merger + ViT 상위 몇 층}** 3조합 어블레이션을 반드시 돌릴 것.
- LoRA는 linear FT보다 망각이 심하고 **1 epoch만에도** 열화가 나타난다(#53). epoch을 적게, lr 1e-5 + cosine으로 보수적으로(#55), 매 체크포인트마다 RefCOCO 같은 일반 grounding 리그레션을 돌려 grounding 붕괴를 감시.
- 데이터 믹싱: 서식 데이터 100%가 아니라 일반 grounding 앵커 데이터를 일정 비율 섞는다(Griffon-G 방식, #8).

**데이터**
- CommonForms 450k 페이지로 **먼저 사전학습**하고 한국 서식 합성 20k로 파인튜닝하는 2단이, 합성 20k 단독보다 거의 확실히 낫다(#17 + DocSynth-300K 패턴 #31). 우리 3-type↔11-type은 계층 매핑 가능.
- 스케일 감각: Nougat 8.2M 페이지, UGround 10M 요소 vs 우리 20k 페이지. recall 98%를 노린다면 20k는 얇다 — 다만 우리는 도메인이 훨씬 좁으므로, 늘리기 전에 **레이아웃 다양성**부터 측정할 것(#34의 내재 품질 평가 프레임).
- 체크박스는 별도 커리큘럼/loss 가중치로 다룰 것. LVLM의 구조적 맹점으로 문서화되어 있다(#19).

**평가**
- COCO mAP 단일 숫자 대신 **recall@IoU0.5 / IoU 통과율 / 타입 정확도**를 분해 보고(#57). 여기에 **containment F1**을 보조 지표로 추가 — 가늘고 긴 입력칸에서 IoU는 작은 세로 오차에 과민하다(#58).
- 996장 holdout에는 부트스트랩 95% CI를 붙여 보고(#18의 관행).

**아키텍처 결정에 대한 솔직한 한 줄**
문헌은 2안(CV proposes, VLM classifies) 쪽으로 꽤 강하게 기울어 있다 — ChatRex, Hallucination-Free GUI Grounding, AcroMELD, LMM-Det이 모두 같은 방향을 가리키고, AcroMELD는 **40M 파라미터**로 dense form에서 IoU-0.5 F1 0.93을 낸다. 4B VLM 단독으로 recall 98%를 밀어붙이기 전에, DocLayout-YOLO/RT-DETR proposal + VLM 타입 분류 baseline을 먼저 세워 두면 위험이 크게 줄고, 실패해도 그 proposal이 그대로 최종 시스템의 recall 안전망이 된다.