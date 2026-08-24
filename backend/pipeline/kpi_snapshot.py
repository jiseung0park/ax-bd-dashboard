import sys
sys.stdout.reconfigure(encoding='utf-8')
import json
import os
from datetime import datetime, timezone

from paths import INPUT_DIR, OUTPUT_DIR

# baseline lives under inputs/ (checked-in reference point), not output/,
# so a full pipeline re-run doesn't wipe out the previous snapshot to diff against
SNAPSHOT_PATH = INPUT_DIR / "kpi_snapshot.json"

with open(OUTPUT_DIR / "pledges_data.json", encoding="utf-8") as f:
    data = json.load(f)
with open(OUTPUT_DIR / "anchor_summary.json", encoding="utf-8") as f:
    anchors = json.load(f)

projects = data["projects"]

current = {
    "grade1": sum(1 for p in projects if p["entry_grade"] == "1순위: 선제 제안 대상"),
    "grade2": sum(1 for p in projects if p["entry_grade"] == "2순위: 공식 입찰 대상"),
    "grade3": sum(1 for p in projects if p["entry_grade"] == "3순위: 경쟁열위"),
    "total": len(projects),
    "anchors": len(anchors),
    "verified": sum(1 for p in projects if p.get("evidence_url")),
    # broader, honestly-positive framing for the KPI strip: "we have a real
    # source link" (competitor-research evidence_url OR any dated log entry
    # with a URL) — distinct from the stricter per-project trust_badge, which
    # still only shows "출처 링크 확인됨" for the narrower evidence_url case.
    "has_source": sum(
        1 for p in projects
        if p.get("evidence_url") or any(e.get("url") for e in p.get("log", []))
    ),
}

# per-project field snapshot — powers the "최근 변경사항" feed (기능: 사업 변화
# 모니터). 이전 스냅샷이 있을 때만 diff를 계산한다 — 없으면 가짜 변화량을 만들지 않음.
SNAPSHOT_FIELDS = ["executor", "budget_text", "filing_status", "entry_grade", "anchor"]
FIELD_LABELS = {
    "executor": "수행기관", "budget_text": "예산", "filing_status": "공고상태",
    "entry_grade": "사업단계", "anchor": "앵커기업",
}
current_projects_snapshot = {
    str(p["no"]): {**{f: p.get(f) for f in SNAPSHOT_FIELDS}, "name": p["name"]}
    for p in projects
}

previous = None
previous_projects = None
if os.path.exists(SNAPSHOT_PATH):
    with open(SNAPSHOT_PATH, encoding="utf-8") as f:
        prev_payload = json.load(f)
        previous = prev_payload.get("counts")
        previous_projects = prev_payload.get("projects")

deltas = {}
for k, v in current.items():
    if previous and k in previous:
        deltas[k] = v - previous[k]
    else:
        deltas[k] = None  # NEW / no baseline yet

changes = []
if previous_projects:
    for no, cur in current_projects_snapshot.items():
        prev = previous_projects.get(no)
        if prev is None:
            changes.append({"no": no, "name": cur["name"], "type": "new"})
            continue
        for f in SNAPSHOT_FIELDS:
            if cur.get(f) != prev.get(f):
                changes.append({
                    "no": no, "name": cur["name"], "type": "field_change",
                    "field": f, "field_label": FIELD_LABELS[f],
                    "old": prev.get(f), "new": cur.get(f),
                })

out = {
    "counts": current,
    "deltas": deltas,
    "changes": changes,
    "has_previous_snapshot": previous_projects is not None,
    "updated_at": datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M"),
}

with open(OUTPUT_DIR / "kpi_snapshot_result.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)

# persist the new baseline for the *next* run
with open(SNAPSHOT_PATH, "w", encoding="utf-8") as f:
    json.dump({"counts": current, "projects": current_projects_snapshot}, f, ensure_ascii=False, indent=1)

print("current:", current)
print("deltas:", deltas)
print("변경사항:", len(changes), "건 (이전 스냅샷", "있음" if previous_projects else "없음", ")")
print("updated_at:", out["updated_at"])
