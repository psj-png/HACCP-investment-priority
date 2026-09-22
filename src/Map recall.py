"""
회수 데이터(I0490) → 품목유형별 등급별 건수 행렬 → merged.csv 병합
==============================================================
입력: data/raw/I0490.csv, data/processed/merged.csv
출력: data/processed/merged.csv (Recall_1등급, Recall_2등급, Recall_3등급 컬럼 추가)

몬테카를로 민감도 분석용: 등급별 건수를 저장해두면
Impact = 건수행렬 × 가중치벡터로 무작위 시뮬레이션 가능 (montecarlo.py).

자율회수·등급공백은 심각도 판정 불가로 제외 (1/2/3등급만).
공백은 "경미"가 아니라 "판정 불가"이며(리스테리아 검출 등 심각 사례도 공백에 포함),
3등급 취급 시 왜곡되므로 제외.
"""

import csv
import re

RECALL_PATH = "data/raw/I0490.csv"
MERGED_PATH = "data/processed/merged.csv"

GRADES = ["1등급", "2등급", "3등급"]   # 이 3개만 사용, 자율회수·공백 제외

NAME_KEYWORD_MAP = [
    (["과자", "빵", "떡", "캔디", "추잉껌", "스낵", "비스킷", "한과"], "과자류, 빵류 또는 떡류"),
    (["빙과", "아이스크림", "빙수", "샤베트", "아이스밀크", "식용얼음"], "빙과류"),
    (["초콜릿", "코코아", "쵸콜릿"], "코코아가공품류 또는 초콜릿류"),
    (["설탕", "당류", "올리고당", "포도당", "물엿", "당시럽", "덱스트린", "과당"], "당류"),
    (["잼", "마멀레이드"], "잼류"),
    (["두부", "묵", "유바"], "두부류 또는 묵류"),
    (["식용유", "참기름", "들기름", "콩기름", "옥수수기름", "올리브유", "유지", "쇼트닝", "마가린", "채종유", "미강유", "해바라기", "팜유", "혼합유"], "식용유지류"),
    (["면류", "국수", "냉면", "당면", "라면", "유탕면", "파스타", "생면", "숙면", "건면", "만두피"], "면류"),
    (["음료", "주스", "커피", "탄산", "두유", "액상차", "침출차", "고형차", "과채주스", "과채음료", "음료베이스"], "음료류"),
    (["영아", "성장기", "이유식", "특수영양", "임산", "수유부", "영유아", "고령자용", "체중조절"], "특수영양식품"),
    (["환자용", "특수의료", "영양조제", "식단형"], "특수의료용도식품"),
    (["간장", "된장", "고추장", "청국장", "메주", "춘장", "장류", "혼합장"], "장류"),
    (["소스", "마요네즈", "케첩", "드레싱", "고춧가루", "카레", "향신료", "복합조미", "조미", "식초", "소금", "실고추"], "조미식품"),
    (["김치", "김칫속", "절임", "당절임", "조림", "젓갈"], "절임류 또는 조림류"),
    (["전분", "밀가루", "시리얼", "곡류가공", "두류가공", "서류가공", "과채가공", "농산가공", "찐쌀", "견과류가공", "땅콩버터", "땅콩 또는 견과", "효소식품", "전분가공"], "농산가공식품류"),
    (["식육", "햄", "소시지", "베이컨", "양념육", "포장육", "갈비", "육포"], "식육가공품"),
    (["알가공", "전란", "난황", "난백", "피단", "알함유"], "알가공품류"),
    (["수산", "어묵", "어육", "연육", "젓갈", "건어포", "조미김", "한천"], "수산가공식품류"),
    (["동물성", "곤충", "자라", "추출가공식품"], "동물성가공식품류"),
    (["벌꿀", "벌집꿀", "로열젤리", "로얄젤리", "화분", "프로폴리스"], "벌꿀 및 화분가공품류"),
    (["즉석", "신선편의", "만두", "도시락", "순대", "생식"], "즉석식품류"),
    (["효모", "기타가공품", "기타 가공품"], "기타식품류"),
]

EXCLUDE_KEYWORDS = [
    "건강기능", "프로바이오틱스", "추출물", "녹차추출",
    "기구", "용기", "포장", "수지", "고무", "종이", "금속제", "목재", "유리", "도자기", "법랑", "폴리",
    "주류", "탁주", "약주", "청주", "맥주", "소주", "위스키", "브랜디", "리큐르", "과실주", "증류주",
]


def normalize(name):
    n = name.strip().replace(".", "").replace("·", "").replace("∙", "")
    return re.sub(r"\s+", "", n)


def map_to_category(name):
    n = normalize(name)
    for kw in EXCLUDE_KEYWORDS:
        if normalize(kw) in n:
            return None
    for keywords, category in NAME_KEYWORD_MAP:
        for kw in keywords:
            if normalize(kw) in n:
                return category
    return None


def main():
    with open(RECALL_PATH, encoding="utf-8-sig") as f:
        recalls = list(csv.DictReader(f))

    # 품목유형별 등급별 건수 [1등급, 2등급, 3등급]
    grade_counts = {}
    unmapped, excluded_grade = 0, 0

    for r in recalls:
        name = r.get("PRDLST_CD_NM", "").strip()
        grade = r.get("RTRVL_GRDCD_NM", "").strip()

        # 등급 명확한 것만 (자율회수·공백 제외)
        if grade not in GRADES:
            excluded_grade += 1
            continue

        cat = map_to_category(name)
        if cat is None:
            unmapped += 1
            continue

        gi = GRADES.index(grade)
        grade_counts.setdefault(cat, [0, 0, 0])[gi] += 1

    total_mapped = sum(sum(v) for v in grade_counts.values())
    print(f"회수 {len(recalls)}건")
    print(f"  등급 제외(자율회수·공백): {excluded_grade}건")
    print(f"  품목유형 매핑 실패: {unmapped}건")
    print(f"  최종 반영: {total_mapped}건\n")

    print(f"{'품목유형':<22}{'1등급':>6}{'2등급':>6}{'3등급':>6}{'계':>5}")
    print("-" * 47)
    for cat in sorted(grade_counts, key=lambda c: -sum(grade_counts[c])):
        c1, c2, c3 = grade_counts[cat]
        print(f"{cat:<22}{c1:>6}{c2:>6}{c3:>6}{c1+c2+c3:>5}")

    # merged.csv에 3개 컬럼 추가
    with open(MERGED_PATH, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
        fieldnames = list(rows[0].keys())

    # 기존 Impact 버전 컬럼 제거 (있으면) + 등급별 컬럼 추가
    old_cols = ["Impact_321", "Impact_2_15_1", "Impact_531", "Impact_111", "Impact_등급가중회수"]
    fieldnames = [f for f in fieldnames if f not in old_cols]
    for col in ["Recall_1등급", "Recall_2등급", "Recall_3등급"]:
        if col not in fieldnames:
            fieldnames.append(col)

    for r in rows:
        cat = r["품목유형"]
        counts = grade_counts.get(cat, [0, 0, 0])
        r["Recall_1등급"] = counts[0]
        r["Recall_2등급"] = counts[1]
        r["Recall_3등급"] = counts[2]
        for c in old_cols:
            r.pop(c, None)

    with open(MERGED_PATH, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)

    print(f"\n→ merged.csv에 등급별 건수 컬럼 추가 (자율회수·공백 제외)")


if __name__ == "__main__":
    main()
