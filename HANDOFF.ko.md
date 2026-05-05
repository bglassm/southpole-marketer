# Southpole 인수인계 가이드 (한국어)

## Southpole이 하는 일

Southpole은 로컬 환경에서 TikTok 리서치를 실행하고, 크리에이터별 DM 초안을 만드는 도구입니다.

운영자는 UI에서 아래 두 가지 버튼만 사용하면 됩니다.

1. `Run Collect + Aggregate`
2. `Generate DM Drafts`

실행할 때마다 `outputs/runs/` 아래에 새로운 실행 폴더가 생성됩니다.

## 아직 하지 않는 일

- TikTok DM 자동 발송은 지원하지 않습니다.
- Docker Desktop 자동 설치는 지원하지 않습니다.

현재 단계는 “수집/집계 + DM 초안 생성/검토”까지입니다.

## 사용 전 준비 (필수)

1. Docker Desktop 설치
2. 프로젝트 루트에 `.env` 파일 준비
3. `.env` 필수 값 입력
   - `APIFY_TOKEN`
   - `N8N_ENCRYPTION_KEY`
   - `OPENAI_API_KEY`

선택 값:

- `OPENAI_MODEL`
- `TZ`

## 시작 방법 (비개발자용)

파일을 더블클릭하세요.

- macOS: `start.command`
- Windows: `start.bat`

시작 파일이 자동으로 하는 일:

1. Docker 설치 여부 확인
2. Docker가 없으면 다운로드 페이지 자동 오픈
3. Docker는 있지만 실행 중이 아니면 Docker Desktop 실행 시도 + 대기
4. Southpole 스택 시작 + 헬스 체크 대기
5. 브라우저에서 Operator UI 자동 오픈
   - `http://localhost:8080/ui`

## UI 사용 방법

접속 주소: `http://localhost:8080/ui`

### 1) Run Collect + Aggregate

입력:

- `keywords` (쉼표 또는 줄바꿈으로 구분)
- `days`
- (선택) `run label`

실행 결과:

- 새로운 run 폴더 생성
- `report.html`, `creators.csv`, 요약 파일 생성

### 2) Generate DM Drafts

입력:

- run 폴더 (기본: 최신 run)
- `language_mode` (`ko`, `en`, `auto`)
- (선택) `brand_context`
- `limit`

실행 결과:

- 해당 run 폴더 아래 DM 결과 생성
  - `dm/dm_drafts.csv`
  - `dm/dm_drafts.json`
  - `dm/dm_review.html`
  - `dm/messages/*.txt`

## 결과물 저장 위치

모든 결과는 로컬에 저장됩니다.

- `outputs/runs/<timestamp>_<slug>/`

주요 파일:

- `report.html`
- `summary.json`
- `keyword_totals.csv`
- `creators.csv`
- `daily_metrics.csv`
- `raw_events.csv`
- `raw_events.jsonl`
- `southpole_run_<timestamp>.xlsx`
- `dm/` (DM 초안 생성 후)

## 종료 방법

파일을 더블클릭하세요.

- macOS: `stop.command`
- Windows: `stop.bat`

Docker 스택이 정상 종료됩니다.

## 문제 해결

### Docker가 설치되지 않음

- 시작 파일이 Docker Desktop 다운로드 페이지를 열어줍니다.
- 설치 후 시작 파일을 다시 실행하세요.

### Docker가 설치되어 있지만 실행 중이 아님

- 시작 파일이 Docker Desktop 실행을 시도합니다.
- 일정 시간 안에 준비되지 않으면 Docker Desktop을 직접 실행한 뒤 다시 시도하세요.

### UI가 자동으로 열리지 않음

1. 브라우저에서 직접 접속: `http://localhost:8080/ui`
2. 그래도 안 되면 시작 파일 재실행
3. 필요 시 기술 담당자가 로그 확인
   - `docker compose logs --tail=200`

### 스택 시작 실패

다음을 확인하세요.

1. Docker Desktop 정상 실행 상태
2. `.env` 존재 여부 및 필수 키 입력 여부
3. `5678`, `8080` 포트 충돌 여부

## 런처 동작 참고

Docker 설치는 **자동 설치가 아니라**
“설치 여부 감지 + 다운로드 페이지 열기” 방식입니다.

## 기술 담당자 확인용 (선택)

- 경로 이식성 검사:
  - `bash scripts/check-portability.sh`
- 목 실행 검증:
  - `bash scripts/verify.sh`
