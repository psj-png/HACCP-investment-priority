"""
SMAA (Stochastic Multicriteria Acceptability Analysis)
============================================
입력: data/processed/merged20.csv
출력: smaa_ranks.csv, smaa_ranks_full.npy, smaa_ranks3_full.npy

검증 3종:
  1) 가중치 무작위 1만 회 (SMAA 본체)
  2) 적용공백 제외 3변수 비교 → 적용공백 의존도
  3) Impact 처리 방식 3버전 비교 → 기간·중복 처리 영향

Impact 버전:
  Recall_      2024년 이후, 중복 제거  (주 분석)
  RecallDup_   2024년 이후, 중복 포함  (민감도 A)
  RecallAll_   전체 누적,   중복 제거  (민감도 B)
"""

import csv
import math
import numpy as np

IN_PATH = "data/processed/merged20.csv"
OUT_PATH = "data/processed/smaa_ranks.csv"
N = 10000
SEED = 42

IMPACT_VERSIONS = {
    "주분석(24~·중복제거)": "Recall",
    "민감도A(24~·중복포함)": "RecallDup",
    "민감도B(전체·중복제거)": "RecallAll",
}


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
    return out, a, b, pm


def spearman(x, y):
    def rank(v):
        v = list(v)
        order = np.argsort(v)
        r = np.empty(len(v), float)
        r[order] = np.arange(1, len(v) + 1)
        for val in set(v):
            idx = [i for i, t in enumerate(v) if t == val]
            if len(idx) > 1:
                r[idx] = np.mean(r[idx])
        return r
    return np.corrcoef(rank(x), rank(y))[0, 1]


def run_smaa(R, S, V, C, n_cat, use_gap=True, seed=SEED):
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


def grade_matrix(rows, prefix):
    """등급별 건수 행렬 (n_cat × 3)"""
    return np.array([[num(r, f"{prefix}_1등급") or 0,
                      num(r, f"{prefix}_2등급") or 0,
                      num(r, f"{prefix}_3등급") or 0] for r in rows])


def main():
    with open(IN_PATH, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    cats = [r["품목유형"] for r in rows]
    n_cat = len(cats)
    print(f"분석 대상: {n_cat}개 식품군\n")

    # 고정 변수
    insp = np.array([num(r, "검사건수") or np.nan for r in rows])
    fail = np.array([num(r, "부적합건수") if num(r, "부적합건수") is not None else np.nan for r in rows])
    risk_raw, alpha, beta, pm = beta_shrink(insp, fail)
    R = minmax(risk_raw)
    scale_raw = np.array([math.log10(num(r, "생산액_천원")) if num(r, "생산액_천원") else np.nan for r in rows])
    S = minmax(scale_raw)
    gap_raw = np.array([(1 - num(r, "HACCP_인증률")) if num(r, "HACCP_인증률") is not None else np.nan for r in rows])
    V = minmax(gap_raw)

    C = grade_matrix(rows, "Recall")          # 주 분석
    recall_total = C.sum(axis=1)

    print(f"베타-이항 축소: 전체 평균 부적합률 {pm*100:.3f}%, α={alpha:.3f}, β={beta:.1f}\n")

    rho = spearman(S, recall_total)
    pear = np.corrcoef(S, np.log(recall_total + 1))[0, 1]
    print("[진단] Scale-Impact 겹침")
    print(f"  순위상관 {rho:.2f} / 상관계수 {pear:.2f} (설명력 {pear**2*100:.0f}%)")
    print("  → Impact(건수)에 규모 효과 부분 반영. 한계로 명시\n")

    # ── SMAA 본체 (주 분석) ──
    print(f"SMAA 실행 중 (N={N:,})...")
    ranks4 = run_smaa(R, S, V, C, n_cat, use_gap=True)
    ranks3 = run_smaa(R, S, V, C, n_cat, use_gap=False)

    med4 = np.median(ranks4, axis=0)
    mean4 = ranks4.mean(axis=0)
    top5_4 = (ranks4 <= 5).mean(axis=0) * 100
    med3 = np.median(ranks3, axis=0)
    top5_3 = (ranks3 <= 5).mean(axis=0) * 100
    order = sorted(range(n_cat), key=lambda i: (med4[i], mean4[i]))

    print("\n" + "=" * 86)
    print(f"SMAA — 4변수 (주 분석), N={N:,}")
    print("=" * 86)
    print(f"{'품목유형':<22}{'적용구분':<14}{'중앙':>5}{'평균':>7}{'top5%':>8}{'최선':>5}{'최악':>5}")
    print("-" * 86)
    for i in order:
        r = ranks4[:, i]
        print(f"{cats[i]:<22}{rows[i].get('적용구분',''):<14}{med4[i]:>5.0f}{mean4[i]:>7.1f}"
              f"{top5_4[i]:>7.1f}%{r.min():>5}{r.max():>5}")

    # ── 검증 1: 적용공백 제외 ──
    print("\n" + "=" * 86)
    print("[검증 1] 적용공백 제외 시 순위 변화")
    print("=" * 86)
    print(f"{'품목유형':<22}{'4변수':>7}{'3변수':>7}{'변화':>7}{'4변수top5':>11}{'3변수top5':>11}{'판정':>14}")
    print("-" * 86)
    for i in order:
        d = med3[i] - med4[i]
        verdict = "적용공백 무관" if abs(d) <= 2 else ("적용공백 의존" if d > 2 else "적용공백에 눌림")
        print(f"{cats[i]:<22}{med4[i]:>7.0f}{med3[i]:>7.0f}{d:>+7.0f}"
              f"{top5_4[i]:>10.1f}%{top5_3[i]:>10.1f}%{verdict:>14}")

    # ── 검증 2: Impact 처리 방식 3버전 ──
    print("\n" + "=" * 86)
    print("[검증 2] Impact 처리 방식별 순위 비교")
    print("=" * 86)
    ver_results = {}
    for label, prefix in IMPACT_VERSIONS.items():
        Cv = grade_matrix(rows, prefix)
        rk = run_smaa(R, S, V, Cv, n_cat, use_gap=True)
        ver_results[label] = {
            "med": np.median(rk, axis=0),
            "top5": (rk <= 5).mean(axis=0) * 100,
            "n": int(Cv.sum()),
        }
    labels = list(IMPACT_VERSIONS.keys())
    print(f"{'품목유형':<22}" + "".join(f"{l:>22}" for l in labels))
    print(f"{'  (총 회수건수)':<22}" + "".join(f"{ver_results[l]['n']:>22}" for l in labels))
    print("-" * 86)
    for i in order:
        line = f"{cats[i]:<22}"
        for l in labels:
            line += f"{ver_results[l]['med'][i]:>13.0f}위{ver_results[l]['top5'][i]:>7.1f}%"
        print(line)

    # 상위 5개 일치 여부
    print("-" * 86)
    tops = {}
    for l in labels:
        m = ver_results[l]["med"]
        tops[l] = set(np.argsort(m)[:5])
    common = set.intersection(*tops.values())
    print(f"세 버전 공통 상위 5: {len(common)}개 — {', '.join(cats[i] for i in sorted(common, key=lambda x: ver_results[labels[0]]['med'][x]))}")
    for l in labels[1:]:
        diff = tops[labels[0]] ^ tops[l]
        if diff:
            print(f"  {l}에서만 차이: {', '.join(cats[i] for i in diff)}")

    # ── 저장 ──
    with open(OUT_PATH, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        header = ["품목유형", "적용구분", "중앙순위", "평균순위", "top5_유지율", "최선", "최악",
                  "중앙순위_3변수", "top5_3변수", "순위변화"]
        for l in labels[1:]:
            header += [f"중앙_{l}", f"top5_{l}"]
        w.writerow(header)
        for i in order:
            r = ranks4[:, i]
            row = [cats[i], rows[i].get("적용구분", ""), f"{med4[i]:.0f}", f"{mean4[i]:.2f}",
                   f"{top5_4[i]:.1f}", r.min(), r.max(),
                   f"{med3[i]:.0f}", f"{top5_3[i]:.1f}", f"{med3[i]-med4[i]:+.0f}"]
            for l in labels[1:]:
                row += [f"{ver_results[l]['med'][i]:.0f}", f"{ver_results[l]['top5'][i]:.1f}"]
            w.writerow(row)

    np.save("data/processed/smaa_ranks_full.npy", ranks4)
    np.save("data/processed/smaa_ranks3_full.npy", ranks3)
    np.save("data/processed/smaa_cats.npy", np.array(cats))
    print(f"\n저장: {OUT_PATH}, smaa_ranks_full.npy, smaa_ranks3_full.npy")


if __name__ == "__main__":
    main()
