# 실행 및 복구 가이드

대상은 공개 저장소 [bglassm/southpole-marketer](https://github.com/bglassm/southpole-marketer)입니다. 모든 명령은 저장소 루트 기준입니다.

## Docker 실행

```bash
git clone https://github.com/bglassm/southpole-marketer.git
cd southpole-marketer
cp .env.example .env
```

`.env`에 필요한 항목만 설정합니다.

| 목적 | 설정 |
| --- | --- |
| 실제 TikTok 수집 | `APIFY_TOKEN` 및 사용 가능한 `APIFY_ACTOR_ID` |
| 선택적 AI DM 초안 | `OPENAI_API_KEY`, 필요 시 `OPENAI_MODEL` |
| n8n 실행 | 임의의 충분히 긴 `N8N_ENCRYPTION_KEY` |
| 모의 수집 | API 키 불필요 |

```bash
bash scripts/up.sh
# GUI: http://localhost:8080/ui
# n8n: http://localhost:5678
bash scripts/down.sh
```

Python 서비스만 필요한 경우 `docker compose up -d --build pipeline`으로 시작할 수 있습니다. `scripts/import-workflows.sh`는 n8n 래퍼를 사용하는 경우에만 필요하며, 워크플로우를 import/publish하고 n8n을 재시작합니다.

## Python 단독 실행

Python 3.11 이상으로 가상환경을 만들고 저장소의 의존성을 설치합니다. 컨테이너는 Python 3.11을 사용합니다.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r apps/pipeline/requirements.txt
export PYTHONPATH=apps/pipeline/src
export OUTPUT_ROOT=outputs/runs
export OPERATOR_STATE_ROOT=outputs/operator_state
python -m uvicorn southpole_pipeline.api:app --host 127.0.0.1 --port 8080
```

Python 단독 실행은 `.env`를 자동으로 읽지 않습니다. 실제 수집/AI 초안에 필요한 키는 프로세스 환경으로 전달하세요. `.env.example`의 `/workspace/...`는 컨테이너 경로이므로 위 로컬 경로와 혼용하지 않습니다.

## 모의 검증

Docker가 준비되어 있으면:

```bash
bash scripts/check-portability.sh
bash scripts/verify.sh
```

Python 가상환경에서는 외부 호출 없이 실행할 수 있습니다.

```bash
PYTHONPATH=apps/pipeline/src OUTPUT_ROOT=outputs/runs   python -m southpole_pipeline.cli run   --keywords 'kbeauty,oliveyoung' --days 365 --slug mock-check   --mock-file apps/pipeline/fixtures/mock_apify_items.json
```

fixture는 2026-03-08~11의 고정 4건입니다. 2026-10-07 기준 365일 창에서 4건/크리에이터 3명이 남으며, 7일 창에서는 0건입니다. `verify.sh`는 7일 창과 파일 존재만 검사하므로 통과와 유효 행 수를 구분하세요. 상세 실측은 [검증 기록](docs/verification.md)에 있습니다.

GUI에는 `mock_file` 입력란이 없습니다. 모의 CLI/API 실행 후 GUI에서 실행 목록과 크리에이터 결과를 확인할 수 있습니다. 모의 데이터를 실제 수집 결과로 표시하지 않습니다.

## 보존 및 복구

- `.env`, `outputs/`, `state/n8n/`는 로컬 자료입니다. 백업·복구는 소유자가 관리합니다.
- n8n 암호화 키는 기존 상태의 키와 일치해야 합니다. 문제가 있어도 상태 디렉터리를 바로 지우지 말고 백업·키 설정부터 확인하세요.
- 8080/5678 충돌, Docker 실행 상태, `docker compose logs --tail=100 pipeline`을 확인하세요. 로그 공유 전 키·개인정보를 제거합니다.
- 레거시 5679 구성과 현재 스택을 혼용하지 않습니다. [레거시 문서](docs/runbook.md)는 별도 참고 자료입니다.
- 현재 API는 인증 없는 로컬 도구입니다. 외부 공개 서버로 직접 운영하는 절차는 제공하지 않습니다.
