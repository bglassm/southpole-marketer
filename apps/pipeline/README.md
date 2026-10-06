# Southpole Pipeline

TikTok 게시물을 수집·정규화·집계하고 로컬 보고서를 만드는 Python 서비스입니다. FastAPI 운영 화면과 CLI가 같은 처리 함수를 사용합니다. 댓글 분석·크리에이터 점수·아웃리치 상태 동기화·OpenAI DM 초안 생성은 별도로 실행하는 단계입니다. **`/run` 한 번으로 이 모든 단계가 실행되지는 않습니다.**

현재 동작의 근거는 [runner.py](src/southpole_pipeline/runner.py), [API](src/southpole_pipeline/api.py), [운영 UI](src/southpole_pipeline/operator_ui.py), [CLI](src/southpole_pipeline/cli.py)입니다. 전체 구성은 [아키텍처](../../docs/architecture.md), 파일별 스키마는 [출력 파일](../../docs/output-files.md)을 참고하세요.

## 실행

아래 명령은 저장소 루트 기준이며 실행 결과를 주장하는 기록이 아닌 재현 명령입니다. Docker 구성은 Python 3.11을 사용합니다.

```bash
# 전체 스택: 사전에 루트 실행 안내에 따라 .env 설정
bash scripts/up.sh
```

기본 운영 화면은 `http://localhost:8080/ui`, API 문서는 `http://localhost:8080/docs`입니다. n8n 없이 서비스만 로컬에서 실행할 수도 있습니다.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r apps/pipeline/requirements.txt
export PYTHONPATH=apps/pipeline/src
export OUTPUT_ROOT=./outputs/runs
export OPERATOR_STATE_ROOT=./outputs/operator_state
python -m uvicorn southpole_pipeline.api:app --host 127.0.0.1 --port 8080
```

Python은 `.env`를 자동으로 읽지 않습니다. 로컬 실행에는 필요한 변수를 프로세스 환경에 설정하세요. 루트 Compose의 `.env.example`에 있는 출력 경로는 컨테이너 경로이므로 로컬 실행에는 위 상대 경로를 사용합니다. 비밀값은 소스나 명령 예제에 넣지 않습니다.

## 외부 수집 없는 기본 실행

가상환경을 활성화하고 `PYTHONPATH`를 설정한 저장소 루트에서:

```bash
python -m southpole_pipeline.cli run \
  --keywords "kbeauty,oliveyoung" --days 365 --slug mock \
  --mock-file apps/pipeline/fixtures/mock_apify_items.json
```

이 명령은 Apify와 OpenAI를 호출하지 않습니다. stdout의 JSON에서 `runId`, `source.provider`, `counts`, `files`를 확인합니다. 동봉 fixture의 게시 날짜는 2026년 3월 8~11일로 고정되어 있어 실행 날짜와 `days`에 따라 정규화 결과가 0건일 수 있습니다. 0건 완료를 실수집 성공으로 해석하지 마세요.

컨테이너에서는 동일한 fixture가 `/app/fixtures/mock_apify_items.json`에 있습니다.

```bash
docker compose run --rm pipeline python -m southpole_pipeline.cli run \
  --keywords "kbeauty,oliveyoung" --days 365 --slug mock \
  --mock-file /app/fixtures/mock_apify_items.json

bash scripts/check-portability.sh
bash scripts/verify.sh
```

`verify.sh`는 `days=7`의 mock 실행과 필수 파일 존재를 확인합니다. 비어 있지 않은 데이터, 실 Apify 수집, OpenAI 생성, 댓글 단계나 UI 전체를 검증하는 스크립트는 아닙니다. UI의 수집 버튼에는 mock 선택이 없으므로 외부 호출 없이 확인하려면 먼저 CLI/API의 `mock_file`로 실행 폴더를 만든 뒤 UI에서 결과를 조회합니다.

## 단계와 API

POST는 JSON을 받으며 처리 완료 후 결과를 반환합니다. 비동기 작업 큐·진행률 조회 API는 없습니다. 정확한 요청 필드와 유효 범위는 `/docs` 및 [api.py](src/southpole_pipeline/api.py)를 기준으로 합니다.

| 엔드포인트 | 동작과 입력 |
| --- | --- |
| `GET /health` | 프로세스 응답 확인. 외부 서비스 연결 검사가 아님 |
| `GET /ui`, `GET /` | 운영 화면, 운영 화면으로 리다이렉트 |
| `GET /runs` | 출력 루트의 실행 폴더와 요약 목록 |
| `GET /runs/{run_id}/creators?limit=12` | 해당 `creators.csv` 미리보기. `limit` 1~200 |
| `GET /artifacts/...` | 생성 파일 제공. 기본 경로 예: `/artifacts/runs/<run_id>/report.html` |
| `POST /run` | 필수 `keywords`(문자열/배열), `days` 기본 7·1~365, 선택 `slug`, `source`, `mock_file`. 수집→정규화→집계→CSV/JSONL/XLSX/HTML |
| `POST /dm/generate` | `run_dir`, `language_mode`(`ko`/`en`/`auto`), `brand_context`, `limit` 기본 10. `creators.csv`에서 OpenAI 초안 생성 |
| `POST /comments/targets` | `run_dir`, `max_targets` 기본 20, `requested_comment_limit` 기본 50, 선택 사유·담당자. 조회수 상위 게시물 대상 파일 생성 |
| `POST /comments/collect` | `run_dir`, 선택 `targets_file`, `mock_file`. 대상 파일을 읽어 댓글 수집·정규화 |
| `POST /comments/analyze` | `run_dir`, 선택 `limit`, `analysis_model`. 댓글별 인사이트·집계·토픽·HTML |
| `POST /scoring/creators` | `run_dir`. 정규화 프로필과 사용 가능한 댓글 신호로 규칙 기반 점수 계산 |
| `POST /outreach/sync` | `run_dir`, `campaign_id`, `owner`, `status`, `notes`. 후보 CSV와 실행 간 등록부/이력 갱신 |

`run_dir`를 생략하면 이름순으로 마지막 출력 디렉터리를 사용합니다. 여러 실행을 다룰 때는 `/run`이 반환한 `runId`를 명시하세요. 이후 단계는 동일 실행의 파일을 갱신하며, 이전 결과를 별도 버전으로 보존하는 작업 저장소는 아닙니다.

CLI에도 동일한 기능이 있습니다. 아래 `RUN_ID`는 앞선 실행의 실제 `runId`로 바꿉니다. 댓글 수집과 DM 명령은 자격증명 설정 시 외부 호출을 수행합니다.

```bash
python -m southpole_pipeline.cli --help
python -m southpole_pipeline.cli comments-targets --run-dir RUN_ID --max-targets 20
python -m southpole_pipeline.cli comments-collect --run-dir RUN_ID
python -m southpole_pipeline.cli comments-analyze --run-dir RUN_ID --limit 200
python -m southpole_pipeline.cli score-creators --run-dir RUN_ID
python -m southpole_pipeline.cli outreach-sync --run-dir RUN_ID --campaign-id example-campaign
python -m southpole_pipeline.cli dm --run-dir RUN_ID --language-mode ko --limit 10
```

## 설정과 외부 호출

| 설정 | 현재 사용 |
| --- | --- |
| `APIFY_TOKEN`, `APIFY_ACTOR_ID` | 실 게시물 수집. 기본 Actor는 `clockworks/tiktok-scraper` |
| `APIFY_BASE_URL`, `APIFY_RESULTS_PER_PAGE`, `APIFY_TIMEOUT_SECONDS`, `APIFY_PROXY_COUNTRY_CODE` | Apify URL·Actor 요청·타임아웃 설정 |
| `APIFY_MAX_ITEMS` | 설정에 존재하지만 현재 collector는 읽은 값을 제한에 사용하지 않음 |
| `APIFY_TIKTOK_COMMENTS_ACTOR_ID` | 실 댓글 수집 시 필수. 게시물 Actor와 별개 |
| `OPENAI_API_KEY`, `OPENAI_MODEL` | DM 초안 생성에 필요. 키 없이 성공하는 mock/fallback은 없음 |
| `OPENAI_ANALYSIS_MODEL` | 댓글 분석 모델. Python 설정 기본은 `OPENAI_MODEL`, Compose 기본값은 별도 지정됨 |
| `OUTPUT_ROOT` | 실행별 출력. 로컬 기본 `./outputs/runs`, Compose 기본 `/workspace/outputs/runs` |
| `OPERATOR_STATE_ROOT` | 실행 간 상태. 기본적으로 출력 루트의 형제 `operator_state` |
| `TZ`, `BUILD_TAG` | 날짜/실행 폴더 시간대와 요약 메타데이터 |

DM은 크리에이터 집계 정보를, 댓글 분석은 댓글 본문과 콘텐츠 식별자를 OpenAI에 전달합니다. 댓글 분석은 키 누락·요청 오류 시 휴리스틱으로 대체하지만 현재 `analysis_model` 필드는 설정 모델명을 그대로 기록합니다. 따라서 이 필드만으로 OpenAI 실행 여부를 판정할 수 없습니다. DM 생성에는 이 대체 경로가 없습니다.

## 구현 경계

- 운영 GUI는 수집·집계, 실행 선택, 크리에이터 미리보기, DM 생성과 결과 링크를 제공합니다. 댓글·점수·아웃리치 단계는 API/CLI로 실행하며 해당 조작 UI는 없습니다.
- DM 입력은 기존 `creators.csv`의 앞쪽 `limit`명입니다. 점수 순 후보나 아웃리치 등록부를 자동으로 읽지 않습니다. `dm_review.html`은 프로필/파일 열기와 복사를 제공하며 승인·반려 저장이나 메시지 전송은 구현하지 않습니다.
- 현재 n8n 워크플로는 수동 실행/웹훅 입력을 `/run`에 전달하는 래퍼입니다. 나머지 단계, 주기 스케줄, `mock_file` 전달은 포함하지 않습니다.
- 다중 SNS 수집, OAuth 계정 통합, 콘텐츠 게시·예약, 자동 DM, Clay 연동은 구현되어 있지 않습니다. 확장 방향은 [로드맵](../../docs/roadmap.md)에서 현재 기능과 분리합니다.
- API 자체 인증은 없습니다. `/artifacts`는 `OUTPUT_ROOT`의 **부모 디렉터리 전체**를 정적 파일 루트로 사용하므로 기본 구성에서는 `operator_state`도 접근 범위에 들어갑니다. Compose 포트 매핑은 loopback으로 한정되어 있지 않습니다. 신뢰할 수 있는 로컬 운영 범위에서 사용하고, 실행 데이터·자격증명을 저장소에 커밋하지 않습니다.
