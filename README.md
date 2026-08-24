# 지역 AX 제안기획형 BD Hub

`/home/jpark790sss/dashboard` — 실제 개발 폴더입니다. 예전에는 Claude 세션의 임시 스크래치패드에서 작업했지만(세션 종료 시 사라짐), 이제 이 폴더가 소스 오브 트루스이고 그대로 실행됩니다.

## 실행 방법

```bash
cd backend/pipeline
../../.venv/bin/python3 run_all.py        # 전체 파이프라인 실행 → frontend/dashboard_v2.html 생성
../../.venv/bin/python3 run_all.py --skip-pool   # Pool 엑셀/saturn.db 접근 안 될 때
```

최초 1회는 가상환경 세팅이 필요합니다: `python3 -m venv --without-pip .venv && .venv/bin/python3 <(curl -s https://bootstrap.pypa.io/get-pip.py) && .venv/bin/pip install openpyxl`

## 아키텍처 요약

**프론트/백엔드가 분리된 정식 웹앱이 아닙니다.** 서버, DB, API, 인증이 없습니다.

- **프론트 (`frontend/`)**: 단일 정적 HTML 파일. CSS/JS/데이터(JSON)가 전부 그 안에 인라인으로 들어있습니다. 브라우저에서 열리면 그 안의 JS가 인라인 JSON을 읽어서 화면을 렌더링합니다.
- **백엔드 (`backend/`)**: 상시 구동되는 서버가 아니라, **엑셀 원본 → JSON → HTML**을 만드는 오프라인 파이썬 파이프라인입니다. 데이터가 바뀌면 사람이 다시 실행해서 `frontend/`의 최종 HTML을 재생성합니다.

## 프론트 (`frontend/`)

| 파일 | 설명 |
|---|---|
| `dashboard_template.html` | 소스 템플릿. `__DATA_JSON__`, `__PLEDGE_HTML__` 같은 플레이스홀더에 백엔드 파이프라인이 데이터를 끼워넣습니다. **수정은 이 파일에서.** |
| `dashboard_v2.html` | 템플릿 + 데이터를 합쳐서 만든 최종 결과물. 지금 실제로 발행되어 있는 페이지와 동일합니다. |

## 백엔드 (`backend/`)

### `pipeline/` — 공약·사업 트래커

- **`paths.py`** — 모든 스크립트가 공유하는 경로 설정. `RAW_DIR`/`DB_DIR`(OneDrive 원본 엑셀·DB, env var로 override 가능), `INPUT_DIR`(`backend/inputs/`), `OUTPUT_DIR`(`backend/output/`, 파생 데이터 전용·git 미추적), `FRONTEND_DIR`을 정의합니다.
- **`run_all.py`** — 아래 1~7단계를 순서대로 실행하는 오케스트레이터. `--skip-pool`로 pool_pipeline 단계 생략 가능.
- 1. **`extract_pledges.py`** — 원본 엑셀(민선9기 공약 및 과제분석)을 읽어 프로젝트/공약/PwC계정 데이터를 JSON으로 추출·정제(예산 텍스트 정규식 추출, 진입등급 계산 등). `backend/inputs/competitor_findings.json`(리서치 결과)을 조인합니다.
- 2. **`build_anchor_data.py`** — 앵커기업별로 관련 사업을 집계하고 PwC 계정과 매칭.
- 3. **`kpi_snapshot.py`** — 현재 KPI 집계를 이전 스냅샷(`backend/inputs/kpi_snapshot.json`)과 비교해 증감(delta) 계산 후 baseline 갱신.
- 4. **`korea_map.py`** — 대한민국 지도 SVG + 지역별 핀 좌표 생성 (`backend/inputs/korea_paths.json` 사용, CC BY 4.0 외부 소스).
- 5. **`generate_pledge_html.py`** — 위 결과들을 조합해 공약트래커 탭/앵커기업 탭/기회인텔리전스 탭의 HTML 조각을 생성.
- 6. **`build_font_css.py`** — Pretendard 폰트(`backend/inputs/fonts/`)를 base64로 인라인 임베드 (CSP 제약상 외부 폰트 링크 불가).
- 7. **`build_dashboard.py`** — 위에서 생성된 모든 조각을 `dashboard_template.html`에 끼워넣어 `frontend/dashboard_v2.html`을 만듭니다.

### `pool_pipeline/` — 충남 AX 기업 Pool

- **`extract_dashboard_data2.py`** — 충남 산업단지 기업 Pool 엑셀 + `db/saturn.db`(DART/NPS 매칭 캐시)를 조합해 `pool_data.json`(경영진 대시보드 탭 데이터)을 생성. DART/NPS 원본 수집·매칭 스크립트(팩토리온 크롤링, DART corpCode 대조, NPS 사업장조회 등)는 별도의 탐색적 스크립트 묶음이라 포함하지 않았습니다.

### `inputs/` — 파이프라인 입력값 (git 추적 대상)

- `competitor_findings.json` — 109개 사업에 대한 경쟁현황/공고상태 리서치 결과 (웹서치 기반 추정치, 사람 검증 안 됨 — TODO 참고)
- `korea_paths.json` — 지도 SVG path 원본 데이터 (외부 소스, CC BY 4.0)
- `kpi_snapshot.json` — KPI 증감 계산용 이전 스냅샷 baseline (매 실행마다 갱신됨)
- `fonts/` — Pretendard-Regular/Bold.woff2

### `output/` — 파이프라인 산출물 (git 미추적, 재실행 때마다 재생성)

`pledges_data.json`, `anchor_summary.json`, `kpi_snapshot_result.json`, `pool_data.json`, `pledge_fragment.html`, `anchor_fragment.html`, `intel_fragment.html`, `font_face.css` 등 — 손으로 편집할 필요 없는 중간 산출물.

## 원본 데이터 위치

원본 엑셀/DB는 이 프로젝트 폴더에 포함하지 않고 OneDrive를 그대로 참조합니다 (PwC 고객 데이터라 git에 넣지 않음):

- `.../개인폴더/한글 saturn 개발/data/raw/00. 민선9기 공약 및 과제분석 종합_개발용.xlsx`
- `.../개인폴더/한글 saturn 개발/data/raw/(260812)충남산업단지기업_Pool_v0.1_개발용.xlsx`
- `.../개인폴더/한글 saturn 개발/db/saturn.db`

경로가 바뀌면 `DASHBOARD_RAW_DIR`, `DASHBOARD_DB_DIR` 환경변수로 override.

## 알려진 한계

- 최신동향 로그 편집(artifact-sync)은 Claude Artifact 플랫폼 자체 기능에 의존하고 있어, 이 코드만으로는 재현되지 않습니다.

## 관련 문서

지난 대화에서 정리한 1차/2차 마일스톤 TODO 리스트(디자인·데이터정제·아키텍처 정립·컨택필드 등)는 별도 보고 자료로 전달드린 상태입니다.
