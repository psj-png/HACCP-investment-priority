"""
fig5: 예산 배분 시뮬레이션 — 균등 vs HIP 차등 (20개)
입력: scores20.csv
출력: fig5_budget.png
"""
import numpy as np
import matplotlib.pyplot as plt
from _common import setup_font, load, SCORES20


def main():
    setup_font()
    scores = load(SCORES20)
    cats = [r["품목유형"] for r in scores]
    hips = np.array([float(r["HIP_ref"]) for r in scores])
    n = len(cats); TOTAL = 100.0
    equal = np.full(n, TOTAL/n)
    hip_a = TOTAL * hips / hips.sum()
    diff = hip_a - equal
    cats_r, eq_r, hip_r, diff_r = cats[::-1], equal[::-1], hip_a[::-1], diff[::-1]
    y = np.arange(n)

    fig, axes = plt.subplots(1, 2, figsize=(16, 8.5), gridspec_kw={'width_ratios': [1.25, 1]})
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
    fig.suptitle("HACCP 예산 배분 시뮬레이션 — 균등 vs 우선순위 기반 차등 (20개)",
                 fontsize=13.5, fontweight='bold', y=0.98)
    plt.tight_layout(rect=[0, 0, 1, 0.95])
    plt.savefig("fig5_budget.png", dpi=150, bbox_inches='tight')
    plt.show()
    print(f"저장: fig5_budget.png (재배분 {gain:.1f}%)")


if __name__ == "__main__":
    main()
