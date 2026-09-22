"""
3단계: 투자 우선순위 스코어링 (v5 - 몬테카를로 연계)
============================================
입력: data/processed/merged.csv (Recall_1/2/3등급 포함)
      data/processed/montecarlo_ranks.csv (montecarlo.py 실행 후 생성)
출력: data/processed/scores.csv

최종 순위는 montecarlo.py의 중앙순위를 정본으로 사용.
이 스크립트는 참고용 단일 기준(등급 3:2:1, 변수 동일가중) HIP를 계산하고,
몬테카를로 중앙순위와 병기한다.

* 몬테카를로를 먼저 실행: python montecarlo.py
"""

import csv
import os
import math

MERGED = "data/processed/merged.csv"
MC_RANKS = "data/processed/montecarlo_ranks.csv"
OUT = "data/processed/scores.csv"
GRADE_W = [3.0, 2.0, 1.0]   # 참고용 단일 기준 (몬테카를로 순서제약의 한 예시)


def num(r, k):
    v = r.get(k, "")
    try:
        return float(v) if str(v).strip() not in ("", "-") else None
    except ValueError:
        return None


def minmax(vals):
    valid = [v for v in vals if v is not None]
    if not valid:
        return vals
    lo, hi = min(valid), max(valid)
    if hi == lo:
        return [0.5 if v is not None else None for v in vals]
    return [(v - lo) / (hi - lo) if v is not None else None for v in vals]


def beta_shrink(rows):
    data = [(r["품목유형"], num(r, "검사건수"), num(r, "부적합건수"))
            for r in rows if num(r, "검사건수") and num(r, "부적합건수") is not None]
    tf = sum(f for _, _, f in data); ti = sum(i for _, i, _ in data)
    pm = tf / ti if ti else 0
    obs = [f / i for _, i, f in data]; nn = len(obs); mean = sum(obs) / nn
    var = sum((x - mean) ** 2 for x in obs) / nn if nn > 1 else 0
    conc = max((mean * (1 - mean) / var) - 1, 1.0) if var > 0 and 0 < mean < 1 else 100.0
    a, b = pm * conc, (1 - pm) * conc
    return {nm: (f + a) / (i + a + b) for nm, i, f in data}


def load_mc_ranks():
    if not os.path.exists(MC_RANKS):
        return None
    with open(MC_RANKS, encoding="utf-8-sig") as f:
        return {r["품목유형"]: r for r in csv.DictReader(f)}


def compute_reference_hip(rows):
    cats = [r["품목유형"] for r in rows]
    shrunk = beta_shrink(rows)
    risk_raw = [shrunk.get(c) for c in cats]
    scale_raw = [math.log10(num(r, "생산액_천원")) if num(r, "생산액_천원") else None for r in rows]
    vuln_raw = [(1 - num(r, "HACCP_인증률")) if num(r, "HACCP_인증률") is not None else None for r in rows]

    impact_raw = []
    for r in rows:
        c1 = num(r, "Recall_1등급") or 0
        c2 = num(r, "Recall_2등급") or 0
        c3 = num(r, "Recall_3등급") or 0
        weighted = c1*GRADE_W[0] + c2*GRADE_W[1] + c3*GRADE_W[2]
        impact_raw.append(math.log(weighted + 1))

    fill = lambda xs: [x if x is not None else 0.0 for x in minmax(xs)]
    R, S, V, I = fill(risk_raw), fill(scale_raw), fill(vuln_raw), fill(impact_raw)

    result = []
    for i, c in enumerate(cats):
        hip = (R[i] + S[i] + V[i] + I[i]) / 4
        result.append({"품목유형": c, "Risk": R[i], "Scale": S[i],
                       "Vulnerability": V[i], "Impact": I[i], "HIP_ref": hip})
    result.sort(key=lambda x: -x["HIP_ref"])
    for rk, r in enumerate(result, 1):
        r["HIP_ref_rank"] = rk
    return result


def main():
    with open(MERGED, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    ref = compute_reference_hip(rows)
    mc = load_mc_ranks()

    for r in ref:
        cat = r["품목유형"]
        if mc and cat in mc:
            r["MC_median_rank"] = int(float(mc[cat]["중앙순위"]))
            r["MC_top5_rate"] = mc[cat]["top5_유지율"]
            r["MC_best"] = mc[cat]["최선"]
            r["MC_worst"] = mc[cat]["최악"]
        else:
            r["MC_median_rank"] = None

    if mc:
        ref.sort(key=lambda x: (x["MC_median_rank"], -x["HIP_ref"]))
    for rk, r in enumerate(ref, 1):
        r["최종순위"] = rk

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8-sig", newline="") as f:
        cols = ["최종순위", "품목유형", "Risk", "Scale", "Vulnerability", "Impact",
                "HIP_ref", "MC_median_rank", "MC_top5_rate", "MC_best", "MC_worst"]
        w = csv.writer(f)
        w.writerow(cols)
        for r in ref:
            w.writerow([r["최종순위"], r["품목유형"],
                        f"{r['Risk']:.4f}", f"{r['Scale']:.4f}",
                        f"{r['Vulnerability']:.4f}", f"{r['Impact']:.4f}",
                        f"{r['HIP_ref']:.4f}",
                        r.get("MC_median_rank", ""), r.get("MC_top5_rate", ""),
                        r.get("MC_best", ""), r.get("MC_worst", "")])

    print("=" * 78)
    if mc:
        print("HACCP 투자 우선순위 — 최종 (몬테카를로 중앙순위 정본)")
    else:
        print("HACCP 투자 우선순위 — 참고 단일기준 (몬테카를로 미실행)")
        print("※ montecarlo.py를 먼저 실행하면 몬테카를로 순위가 병기됩니다")
    print("=" * 78)
    header = f"{'순위':>3} {'품목유형':<20}{'Risk':>6}{'Scale':>6}{'Vuln':>6}{'Impact':>7}{'HIP':>7}"
    if mc:
        header += f"{'MC중앙':>7}{'top5%':>7}"
    print(header)
    print("-" * 78)
    for r in ref:
        line = (f"{r['최종순위']:>3} {r['품목유형']:<20}"
                f"{r['Risk']:>6.3f}{r['Scale']:>6.3f}{r['Vulnerability']:>6.3f}"
                f"{r['Impact']:>7.3f}{r['HIP_ref']:>7.3f}")
        if mc and r.get("MC_median_rank"):
            line += f"{r['MC_median_rank']:>7}{r['MC_top5_rate']:>6}%"
        print(line)

    print(f"\n저장: {OUT}")


if __name__ == "__main__":
    main()
