# Southpole 사용 가이드

Southpole은 TikTok 키워드 수집·집계와 크리에이터 결과 확인을 위한 로컬 도구입니다. [공개 저장소](https://github.com/bglassm/southpole-marketer)의 코드를 사용하며, 실제 데이터와 키는 로컬에 보관합니다.

## 준비와 시작

1. Docker Desktop을 설치하고 실행합니다.
2. 저장소 루트에서 `.env.example`을 `.env`로 복사합니다.
3. 실제 수집에는 `APIFY_TOKEN`, AI 초안에는 `OPENAI_API_KEY`, n8n에는 `N8N_ENCRYPTION_KEY`를 설정합니다. AI 초안은 선택 기능입니다.
4. macOS는 `start.command`, Windows는 `start.bat`을 실행합니다. 셸에서는 `bash scripts/up.sh`입니다.
5. `http://localhost:8080/ui`에 접속합니다.

시작 런처는 Docker 설치를 감지하고 필요한 경우 다운로드 페이지를 열지만 자동 설치하지 않습니다. Python 단독 실행은 [REBUILD.md](REBUILD.md)를 참고하세요.

## 키워드에서 결과까지

1. **Keywords**에 쉼표나 줄바꿈으로 키워드를 입력합니다.
2. **Days**와 선택적인 실행 이름을 지정합니다. 기간은 수집된 게시물을 정규화할 때 필터링합니다.
3. **Run Collect + Aggregate**를 누릅니다. 수집·정규화·집계 후 새 실행 폴더가 생성됩니다.
4. **Latest Creators Preview**에서 크리에이터 핸들·이름·집계 수치를 확인합니다. 원본에 없는 팔로워 수치는 확보되었다고 해석하지 않습니다.
5. 화면 링크에서 `report.html`, `creators.csv`를 엽니다. `summary.json`과 Excel 파일은 `outputs/runs/<run_id>/` 실행 폴더에서 확인합니다.

[실제 GUI와 모의 검증 기록](docs/verification.md)은 고정 fixture 기반입니다. GUI 자체에는 모의 실행 선택란이 없습니다. 키 없이 확인하려면 [모의 CLI 실행](REBUILD.md#모의-검증)을 먼저 수행하고 GUI를 새로고침하세요.

## 선택적 AI DM 초안

실행 폴더·언어(`ko`/`en`/`auto`)·개수·브랜드 맥락을 선택하고 **Generate DM Drafts**를 누릅니다. `OPENAI_API_KEY`가 없으면 오류가 나며 대체 초안을 자동 생성하지 않습니다.

결과는 `dm/dm_drafts.csv`, `dm/dm_drafts.json`, `dm/dm_review.html`, `dm/messages/*.txt`입니다. 검토 화면은 내용을 읽고 복사하는 용도입니다. 승인 상태 저장·자동 DM 발송·게시 기능은 없습니다. AI가 제안한 내용은 사실·표현·수신자 적합성을 사람이 확인해야 합니다.

## 추가 처리와 범위

댓글 수집/분석·크리에이터 점수·아웃리치 레지스트리는 [별도 API/CLI](apps/pipeline/README.md)입니다. 수집 버튼이 모두 자동 실행하지 않습니다. 다중 SNS·OAuth·게시/예약·Clay는 [향후 계획](docs/roadmap.md)이며 현재 기능이 아닙니다.

현재 GUI는 Python API를 직접 호출합니다. n8n 현재 래퍼와 옛 Google Sheets 실행 구성은 [아키텍처](docs/architecture.md)에서 구분합니다.

## 종료와 문제 해결

- 종료: `stop.command`, `stop.bat`, 또는 `bash scripts/down.sh`.
- 접속 실패: Docker 상태와 8080/5678 포트 충돌, `docker compose logs --tail=100 pipeline` 확인.
- 수집 실패: 로컬 키·Actor 접근 권한·네트워크 확인. 키나 응답 속 개인정보를 그대로 공유하지 않습니다.
- 결과 0건: 검색 조건과 기간을 확인합니다. 고정 fixture도 기간 밖이면 0건입니다.
- n8n 키 불일치: 상태 백업과 기존 키를 먼저 확인합니다. 데이터를 임의로 삭제하지 않습니다.

API 인증이 없는 로컬 도구이므로 공용 인터넷 서버로 직접 노출하지 않습니다. [공개 이력 점검](docs/public-history-review.md)은 데이터·권리 관련 별도 확인 사항입니다.
