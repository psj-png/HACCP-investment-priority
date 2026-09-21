"""
4단계: 시각화 (7종)
============================================
입력: data/processed/merged.csv, data/processed/scores.csv
출력: fig0_eda.png ~ fig6_shrinkage.png

fig0: EDA (변수 분포 + log 변환 근거)
fig1: HIP 순위 바차트
fig2: 4변수 누적막대 (HIP 구성)
fig3: 민감도 히트맵
fig4: 위험-규모 매트릭스 (0.5 / 중앙값 병치)
fig5: 예산 배분 시뮬레이션
fig6: 베타-이항 보정 효과

* 코랩 실행 시 한글 폰트 설정 필요:
    !apt-get install -y fonts-nanum -qq
    import matplotlib.font_manager as fm, glob
    for fp in glob.glob('/usr/share/fonts/truetype/nanum/*.ttf'):
        fm.fontManager.addfont(fp)
    plt.rcParams['font.family'] = 'NanumGothic'
    plt.rcParams['axes.unicode_minus'] = False
"""

import csv
import math
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from matplotlib.lines import Line2D

MERGED = "data/processed/merged.csv"
SCORES = "data/processed/scores.csv"
IMPACT_VERSIONS = ["Impact_321", "Impact_2_15_1", "Impact_531", "Impact_111"]


def num(r, k):
    v = r.get(k, "")
    try:
        return float(v) if str(v).strip() not in ("", "-") else None
    except ValueError:
        return None


def load(path):
    with open(path, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


# ═══════════════════════════════════════════════════
# 공통: 베타-이항 축소 + 정규화 (민감도 재계산용)
# ═══════════════════════════════════════════════════
def beta_shrink(rows):
    data = [(r["품목유형"], num(r, "검사건수"), num(r, "부적합건수"))
            for r in rows if num(r, "검사건수") and num(r, "부적합건수") is not None]
    tf = sum(f for _, _, f in data); ti = sum(i for _, i, _ in data)
    pm = tf / ti if ti else 0
    obs = [f / i for _, i, f in data]; nn = len(obs); mean = sum(obs) / nn
    var = sum((x - mean) ** 2 for x in obs) / nn if nn > 1 else 0
    conc = max((mean * (1 - mean) / var) - 1, 1.0) if var > 0 and 0 < mean < 1 else 100.0
    a, b = pm * conc, (1 - pm) * conc
    return {nm: (f + a) / (i + a + b) for nm, i, f in data}, pm, a, b


def minmax(vals):
    valid = [v for v in vals if v is not None]
    if not valid:
        return vals
    lo, hi = min(valid), max(valid)
    if hi == lo:
        return [0.5 if v is not None else None for v in vals]
    return [(v - lo) / (hi - lo) if v is not None else None for v in vals]


# ═══════════════════════════════════════════════════
# fig0: EDA
# ═══════════════════════════════════════════════════
def fig0_eda(rows):
    fail = [(num(r, "부적합건수") / num(r, "검사건수") * 100) if num(r, "검사건수") else None for r in rows]
    prod = [num(r, "생산액_천원") for r in rows]
    cert = [num(r, "HACCP_인증률") * 100 if num(r, "HACCP_인증률") is not None else None for r in rows]
    recall = [num(r, "Impact_321") or 0 for r in rows]

    fig, axes = plt.subplots(2, 3, figsize=(17, 9.5))

    ax = axes[0, 0]
    v = [x for x in fail if x is not None]
    ax.hist(v, bins=12, color='#C0392B', alpha=0.75, edgecolor='white')
    ax.axvline(np.median(v), color='#34495E', ls='--', lw=1.3, label=f'중앙값 {np.median(v):.2f}%')
    ax.annotate(f'빙과류 {max(v):.2f}%\n(단일 극단값)', xy=(max(v), 1), xytext=(max(v)*0.62, 5),
                fontsize=9, color='#922B21', arrowprops=dict(arrowstyle='->', color='#922B21', lw=1.2))
    ax.set_xlabel("부적합률 (%)", fontsize=10); ax.set_ylabel("식품군 수", fontsize=10)
    ax.set_title("(1) 부적합률 — 극단값 존재", fontsize=11, fontweight='bold'); ax.legend(fontsize=8.5)

    ax = axes[0, 1]
    pv = [p/1e8 for p in prod if p]
    ax.hist(pv, bins=14, color='#E67E22', alpha=0.75, edgecolor='white')
    ax.set_xlabel("생산액 (억원)", fontsize=10); ax.set_ylabel("식품군 수", fontsize=10)
    ax.set_title(f"(2) 생산액 원본 — 최대/최소 {max(pv)/min(pv):.0f}배", fontsize=11, fontweight='bold')
    ax.text(0.97, 0.92, "대부분 좌측 집중\n→ 소수가 스케일 지배", transform=ax.transAxes,
            ha='right', va='top', fontsize=9, color='#7E5109')

    ax = axes[0, 2]
    lv = [np.log10(p) for p in prod if p]
    ax.hist(lv, bins=14, color='#27AE60', alpha=0.75, edgecolor='white')
    ax.set_xlabel("log10(생산액)", fontsize=10); ax.set_ylabel("식품군 수", fontsize=10)
    ax.set_title("(3) log 변환 후 — 고른 분포", fontsize=11, fontweight='bold')
    ax.text(0.03, 0.92, "편차 완화 →\n모든 식품군 반영", transform=ax.transAxes,
            ha='left', va='top', fontsize=9, color='#1E8449')

    ax = axes[1, 0]
    cv = [x for x in cert if x is not None]
    ax.hist(cv, bins=12, color='#2980B9', alpha=0.75, edgecolor='white')
    ax.axvline(np.median(cv), color='#34495E', ls='--', lw=1.3, label=f'중앙값 {np.median(cv):.1f}%')
    ax.set_xlabel("HACCP 인증율 (%)", fontsize=10); ax.set_ylabel("식품군 수", fontsize=10)
    ax.set_title(f"(4) 인증율 — {min(cv):.0f}~{max(cv):.0f}% 고르게 분포", fontsize=11, fontweight='bold')
    ax.legend(fontsize=8.5)

    ax = axes[1, 1]
    ax.hist(recall, bins=14, color='#8E44AD', alpha=0.75, edgecolor='white')
    ax.set_xlabel("등급가중 회수 점수", fontsize=10); ax.set_ylabel("식품군 수", fontsize=10)
    ax.set_title(f"(5) 회수 원본 — 최대 {max(recall):.0f} vs 다수 0", fontsize=11, fontweight='bold')
    ax.text(0.97, 0.92, "기타식품류 돌출\n→ log 변환 필요", transform=ax.transAxes,
            ha='right', va='top', fontsize=9, color='#6C3483')

    ax = axes[1, 2]
    rv = [np.log(x+1) for x in recall]
    ax.hist(rv, bins=14, color='#27AE60', alpha=0.75, edgecolor='white')
    ax.set_xlabel("log(회수 점수 + 1)", fontsize=10); ax.set_ylabel("식품군 수", fontsize=10)
    ax.set_title("(6) log 변환 후 — 완화됨", fontsize=11, fontweight='bold')

    for ax in axes.flat:
        ax.grid(alpha=0.15); ax.set_axisbelow(True)
        for sp in ['top', 'right']:
            ax.spines[sp].set_visible(False)
    fig.suptitle("탐색적 데이터 분석 — 변수 분포와 변환 근거", fontsize=14, fontweight='bold', y=0.99)
    plt.tight_layout(rect=[0, 0, 1, 0.95])
    plt.savefig("fig0_eda.png", dpi=150, bbox_inches='tight'); plt.close()


# ═══════════════════════════════════════════════════
# fig1: HIP 순위
# ═══════════════════════════════════════════════════
def fig1_ranking(scores):
    cats = [r["품목유형"] for r in scores]
    hips = [float(r["HIP"]) for r in scores]
    cats_r, hips_r = cats[::-1], hips[::-1]
    n = len(cats_r)
    colors = ["#B03A2E" if (n-i) <= 5 else ("#D98880" if (n-i) <= 10 else "#AEB6BF") for i in range(n)]

    fig, ax = plt.subplots(figsize=(9, 9))
    ax.barh(range(n), hips_r, color=colors, height=0.7)
    ax.set_yticks(range(n)); ax.set_yticklabels(cats_r, fontsize=10)
    for i, v in enumerate(hips_r):
        ax.text(v + 0.008, i, f"{v:.3f}", va='center', fontsize=9, color='#333')
    ax.axhline(y=n - 5.5, color='#B03A2E', ls='--', lw=1.2, alpha=0.6)
    ax.set_xlabel("HIP (투자 우선순위 점수)", fontsize=11)
    ax.set_title("식품군별 HACCP 투자 우선순위", fontsize=14, fontweight='bold', pad=12)
    ax.set_xlim(0, max(hips) * 1.13); ax.grid(axis='x', alpha=0.25); ax.set_axisbelow(True)
    legend = [Patch_(("#B03A2E"), "최우선 (1–5위)"), Patch_(("#D98880"), "차순위 (6–10위)"),
              Patch_(("#AEB6BF"), "후순위 (11위–)")]
    ax.legend(handles=legend, loc='lower right', fontsize=9, framealpha=0.95)
    for sp in ['top', 'right']:
        ax.spines[sp].set_visible(False)
    plt.tight_layout(); plt.savefig("fig1_hip_ranking.png", dpi=150, bbox_inches='tight'); plt.close()


def Patch_(color, label):
    from matplotlib.patches import Patch
    return Patch(facecolor=color, label=label)


# ═══════════════════════════════════════════════════
# fig2: 4변수 누적막대
# ═══════════════════════════════════════════════════
def fig2_composition(scores):
    cats = [r["품목유형"] for r in scores][::-1]
    R = [float(r["Risk"])*0.25 for r in scores][::-1]
    S = [float(r["Scale"])*0.25 for r in scores][::-1]
    V = [float(r["Vulnerability"])*0.25 for r in scores][::-1]
    I = [float(r["Impact"])*0.25 for r in scores][::-1]
    n = len(cats)

    fig, ax = plt.subplots(figsize=(10, 9))
    left = np.zeros(n)
    for arr, c, lab in [(R, "#C0392B", "위험도 (Risk)"), (S, "#E67E22", "규모 (Scale)"),
                        (V, "#2980B9", "취약도 (Vuln)"), (I, "#27AE60", "사고 (Impact)")]:
        ax.barh(range(n), arr, left=left, color=c, label=lab, height=0.72)
        left += np.array(arr)
    ax.set_yticks(range(n)); ax.set_yticklabels(cats, fontsize=10)
    ax.set_xlabel("HIP 기여도 (변수별 × 0.25)", fontsize=11)
    ax.set_title("식품군별 HIP 구성 — 어떤 변수가 우선순위를 이끄는가", fontsize=13, fontweight='bold', pad=12)
    ax.legend(loc='lower right', fontsize=9, framealpha=0.95, ncol=2)
    ax.grid(axis='x', alpha=0.25); ax.set_axisbelow(True)
    for sp in ['top', 'right']:
        ax.spines[sp].set_visible(False)
    plt.tight_layout(); plt.savefig("fig2_hip_composition.png", dpi=150, bbox_inches='tight'); plt.close()


# ═══════════════════════════════════════════════════
# fig3: 민감도 히트맵
# ═══════════════════════════════════════════════════
def fig3_sensitivity(rows):
    cats = [r["품목유형"] for r in rows]
    shrunk, _, _, _ = beta_shrink(rows)

    def variables(impact_col):
        risk = [shrunk.get(c) for c in cats]
        scale = [math.log10(num(r, "생산액_천원")) if num(r, "생산액_천원") else None for r in rows]
        vuln = [(1 - num(r, "HACCP_인증률")) if num(r, "HACCP_인증률") is not None else None for r in rows]
        impact = [math.log((num(r, impact_col) or 0) + 1) for r in rows]
        fill = lambda xs: [x if x is not None else 0.0 for x in minmax(xs)]
        return fill(risk), fill(scale), fill(vuln), fill(impact)

    def rank_map(weights, impact_col="Impact_321"):
        R, S, V, I = variables(impact_col)
        wr, ws, wv, wi = weights
        sc = [(cats[i], wr*R[i]+ws*S[i]+wv*V[i]+wi*I[i]) for i in range(len(cats))]
        sc.sort(key=lambda x: -x[1])
        return {c: i+1 for i, (c, _) in enumerate(sc)}

    scenarios = {
        "동일가중": rank_map((0.25,)*4), "Risk↑": rank_map((0.40, 0.20, 0.20, 0.20)),
        "Scale↑": rank_map((0.20, 0.40, 0.20, 0.20)), "Vuln↑": rank_map((0.20, 0.20, 0.40, 0.20)),
        "Impact↑": rank_map((0.20, 0.20, 0.20, 0.40)),
        "등급5:3:1": rank_map((0.25,)*4, "Impact_531"), "등급1:1:1": rank_map((0.25,)*4, "Impact_111"),
    }
    base = scenarios["동일가중"]
    ordered = sorted(base, key=lambda c: base[c])
    matrix = np.array([[scenarios[s][c] for s in scenarios] for c in ordered])

    fig, ax = plt.subplots(figsize=(9, 11))
    im = ax.imshow(matrix, cmap='RdYlGn_r', aspect='auto', vmin=1, vmax=23)
    ax.set_xticks(range(len(scenarios))); ax.set_xticklabels(scenarios.keys(), fontsize=10, rotation=30, ha='right')
    ax.set_yticks(range(len(ordered))); ax.set_yticklabels(ordered, fontsize=9)
    for i in range(len(ordered)):
        for j in range(len(scenarios)):
            v = matrix[i, j]
            ax.text(j, i, int(v), ha='center', va='center', fontsize=8,
                    color='white' if (v <= 5 or v >= 19) else 'black')
    ax.set_title("가중치 민감도 분석 — 시나리오별 순위 변동", fontsize=13, fontweight='bold', pad=12)
    plt.colorbar(im, ax=ax, shrink=0.5, label='순위 (1=최우선)')
    plt.tight_layout(); plt.savefig("fig3_sensitivity.png", dpi=150, bbox_inches='tight'); plt.close()


# ═══════════════════════════════════════════════════
# fig4: 위험-규모 매트릭스 (0.5 / 중앙값 병치)
# ═══════════════════════════════════════════════════
def fig4_matrix(scores):
    try:
        from adjustText import adjust_text
        HAS_ADJUST = True
    except ImportError:
        HAS_ADJUST = False

    cats = [r["품목유형"] for r in scores]
    risk = [float(r["Risk"]) for r in scores]
    scale = [float(r["Scale"]) for r in scores]
    vuln = [float(r["Vulnerability"]) for r in scores]
    ranks = [int(r["Rank"]) for r in scores]
    sizes = [60 + v*460 for v in vuln]
    colors = ["#B03A2E" if rk <= 5 else ("#E59866" if rk <= 10 else "#85929E") for rk in ranks]
    med_x, med_y = np.median(scale), np.median(risk)

    targets = set(cats[:10]) | {"장류", "과자류, 빵류 또는 떡류", "면류", "벌꿀 및 화분가공품류", "유가공품류"}
    sn = lambda c: (c.replace(", 빵류 또는 떡류", "류").replace(" 및 화분가공품류", "").replace("류 또는 조림류", "·조림류"))

    def panel(ax, cx, cy, title):
        xlo, xhi, ylo, yhi = -0.08, 1.08, -0.08, 1.10
        ax.add_patch(Rectangle((cx, cy), xhi-cx, yhi-cy, facecolor='#F5B7B1', alpha=0.35, zorder=0))
        ax.add_patch(Rectangle((xlo, cy), cx-xlo, yhi-cy, facecolor='#FADBD8', alpha=0.22, zorder=0))
        ax.add_patch(Rectangle((cx, ylo), xhi-cx, cy-ylo, facecolor='#D5DBDB', alpha=0.22, zorder=0))
        ax.add_patch(Rectangle((xlo, ylo), cx-xlo, cy-ylo, facecolor='#EAEDED', alpha=0.22, zorder=0))
        ax.axhline(cy, color='#7B7D7D', ls='--', lw=1, alpha=0.7, zorder=1)
        ax.axvline(cx, color='#7B7D7D', ls='--', lw=1, alpha=0.7, zorder=1)
        ax.scatter(scale, risk, s=sizes, c=colors, alpha=0.75, edgecolors='white', linewidths=1.3, zorder=3)
        texts = []
        for i, c in enumerate(cats):
            if c in targets:
                texts.append(ax.text(scale[i], risk[i], sn(c), fontsize=8, color='#212F3D', zorder=5))
        if HAS_ADJUST:
            adjust_text(texts, ax=ax, arrowprops=dict(arrowstyle='-', color='#909497', lw=0.6), expand_points=(1.4, 1.4))
        for lab, x, y, ha, va, col in [
            ("① 고위험·대규모", xhi-0.02, yhi-0.02, 'right', 'top', '#922B21'),
            ("② 고위험·소규모", xlo+0.02, yhi-0.02, 'left', 'top', '#7E5109'),
            ("③ 저위험·대규모", xhi-0.02, ylo+0.02, 'right', 'bottom', '#5D6D7E'),
            ("④ 저위험·소규모", xlo+0.02, ylo+0.02, 'left', 'bottom', '#808B96')]:
            ax.text(x, y, lab, ha=ha, va=va, fontsize=9, color=col,
                    fontweight='bold' if '①' in lab else 'normal', zorder=6)
        q1 = sum(1 for i in range(len(cats)) if scale[i] >= cx and risk[i] >= cy)
        q2 = sum(1 for i in range(len(cats)) if scale[i] < cx and risk[i] >= cy)
        q3 = sum(1 for i in range(len(cats)) if scale[i] >= cx and risk[i] < cy)
        q4 = sum(1 for i in range(len(cats)) if scale[i] < cx and risk[i] < cy)
        for txt, x, y, ha, va, col in [(f"({q1}개)", xhi-0.02, yhi-0.12, 'right', 'top', '#922B21'),
                                        (f"({q2}개)", xlo+0.02, yhi-0.12, 'left', 'top', '#7E5109'),
                                        (f"({q3}개)", xhi-0.02, ylo+0.10, 'right', 'bottom', '#5D6D7E'),
                                        (f"({q4}개)", xlo+0.02, ylo+0.10, 'left', 'bottom', '#808B96')]:
            ax.text(x, y, txt, ha=ha, va=va, fontsize=8, color=col)
        ax.set_xlim(xlo, xhi); ax.set_ylim(ylo, yhi)
        ax.set_xlabel("Scale — 경제 규모 (생산액, 정규화)", fontsize=10)
        ax.set_title(title, fontsize=11.5, fontweight='bold', pad=10)
        ax.grid(alpha=0.12, zorder=0)
        for sp in ['top', 'right']:
            ax.spines[sp].set_visible(False)

    fig, axes = plt.subplots(1, 2, figsize=(17, 8))
    panel(axes[0], 0.5, 0.5, "(A) 고정 기준선 0.5 — 일반적 방식")
    panel(axes[1], med_x, med_y, f"(B) 중앙값 기준선 (Scale {med_x:.2f} / Risk {med_y:.2f}) — 분포 반영")
    axes[0].set_ylabel("Risk — 안전 위험도 (부적합률, 정규화)", fontsize=10)
    legend = [Line2D([0], [0], marker='o', color='w', markerfacecolor=c, markersize=10, label=l)
              for c, l in [("#B03A2E", 'HIP 1–5위'), ("#E59866", 'HIP 6–10위'), ("#85929E", 'HIP 11위–')]]
    axes[0].legend(handles=legend, loc='center left', fontsize=9, framealpha=0.95)
    fig.suptitle("위험–규모 포트폴리오 매트릭스 — 기준선 비교\n점 크기 = HACCP 취약도(미인증 비율), 색 = HIP 순위",
                 fontsize=13.5, fontweight='bold', y=0.99)
    plt.tight_layout(rect=[0, 0, 1, 0.94])
    plt.savefig("fig4_risk_scale_matrix.png", dpi=150, bbox_inches='tight'); plt.close()


# ═══════════════════════════════════════════════════
# fig5: 예산 배분 시뮬레이션
# ═══════════════════════════════════════════════════
def fig5_budget(scores):
    cats = [r["품목유형"] for r in scores]
    hips = np.array([float(r["HIP"]) for r in scores])
    n = len(cats); TOTAL = 100.0
    equal = np.full(n, TOTAL/n)
    hip_a = TOTAL * hips / hips.sum()
    diff = hip_a - equal
    cats_r, eq_r, hip_r, diff_r = cats[::-1], equal[::-1], hip_a[::-1], diff[::-1]
    y = np.arange(n)

    fig, axes = plt.subplots(1, 2, figsize=(16, 9), gridspec_kw={'width_ratios': [1.25, 1]})
    ax = axes[0]; h = 0.38
    ax.barh(y - h/2, eq_r, height=h, color='#AEB6BF', label='균등 배분 (비교 기준)')
    ax.barh(y + h/2, hip_r, height=h, color='#B03A2E', label='HIP 기반 차등 배분 (제안)')
    ax.set_yticks(y); ax.set_yticklabels(cats_r, fontsize=9)
    ax.axvline(TOTAL/n, color='#566573', ls=':', lw=1.2, alpha=0.8)
    ax.text(TOTAL/n, n-0.3, f' 균등선 {TOTAL/n:.1f}', fontsize=8, color='#566573', va='bottom', style='italic')
    ax.set_xlabel("배분 예산 (총 100 기준)", fontsize=10.5)
    ax.set_title("(A) 배분 방식별 예산 비교", fontsize=12, fontweight='bold', pad=10)
    ax.legend(loc='lower right', fontsize=9, framealpha=0.95)
    ax.grid(axis='x', alpha=0.2); ax.set_axisbelow(True)
    for sp in ['top', 'right']:
        ax.spines[sp].set_visible(False)

    ax2 = axes[1]
    bar_colors = ['#B03A2E' if d > 0 else '#5D8AA8' for d in diff_r]
    ax2.barh(y, diff_r, height=0.66, color=bar_colors)
    ax2.set_yticks(y); ax2.set_yticklabels([])
    ax2.axvline(0, color='#34495E', lw=1.1)
    for i, d in enumerate(diff_r):
        ax2.text(d + (0.09 if d > 0 else -0.09), i, f"{d:+.1f}", va='center',
                 ha='left' if d > 0 else 'right', fontsize=8.5, color='#2C3E50')
    ax2.set_xlabel("균등 배분 대비 증감", fontsize=10.5)
    ax2.set_title("(B) 재배분 효과 — 어디로 옮겨가는가", fontsize=12, fontweight='bold', pad=10)
    lim = max(abs(diff)) * 1.35; ax2.set_xlim(-lim, lim)
    ax2.grid(axis='x', alpha=0.2); ax2.set_axisbelow(True)
    for sp in ['top', 'right', 'left']:
        ax2.spines[sp].set_visible(False)
    gain = diff[diff > 0].sum()
    ax2.text(lim*0.95, -0.9, f"상위군으로 이동: +{gain:.1f}", ha='right', va='top',
             fontsize=9.5, color='#B03A2E', fontweight='bold')
    fig.suptitle("HACCP 예산 배분 시뮬레이션 — 균등 배분 vs 우선순위 기반 차등 배분",
                 fontsize=13.5, fontweight='bold', y=0.98)
    plt.tight_layout(rect=[0, 0, 1, 0.95])
    plt.savefig("fig5_budget_allocation.png", dpi=150, bbox_inches='tight'); plt.close()


# ═══════════════════════════════════════════════════
# fig6: 베타-이항 보정 효과
# ═══════════════════════════════════════════════════
def fig6_shrinkage(rows):
    data = [(r["품목유형"], num(r, "검사건수"), num(r, "부적합건수"))
            for r in rows if num(r, "검사건수") and num(r, "부적합건수") is not None]
    _, pm, a, b = beta_shrink(rows)
    names = [d[0] for d in data]
    insp = np.array([d[1] for d in data])
    raw = np.array([d[2]/d[1]*100 for d in data])
    adj = np.array([(d[2]+a)/(d[1]+a+b)*100 for d in data])

    fig, ax = plt.subplots(figsize=(12, 8))
    for i in range(len(names)):
        s = abs(raw[i]-adj[i])
        c = '#C0392B' if s > 0.3 else ('#E67E22' if s > 0.05 else '#95A5A6')
        ax.annotate('', xy=(insp[i], adj[i]), xytext=(insp[i], raw[i]),
                    arrowprops=dict(arrowstyle='->', color=c, lw=1.6, alpha=0.8))
    ax.scatter(insp, raw, s=70, c='#BDC3C7', edgecolors='#7F8C8D', linewidths=1, label='원본 부적합률', zorder=3)
    ax.scatter(insp, adj, s=70, c='#C0392B', edgecolors='white', linewidths=1, label='보정 후 (베타-이항 축소)', zorder=3)
    ax.axhline(pm*100, color='#34495E', ls=':', lw=1.3, label=f'전체 평균 {pm*100:.2f}% (축소 목표점)')
    for i, nm in enumerate(names):
        if abs(raw[i]-adj[i]) > 0.25 or insp[i] > 7000:
            ax.annotate(nm.replace(" 및 화분가공품류", "").replace(", 빵류 또는 떡류", "류"),
                        (insp[i], raw[i]), fontsize=9, xytext=(7, 4), textcoords='offset points', color='#2C3E50')
    ax.set_xscale('log')
    ax.set_xlabel("검사 건수 (log scale)", fontsize=11); ax.set_ylabel("부적합률 (%)", fontsize=11)
    ax.set_title("베타-이항 축소 효과 — 소표본 편향 보정\n검사 건수가 적을수록 전체 평균 쪽으로 크게 축소",
                 fontsize=13, fontweight='bold', pad=12)
    ax.legend(fontsize=9.5, loc='upper right'); ax.grid(alpha=0.18); ax.set_axisbelow(True)
    for sp in ['top', 'right']:
        ax.spines[sp].set_visible(False)
    ax.text(0.02, 0.97, f"α={a:.3f}, β={b:.1f}  (적률법 추정)\n→ 검사 약 {a+b:.0f}건 이상부터 관측값 신뢰",
            transform=ax.transAxes, va='top', fontsize=9, color='#566573',
            bbox=dict(boxstyle='round,pad=0.5', facecolor='#F8F9F9', edgecolor='#D5DBDB'))
    plt.tight_layout(); plt.savefig("fig6_shrinkage.png", dpi=150, bbox_inches='tight'); plt.close()


def main():
    merged = load(MERGED)
    scores = load(SCORES)
    fig0_eda(merged)
    fig1_ranking(scores)
    fig2_composition(scores)
    fig3_sensitivity(merged)
    fig4_matrix(scores)
    fig5_budget(scores)
    fig6_shrinkage(merged)
    print("7종 시각화 저장 완료: fig0~fig6")


if __name__ == "__main__":
    main()
