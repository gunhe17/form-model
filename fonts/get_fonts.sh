#!/bin/sh
# 한글 무료 글꼴 내려받기 + MANIFEST.json 생성 (생성기 v4 ②).
# 전부 SIL Open Font License 1.1 — 출처는 Google Fonts 저장소(google/fonts, ofl/).
# 큰 폰트 파일은 커밋하지 않는다(.gitignore). 재현은 이 스크립트로.
#   sh fonts/get_fonts.sh            # 없는 것만 받고 MANIFEST 갱신
#   sh fonts/get_fonts.sh --force    # 전부 다시 받기
set -u
DIR=$(cd "$(dirname "$0")" && pwd)
BASE="https://raw.githubusercontent.com/google/fonts/main/ofl"
FORCE=${1:-}

# 계열|글꼴이름|굵기|ofl 경로        (굵기 "100 900" = 가변 글꼴 범위)
LIST='
고딕|NotoSansKR|100 900|notosanskr/NotoSansKR[wght].ttf
고딕|GothicA1-Light|300|gothica1/GothicA1-Light.ttf
고딕|GothicA1|400|gothica1/GothicA1-Regular.ttf
고딕|GothicA1-Medium|500|gothica1/GothicA1-Medium.ttf
고딕|GothicA1-Bold|700|gothica1/GothicA1-Bold.ttf
고딕|GothicA1-Black|900|gothica1/GothicA1-Black.ttf
고딕|IBMPlexSansKR-Light|300|ibmplexsanskr/IBMPlexSansKR-Light.ttf
고딕|IBMPlexSansKR|400|ibmplexsanskr/IBMPlexSansKR-Regular.ttf
고딕|IBMPlexSansKR-Bold|700|ibmplexsanskr/IBMPlexSansKR-Bold.ttf
고딕|NanumGothicGF|400|nanumgothic/NanumGothic-Regular.ttf
고딕|NanumGothicCoding|400|nanumgothiccoding/NanumGothicCoding-Regular.ttf
고딕|Sunflower-Light|300|sunflower/Sunflower-Light.ttf
고딕|Sunflower|500|sunflower/Sunflower-Medium.ttf
고딕|Sunflower-Bold|700|sunflower/Sunflower-Bold.ttf
고딕|GowunDodum|400|gowundodum/GowunDodum-Regular.ttf
명조|NotoSerifKR|100 900|notoserifkr/NotoSerifKR[wght].ttf
명조|NanumMyeongjoGF|400|nanummyeongjo/NanumMyeongjo-Regular.ttf
명조|SongMyung|400|songmyung/SongMyung-Regular.ttf
명조|GowunBatang|400|gowunbatang/GowunBatang-Regular.ttf
명조|GowunBatang-Bold|700|gowunbatang/GowunBatang-Bold.ttf
명조|HahmletGF|100 900|hahmlet/Hahmlet[wght].ttf
명조|Diphylleia|400|diphylleia/Diphylleia-Regular.ttf
손글씨|NanumBrushScript|400|nanumbrushscript/NanumBrushScript-Regular.ttf
손글씨|NanumPenScript|400|nanumpenscript/NanumPenScript-Regular.ttf
손글씨|Gaegu-Light|300|gaegu/Gaegu-Light.ttf
손글씨|Gaegu|400|gaegu/Gaegu-Regular.ttf
손글씨|Gaegu-Bold|700|gaegu/Gaegu-Bold.ttf
손글씨|HiMelody|400|himelody/HiMelody-Regular.ttf
손글씨|GamjaFlower|400|gamjaflower/GamjaFlower-Regular.ttf
손글씨|PoorStory|400|poorstory/PoorStory-Regular.ttf
손글씨|Dokdo|400|dokdo/Dokdo-Regular.ttf
손글씨|EastSeaDokdo|400|eastseadokdo/EastSeaDokdo-Regular.ttf
손글씨|SingleDay|400|singleday/SingleDay-Regular.ttf
손글씨|KirangHaerang|400|kiranghaerang/KirangHaerang-Regular.ttf
손글씨|CuteFont|400|cutefont/CuteFont-Regular.ttf
장식|DoHyeon|400|dohyeon/DoHyeon-Regular.ttf
장식|Jua|400|jua/Jua-Regular.ttf
장식|BlackHanSans|400|blackhansans/BlackHanSans-Regular.ttf
장식|Gugi|400|gugi/Gugi-Regular.ttf
장식|Stylish|400|stylish/Stylish-Regular.ttf
장식|YeonSung|400|yeonsung/YeonSung-Regular.ttf
장식|MoiraiOne|400|moiraione/MoiraiOne-Regular.ttf
장식|BagelFatOne|400|bagelfatone/BagelFatOne-Regular.ttf
'

# 저장소에 이미 있는 5개(v1~v3 테마가 참조 — 지우지 말 것)
LEGACY='
명조|Hahmlet|100 900|Hahmlet.ttf
명조|NanumMyeongjo|400|NanumMyeongjo.ttf
명조|NanumMyeongjo-Bold|700|NanumMyeongjo-Bold.ttf
고딕|NanumDotum|400|NanumGothic.ttf
고딕|NanumDotum-Bold|700|NanumGothic-Bold.ttf
'

echo "$LIST" | while IFS='|' read -r fam name weight path; do
  [ -z "${path:-}" ] && continue
  file=$(basename "$path" | sed 's/\[wght\]/-VF/')
  if [ -n "$FORCE" ] || [ ! -s "$DIR/$file" ]; then
    curl -gsSfL --max-time 90 -o "$DIR/$file.part" "$BASE/$path" 2>/dev/null \
      && mv "$DIR/$file.part" "$DIR/$file" || { rm -f "$DIR/$file.part"; echo "  실패: $name ($path)" >&2; }
  fi
done

# MANIFEST: 실제로 존재하는 파일만 기록
{
echo '{'
echo ' "_": "한글 글꼴 풀 (생성기 v4). 전부 SIL OFL 1.1. 파일은 커밋하지 않음 — fonts/get_fonts.sh 로 재생성.",'
echo ' "fonts": ['
first=1
printf '%s%s' "$LEGACY" "$LIST" | while IFS='|' read -r fam name weight path; do
  [ -z "${path:-}" ] && continue
  case "$path" in */*) file=$(basename "$path" | sed 's/\[wght\]/-VF/'); src="$BASE/$path";;
                   *) file="$path"; src="google/fonts (OFL, 저장소 동봉)";; esac
  [ -s "$DIR/$file" ] || continue
  [ $first -eq 1 ] || printf ',\n'
  first=0
  printf '  {"name": "%s", "file": "%s", "family": "%s", "weight": "%s", "source": "%s"}' \
         "$name" "$file" "$fam" "$weight" "$src"
done
printf '\n ]\n}\n'
} > "$DIR/MANIFEST.json"

python3 - "$DIR/MANIFEST.json" <<'PY'
import json, sys, collections
m = json.load(open(sys.argv[1]))
c = collections.Counter(f["family"] for f in m["fonts"])
print(f'MANIFEST: {len(m["fonts"])}종 ' + " · ".join(f"{k} {v}" for k, v in sorted(c.items())))
PY
