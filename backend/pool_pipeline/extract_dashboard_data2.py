import sys
sys.stdout.reconfigure(encoding='utf-8')
import json
import re
import sqlite3
import sys
import os
import openpyxl

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "pipeline"))
from paths import RAW_DIR, DB_DIR, OUTPUT_DIR

PATH = RAW_DIR / "(260812)충남산업단지기업_Pool_v0.1_개발용.xlsx"
DB_PATH = DB_DIR / "saturn.db"
OUT_JSON = OUTPUT_DIR / "pool_data.json"

# ---- 1) backfill HQ address / CEO from saturn.db (already-fetched DART cache) ----
conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()
cur.execute("""
    SELECT dart_bizr_no, adres, ceo_nm FROM dart_crosscheck_full
    WHERE dart_bizr_no IS NOT NULL AND dart_bizr_no != '' AND error IS NULL
""")
hq_by_bizno = {}
for bizno, adres, ceo in cur.fetchall():
    if bizno not in hq_by_bizno or (adres and not hq_by_bizno[bizno][0]):
        hq_by_bizno[bizno] = (adres, ceo)
conn.close()
print("DART 캐시 기반 본사정보 보유 사업자번호:", len(hq_by_bizno))

# ---- 2) industry category classifier ----
IND_RULES = [
    ("반도체·디스플레이", ["반도체", "디스플레이", "전자부품", "전자소자", "집적회로", "다이오드", "센서"]),
    ("자동차·모빌리티", ["자동차", "자동차부품", "이륜자동차", "운송장비", "차체", "트레일러"]),
    ("철강·금속", ["철강", "금속", "주조", "단조", "제강", "합금", "비철금속", "선재", "압연"]),
    ("화학·소재", ["화학", "고무", "플라스틱", "석유", "합성수지", "도료", "잉크", "섬유", "화합물"]),
    ("기계·장비", ["기계", "장비", "금형", "공작기계", "발전기", "펌프", "밸브", "베어링", "엔진"]),
    ("식품·바이오", ["식품", "음료", "바이오", "제약", "의약품", "사료", "축산", "수산물가공"]),
    ("전기·에너지", ["전기", "배터리", "이차전지", "태양광", "발전", "에너지", "변압기", "축전지"]),
]


def classify_industry(industry_text, product_text):
    combined = f"{industry_text or ''} {product_text or ''}"
    for cat, keywords in IND_RULES:
        if any(k in combined for k in keywords):
            return cat
    return "기타 제조업"


# ---- 3) service-type inference from project names ----
SERVICE_RULES = [
    ("Audit", ["회계감사", "감사", "PA", "IFRS", "XBRL", "K-SOX", "KSOX", "KSoX", "내부회계", "Audit", "Reporting"]),
    ("Tax", ["세무", "Tax", "이전가격", "관세"]),
    ("Deals", ["M&A", "인수", "합병", "밸류에이션", "가치평가", "실사", "Due Diligence", "IPO", "평가"]),
    ("Consulting", ["자문", "컨설팅", "Consulting", "전략", "혁신", "정산", "구축"]),
]


def infer_services(proj_text):
    if not proj_text:
        return []
    found = set()
    for svc, keywords in SERVICE_RULES:
        if any(k.lower() in proj_text.lower() for k in keywords):
            found.add(svc)
    return sorted(found) if found else ["기타"]


def region_of_address(addr):
    if not addr:
        return None
    first = str(addr).split("\n")[0].strip()
    m = re.match(r"^(\S+?[시도])", first)
    return m.group(1) if m else first.split(" ")[0]


# 원본 엑셀 "소재 시군" 컬럼에 있는 확인된 오타 — 사용자가 직접 확인해준 것만 고침
# (임의로 다른 값을 추정해서 합치지 않음)
REGION_TYPO_FIXES = {"아신시": "아산시"}


def fix_region_typo(region):
    return REGION_TYPO_FIXES.get(region, region)


# ---- 4) load master pool file ----
wb = openpyxl.load_workbook(PATH, data_only=True, read_only=True)
ws = wb["통합 DB"]
rows = ws.iter_rows(values_only=True)
next(rows)
col_names = list(next(rows))
idx = {name: i for i, name in enumerate(col_names) if name}


def g(row, key):
    i = idx.get(key)
    if i is None:
        return None
    v = row[i]
    if v is None:
        return None
    if isinstance(v, str):
        v = v.strip()
        return v if v else None
    return v


def first_line(v):
    if v is None:
        return None
    return str(v).split("\n")[0].strip()


def num(v):
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


FIELDS = ["n", "ind_complex", "region", "addr", "site_count", "product", "industry", "ind_cat", "emp",
          "sf_client", "sf_proj_cnt", "sf_proj", "sf_staff", "sf_services",
          "fin_year", "revenue", "op_income", "assets", "liabilities", "equity",
          "audit_opinion", "auditor", "listed", "market", "phone", "homepage",
          "dart_corp", "dart_bizno", "hq_addr", "hq_region", "ceo"]

records = []
for row in rows:
    if g(row, "표준기업명") is None:
        continue
    industry = first_line(g(row, "업종"))
    product = first_line(g(row, "주요 생산품·서비스"))
    bizno = g(row, "DART 사업자등록번호")
    hq_addr, ceo = hq_by_bizno.get(str(bizno), (None, None)) if bizno else (None, None)
    sf_proj = g(row, "프로젝트명")

    rec = [
        g(row, "표준기업명"),
        first_line(g(row, "산업단지명")),
        fix_region_typo(g(row, "소재 시군")),
        (first_line(g(row, "공장주소")) or "").replace("아신시", "아산시") or None,
        g(row, "충남공장수"),
        product,
        industry,
        classify_industry(industry, product),
        num(g(row, "종업원수")),
        g(row, "salesforce_CLIENTNM"),
        g(row, "프로젝트수"),
        sf_proj,
        g(row, "담당자"),
        infer_services(sf_proj),
        g(row, "DART_보고서기준연도"),
        num(g(row, "DART_매출액")),
        num(g(row, "DART_영업이익")),
        num(g(row, "DART_자산총계")),
        num(g(row, "DART_부채총계")),
        num(g(row, "DART_자본총계")),
        g(row, "DART_감사의견"),
        g(row, "DART_감사인"),
        g(row, "상장여부"),
        g(row, "상장시장"),
        first_line(g(row, "대표전화")) or first_line(g(row, "전화번호")),
        g(row, "DART_홈페이지"),
        g(row, "DART 법인명"),
        bizno,
        hq_addr,
        region_of_address(hq_addr),
        ceo,
    ]
    records.append(rec)

print("총 레코드:", len(records))

payload = {"fields": FIELDS, "rows": records}
with open(OUT_JSON, "w", encoding="utf-8") as f:
    json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))

import os
size_mb = os.path.getsize(OUT_JSON) / 1024 / 1024
print(f"JSON 크기: {size_mb:.2f} MB")

fi = {name: i for i, name in enumerate(FIELDS)}
from collections import Counter
hq_known = sum(1 for r in records if r[fi["hq_addr"]])
print("본사주소 확보:", hq_known)
diff_hq = sum(1 for r in records if r[fi["hq_region"]] and r[fi["region"]] and r[fi["hq_region"]] not in r[fi["region"]])
print("본사지역 != 충남 추정(타지역본사+충남생산거점):", diff_hq)
cats = Counter(r[fi["ind_cat"]] for r in records)
print("산업대분류 분포:", cats.most_common())
multi_site = sum(1 for r in records if (r[fi["site_count"]] or 0) and r[fi["site_count"]] >= 2)
print("충남 복수공장 보유:", multi_site)
