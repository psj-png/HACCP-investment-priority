"""
fig1: HIP 순위 바차트 (SMAA 중앙순위 정본, 20개)
입력: scores20.csv
출력: fig1_ranking.png
"""
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from _common import setup_font, num, load, SCORES20


def main():
    setup_font()
    scores = load(SCORES20)
    # scores20.csv는 최종순위(SMAA 중앙) 오름차순 정렬됨
    cats = [r["품목유형"] for r in scores]
    hips = [float(r["HIP_ref"]) for r in scores]
    # barh는 아래부터 → 역순 (1위가 맨 위)
    cats_r, hips_r = cats[::-1], hips[::-1]
    n = len(cats_r)
    colors = ["#B03A2E" if (n-i) <= 5 else ("#D98880" if (n-i) <= 10 else "#AEB6BF") for i in range(n)]

    fig, ax = plt.subplots(figsize=(9, 8.5))
    ax.barh(range(n), hips_r, color=colors, height=0.7)
    ax.set_yticks(range(n)); ax.set_yticklabels(cats_r, fontsize=10)
    for i, v in enumerate(hips_r):
        ax.text(v + 0.008, i, f"{v:.3f}", va='center', fontsize=9, color='#333')
    ax.axhline(y=n - 5.5, color='#B03A2E', ls='--', lw=1.2, alpha=0.6)
    ax.set_xlabel("HIP (참고: 등급 3:2:1·동일가중)", fontsize=11)
    ax.set_title("식품군별 HACCP 투자 우선순위 (20개, SMAA 중앙순위)",
                 fontsize=13, fontweight='bold', pad=12)
    ax.set_xlim(0, max(hips) * 1.13); ax.grid(axis='x', alpha=0.25); ax.set_axisbelow(True)
    legend = [Patch(facecolor="#B03A2E", label="최우선 (1–5위)"),
              Patch(facecolor="#D98880", label="차순위 (6–10위)"),
              Patch(facecolor="#AEB6BF", label="후순위 (11위–)")]
    ax.legend(handles=legend, loc='lower right', fontsize=9, framealpha=0.95)
    for sp in ['top', 'right']:
        ax.spines[sp].set_visible(False)
    plt.tight_layout()
    plt.savefig("fig1_ranking.png", dpi=150, bbox_inches='tight')
    plt.show()
    print("저장: fig1_ranking.png")


if __name__ == "__main__":
    main()
