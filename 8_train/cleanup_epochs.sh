#!/bin/sh
# 학습 런의 에폭 스냅샷(weights/epoch*.pt)만 지운다. last.pt·best.pt 는 전부 남긴다.
# 대상: 8_train/runs/*/weights/epoch<숫자>.pt  단, 아래 PRESERVE 런은 통째로 제외.
#   보존: ft_v5e(최종 채택) · ffdnet_s1v5_syn(그 베이스)
# 에폭 스냅샷은 학습 중간 상태이고 재현 절차(8_train/README '최종 채택 가중치 재현')로 다시 만들 수 있다.
# 안전장치(하나라도 실패하면 아무것도 지우지 않는다):
#   G1 저장소 루트 아래 실경로, 심볼릭 링크 아님
#   G2 git 이 무시하는 경로이고 추적 파일 0
#   G3 루트와 같은 디바이스
#   G4 파일명이 정확히 epoch<숫자>.pt (last/best/기타는 대상 아님)
#   G5 학습 프로세스가 돌고 있지 않음
#   사후 검증: 런마다 last.pt 또는 best.pt 가 남아 있는지 확인
# 사용: sh 8_train/cleanup_epochs.sh          # 검사 + 목록만
#       sh 8_train/cleanup_epochs.sh --yes    # 검사 통과 시 삭제
set -u
ROOT=$(cd "$(dirname "$0")/.." && pwd -P)
RUNS="$ROOT/8_train/runs"
PRESERVE="ft_v5e ffdnet_s1v5_syn"
YES=${1:-}
fail() { echo "중단: $*" >&2; exit 1; }
dev() { stat -c %d "$1" 2>/dev/null || stat -f %d "$1"; }

echo "루트: $ROOT"
[ -d "$ROOT/.git" ] || fail "저장소 루트가 아님"
[ -d "$RUNS" ] || { echo "runs 없음 — 할 일 없음"; exit 0; }
ROOTDEV=$(dev "$ROOT")
(cd "$ROOT" && git check-ignore -q "8_train/runs") || fail "G2 8_train/runs 가 gitignore 대상이 아님"
n_tracked=$(cd "$ROOT" && git ls-files "8_train/runs" | wc -l)
[ "$n_tracked" -eq 0 ] || fail "G2 runs 안에 추적 파일 $n_tracked 개"
pgrep -f "yolo detect train" >/dev/null 2>&1 && fail "G5 학습 프로세스 실행 중 — 종료 후 실행할 것"

LIST=$(mktemp); TOTAL=0; N=0
for wd in "$RUNS"/*/weights; do
  [ -d "$wd" ] || continue
  run=$(basename "$(dirname "$wd")")
  skip=0
  for p in $PRESERVE; do [ "$run" = "$p" ] && skip=1; done
  if [ "$skip" -eq 1 ]; then echo "  보존: $run (통째로)"; continue; fi
  cnt=0; sz=0
  for f in "$wd"/epoch*.pt; do
    [ -f "$f" ] || continue
    b=$(basename "$f")
    case "$b" in epoch*.pt) ;; *) fail "G4 대상 아님: $f";; esac
    echo "$b" | grep -Eq '^epoch[0-9]+\.pt$' || fail "G4 파일명 규칙 불일치: $f"
    [ -L "$f" ] && fail "G1 심볼릭 링크: $f"
    rp=$(cd "$(dirname "$f")" && pwd -P)/$b
    case "$rp" in "$RUNS"/*) ;; *) fail "G1 runs 밖: $rp";; esac
    [ "$(dev "$f")" = "$ROOTDEV" ] || fail "G3 디바이스 다름: $f"
    echo "$f" >> "$LIST"; cnt=$((cnt+1)); sz=$((sz+$(wc -c < "$f")))
  done
  [ "$cnt" -gt 0 ] && { echo "  $run: epoch*.pt $cnt 개 $((sz/1024/1024)) MB"; N=$((N+cnt)); TOTAL=$((TOTAL+sz)); }
done
echo "== 대상 합계: $N 파일 · $((TOTAL/1024/1024)) MB"
[ "$N" -gt 0 ] || { echo "지울 것 없음"; rm -f "$LIST"; exit 0; }
echo "== 여유(전)"; df -h "$ROOT" | tail -1
if [ "$YES" != "--yes" ]; then echo "dry-run — 삭제하지 않음. 실제 삭제는 --yes"; rm -f "$LIST"; exit 0; fi
echo "== 삭제"
while IFS= read -r f; do
  if command -v ionice >/dev/null 2>&1; then ionice -c3 nice -n19 rm -f "$f"; else nice -n19 rm -f "$f"; fi
done < "$LIST"
rm -f "$LIST"
echo "== 여유(후)"; df -h "$ROOT" | tail -1
echo "== 사후 검증 (런마다 last/best 가 남아 있어야 함)"
for wd in "$RUNS"/*/weights; do
  [ -d "$wd" ] || continue
  run=$(basename "$(dirname "$wd")")
  if [ -f "$wd/last.pt" ] || [ -f "$wd/best.pt" ]; then echo "  OK   $run"; else echo "  경고 $run: last/best 없음"; fi
done
echo "== 추적 파일 무손실 확인 (비어 있어야 함)"; (cd "$ROOT" && git status --short | grep -v '^??' || true)
echo "완료"
