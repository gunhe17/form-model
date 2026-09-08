# 6 조사 — 유사 사례·튜닝 문헌 (2026-09-08)

두 에이전트가 독립 조사. 원문은 그대로 보관, 이 문서는 교차 검증과 종합.

| 파일 | 담당 | 범위 | 건수 |
|---|---|---|---|
| `opus_report.md` | Claude Opus | arXiv·학회 논문 6축 (VLM grounding / 서식 검출 / 합성 데이터 / 병리 대응 / LoRA / 평가) | 60 |
| `grok_report.md` | Grok Build (X 검색 포함) | GitHub 이슈·HF·X 스레드·상용 서비스·한국 사례 5축 | 37 |

## 두 보고서가 일치하는 결론

1. **가장 가까운 선행 = CommonForms/FFDNet** (arXiv:2509.16506). 빈 PDF 서식 → Text/Choice/Signature 3종 검출, 450k 페이지 무료 GT, 학습비 $500 미만, "고해상도가 결정적". 우리 11종은 이 3종의 세분화라 사전학습 코퍼스로 쓸 수 있다.
2. **해상도가 모델 크기보다 중요.** DocLayout-YOLO 1120~1600px, FFDNet 1216px, ViCrop "크기에 따라 최대 45.9%p 하락". 25px 글리프 실패의 직접 원인.
3. **ghost tail은 흔한 병리이고 처방이 있다.** Pix2Seq sequence augmentation(가짜 토큰을 학습시켜 경계를 스스로 표시), 고정 JSON 스키마 + 단일 토큰 클래스명(Florence-2-DocLayNet-Fixed, +7pt), 개수 N 프롬프트 + `max_new_tokens` 캡, 빈 페이지 음성 샘플.
4. **LoRA 기본값 = ViT·merger freeze, LLM만.** 공식 qwen-vl-finetune, ms-swift, Unsloth, 2U1 레포 모두 동일. 단 우리 병목은 지각이므로 {LLM} / {LLM+merger} / {+ViT 상위층} 어블레이션 필요.
5. **박스 순서를 GT에서 고정** (reading order: 표 → 행 → 열). 합성 GT라 완전 통제 가능한 우리 강점.
6. **"CV가 제안, VLM이 분류" 2안을 반드시 베이스라인으로.** ChatRex, AcroMELD(40M 파라미터로 dense form IoU-0.5 F1 0.93), Hallucination-Free GUI Grounding이 좌표 회귀 자체를 제거하는 쪽으로 기운다. README의 미결 "아키텍처 확정" 항목에 대한 문헌 답.
7. **상용 서비스는 우회로가 아니다.** Adobe Acrobat은 체크박스를 거의 못 잡고(CommonForms 비교), Google/Azure는 채워진 값 추출이 주목적. 한국어 빈 서식 필드 bbox 벤치마크는 공개된 것이 없다.

## 두 보고서가 갈리는 점 (실험으로 결정)

| 쟁점 | Opus | Grok | 판단 |
|---|---|---|---|
| 좌표 형식 | "Qwen 절대 픽셀 유지, 해상도 고정" | **Qwen3-VL은 0~1000 상대좌표, 패치 인수 32** (메인테이너 확인 이슈 #1623) | Grok이 맞다. Opus는 Qwen2.5-VL 기준. **우리 GT(픽셀 xywh) → 0~1000 xyxy 변환 필수** |
| max_pixels | 0.26~1.3M 안에 머물 것 (12.8M 기본값이 grounding 열화, mlx-vlm #1175) | 1.3~4.2M으로 올릴 것 (메인테이너 권장 0.4~6.1M) | 상충 아님. 핵심은 **train=infer 동일 고정**. 2M 부근에서 시작해 1.3M / 4M 비교 |
| LoRA 학습률 | 1e-5 + cosine (보수적) | 1e-4, 1~2 epoch (망각 논문: LoRA 1e-4는 망각 거의 없음) | 1e-4 시작, 매 체크포인트 RefCOCO류 회귀 스위트로 붕괴 감시 |
| 소형 객체 | SAHI식 고정 타일링(2×2/3×3, overlap 15~20%) + MEGA-GUI coarse→fine | 학습에 크롭 뷰 혼합, 또는 ZwZ식 증류로 단일 패스 유지 | 결정론·지연 요건상 **학습 시 멀티스케일 혼합 우선**, 부족하면 고정 타일링 |

## 우리 단계에 바로 반영할 것

**5_dataset (증강 전 변환)**
- GT를 `{"bbox_2d":[x1,y1,x2,y2] (0~1000), "type":"checkbox"}` 로 내보내는 변환기. 원본 W,H 기준. 픽셀 xywh는 평가 때만 복원.
- 시퀀스 순서 규칙 명문화 후 정렬. 음성 페이지(GT 0) 1,323장은 이미 확보.
- 타입명 11종이 토크나이저에서 단일 토큰인지 확인. 아니면 짧은 별칭.

**7 증강**
- 렌더 긴 변 1600~2048 유지. dpi 축이 이미 계획에 있으므로 해상도 하한을 이 범위로.
- 실험 항목 추가: 페이지에 눈금 오버레이(RULER 토큰식). 구현 30분.

**8 학습**
- 1차: Qwen3-VL-4B, LLM LoRA r=16 α=32 all-linear, ViT freeze, LR 1e-4, 1~2 epoch, max_pixels 2M 고정.
- Pix2Seq noise 토큰 또는 N 지정 프롬프트 중 하나로 정지 학습.
- 병렬 베이스라인: **FFDNet-L 또는 DocLayout-YOLO를 우리 합성 데이터로 학습**. VLM recall이 detector를 못 넘으면 2안(detector 제안 + VLM 분류)으로 전환.
- 선택: SFT 후 GRPO(VLM-R1). 우리 GT가 결정론적이라 IoU·recall을 reward로 직접 쓸 수 있다.

**평가**
- recall@IoU0.5 / IoU 통과율 / 타입 정확도 분해 보고 + **containment F1** 보조(가늘고 긴 입력칸은 IoU가 세로 오차에 과민).
- holdout 996장에 부트스트랩 95% CI. Rejection 축(없는 필드 요구 시 거부) 추가.
- 무학습 후처리 안전망: MTLA 신뢰도 재랭킹(AP 20→37 사례), clip·NMS·최소 크기 필터.

## 꼭 읽을 8편 (합산 순위)

1. CommonForms (2509.16506) — 동일 문제, 데이터·베이스라인·해상도 근거
2. AcroMELD (2608.22338) — dense form set prediction, containment 지표
3. Qwen3-VL 좌표 이슈 #1623 + Tech Report (2511.21631) — 0~1000, factor 32
4. Pix2Seq (2109.10852) — ghost tail 교과서 처방
5. ChatRex (2411.18363) — CV 제안 + VLM 인덱스 선택
6. Propose and Attend / MTLA (2607.05978) — 무학습 박스 신뢰도
7. OS-Atlas (2410.23218) — 작은 UI 위젯 + 0~1000 + Qwen2-VL LoRA 공개 레시피
8. GutenOCR (2601.14490) — Qwen2.5-VL-3B 문서 grounding 합성 SFT, 0.40→0.82
