import sys
sys.stdout.reconfigure(encoding='utf-8')

from paths import FRONTEND_DIR, OUTPUT_DIR

with open(FRONTEND_DIR / "dashboard_template.html", "r", encoding="utf-8") as f:
    template = f.read()
with open(OUTPUT_DIR / "pool_data.json", "r", encoding="utf-8") as f:
    data_json = f.read()
with open(OUTPUT_DIR / "pledge_fragment.html", "r", encoding="utf-8") as f:
    pledge_html = f.read()
with open(OUTPUT_DIR / "pledge_fragment_summary.json", "r", encoding="utf-8") as f:
    pledge_json = f.read()
with open(OUTPUT_DIR / "font_face.css", "r", encoding="utf-8") as f:
    font_css = f.read()
with open(OUTPUT_DIR / "anchor_fragment.html", "r", encoding="utf-8") as f:
    anchor_html = f.read()
with open(OUTPUT_DIR / "intel_fragment.html", "r", encoding="utf-8") as f:
    intel_html = f.read()
with open(OUTPUT_DIR / "anchor_summary.json", "r", encoding="utf-8") as f:
    anchor_json = f.read()

out = template.replace("__FONT_FACE_CSS__", font_css)
out = out.replace("__DATA_JSON__", data_json)
out = out.replace("__PLEDGE_HTML__", pledge_html)
out = out.replace("__PLEDGE_JSON__", pledge_json)
out = out.replace("__ANCHOR_HTML__", anchor_html)
out = out.replace("__ANCHOR_JSON__", anchor_json)
out = out.replace("__INTEL_HTML__", intel_html)

out_path = FRONTEND_DIR / "dashboard_v2.html"
with open(out_path, "w", encoding="utf-8") as f:
    f.write(out)

import os
print("size MB:", os.path.getsize(out_path) / 1024 / 1024)
print("saved:", out_path)
