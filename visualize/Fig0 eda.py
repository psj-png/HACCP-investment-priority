"""
fig0: EDA — 변수 분포 + log 변환 근거 (20개 식품군)
입력: merged20.csv
출력: fig0_eda.png
"""
import numpy as np
import matplotlib.pyplot as plt
from _common import setup_font, num, load, MERGED20


def main():
    setup_font()
    rows = load(MERGED20)

    fail = [(num(r, "부적합건수") / num(r, "검사건수") * 100) if num(r, "검사건수") else None for r in rows]
    prod = [num(r, "생산액_천원") for r in rows]
    cert = [num(r, "HACCP_인증률") * 100 if num(r, "HACCP_인증률") is not None else None for r in rows]
    recall = [((num(r, "Recall_1등급") or 0)*3 + (num(r, "Recall_2등급") or 0)*2
               + (num(r, "Recall_3등급") or 0)*1) for r in rows]

    fig, axes = plt.subplots(2, 3, figsize=(17, 9.5))

    ax = axes[0, 0]
    v = [x for x in fail if x is not None]
    ax.hist(v, bins=12, color='#C0392B', alpha=0.75, edgecolor='white')
    ax.axvline(np.median(v), color='#34495E', ls='--', lw=1.3, label=f'중앙값 {np.median(v):.2f}%')
    ax.annotate(f'최대 {max(v):.2f}%\n(극단값)', xy=(max(v), 1), xytext=(max(v)*0.6, 4),
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
    ax.set_title(f"(4) 인증율 — {min(cv):.0f}~{max(cv):.0f}% 분포", fontsize=11, fontweight='bold')
    ax.legend(fontsize=8.5)

    ax = axes[1, 1]
    ax.hist(recall, bins=14, color='#8E44AD', alpha=0.75, edgecolor='white')
    ax.set_xlabel("등급가중 회수 점수", fontsize=10); ax.set_ylabel("식품군 수", fontsize=10)
    ax.set_title(f"(5) 회수 원본 — 최대 {max(recall):.0f} vs 다수 0", fontsize=11, fontweight='bold')
    ax.text(0.97, 0.92, "소수 돌출\n→ log 변환 필요", transform=ax.transAxes,
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
    fig.suptitle("탐색적 데이터 분석 — 변수 분포와 변환 근거 (20개 식품군)",
                 fontsize=14, fontweight='bold', y=0.99)
    plt.tight_layout(rect=[0, 0, 1, 0.95])
    plt.savefig("fig0_eda.png", dpi=150, bbox_inches='tight')
    plt.show()
    print("저장: fig0_eda.png")


if __name__ == "__main__":
    main()
