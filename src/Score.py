"""
3단계: 투자 우선순위 스코어링 (v4 - 4변수 HIP + 이중 민감도)
============================================
입력: data/processed/merged.csv (Impact_321 등 4버전 포함)
출력: data/processed/scores.csv

HIP = (Risk + Scale + Vulnerability + Impact) / 4   # 동일가중
  Risk          = 부적합률 (베타-이항 축소 → min-max)
  Scale         = 생산액 (log10 → min-max)
  Vulnerability = 1 - HACCP인증률 (min-max)
  Impact        = 등급가중 회수 Impact_321 (log(x+1) → min-max)

민감도 2종:
  1) 변수 가중치 (Risk/Scale/Vuln/Impact 비중 변경)
  2) 등급 가중치 (3:2:1 / 2:1.5:1 / 5:3:1 / 1:1:1)
"""

import csv
import os
import math

IN_PATH = "data/processed/merged.csv"
OUT_PATH = "data/processed/scores.csv"

IMPACT_DEFAULT = "Impact_321"
IMPACT_VERSIONS = ["Impact_321", "Impact_2_15_1", "Impact_531", "Impact_111"]


def to_num(s):
    if s is None or str(s).strip() in ("", "-"):
        return None
    try:
        return float(str(s).replace(",", ""))
    except ValueError:
        return None


def minmax_normalize(values):
    valid = [v for v in values if v is not None]
    if not valid:
        return values
    lo, hi = min(valid), max(valid)
    if hi == lo:
        return [0.5 if v is not None else None for v in values]
    return [(v - lo) / (hi - lo) if v is not None else None for v in values]


def load_data():
    with open(IN_PATH, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def beta_binomial_shrinkage(rows):
    """부적합률 소표본 보정 (Empirical Bayes)"""
    data = []
    for r in rows:
        insp = to_num(r.get("검사건수"))
        fail = to_num(r.get("부적합건수"))
        if insp is not None and insp > 0 and fail is not None:
            data.append((r["품목유형"], insp, fail))
    total_fail = sum(f for _, _, f in data)
    total_insp = sum(i for _, i, f in data)
    prior_mean = total_fail / total_insp if total_insp > 0 else 0.0
    obs = [f / i for _, i, f in data]
    n = len(obs); mean = sum(obs)/n
    var = sum((x-mean)**2 for x in obs)/n if n > 1 else 0.0
    if var > 0 and 0 < mean < 1:
        conc = max((mean*(1-mean)/var) - 1, 1.0)
    else:
        conc = 100.0
    alpha, beta = prior_mean*conc, (1-prior_mean)*conc
    return {name: (fail+alpha)/(insp+alpha+beta) for name, insp, fail in data}


def base_variables(rows, impact_col=IMPACT_DEFAULT):
    cats = [r["품목유형"] for r in rows]
    shrunk = beta_binomial_shrinkage(rows)
    risk_raw = [shrunk.get(c) for c in cats]
    scale_raw = [math.log10(to_num(r.get("생산액_천원"))) if to_num(r.get("생산액_천원")) else None for r in rows]
    vuln_raw = [(1 - to_num(r.get("HACCP_인증률"))) if to_num(r.get("HACCP_인증률")) is not None else None for r in rows]
    impact_raw = [math.log((to_num(r.get(impact_col)) or 0.0) + 1) for r in rows]
    return cats, risk_raw, scale_raw, vuln_raw, impact_raw


def norm_fill(xs):
    return [x if x is not None else 0.0 for x in minmax_normalize(xs)]


def compute_hip(rows, impact_col=IMPACT_DEFAULT, weights=(0.25, 0.25, 0.25, 0.25)):
    cats, risk_raw, scale_raw, vuln_raw, impact_raw = base_variables(rows, impact_col)
    R, S, V, I = norm_fill(risk_raw), norm_fill(scale_raw), norm_fill(vuln_raw), norm_fill(impact_raw)
    wr, ws, wv, wi = weights
    scored = [(cats[i], wr*R[i]+ws*S[i]+wv*V[i]+wi*I[i], R[i], S[i], V[i], I[i]) for i in range(len(cats))]
    scored.sort(key=lambda x: -x[1])
    return scored


def main():
    rows = load_data()

    # 기본 HIP
    scored = compute_hip(rows)
    results = [{"Rank": i+1, "품목유형": s[0], "HIP": s[1],
                "Risk": s[2], "Scale": s[3], "Vulnerability": s[4], "Impact": s[5]}
               for i, s in enumerate(scored)]

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Rank", "품목유형", "Risk", "Scale", "Vulnerability", "Impact", "HIP"])
        for r in results:
            w.writerow([r["Rank"], r["품목유형"], f"{r['Risk']:.4f}", f"{r['Scale']:.4f}",
                        f"{r['Vulnerability']:.4f}", f"{r['Impact']:.4f}", f"{r['HIP']:.4f}"])

    print("=" * 78)
    print("HACCP 투자 우선순위 (HIP) - 4변수 동일가중, Impact=3:2:1")
    print("=" * 78)
    print(f"{'순위':>3} {'품목유형':<20}{'Risk':>7}{'Scale':>7}{'Vuln':>7}{'Impact':>7}{'HIP':>8}")
    print("-" * 78)
    for r in results:
        print(f"{r['Rank']:>3} {r['품목유형']:<20}{r['Risk']:>7.3f}{r['Scale']:>7.3f}"
              f"{r['Vulnerability']:>7.3f}{r['Impact']:>7.3f}{r['HIP']:>8.3f}")

    # 민감도 1: 변수 가중치
    print("\n" + "=" * 78)
    print("[민감도 1] 변수 가중치 변경")
    print("=" * 78)
    var_scenarios = {
        "동일":     (0.25, 0.25, 0.25, 0.25),
        "Risk↑":   (0.40, 0.20, 0.20, 0.20),
        "Scale↑":  (0.20, 0.40, 0.20, 0.20),
        "Vuln↑":   (0.20, 0.20, 0.40, 0.20),
        "Impact↑": (0.20, 0.20, 0.20, 0.40),
    }
    var_ranks = {}
    for name, w in var_scenarios.items():
        sc = compute_hip(rows, weights=w)
        var_ranks[name] = {cat: i+1 for i, (cat, *_) in enumerate(sc)}
    base = var_ranks["동일"]
    print(f"{'품목유형':<20}" + "".join(f"{n:>9}" for n in var_scenarios))
    print("-" * 78)
    for cat in sorted(base, key=lambda c: base[c]):
        print(f"{cat:<20}" + "".join(f"{var_ranks[n][cat]:>9}" for n in var_scenarios))

    # 민감도 2: 등급 가중치
    print("\n" + "=" * 78)
    print("[민감도 2] 회수등급 가중치 변경 (변수는 동일가중)")
    print("=" * 78)
    grade_ranks = {}
    for ver in IMPACT_VERSIONS:
        sc = compute_hip(rows, impact_col=ver)
        grade_ranks[ver] = {cat: i+1 for i, (cat, *_) in enumerate(sc)}
    label = {"Impact_321": "3:2:1", "Impact_2_15_1": "2:1.5:1", "Impact_531": "5:3:1", "Impact_111": "1:1:1"}
    base2 = grade_ranks["Impact_321"]
    print(f"{'품목유형':<20}" + "".join(f"{label[v]:>10}" for v in IMPACT_VERSIONS))
    print("-" * 78)
    for cat in sorted(base2, key=lambda c: base2[c]):
        print(f"{cat:<20}" + "".join(f"{grade_ranks[v][cat]:>10}" for v in IMPACT_VERSIONS))

    print("\n[등급 가중치 민감도] 순위 변동폭")
    print("-" * 78)
    for cat in sorted(base2, key=lambda c: base2[c]):
        vals = [grade_ranks[v][cat] for v in IMPACT_VERSIONS]
        spread = max(vals) - min(vals)
        stab = "안정" if spread <= 2 else ("보통" if spread <= 5 else "변동큼")
        print(f"  {base2[cat]:>2}위 {cat:<20} ±{spread:>2} ({stab})")

    print(f"\n저장: {OUT_PATH}")


if __name__ == "__main__":
    main()
