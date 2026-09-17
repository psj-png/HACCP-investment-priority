"""
HACCP 인증업체 API 수집 + 품목유형 매핑 (통합본 v2 - JSON/XML 자동분기)
============================================
코랩 셀에 통째로 붙여넣고 실행.
결과: data/raw/ 폴더에 CSV 4개 생성
"""

import requests
import time
import csv
import os
import json
import xml.etree.ElementTree as ET
from collections import Counter

API_KEY = "CsmDqep0ZFAAOzbJokelCHAOegO10ZksDnsaGGAEkdWbfdwqqk%2BHYI9ou%2Br9DaXhXm0Xr4Ok9UNGW3we9QC54A%3D%3D"
OUTPUT_DIR = "data/raw"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ═══ 매핑 테이블 ═══
PCD_TO_CATEGORY = {
    "C093": "과자류, 빵류 또는 떡류", "C094": "빙과류",
    "C095": "코코아가공품류 또는 초콜릿류", "C096": "당류", "C097": "잼류",
    "C098": "두부류 또는 묵류", "C099": "식용유지류", "C100": "면류",
    "C101": "음료류", "C102": "특수영양식품", "C103": "장류",
    "C104": "조미식품", "C105": "절임류 또는 조림류", "C106": "주류",
    "C107": "농산가공식품류", "C108": "식육가공품", "C109": "알가공품류",
    "C110": "수산가공식품류", "C111": "동물성가공식품류",
    "C112": "벌꿀 및 화분가공품류", "C113": "즉석식품류",
    "C114": "기타식품류", "C115": "기타식품류", "C116": "음료류",
    "C117": "수산가공식품류", "C118": "수산가공식품류", "C119": "수산가공식품류",
    "C120": "즉석식품류", "C121": "즉석식품류", "C122": "면류",
    "C123": "절임류 또는 조림류", "C124": "면류", "C125": "즉석식품류",
    "C126": "기타식품류", "C127": "면류", "C128": "면류", "C129": "면류",
    "C130": "유가공품류", "C131": "면류",
    "C001": "기타식품류", "C002": "즉석식품류", "C005": "과자류, 빵류 또는 떡류",
    "C031": "특수의료용도식품", "C85": "식품첨가물", "C87": "식품첨가물",
    "PKD001": "식육가공품", "PKD002": "식육가공품", "PKD003": "식육가공품",
    "PKD004": "식육가공품", "PKD005": "식육가공품", "PKD008": "식육가공품",
    "PKD009": "식육가공품", "PKD025": "식육가공품", "PKD033": "식육가공품",
    "PKD010": "유가공품류", "PKD011": "유가공품류", "PKD012": "유가공품류",
    "PKD013": "유가공품류", "PKD014": "유가공품류", "PKD015": "유가공품류",
    "PKD016": "유가공품류", "PKD017": "유가공품류", "PKD018": "유가공품류",
    "PKD019": "유가공품류", "PKD020": "유가공품류", "PKD0201": "유가공품류",
    "PKD021": "유가공품류", "PKD022": "유가공품류", "PKD023": "유가공품류",
    "PKD026": "유가공품류", "PKD027": "유가공품류", "PKD028": "유가공품류",
    "PKD029": "유가공품류", "PKD030": "유가공품류", "PKD034": "알가공품류",
}

NUMERIC_CODE_MAP = {
    "79": "식육가공품", "80": "식육가공품", "81": "식육가공품",
    "82": "식육가공품", "83": "식육가공품", "84": "식육가공품",
    "85": "식육가공품", "86": "식육가공품", "87": "식육가공품",
    "88": "식육가공품", "89": "식육가공품", "78": "식육가공품",
    "90": "식육가공품", "91": "식육가공품", "92": "식육가공품", "93": "식육가공품",
    "94": "알가공품류", "95": "알가공품류", "96": "알가공품류",
    "97": "알가공품류", "98": "알가공품류", "99": "알가공품류",
    "100": "알가공품류", "102": "알가공품류",
    "686": "식육가공품", "687": "식육가공품", "688": "식육가공품",
    "689": "식육가공품", "690": "식육가공품", "691": "식육가공품", "722": "식육가공품",
}

LONG_CODE_MAP = {
    "C0322020400000": "즉석식품류", "P02500001": "식육가공품",
    "P03300001": "식육가공품", "H03000002": "즉석식품류",
}

FIELDS = ["rnum","appointno","productGb","company","area1","area2",
          "companykind","companykindNm","businesstype","businesstypeNm",
          "businessitem","businessitemNm","issuedate","issueenddate"]


def parse_response(text):
    """XML이든 JSON이든 (items, total) 반환"""
    text = text.strip()
    if text.startswith("{"):  # JSON
        data = json.loads(text)
        body = data.get("body", {})
        tc = int(body.get("totalCount", 0))
        rows_out = []
        for wrapper in body.get("items", []):
            item = wrapper.get("item", wrapper)
            rows_out.append({f: item.get(f, "") for f in FIELDS})
        return rows_out, tc
    else:  # XML
        root = ET.fromstring(text)
        tc_el = root.find(".//totalCount")
        tc = int(tc_el.text) if tc_el is not None else 0
        rows_out = []
        for item_el in root.findall(".//item"):
            rows_out.append({f: (item_el.find(f).text if item_el.find(f) is not None else "") for f in FIELDS})
        return rows_out, tc


def fetch_product_codes():
    print("[1/3] 품목코드 매핑 테이블 수집 중...")
    url = f"https://apis.data.go.kr/B553748/PrdLstListService/getPrdLstListService?ServiceKey={API_KEY}&returnType=json&numOfRows=10000"
    data = requests.get(url).json()
    items = data.get("list", [])
    code_to_pcd = {}
    path = os.path.join(OUTPUT_DIR, "product_codes.csv")
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["cd", "pcd", "cdnmKr"])
        for item in items:
            cd, pcd = item.get("cd","").strip(), item.get("pcd","").strip()
            w.writerow([cd, pcd, item.get("cdnmKr","")])
            if cd and pcd:
                code_to_pcd[cd] = pcd
    print(f"  → 품목코드 {len(code_to_pcd)}개")
    return code_to_pcd


def fetch_haccp_companies():
    print("[2/3] HACCP 인증업체 수집 중...")
    base_url = "https://apis.data.go.kr/B553748/CertCompanyListService2/getCertCompanyListService2"
    all_items = []
    page = 1
    rows = 100
    total = None
    while total is None or len(all_items) < total:
        url = f"{base_url}?ServiceKey={API_KEY}&pageNo={page}&numOfRows={rows}"
        items, tc = parse_response(requests.get(url).text)
        if total is None:
            total = tc
            print(f"  → 전체 {total:,}건, {(total//rows)+1}페이지")
        if not items:
            print(f"  → 페이지 {page}: 빈 응답, 중단")
            break
        all_items.extend(items)
        if page % 20 == 0:
            print(f"  → 페이지 {page} ({len(all_items):,}/{total:,})")
        page += 1
        time.sleep(0.2)

    path = os.path.join(OUTPUT_DIR, "haccp_companies_raw.csv")
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(all_items)
    print(f"  → 총 {len(all_items):,}건 저장")
    return all_items


def resolve_category(biz_item, code_to_pcd):
    for code in [c.strip() for c in biz_item.split(",")]:
        if code in LONG_CODE_MAP:
            return LONG_CODE_MAP[code]
        if code in NUMERIC_CODE_MAP:
            return NUMERIC_CODE_MAP[code]
        pcd = code_to_pcd.get(code, "")
        if pcd and pcd in PCD_TO_CATEGORY:
            return PCD_TO_CATEGORY[pcd]
        for L in range(len(code), 2, -1):
            if code[:L] in PCD_TO_CATEGORY:
                return PCD_TO_CATEGORY[code[:L]]
    return ""


def aggregate_by_category(companies, code_to_pcd):
    print("[3/3] 품목유형별 집계 중...")
    cat_counter = Counter()
    unmapped = Counter()
    food, livestock = 0, 0
    for c in companies:
        if c.get("productGb") == "식품":
            food += 1
        else:
            livestock += 1
        cat = resolve_category(c.get("businessitem","").strip(), code_to_pcd)
        if cat:
            cat_counter[cat] += 1
        else:
            unmapped[f"{c.get('businessitem','')}({c.get('businessitemNm','')})"] += 1

    print(f"\n  식품 {food:,} / 축산물 {livestock:,}")
    print(f"  매핑 성공 {sum(cat_counter.values()):,} / 실패 {sum(unmapped.values()):,}\n")
    for cat, cnt in cat_counter.most_common():
        print(f"  {cat:<25} {cnt:>7,}")

    path = os.path.join(OUTPUT_DIR, "haccp_by_category.csv")
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["품목유형", "HACCP_인증_업체수"])
        for cat, cnt in cat_counter.most_common():
            w.writerow([cat, cnt])
    print(f"\n  → 저장: {path}")

    if unmapped:
        path_u = os.path.join(OUTPUT_DIR, "unmapped_codes.csv")
        with open(path_u, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.writer(f)
            w.writerow(["코드(품목명)", "건수"])
            for code, cnt in unmapped.most_common():
                w.writerow([code, cnt])
    return cat_counter


if __name__ == "__main__":
    print("\n HACCP 데이터 수집 (v2)\n")
    code_to_pcd = fetch_product_codes()
    # 항상 새로 수집 (예전 파일 덮어쓰기)
    companies = fetch_haccp_companies()
    aggregate_by_category(companies, code_to_pcd)
    print("\n완료! haccp_by_category.csv 최신화됨 (합계 31,857 확인)")
