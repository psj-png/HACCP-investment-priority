"""
fig7: SMAA 순위 분포 박스플롯 (4변수) + 적용공백 강건성 (3변수 비교)
============================================
입력: smaa_ranks_full.npy, smaa_ranks3_full.npy, smaa_cats.npy
출력: fig7_smaa.png

왼쪽:  4변수 SMAA 순위 분포 (박스=사분위, 좁을수록 안정)
오른쪽: 적용공백 제외(3변수) 시 중앙순위 변화 — 적용공백 의존도
"""
import numpy as np
import matplotlib.pyplot as plt
from _common import setup_font, short_name


def main():
    setup_font()
    ranks4 = np.load("data/processed/smaa_ranks_full.npy")     # N × 20
    ranks3 = np.load("data/processed/smaa_ranks3_full.npy")
    cats = np.load("data/processed/smaa_cats.npy", allow_pickle=True)

    med4 = np.median(ranks4, axis=0)
    med3 = np.median(ranks3, axis=0)
    order = np.argsort(med4)[::-1]   # 박스플롯 아래→위 (1위가 위로)

    cats_o = [short_name(cats[i]) for i in order]
    data = [ranks4[:, i] for i in order]
    n = len(cats_o)

    fig, axes = plt.subplots(1, 2, figsize=(16, 9), gridspec_kw={'width_ratios': [1.4, 1]})

    # ─── 왼쪽: 4변수 순위 분포 박스플롯 ───
    ax = axes[0]
    bp = ax.boxplot(data, vert=False, widths=0.6, patch_artist=True,
                    showfliers=False, medianprops=dict(color='#1C2833', linewidth=1.5))
    for i, patch in enumerate(bp['boxes']):
        m = med4[order[i]]
        patch.set_facecolor("#B03A2E" if m <= 5 else ("#E59866" if m <= 10 else "#AEB6BF"))
        patch.set_alpha(0.75)
    for w in bp['whiskers']:
        w.set(color='#7B7D7D', linewidth=1)
    for cap in bp['caps']:
        cap.set(color='#7B7D7D', linewidth=1)
    ax.set_yticks(range(1, n+1)); ax.set_yticklabels(cats_o, fontsize=9)
    ax.set_xlabel("순위 분포 (SMAA 1만 회, 1=최우선)", fontsize=10.5)
    ax.set_title("(A) SMAA 순위 분포 — 가중치 무작위 1만 회\n박스=사분위 범위 (좁을수록 안정)",
                 fontsize=12, fontweight='bold', pad=10)
    ax.axvline(5.5, color='#B03A2E', ls='--', lw=1, alpha=0.5)
    ax.text(5.5, n+0.4, ' top5 경계', color='#B03A2E', fontsize=8, va='bottom')
    ax.set_xlim(0, n+1); ax.grid(axis='x', alpha=0.2); ax.set_axisbelow(True)
    for sp in ['top', 'right']:
        ax.spines[sp].set_visible(False)

    # ─── 오른쪽: 4변수 vs 3변수 중앙순위 변화 ───
    ax2 = axes[1]
    y = np.arange(1, n+1)
    m4 = [med4[i] for i in order]
    m3 = [med3[i] for i in order]

    for i in range(n):
        diff = m3[i] - m4[i]
        color = '#5D8AA8' if abs(diff) <= 2 else ('#C0392B' if diff > 2 else '#E67E22')
        ax2.plot([m4[i], m3[i]], [y[i], y[i]], color=color, lw=1.5, alpha=0.7, zorder=2)
    ax2.scatter(m4, y, s=45, color='#2C3E50', label='4변수 (적용공백 포함)', zorder=3)
    ax2.scatter(m3, y, s=45, facecolors='white', edgecolors='#7B7D7D',
                linewidths=1.3, label='3변수 (적용공백 제외)', zorder=3)

    ax2.set_yticks(range(1, n+1)); ax2.set_yticklabels([])
    ax2.set_xlabel("중앙 순위", fontsize=10.5)
    ax2.set_title("(B) 적용공백 제외 시 순위 변화\n선이 길수록 적용공백 의존 큼",
                  fontsize=12, fontweight='bold', pad=10)
    ax2.legend(loc='lower right', fontsize=8.5, framealpha=0.95)
    ax2.set_xlim(0, n+1); ax2.grid(axis='x', alpha=0.2); ax2.set_axisbelow(True)
    ax2.invert_xaxis()  # 1위가 오른쪽 (왼쪽 박스플롯과 방향 일치 위해 재반전)
    ax2.invert_xaxis()
    for sp in ['top', 'right', 'left']:
        ax2.spines[sp].set_visible(False)

    fig.suptitle("SMAA 강건성 — 순위 안정성과 적용공백 의존도 (20개)",
                 fontsize=13.5, fontweight='bold', y=0.99)
    plt.tight_layout(rect=[0, 0, 1, 0.95])
    plt.savefig("fig7_smaa.png", dpi=150, bbox_inches='tight')
    plt.show()
    print("저장: fig7_smaa.png")


if __name__ == "__main__":
    main()
