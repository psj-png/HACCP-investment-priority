# 식품안전 리스크 및 경제적 영향을 고려한 HACCP 투자 우선순위 평가

> 2026 한국식품안전관리인증원 공공데이터 분석·활용 경진대회 출품작

## 문제 정의

HACCP 인증 확대를 위한 정부 예산은 한정되어 있다. 현행 방식은 업종·지역 단위로 균등 배분하지만, 식품군마다 안전 위험도와 경제적 영향이 다르기 때문에 동일한 투자가 동일한 효과를 보장하지 않는다.

본 프로젝트는 금융의 자본배분(Capital Allocation) 개념을 적용하여, **"한정된 HACCP 투자 자원을 어떤 식품군에 먼저 배분해야 하는가"**를 데이터 기반으로 제안한다.

## 분석 프레임워크

식품군별 투자 우선순위 스코어를 4개 변수의 가중합으로 산출한다.

```
Priority Score(i) = w1·Risk(i) + w2·Scale(i) + w3·Vulnerability(i) + w4·Impact(i)
```

| 변수 | 정의 | 조작적 정의 |
|---|---|---|
| **Risk** | 해당 식품군의 안전 위험도 | 부적합률, 위반율 |
| **Scale** | 해당 식품군의 경제적 규모 | 생산액, 생산량 |
| **Vulnerability** | HACCP 인증 취약도 | 1 − (HACCP 인증 업체 수 / 전체 업체 수) |
| **Impact** | 사고 발생 시 피해 규모 | 회수·판매중지 건수 (3단계 예정) |

가중치는 동일 가중 후 민감도 분석(가중치 변화에 따른 순위 변동 확인)으로 검증한다.

## 분석 대상

식품제조·가공업 기준 **23개 품목유형**. 축산물(별도 부처 소관), 주류(국세청 소관), 식품첨가물(별도 업종)은 데이터 정합성을 위해 제외. 자세한 근거는 [`docs/data-mapping.md`](docs/data-mapping.md) 참조.

## 데이터 출처

### 식품의약품안전처 통계 (CSV)

| 파일 | 내용 | 분석 변수 |
|---|---|---|
| `1-1-1-2.csv` | 식품제조·가공업체 현황 (품목유형별) | Vulnerability (분모) |
| `1-2-1-2.csv` | 생산량·생산액 (품목유형별) | Scale |
| `1-3-1-1.csv` | 감시 및 위반 현황 (품목유형별) | Risk |
| `1-4-3.csv` | 수거·검사건수 (품목유형별) | Risk (부적합률) |
| `1-1-1-1.csv`, `1-2-1-1.csv`, `1-2-1-8.csv` | 업종별 업체·생산·규모 (보조) | 보조 분석 |

### 한국식품안전관리인증원 Open API (data.go.kr)

| API | 용도 |
|---|---|
| HACCP 인증업체정보 (`CertCompanyListService2`) | 업체별 품목코드 → 식품군별 인증 업체 수 |
| 품목코드정보 (`PrdLstListService`) | `businessitem` → `pcd` 상위 카테고리 매핑 |

### 3단계 예정

식품안전나라 회수·판매중지 정보 (Impact 변수용).

## 파이프라인

```
[1단계] 데이터 수집 ✅
    ├── 식약처 CSV 다운로드
    ├── HACCP 인증업체 API 수집 (41,091건)
    │     └── XML/JSON 자동분기, numOfRows=100 페이징, 재시도 로직
    └── 품목코드 API → pcd 매핑 → 식품군별 집계
          └── 식품제조가공업 + 업체 중복제거 → 23개 품목유형

[2단계] 조인 및 정합성 확보 ✅
    ├── 품목유형명 정규화 (영문/주석 제거, 동의어 통일)
    ├── 세부행 합산 (분할된 품목유형 재집계)
    ├── 분자·분모 범위 통일 (식품·제조가공업·업체단위)
    └── data/processed/merged.csv (23개 품목유형 × 12개 지표)

[3단계] 스코어링 ⏳
    ├── Risk / Scale / Vulnerability / Impact 정규화
    ├── Priority Score 산출 + 민감도 분석
    └── 정책 제언: 우선 투자 대상 식품군 도출

[4단계] 시각화 및 보고서 ⏳
```

## 프로젝트 구조

```
haccp-investment-priority/
├── README.md
├── docs/
│   └── data-mapping.md          # 데이터 매핑 설계 + 문제해결 기록
├── src/
│   ├── collect_haccp_api.py     # 1단계: API 수집 + 품목유형 집계
│   └── merge_csv.py             # 2단계: CSV 조인
└── data/
    ├── raw/                     # 원본 CSV + API 수집 데이터
    │   ├── 1-1-1-2.csv 등 식약처 통계
    │   ├── haccp_companies_raw.csv   # 인증업체 원본 (41,091건)
    │   ├── haccp_by_category.csv     # 품목유형별 집계 (23개)
    │   └── product_codes.csv         # 품목코드 매핑 테이블
    └── processed/
        └── merged.csv           # 최종 통합 테이블 (3단계 입력)
```

## 실행 방법

```bash
pip install requests

# 1단계: API 수집 + 집계 (data/raw/ 생성)
python src/collect_haccp_api.py

# 2단계: CSV 조인 (data/processed/merged.csv 생성)
python src/merge_csv.py
```

식약처 CSV 7개는 `data/raw/`에 미리 위치시켜야 한다.
