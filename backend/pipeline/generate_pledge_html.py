import sys
sys.stdout.reconfigure(encoding='utf-8')
import json
import re
import html as htmlmod
from collections import defaultdict
from datetime import datetime

from paths import OUTPUT_DIR
import korea_map

IN = OUTPUT_DIR / "pledges_data.json"
OUT = OUTPUT_DIR / "pledge_fragment.html"
OUT_SUMMARY = OUTPUT_DIR / "pledge_fragment_summary.json"

with open(IN, encoding="utf-8") as f:
    data = json.load(f)
with open(OUTPUT_DIR / "anchor_summary.json", encoding="utf-8") as f:
    anchors = json.load(f)
with open(OUTPUT_DIR / "kpi_snapshot_result.json", encoding="utf-8") as f:
    kpi = json.load(f)

projects = data["projects"]
pledges = data["pledges"]


def esc(v):
    if v is None:
        return ""
    return htmlmod.escape(str(v), quote=True)


def slugify(name):
    return re.sub(r'[^a-zA-Z0-9가-힣]+', '-', name or '').strip('-')


PROCESS_STEPS = [
    "후보자 공약", "당선·인수위 검토", "도정·시정 비전 반영", "담당 실·국 지정",
    "사업기획·수요조사", "사업유형·재원 결정", "소관 중앙부처 반영", "예산심사", "연도별 시행계획",
]

# hand-drawn minimal line icons, 24x24 viewBox, stroke=currentColor
PROCESS_ICONS = [
    '<path d="M5 21V4M5 4h13l-3 4 3 4H5"/>',
    '<path d="M12 3l7 3v6c0 5-3.5 8-7 9-3.5-1-7-4-7-9V6l7-3z"/><path d="M9 12l2 2 4-4"/>',
    '<circle cx="12" cy="12" r="8"/><circle cx="12" cy="12" r="2.5"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3"/>',
    '<path d="M4 21V7l8-4 8 4v14"/><path d="M9 21v-6h6v6"/><path d="M9 11h.01M15 11h.01"/>',
    '<rect x="5" y="3" width="14" height="18" rx="1.5"/><path d="M9 3h6v3H9z"/><circle cx="10.5" cy="13" r="2.5"/><path d="M12.5 15L15 17.5"/>',
    '<rect x="3" y="14.5" width="18" height="4" rx="2"/><rect x="3" y="9.5" width="18" height="4" rx="2"/><rect x="3" y="4.5" width="18" height="4" rx="2"/>',
    '<path d="M3 21h18M4 21V10l8-6 8 6v11M9 21v-6h6v6"/><path d="M9 10h.01M12 10h.01M15 10h.01"/>',
    '<path d="M14 4l6 6-2 2-6-6z"/><path d="M12.5 5.5L4 14l2 2 8.5-8.5"/><path d="M2 22l4-4"/>',
    '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M3 10h18M8 3v4M16 3v4"/><path d="M8 14h.01M12 14h.01M16 14h.01M8 17h.01M12 17h.01"/>',
]

# ---- 기획제안형 BD 6단계: RFP 발주 전 선제 진입 경로(삼일PwC BD 전략 프레임) ----
BD_PROCESS_STEPS = [
    "정부정책 분석", "지역사업 구체화", "아젠다 선제기획", "앵커기업·기관 컨텍", "기획제안·RFP설계", "본사업·PMO 수주",
]
BD_PROCESS_ICONS = [
    '<circle cx="10" cy="10" r="6"/><path d="M15 15l6 6"/>',
    '<path d="M12 21s7-6.5 7-12a7 7 0 1 0-14 0c0 5.5 7 12 7 12z"/><circle cx="12" cy="9" r="2.5"/>',
    '<path d="M9 18h6M10 22h4M12 2a6 6 0 0 0-4 10.5c.7.6 1 1.3 1 2.5h6c0-1.2.3-1.9 1-2.5A6 6 0 0 0 12 2z"/>',
    '<circle cx="8" cy="8" r="3"/><circle cx="16" cy="8" r="3"/><path d="M2 21c0-3.5 2.5-6 6-6M22 21c0-3.5-2.5-6-6-6"/>',
    '<path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4 12.5-12.5z"/>',
    '<path d="M8 21h8M12 17v4M7 4h10v4a5 5 0 0 1-10 0V4z"/><path d="M7 6H4a3 3 0 0 0 3 5M17 6h3a3 3 0 0 1-3 5"/>',
]

GRADE_SHORT = {
    "1순위: 선제 제안 대상": "기획단계",
    "2순위: 공식 입찰 대상": "공고단계",
    "3순위: 경쟁열위": "경쟁단계",
    "미조사": "미조사",
}
GRADE_CLASS = {
    "1순위: 선제 제안 대상": "grade1",
    "2순위: 공식 입찰 대상": "grade2",
    "3순위: 경쟁열위": "grade3",
    "미조사": "grade0",
}
POTENTIAL_LABEL = {"A": "잠재등급 A", "B": "잠재등급 B", "C": "잠재등급 C"}

# 기획제안형 BD 6단계(①정부정책분석 ②지역사업구체화 ③아젠다선제기획 ④앵커기업·기관컨텍
# ⑤기획제안·RFP설계 ⑥본사업수주) 상에서 entry_grade가 지금 어디에 해당하는지 매핑.
# entry_grade == "공고전"이면 아직 기획제안형 창구가 열려있고(③~④), "공고중"이면
# 이미 RFP가 구체화돼 반응형 수주경쟁으로 넘어간 것(⑤), "경쟁사확정"이면 이번 사이클 종료(⑥).
BD_STAGE_LABEL = {
    "1순위: 선제 제안 대상": "③~④ 선제기획·컨택",
    "2순위: 공식 입찰 대상": "⑤ RFP 대응(반응형 전환)",
    "3순위: 경쟁열위": "⑥ 수주종료(경쟁사)",
    "미조사": "① 정책분석 필요",
}
BD_STEP_CURRENT = {
    "1순위: 선제 제안 대상": 3, "2순위: 공식 입찰 대상": 5,
    "3순위: 경쟁열위": 6, "미조사": 1,
}


def entry_reason_tags(p):
    """Short, honest status tags built only from fields that actually exist —
    no invented maturity score. Answers "왜 이 등급인가" at a glance."""
    tags = []
    if p.get("executor") and p["executor"] != "미정":
        tags.append(f"수행기관 확정: {p['executor'][:14]}")
    else:
        tags.append("수행기관 미확정")
    tags.append("앵커기업 후보 존재" if p.get("anchor") else "앵커기업 후보 없음")
    tags.append(f"예산 확인됨: {p['budget_text']}" if p.get("budget_text") else "예산 미확정")
    if p.get("latest_news"):
        tags.append("최근 정책동향 확인됨")
    return tags


def next_action_detail(p, grade):
    """다음 액션을 프로젝트 실제 필드(주관기관/수행기관/앵커기업)로 구체화한다.
    필드가 없으면 일반 단계명으로 정직하게 폴백 — 없는 접점을 지어내지 않는다."""
    current = BD_STEP_CURRENT.get(grade, 1)
    if grade == "3순위: 경쟁열위":
        return '이번 사이클 종료 — 후속·연차 사업 모니터링 권장'
    if current >= len(BD_PROCESS_STEPS):
        return '본사업·PMO 수주 단계'
    next_step = BD_PROCESS_STEPS[current]
    org = p.get("org") or p.get("ministry")
    anchor_first = (p.get("anchor") or "").split(",")[0].split("\n")[0].strip()
    if next_step == "앵커기업·기관 컨택":
        if anchor_first:
            return f'앵커기업({esc(anchor_first)}) 참여 가능성 확인 후 사업구조 구체화'
        if org:
            return f'{esc(org)} 사업기획 담당 접점 확인'
        return '수행·주관기관 사업기획 담당 접점 확인'
    if next_step == "아젠다 선제기획":
        return '정책방향 기반 기획제안 Agenda 구성'
    if next_step == "기획제안·RFP설계":
        return '기획제안서·RFP 초안 설계 착수'
    if next_step == "지역사업 구체화":
        return '지역 정책방향 기반 사업 범위·모델 구체화'
    return esc(next_step)


def next_action_stepper(p, grade):
    current = BD_STEP_CURRENT.get(grade, 1)
    ended = grade == "3순위: 경쟁열위"
    items = []
    for i, step in enumerate(BD_PROCESS_STEPS, start=1):
        if ended:
            cls = "ps-done" if i <= current else "ps-future"
        elif i < current:
            cls = "ps-done"
        elif i == current:
            cls = "ps-current"
        else:
            cls = "ps-future"
        items.append(f'<div class="mini-step {cls}"><span class="ms-dot"></span><span class="ms-label">{esc(step)}</span></div>')
    next_line = f'다음 액션: <b>{next_action_detail(p, grade)}</b>'
    return f'<div class="mini-stepper">{"".join(items)}</div><div class="mini-step-next">{next_line}</div>'


def stakeholder_chain_html(p, partner_names):
    """중앙정부→지자체→수행기관→앵커기업→PwC 담당 체인 — 전부 실제 DB 필드에서만
    가져온다. 값이 없으면 '미정'/'확인 필요'로 정직하게 표시(가상 데이터 생성 금지)."""
    anchor_first = ((p.get("anchor") or "").split(",")[0].split("\n")[0].strip()) or "미정"
    nodes = [
        ("소관부처", p.get("ministry") or "확인 필요"),
        ("주관기관", p.get("org") or "확인 필요"),
        ("수행기관", p.get("executor") if p.get("executor") and p.get("executor") != "미정" else "미정"),
        ("앵커기업", anchor_first),
        ("PwC 담당", partner_names if partner_names and partner_names != "미지정" else "미지정"),
    ]
    parts = []
    for i, (k, v) in enumerate(nodes):
        parts.append(f'<div class="sh-node"><div class="sh-node-k">{esc(k)}</div><div class="sh-node-v">{esc(v)}</div></div>')
        if i < len(nodes) - 1:
            parts.append('<div class="sh-arrow">→</div>')
    return "".join(parts)


# deterministic, grade-keyed approach guidance — never per-project invented text,
# just the fixed strategic implication of the already-computed entry_grade.
STRATEGY_TEMPLATE = {
    "1순위: 선제 제안 대상": "지역 아젠다가 아직 RFP로 구체화되지 않았습니다 — 기획제안형 BD ③아젠다 선제기획 → ④앵커기업·기관 컨텍 단계입니다. 사업모델을 먼저 설계해 유관기관에 제안하세요.",
    "2순위: 공식 입찰 대상": "RFP가 이미 구체화되어 공고·모집이 진행 중입니다 — 기획제안형 창구는 닫혔고 공고이후 수주경쟁 방식(제안서 작성·입찰경쟁)으로 전환됩니다.",
    "3순위: 경쟁열위": "경쟁사·수행기관이 이미 확정됐습니다 — 이번 사이클은 종료된 것으로 보고 후속·연차 사업에서 재진입 기회를 모니터링하세요.",
    "미조사": "① 정부정책분석·리서치가 아직 완료되지 않았습니다. 진입전략을 판단하기 전에 최신동향 로그 확인 또는 추가 리서치가 필요합니다.",
}


def trust_badge(p):
    """Surfaces how verifiable the entry_grade / competitor research actually is,
    so a partner knows what to double-check before acting on it."""
    if p["entry_grade"] == "미조사":
        return '<span class="trust-badge unresearched">리서치 미완료</span>'
    if p.get("evidence_url"):
        return '<span class="trust-badge verified">출처 링크 확인됨</span>'
    return '<span class="trust-badge unverified">AI 추정 · 출처 미확인</span>'

# ---- summary JSON for table / cross-tab JS rendering ----
summary = []
for p in projects:
    latest_news_line = p.get("latest_news") or (p["log"][-1]["text"] if p.get("log") else None)
    summary.append({
        "no": p["no"], "region": p["region"], "group": p["group"], "name": p["name"],
        "biz_type": p["biz_type"], "stage": p["stage"], "executor": p["executor"], "org": p["org"],
        "anchor": p["anchor"], "latest_news": latest_news_line, "new_or_existing": p["new_or_existing"],
        "entry_grade": p["entry_grade"], "filing_status": p["filing_status"],
        "competition_status": p["competition_status"], "is_yeta": p["is_yeta"],
        "potential_grade": p.get("potential_grade"), "budget_text": p.get("budget_text"),
        "budget_eok": p.get("budget_eok"), "filing_estimate": p.get("filing_estimate"),
        "has_evidence": bool(p.get("evidence_url")),
        "has_source": bool(p.get("evidence_url") or any(e.get("url") for e in p.get("log", []))),
    })

# ---- Korea map data: count by region (combined region tags like "전남·광주" are split) ----
map_counts = {}
for p in projects:
    for r in korea_map.expand_region(p["region"]):
        d = map_counts.setdefault(r, {"total": 0, "grade1": 0})
        d["total"] += 1
        if p["entry_grade"] == "1순위: 선제 제안 대상":
            d["grade1"] += 1
map_svg, map_pins = korea_map.build_svg(map_counts)

MAP_PIN_INTENSITY_CLASS = lambda i: "hi" if i >= 0.7 else ("mid" if i >= 0.3 else ("lo" if i > 0 else "zero"))
map_pin_html = "".join(f'''
<button type="button" class="map-pin {MAP_PIN_INTENSITY_CLASS(pin["intensity"])} {"has-grade1" if pin["grade1"] > 0 else ""}"
  style="left:{pin["left_pct"]}%; top:{pin["top_pct"]}%;" data-region="{esc(pin["name"])}" title="{esc(pin["name"])}: {pin["total"]}건">
  <span class="mp-dot"><span class="mp-count tabular">{pin["total"]}</span></span>
  <span class="mp-label">{esc(pin["name"])}</span>
</button>''' for pin in map_pins)

# ---- "최근 포착된 사업 신호" — data-driven pick, recomputed every pipeline run so it
# stays current as the tracker Excel is refreshed. No real per-project update
# date exists in the source data, so this ranks by actionability signal
# (still-open + action keyword in the latest news + verified source) rather
# than true recency. BD 관점에서 신호 종류를 구분해 보여준다 — 전부 latest_news 실제
# 텍스트/anchor 필드 매칭에서만 도출, 가상 카테고리 생성 없음.
WATCH_ACTION_KEYWORDS = ["공고", "모집", "접수", "용역", "선정", "착수", "협약", "체결", "마감", "입찰", "공모"]
SIGNAL_FILING_KEYWORDS = ["공고", "입찰", "모집", "공모", "마감"]
SIGNAL_EXEC_KEYWORDS = ["선정", "협약", "체결", "수행", "위탁", "착수"]
SIGNAL_BUDGET_KEYWORDS = ["예산", "출연", "국비", "투자"]

def signal_label(p):
    text = p.get("latest_news") or ""
    anchor_first = (p.get("anchor") or "").split(",")[0].split("\n")[0].strip()
    if anchor_first and anchor_first in text:
        return "앵커기업 참여"
    if any(k in text for k in SIGNAL_FILING_KEYWORDS):
        return "공고 예정"
    if any(k in text for k in SIGNAL_EXEC_KEYWORDS):
        return "수행기관 논의"
    if any(k in text for k in SIGNAL_BUDGET_KEYWORDS):
        return "예산 반영"
    return "사업 구체화 움직임"

def watch_score(p):
    text = p.get("latest_news") or ""
    score = 0
    if p["entry_grade"] == "1순위: 선제 제안 대상":
        score += 10
    if any(k in text for k in WATCH_ACTION_KEYWORDS):
        score += 5
    if p.get("evidence_url"):
        score += 3
    return score

watch_candidates = [p for p in projects if p.get("latest_news")]
watch_candidates.sort(key=watch_score, reverse=True)
recent_watch = watch_candidates[:6]
recent_watch_html = "".join(f'''
<li class="watch-row" data-jump-no="{p['no']}">
  <div class="wr-top">
    <span class="entry-grade-badge {GRADE_CLASS.get(p['entry_grade'],'grade0')}" style="margin-left:0;">{esc(GRADE_SHORT.get(p['entry_grade'], p['entry_grade']))}</span>
    <span class="wr-region">{esc(p['region'])}</span>
  </div>
  <div class="wr-name">{esc(p['name'])}</div>
  <span class="wr-signal">{esc(signal_label(p))}</span>
  <div class="wr-news">{esc(p['latest_news'])}</div>
</li>''' for p in recent_watch) or '<li class="empty-state" style="padding:20px;">표시할 동향이 없습니다.</li>'

# ---- KPI strip (static, real snapshot deltas) ----
def delta_html(key):
    d = kpi["deltas"].get(key)
    if d is None:
        return '<span class="kpi-delta new">NEW</span>'
    if d > 0:
        return f'<span class="kpi-delta up">▲ {d}</span>'
    if d < 0:
        return f'<span class="kpi-delta down">▼ {abs(d)}</span>'
    return '<span class="kpi-delta flat">변동없음</span>'

KPI_TILES = [
    ("total", "전체 트래킹 사업", ""), ("grade1", "기획단계 · 선제제안", "emph"),
    ("grade2", "공고단계 · RFP진행", ""), ("grade3", "경쟁단계 · 후발진입", ""),
    ("anchors", "매핑된 앵커기업", ""),
]

# clicking a KPI tile filters the list below to just that slice, reusing the
# same pledgeFilter state the quick-filter chips already drive
KPI_GRADE_FILTER = {
    "grade1": "1순위: 선제 제안 대상", "grade2": "2순위: 공식 입찰 대상",
    "grade3": "3순위: 경쟁열위", "total": "",
}

def kpi_click_attrs(key):
    if key in KPI_GRADE_FILTER:
        return f'data-kpi-action="filter-grade" data-kpi-value="{esc(KPI_GRADE_FILTER[key])}"'
    if key == "anchors":
        return 'data-kpi-action="goto-anchors"'
    return ''

pledge_kpi_html = "".join(f'''
    <div class="kpi {emph}" {kpi_click_attrs(key)}>
      <div class="label">{esc(label)}</div>
      <div class="value tabular">{kpi["counts"][key]}<span class="unit">건</span></div>
      {delta_html(key)}
    </div>''' for key, label, emph in KPI_TILES)

# ---- AI Insight panel (static, data-driven sentences — computed at build time, not live-generated) ----
def top_n(counter_src, n=1):
    c = defaultdict(int)
    for v in counter_src:
        if v:
            c[v] += 1
    return sorted(c.items(), key=lambda x: -x[1])[:n]

grade1_projects = [p for p in projects if p["entry_grade"] == "1순위: 선제 제안 대상"]
top_group = top_n((p["group"] for p in grade1_projects), 1)
top_biztype = top_n((p["biz_type"] for p in projects), 1)
yeta_count = sum(1 for p in projects if p.get("is_yeta") in ("예타대상", "예타진행중"))
budget_found = sum(1 for p in projects if p.get("budget_text"))
matched_anchor_count = sum(1 for a in anchors if a.get("account"))

insight_lines = []
if top_group:
    insight_lines.append(f'<b>{esc(top_group[0][0])}</b> 권역이 선제 제안 대상 <b>{top_group[0][1]}건</b>으로 가장 많아 우선 접촉 후보 지역입니다.')
if top_biztype:
    insight_lines.append(f'전체 트래킹 사업 중 <b>{esc(top_biztype[0][0])}</b> 유형이 <b>{top_biztype[0][1]}건</b>으로 가장 큰 비중을 차지합니다.')
insight_lines.append(f'예비타당성조사 대상/진행 사업이 <b>{yeta_count}건</b> 확인되어 초기 자문 진입 여지가 있습니다.')
insight_lines.append(f'앵커기업 <b>{len(anchors)}개사</b> 중 <b>{matched_anchor_count}개사</b>가 기존 PwC 계정과 매핑되어 관계 기반 접근이 가능합니다.')
insight_lines.append(f'예산 규모가 텍스트에서 확인된 사업은 <b>{budget_found}/{len(projects)}건</b>이며, 나머지는 근거자료 확인이 필요합니다.')

ai_insight_html = f'''
<div class="ai-insight-panel" id="aiInsightPanel">
  <div class="aip-head">
    <span class="aip-ic">▤</span> 핵심 지표 요약
    <span class="aip-updated">{esc(kpi["updated_at"])} 기준</span>
  </div>
  <ul class="aip-list">
    {"".join(f"<li>{line}</li>" for line in insight_lines)}
  </ul>
  <div class="aip-note">※ 원본 데이터 집계 기반 자동 요약입니다. AI가 실시간으로 생성하는 문장이 아닙니다.</div>
</div>'''

# ---- static detail blocks (must be real HTML for artifact-sync) ----
def anchor_chip_row(anchor_field, project_no):
    if not anchor_field:
        return '<div style="color:var(--ink-muted); font-size:14px; font-weight:600;">지정된 앵커기업 없음</div>'
    names = [n.strip() for n in re.split(r'[,\n·/、]', anchor_field) if n.strip()]
    chips = "".join(
        f'<button type="button" class="anchor-chip" data-anchor-name="{esc(n)}" title="{esc(n)}">'
        f'<span class="ac-initial">{esc(n[0])}</span>{esc(n)}</button>'
        for n in names
    )
    return f'<div class="anchor-chip-row">{chips}</div>'


detail_blocks = []
for p in projects:
    no = p["no"]
    partners = [x for x in [p.get("grp_partner"), p.get("leader")] if x]
    services = []
    if p.get("assurance"):
        services.append(("Assurance", p["assurance"]))
    if p.get("tax"):
        services.append(("Tax", p["tax"]))
    if p.get("deals"):
        services.append(("Deals", p["deals"]))
    if p.get("consulting"):
        services.append(("Consulting", p["consulting"]))

    log_html = ""
    for entry in p["log"]:
        text = esc(entry.get("text"))
        url = entry.get("url")
        url_html = f'<div class="le-url"><a href="{esc(url)}" target="_blank" rel="noopener">근거 링크 ↗</a></div>' if url else ""
        log_html += f'<li class="log-entry"><div class="le-text">{text}</div>{url_html}</li>\n'
    if not log_html:
        log_html = '<li class="log-entry"><div class="le-text" style="color:var(--ink-muted);">등록된 동향 없음</div></li>\n'

    partner_rows = "".join(
        f'<div><div class="k" style="font-size:11px;color:var(--ink-muted);font-weight:700;">{esc(k)}</div><div class="v" style="font-weight:700;">{esc(v)}</div></div>'
        for k, v in services
    )
    partner_names = ", ".join(esc(x) for x in partners) if partners else "미지정"

    grade = p["entry_grade"]
    grade_class = GRADE_CLASS.get(grade, "grade0")
    yeta_badge = f'<span class="yeta-badge">예타 {esc(p["is_yeta"])}</span>' if p.get("is_yeta") in ("예타대상", "예타진행중") else ""
    evidence_html = ""
    if p.get("evidence_summary"):
        url_part = f' — <a href="{esc(p["evidence_url"])}" target="_blank" rel="noopener">근거링크 ↗</a>' if p.get("evidence_url") else ""
        evidence_html = f'<div style="grid-column:1/-1;"><div class="k">리서치 근거 (자동조사, 참고용)</div><div class="v" style="font-weight:500;">{esc(p["evidence_summary"])}{url_part}</div></div>'
    competitor_line = f'<div><div class="k">경쟁사(추정)</div><div class="v">{esc(p["competitor_name"])}</div></div>' if p.get("competitor_name") else ""

    pgrade = p.get("potential_grade")
    pgrade_badge = f'<div class="stat-cell"><div class="sc-k">잠재등급</div><div class="sc-v"><span class="potential-badge p{esc(pgrade)}">{esc(pgrade or "미정")}</span></div></div>'
    bd_stage_badge = f'<div class="stat-cell"><div class="sc-k">BD 단계</div><div class="sc-v">{esc(BD_STAGE_LABEL.get(grade, BD_STAGE_LABEL["미조사"]))}</div></div>'
    budget_note = ' <span class="stat-asterisk">*텍스트 추정</span>' if p.get("budget_text") else ""
    header_stats = f'''
    <div class="pd-stats">
      {bd_stage_badge}
      {pgrade_badge}
      <div class="stat-cell"><div class="sc-k">공고상태</div><div class="sc-v">{esc(p["filing_status"]) or "확인필요"}</div></div>
      <div class="stat-cell"><div class="sc-k">공고기관</div><div class="sc-v">{esc(p["org"]) or "확인필요"}</div></div>
      <div class="stat-cell"><div class="sc-k">투자예산규모</div><div class="sc-v">{esc(p.get("budget_text")) or "확인필요"}{budget_note}</div></div>
      <div class="stat-cell"><div class="sc-k">예상공고시점</div><div class="sc-v">{esc(p.get("filing_estimate")) or "미정"}</div></div>
      <div class="stat-cell"><div class="sc-k">현재공약단계</div><div class="sc-v">{esc(p["stage"])}</div></div>
      <div class="stat-cell"><div class="sc-k">수행기관현황</div><div class="sc-v">{esc(p["executor"]) or "미정"}</div></div>
    </div>'''

    action_cards = f'''
    <div class="pd-actions">
      <button type="button" class="pd-action" data-action="anchor" data-anchor="{esc((p.get("anchor") or "").split(",")[0].split(chr(10))[0].strip())}" {"disabled" if not p.get("anchor") else ""}>
        <span class="pa-ic">◎</span>앵커기업 프로필 보기
      </button>
      <button type="button" class="pd-action" data-action="evidence" data-url="{esc(p.get("evidence_url") or (p["log"][-1].get("url") if p["log"] else ""))}" {"disabled" if not (p.get("evidence_url") or (p["log"] and p["log"][-1].get("url"))) else ""}>
        <span class="pa-ic">↗</span>근거자료 원문 열기
      </button>
      <button type="button" class="pd-action" data-action="similar" data-biztype="{esc(p["biz_type"])}">
        <span class="pa-ic">≡</span>동일 유형 사업 모아보기
      </button>
      <button type="button" class="pd-action" data-action="log" data-target="pd-{no}">
        <span class="pa-ic">●</span>최신동향 로그로 이동
      </button>
    </div>'''

    block = f"""
<div class="pledge-detail {grade_class}" id="pd-{no}" data-no="{no}" data-grade="{esc(grade)}">
  <div class="pd-head">
    <div class="pd-head-top">
      <div class="pd-region">{esc(p['group'])} · {esc(p['region'])} · {esc(p['politician'])}</div>
      <div class="pd-head-tools">
        <button type="button" class="pd-tool-btn pd-fav-btn" data-fav-no="{no}" title="즐겨찾기">☆</button>
        <button type="button" class="pd-tool-btn" onclick="window.print()" title="인쇄용 보기">⎙ 인쇄</button>
      </div>
    </div>
    <h3>{esc(p['name'])}</h3>
    <span class="stage-badge {esc(p['stage'])}">{esc(p['stage'])}</span>
    <span class="entry-grade-badge {grade_class}">{esc(GRADE_SHORT.get(grade, grade))}</span>
    {yeta_badge}
    <div class="reason-tags">{"".join(f'<span class="reason-tag">{esc(t)}</span>' for t in entry_reason_tags(p))}</div>
  </div>
  <div class="pd-panel" style="margin:16px 0;">
    <h4>현재 진입 포인트 → Next Action</h4>
    {next_action_stepper(p, grade)}
  </div>
  {header_stats}
  <div class="pd-panel" style="margin:16px 0;">
    <h4>진입전략 {trust_badge(p)}</h4>
    <div class="strategy-box {grade_class}">{esc(STRATEGY_TEMPLATE.get(grade, STRATEGY_TEMPLATE["미조사"]))}</div>
    <div class="kv-grid">
      <div><div class="k">공고상태</div><div class="v">{esc(p['filing_status']) or '미조사'}</div></div>
      <div><div class="k">경쟁현황</div><div class="v">{esc(p['competition_status']) or '미조사'}</div></div>
      {competitor_line}
      <div><div class="k">예타여부</div><div class="v">{esc(p['is_yeta']) or '불명'}</div></div>
      {evidence_html}
    </div>
  </div>
  <div class="pd-grid">
    <div class="pd-panel">
      <h4>사업 개요</h4>
      <div class="kv-grid">
        <div><div class="k">사업유형</div><div class="v">{esc(p['biz_type']) or '—'}</div></div>
        <div><div class="k">신규/기존</div><div class="v">{esc(p['new_or_existing']) or '—'}</div></div>
        <div><div class="k">주관기관</div><div class="v">{esc(p['org']) or '—'}</div></div>
        <div><div class="k">소관부처</div><div class="v">{esc(p['ministry']) or '—'}</div></div>
        <div style="grid-column:1/-1;"><div class="k">수행기관</div><div class="v">{esc(p['executor']) or '미정'}</div></div>
        <div style="grid-column:1/-1;"><div class="k">참여가능 앵커기업</div>{anchor_chip_row(p.get('anchor'), no)}</div>
      </div>
    </div>
    <div class="pd-panel">
      <h4>PwC Relationship</h4>
      <div class="kv-grid">
        <div style="grid-column:1/-1;"><div class="k" style="font-size:11px;color:var(--ink-muted);font-weight:700;">GRP/시니어파트너 · 리더</div><div class="v" style="font-weight:700;">{partner_names}</div></div>
        {partner_rows}
      </div>
    </div>
  </div>
  <div class="pd-panel" style="margin-bottom:16px;">
    <h4>Stakeholder — 이 사업, 누구를 통해 접근하나</h4>
    <div class="sh-chain">{stakeholder_chain_html(p, partner_names)}</div>
  </div>
  <div class="pd-panel">
    <h4>최신 동향 로그 <span class="readonly-note">(편집 권한이 있으면 아래에서 바로 추가 가능)</span></h4>
    <ul class="log-list" artifact-sync>
{log_html}    </ul>
    <div class="log-add-form">
      <input type="text" class="le-date-input" placeholder="예: 2026-08-20" />
      <input type="text" class="le-text-input" placeholder="새 동향 내용 입력..." />
      <input type="text" class="le-url-input" placeholder="근거 URL (선택)" />
      <button type="button" onclick="addLogEntry(this)">+ 동향 추가</button>
    </div>
  </div>
  <div class="pd-panel">
    <h4>추천 실행 액션</h4>
    {action_cards}
  </div>
</div>"""
    detail_blocks.append(block)

process_strip_html = "".join(
    f'<div class="process-step"><svg class="ps-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">{PROCESS_ICONS[i]}</svg><span class="pn">{i+1:02d}</span>{esc(s)}</div>'
    for i, s in enumerate(PROCESS_STEPS)
)

bd_process_strip_html = "".join(
    f'<div class="process-step"><svg class="ps-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">{BD_PROCESS_ICONS[i]}</svg><span class="pn">{i+1:02d}</span>{esc(s)}</div>'
    for i, s in enumerate(BD_PROCESS_STEPS)
)

MAP_LEGEND_HTML = '''
<div class="map-legend">
  <span class="ml-item"><i class="ml-swatch" style="--i:0"></i>0건</span>
  <span class="ml-item"><i class="ml-swatch" style="--i:0.35"></i>1~4건</span>
  <span class="ml-item"><i class="ml-swatch" style="--i:0.65"></i>5~7건</span>
  <span class="ml-item"><i class="ml-swatch" style="--i:1"></i>8건 이상</span>
  <span class="ml-item ml-dot"><span class="map-legend-dot"></span>선제 제안 대상 보유</span>
</div>'''

# ---- A4 reference layer: national pledge list (light, searchable, not linked to B2) ----
a4_rows = "".join(f"""
  <div class="a4-row" data-search="{esc((p['sido'] or '') + ' ' + (p['politician'] or '') + ' ' + (p['title'] or '') + ' ' + (p['keywords'] or ''))}">
    <div class="a4-top">
      <span class="a4-sido">{esc(p['sido'])}</span>
      <span class="a4-politician">{esc(p['politician'])} ({esc(p['party']) or '무소속'})</span>
      {'<span class="badge listed" style="font-size:10px;">AI/AX</span>' if p.get('is_ai') == 'Y' else ''}
    </div>
    <div class="a4-title">{esc(p['title'])}</div>
    <div class="a4-goal">{esc(p['goal'])}</div>
    {f'<div class="a4-idea">💡 {esc(p["idea"])}</div>' if p.get('idea') else ''}
  </div>""" for p in pledges)

fragment = f"""
<div class="exec-head">
  <h1>전국 AI·AX 정책사업 Pipeline</h1>
  <div class="sub">전국 AI·AX 정책사업을 공약 단계부터 추적하여, 발주 이전의 기획제안 기회를 선제적으로 포착합니다.</div>
</div>
<div class="kpi-refresh-note">최근 갱신: {esc(kpi["updated_at"])} · 신규 리서치·공고 반영 시 지표가 자동 갱신됩니다</div>
<div class="kpi-grid pledge-kpi-grid">{pledge_kpi_html}</div>

<div class="section-head"><h2>기획제안형 BD 프로세스</h2></div>
<div class="process-strip">{bd_process_strip_html}</div>

<details class="process-strip-details" style="margin-top:22px;">
  <summary>참고: 공약→예산화 프로세스(9단계) — 각 사업이 지자체 정책 파이프라인상 어느 단계를 거쳐 예산사업이 되는지</summary>
  <div class="process-strip" style="margin-top:12px;">{process_strip_html}</div>
</details>

<div class="section-head" style="margin-top:22px;"><h2>전국 권역별 사업 현황</h2></div>
<div class="map-watch-grid">
  <div class="korea-map-wrap">
    <div class="map-stage">{map_svg}<div class="map-pin-layer">{map_pin_html}</div></div>
    {MAP_LEGEND_HTML}
    <div class="map-credit">지도 데이터: <a href="https://github.com/VictorCazanave/svg-maps" target="_blank" rel="noopener">@svg-maps/south-korea</a> (CC BY 4.0) · 제주는 위치 조정 표시</div>
  </div>
  <div class="watch-panel">
    <div class="watch-panel-head">최근 포착된 사업 신호<span class="hint" style="font-weight:600;">사업 구체화·수행기관·예산·앵커기업 등 BD 관점 신호 기준 자동 선별</span></div>
    <ul class="watch-list">{recent_watch_html}</ul>
  </div>
</div>

<div class="pledge-main-grid">
  <div class="pledge-main-col">
    <div class="section-head"><h2>전체 사업 Pipeline</h2></div>
    <div class="quick-filters" id="pledgeStageFilters"></div>

    <div class="filter-panel" id="pledgeFilterPanel"></div>

    <div class="detail-summary" style="display:flex; align-items:center; justify-content:space-between; gap:12px; flex-wrap:wrap;">
      <span><strong id="pledgeCount"></strong> 개 사업이 조건에 맞습니다</span>
      <button id="pledgeHideClosedToggle" type="button" class="quick-filter" style="padding:6px 14px; font-size:13.5px;"></button>
    </div>

    <div class="pledge-table-card">
      <div class="pledge-row head">
        <span>지역</span><span>공약명</span><span>유형</span><span>진입등급</span><span>수행기관</span><span>앵커기업</span><span>최신동향</span>
      </div>
      <div id="pledgeTableBody"></div>
    </div>
  </div>
  <div class="pledge-side-col">
    {ai_insight_html}
  </div>
</div>

<div id="pledgeDetails">
{"".join(detail_blocks)}
</div>

<details class="process-strip-details" style="margin-top:36px;">
  <summary>참고: 전국 공약 원문 전수(121건) — 민선9기 시·도지사 AI 공약 · 위 트래킹 사업과 자동 연결되지 않는 별도 참고 레이어</summary>
  <div class="filter-panel" style="grid-template-columns:1fr; margin-top:12px;">
    <div class="f-item"><label>검색</label><input type="text" id="a4Search" placeholder="지역, 당선인, 공약명, 키워드 검색..." /></div>
  </div>
  <div class="a4-list" id="a4List">
{a4_rows}
  </div>
</details>
"""

with open(OUT, "w", encoding="utf-8") as f:
    f.write(fragment)

with open(OUT_SUMMARY, "w", encoding="utf-8") as f:
    json.dump(summary, f, ensure_ascii=False, separators=(",", ":"))

# ================= ANCHOR TAB (앵커기업 탐색) =================
def anchor_project_rows(proj_list):
    rows = ""
    for pr in proj_list:
        gclass = GRADE_CLASS.get(pr["entry_grade"], "grade0")
        rows += f'''<div class="anchor-proj-row" data-jump-no="{pr["no"]}">
          <span class="apr-name">{esc(pr["name"])}</span>
          <span class="apr-region">{esc(pr["region"])}</span>
          <span class="entry-grade-badge {gclass}" style="margin-left:0;">{esc(GRADE_SHORT.get(pr["entry_grade"], pr["entry_grade"]))}</span>
        </div>'''
    return rows


anchor_cards = ""
for i, a in enumerate(anchors):
    acc = a.get("account")
    acc_html = ""
    if acc:
        field_rows = "".join(
            f'<div><div class="k" style="font-size:11px;color:var(--ink-muted);font-weight:700;">{esc(k)}</div><div class="v" style="font-weight:700;">{esc(v)}</div></div>'
            for k, v in acc["fields"].items()
        )
        acc_html = f'''<div class="anchor-acc-block">
          <div class="anchor-acc-badge">PwC 계정 매핑 확인됨 · {esc(acc["display_name"])}</div>
          <div class="kv-grid" style="margin-top:8px;">{field_rows}</div>
        </div>'''
    else:
        acc_html = '<div class="anchor-acc-block anchor-acc-none">PwC 계정 매핑 미확인 — 신규 접촉 대상</div>'

    anchor_cards += f'''
<div class="anchor-card" id="anc-{i}" data-name="{esc(a['name'])}">
  <div class="anchor-card-head">
    <span class="ac-initial-lg">{esc(a['name'][0])}</span>
    <div>
      <h3>{esc(a['name'])}</h3>
      <div class="anchor-meta">관련 기회 {a['project_count']}건 · {esc(', '.join(a['regions']))}</div>
    </div>
  </div>
  {acc_html}
  <div class="anchor-proj-list">
    <div class="anchor-proj-head">관련 트래킹 사업</div>
    {anchor_project_rows(a['projects'])}
  </div>
</div>'''

matched_pct = round(matched_anchor_count / len(anchors) * 100) if anchors else 0
anchor_fragment = f'''
<div class="exec-head">
  <h1>앵커기업 탐색</h1>
  <div class="sub">공약·사업 파이프라인에서 언급된 앵커기업 {len(anchors)}개사 · PwC 기존 계정 매핑 {matched_anchor_count}개사({matched_pct}%)</div>
</div>
<div class="filter-panel" style="grid-template-columns:1fr;">
  <div class="f-item"><label>기업명 검색</label><input type="text" id="anchorSearch" placeholder="앵커기업명 검색..." /></div>
</div>
<div class="anchor-grid" id="anchorGrid">
{anchor_cards}
</div>
'''
with open(OUTPUT_DIR / "anchor_fragment.html", "w", encoding="utf-8") as f:
    f.write(anchor_fragment)

# ================= 선제 진입 기회 TAB (구 "우선순위 분석") =================
# 이 페이지는 "어느 산업/지역이 유망한가"를 보여주는 통계 페이지가 아니라, "지금 PwC가
# 먼저 움직일 수 있는 사업이 뭔가"를 보여주는 실행형 리스트다. 그래서 경쟁단계(이미
# 경쟁사 확정)는 기본적으로 이 페이지 대상에서 제외하고, 막대그래프 대신 사업 단위
# 카드 + 아직 미정인 요소 + Next Action을 보여준다. 모든 수치는 실제 DB 필드에서만
# 파생한다 — 유망도/구체화점수/진입가능성% 같은 임의 점수는 절대 만들지 않는다.
# 이 페이지가 다루는 모집단은 경쟁단계(이미 경쟁사 확정)를 뺀 84건뿐이다. KPI 숫자를
# 전체 109건 기준으로 세면 "공고 예정·임박 11건" 눌렀는데 리스트엔 9건만 뜨는 식으로
# 숫자가 안 맞는다 — 반드시 opportunity_projects(=리스트에 실제 보이는 모집단) 기준으로
# 세서, 어떤 KPI를 눌러도 "그 숫자만큼 카드가 보인다"가 항상 성립하게 한다.
opportunity_projects = [p for p in projects if p["entry_grade"] != "3순위: 경쟁열위"]
opportunity_projects.sort(key=lambda p: 0 if p["entry_grade"] == "1순위: 선제 제안 대상" else 1)

OPP_KPI_DEFS = [
    ("opp_ready", "선제 진입 가능 사업", lambda p: p["entry_grade"] == "1순위: 선제 제안 대상", "emph"),
    ("opp_pre_concrete", "사업 구체화 전", lambda p: p.get("stage") == "미정", ""),
    ("opp_exec_undecided", "수행기관 미확정", lambda p: not p.get("executor") or p.get("executor") == "미정", ""),
    ("opp_anchor", "앵커기업 후보 존재", lambda p: bool(p.get("anchor")), ""),
    ("opp_budget_undecided", "예산 미확정", lambda p: not p.get("budget_text"), ""),
    ("opp_filing_soon", "공고 예정·임박", lambda p: bool(p.get("filing_estimate")), ""),
]
opp_kpi_html = "".join(f'''
    <div class="kpi {emph}" data-opp-filter="{key}">
      <div class="label">{esc(label)}</div>
      <div class="value tabular">{sum(1 for p in opportunity_projects if fn(p))}<span class="unit">건</span></div>
    </div>''' for key, label, fn, emph in OPP_KPI_DEFS)


def undetermined_items(p):
    missing = []
    if not p.get("executor") or p.get("executor") == "미정":
        missing.append("수행기관")
    if not p.get("anchor"):
        missing.append("앵커기업")
    if not p.get("budget_text"):
        missing.append("예산")
    if p.get("stage") == "미정":
        missing.append("세부사업")
    return missing


def next_action_label(grade):
    if grade == "3순위: 경쟁열위":
        return "후속·연차 사업 모니터링"
    current = BD_STEP_CURRENT.get(grade, 1)
    return BD_PROCESS_STEPS[current] if current < len(BD_PROCESS_STEPS) else "본사업·PMO 수주"


def opportunity_card(p, extra=False):
    grade = p["entry_grade"]
    gclass = GRADE_CLASS.get(grade, "grade0")
    tags_html = "".join(f'<span class="reason-tag">{esc(t)}</span>' for t in entry_reason_tags(p))
    missing = undetermined_items(p)
    missing_html = f'미정: {esc("·".join(missing))}' if missing else '주요 정보 확인됨'
    extra_cls = " opp-extra" if extra else ""
    return f'''
<div class="opp-card{extra_cls}" data-jump-no="{p['no']}" data-executor-undecided="{1 if (not p.get('executor') or p.get('executor')=='미정') else 0}" data-anchor="{1 if p.get('anchor') else 0}" data-budget-undecided="{1 if not p.get('budget_text') else 0}" data-stage-undecided="{1 if p.get('stage')=='미정' else 0}" data-filing-soon="{1 if p.get('filing_estimate') else 0}" data-grade="{gclass}">
  <div class="opp-card-top">
    <span class="entry-grade-badge {gclass}" style="margin-left:0;">{esc(GRADE_SHORT.get(grade, grade))}</span>
    <span class="opp-region">{esc(p['region'])}</span>
  </div>
  <div class="opp-name">{esc(p['name'])}</div>
  <div class="opp-tags">{tags_html}</div>
  <div class="opp-missing">{missing_html}</div>
  <div class="opp-foot">
    <span class="opp-filing">{esc(p.get('filing_estimate') or '공고시점 미정')}</span>
    <span class="opp-next">→ {esc(next_action_label(grade))}</span>
  </div>
</div>'''


# 첫 화면에는 대표 항목(선제 제안 대상 우선 정렬 기준 상위 N건)만 노출 — 나머지는
# "전체 보기" 클릭 시 펼침. 발표 화면에서 카드가 한꺼번에 다 쏟아지지 않도록.
OPP_INITIAL_VISIBLE = 8
opportunity_cards_html = "".join(
    opportunity_card(p, extra=(i >= OPP_INITIAL_VISIBLE)) for i, p in enumerate(opportunity_projects)
) or '<div class="empty-state" style="padding:24px;">조건에 맞는 사업이 없습니다.</div>'
opp_extra_count = max(0, len(opportunity_projects) - OPP_INITIAL_VISIBLE)
opp_show_all_html = (
    f'<button type="button" class="opp-show-all-btn" id="oppShowAllBtn" data-extra-count="{opp_extra_count}">'
    f'전체 {len(opportunity_projects)}건 보기 (+{opp_extra_count}건)</button>'
    if opp_extra_count > 0 else ''
)

# ---- 예상 공고 시점 타임라인 (연도 단위 — 월 단위 정밀도는 원본 데이터에 없음) ----
def filing_bucket(estimate_text):
    m = re.search(r'(20\d{2})', estimate_text or "")
    if not m:
        return "시점 미정"
    year = int(m.group(1))
    current_year = datetime.now().year
    if year <= current_year:
        return f"{year}년 예정"
    if year == current_year + 1:
        return f"{year}년 예정"
    return "2028년 이후" if year >= 2028 else f"{year}년 예정"

timeline_buckets = defaultdict(list)
for p in projects:
    if p.get("filing_estimate"):
        timeline_buckets[filing_bucket(p["filing_estimate"])].append(p)
BUCKET_ORDER = sorted(timeline_buckets.keys(), key=lambda b: (0, b) if "미정" not in b else (1, b))

timeline_html = "".join(f'''
<div class="timeline-bucket">
  <div class="timeline-bucket-head">{esc(bucket)}<span class="hint">{len(timeline_buckets[bucket])}건</span></div>
  <div class="timeline-bucket-cards">{"".join(opportunity_card(p) for p in timeline_buckets[bucket])}</div>
</div>''' for bucket in BUCKET_ORDER) or '<div class="empty-state" style="padding:24px;">예상 공고시점이 확인된 사업이 없습니다.</div>'

# ---- 대표 Opportunity 3건 (구 "BD 기회 요약") — KPI 숫자를 문장으로 다시 요약하는
# 대신, 선제 제안 대상 우선순위 상위 사업을 그대로 보여준다. 전부 opportunity_projects
# 발췌이며, 클릭하면 사업상세로 이동.
top_opportunities = opportunity_projects[:3]
top_opp_html = "".join(f'''
<div class="top-opp-item" data-jump-no="{p['no']}">
  <div class="top-opp-top">
    <span class="entry-grade-badge {GRADE_CLASS.get(p['entry_grade'],'grade0')}" style="margin-left:0;">{esc(GRADE_SHORT.get(p['entry_grade'], p['entry_grade']))}</span>
    <span class="opp-region">{esc(p['region'])}</span>
  </div>
  <div class="top-opp-name">{esc(p['name'])}</div>
  <div class="top-opp-next">→ {esc(next_action_label(p['entry_grade']))}</div>
</div>''' for p in top_opportunities) or '<div class="empty-state" style="padding:16px;">표시할 사업이 없습니다.</div>'

top_opp_panel_html = f'''
<div class="ai-insight-panel" id="topOppPanel">
  <div class="aip-head">대표 Opportunity</div>
  <div class="top-opp-list">{top_opp_html}</div>
</div>'''

intel_fragment = f'''
<div class="exec-head">
  <h1>선제 진입 기회</h1>
  <div class="sub">사업구조·수행기관·앵커기업 등이 확정되기 전, 기획제안이 가능한 사업을 선별했습니다.</div>
</div>

<div class="kpi-grid pledge-kpi-grid" id="oppKpiGrid">{opp_kpi_html}</div>

<div class="opp-main-grid">
  <div class="opp-main-col">
    <div class="section-head"><h2>선제 진입 기회 리스트</h2><div class="hint" id="oppCount"></div></div>
    <div class="opp-card-grid" id="oppCardGrid">{opportunity_cards_html}</div>
    {opp_show_all_html}

    <div class="section-head" style="margin-top:30px;"><h2>예상 사업화·공고 시점</h2><div class="hint">선제 접촉 및 기획제안 시점 판단</div></div>
    <div id="oppTimeline">{timeline_html}</div>
  </div>
  <div class="pledge-side-col">
    {top_opp_panel_html}
  </div>
</div>
'''
with open(OUTPUT_DIR / "intel_fragment.html", "w", encoding="utf-8") as f:
    f.write(intel_fragment)


import os
print("pledge fragment KB:", os.path.getsize(OUT) / 1024)
print("anchor fragment KB:", os.path.getsize(OUTPUT_DIR / "anchor_fragment.html") / 1024)
print("intel fragment KB:", os.path.getsize(OUTPUT_DIR / "intel_fragment.html") / 1024)
print("summary KB:", os.path.getsize(OUT_SUMMARY) / 1024)
print("projects:", len(projects), "pledges:", len(pledges), "anchors:", len(anchors))
