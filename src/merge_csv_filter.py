"""
20개 식품군 필터 + 적용구분 라벨
============================================
입력:  data/processed/merged.csv (23개)
출력:  data/processed/merged20.csv (20개 + 적용구분 컬럼)

- 축산 3개(식육가공품·유가공품류·알가공품류) 제외
  → 축산물 위생관리법 소관으로 식품위생법 체계와 법적 기반이 달라 분석 범위에서 제외
- 적용구분: 식품위생법 시행규칙 제62조 기준, 해석 전용 (점수·순위 계산에 미사용)
  ※ 식품공학 검증 후 LEGAL_BASIS의 조항 번호 보완 필요
"""

import csv

IN_PATH = "data/processed/merged.csv"
OUT_PATH = "data/processed/merged20.csv"

# 축산물 위생관리법 소관 → 제외
EXCLUDE_LIVESTOCK = ["식육가공품", "유가공품류", "알가공품류"]

# 적용구분 (해석 전용)
#   대부분 의무 : 품목유형 대부분이 의무 대상
#   일부 의무   : 품목유형 내 특정 품목만 의무 대상
#   품목 의무 없음 : 품목 단위 의무 없음 (매출 100억 이상 업소 기준만 적용)
# ※ 100억 원 이상 식품제조·가공업소 기준은 모든 식품군에 공통 적용됨
APPLY_CLASS = {
    "과자류, 빵류 또는 떡류": "대부분 의무",
    "특수영양식품": "대부분 의무",
    "특수의료용도식품": "대부분 의무",
    "코코아가공품류 또는 초콜릿류": "대부분 의무",
    "면류": "대부분 의무",
    "빙과류": "대부분 의무",
    "음료류": "대부분 의무",

    "즉석식품류": "일부 의무",
    "수산가공식품류": "일부 의무",
    "절임류 또는 조림류": "일부 의무",

    "장류": "품목 의무 없음",
    "조미식품": "품목 의무 없음",
    "농산가공식품류": "품목 의무 없음",
    "당류": "품목 의무 없음",
    "잼류": "품목 의무 없음",
    "두부류 또는 묵류": "품목 의무 없음",
    "식용유지류": "품목 의무 없음",
    "동물성가공식품류": "품목 의무 없음",
    "벌꿀 및 화분가공품류": "품목 의무 없음",
    "기타식품류": "품목 의무 없음",
}

# 근거 메모 (친구 검증 후 조항 번호 보완)
LEGAL_BASIS = {
    "대부분 의무": "식품위생법 시행규칙 제62조 제1항 - 해당 품목유형 대부분이 의무 대상",
    "일부 의무": "식품위생법 시행규칙 제62조 제1항 - 품목유형 내 특정 품목만 의무 대상",
    "품목 의무 없음": "품목 단위 의무 없음. 제62조 제1항 제13호(매출 100억 이상 업소) 기준만 적용",
}


def main():
    with open(IN_PATH, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
        fieldnames = list(rows[0].keys())

    print(f"입력: {len(rows)}개 식품군")

    # 축산 제외
    kept, removed = [], []
    for r in rows:
        (removed if r["품목유형"] in EXCLUDE_LIVESTOCK else kept).append(r)

    print(f"제외(축산물 위생관리법 소관): {len(removed)}개 → {[r['품목유형'] for r in removed]}")
    print(f"분석 대상: {len(kept)}개\n")

    # 적용구분 부여
    if "적용구분" not in fieldnames:
        fieldnames.append("적용구분")

    missing = []
    for r in kept:
        cls = APPLY_CLASS.get(r["품목유형"])
        if cls is None:
            missing.append(r["품목유형"])
            cls = "미분류"
        r["적용구분"] = cls

    if missing:
        print(f"[주의] 적용구분 미지정: {missing}\n")

    # 요약 출력
    print(f"{'적용구분':<14}{'식품군수':>6}  품목")
    print("-" * 78)
    for cls in ["대부분 의무", "일부 의무", "품목 의무 없음"]:
        items = [r["품목유형"] for r in kept if r["적용구분"] == cls]
        print(f"{cls:<14}{len(items):>6}  {', '.join(items)}")
    print()

    # 적용구분별 평균 인증률 (편향 진단)
    print("[진단] 적용구분별 HACCP 인증률")
    print("-" * 50)
    for cls in ["대부분 의무", "일부 의무", "품목 의무 없음"]:
        rates = []
        for r in kept:
            if r["적용구분"] != cls:
                continue
            v = r.get("HACCP_인증률", "")
            try:
                rates.append(float(v) * 100)
            except (ValueError, TypeError):
                pass
        if rates:
            print(f"  {cls:<14} 평균 {sum(rates)/len(rates):>5.1f}%  "
                  f"(범위 {min(rates):.1f}~{max(rates):.1f}%)")

    with open(OUT_PATH, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(kept)

    print(f"\n저장: {OUT_PATH}")
    print("\n[근거 메모]")
    for k, v in LEGAL_BASIS.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
