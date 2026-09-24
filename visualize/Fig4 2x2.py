"""
fig4: 2×2 처방 매트릭스 (적용공백 × 부적합률)
============================================
입력: scores20.csv
출력: fig4_2x2.png

- 가로 = 적용공백 (1 − HACCP 인증률)
- 세로 = 부적합률 (Risk, 베타-이항 보정)
- 원 크기 = 회수 건수 (등급 가중 없음)
- 기준선 = 각 축 중앙값

목적: "인증률이 낮은 것"과 "실제 위험한 것"을 구분 (적용공백 오해석 방지).
순위·예산에는 미사용. 칸별 처방은 가설적 제언.
  ① 공백+위해   → 인증 확대·기술지원
  ② 공백만      → 지원보다 모니터링
  ③ 적용됐으나 위해 → 사후관리 점검 (인증/미인증 구분 불가)
  ④ 안정        → 현 수준 유지
"""
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from _common import setup_font, num, load, short_name, SCORES20

try:
    from adjustText import adjust_text
    HAS_ADJUST = True
except ImportError:
    HAS_ADJUST = False


def main():
    setup_font()
    scores = load(SCORES20)

    cats = [r["품목유형"] for r in scores]
    gap = [float(r["적용공백"]) for r in scores]
    risk = [float(r["Risk"]) for r in scores]
    recall = [int(float(r["회수건수"])) for r in scores]

    gap_med, risk_med = np.median(gap), np.median(risk)
    recall_med = np.median(recall)

    # 원 크기: 회수 건수 (0건도 보이게 최소 크기)
    sizes = [40 + rc * 12 for rc in recall]

    # 점 색: 4분면
    def quad_color(g, r):
        hg, hr = g >= gap_med, r >= risk_med
        if hg and hr:
            return "#B03A2E"   # ① 공백+위해
        if hg and not hr:
            return "#E59866"   # ② 공백만
        if not hg and hr:
            return "#7D6699"   # ③ 적용됐으나 위해
        return "#AEB6BF"       # ④ 안정
    colors = [quad_color(gap[i], risk[i]) for i in range(len(cats))]

    fig, ax = plt.subplots(figsize=(12, 9))
    xlo, xhi, ylo, yhi = -0.08, 1.12, -0.08, 1.12

    # 4분면 배경
    ax.add_patch(Rectangle((gap_med, risk_med), xhi-gap_med, yhi-risk_med,
                           facecolor='#F5B7B1', alpha=0.30, zorder=0))   # ① 우상
    ax.add_patch(Rectangle((xlo, risk_med), gap_med-xlo, yhi-risk_med,
                           facecolor='#D6B0D0', alpha=0.22, zorder=0))   # ③ 좌상
    ax.add_patch(Rectangle((gap_med, ylo), xhi-gap_med, risk_med-ylo,
                           facecolor='#FAE5D3', alpha=0.30, zorder=0))   # ② 우하
    ax.add_patch(Rectangle((xlo, ylo), gap_med-xlo, risk_med-ylo,
                           facecolor='#EAEDED', alpha=0.25, zorder=0))   # ④ 좌하

    ax.axhline(risk_med, color='#7B7D7D', ls='--', lw=1, alpha=0.7, zorder=1)
    ax.axvline(gap_med, color='#7B7D7D', ls='--', lw=1, alpha=0.7, zorder=1)

    # 기준선 라벨
    ax.text(xhi-0.01, risk_med+0.012, f"부적합률 중앙값 {risk_med:.2f}", ha='right', va='bottom',
            fontsize=8, color='#7B7D7D', style='italic')
    ax.text(gap_med+0.012, ylo+0.02, f"적용공백 중앙값 {gap_med:.2f}", ha='left', va='bottom',
            fontsize=8, color='#7B7D7D', style='italic', rotation=90)

    ax.scatter(gap, risk, s=sizes, c=colors, alpha=0.78,
               edgecolors='white', linewidths=1.3, zorder=3)

    # 라벨 (전부)
    texts = []
    for i, c in enumerate(cats):
        texts.append(ax.text(gap[i], risk[i], short_name(c), fontsize=8, color='#212F3D', zorder=5))
    if HAS_ADJUST:
        adjust_text(texts, ax=ax, arrowprops=dict(arrowstyle='-', color='#909497', lw=0.6),
                    expand_points=(1.4, 1.4))

    # 4분면 이름 + 처방
    quad_labels = [
        ("① 공백 + 위해\n인증 확대·기술지원", xhi-0.02, yhi-0.02, 'right', 'top', '#922B21', True),
        ("③ 적용됐으나 위해 신호\n사후관리 점검", xlo+0.02, yhi-0.02, 'left', 'top', '#5B4B72', False),
        ("② 공백만\n지원보다 모니터링", xhi-0.02, ylo+0.02, 'right', 'bottom', '#935116', False),
        ("④ 안정\n현 수준 유지", xlo+0.02, ylo+0.02, 'left', 'bottom', '#808B96', False),
    ]
    for lab, x, y, ha, va, col, bold in quad_labels:
        ax.text(x, y, lab, ha=ha, va=va, fontsize=9.5, color=col,
                fontweight='bold' if bold else 'normal', zorder=6, linespacing=1.4)

    ax.set_xlim(xlo, xhi); ax.set_ylim(ylo, yhi)
    ax.set_xlabel("적용공백 (1 − HACCP 인증률) →  관리 범위 작음", fontsize=11)
    ax.set_ylabel("부적합률 (Risk, 정규화) →  실제 위해 발생", fontsize=11)
    ax.set_title("HACCP 적용공백 × 위해 신호 — 처방 구분 매트릭스\n"
                 "원 크기 = 회수 건수 (칸 결정에 미사용)",
                 fontsize=13, fontweight='bold', pad=14)
    ax.grid(alpha=0.12, zorder=0)
    for sp in ['top', 'right']:
        ax.spines[sp].set_visible(False)

    # 회수 다수(중앙값 이상) 주석 안내
    ax.text(0.5, -0.11,
            f"※ 회수 건수 중앙값({recall_med:.0f}건) 이상 식품군은 큰 원으로 표시 — 해당 칸 해석 시 회수 모니터링 병행",
            transform=ax.transAxes, ha='center', fontsize=8.5, color='#566573')

    plt.tight_layout()
    plt.savefig("fig4_2x2.png", dpi=150, bbox_inches='tight')
    plt.show()

    # 콘솔 요약
    print(f"기준선 — 적용공백 중앙값 {gap_med:.3f}, 부적합률 중앙값 {risk_med:.3f}, 회수 중앙값 {recall_med:.0f}건\n")
    labels = {"①": [], "②": [], "③": [], "④": []}
    for i, c in enumerate(cats):
        hg, hr = gap[i] >= gap_med, risk[i] >= risk_med
        q = "①" if (hg and hr) else "②" if (hg and not hr) else "③" if (not hg and hr) else "④"
        flag = " (회수 다수)" if recall[i] >= recall_med else ""
        labels[q].append(short_name(c) + flag)
    names = {"①": "공백+위해", "②": "공백만", "③": "적용됐으나 위해", "④": "안정"}
    for q in ["①", "②", "③", "④"]:
        print(f"  {q} {names[q]}: {', '.join(labels[q])}")


if __name__ == "__main__":
    main()
