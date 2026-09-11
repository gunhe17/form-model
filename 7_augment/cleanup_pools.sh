#!/bin/sh
# 종료된 라운드의 증강 풀만 지운다 — 딱 아래 세 경로. 다른 것은 어떤 경우에도 건드리지 않는다.
#   7_augment/pool        1·2차(11종) 풀  ≈ 9.9G   재생성: 7_augment/README '2차' 절 (build_pool.sh 기본 인자)
#   7_augment/pool_s1     3차(v2) 풀      ≈ 11G    재생성: README '3차' 절 (Y=yolo_s1 POOL=pool_s1 RS=render_swap_v2 S1=1)
#   7_augment/pool_s1v3   4차(v3) 풀      ≈ 11G    재생성: README '4차' 절 (Y=yolo_s1v3 POOL=pool_s1v3 RS=render_swap_v3 S1=1)
# 안전장치(하나라도 실패하면 아무것도 지우지 않고 종료):
#   G1 저장소 루트(/work 또는 git 루트)를 realpath 로 고정하고, 대상은 그 아래의 고정 상대경로만
#   G2 대상이 디렉터리이고 git 이 무시하는 경로(git check-ignore)일 것 — 추적 파일은 절대 대상이 아님
#   G3 대상과 루트의 디바이스 번호가 같을 것(안에 다른 마운트가 끼어 있지 않음)
#   G4 대상 안의 심볼릭 링크가 루트 밖을 가리키지 않을 것(rm -r 은 링크를 따라가지 않지만 목록으로 확인)
#   G5 현재 학습 데이터 정의(forms_s1v4.yaml)가 대상을 참조하지 않을 것
#   삭제는 rm -rf --one-file-system 을 ionice/nice 로 한 경로씩. 기본은 dry-run, 실제 삭제는 --yes.
# 사용:  sh 7_augment/cleanup_pools.sh          # 검사 + 목록만
#        sh 7_augment/cleanup_pools.sh --yes    # 검사 통과 시 삭제
set -u
ROOT=$(cd "$(dirname "$0")/.." && pwd -P)
TARGETS="7_augment/pool 7_augment/pool_s1 7_augment/pool_s1v3"
YES=${1:-}
fail() { echo "중단: $*" >&2; exit 1; }

echo "루트: $ROOT"
[ -d "$ROOT/.git" ] || fail "저장소 루트가 아님 ($ROOT)"
dev() { stat -c %d "$1" 2>/dev/null || stat -f %d "$1"; }   # Linux / macOS
ROOTDEV=$(dev "$ROOT")
echo "== 검사"
for t in $TARGETS; do
  p="$ROOT/$t"
  [ -e "$p" ] || { echo "  $t: 없음(건너뜀)"; continue; }
  rp=$(realpath "$p")
  case "$rp" in "$ROOT"/*) ;; *) fail "G1 $t 가 루트 밖을 가리킴: $rp";; esac
  [ -d "$rp" ] && [ ! -L "$p" ] || fail "G1 $t 가 디렉터리가 아님(링크?)"
  (cd "$ROOT" && git check-ignore -q "$t") || fail "G2 $t 는 git 이 무시하는 경로가 아님 — 추적 파일 포함 가능"
  n_tracked=$(cd "$ROOT" && git ls-files "$t" | wc -l)
  [ "$n_tracked" -eq 0 ] || fail "G2 $t 안에 추적 파일 $n_tracked 개"
  [ -n "$ROOTDEV" ] && [ "$(dev "$rp")" = "$ROOTDEV" ] || fail "G3 $t 디바이스가 루트와 다름"
  bad=0
  for l in $(find "$rp" -type l 2>/dev/null); do
    lt=$(readlink -f "$l"); case "$lt" in "$ROOT"/*) ;; *) echo "  G4 밖을 가리키는 링크: $l -> $lt"; bad=1;; esac
  done
  [ "$bad" -eq 0 ] || fail "G4 $t 안에 루트 밖 링크"
  grep -q "$(basename "$t")/" "$ROOT/8_train/forms_s1v4.yaml" && fail "G5 $t 를 현재 학습 yaml 이 참조"
  echo "  $t: OK  $(du -sh "$rp" 2>/dev/null | cut -f1)  파일 $(find "$rp" -type f | wc -l)"
done
echo "== 여유(전)"; df -h "$ROOT" | tail -1
if [ "$YES" != "--yes" ]; then echo "dry-run — 삭제하지 않음. 실제 삭제는 --yes"; exit 0; fi
echo "== 삭제"
for t in $TARGETS; do
  p="$ROOT/$t"; [ -d "$p" ] || continue
  ionice -c3 nice -n19 rm -rf --one-file-system "$p" && echo "  삭제됨: $t"
done
echo "== 여유(후)"; df -h "$ROOT" | tail -1
echo "== 추적 파일 무손실 확인 (비어 있어야 함)"; (cd "$ROOT" && git status --short | grep -v '^??' || true)
echo "완료"
