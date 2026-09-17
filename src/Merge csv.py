"""
2단계: CSV 8개 조인 → 식품군별 통합 테이블
============================================
코랩에서 실행. data/raw/의 파일들을 읽어 하나로 병합.
결과: data/processed/merged.csv
"""

import csv
import os
import re

RAW_DIR = "data/raw"
OUT_DIR = "data/processed"
os.makedirs(OUT_DIR, exist_ok=True)


def read_csv_flexible(path):
    for enc in ["utf-8-sig", "euc-kr", "cp949"]:
        try:
            with open(path, encoding=enc) as f:
                return list(csv.reader(f))
        except (UnicodeDecodeError, UnicodeError):
            continue
    raise RuntimeError(f"인코딩 감지 실패: {path}")


def clean_name(raw):
    if not raw:
        return ""
    name = raw.split("\n")[0].strip()
    name = re.sub(r"[A-Za-z].*$", "", name).strip()   # 영문 병기 제거
    name = re.sub(r"\s*\d+\)\s*$", "", name).strip()  # 주석 "1)" 제거
    name = re.sub(r"[*※].*$", "", name).strip()        # * ※ 이후 제거
    name = re.sub(r"\s+", " ", name)
    SYNONYM = {
        "과자류, 빵 또는 떡류": "과자류, 빵류 또는 떡류",
        "과자류,빵류 또는 떡류": "과자류, 빵류 또는 떡류",
        "식육가공품 및 포장육": "식육가공품",
        "식육함류가공품": "식육가공품",
        "식육함유가공품": "식육가공품",
        "유함유가공품": "유가공품류",
        "유가공품": "유가공품류",
        "알가공품": "알가공품류",
    }
    return SYNONYM.get(name, name)


def to_num(s):
    if not s or s.strip() in ("-", ""):
        return None
    try:
        return float(s.replace(",", ""))
    except ValueError:
        return None


def is_meta_row(col0):
    """헤더/합계/메타 행인지 판정"""
    if col0.startswith("표") or col0.startswith("Table") or col0.startswith("Classification") \
       or col0.startswith("단위") or col0.startswith("자료") or col0.startswith("주 "):
        return True
    if ("총" in col0 and "계" in col0):
        return True
    return False


def parse_haccp():
    rows = read_csv_flexible(os.path.join(RAW_DIR, "haccp_by_category.csv"))
    result = {}
    for r in rows[1:]:
        if len(r) >= 2 and r[0].strip():
            name = clean_name(r[0])
            val = to_num(r[1])
            if name and val is not None:
                result[name] = {"HACCP_인증업체수": val}
    return result


def parse_1112():
    """전체 업체 수. 단일 컬럼 구조 (col0=품목, col1=총계)."""
    rows = read_csv_flexible(os.path.join(RAW_DIR, "1-1-1-2.csv"))
    result = {}
    for r in rows:
        if not r or not r[0].strip():
            continue
        name = clean_name(r[0])
        if is_meta_row(name) or name in ("구 분", "구분", ""):
            continue
        val = to_num(r[1]) if len(r) > 1 else None
        if name and val is not None:
            result[name] = {"전체업체수": val}
    return result


def parse_with_subrows(filename, col_map):
    """
    세부행 합산 공통 파서.
    상위 품목유형(col0에 이름) 아래 세부행(col0 비고 col1에 세부명)을
    상위로 합산한다. 값 컬럼은 항상 고정 위치(col_map).

    col_map: {출력키: 컬럼인덱스}
    """
    rows = read_csv_flexible(os.path.join(RAW_DIR, filename))
    result = {}
    current_top = None
    max_col = max(col_map.values())

    for r in rows:
        if not r or len(r) <= max_col:
            continue
        col0 = clean_name(r[0])

        # 메타행 스킵 (단, current_top은 유지)
        if is_meta_row(col0):
            current_top = None
            continue
        if col0 in ("구 분", "구분"):
            continue

        # 상위 품목유형 갱신
        if col0:
            current_top = col0

        target = current_top
        if not target:
            continue

        if target not in result:
            result[target] = {k: 0.0 for k in col_map}

        for key, idx in col_map.items():
            v = to_num(r[idx]) if len(r) > idx else None
            if v is not None:
                result[target][key] += v
    return result


def parse_1212():
    """생산량(col3), 생산액(col4). 세부행 합산."""
    return parse_with_subrows("1-2-1-2.csv", {"생산량_톤": 3, "생산액_천원": 4})


def parse_143():
    """검사(col2), 부적합(col4). 세부행 합산."""
    return parse_with_subrows("1-4-3.csv", {"검사건수": 2, "부적합건수": 4})


def parse_1311():
    """감시(col1), 위반소계(col2). 품목유형 블록(단일 행 구조)."""
    rows = read_csv_flexible(os.path.join(RAW_DIR, "1-3-1-1.csv"))
    result = {}
    for r in rows:
        if not r or not r[0].strip():
            continue
        name = clean_name(r[0])
        if re.match(r"^\d{4}$", r[0].strip()):  # 연도행 스킵
            continue
        if is_meta_row(name) or name in ("구 분", "구분", ""):
            continue
        surveillance = to_num(r[1]) if len(r) > 1 else None
        violation = to_num(r[2]) if len(r) > 2 else None
        if name and (surveillance is not None or violation is not None):
            result[name] = {"감시건수": surveillance or 0.0, "위반건수": violation or 0.0}
    return result


def main():
    print("=" * 50)
    print("CSV 조인 시작")
    print("=" * 50)

    haccp = parse_haccp()
    t1112 = parse_1112()
    t1212 = parse_1212()
    t1311 = parse_1311()
    t143  = parse_143()

    print(f"HACCP 품목유형: {len(haccp)}개")
    print(f"1-1-1-2 (전체업체): {len(t1112)}개")
    print(f"1-2-1-2 (생산): {len(t1212)}개")
    print(f"1-3-1-1 (위반): {len(t1311)}개")
    print(f"1-4-3 (수거검사): {len(t143)}개")

    merged = {}
    capped = []
    for cat in haccp:
        row = {"품목유형": cat}
        row.update(haccp[cat])
        row.update(t1112.get(cat, {"전체업체수": None}))
        row.update(t1212.get(cat, {"생산량_톤": None, "생산액_천원": None}))
        row.update(t1311.get(cat, {"감시건수": None, "위반건수": None}))
        row.update(t143.get(cat, {"검사건수": None, "부적합건수": None}))

        if row.get("검사건수") and row.get("부적합건수") is not None and row["검사건수"] > 0:
            row["부적합률"] = row["부적합건수"] / row["검사건수"]
        else:
            row["부적합률"] = None
        if row.get("감시건수") and row.get("위반건수") is not None and row["감시건수"] > 0:
            row["위반율"] = row["위반건수"] / row["감시건수"]
        else:
            row["위반율"] = None
        if row.get("전체업체수") and row.get("HACCP_인증업체수") is not None and row["전체업체수"] > 0:
            raw_rate = row["HACCP_인증업체수"] / row["전체업체수"]
            row["HACCP_인증률_원본"] = raw_rate
            row["HACCP_인증률"] = min(raw_rate, 1.0)
            if raw_rate > 1.0:
                capped.append((cat, raw_rate))
        else:
            row["HACCP_인증률_원본"] = None
            row["HACCP_인증률"] = None

        merged[cat] = row

    cols = ["품목유형", "전체업체수", "HACCP_인증업체수", "HACCP_인증률", "HACCP_인증률_원본",
            "생산량_톤", "생산액_천원", "감시건수", "위반건수", "위반율",
            "검사건수", "부적합건수", "부적합률"]

    out_path = os.path.join(OUT_DIR, "merged.csv")
    with open(out_path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for cat in merged:
            w.writerow({c: merged[cat].get(c, "") for c in cols})

    print("\n" + "=" * 50)
    print(f"병합 완료: {out_path} ({len(merged)}개 품목유형)")
    print("=" * 50)

    if capped:
        print("\n[100% 초과 → 캡 처리된 품목]")
        for cat, rate in capped:
            print(f"  {cat}: 원본 {rate:.1%} → 100%")

    print("\n[결측 현황]")
    for c in cols[1:]:
        missing = [cat for cat in merged if merged[cat].get(c) is None]
        if missing:
            print(f"  {c}: {len(missing)}개 → {', '.join(missing[:5])}{'...' if len(missing) > 5 else ''}")

    print("\n[전체 검증표]")
    print(f"{'품목유형':<22}{'전체':>7}{'HACCP':>7}{'인증률':>8}{'검사':>8}{'부적합':>7}{'부적합률':>9}")
    for cat in merged:
        m = merged[cat]
        def fmt(v, pct=False, dec=0):
            if v is None: return "-"
            if pct: return f"{v:.1%}"
            return f"{v:.{dec}f}"
        print(f"{cat:<22}{fmt(m.get('전체업체수')):>7}{fmt(m.get('HACCP_인증업체수')):>7}"
              f"{fmt(m.get('HACCP_인증률'),pct=True):>8}{fmt(m.get('검사건수')):>8}"
              f"{fmt(m.get('부적합건수')):>7}{fmt(m.get('부적합률'),pct=True):>9}")


if __name__ == "__main__":
    main()
