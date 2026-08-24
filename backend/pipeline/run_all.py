"""Runs the full pipeline end to end, in the order documented in README.md.

Usage: python run_all.py [--skip-pool]
  --skip-pool   skip the pool_pipeline stage (Pool 엑셀/saturn.db 접근 불가할 때)
"""
import subprocess
import sys
from pathlib import Path

PIPELINE_DIR = Path(__file__).resolve().parent
POOL_DIR = PIPELINE_DIR.parent / "pool_pipeline"

STEPS = [
    ("공약 데이터 추출", PIPELINE_DIR / "extract_pledges.py"),
    ("앵커기업 집계", PIPELINE_DIR / "build_anchor_data.py"),
    ("KPI 스냅샷", PIPELINE_DIR / "kpi_snapshot.py"),
    ("Pool 데이터 추출 (충남 AX 기업)", POOL_DIR / "extract_dashboard_data2.py"),
    ("공약트래커/앵커/기회인텔리전스 HTML 생성", PIPELINE_DIR / "generate_pledge_html.py"),
    ("폰트 CSS 인라인 빌드", PIPELINE_DIR / "build_font_css.py"),
    ("최종 대시보드 조립", PIPELINE_DIR / "build_dashboard.py"),
]


def main():
    skip_pool = "--skip-pool" in sys.argv
    for label, script in STEPS:
        if skip_pool and script.parent == POOL_DIR:
            print(f"[skip] {label}")
            continue
        print(f"\n=== {label} ({script.name}) ===", flush=True)
        result = subprocess.run([sys.executable, str(script)], cwd=str(script.parent))
        if result.returncode != 0:
            print(f"\n[중단] '{label}' 단계에서 실패했습니다 ({script}).")
            sys.exit(result.returncode)
    print("\n완료: frontend/dashboard_v2.html 생성됨.")


if __name__ == "__main__":
    main()
