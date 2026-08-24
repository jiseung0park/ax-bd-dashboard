"""기능 2 — "이 문서는 어느 기존 사업 얘기냐?"

신규 문서(제목+본문)를 기존 트래킹 사업(사업명+최근동향) 텍스트와 비교해 Top 3 후보를
반환한다. 자동 확정은 하지 않음 — 사람이 최종 선택(기능 3의 입력이 됨).

문자 n-gram TF-IDF + 코사인 유사도를 쓴다(sentence-transformer 계열 임베딩은
huggingface.co 접근이 막혀 있어 이 환경에서 모델을 못 받아옴 — 완전 로컬,
네트워크/API 키 불필요한 방식으로 대체. 한국어는 띄어쓰기 기반 토큰화보다 문자
n-gram이 형태소 분석 없이도 부분 일치를 잘 잡아서 이런 용도엔 오히려 안정적).
"""
import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "pipeline"))
from paths import OUTPUT_DIR

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def _project_corpus_text(p):
    parts = [p.get("name") or "", p.get("biz_type") or "", p.get("latest_news") or ""]
    for entry in (p.get("log") or [])[-2:]:
        if entry.get("text"):
            parts.append(entry["text"])
    return " ".join(x for x in parts if x)


def load_projects():
    with open(OUTPUT_DIR / "pledges_data.json", encoding="utf-8") as f:
        return json.load(f)["projects"]


def build_project_index(projects=None):
    """Fits the TF-IDF vectorizer once on the tracked-project corpus. Reuse
    the returned index across many documents in the same run."""
    projects = projects or load_projects()
    texts = [_project_corpus_text(p) for p in projects]
    vectorizer = TfidfVectorizer(analyzer="char", ngram_range=(3, 6), min_df=1, sublinear_tf=True)
    matrix = vectorizer.fit_transform(texts)
    return {"projects": projects, "vectorizer": vectorizer, "matrix": matrix}


def top_matches(doc, index, k=3):
    """doc: RawDocument (or dict with .title/.body). Returns list of
    {no, name, region, entry_grade, score} sorted by score desc."""
    title = getattr(doc, "title", None) if hasattr(doc, "title") else doc.get("title", "")
    body = getattr(doc, "body", None) if hasattr(doc, "body") else doc.get("body", "")
    text = f"{title} {body}"
    query_vec = index["vectorizer"].transform([text])
    sims = cosine_similarity(query_vec, index["matrix"])[0]
    order = sims.argsort()[::-1][:k]
    results = []
    for i in order:
        p = index["projects"][i]
        results.append({
            "no": p["no"], "name": p["name"], "region": p["region"],
            "entry_grade": p["entry_grade"], "score": round(float(sims[i]), 4),
        })
    return results


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    from raw_document import RawDocument
    index = build_project_index()
    print(f"인덱싱된 사업: {len(index['projects'])}건")
    sample = RawDocument(
        source="test", title="충남 제조기업 AI 전환 지원 확대",
        body="충남테크노파크가 지역 중소 제조기업을 대상으로 AI 전환 지원사업을 확대한다고 밝혔다.",
        published_at=None, url="https://example.com",
    )
    for m in top_matches(sample, index):
        print(f"  {m['name']} ({m['region']}) — {m['score']*100:.0f}%")
