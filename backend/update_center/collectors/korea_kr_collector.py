"""대한민국 정책브리핑(korea.kr) 보도자료 수집기 — 과기정통부/산업부/중기부 등
중앙부처 보도자료를 한 곳에서 커버한다. 서버사이드 렌더링 + 키워드 검색을
지원해서(&srchWord=), 사이트별 개별 크롤러(ChungnamCollector류)보다 훨씬 안정적이다.
지자체(충남도청 등) 보도자료는 이 사이트에 실리지 않으므로 별도 소스가 필요하다 — 다음 단계.
"""
import sys
import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from urllib.parse import quote

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from raw_document import RawDocument

LIST_URL = "https://www.korea.kr/briefing/pressReleaseList.do"
VIEW_URL_BASE = "https://www.korea.kr/briefing/pressReleaseView.do?newsId="

AX_KEYWORDS = ["인공지능", "AI", "AX", "디지털전환", "지능정보"]


def _date_range(days_back):
    end = datetime.now()
    begin = end - timedelta(days=days_back)
    return begin.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")


def collect(days_back=14, max_per_keyword=30):
    begin, end = _date_range(days_back)
    docs = {}  # newsId -> RawDocument, dedup across keyword searches
    for kw in AX_KEYWORDS:
        resp = requests.get(LIST_URL, params={
            "srchWord": kw, "startDate": begin, "endDate": end, "pageIndex": 1,
        }, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        for a in soup.select('a[href*="pressReleaseView.do?newsId="]'):
            href = a.get("href", "")
            news_id = None
            for part in href.split("?", 1)[-1].split("&"):
                if part.startswith("newsId="):
                    news_id = part.split("=", 1)[1]
                    break
            if not news_id or news_id in docs:
                continue
            title_tag = a.select_one("strong")
            lead_tag = a.select_one(".lead")
            source_spans = a.select(".source span")
            title = title_tag.get_text(strip=True) if title_tag else ""
            lead = lead_tag.get_text(strip=True) if lead_tag else ""
            published = source_spans[0].get_text(strip=True) if len(source_spans) > 0 else None
            agency = source_spans[1].get_text(strip=True) if len(source_spans) > 1 else "정책브리핑"
            if not title:
                continue
            docs[news_id] = RawDocument(
                source=f"정책브리핑-{agency}",
                title=title,
                body=lead,
                published_at=published,
                url=f"{VIEW_URL_BASE}{news_id}",
            )
        if len(docs) >= max_per_keyword * len(AX_KEYWORDS):
            break
    return list(docs.values())


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    results = collect()
    print(f"정책브리핑 AX 관련: {len(results)}건")
    for d in results[:10]:
        print(f" - [{d.source}] {d.title} ({d.published_at})")
