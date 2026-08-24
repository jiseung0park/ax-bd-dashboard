import sys
sys.stdout.reconfigure(encoding='utf-8')
import json
import re
from collections import defaultdict

from paths import OUTPUT_DIR

with open(OUTPUT_DIR / "pledges_data.json", encoding="utf-8") as f:
    data = json.load(f)

projects = data["projects"]
accounts_c3 = data["accounts_c3"]
accounts_c4 = data["accounts_c4"]


def norm(s):
    if not s:
        return ""
    return re.sub(r"[\s()（）]", "", str(s))


# consolidate C3+C4 rows per group (multiple rows per group -> merge, first non-null wins)
consolidated = {}
for row in accounts_c3 + accounts_c4:
    key = norm(row["group"])
    if not key:
        continue
    merged = consolidated.setdefault(key, {"display_name": row["group"], "fields": {}})
    for k, v in row.items():
        if k in ("group", "row_label") or not v:
            continue
        merged["fields"].setdefault(k, v)

FIELD_LABELS = {
    "senior_partner": "시니어파트너", "leader": "Leader", "assurance": "Assurance",
    "tax": "Tax", "deals": "Deals", "consulting": "Consulting",
    "grp": "GRP", "global_coordinator": "Global Coordinator", "srp": "SRP",
}


def find_account(anchor_name):
    key = norm(anchor_name)
    if key in consolidated:
        return consolidated[key]
    # substring match both ways (e.g. "HD현대(현대중공업)" vs "HD현대")
    for ck, cv in consolidated.items():
        if ck in key or key in ck:
            return cv
    return None


# aggregate anchors across projects
agg = defaultdict(lambda: {"projects": [], "regions": set()})
for p in projects:
    if not p.get("anchor"):
        continue
    name = p["anchor"].strip()
    a = agg[name]
    a["projects"].append({"no": p["no"], "name": p["name"], "region": p["region"], "entry_grade": p["entry_grade"]})
    a["regions"].add(p["region"])

anchor_list = []
for name, info in agg.items():
    account = find_account(name)
    anchor_list.append({
        "name": name,
        "project_count": len(info["projects"]),
        "regions": sorted(info["regions"]),
        "projects": info["projects"],
        "account": {
            "display_name": account["display_name"],
            "fields": {FIELD_LABELS.get(k, k): v for k, v in account["fields"].items()},
        } if account else None,
    })

anchor_list.sort(key=lambda x: -x["project_count"])

with open(OUTPUT_DIR / "anchor_summary.json", "w", encoding="utf-8") as f:
    json.dump(anchor_list, f, ensure_ascii=False, indent=1)

print("고유 앵커기업 수:", len(anchor_list))
matched = sum(1 for a in anchor_list if a["account"])
print("PwC 계정 매핑 성공:", matched, "/", len(anchor_list))
for a in anchor_list:
    print(a["name"], "| 프로젝트", a["project_count"], "| 계정매핑:", bool(a["account"]))
