"""
최종 순위표 (v6 - 20개, SMAA 정본, 2×2 분류 포함)
============================================
입력: data/processed/merged20.csv, data/processed/smaa_ranks.csv
출력: data/processed/scores20.csv

- 순위: SMAA 중앙순위 정본 (동점은 평균순위로 정리)
- 참고 HIP: 등급 3:2:1, 변수 동일가중 (단일 기준 예시)
- 2×2 분류: 가로=적용공백, 세로=부적합률, 기준선=각 축 중앙값
            회수 건수는 칸 결정에 미사용 (중앙값 이상이면 해석 플래그)
"""

import csv
import os
import math

MERGED = "data/processed/merged20.csv"
SMAA = "data/processed/smaa_ranks.csv"
OUT = "data/processed/scores20.csv"
GRADE_W = [3.0, 2.0, 1.0]   # 참고용 단일 기준


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


def median(vals):
    s = sorted(v for v in vals if v is not None)
    n = len(s)
    return (s[n//2] if n % 2 else (s[n//2-1] + s[n//2]) / 2) if n else 0


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


def classify_2x2(gap, risk, gap_med, risk_med):
    """2×2 분류. 칸은 적용공백×부적합률로만 결정"""
    high_gap = gap >= gap_med
    high_risk = risk >= risk_med
    if high_gap and high_risk:
        return "① 공백+위해 (우선 검토)"
    if high_gap and not high_risk:
        return "② 공백만 (시급성 낮음)"
    if not high_gap and high_risk:
        return "③ 적용됐으나 위해 신호"
    return "④ 안정"


def main():
    with open(MERGED, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    cats = [r["품목유형"] for r in rows]

    # SMAA 결과
    smaa = {}
    if os.path.exists(SMAA):
        with open(SMAA, encoding="utf-8-sig") as f:
            smaa = {r["품목유형"]: r for r in csv.DictReader(f)}
    else:
        print("[주의] SMAA 결과 없음 → montecarlo.py 먼저 실행 권장\n")

    # 변수 계산
    shrunk = beta_shrink(rows)
    risk_raw = [shrunk.get(c) for c in cats]
    scale_raw = [math.log10(num(r, "생산액_천원")) if num(r, "생산액_천원") else None for r in rows]
    gap_raw = [(1 - num(r, "HACCP_인증률")) if num(r, "HACCP_인증률") is not None else None for r in rows]
    impact_raw = []
    recall_total = []
    for r in rows:
        c1 = num(r, "Recall_1등급") or 0
        c2 = num(r, "Recall_2등급") or 0
        c3 = num(r, "Recall_3등급") or 0
        impact_raw.append(math.log(c1*GRADE_W[0] + c2*GRADE_W[1] + c3*GRADE_W[2] + 1))
        recall_total.append(c1 + c2 + c3)

    fill = lambda xs: [x if x is not None else 0.0 for x in minmax(xs)]
    R, S, V, I = fill(risk_raw), fill(scale_raw), fill(gap_raw), fill(impact_raw)

    # 2×2 기준선 (중앙값)
    gap_med, risk_med, recall_med = median(V), median(R), median(recall_total)

    result = []
    for i, c in enumerate(cats):
        hip = (R[i] + S[i] + V[i] + I[i]) / 4
        quad = classify_2x2(V[i], R[i], gap_med, risk_med)
        row = {
            "품목유형": c, "적용구분": rows[i].get("적용구분", ""),
            "Risk": R[i], "Scale": S[i], "적용공백": V[i], "Impact": I[i],
            "HIP_ref": hip, "회수건수": recall_total[i],
            "회수_플래그": "회수 다수" if recall_total[i] >= recall_med else "",
            "2x2": quad,
        }
        if c in smaa:
            row["SMAA_중앙"] = int(float(smaa[c]["중앙순위"]))
            row["SMAA_평균"] = float(smaa[c]["평균순위"])
            row["top5%"] = smaa[c]["top5_유지율"]
            row["3변수중앙"] = int(float(smaa[c]["중앙순위_3변수"]))
            row["순위변화"] = smaa[c]["순위변화"]
        result.append(row)

    # 정렬: SMAA 중앙 → 평균 (없으면 참고 HIP)
    if smaa:
        result.sort(key=lambda x: (x["SMAA_중앙"], x["SMAA_평균"]))
    else:
        result.sort(key=lambda x: -x["HIP_ref"])
    for rk, r in enumerate(result, 1):
        r["최종순위"] = rk

    # 출력
    print("=" * 100)
    print("HACCP 투자 우선순위 — 20개 식품군 (SMAA 중앙순위 정본)")
    print("=" * 100)
    hdr = f"{'순위':>3} {'품목유형':<22}{'적용구분':<13}{'Risk':>6}{'Scale':>6}{'공백':>6}{'Impact':>7}"
    if smaa:
        hdr += f"{'top5%':>7}{'3변수':>6}"
    hdr += f"  {'2×2 분류':<22}{'회수'}"
    print(hdr)
    print("-" * 100)
    for r in result:
        line = (f"{r['최종순위']:>3} {r['품목유형']:<22}{r['적용구분']:<13}"
                f"{r['Risk']:>6.3f}{r['Scale']:>6.3f}{r['적용공백']:>6.3f}{r['Impact']:>7.3f}")
        if smaa:
            line += f"{r['top5%']:>6}%{r['3변수중앙']:>6}"
        line += f"  {r['2x2']:<22}{r['회수_플래그']}"
        print(line)

    print("-" * 100)
    print(f"2×2 기준선(중앙값): 적용공백 {gap_med:.3f} / 부적합률 {risk_med:.3f} / 회수 {recall_med:.0f}건")

    # 2×2 요약
    print("\n[2×2 분류 요약]")
    print("-" * 60)
    for q in ["① 공백+위해 (우선 검토)", "② 공백만 (시급성 낮음)",
              "③ 적용됐으나 위해 신호", "④ 안정"]:
        items = [r["품목유형"] for r in result if r["2x2"] == q]
        print(f"  {q:<24} {len(items)}개")
        if items:
            print(f"      {', '.join(items)}")

    # 저장
    with open(OUT, "w", encoding="utf-8-sig", newline="") as f:
        cols = ["최종순위", "품목유형", "적용구분", "Risk", "Scale", "적용공백", "Impact",
                "HIP_ref", "회수건수", "2x2", "회수_플래그"]
        if smaa:
            cols += ["SMAA_중앙", "SMAA_평균", "top5%", "3변수중앙", "순위변화"]
        w = csv.writer(f)
        w.writerow(cols)
        for r in result:
            w.writerow([r.get(c, "") if not isinstance(r.get(c), float)
                        else f"{r[c]:.4f}" for c in cols])

    print(f"\n저장: {OUT}")


if __name__ == "__main__":
    main()
