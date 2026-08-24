"""기능 3 — "이 문서 때문에 DB에서 뭐를 업데이트해야 해?"

사람이 관련 사업을 최종 선택한 뒤, 그 사업의 현재 값과 신규 문서를 비교해 변경
후보를 만든다. LLM 자유요약이 아니라 규칙 기반 필드 추출(extract_pledges.py의
예산/시점 정규식 추출과 같은 철학) — 나중에 LLM 추출로 업그레이드할 여지는
남겨두되, 1차 MVP는 결정적이고 설명 가능해야 한다. 모든 변경 후보는 원문 근거
문장 + URL을 같이 저장해서 "왜 바뀌었냐"를 항상 답할 수 있게 한다.
"""
import re

EXECUTOR_RE = re.compile(r'([가-힣A-Za-z0-9()]{2,20}?)\s*(?:이|가)?\s*(?:수행|주관|운영|추진)(?:한다|합니다|중)?')
BUDGET_RE = re.compile(
    r'(\d[\d,]*(?:\.\d+)?\s*조\s*(?:\d[\d,]*(?:\.\d+)?\s*억)?\s*원|\d[\d,]*(?:\.\d+)?\s*억\s*원)'
)
STAGE_KEYWORDS = [
    (["선정결과", "낙찰자 결정", "수행기관 선정", "우선협상대상자"], "수행기관 선정 완료"),
    (["공고", "모집공고", "입찰공고", "접수 중", "접수중"], "공고 진행중"),
    (["사전규격", "규격서 의견"], "공고 준비(사전규격)"),
    (["협약", "체결"], "협약 체결"),
    (["착수", "착수보고회"], "사업 착수"),
]
EVENT_TYPE_KEYWORDS = [
    (["공고", "모집공고", "입찰공고"], "공고"),
    (["선정", "낙찰", "우선협상대상자"], "선정"),
    (["예산", "배정예산", "출연"], "예산"),
    (["협약", "체결", "MOU"], "협약"),
]


def _guess_event_type(text):
    for keywords, label in EVENT_TYPE_KEYWORDS:
        if any(k in text for k in keywords):
            return label
    return "기타"


def _guess_stage(text):
    for keywords, label in STAGE_KEYWORDS:
        if any(k in text for k in keywords):
            return label
    return None


def _guess_executor(text):
    m = EXECUTOR_RE.search(text)
    return m.group(1).strip() if m else None


def _guess_budget(text):
    m = BUDGET_RE.search(text)
    return m.group(1).replace(" ", "") if m else None


def extract_change_candidates(project, doc):
    """project: 기존 pledges_data.json의 project dict.
    doc: RawDocument (매칭된 신규 문서).
    반환: [{field, field_label, old_value, new_value, evidence, url}] — 실제로
    달라지는(또는 새로 채워지는) 필드만 포함, 값이 같으면 후보에 안 올라감."""
    text = f"{doc.title} {doc.body}"
    candidates = []

    new_executor = _guess_executor(text)
    old_executor = project.get("executor") or "미정"
    if new_executor and new_executor != old_executor and new_executor not in (old_executor or ""):
        candidates.append({
            "field": "executor", "field_label": "수행기관",
            "old_value": old_executor, "new_value": new_executor,
            "evidence": doc.title, "url": doc.url,
        })

    new_budget = _guess_budget(text)
    old_budget = project.get("budget_text") or "미확인"
    if new_budget and new_budget != old_budget:
        candidates.append({
            "field": "budget_text", "field_label": "예산",
            "old_value": old_budget, "new_value": new_budget,
            "evidence": doc.title, "url": doc.url,
        })

    new_stage = _guess_stage(text)
    old_filing = project.get("filing_status") or "미확인"
    if new_stage and new_stage != old_filing:
        candidates.append({
            "field": "filing_status", "field_label": "공고상태",
            "old_value": old_filing, "new_value": new_stage,
            "evidence": doc.title, "url": doc.url,
        })

    # 최근동향은 항상 "추가" 후보로 제안 (필드값 대체가 아니라 로그 누적이라 성격이 다름)
    candidates.append({
        "field": "log_append", "field_label": "최근동향(신규 로그 추가)",
        "old_value": None, "new_value": doc.title,
        "evidence": doc.body or doc.title, "url": doc.url,
    })

    return {
        "event_type": _guess_event_type(text),
        "candidates": candidates,
    }


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    from raw_document import RawDocument
    fake_project = {"name": "중소기업 AI 전환 지원", "executor": "미정", "budget_text": None, "filing_status": "공고전"}
    doc = RawDocument(
        source="test", title="충남테크노파크, 중소기업 AI 전환 지원사업 75억 규모 공고",
        body="충남테크노파크가 수행하는 이번 사업은 총사업비 75억원 규모로 9월 공모를 시작한다.",
        published_at=None, url="https://example.com",
    )
    result = extract_change_candidates(fake_project, doc)
    print("event_type:", result["event_type"])
    for c in result["candidates"]:
        print(f"  [{c['field_label']}] {c['old_value']} → {c['new_value']}")
