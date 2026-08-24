"""Generates a real-shape SVG map of South Korea's 17 provinces/metros,
using path data sourced from @svg-maps/south-korea (CC-BY-4.0, Victor Cazanave).

The map itself renders as plain (shadow-lifted) shapes only — no SVG text —
because SVG text scales with the map's rendered width, which made labels
balloon when the map was widened. Region labels/counts are instead rendered
as fixed-size HTML "pin" markers, absolutely positioned over the map by
percentage, so their size never depends on the map's width."""
import json

from paths import INPUT_DIR

PATHS_FILE = INPUT_DIR / "korea_paths.json"

ID_TO_KOREAN = {
    "busan": "부산", "daegu": "대구", "daejeon": "대전", "gangwon": "강원",
    "gwangju": "광주", "gyeonggi": "경기", "incheon": "인천", "jeju": "제주",
    "north-chungcheong": "충북", "north-gyeongsang": "경북", "north-jeolla": "전북",
    "sejong": "세종", "seoul": "서울", "south-chungcheong": "충남",
    "south-gyeongsang": "경남", "south-jeolla": "전남", "ulsan": "울산",
}

with open(PATHS_FILE, encoding="utf-8") as f:
    _PATH_DATA = json.load(f)

# Jeju sits far south of the mainland in the source data, leaving a large empty
# gap. Relocate it as a compact inset just below the mainland's SE corner and
# trim the viewBox height to match, so the map doesn't waste vertical space.
JEJU_OFFSET = (178, -53)
VIEWBOX_W, VIEWBOX_H = 524, 600
VIEWBOX = f"0 0 {VIEWBOX_W} {VIEWBOX_H}"

# manual label nudges for elongated/irregular provinces where the bbox center
# would land outside (or awkwardly on) the actual shape
LABEL_NUDGE = {
    "강원": (10, -15),
    "경북": (-10, 20),
    "전남": (10, 10),
    "충남": (-15, 0),
    # 서울 is a small enclave inside 경기's much larger territory, so their raw
    # centroids sit almost on top of each other. Nudge only the (tiny) 서울 pin
    # up-left into open space; 경기's own centroid is left untouched so it
    # doesn't drift outside its own territory.
    "서울": (-12, -16),
}

# some source rows tag a project with a combined region label (e.g. a
# 5극3특 특별연합 pairing); split so counts land on every real map region.
REGION_ALIASES = {
    "전남·광주": ["전남", "광주"],
}


def expand_region(raw_region):
    if not raw_region:
        return []
    if raw_region in REGION_ALIASES:
        return REGION_ALIASES[raw_region]
    return [raw_region]


def build_svg(counts_by_region):
    """counts_by_region: dict Korean-region-name -> {'total': N, 'grade1': N}
    Returns (svg_html, pins) — pins is a list of dicts for the HTML overlay:
    {name, left_pct, top_pct, total, grade1}"""
    max_total = max((v.get('total', 0) for v in counts_by_region.values()), default=1) or 1
    parts = []
    pins = []
    for region_id, info in _PATH_DATA.items():
        name = ID_TO_KOREAN.get(region_id)
        if not name:
            continue
        d = info["d"]
        cx, cy = info["cx"], info["cy"]
        nx, ny = LABEL_NUDGE.get(name, (0, 0))
        lx, ly = cx + nx, cy + ny
        if name == "제주":
            lx, ly = lx + JEJU_OFFSET[0], ly + JEJU_OFFSET[1]
            group_attrs = f' transform="translate({JEJU_OFFSET[0]},{JEJU_OFFSET[1]})" class="map-tile map-tile-inset"'
        else:
            group_attrs = ' class="map-tile"'

        counts = counts_by_region.get(name, {})
        total = counts.get('total', 0)
        grade1 = counts.get('grade1', 0)
        # power curve (>1) keeps most regions near-white and reserves visible
        # blue for the genuinely high-count few — white base, color only on
        # what matters, instead of a blue wash across the whole map
        intensity = (total / max_total) ** 4 if total and max_total else 0

        parts.append(f'''
    <g{group_attrs} data-region="{name}" tabindex="0" role="button" aria-label="{name}: {total}건">
      <path d="{d}" class="map-rect" style="--intensity:{intensity:.2f};" />
    </g>''')
        pins.append({
            "name": name, "total": total, "grade1": grade1, "intensity": intensity,
            "left_pct": round(lx / VIEWBOX_W * 100, 2), "top_pct": round(ly / VIEWBOX_H * 100, 2),
        })

    svg = f'''<svg viewBox="{VIEWBOX}" class="korea-map-svg" role="img" aria-label="대한민국 권역별 사업 현황 지도">
{"".join(parts)}
</svg>'''
    return svg, pins


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    test_counts = {"충남": {"total": 9, "grade1": 3}, "서울": {"total": 6, "grade1": 1}}
    svg, pins = build_svg(test_counts)
    print("length:", len(svg), "pins:", len(pins))
    print(pins[:3])
