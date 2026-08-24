"""Update Center 파이프라인 오케스트레이터 (1차 MVP).

collectors → matcher(Top3 추천) → extractor(1위 후보 기준 변경 후보 미리보기)
→ backend/output/update_candidates.json (검토 대기열)

이 스크립트는 후보만 만든다 — 사람이 검토/승인하기 전까지 Project Master
(pledges_data.json)는 절대 건드리지 않는다. 승인 흐름은 다음 단계.
"""
import sys
import os
import json
from datetime import datetime, timezone

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "pipeline"))
from paths import OUTPUT_DIR

from collectors import naramarket_collector, korea_kr_collector
from matcher import build_project_index, top_matches
from extractor import extract_change_candidates

MIN_SCORE_TO_SURFACE = 0.08  # below this, TF-IDF match is noise — don't bother a human with it


def run(days_back=14):
    print("=== 1. 수집 ===")
    docs = []
    try:
        docs += naramarket_collector.collect_prespec(days_back=days_back)
        docs += naramarket_collector.collect_bid_announcements(days_back=days_back)
    except FileNotFoundError as e:
        print(f"[건너뜀] 나라장터: {e}")
    try:
        docs += korea_kr_collector.collect(days_back=days_back)
    except Exception as e:
        print(f"[건너뜀] 정책브리핑: {e}")
    print(f"수집된 문서: {len(docs)}건")

    print("=== 2. 사업 매칭 ===")
    index = build_project_index()
    projects_by_no = {p["no"]: p for p in index["projects"]}

    print("=== 3. 변경후보 추출 (1위 매칭 기준 미리보기) ===")
    inbox = []
    for doc in docs:
        matches = top_matches(doc, index, k=3)
        matches = [m for m in matches if m["score"] >= MIN_SCORE_TO_SURFACE]
        if not matches:
            continue
        top_project = projects_by_no[matches[0]["no"]]
        preview = extract_change_candidates(top_project, doc)
        inbox.append({
            "doc": doc.to_dict(),
            "top_matches": matches,
            "event_type": preview["event_type"],
            "change_candidates_preview": preview["candidates"],
            "status": "검토필요",
        })

    inbox.sort(key=lambda x: x["top_matches"][0]["score"], reverse=True)

    out = {
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "days_back": days_back,
        "collected_count": len(docs),
        "surfaced_count": len(inbox),
        "inbox": inbox,
    }
    out_path = OUTPUT_DIR / "update_candidates.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(f"검토 대기열: {len(inbox)}건 → {out_path}")
    return out


if __name__ == "__main__":
    run()
