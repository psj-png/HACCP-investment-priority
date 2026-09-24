"""
SMAA (Stochastic Multicriteria Acceptability Analysis)
============================================
입력: data/processed/merged20.csv
출력: data/processed/smaa_ranks.csv, smaa_ranks_full.npy

가중치를 모르는 상황에서 가중치 공간을 무작위 탐색해 순위 분포를 산출.
(Lahdelma et al. 1998; 계산은 몬테카를로 시뮬레이션 1만 회)

  - 변수 가중치 (Risk/Scale/적용공백/Impact): 완전 무작위 (Dirichlet)
  - 회수 등급 가중치 (1/2/3): 순서 제약만 (g1 ≥ g2 ≥ g3, 식약처 등급 정의)

보고 지표 (결과 산출 전 확정):
  - top5 유지율 : 핵심 (SMAA 순위 수용성 지수의 누적형)
  - 중앙 순위   : 대표값
  - 평균 순위   : 동점 정리용

강건성 검증: 적용공백 제외 3변수 SMAA를 함께 산출해 순위 변화 비교.
"""

import csv
import math
import numpy as np

IN_PATH = "data/processed/merged20.csv"
OUT_PATH = "data/processed/smaa_ranks.csv"
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
    """부적합률 소표본 보정 (경험적 베이즈)"""
    mask = (insp > 0) & ~np.isnan(fail)
    tf, ti = fail[mask].sum(), insp[mask].sum()
    pm = tf / ti if ti else 0
    obs = fail[mask] / insp[mask]
    mean, var = obs.mean(), obs.var()
    conc = max((mean * (1 - mean) / var) - 1, 1.0) if var > 0 and 0 < mean < 1 else 100.0
    a, b = pm * conc, (1 - pm) * conc
    out = np.full(len(insp), np.nan)
    out[mask] = (fail[mask] + a) / (insp[mask] + a + b)
    return out, a, b, pm


def spearman(x, y):
    """순위 상관 (scipy 없이)"""
    def rank(v):
        order = np.argsort(v)
        r = np.empty(len(v), float)
        r[order] = np.arange(1, len(v) + 1)
        # 동점 평균 처리
        for val in set(v):
            idx = [i for i, t in enumerate(v) if t == val]
            if len(idx) > 1:
                r[idx] = np.mean(r[idx])
        return r
    rx, ry = rank(list(x)), rank(list(y))
    return np.corrcoef(rx, ry)[0, 1]


def run_smaa(R, S, V, I, C, n_cat, use_gap=True, seed=SEED):
    """SMAA 시뮬레이션. use_gap=False면 적용공백 제외(3변수)"""
    rng = np.random.default_rng(seed)
    n_var = 4 if use_gap else 3
    rank_log = np.zeros((N, n_cat), dtype=int)

    for t in range(N):
        var_w = rng.dirichlet([1] * n_var)
        grade_w = np.sort(rng.random(3))[::-1]
        Imp = minmax(np.log((C @ grade_w) + 1))
        if use_gap:
            hip = var_w[0]*R + var_w[1]*S + var_w[2]*V + var_w[3]*Imp
        else:
            hip = var_w[0]*R + var_w[1]*S + var_w[2]*Imp
        rank_log[t] = np.argsort(np.argsort(-hip)) + 1
    return rank_log


def main():
    with open(IN_PATH, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    cats = [r["품목유형"] for r in rows]
    n_cat = len(cats)
    print(f"분석 대상: {n_cat}개 식품군\n")

    # 변수 준비
    insp = np.array([num(r, "검사건수") or np.nan for r in rows])
    fail = np.array([num(r, "부적합건수") if num(r, "부적합건수") is not None else np.nan for r in rows])
    risk_raw, alpha, beta, pm = beta_shrink(insp, fail)
    R = minmax(risk_raw)

    scale_raw = np.array([math.log10(num(r, "생산액_천원")) if num(r, "생산액_천원") else np.nan for r in rows])
    S = minmax(scale_raw)

    gap_raw = np.array([(1 - num(r, "HACCP_인증률")) if num(r, "HACCP_인증률") is not None else np.nan for r in rows])
    V = minmax(gap_raw)

    C = np.array([[num(r, "Recall_1등급") or 0, num(r, "Recall_2등급") or 0,
                   num(r, "Recall_3등급") or 0] for r in rows])
    recall_total = C.sum(axis=1)

    print(f"베타-이항 축소: 전체 평균 부적합률 {pm*100:.3f}%, α={alpha:.3f}, β={beta:.1f}")
    print(f"  → 검사 약 {alpha+beta:.0f}건 이상부터 관측값 신뢰\n")

    # ── Scale-Impact 상관 (이중 반영 진단) ──
    rho = spearman(S, recall_total)
    log_recall = np.log(recall_total + 1)
    pear = np.corrcoef(S, log_recall)[0, 1]
    print("[진단] Scale과 Impact의 겹침")
    print("-" * 50)
    print(f"  순위상관(Scale, 회수건수)  = {rho:.2f}")
    print(f"  상관계수(Scale, log회수)   = {pear:.2f}  (설명력 {pear**2*100:.0f}%)")
    print("  → 규모가 큰 식품군이 회수도 많은 경향이 일부 존재")
    print("  → Impact(건수)에 규모 효과가 부분 반영됨. 한계로 명시\n")

    # ── SMAA 실행 ──
    print(f"SMAA 실행 중 (N={N:,})...")
    ranks4 = run_smaa(R, S, V, C, n_cat, use_gap=True)
    ranks3 = run_smaa(R, S, V, C, n_cat, use_gap=False)

    med4 = np.median(ranks4, axis=0)
    mean4 = ranks4.mean(axis=0)
    top5_4 = (ranks4 <= 5).mean(axis=0) * 100
    med3 = np.median(ranks3, axis=0)
    top5_3 = (ranks3 <= 5).mean(axis=0) * 100

    # 정렬: 중앙순위 → 평균순위(동점 정리)
    order = sorted(range(n_cat), key=lambda i: (med4[i], mean4[i]))

    # ── 출력: 4변수 ──
    print("\n" + "=" * 86)
    print(f"SMAA 결과 — 4변수 (Risk + Scale + 적용공백 + Impact), N={N:,}")
    print("=" * 86)
    print(f"{'품목유형':<22}{'적용구분':<14}{'중앙':>5}{'평균':>7}{'top5%':>8}{'최선':>5}{'최악':>5}")
    print("-" * 86)
    for i in order:
        cls = rows[i].get("적용구분", "")
        r = ranks4[:, i]
        print(f"{cats[i]:<22}{cls:<14}{med4[i]:>5.0f}{mean4[i]:>7.1f}"
              f"{top5_4[i]:>7.1f}%{r.min():>5}{r.max():>5}")

    # ── 출력: 3변수 비교 (강건성) ──
    print("\n" + "=" * 86)
    print("[강건성 검증] 적용공백 제외 시 순위 변화")
    print("=" * 86)
    print(f"{'품목유형':<22}{'4변수중앙':>9}{'3변수중앙':>9}{'변화':>7}"
          f"{'4변수top5':>10}{'3변수top5':>10}{'판정':>12}")
    print("-" * 86)
    for i in order:
        diff = med3[i] - med4[i]
        if abs(diff) <= 2:
            verdict = "적용공백 무관"
        elif diff > 2:
            verdict = "적용공백 의존"
        else:
            verdict = "적용공백에 눌림"
        print(f"{cats[i]:<22}{med4[i]:>9.0f}{med3[i]:>9.0f}{diff:>+7.0f}"
              f"{top5_4[i]:>9.1f}%{top5_3[i]:>9.1f}%{verdict:>12}")

    # ── 저장 ──
    with open(OUT_PATH, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["품목유형", "적용구분", "중앙순위", "평균순위", "top5_유지율",
                    "최선", "최악", "중앙순위_3변수", "top5_3변수", "순위변화"])
        for i in order:
            r = ranks4[:, i]
            w.writerow([cats[i], rows[i].get("적용구분", ""),
                        f"{med4[i]:.0f}", f"{mean4[i]:.2f}", f"{top5_4[i]:.1f}",
                        r.min(), r.max(), f"{med3[i]:.0f}", f"{top5_3[i]:.1f}",
                        f"{med3[i]-med4[i]:+.0f}"])

    np.save("data/processed/smaa_ranks_full.npy", ranks4)
    np.save("data/processed/smaa_ranks3_full.npy", ranks3)
    np.save("data/processed/smaa_cats.npy", np.array(cats))

    # 상관 결과도 별도 저장
    with open("data/processed/scale_impact_corr.txt", "w", encoding="utf-8") as f:
        f.write(f"Spearman(Scale, 회수건수) = {rho:.3f}\n")
        f.write(f"Pearson(Scale, log회수)   = {pear:.3f}\n")
        f.write(f"R^2 = {pear**2:.3f}\n")

    print(f"\n저장: {OUT_PATH}")
    print("저장: smaa_ranks_full.npy, smaa_ranks3_full.npy (박스플롯용)")
    print("저장: scale_impact_corr.txt")


if __name__ == "__main__":
    main()
