"""
시각화 공통 유틸 (모든 fig 스크립트가 import)
============================================
한글 폰트 설정 + 데이터 로드 + 공통 함수

각 figN 스크립트 실행 전 코랩에서 한 번:
    !apt-get install -y fonts-nanum -qq
"""
import csv
import glob
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

MERGED20 = "data/processed/merged20.csv"
SCORES20 = "data/processed/scores20.csv"


def setup_font():
    """나눔폰트 등록. 각 스크립트 시작 시 호출."""
    for fp in glob.glob('/usr/share/fonts/truetype/nanum/*.ttf'):
        fm.fontManager.addfont(fp)
    plt.rcParams['font.family'] = 'NanumGothic'
    plt.rcParams['axes.unicode_minus'] = False


def num(r, k):
    v = r.get(k, "")
    try:
        return float(v) if str(v).strip() not in ("", "-") else None
    except ValueError:
        return None


def load(path):
    with open(path, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def minmax(vals):
    valid = [v for v in vals if v is not None]
    if not valid:
        return vals
    lo, hi = min(valid), max(valid)
    if hi == lo:
        return [0.5 if v is not None else None for v in vals]
    return [(v - lo) / (hi - lo) if v is not None else None for v in vals]


def beta_shrink(rows):
    """부적합률 베타-이항 축소. (dict, 전체평균, α, β) 반환"""
    data = [(r["품목유형"], num(r, "검사건수"), num(r, "부적합건수"))
            for r in rows if num(r, "검사건수") and num(r, "부적합건수") is not None]
    tf = sum(f for _, _, f in data); ti = sum(i for _, i, _ in data)
    pm = tf / ti if ti else 0
    obs = [f / i for _, i, f in data]; nn = len(obs); mean = sum(obs) / nn
    var = sum((x - mean) ** 2 for x in obs) / nn if nn > 1 else 0
    conc = max((mean * (1 - mean) / var) - 1, 1.0) if var > 0 and 0 < mean < 1 else 100.0
    a, b = pm * conc, (1 - pm) * conc
    return {nm: (f + a) / (i + a + b) for nm, i, f in data}, pm, a, b


def short_name(c):
    """긴 품목유형명 축약"""
    return (c.replace(", 빵류 또는 떡류", "류")
             .replace(" 및 화분가공품류", "")
             .replace("류 또는 조림류", "·조림류"))
