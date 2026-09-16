"""복제본 GT 를 원본 스캔 좌표로 옮긴다 — 가로 괘선 위치를 단조 정합해 세로축 조각선형 사상.
폭은 두 집합 모두 1004 로 같으므로 x 는 그대로 두고 y 만 옮긴다. 검출기와 무관(픽셀만 사용)."""
import numpy as np, json, sys
from PIL import Image

def rules(path, thr=0.40, minw=3):
    im=np.asarray(Image.open(path).convert('L'),dtype=np.float32)
    d=(255-im).mean(1); m=d.max()
    idx=np.where(d>m*thr)[0]
    g=[]
    for i in idx:
        if not g or i-g[-1][-1]>minw: g.append([i])
        else: g[-1].append(i)
    return np.array([float(np.mean(x)) for x in g]), im.shape[0]

def match(a, b, tol=0.25):
    """단조 정합: DP 로 a[i]↔b[j] 대응을 찾되 건너뜀 허용. 비용 = |정규화 위치 차|."""
    A,B=len(a),len(b)
    if A==0 or B==0: return []
    na,nb=a/a[-1], b/b[-1]
    INF=1e9; D=np.full((A+1,B+1),INF); D[0,0]=0; P={}
    for i in range(A+1):
        for j in range(B+1):
            if D[i,j]>=INF: continue
            if i<A and j<B:
                c=abs(na[i]-nb[j])
                if c<tol and D[i,j]+c<D[i+1,j+1]: D[i+1,j+1]=D[i,j]+c; P[(i+1,j+1)]=(i,j,True)
            if i<A and D[i,j]+0.02<D[i+1,j]: D[i+1,j]=D[i,j]+0.02; P[(i+1,j)]=(i,j,False)
            if j<B and D[i,j]+0.02<D[i,j+1]: D[i,j+1]=D[i,j]+0.02; P[(i,j+1)]=(i,j,False)
    i,j=A,B; out=[]
    while (i,j)!=(0,0):
        pi,pj,keep=P.get((i,j),(max(i-1,0),max(j-1,0),False))
        if keep: out.append((pi,pj))
        i,j=pi,pj
    return out[::-1]

def ymap(stem, orig_dir='1_corpus/pages', rep_dir='4_replica/render'):
    ro,Ho=rules(f'{orig_dir}/{stem}.png'); rr,Hr=rules(f'{rep_dir}/{stem}.png')
    pairs=match(ro,rr)
    if len(pairs)<3: return None,None,None
    xs=np.array([rr[j] for _,j in pairs]); ys=np.array([ro[i] for i,_ in pairs])   # 복제 y → 원본 y
    k=np.argsort(xs); xs,ys=xs[k],ys[k]
    keep=np.concatenate(([True], np.diff(xs)>1)); xs,ys=xs[keep],ys[keep]
    # 양 끝 선형 외삽용 기울기
    def f(y):
        return np.interp(y, xs, ys, left=ys[0]+(y-xs[0])*(ys[1]-ys[0])/max(xs[1]-xs[0],1) if len(xs)>1 else ys[0],
                                    right=ys[-1]+(y-xs[-1])*(ys[-1]-ys[-2])/max(xs[-1]-xs[-2],1) if len(xs)>1 else ys[-1])
    return f, (xs,ys), (Ho,Hr)

def residual(stem):
    """정합 품질: 대응된 괘선의 사상 후 잔차(leave-one-out)."""
    ro,Ho=rules(f'1_corpus/pages/{stem}.png'); rr,Hr=rules(f'4_replica/render/{stem}.png')
    pairs=match(ro,rr)
    if len(pairs)<4: return None
    xs=np.array([rr[j] for _,j in pairs],float); ys=np.array([ro[i] for i,_ in pairs],float)
    k=np.argsort(xs); xs,ys=xs[k],ys[k]
    res=[]
    for t in range(1,len(xs)-1):
        m=np.ones(len(xs),bool); m[t]=False
        res.append(abs(np.interp(xs[t], xs[m], ys[m])-ys[t]))
    return np.array(res), len(pairs), len(ro), len(rr)

if __name__=='__main__':
    import glob, os
    stems=[os.path.basename(p)[:-4] for p in sorted(glob.glob('1_corpus/pages/*.png'))]
    allr=[]
    for s in stems:
        if not os.path.exists(f'4_replica/render/{s}.png'): continue
        r=residual(s)
        if r is None: print(f"  {s[:34]:36s} 괘선 부족"); continue
        res,np_,no,nr=r; allr.append(res)
        print(f"  {s[:34]:36s} 대응 {np_:3d}/{no:3d}·{nr:3d}  잔차 중위 {np.median(res):5.1f}px  90% {np.percentile(res,90):5.1f}px")
    if allr:
        a=np.concatenate(allr); print(f"\n전체: 잔차 중위 {np.median(a):.2f}px · 90분위 {np.percentile(a,90):.2f}px · ≤3px 비율 {100*(a<=3).mean():.1f}%")
