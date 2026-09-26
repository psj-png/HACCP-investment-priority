# ═══════════════════════════════════════════════════════════════
# HACCP 투자 우선순위 — 시각화 전체 (20개 식품군)
# 입력: merged20.csv, scores20.csv, smaa_ranks_full.npy, smaa_ranks3_full.npy, smaa_cats.npy
# 출력: fig0, fig1, fig2, fig4, fig5, fig6, fig7
# ═══════════════════════════════════════════════════════════════
import csv, glob
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from matplotlib.patches import Patch

# ── 한글 폰트 ──
paths = glob.glob('/usr/share/fonts/truetype/nanum/*.ttf')
for fp in paths:
    fm.fontManager.addfont(fp)
names = sorted({fm.FontProperties(fname=fp).get_name() for fp in paths})
pick = next((n for n in names if n == 'NanumGothic'),
       next((n for n in names if 'Gothic' in n and 'Coding' not in n), 'DejaVu Sans'))
plt.rcParams['font.family'] = pick
plt.rcParams['axes.unicode_minus'] = False   # 유니코드 빼기 기호 비활성 (□ 방지)
print("폰트:", pick)

try:
    from adjustText import adjust_text
    HAS_ADJUST = True
except ImportError:
    HAS_ADJUST = False
    print("[안내] adjustText 미설치 — !pip install adjustText -q 권장 (fig4 라벨 겹침 방지)")

MERGED20 = "data/processed/merged20.csv"
SCORES20 = "data/processed/scores20.csv"

def num(r, k):
    v = r.get(k, "")
    try: return float(v) if str(v).strip() not in ("", "-") else None
    except ValueError: return None

def load(p):
    with open(p, encoding="utf-8-sig") as f: return list(csv.DictReader(f))

def short_name(c):
    return (c.replace("과자류, 빵류 또는 떡류", "과자·빵·떡류")
             .replace("코코아가공품류 또는 초콜릿류", "코코아·초콜릿")
             .replace("절임류 또는 조림류", "절임·조림류")
             .replace("두부류 또는 묵류", "두부·묵류")
             .replace("벌꿀 및 화분가공품류", "벌꿀")
             .replace("수산가공식품류", "수산가공")
             .replace("농산가공식품류", "농산가공")
             .replace("동물성가공식품류", "동물성가공")
             .replace("특수의료용도식품", "특수의료"))

def beta_shrink(rows):
    d = [(r["품목유형"], num(r,"검사건수"), num(r,"부적합건수"))
         for r in rows if num(r,"검사건수") and num(r,"부적합건수") is not None]
    tf = sum(f for _,_,f in d); ti = sum(i for _,i,_ in d); pm = tf/ti if ti else 0
    obs = [f/i for _,i,f in d]; nn=len(obs); mean=sum(obs)/nn
    var = sum((x-mean)**2 for x in obs)/nn if nn>1 else 0
    conc = max((mean*(1-mean)/var)-1, 1.0) if var>0 and 0<mean<1 else 100.0
    a, b = pm*conc, (1-pm)*conc
    return {nm:(f+a)/(i+a+b) for nm,i,f in d}, pm, a, b

merged, scores = load(MERGED20), load(SCORES20)
# fig1·2·5는 HIP 크기순으로 정렬 (막대 길이와 순서 일치)
scores_hip = sorted(scores, key=lambda r: -float(r["HIP_ref"]))
print(f"로드: merged20 {len(merged)}개 / scores20 {len(scores)}개")
print("상위 5:", [r["품목유형"] for r in scores[:5]], "\n")


# ═══════════════ fig0: EDA ═══════════════
def fig0():
    rows = merged
    fail = [(num(r,"부적합건수")/num(r,"검사건수")*100) if num(r,"검사건수") else None for r in rows]
    prod = [num(r,"생산액_천원") for r in rows]
    cert = [num(r,"HACCP_인증률")*100 if num(r,"HACCP_인증률") is not None else None for r in rows]
    recall = [((num(r,"Recall_1등급") or 0)*3 + (num(r,"Recall_2등급") or 0)*2
               + (num(r,"Recall_3등급") or 0)) for r in rows]
    fig, ax_ = plt.subplots(2, 3, figsize=(17, 9.5))
    a = ax_[0,0]; v=[x for x in fail if x is not None]
    a.hist(v, bins=12, color='#C0392B', alpha=.75, edgecolor='white')
    a.axvline(np.median(v), color='#34495E', ls='--', lw=1.3, label=f'중앙값 {np.median(v):.2f}%')
    a.annotate(f'최대 {max(v):.2f}%\n(극단값)', xy=(max(v),1), xytext=(max(v)*.6,4), fontsize=9,
               color='#922B21', arrowprops=dict(arrowstyle='->', color='#922B21', lw=1.2))
    a.set_xlabel("부적합률 (%)", fontsize=10); a.set_ylabel("식품군 수", fontsize=10)
    a.set_title("(1) 부적합률 — 극단값 존재", fontsize=11, fontweight='bold'); a.legend(fontsize=8.5)
    a = ax_[0,1]; pv=[p/1e8 for p in prod if p]
    a.hist(pv, bins=14, color='#E67E22', alpha=.75, edgecolor='white')
    a.set_xlabel("생산액 (억원)", fontsize=10); a.set_ylabel("식품군 수", fontsize=10)
    a.set_title(f"(2) 생산액 원본 — 최대/최소 {max(pv)/min(pv):.0f}배", fontsize=11, fontweight='bold')
    a.text(.97,.92,"대부분 좌측 집중\n→ 소수가 스케일 지배", transform=a.transAxes,
           ha='right', va='top', fontsize=9, color='#7E5109')
    a = ax_[0,2]; lv=[np.log10(p) for p in prod if p]
    a.hist(lv, bins=14, color='#27AE60', alpha=.75, edgecolor='white')
    a.set_xlabel("log10(생산액)", fontsize=10); a.set_ylabel("식품군 수", fontsize=10)
    a.set_title("(3) log 변환 후 — 고른 분포", fontsize=11, fontweight='bold')
    a.text(.03,.92,"편차 완화 →\n모든 식품군 반영", transform=a.transAxes,
           ha='left', va='top', fontsize=9, color='#1E8449')
    a = ax_[1,0]; cv=[x for x in cert if x is not None]
    a.hist(cv, bins=12, color='#2980B9', alpha=.75, edgecolor='white')
    a.axvline(np.median(cv), color='#34495E', ls='--', lw=1.3, label=f'중앙값 {np.median(cv):.1f}%')
    a.set_xlabel("HACCP 인증율 (%)", fontsize=10); a.set_ylabel("식품군 수", fontsize=10)
    a.set_title(f"(4) 인증율 — {min(cv):.0f}~{max(cv):.0f}% 분포", fontsize=11, fontweight='bold')
    a.legend(fontsize=8.5)
    a = ax_[1,1]
    a.hist(recall, bins=14, color='#8E44AD', alpha=.75, edgecolor='white')
    a.set_xlabel("등급가중 회수 점수", fontsize=10); a.set_ylabel("식품군 수", fontsize=10)
    a.set_title(f"(5) 회수 원본 — 최대 {max(recall):.0f} vs 다수 0", fontsize=11, fontweight='bold')
    a.text(.97,.92,"소수 돌출\n→ log 변환 필요", transform=a.transAxes,
           ha='right', va='top', fontsize=9, color='#6C3483')
    a = ax_[1,2]; rv=[np.log(x+1) for x in recall]
    a.hist(rv, bins=14, color='#27AE60', alpha=.75, edgecolor='white')
    a.set_xlabel("log(회수 점수 + 1)", fontsize=10); a.set_ylabel("식품군 수", fontsize=10)
    a.set_title("(6) log 변환 후 — 완화됨", fontsize=11, fontweight='bold')
    for a in ax_.flat:
        a.grid(alpha=.15); a.set_axisbelow(True)
        for sp in ['top','right']: a.spines[sp].set_visible(False)
    fig.suptitle("탐색적 데이터 분석 — 변수 분포와 변환 근거 (20개 식품군)",
                 fontsize=14, fontweight='bold', y=.99)
    plt.tight_layout(rect=[0,0,1,.95]); plt.savefig("fig0_eda.png", dpi=150, bbox_inches='tight')
    plt.show(); print("저장: fig0_eda.png")


# ═══════════════ fig1: HIP 순위 ═══════════════
def fig1():
    s = scores_hip
    cats = [short_name(r["품목유형"]) for r in s]
    hips = [float(r["HIP_ref"]) for r in s]
    cats_r, hips_r = cats[::-1], hips[::-1]
    n = len(cats_r)
    colors = ["#B03A2E" if (n-i)<=5 else ("#D98880" if (n-i)<=10 else "#AEB6BF") for i in range(n)]
    fig, ax = plt.subplots(figsize=(9, 8.5))
    ax.barh(range(n), hips_r, color=colors, height=.7)
    ax.set_yticks(range(n)); ax.set_yticklabels(cats_r, fontsize=10)
    for i, v in enumerate(hips_r): ax.text(v+.008, i, f"{v:.3f}", va='center', fontsize=9, color='#333')
    ax.axhline(y=n-5.5, color='#B03A2E', ls='--', lw=1.2, alpha=.6)
    ax.set_xlabel("HIP (참고 기준: 등급 3:2:1·동일가중)", fontsize=11)
    ax.set_title("식품군별 HACCP 투자 우선순위 지수 (20개)", fontsize=13, fontweight='bold', pad=12)
    ax.set_xlim(0, max(hips)*1.13); ax.grid(axis='x', alpha=.25); ax.set_axisbelow(True)
    ax.legend(handles=[Patch(facecolor="#B03A2E", label="상위 5"),
                       Patch(facecolor="#D98880", label="6–10"),
                       Patch(facecolor="#AEB6BF", label="11위 이하")],
              loc='lower right', fontsize=9, framealpha=.95)
    for sp in ['top','right']: ax.spines[sp].set_visible(False)
    plt.tight_layout(); plt.savefig("fig1_ranking.png", dpi=150, bbox_inches='tight')
    plt.show(); print("저장: fig1_ranking.png")


# ═══════════════ fig2: 4변수 구성 ═══════════════
def fig2():
    s = scores_hip
    cats = [short_name(r["품목유형"]) for r in s][::-1]
    R = [float(r["Risk"])*.25 for r in s][::-1]
    S = [float(r["Scale"])*.25 for r in s][::-1]
    V = [float(r["적용공백"])*.25 for r in s][::-1]
    I = [float(r["Impact"])*.25 for r in s][::-1]
    n = len(cats)
    fig, ax = plt.subplots(figsize=(10, 8.5)); left = np.zeros(n)
    for arr, c, lab in [(R,"#C0392B","위험도 (Risk)"), (S,"#E67E22","규모 (Scale)"),
                        (V,"#2980B9","적용공백"), (I,"#27AE60","사고 (Impact)")]:
        ax.barh(range(n), arr, left=left, color=c, label=lab, height=.72); left += np.array(arr)
    ax.set_yticks(range(n)); ax.set_yticklabels(cats, fontsize=10)
    ax.set_xlabel("HIP 기여도 (변수별 × 0.25)", fontsize=11)
    ax.set_title("식품군별 HIP 구성 — 어떤 변수가 우선순위를 이끄는가", fontsize=13, fontweight='bold', pad=12)
    ax.legend(loc='lower right', fontsize=9, framealpha=.95, ncol=2)
    ax.grid(axis='x', alpha=.25); ax.set_axisbelow(True)
    for sp in ['top','right']: ax.spines[sp].set_visible(False)
    plt.tight_layout(); plt.savefig("fig2_composition.png", dpi=150, bbox_inches='tight')
    plt.show(); print("저장: fig2_composition.png")


# ═══════════════ fig4: 적용공백 × 부적합률 (중앙값 십자선) ═══════════════
def fig4():
    cats = [r["품목유형"] for r in scores]
    gap = [float(r["적용공백"]) for r in scores]
    risk = [float(r["Risk"]) for r in scores]
    recall = [int(float(r["회수건수"])) for r in scores]
    gm, rm, cm = np.median(gap), np.median(risk), np.median(recall)
    sizes = [40 + rc*11 for rc in recall]

    fig, ax = plt.subplots(figsize=(11.5, 9))
    xlo, xhi, ylo, yhi = -.10, 1.16, -.10, 1.14

    # 중앙값 십자선만 (배경 채색 없음)
    ax.axhline(rm, color='#5D6D7E', ls='--', lw=1, alpha=.8, zorder=1)
    ax.axvline(gm, color='#5D6D7E', ls='--', lw=1, alpha=.8, zorder=1)

    ax.scatter(gap, risk, s=sizes, facecolor='#5D8AA8', alpha=.55,
               edgecolors='#2C3E50', linewidths=.9, zorder=3)

    texts = [ax.text(gap[i], risk[i], short_name(c), fontsize=8.5, color='#212F3D', zorder=5)
             for i, c in enumerate(cats)]
    if HAS_ADJUST:
        adjust_text(texts, ax=ax, arrowprops=dict(arrowstyle='-', color='#909497', lw=.6),
                    expand_points=(1.5, 1.5))

    # 사분면 이름만 (짧게, 회색)
    for lab, x, y, ha, va in [("Ⅰ", xhi-.02, yhi-.02, 'right', 'top'),
                              ("Ⅱ", xhi-.02, ylo+.02, 'right', 'bottom'),
                              ("Ⅲ", xlo+.02, yhi-.02, 'left', 'top'),
                              ("Ⅳ", xlo+.02, ylo+.02, 'left', 'bottom')]:
        ax.text(x, y, lab, ha=ha, va=va, fontsize=13, color='#95A5A6',
                fontweight='bold', zorder=6)

    ax.text(gm+.01, yhi-.015, f"중앙값 {gm:.2f}", ha='left', va='top',
            fontsize=8, color='#5D6D7E', style='italic', rotation=90)
    ax.text(xlo+.01, rm+.01, f"중앙값 {rm:.2f}", ha='left', va='bottom',
            fontsize=8, color='#5D6D7E', style='italic')

    ax.set_xlim(xlo, xhi); ax.set_ylim(ylo, yhi)
    ax.set_xlabel("적용공백  (1 - HACCP 인증률, 정규화)", fontsize=11)
    ax.set_ylabel("검사상 부적합 발생 수준  (Risk, 정규화)", fontsize=11)
    ax.set_title("HACCP 적용공백 × 검사상 부적합 발생 수준 (20개 식품군)\n"
                 f"기준선 = 각 축 중앙값 · 원 크기 = 회수 건수(중앙값 {cm:.0f}건)",
                 fontsize=12.5, fontweight='bold', pad=13)
    ax.grid(alpha=.12, zorder=0)
    for sp in ['top','right']: ax.spines[sp].set_visible(False)
    ax.text(.5, -.10,
            "※ 본 분류는 식품군 단위의 HACCP 인증 수준과 검사상 부적합 발생 수준을 활용한 1차 선별 결과이며,\n"
            "HACCP 운영 적정성 또는 개별 업체의 안전관리 수준을 직접 평가하는 것은 아님",
            transform=ax.transAxes, ha='center', fontsize=8.3, color='#566573', linespacing=1.5)
    plt.tight_layout(); plt.savefig("fig4_2x2.png", dpi=150, bbox_inches='tight')
    plt.show()

    # 사분면 배정은 콘솔로 (보고서 본문·표에 사용)
    print(f"\n기준선 — 적용공백 {gm:.3f} / 부적합률 {rm:.3f} / 회수 {cm:.0f}건")
    q = {"Ⅰ":[], "Ⅱ":[], "Ⅲ":[], "Ⅳ":[]}
    for i, c in enumerate(cats):
        hg, hr = gap[i] >= gm, risk[i] >= rm
        key = "Ⅰ" if (hg and hr) else "Ⅱ" if hg else "Ⅲ" if hr else "Ⅳ"
        q[key].append(short_name(c) + (" *" if recall[i] >= cm else ""))
    nm = {"Ⅰ": "적용공백 큼 + 부적합 높음 → 우선 지원·관리 검토",
          "Ⅱ": "적용공백 큼 + 부적합 낮음 → 현황 모니터링",
          "Ⅲ": "적용공백 작음 + 부적합 높음 → 운영·관리 실효성 추가 점검",
          "Ⅳ": "적용공백 작음 + 부적합 낮음 → 현 수준 유지·지속 모니터링"}
    for k in ["Ⅰ","Ⅱ","Ⅲ","Ⅳ"]:
        print(f"\n  {k}. {nm[k]}\n     {', '.join(q[k])}")
    print("\n  * 회수 건수 중앙값 이상")


# ═══════════════ fig5: 예산 배분 ═══════════════
def fig5():
    s = scores_hip
    cats = [short_name(r["품목유형"]) for r in s]
    hips = np.array([float(r["HIP_ref"]) for r in s])
    n = len(cats); T = 100.0
    eq = np.full(n, T/n); hp = T*hips/hips.sum(); df = hp-eq
    cr, er, hr, dr = cats[::-1], eq[::-1], hp[::-1], df[::-1]; y = np.arange(n)
    fig, axes = plt.subplots(1, 2, figsize=(16, 8.5), gridspec_kw={'width_ratios':[1.25,1]})
    ax = axes[0]; h=.38
    ax.barh(y-h/2, er, height=h, color='#AEB6BF', label='균등 배분 (비교 기준)')
    ax.barh(y+h/2, hr, height=h, color='#B03A2E', label='HIP 기반 차등 배분 (제안)')
    ax.set_yticks(y); ax.set_yticklabels(cr, fontsize=9)
    ax.axvline(T/n, color='#566573', ls=':', lw=1.2, alpha=.8)
    ax.text(T/n, n-.3, f' 균등선 {T/n:.1f}', fontsize=8, color='#566573', va='bottom', style='italic')
    ax.set_xlabel("배분 예산 (총 100 기준)", fontsize=10.5)
    ax.set_title("(A) 배분 방식별 예산 비교", fontsize=12, fontweight='bold', pad=10)
    ax.legend(loc='lower right', fontsize=9, framealpha=.95)
    ax.grid(axis='x', alpha=.2); ax.set_axisbelow(True)
    for sp in ['top','right']: ax.spines[sp].set_visible(False)
    a2 = axes[1]
    a2.barh(y, dr, height=.66, color=['#B03A2E' if d>0 else '#5D8AA8' for d in dr])
    a2.set_yticks(y); a2.set_yticklabels([]); a2.axvline(0, color='#34495E', lw=1.1)
    for i, d in enumerate(dr):
        a2.text(d+(.09 if d>0 else -.09), i, f"{d:+.1f}", va='center',
                ha='left' if d>0 else 'right', fontsize=8.5, color='#2C3E50')
    a2.set_xlabel("균등 배분 대비 증감", fontsize=10.5)
    a2.set_title("(B) 재배분 효과 — 어디로 옮겨가는가", fontsize=12, fontweight='bold', pad=10)
    lim = max(abs(df))*1.35; a2.set_xlim(-lim, lim)
    a2.grid(axis='x', alpha=.2); a2.set_axisbelow(True)
    for sp in ['top','right','left']: a2.spines[sp].set_visible(False)
    g = df[df>0].sum()
    a2.text(lim*.95, -.9, f"상위군으로 이동: +{g:.1f}", ha='right', va='top',
            fontsize=9.5, color='#B03A2E', fontweight='bold')
    fig.suptitle("HACCP 예산 배분 시뮬레이션 — 균등 vs 우선순위 기반 차등 (20개)",
                 fontsize=13.5, fontweight='bold', y=.98)
    plt.tight_layout(rect=[0,0,1,.95]); plt.savefig("fig5_budget.png", dpi=150, bbox_inches='tight')
    plt.show(); print(f"저장: fig5_budget.png (재배분 {g:.1f}%)")


# ═══════════════ fig6: 베타-이항 보정 ═══════════════
def fig6():
    rows = merged
    d = [(r["품목유형"], num(r,"검사건수"), num(r,"부적합건수"))
         for r in rows if num(r,"검사건수") and num(r,"부적합건수") is not None]
    _, pm, a, b = beta_shrink(rows)
    nmz = [x[0] for x in d]; insp = np.array([x[1] for x in d])
    raw = np.array([x[2]/x[1]*100 for x in d]); adj = np.array([(x[2]+a)/(x[1]+a+b)*100 for x in d])
    fig, ax = plt.subplots(figsize=(12, 8))
    for i in range(len(nmz)):
        s = abs(raw[i]-adj[i])
        c = '#C0392B' if s>.3 else ('#E67E22' if s>.05 else '#95A5A6')
        ax.annotate('', xy=(insp[i],adj[i]), xytext=(insp[i],raw[i]),
                    arrowprops=dict(arrowstyle='->', color=c, lw=1.6, alpha=.8))
    ax.scatter(insp, raw, s=70, c='#BDC3C7', edgecolors='#7F8C8D', linewidths=1, label='원본 부적합률', zorder=3)
    ax.scatter(insp, adj, s=70, c='#C0392B', edgecolors='white', linewidths=1, label='보정 후 (베타-이항 축소)', zorder=3)
    ax.axhline(pm*100, color='#34495E', ls=':', lw=1.3, label=f'전체 평균 {pm*100:.2f}% (축소 목표점)')
    for i, x in enumerate(nmz):
        if abs(raw[i]-adj[i])>.2 or insp[i]>6000:
            ax.annotate(short_name(x), (insp[i],raw[i]), fontsize=9,
                        xytext=(7,4), textcoords='offset points', color='#2C3E50')
    ax.set_xscale('log')
    ax.set_xlabel("검사 건수 (log scale)", fontsize=11); ax.set_ylabel("부적합률 (%)", fontsize=11)
    ax.set_title("베타-이항 축소 효과 — 소표본 편향 보정\n검사 건수가 적을수록 전체 평균 쪽으로 크게 축소",
                 fontsize=13, fontweight='bold', pad=12)
    ax.legend(fontsize=9.5, loc='upper right'); ax.grid(alpha=.18); ax.set_axisbelow(True)
    for sp in ['top','right']: ax.spines[sp].set_visible(False)
    ax.text(.02,.97, f"알파={a:.3f}, 베타={b:.1f}  (적률법 추정)\n→ 검사 약 {a+b:.0f}건 이상부터 관측값 신뢰",
            transform=ax.transAxes, va='top', fontsize=9, color='#566573',
            bbox=dict(boxstyle='round,pad=0.5', facecolor='#F8F9F9', edgecolor='#D5DBDB'))
    plt.tight_layout(); plt.savefig("fig6_shrinkage.png", dpi=150, bbox_inches='tight')
    plt.show(); print("저장: fig6_shrinkage.png")


# ═══════════════ fig7: SMAA 분포 + 강건성 ═══════════════
def fig7():
    r4 = np.load("data/processed/smaa_ranks_full.npy")
    r3 = np.load("data/processed/smaa_ranks3_full.npy")
    cats = np.load("data/processed/smaa_cats.npy", allow_pickle=True)
    m4 = np.median(r4, axis=0); m3 = np.median(r3, axis=0)
    order = np.argsort(m4)[::-1]
    cats_o = [short_name(cats[i]) for i in order]
    data = [r4[:,i] for i in order]; n = len(cats_o)
    fig, axes = plt.subplots(1, 2, figsize=(16, 9), gridspec_kw={'width_ratios':[1.4,1]})
    ax = axes[0]
    bp = ax.boxplot(data, vert=False, widths=.6, patch_artist=True, showfliers=False,
                    medianprops=dict(color='#1C2833', linewidth=1.5))
    for i, p in enumerate(bp['boxes']):
        m = m4[order[i]]
        p.set_facecolor("#B03A2E" if m<=5 else ("#E59866" if m<=10 else "#AEB6BF")); p.set_alpha(.75)
    for w in bp['whiskers']: w.set(color='#7B7D7D', linewidth=1)
    for c in bp['caps']: c.set(color='#7B7D7D', linewidth=1)
    ax.set_yticks(range(1,n+1)); ax.set_yticklabels(cats_o, fontsize=9)
    ax.set_xlabel("순위 분포 (SMAA 1만 회, 1=최우선)", fontsize=10.5)
    ax.set_title("(A) SMAA 순위 분포 — 가중치 무작위 1만 회\n박스=사분위 범위 (좁을수록 안정)",
                 fontsize=12, fontweight='bold', pad=10)
    ax.axvline(5.5, color='#B03A2E', ls='--', lw=1, alpha=.5)
    ax.text(5.5, n+.4, ' 상위 5 경계', color='#B03A2E', fontsize=8, va='bottom')
    ax.set_xlim(0,n+1); ax.grid(axis='x', alpha=.2); ax.set_axisbelow(True)
    for sp in ['top','right']: ax.spines[sp].set_visible(False)
    a2 = axes[1]; y = np.arange(1,n+1)
    v4 = [m4[i] for i in order]; v3 = [m3[i] for i in order]
    for i in range(n):
        d = v3[i]-v4[i]
        col = '#5D8AA8' if abs(d)<=2 else ('#C0392B' if d>2 else '#E67E22')
        a2.plot([v4[i],v3[i]], [y[i],y[i]], color=col, lw=1.5, alpha=.7, zorder=2)
    a2.scatter(v4, y, s=45, color='#2C3E50', label='4변수 (적용공백 포함)', zorder=3)
    a2.scatter(v3, y, s=45, facecolors='white', edgecolors='#7B7D7D', linewidths=1.3,
               label='3변수 (적용공백 제외)', zorder=3)
    a2.set_yticks(range(1,n+1)); a2.set_yticklabels([])
    a2.set_xlabel("중앙 순위", fontsize=10.5)
    a2.set_title("(B) 적용공백 제외 시 순위 변화\n선이 길수록 적용공백 의존 큼",
                 fontsize=12, fontweight='bold', pad=10)
    a2.legend(loc='lower right', fontsize=8.5, framealpha=.95)
    a2.set_xlim(0,n+1); a2.grid(axis='x', alpha=.2); a2.set_axisbelow(True)
    for sp in ['top','right','left']: a2.spines[sp].set_visible(False)
    fig.suptitle("SMAA 강건성 — 순위 안정성과 적용공백 의존도 (20개)",
                 fontsize=13.5, fontweight='bold', y=.99)
    plt.tight_layout(rect=[0,0,1,.95]); plt.savefig("fig7_smaa.png", dpi=150, bbox_inches='tight')
    plt.show(); print("저장: fig7_smaa.png")


for f in [fig0, fig1, fig2, fig4, fig5, fig6, fig7]:
    f()
print("\n완료 — fig0, fig1, fig2, fig4, fig5, fig6, fig7")
