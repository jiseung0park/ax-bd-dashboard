"""나라장터(조달청) Open API 수집기 — 사전규격 + 입찰공고.

크롤링이 아니라 정식 API라서(HTML 구조 개편에 안 깨짐), 파일럿의 핵심 소스로 삼는다.
API 자체는 전체 업종을 다 반환하므로(수십만 건), 여기서 AI/AX 키워드로 클라이언트 사이드
필터링한다 — 나라장터 API가 자유 키워드 검색을 지원하지 않기 때문.
"""
import sys
import os
import requests
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "pipeline"))
from paths import INPUT_DIR

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from raw_document import RawDocument

AX_KEYWORDS = ["AI", "인공지능", "AX", "디지털전환", "지능형", "빅데이터", "데이터플랫폼"]

PRESPEC_URL = "https://apis.data.go.kr/1230000/ao/HrcspSsstndrdInfoService/getPublicPrcureThngInfoServc"
BID_URL = "https://apis.data.go.kr/1230000/ad/BidPublicInfoService/getBidPblancListInfoServc"


def _load_service_key():
    """Reads the data.go.kr service key from backend/inputs/secrets/narajangteo_key.txt
    (kept out of the pipeline's tracked JSON inputs since it's a credential, not data)."""
    key_path = INPUT_DIR / "secrets" / "narajangteo_key.txt"
    if not key_path.exists():
        raise FileNotFoundError(
            f"나라장터 서비스키 파일이 없습니다: {key_path}\n"
            "data.go.kr에서 받은 인증키(Encoding)를 이 파일에 한 줄로 저장하세요."
        )
    return key_path.read_text(encoding="utf-8").strip()


def _matches_ax_keyword(text):
    text = text or ""
    return any(k.lower() in text.lower() for k in AX_KEYWORDS)


def _date_range(days_back):
    end = datetime.now()
    begin = end - timedelta(days=days_back)
    return begin.strftime("%Y%m%d0000"), end.strftime("%Y%m%d2359")


def collect_prespec(days_back=14, max_pages=5):
    """사전규격정보 — RFP가 뜨기 전, 배정예산·규격서가 먼저 공개되는 단계."""
    key = _load_service_key()
    begin_dt, end_dt = _date_range(days_back)
    docs = []
    for page in range(1, max_pages + 1):
        resp = requests.get(PRESPEC_URL, params={
            "serviceKey": key, "pageNo": page, "numOfRows": 100,
            "inqryDiv": 1, "inqryBgnDt": begin_dt, "inqryEndDt": end_dt, "type": "json",
        }, timeout=15)
        resp.raise_for_status()
        body = resp.json().get("response", {}).get("body", {})
        items = body.get("items") or []
        if not items:
            break
        for it in items:
            title = it.get("prdctClsfcNoNm", "")
            if not _matches_ax_keyword(title):
                continue
            budget = it.get("asignBdgtAmt")
            body_text = f"수요기관: {it.get('rlDminsttNm','')} · 배정예산: {budget}원" if budget else f"수요기관: {it.get('rlDminsttNm','')}"
            docs.append(RawDocument(
                source="나라장터-사전규격",
                title=title,
                body=body_text,
                published_at=(it.get("rcptDt") or "")[:10] or None,
                url=it.get("specDocFileUrl1") or f"https://www.g2b.go.kr (사전규격번호 {it.get('bfSpecRgstNo','')})",
            ))
        if len(items) < 100:
            break
    return docs


def collect_bid_announcements(days_back=14, max_pages=5):
    """입찰공고정보 — 사전규격 다음 단계, RFP가 실제로 공고된 시점."""
    key = _load_service_key()
    begin_dt, end_dt = _date_range(days_back)
    docs = []
    for page in range(1, max_pages + 1):
        resp = requests.get(BID_URL, params={
            "serviceKey": key, "pageNo": page, "numOfRows": 100,
            "inqryDiv": 1, "inqryBgnDt": begin_dt, "inqryEndDt": end_dt, "type": "json",
        }, timeout=15)
        resp.raise_for_status()
        body = resp.json().get("response", {}).get("body", {})
        items = body.get("items") or []
        if not items:
            break
        for it in items:
            title = it.get("bidNtceNm", "")
            if not _matches_ax_keyword(title):
                continue
            budget = it.get("asignBdgtAmt")
            parts = [f"공고기관: {it.get('ntceInsttNm','')}", f"수요기관: {it.get('dminsttNm','')}"]
            if budget:
                parts.append(f"배정예산: {budget}원")
            if it.get("bidClseDt"):
                parts.append(f"입찰마감: {it['bidClseDt']}")
            docs.append(RawDocument(
                source="나라장터-입찰공고",
                title=title,
                body=" · ".join(parts),
                published_at=(it.get("bidNtceDt") or "")[:10] or None,
                url=it.get("bidNtceUrl") or it.get("bidNtceDtlUrl") or "",
            ))
        if len(items) < 100:
            break
    return docs


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    prespec = collect_prespec()
    bids = collect_bid_announcements()
    print(f"사전규격 AX 관련: {len(prespec)}건")
    for d in prespec[:5]:
        print(" -", d.title)
    print(f"입찰공고 AX 관련: {len(bids)}건")
    for d in bids[:5]:
        print(" -", d.title)
