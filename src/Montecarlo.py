"""
몬테카를로 민감도 분석
============================================
입력: data/processed/merged.csv (Recall_1/2/3등급 포함)
출력: data/processed/montecarlo_ranks.csv,
      data/processed/montecarlo_ranks_full.npy (박스플롯용)

가중치를 무작위로 1만 회 추출해 순위 분포 산출:
  - 변수 가중치 (R/S/V/I): 완전 무작위 (Dirichlet, 제약 없음)
  - 등급 가중치 (1/2/3): 순서 제약 (g1 ≥ g2 ≥ g3)

특정 가중치 값을 지정하지 않으므로 "왜 3:2:1?" 반박이 성립하지 않음.
근거 있는 가정은 등급 순서(식약처 정의)뿐.
"""

import csv
import math
import numpy as np

MERGED = "data/processed/merged.csv"
OUT = "data/processed/montecarlo_ranks.csv"
N = 10000
SEED = 42


def num(r, k):
    v = r.get(k, "")
    try:
        return float(v) if str(v).strip() not in ("", "-") else None
    except ValueError:
        return None


def minmax(arr):
    valid = arr[~np.isnan(arr)]
    if len(valid) == 0:
        return np.zeros_like(arr)
    lo, hi = valid.min(), valid.max()
    out = np.full_like(arr, 0.5) if hi == lo else (arr - lo) / (hi - lo)
    out[np.isnan(out)] = 0.0
    return out


def beta_shrink(insp, fail):
    mask = (insp > 0) & ~np.isnan(fail)
    tf, ti = fail[mask].sum(), insp[mask].sum()
    pm = tf / ti if ti else 0
    obs = fail[mask] / insp[mask]
    mean, var = obs.mean(), obs.var()
    conc = max((mean * (1 - mean) / var) - 1, 1.0) if var > 0 and 0 < mean < 1 else 100.0
    a, b = pm * conc, (1 - pm) * conc
    out = np.full(len(insp), np.nan)
    out[mask] = (fail[mask] + a) / (insp[mask] + a + b)
    return out


def main():
    with open(MERGED, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    cats = [r["품목유형"] for r in rows]
    n_cat = len(cats)

    insp = np.array([num(r, "검사건수") or np.nan for r in rows])
    fail = np.array([num(r, "부적합건수") if num(r, "부적합건수") is not None else np.nan for r in rows])
    R = minmax(beta_shrink(insp, fail))
    scale_raw = np.array([math.log10(num(r, "생산액_천원")) if num(r, "생산액_천원") else np.nan for r in rows])
    S = minmax(scale_raw)
    vuln_raw = np.array([(1 - num(r, "HACCP_인증률")) if num(r, "HACCP_인증률") is not None else np.nan for r in rows])
    V = minmax(vuln_raw)

    C = np.array([[num(r, "Recall_1등급") or 0, num(r, "Recall_2등급") or 0,
                   num(r, "Recall_3등급") or 0] for r in rows])

    rng = np.random.default_rng(SEED)
    rank_log = np.zeros((N, n_cat), dtype=int)

    for t in range(N):
        var_w = rng.dirichlet([1, 1, 1, 1])
        grade_w = np.sort(rng.random(3))[::-1]
        I = minmax(np.log((C @ grade_w) + 1))
        hip = var_w[0]*R + var_w[1]*S + var_w[2]*V + var_w[3]*I
        rank_log[t] = np.argsort(np.argsort(-hip)) + 1

    median_rank = np.median(rank_log, axis=0)
    order = np.argsort(median_rank)

    print("=" * 70)
    print(f"몬테카를로 민감도 분석 (N={N:,})")
    print("변수 가중치: 무작위 / 등급 가중치: 순서 제약(1≥2≥3)")
    print("=" * 70)
    print(f"{'품목유형':<22}{'중앙순위':>7}{'최선':>5}{'최악':>5}{'top5 유지율':>11}{'top10':>8}")
    print("-" * 70)
    for i in order:
        r = rank_log[:, i]
        print(f"{cats[i]:<22}{np.median(r):>7.0f}{r.min():>5}{r.max():>5}"
              f"{(r<=5).mean()*100:>10.1f}%{(r<=10).mean()*100:>7.1f}%")

    with open(OUT, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["품목유형", "중앙순위", "최선", "최악", "top5_유지율", "top10_유지율"])
        for i in order:
            r = rank_log[:, i]
            w.writerow([cats[i], f"{np.median(r):.0f}", r.min(), r.max(),
                        f"{(r<=5).mean()*100:.1f}", f"{(r<=10).mean()*100:.1f}"])

    np.save("data/processed/montecarlo_ranks_full.npy", rank_log)
    np.save("data/processed/montecarlo_cats.npy", np.array(cats))
    print(f"\n저장: {OUT}")
    print("저장: montecarlo_ranks_full.npy (박스플롯용)")


if __name__ == "__main__":
    main()
