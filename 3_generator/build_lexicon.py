"""1_corpus/ocr_cache/*.json → 2_spec/lexicon_real.json (실서식 어휘 사전).

생성기 v4 ③ 어휘 주입용. 뜻이 맞을 필요는 없다 — 길이·빈도 분포만 실서식을 덮으면 된다(DDR 2105.14931).
  python3 3_generator/build_lexicon.py          # 기본 경로
"""
import json, glob, re, collections, argparse, os

HAN = r'가-힣'
KEEP = re.compile(r'^[' + HAN + r'A-Za-z0-9()·\-/,~:%\s]+$')
NOISE = re.compile(r'^[\s\W_]*$')
UNIT = re.compile(r'^[0-9○]{1,4}\s?(원|명|세|년|월|일|시간|분|회|점|개|건|매|부|%|km|m|kg|cm)$')
SENT_END = re.compile(r'(다|음|함|요|오|까)[.?]?$')
STRIP = '[](){}〈〉<>「」『』·.,:;※□■○●◎-–—_* \t'

def norm(s):
    s = re.sub(r'\s+', ' ', s.replace(' ', ' ')).strip(STRIP)
    return s.strip()

def build(cache_dir, min_conf=0.5):
    labels, phrases, units = collections.Counter(), collections.Counter(), collections.Counter()
    for f in sorted(glob.glob(os.path.join(cache_dir, '*.json'))):
        for it in json.load(open(f)):
            if it.get('conf', 0) < min_conf: continue
            t = norm(it.get('text', ''))
            if not t or NOISE.match(t) or not KEEP.match(t): continue
            han = len(re.findall('[' + HAN + ']', t))
            if UNIT.match(t): units[t] += 1; continue
            if han < 2: continue
            n = len(t)
            if n <= 8 and ' ' not in t:
                labels[t] += 1                       # 라벨 후보: 2~8자 명사구
            elif 6 <= n <= 40 and han / n >= 0.5:
                # 문장 조각(서술) vs 공백 포함 머리말
                (phrases if (SENT_END.search(t) or n >= 14) else labels)[t] += 1
            for w in t.split(' '):                   # 어절도 라벨 후보로 (실서식 라벨은 대개 한 어절)
                w = norm(w)
                if 2 <= len(w) <= 8 and len(re.findall('[' + HAN + ']', w)) >= 2: labels[w] += 1
    return labels, phrases, units

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--cache', default='1_corpus/ocr_cache')
    ap.add_argument('--out', default='2_spec/lexicon_real.json')
    ap.add_argument('--min-conf', type=float, default=0.5)
    a = ap.parse_args()
    labels, phrases, units = build(a.cache, a.min_conf)
    by_len = collections.Counter(len(w) for w in labels)
    doc = {"_": "1_corpus/ocr_cache 에서 추출한 실서식 어휘. 3_generator/build_lexicon.py 로 재생성.",
           "labels": labels.most_common(), "phrases": phrases.most_common(), "units": units.most_common(),
           "label_len_hist": sorted(by_len.items())}
    json.dump(doc, open(a.out, 'w'), ensure_ascii=False, indent=0)
    print(f"라벨 {len(labels)} · 문장조각 {len(phrases)} · 수량표현 {len(units)} → {a.out}")
    print("라벨 길이 분포:", dict(sorted(by_len.items())))
    print("라벨 상위:", [w for w, _ in labels.most_common(12)])
    print("문장 예:", [w for w, _ in phrases.most_common(3)])
