import sys
sys.stdout.reconfigure(encoding='utf-8')
import base64
import os

from paths import FONT_DIR, OUTPUT_DIR

with open(FONT_DIR / "Pretendard-Regular.woff2", "rb") as f:
    reg_b64 = base64.b64encode(f.read()).decode("ascii")
with open(FONT_DIR / "Pretendard-Bold.woff2", "rb") as f:
    bold_b64 = base64.b64encode(f.read()).decode("ascii")

css = f"""@font-face {{
  font-family: 'PretendardEmbed';
  src: url(data:font/woff2;base64,{reg_b64}) format('woff2');
  font-weight: 400;
  font-style: normal;
  font-display: swap;
}}
@font-face {{
  font-family: 'PretendardEmbed';
  src: url(data:font/woff2;base64,{bold_b64}) format('woff2');
  font-weight: 700 900;
  font-style: normal;
  font-display: swap;
}}
"""

out_path = OUTPUT_DIR / "font_face.css"
with open(out_path, "w", encoding="utf-8") as f:
    f.write(css)

print("css size KB:", os.path.getsize(out_path) / 1024)
