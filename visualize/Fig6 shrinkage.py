"""
fig6: 베타-이항 축소 효과 — 소표본 편향 보정 (20개)
입력: merged20.csv
출력: fig6_shrinkage.png
"""
import numpy as np
import matplotlib.pyplot as plt
from _common import setup_font, num, load, beta_shrink, MERGED20


def main():
    setup_font()
    rows = load(MERGED20)
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
    ax.scatter(insp, raw, s=70, c='#BDC3C7', edgecolors='#7F8C8D', linewidths=1,
               label='원본 부적합률', zorder=3)
    ax.scatter(insp, adj, s=70, c='#C0392B', edgecolors='white', linewidths=1,
               label='보정 후 (베타-이항 축소)', zorder=3)
    ax.axhline(pm*100, color='#34495E', ls=':', lw=1.3, label=f'전체 평균 {pm*100:.2f}% (축소 목표점)')
    for i, nm in enumerate(names):
        if abs(raw[i]-adj[i]) > 0.2 or insp[i] > 6000:
            ax.annotate(nm.replace(" 및 화분가공품류", "").replace(", 빵류 또는 떡류", "류"),
                        (insp[i], raw[i]), fontsize=9, xytext=(7, 4),
                        textcoords='offset points', color='#2C3E50')
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
    plt.tight_layout()
    plt.savefig("fig6_shrinkage.png", dpi=150, bbox_inches='tight')
    plt.show()
    print("저장: fig6_shrinkage.png")


if __name__ == "__main__":
    main()
