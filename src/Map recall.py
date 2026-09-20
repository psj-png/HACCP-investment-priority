"""
회수 데이터(I0490) → 품목유형별 Impact (4가지 등급가중 버전) → merged.csv 병합
==============================================================
입력: data/raw/I0490.csv, data/processed/merged.csv
출력: data/processed/merged.csv (Impact 4버전 컬럼 추가)

등급 가중치 민감도 검증용으로 여러 버전 생성:
  Impact_321   : 1등급3, 2등급2, 3등급1 (기본)
  Impact_2_15_1: 1등급2, 2등급1.5, 3등급1 (완만)
  Impact_531   : 1등급5, 2등급3, 3등급1 (급격)
  Impact_111   : 1등급1, 2등급1, 3등급1 (단순 건수)

매핑: 회수 데이터의 품목명(PRDLST_CD_NM)을 23개 품목유형에 키워드 매핑.
      회수 코드(PRDLST_CD)는 14자리로 우리 매핑 테이블과 체계가 달라 품목명 사용.
"""

import csv
import os
import re
from collections import Counter

RECALL_PATH = "data/raw/I0490.csv"
MERGED_PATH = "data/processed/merged.csv"

GRADE_WEIGHT_VERSIONS = {
    "Impact_321":    {"1등급": 3.0, "2등급": 2.0, "3등급": 1.0, "자율회수": 1.0, "": 1.0},
    "Impact_2_15_1": {"1등급": 2.0, "2등급": 1.5, "3등급": 1.0, "자율회수": 1.0, "": 1.0},
    "Impact_531":    {"1등급": 5.0, "2등급": 3.0, "3등급": 1.0, "자율회수": 1.0, "": 1.0},
    "Impact_111":    {"1등급": 1.0, "2등급": 1.0, "3등급": 1.0, "자율회수": 1.0, "": 1.0},
}

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

    impacts = {ver: {} for ver in GRADE_WEIGHT_VERSIONS}
    raw_count = {}
    unmapped = 0

    for r in recalls:
        name = r.get("PRDLST_CD_NM", "").strip()
        grade = r.get("RTRVL_GRDCD_NM", "").strip()
        cat = map_to_category(name)
        if cat is None:
            unmapped += 1
            continue
        raw_count[cat] = raw_count.get(cat, 0) + 1
        for ver, weights in GRADE_WEIGHT_VERSIONS.items():
            w = weights.get(grade, 1.0)
            impacts[ver][cat] = impacts[ver].get(cat, 0.0) + w

    print(f"회수 {len(recalls)}건 / 매핑 {len(recalls)-unmapped}건 / 제외 {unmapped}건\n")

    print(f"{'품목유형':<22}{'건수':>5}{'3:2:1':>8}{'2:1.5:1':>9}{'5:3:1':>8}{'1:1:1':>8}")
    print("-" * 62)
    all_cats = sorted(raw_count, key=lambda c: -impacts["Impact_321"].get(c, 0))
    for cat in all_cats:
        row = f"{cat:<22}{raw_count[cat]:>5}"
        for ver in ["Impact_321", "Impact_2_15_1", "Impact_531", "Impact_111"]:
            v = impacts[ver].get(cat, 0)
            row += f"{v:>9.1f}" if ver == "Impact_2_15_1" else f"{v:>8.1f}"
        print(row)

    # merged.csv에 4개 컬럼 추가
    with open(MERGED_PATH, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
        fieldnames = list(rows[0].keys())

    for ver in GRADE_WEIGHT_VERSIONS:
        if ver not in fieldnames:
            fieldnames.append(ver)

    for r in rows:
        cat = r["품목유형"]
        for ver in GRADE_WEIGHT_VERSIONS:
            r[ver] = impacts[ver].get(cat, 0.0)

    with open(MERGED_PATH, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)

    print(f"\n→ merged.csv에 4개 Impact 버전 컬럼 추가 완료")


if __name__ == "__main__":
    main()
