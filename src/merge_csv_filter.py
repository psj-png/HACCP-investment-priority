"""
20개 식품군 필터 + 적용구분 라벨
============================================
입력:  data/processed/merged.csv (23개)
출력:  data/processed/merged20.csv (20개 + 적용구분)

- 축산 3개(식육가공품·유가공품류·알가공품류) 제외
  → 「축산물 위생관리법」 제9조 이하 소관으로 「식품위생법」 제48조 체계와 법적 기반 상이
- 적용구분: 「식품위생법 시행규칙」 제62조 제1항 기준 (해석 전용, 점수·순위·2×2 미사용)
  [시행 2026.9.1] 총리령 제2150호
"""

import csv

IN_PATH = "data/processed/merged.csv"
OUT_PATH = "data/processed/merged20.csv"

EXCLUDE_LIVESTOCK = ["식육가공품", "유가공품류", "알가공품류"]

# 적용구분 3분류 (시행규칙 제62조 제1항)
#   대부분 의무      : 품목유형 대부분이 의무 대상
#   일부 의무        : 품목유형 내 특정 품목만 의무 대상
#   100억 기준 적용  : 품목별 의무대상은 아니나, 전년도 총매출액 100억원 이상
#                     식품제조·가공업 영업소에서 제조·가공하는 경우 적용 대상(제13호)
APPLY_CLASS = {
    # ── 대부분 의무 (5) ──
    "과자류, 빵류 또는 떡류": "대부분 의무",        # 제4호 과자·캔디류·빵류·떡류
    "음료류": "대부분 의무",                        # 제6호 (다류·커피류 제외)
    "면류": "대부분 의무",                          # 제10호 유탕면·생면·숙면·건면
    "특수영양식품": "대부분 의무",                  # 제11호
    "특수의료용도식품": "대부분 의무",              # 제11의2호

    # ── 일부 의무 (5) ──
    "빙과류": "일부 의무",                          # 제5호 빙과류 중 '빙과'만
    "코코아가공품류 또는 초콜릿류": "일부 의무",    # 제9호 '초콜릿류'만
    "수산가공식품류": "일부 의무",                  # 제1호 어묵·어육소시지, 제2호 냉동 어류·연체류·조미가공품
    "즉석식품류": "일부 의무",                      # 제12호 즉석섭취식품, 제12의2호 순대
    "절임류 또는 조림류": "일부 의무",              # 제8호 김치류 중 배추김치

    # ── 100억 기준 적용 (10) ── 제13호만 해당
    "장류": "100억 기준 적용",
    "조미식품": "100억 기준 적용",
    "농산가공식품류": "100억 기준 적용",
    "당류": "100억 기준 적용",
    "잼류": "100억 기준 적용",
    "두부류 또는 묵류": "100억 기준 적용",
    "식용유지류": "100억 기준 적용",
    "동물성가공식품류": "100억 기준 적용",
    "벌꿀 및 화분가공품류": "100억 기준 적용",
    "기타식품류": "100억 기준 적용",
}

# 근거 조항 (문서·표 각주용)
LEGAL_BASIS = {
    "대부분 의무":
        "시행규칙 제62조 제1항 제4·6·10·11·11의2호 — 품목유형 대부분이 의무 대상",
    "일부 의무":
        "시행규칙 제62조 제1항 제1·2·5·8·9·12·12의2호 — 품목유형 내 특정 품목만 의무 대상",
    "100억 기준 적용":
        "품목별 의무대상은 아니나, 전년도 총매출액 100억원 이상인 식품제조·가공업 "
        "영업소에서 제조·가공하는 경우 HACCP 적용 대상(제62조 제1항 제13호)",
}

FOOTNOTES = [
    "제62조 제1항 제3호(냉동식품 중 피자류·만두류·면류)와 제7호(레토르트식품)는 "
    "본 분석의 20개 식품군과 1:1 대응하지 않는 별도의 HACCP 의무대상 범주이므로, "
    "식품군별 의무 여부를 단순 비교할 때에는 별도로 고려한다.",
    "제62조 제1항 제13호(매출 100억원 이상 영업소)는 모든 식품군에 공통 적용되나, "
    "업종별 대형 업체 비중에 따라 실질 의무 범위는 상이할 수 있다.",
    "빙과류의 업체 수 통계에는 축산물 소관 아이스크림류 제조업체가 포함되었을 수 있어 "
    "적용공백이 과대 산출될 가능성이 있다(회수 사례는 빙과·샤베트·식용얼음만 확인).",
]


def main():
    with open(IN_PATH, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
        fieldnames = list(rows[0].keys())

    print(f"입력: {len(rows)}개 식품군")

    kept, removed = [], []
    for r in rows:
        (removed if r["품목유형"] in EXCLUDE_LIVESTOCK else kept).append(r)
    print(f"제외(축산물 위생관리법 소관): {len(removed)}개 → {[r['품목유형'] for r in removed]}")
    print(f"분석 대상: {len(kept)}개\n")

    if "적용구분" not in fieldnames:
        fieldnames.append("적용구분")

    missing = []
    for r in kept:
        cls = APPLY_CLASS.get(r["품목유형"])
        if cls is None:
            missing.append(r["품목유형"]); cls = "미분류"
        r["적용구분"] = cls
    if missing:
        print(f"[주의] 적용구분 미지정: {missing}\n")

    print(f"{'적용구분':<16}{'수':>3}  품목")
    print("-" * 90)
    for cls in ["대부분 의무", "일부 의무", "100억 기준 적용"]:
        items = [r["품목유형"] for r in kept if r["적용구분"] == cls]
        print(f"{cls:<16}{len(items):>3}  {', '.join(items)}")

    print("\n[진단] 적용구분별 HACCP 인증률")
    print("-" * 52)
    for cls in ["대부분 의무", "일부 의무", "100억 기준 적용"]:
        rates = []
        for r in kept:
            if r["적용구분"] != cls:
                continue
            try:
                rates.append(float(r.get("HACCP_인증률", "")) * 100)
            except (ValueError, TypeError):
                pass
        if rates:
            print(f"  {cls:<16} 평균 {sum(rates)/len(rates):>5.1f}%  "
                  f"(범위 {min(rates):.1f}~{max(rates):.1f}%)")

    with open(OUT_PATH, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader(); w.writerows(kept)
    print(f"\n저장: {OUT_PATH}")

    print("\n[근거 조항]")
    for k, v in LEGAL_BASIS.items():
        print(f"  · {k}: {v}")
    print("\n[각주]")
    for i, note in enumerate(FOOTNOTES, 1):
        print(f"  {i}) {note}")


if __name__ == "__main__":
    main()
