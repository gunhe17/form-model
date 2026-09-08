# Qwen3-VL 4B LoRA로 한국어 행정서식 필드 검출 — 리서치 리포트

**작성일:** 2026-09-08  
**범위:** 웹 / X / GitHub / Hugging Face / arXiv. 코드 변경 없음.  
**우리 문제:** 빈 한국어 행정서식 이미지 → 11종 필드의 bbox `(x,y,w,h)`. 목표 recall ≥98%, IoU≥0.5 on ≥95%, type ≥97%, 결정론적. Zero-shot: 체크박스 **개수는 맞추지만 위치를 못 잡음**, 실박스 소진 후 **ghost box**, ~25px 글리프는 **3× zoom** 후에야 localize.

---

## 1. VLM 미세조정 — dense bbox grounding (문서/폼/테이블/UI)

### 1.1 Qwen3-VL Technical Report
**Qwen Team · 2025-11 (arXiv:2511.21631)**  
https://arxiv.org/abs/2511.21631 · HTML: https://arxiv.org/html/2511.21631

문서 파싱용으로 Common Crawl PDF 3M(10종 × 300k) + 사내 4M을 쓰고, in-house layout 모델이 reading order와 bbox를 먼저 예측한다. Grounding은 box + point 두 모드. 좌표는 **Qwen2.5-VL의 절대좌표에서 0–1000 상대좌표로 바뀌었다.** 작은 모델도 ODinW-13 / RefCOCO에서 multi-target grounding이 강해졌다.

**왜 우리:** 우리가 쓰는 백본의 공식 좌표 체계·문서 데이터 규모·multi-target 설계가 여기 있다. 2.5 레시피를 그대로 가져오면 좌표가 깨진다.

### 1.2 Qwen2.5-VL Technical Report
**Qwen Team · 2025-02 (arXiv:2502.13923)**  
https://arxiv.org/abs/2502.13923 · https://arxiv.org/html/2502.13923

2.5-VL은 **resized 이미지의 절대 픽셀 좌표**를 쓴다. 인보이스/폼/테이블 structured extraction과 “precise object grounding (absolute coords + JSON)”을 강조. Grounding 데이터는 COCO/Objects365 + Grounding DINO/SAM 합성, XML/JSON/커스텀 포맷을 섞었다.

**왜 우리:** 2.5 vs 3 좌표 차이를 모르면 LoRA 후 IoU가 무너진다. 공식 노트북 `process_bbox.ipynb`가 2.5용 `smart_resize` 스케일을 한다.

### 1.3 Qwen3-VL official finetune repo + grounding JSON
**QwenLM/Qwen3-VL · qwen-vl-finetune (README 갱신 2025–2026)**  
https://github.com/QwenLM/Qwen3-VL/tree/main/qwen-vl-finetune  
LoRA 문서: https://www.mintlify.com/QwenLM/Qwen3-VL/fine-tuning/lora  
데이터 포맷: https://www.mintlify.com/QwenLM/Qwen3-VL/fine-tuning/dataset-preparation  
2D cookbook: https://github.com/QwenLM/Qwen3-VL/blob/main/cookbooks/2d_grounding.ipynb

공식 레시피: `--tune_mm_llm True --tune_mm_vision False --tune_mm_mlp False`, LoRA `r=8, alpha=16`, LR **1e-6 ~ 2e-7** (full에 가깝게), `--max_pixels 576*28*28`, `--min_pixels 16*28*28`. Grounding 샘플은 `{"bbox_2d": [x1,y1,x2,y2]}`. README가 “training resolution is critical”을 명시.

**왜 우리:** 2×3090에서 바로 돌릴 공식 스크립트. ViT freeze가 기본값인 이유(안정성)와 pixel 범위가 여기 있다.

### 1.4 Qwen3-VL issue #1623 — 0–1000 스케일 + max_pixels
**Hormoney et al. · opened ~2025-10, comments through 2025-12**  
https://github.com/QwenLM/Qwen3-VL/issues/1623  
미러: http://gitmemories.com/QwenLM/Qwen3-VL/issues/1623

메인테이너 확인: **Qwen3-VL SFT 라벨은 반드시 0–1000으로 양자화.** 2.5의 28-배수 절대좌표를 그대로 쓰면 안 된다. 고해상도 grounding에는 `min/max ≈ 400*32*32 ~ 6000*32*32` (3-VL patch factor=32, 2.5는 28). 이미지가 1000×1000으로 늘어나는 게 아니라, **출력 좌표만 1000 그리드**.

**왜 우리:** 좌표 버그의 1순위 원인. 25px 체크박스는 이 pixel range를 올리지 않으면 한 패치에도 못 실린다.

### 1.5 LLaMA-Factory — grounding 특수토큰 vs bbox resize
**hiyouga/LlamaFactory #9279 · 2025-10-15**  
https://github.com/hiyouga/LlamaFactory/issues/9279  
관련: https://github.com/QwenLM/Qwen3-VL/issues/1616 · https://github.com/QwenLM/Qwen3-VL/issues/1835  
이슈 #584 (grounding 성능 붕괴): http://gitmemories.com/QwenLM/Qwen3-VL/issues/584

질문 핵심: (1) `<|box_start|>` 등을 JSON에 직접 넣을지, (2) LLaMA-Factory가 `smart_resize` bbox 스케일을 자동으로 하는지. 여러 사용자가 **LoRA 후 grounding이 90%→거의 0**으로 떨어졌다고 보고. 원인 후보: 2 vs 2.5 좌표 포맷 혼용, train/infer processor 불일치, transformers 버전.

**왜 우리:** LLaMA-Factory를 쓰면 **라벨을 resized 절대좌표(2.5) 또는 0–1000(3)로 직접 맞춰야** 한다. 프레임워크가 알아서 해주지 않는다.

### 1.6 ms-swift grounding notebook + 깨진 bbox 출력
**modelscope/ms-swift · notebook `qwen2_5-vl-grounding`**  
https://github.com/modelscope/ms-swift/blob/main/examples/notebook/qwen2_5-vl-grounding/zh.ipynb  
이슈 #5008: https://github.com/modelscope/ms-swift/issues/5008  
이슈 #5280: https://github.com/modelscope/ms-swift/issues/5280  
CLI: https://swift.readthedocs.io/en/latest/Instruction/Command-line-parameters.html (`QWENVL_BBOX_FORMAT=legacy|new`)

권장 커맨드: `MAX_PIXELS=1003520`, LoRA r=8 α=32, `--target_modules all-linear`, `--freeze_vit true`, LR 1e-4, 1 epoch. 전처리가 모델별로 bbox를 0–1000 정규화할지 말지 고른다 (2.5는 정규화 안 함, 3은 함). #5280: LoRA 후 `<|box_start|>(764,25),(1659,1)` 같은 **잘린/중복 박스, 끝나지 않는 토큰**.

**왜 우리:** 우리 스택 후보 중 grounding 전용 노트북이 있는 유일한 프레임워크. ghost/무한생성의 실제 재현 사례.

### 1.7 Unsloth — Qwen3-VL vision LoRA (선택적 ViT)
**@UnslothAI · 2025-10-16** https://x.com/UnslothAI/status/1978821090135687182  
Docs: https://docs.unsloth.ai/basics/vision-fine-tuning  
Notebook: https://github.com/unslothai/notebooks/blob/main/nb/Qwen3_VL_(8B)-Vision.ipynb  
Colab: https://colab.research.google.com/github/unslothai/notebooks/blob/main/nb/Qwen3_VL_(8B)-Vision.ipynb

`FastVisionModel.get_peft_model(..., finetune_vision_layers=True/False, r=16, lora_alpha=16, target_modules="all-linear")`. 기본은 vision+language 둘 다. vLLM LoRA는 **vision LoRA 미지원** → 배포 시 `finetune_vision_layers=False`. 2×3090에서 4B는 여유.

**왜 우리:** 3090 2장에 맞는 최소 경로. **작은 글리프면 ViT LoRA를 켜는 실험**이 여기서 한 줄이다.

### 1.8 OS-Atlas-Base-7B (Qwen2-VL GUI grounding)
**OS-Copilot · 2024-10 (ICLR 2025, arXiv:2410.23218)**  
Paper: https://arxiv.org/abs/2410.23218 · Repo: https://github.com/OS-Copilot/OS-Atlas  
HF: https://huggingface.co/OS-Copilot/OS-Atlas-Base-7B  
데이터: https://huggingface.co/datasets/OS-Copilot/OS-Atlas-data

Qwen2-VL-7B를 GUI element grounding에 SFT. **출력은 0–1000 상대좌표** (point 또는 `[left,top,right,bottom]`). 학습 시 `[0,1]` bbox에 ×1000. ScreenSpot에서 7B avg ~81. 아이콘(작은 위젯)이 텍스트보다 어렵다.

**왜 우리:** 폼 체크박스 ≈ UI 아이콘. **작은 위젯 + 0–1000 + Qwen2-VL LoRA**의 가장 가까운 공개 레시피.

### 1.9 UGround-V1 (Qwen2-VL, 10M GUI elements)
**OSU NLP · 2024-10 (arXiv:2410.05243)**  
https://arxiv.org/abs/2410.05243 · https://osu-nlp-group.github.io/UGround  
HF: https://huggingface.co/osunlp/UGround

웹에서 합성한 1.3M 스크린샷 / 10M element. 출력은 **element 중심점**. UGround-V1-7B (Qwen2-VL) ScreenSpot avg 86.3, 아이콘도 79–84. “간단한 레시피 + 대량 합성 GT”가 핵심.

**왜 우리:** HTML 렌더 → 무료 GT라는 우리 계획과 동일. **포인트 vs 박스**를 ablation할 근거.

### 1.10 Florence-2-DocLayNet-Fixed — 클래스명 hallucination 수정
**Yifei Hu (@hu_yifei) · 2024-10-29**  
X: https://x.com/hu_yifei/status/1851335124853408002  
HF: https://huggingface.co/yifeihu/Florence-2-DocLayNet-Fixed

DocLayNet에 Florence-2-large-ft. **클래스명을 단일 토큰으로 리맵** (`Section-header`→`Section`) → mAP50-95 **+7pt**, 추론도 빨라짐. 그래도 YOLO(~79%)보다 낮음(70%). 정성적으로는 **박스 경계가 YOLO보다 깨끗**하고, YOLO는 텍스트 중간을 자르거나 중복 박스를 그린다. 자신감 점수가 없어 mAP 계산 시 conf=1로 강제.

**왜 우리:** 11개 타입을 `checkbox`/`radio`처럼 **짧은 단일 토큰**으로 고정하면 ghost 라벨이 줄어든다. VLM은 검출 mAP에서 YOLO에 지지만 박스 품질은 나을 수 있다.

### 1.11 PaliGemma `<loc0000>`–`<loc1023>` (0–1024 bins)
**Google · 2024-05/07 (arXiv:2407.07726)**  
HF blog: https://huggingface.co/blog/paligemma  
Table-detection FT: https://huggingface.co/ucsahin/paligemma-3b-mix-448-ft-TableDetection

좌표를 **vocab 토큰**으로 양자화. 순서 **y1,x1,y2,x2** (COCO와 반대). `/1024 * H/W`. 문서 이해 mix 체크포인트가 있고, 테이블 검출 LoRA 사례가 있다.

**왜 우리:** JSON 숫자가 아니라 **finite vocab**이면 “끝나지 않는 박스 나열”이 원리적으로 어렵다. 25px 객체는 1024-bin에서 ~1–2 bin → 양자화 오차가 IoU 0.5를 위협.

### 1.12 Datature — Qwen2.5-VL LoRA, 반복/범위 밖 박스
**Datature Blog · 날짜 페이지 기준 2025**  
https://datature.io/blog/how-to-fine-tune-qwen2-5-vl

LoRA r=4, α=16, **W_q/W_v만**. 절대좌표는 (a) 이미지 밖 박스, (b) 반복 실패. 정규화 좌표가 해상도 변화에 안정. 파인튠 후에도 **박스를 반복**하고 복잡한 객체에서 hallucination.

**왜 우리:** ghost/반복의 공개 재현. **q/v only는 용량이 부족**할 수 있음 → all-linear가 더 안전.

### 1.13 @hu_yifei — Qwen2-VL-7B LoRA OCR (WER 0.02)
**Yifei Hu · 2024-09-10**  
https://x.com/hu_yifei/status/1833559442077753723

같은 OCR 데이터로 Qwen2-VL-2B / 7B LoRA / Phi-3.5-vision 비교. **7B LoRA가 압도**, 일반화 징후. 2B와 4bit는 엣지에서 붕괴.

**왜 우리:** 4B를 쓰는 우리 계획의 하한선. 문서 태스크에서 2B급은 위험, 7B LoRA가 sweet spot이라는 현장 증거.

### 1.14 @rachitt_123 — Qwen3-VL-4B LoRA, 인도 금융문서 → JSON
**Rachit · 2026-09-05**  
https://x.com/rachitt_123/status/2096114816683544937  
모델: https://huggingface.co/objectai/obj_v1

Qwen3-VL-4B를 금융 문서 이미지→JSON에 LoRA. 우리 백본·사이즈와 동일. bbox가 아니라 structured extraction.

**왜 우리:** 4B LoRA가 “문서→구조화”에 실제로 쓰이고 있다. 필드 **값** 추출과 **위치** 추출은 다르다는 점만 구분할 것.

---

## 2. Form field / fillable-widget / checkbox 검출

### 2.1 CommonForms + FFDNet (가장 직접적인 SOTA)
**Joe Barrow · 2025-09-20 (arXiv:2509.16506)**  
https://arxiv.org/abs/2509.16506 · https://arxiv.org/html/2509.16506  
Repo: https://github.com/jbarrow/commonforms  
모델: https://huggingface.co/jbarrow/FFDNet-L · 데이터: https://huggingface.co/datasets/jbarrow/CommonForms

Common Crawl fillable PDF → 55k docs / 450k pages, 1/3 non-English. 3-class detector: **Text Input / Choice Button (checkbox+radio) / Signature**. FFDNet-L @1216px: Text 71.4 / Choice 78.1 / Signature 93.5, AP 81.0. **고해상도가 ablation에서 핵심.** Adobe Acrobat은 체크박스를 거의 안 잡고, FFDNet이 더 낫다고 정성 비교. 학습비 <$500.

**왜 우리:** VLM 대신 **순수 detector 베이스라인**. 체크박스 AP 78은 우리 IoU≥0.5 @95%에 아직 못 미치지만, 25px 글리프에는 detector가 VLM보다 유리할 가능성이 크다. 합성 HTML GT로 YOLO/DETR을 같이 학습하는 앙상블 후보.

### 2.2 Adobe Acrobat AI Form Detection
**Adobe HelpX · 2026-04 “Detect form fields more accurately…”**  
https://helpx.adobe.com/acrobat/desktop/whats-new/whats-new-acrobat-desktop.html  
설계 가이드(구버전, 알고리즘 설명): https://acrobatusers.com/tutorials/designing-forms-auto-field-detection-adobe-acrobat/index.html

감지 대상: underline/box, checkbox, radio, signature, comb, table fill-in. **combo/list/barcode는 비검출.** “stroked square”만 체크로 보고, 원형은 라디오로 오인하는 고전적 실패. CommonForms 논문: Acrobat은 **choice button을 사실상 스킵**.

**왜 우리:** 상용 상한선이 체크박스에서 낮다. `□ [ ] ①②` 글리프는 Acrobat 규칙에도 안 걸린다.

### 2.3 Google Document AI Form Parser
**Google Cloud Docs (v2.0 GA)**  
https://docs.cloud.google.com/document-ai/docs/form-parser  
프로세서 목록: https://cloud.google.com/document-ai/docs/processors-list

KVP + 테이블 + **selection marks (checkbox filled/unfilled)** + 11 generic entities (email, phone, date_time, …). 200+ 언어. 잘 정의된 “label: ___” 폼에 강함. **빈 필드 위치**보다 **채워진 값/KVP**가 주 출력.

**왜 우리:** type taxonomy(phone/email/date)는 비슷하지만, 빈 HWP 서식의 **빈 칸 bbox**는 이 제품의 주 목표가 아니다.

### 2.4 Azure Document Intelligence (구 Form Recognizer)
**Microsoft Learn, Layout / General document, v3.1+**  
https://learn.microsoft.com/en-us/azure/ai-services/document-intelligence/prebuilt/general-document  
모델 개요: https://learn.microsoft.com/en-us/azure/ai-services/document-intelligence/concept-layout  
CJK 테이블 + selection mark 개선 블로그: https://techcommunity.microsoft.com/blog/azure-ai-services-blog/document-layout-analysis-model-by-form-recognizer-adds-new-structure-insights/3642004

Layout 모델: text, tables, **selection marks**, paragraphs, roles. Custom template은 **signature presence**. CJK 밀집 테이블을 따로 개선했다고 명시.

**왜 우리:** 한국어 테이블+체크에 가장 가까운 상용 엔진. 그래도 HWP `□` 글리프·인라인 공백·“(서명 또는 인)”은 커스텀.

### 2.5 DocLayout-YOLO + DocSynth-300K
**opendatalab · 2024-10 (arXiv:2410.12628)**  
https://arxiv.org/abs/2410.12628 · https://github.com/opendatalab/DocLayout-YOLO

YOLOv10 + Mesh-candidate BestFit 합성 300k. DocLayNet mAP **79.7**, AP50 93.4, imgsz **1120–1600**, 85+ FPS. 클래스: Title/Text/Table/List/Caption/Header/Footer/Footnote/Picture/Formula. **Form field / checkbox 클래스 없음.**

**왜 우리:** 레이아웃 프리필터(표/본문 영역)로는 최고 효율. 필드 검출기로 쓰려면 클래스를 다시 찍어야 한다. **고해상도(≥1600)가 문서 검출의 기본값.**

### 2.6 PP-DocLayout / PP-DocLayoutV3 (RT-DocLayout)
**PaddlePaddle · 2025-03 (arXiv:2503.17213) / 2026 RT-DocLayout (PP-DocLayoutV3)**  
https://arxiv.org/abs/2503.17213 · https://arxiv.org/html/2503.17213v1  
V3는 25 클래스, polygon, reading order. Docling 플러그인: https://github.com/DCC-BS/docling-pp-doc-layout

PP-DocLayout-L mAP@0.5 **90.4**, 31M params. DocLayout-YOLO보다 세분(문서제목 vs 문단제목, header/footer를 abandon하지 않음). V3는 왜곡/비평면 문서.

**왜 우리:** 오픈소스 레이아웃 중 클래스 세분이 가장 실무적. 그래도 checkbox widget은 없음.

### 2.7 Surya layout (datalab-to)
**https://github.com/datalab-to/surya**

라인 검출 + layout. 라벨에 **Form**, Table, Text, Header, Handwriting 등. 스캔 폼 예시가 README에 있음. 필드 위젯이 아니라 페이지 영역.

**왜 우리:** 빠른 CPU 레이아웃. 폼 페이지 vs 일반 문서를 거르는 프론트엔드.

### 2.8 Docling (IBM)
**arXiv:2408.09869 · https://arxiv.org/abs/2408.09869 · https://docling.ai/**

RT-DETR 계열을 DocLayNet에 재학습. 레이아웃+TableFormer+OCR. 폼 필드는 없음.

**왜 우리:** 파이프라인 조립용. 필드 검출 대체재 아님.

### 2.9 yolo-doclaynet (ppaanngggg)
**https://github.com/ppaanngggg/yolo-doclaynet**  
YOLOv12x mAP50-95 **0.794**, Table 0.888 / Text 0.880. Nano도 0.73+.

**왜 우리:** Florence-2 대비 “작은 YOLO가 문서 mAP에서 이긴다”는 정량 근거. 우리 11클래스를 이 레포 학습 스크립트에 바꿔 끼울 수 있다.

### 2.10 Upstage Document Digitization / Parse
**https://console.upstage.ai/api/docs** (Document Digitization API)

페이지 width/height + 텍스트 + 다각형. Clova OCR 스키마 마이그레이션 옵션. 한국 스타트업, 문서 OCR/파싱이 주력. **빈 위젯 검출 API는 공개 문서에 없음.**

**왜 우리:** 한국어 OCR 품질 참고. 필드 localize는 우리가 직접 해야 함.

---

## 3. Synthetic document 파이프라인 (HTML/LaTeX → 무료 GT)

### 3.1 SynthDoG + Donut (네이버 클로바, **한국어 포함**)
**Kim et al., ECCV 2022 (arXiv:2111.15664)**  
https://arxiv.org/abs/2111.15664 · https://github.com/clovaai/donut  
SynthDoG: https://github.com/clovaai/donut/tree/master/synthdog  
HF ko: https://huggingface.co/datasets/naver-clova-ix/synthdog-ko

Wikipedia ECJK로 언어당 0.5M 페이지. 배경(ImageNet)+종이 텍스처+랜덤 레이아웃. Donut은 OCR-free image→JSON. **bbox GT는 없음** (읽기/파싱 프리트레인용).

**왜 우리:** 한국어 문서 VLM의 원조 합성기. 우리 HTML 렌더러에 **한글 위키 텍스트 + 한컴 폰트**를 넣는 최소 구현체.

### 3.2 DocSynth-300K (DocLayout-YOLO)
**https://huggingface.co/datasets/opendatalab/DocSynth-300K** (논문 2410.12628)

문서 합성을 2D bin packing으로 보고 텍스트/이미지/표를 배치. **레이아웃 bbox GT가 공짜.**

**왜 우리:** “렌더 = GT”의 대규모 선행. 우리는 빈 칸/체크/서명 위젯을 패킹 아이템으로 추가하면 된다.

### 3.3 Kosmos-2.5 (Microsoft, 357M pages)
**arXiv:2309.11419 · https://arxiv.org/abs/2309.11419**  
HF: https://huggingface.co/microsoft/kosmos-2.5

두 태스크: (1) **text + spatial coordinates**, (2) markdown. 문서/표/차트/손글씨. bbox 있는 literate pretrain의 규모 상한.

**왜 우리:** “텍스트 블록 bbox”와 “필드 bbox”는 다르지만, **좌표를 언어 헤드가 내도록** 사전학습한 가장 큰 공개 선례.

### 3.4 Nougat (Meta, arXiv LaTeX→PDF 쌍)
**arXiv:2308.13418 · https://github.com/facebookresearch/nougat**

1.7M arXiv 소스 → LaTeXML HTML → 페이지 이미지 + markdown GT. 수식/표에 강함. 폼/체크 없음.

**왜 우리:** **컴파일 가능한 소스에서 픽셀-GT를 뽑는** 파이프라인 참고. 우리 HTML/CSS 렌더와 동형.

### 3.5 SynthDoc (bilingual rendering, 2024)
**arXiv:2408.14764 · https://arxiv.org/abs/2408.14764**

공개 코퍼스 + 렌더러로 텍스트/이미지/표/차트. Donut 프리트레인에 넣으면 read task가 좋아짐. 영·중 중심.

**왜 우리:** 렌더 파이프라인 모듈 구조(텍스트 엔진, 표, 차트)를 한국어 서식 쪽으로 옮길 때 체크리스트.

### 3.6 Qwen3-VL 자체 문서 합성
기술 리포트 §문서 파싱: layout 모델 bbox + Qwen2.5-VL-72B region OCR → **QwenVL-HTML (element-level bbox)**. Grounding은 Qwen2.5-VL + Grounding DINO로 unlabeled 이미지에 pseudo-box.

**왜 우리:** 우리가 HTML을 직접 렌더하면 **pseudo-label이 필요 없다.** 교사 모델 증류는 실스캔 도메인 적응 단계에만 쓰면 된다.

---

## 4. Qwen-VL grounding 미세조정의 알려진 실패와 고침

### 4.1 좌표 드리프트: 2.5 절대 vs 3 상대, factor 28 vs 32
**이슈 #1623, #1835, #1780**  
https://github.com/QwenLM/Qwen3-VL/issues/1623  
https://github.com/QwenLM/Qwen3-VL/issues/1835  
https://github.com/QwenLM/Qwen3-VL/issues/1780  
설명 글: https://adg.csdn.net/694cf2fa5b9f5f31781a9f5b.html

| | Qwen2.5-VL | Qwen3-VL |
|---|---|---|
| 좌표 | resized 절대 px | **0–1000 상대** |
| patch / factor | 14 / **28** | 16 / **32** |
| 라벨 변환 | `smart_resize` 후 스케일 | `x/W*1000` (원본 W,H) |

Train/infer `min_pixels`/`max_pixels`가 다르면 2.5는 박스가 어긋나고, 3은 상대좌표라 이 문제는 줄어든다. Computer-use는 또 0–1000 display 공간을 쓴다 (#1780).

**왜 우리:** 데이터 파이프라인 1순위 버그. **라벨은 원본 이미지 기준 0–1000**, processor는 factor=32.

### 4.2 Ghost / 반복 / 멈추지 않는 박스
**Datature 블로그** (위 1.12), **ms-swift #5280**, **Florence-2 클래스 hallucination** (1.10)

패턴: 실제 객체가 끝나면 박스를 계속 찍거나, `<|box_start|>`만 반복하거나, 좌표가 이미지 밖으로 나감. Datature는 **새 special token을 LoRA로 충분히 못 데워서**라고 가설. Florence-2는 **가변 길이 클래스 문자열이 환각**을 키운다고 보고 단일 토큰으로 고침.

**고침 (문헌+이슈에서 반복되는 것):**
- 출력 스키마를 **고정 JSON 배열**로, 가능하면 `N`을 프롬프트에 넣기 (`"There are 37 checkboxes; emit exactly 37"`).
- 클래스명 단일 토큰 / enum.
- `max_new_tokens`를 `N * tokens_per_box + slack`으로 캡.
- 디코드 후 IoU-NMS, 면적 < min_glyph 삭제, 이미지 밖 clip.
- 학습에 **empty-page / hard-negative**와 **정확한 N에서 EOS**.

**왜 우리:** zero-shot 실패 모드와 동일. 손실만 CE로 두면 모델은 “박스 토큰을 더 내는 것”을 선호한다.

### 4.3 LoRA 후 grounding 붕괴 / forgetting
**LLaMA-Factory 사용자들 (#584 등)**, **ms-swift #3617 (다이미지 후 난해 출력)**  
논문: *Fine-tuning MLLMs Without Forgetting Is Easier Than You Think* https://arxiv.org/html/2603.14493v1

고LR full FT (1e-5)는 OOD −16~−34pt. **LoRA 1e-4 또는 full 1e-6**이면 forgetting이 거의 없음. 공식 Qwen 스크립트는 ViT freeze + 매우 낮은 LR. Unsloth/ms-swift 기본도 `freeze_vit=true`.

**왜 우리:** 첫 실험은 **LLM LoRA only, ViT freeze, LR 1e-4, 1–2 epoch**. 작은 글리프가 안 잡히면 그때만 ViT LoRA를 낮은 LR로.

### 4.4 작은 객체: zoom-in / think-with-images / ZwZ
**Qwen3-VL cookbook** https://github.com/QwenLM/Qwen3-VL/blob/main/cookbooks/think_with_images.ipynb  
툴 코드: https://github.com/QwenLM/Qwen-Agent/blob/main/qwen_agent/tools/image_zoom_in_qwen3vl.py  
ZwZ (Region-to-Image Distillation, arXiv:2602.11858): https://arxiv.org/abs/2602.11858 · HF https://huggingface.co/inclusionAI/ZwZ-8B

공식 툴: bbox를 0–1000으로 받아 crop한 뒤 `smart_resize(..., factor=32, min_pixels=256*32*32)`로 **크롭을 최소 256 토큰까지 확대**. ZwZ는 추론 시 zoom 대신, 크롭 VQA를 풀이미지+overlay bbox로 증류. ZoomBench에서 큰 폭 향상, 단일 패스.

**왜 우리:** zero-shot 3× zoom과 정확히 같은 축. 학습 때 **풀페이지 + 타일(셀/행 crop)** 멀티스케일을 넣거나, 추론 때 zoom을 쓰면 25px가 산다. 결정론·지연을 지키려면 ZwZ식 증류가 더 맞다.

### 4.5 해상도 / tiling
DocLayout-YOLO imgsz 1120–1600, FFDNet 1216–1600, CommonForms ablation “high-res is crucial”. Qwen3-VL 메인테이너: grounding은 `400*32*32 ~ 6000*32*32`. A4 300dpi ≈ 2480×3508인데 기본 `576*28*28≈0.45Mpx`로 줄이면 25px 체크가 수 픽셀이 된다.

**왜 우리:** **max_pixels를 최소 ~1.5–4M (대략 1280–2048 장변)** 로 올리고, 그래도 부족하면 표 셀 단위 crop-and-merge.

### 4.6 박스 순서
문서 모델(Qwen3-VL HTML, Docling, PP-DocLayoutV3)은 **reading order**를 따로 학습한다. GUI 모델은 보통 지시된 한 원소만. 밀집 폼에서 순서가 비면 모델이 같은 칸을 두 번 찍거나 건너뛴다.

**왜 우리:** GT를 **top-to-bottom, left-to-right (테이블은 row-major)** 로 고정. 학습/평가 모두 같은 정렬 후 Hungarian matching.

---

## 5. 한국어 — HWP / 서식 / 필드

### 5.1 Donut + SynthDoG-ko (네이버 클로바)
위 3.1. 한국어 VDU의 사실상 표준 프리트레인. 산업 영수증/문서 JSON 파싱에 쓰였지만 **필드 위치는 비공개/비공개 데이터**.

**왜 우리:** 한글 렌더·폰트·줄간격의 공개 레퍼런스. 클로바 상업 OCR(Document AI)은 값 추출 중심.

### 5.2 hwpkit — HWP/HWPX 폼 채우기 (소스 레벨, 비전 아님)
**PyPI 2026-06-09** https://pypi.org/project/hwpkit/

순수 파이썬으로 `.hwp`/`.hwpx` 열고 `inject_text`, `swap_in_para_text("□ 석사", "☑ 석사")`, `place_image`로 도장/서명. 한글이 검증하는 OLE 구조를 유지.

**왜 우리:** **디지털 HWP가 있으면 비전 없이 필드를 채울 수 있다.** 우리 입력은 “빈 서식 **이미지**”이므로 보완재. 합성 GT를 만들 때 HWPX XML에서 필드 인덱스를 뽑아 HTML로 렌더하는 경로가 가능하다.

### 5.3 한글 양식 개체 — 누름틀 / 체크박스 / “(서명 또는 인)”
**inline AI · 2026-02-09** https://www.inline-ai.com/en/blog/hwp-form-controls-guide  
한컴 필드: https://help.hancom.com/hoffice/multi/ko_kr/hwp/insert/madanginfo/madanginfo(summary).htm  
HWP 스펙 Tag `HWPTAG_FORM_OBJECT` (특허 KR102547757B1 등)

실무에서 체크는 (1) **문자표 글리프 `□/☑`** (클릭 불가), (2) **양식 개체 선택상자** (진짜 위젯). 행정서식은 거의 (1)+밑줄+표 셀. 서명란 관용구 **“(서명 또는 인)”**.

**왜 우리:** 타입 정의. `□ [ ] ①②`는 위젯이 아니라 **글리프**라 detector/VLM 모두 소객체 문제. 합성 HTML에 이 세 글리프+서명 문구를 필수 템플릿으로.

### 5.4 KISTI — DocLayout-YOLO로 국내 R&D 보고서 TOC
**KCI ART003306058 · 2026-02**  
https://www.kci.go.kr/kciportal/landing/article.kci?arti_id=ART003306058

국내 과기 보고서(스캔 PDF 포함)에 DocLayout-YOLO 10클래스 + 영역 OCR. 학술 문서이지 행정 양식은 아님.

**왜 우리:** 한국어 문서에 YOLO 레이아웃을 실제로 쓴 공개 사례. 행정서식 벤치가 아직 비어 있다는 뜻.

### 5.5 군수 성적서 + PaddleOCR PP-Structure (한국어 논문)
**JKSQM 2025, 53(3):435** https://doi.org/10.7469/jksqm.2025.53.3.435

한국어+영어 Tesseract vs PP-Structure. 표 셀 **bbox+텍스트 HTML GT**. 레이아웃 파이프라인이 사후 OCR 수정보다 낫다.

**왜 우리:** 한국어 **밀집 표 + 셀 bbox** GT 설계가 우리 표 칸 필드와 유사.

### 5.6 행정 서식 원문 패턴 (프리폼 등)
예: https://www.freeforms.co.kr/view/52-form100-014606.html — `□ 면허증`, `신청인 (서명 또는 인)`, 처리기간, 주민등록번호 칸.

**왜 우리:** 합성 템플릿의 리얼리즘 체크리스트. radio는 `□` 나열, signature는 고정 문자열, 전화번호/날짜는 밑줄 또는 칸 분할.

공개된 “한국어 행정서식 필드 bbox 벤치마크”나 스타트업의 필드 추출 논문은 **거의 없음**. Upstage/Clova는 OCR·KIE. 이 공백이 우리 기회의 근거.

---

## Top 8 (우리 문제에 대한 영향 순)

| # | 항목 | 한 줄 |
|---|---|---|
| 1 | **Qwen3-VL 좌표 = 0–1000, factor=32** (#1623, tech report) | 라벨/평가를 2.5 절대좌표로 두면 IoU가 처음부터 죽음 |
| 2 | **CommonForms / FFDNet** | 체크/서명/텍스트 위젯 detector SOTA. VLM 대비 베이스라인·앙상블 |
| 3 | **고해상도 + zoom** (FFDNet ablation, DocLayout-YOLO 1600, Qwen zoom-in, ZwZ) | 25px 실패의 직접 원인. max_pixels와 타일이 모델 크기보다 중요 |
| 4 | **고정 길이 JSON + 단일 토큰 클래스** (Florence-2-Fixed, Datature 반복 박스) | ghost/무한생성 억제 |
| 5 | **OS-Atlas / UGround 레시피** (Qwen2-VL, 0–1000, 작은 UI 위젯, 합성 GT) | 우리 태스크와 기하가 가장 비슷 |
| 6 | **공식 LoRA: freeze ViT, r=8–16, 낮은 LR** (qwen-vl-finetune, ms-swift) | grounding 붕괴를 피하는 기본값 |
| 7 | **HTML/HWP 렌더 = 무료 GT** (SynthDoG-ko, DocSynth-300K, hwpkit) | 20k–60k 페이지 계획의 검증된 길 |
| 8 | **Adobe/Google/Azure는 빈 HWP 글리프를 못 잡음** | 상용으로 우회 불가. 우리가 풀 문제 |

---

## 우리 설계에 바로 적용할 것

**좌표 포맷**  
- Qwen3-VL-4B: 라벨·모델 출력 모두 **`bbox_2d: [x1,y1,x2,y2]` in 0–1000**, 원본 이미지 width/height 기준.  
- 평가 때만 `x1/1000*W` → `(x,y,w,h)` 픽셀.  
- 2.5 코드/`process_bbox.ipynb`의 resized-absolute를 **쓰지 말 것**.  
- 내부 스키마는 COCO xyxy, 모델 I/O만 1000-grid.

**해상도**  
- Processor `factor=32`.  
- `min_pixels` ≥ `256*32*32` (크롭 시 공식 zoom 툴과 동일), `max_pixels` **최소 `1280*32*32` ~ `2048*32*32`** (약 1.3–4.2M). 기본 576×28×28은 25px를 지운다.  
- A4 렌더를 **긴 변 1600–2048**로 맞추고, 표가 밀집한 페이지는 **행/셀 crop-and-merge** (추론) 또는 학습에 크롭 뷰를 섞기.  
- train/val/infer **동일** min/max_pixels.

**LoRA**  
- 1단계: `tune_mm_llm=True`, **ViT·merger freeze**, `r=16`, `alpha=32`, `target_modules=all-linear` (q/k/v/o + MLP; vision 이름 충돌 주의). LR **1e-4**, cosine, warmup 3–5%, **1–2 epoch**, 2×3090 bf16.  
- 2단계(작은 글리프가 안 잡히면): vision LoRA `r=8`, LR **1e-5 이하**.  
- Unsloth면 `finetune_vision_layers` 플래그로 동일. vLLM 서빙이면 vision LoRA는 빼기.

**박스 순서·스키마**  
- GT 정렬: **reading order** (y, then x; 테이블 row-major).  
- 출력:  
  `[{"bbox_2d":[...],"type":"checkbox"}, ...]`  
  `type ∈ {text,number,date,time,phone,email,radio,checkbox,signature,textarea,image}` — **한 토큰 클래스**.  
- 프롬프트에 **타입별 개수** 또는 전체 N을 넣고, 학습 타깃은 그 N개 후 EOS.  
- `max_new_tokens = N * ~20 + 64`. temperature=0.

**Stop / ghost**  
- 학습: N개에서 끝나는 예 + “0 fields” 빈 페이지.  
- 추론: JSON parse 실패 시 재시도 1회, 그다음 버림.  
- 후처리: clip to image, min side ≥ ~0.4% of min(H,W) (25px @ 2048 ≈ 1.2%), pairwise IoU>0.5 NMS, 타입별 개수가 GT 분포를 크게 넘으면 truncate.  
- 결정론: greedy, 동일 seed, 동일 해상도.

**데이터**  
- HTML 템플릿에 한국어 행정 관용: `□ [ ] ①②`, 밑줄 빈칸, `"(서명 또는 인)"`, 주민번호/전화 칸, 표. 폰트는 한컴/Noto Sans KR.  
- SynthDoG-ko 텍스트 + DocSynth식 패킹으로 20k부터.  
- **FFDNet-L을 병렬 베이스라인**으로 돌려 VLM recall이 detector를 넘는지 먼저 확인.  cast: checkbox/radio→Choice, signature→Signature, 나머지 텍스트류→Text Input.  
- 실스캔 적응은 나중에, HWP 원본이 있으면 hwpkit으로 위젯 GT를 뽑아 렌더와 대조.

**하지 말 것**  
- 2.5 절대좌표 데이터로 3을 학습.  
- 기본 max_pixels로 풀페이지만.  
- 열린 caption 스타일로 박스를 무제한 나열.  
- 첫 런에서 ViT full FT + LR 1e-4.  
- Acrobat/Document AI에 빈 `□` 검출을 맡기기.
