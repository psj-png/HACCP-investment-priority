"""
fig2: 4변수 누적막대 — HIP 구성 (20개)
입력: scores20.csv
출력: fig2_composition.png
"""
import numpy as np
import matplotlib.pyplot as plt
from _common import setup_font, load, SCORES20


def main():
    setup_font()
    scores = load(SCORES20)
    cats = [r["품목유형"] for r in scores][::-1]
    R = [float(r["Risk"])*0.25 for r in scores][::-1]
    S = [float(r["Scale"])*0.25 for r in scores][::-1]
    V = [float(r["적용공백"])*0.25 for r in scores][::-1]
    I = [float(r["Impact"])*0.25 for r in scores][::-1]
    n = len(cats)

    fig, ax = plt.subplots(figsize=(10, 8.5))
    left = np.zeros(n)
    for arr, c, lab in [(R, "#C0392B", "위험도 (Risk)"), (S, "#E67E22", "규모 (Scale)"),
                        (V, "#2980B9", "적용공백"), (I, "#27AE60", "사고 (Impact)")]:
        ax.barh(range(n), arr, left=left, color=c, label=lab, height=0.72)
        left += np.array(arr)
    ax.set_yticks(range(n)); ax.set_yticklabels(cats, fontsize=10)
    ax.set_xlabel("HIP 기여도 (변수별 × 0.25)", fontsize=11)
    ax.set_title("식품군별 HIP 구성 — 어떤 변수가 우선순위를 이끄는가",
                 fontsize=13, fontweight='bold', pad=12)
    ax.legend(loc='lower right', fontsize=9, framealpha=0.95, ncol=2)
    ax.grid(axis='x', alpha=0.25); ax.set_axisbelow(True)
    for sp in ['top', 'right']:
        ax.spines[sp].set_visible(False)
    plt.tight_layout()
    plt.savefig("fig2_composition.png", dpi=150, bbox_inches='tight')
    plt.show()
    print("저장: fig2_composition.png")


if __name__ == "__main__":
    main()
