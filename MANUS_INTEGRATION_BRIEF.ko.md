# Manus AI 통합 작업 지시서

## 목적

`bglassm/southpole-marketer`는 현재 로컬 우선 TikTok 리서치 + 크리에이터 분석 + DM 초안 생성 도구입니다. Manus AI의 전천후 마케팅 운영 프로젝트에 이 기능을 통합해, 여러 계정의 콘텐츠/포스팅 현황/리뷰 수집/크리에이터 후보 관리/후속 액션을 한 곳에서 볼 수 있도록 실제 통합 방안을 마련하세요.

이 문서는 단순 아이디어 제안이 아니라, Manus가 repo 구조를 읽고 구체적인 통합 설계와 실행 계획을 산출하기 위한 작업 지시입니다.

## 우선 읽을 파일

먼저 아래 파일을 순서대로 읽으세요.

1. `AGENTS.md`
2. `README.md`
3. `REPO_CONTEXT.md`
4. `HANDOFF.ko.md`
5. `apps/pipeline/README.md`
6. `docs/output-files.md`
7. `docker-compose.yml`
8. `apps/pipeline/src/southpole_pipeline/api.py`
9. `apps/pipeline/src/southpole_pipeline/runner.py`
10. `apps/pipeline/src/southpole_pipeline/dm_generator.py`
11. `apps/pipeline/src/southpole_pipeline/outreach_state.py`
12. `n8n/workflows/southpole_run_pipeline.json`

기존 원격 repo에 `docker/`, `workflows/` 같은 이전 스냅샷 파일이 남아 있을 수 있습니다. 현재 통합 기준은 `docker-compose.yml`, `apps/pipeline/`, `n8n/workflows/southpole_run_pipeline.json`입니다.

## 보안 및 접근 규칙

- `.env` 값, API key, OAuth token, n8n DB, 실행 결과 파일은 요청하거나 노출하지 마세요.
- repo에 있는 `.env.example`만 설정 이름 파악용으로 사용하세요.
- `outputs/runs/`, `outputs/operator_state/`, `state/n8n/`, `data/`는 로컬 생성 데이터로 취급하세요.
- TikTok DM 자동 발송은 현재 범위가 아닙니다. DM은 초안 생성과 사람이 검토하는 흐름까지만 다루세요.
- GitHub Deploy key를 받는 경우 가능하면 read-only로 사용하세요. write access가 필요한 변경은 별도 승인 후 진행하세요.

## 현재 기능 요약

Southpole은 다음 흐름을 제공합니다.

1. Operator UI에서 키워드와 기간을 입력합니다.
2. Apify 기반 TikTok 수집을 실행합니다.
3. 수집 데이터를 정규화하고 집계합니다.
4. creator/profile/post/comment 관련 결과물을 로컬 파일로 저장합니다.
5. creator 점수와 outreach 상태를 동기화합니다.
6. OpenAI 기반 DM 초안을 생성합니다.
7. 사람이 `dm_review.html`, CSV, TXT 메시지 파일을 보고 검토합니다.

주요 API는 다음입니다.

- `GET /health`
- `GET /ui`
- `GET /runs`
- `POST /run`
- `POST /dm/generate`
- `POST /comments/targets`
- `POST /comments/collect`
- `POST /comments/analyze`
- `POST /scoring/creators`
- `POST /outreach/sync`

## Manus 프로젝트와의 통합 목표

Manus의 기존 마케팅 프로젝트가 다음 기능을 갖고 있다고 가정합니다.

- 여러 계정 또는 브랜드의 포스팅 현황을 한 곳에서 확인
- 게시/예약/콘텐츠 상태 관리
- 게시물별 리뷰 또는 반응 수집
- 마케팅 액션의 진행 상황 추적
- 운영자가 한 화면에서 다음 액션을 판단

Southpole을 여기에 통합할 때 목표는 다음입니다.

1. TikTok 리서치 실행 결과를 Manus의 캠페인/계정/콘텐츠 관리 구조에 연결합니다.
2. Southpole의 creator 후보, 점수, DM 초안, outreach 상태를 Manus의 운영 대시보드에서 볼 수 있게 합니다.
3. Manus의 리뷰/반응 수집 기능과 Southpole의 comment analysis 결과를 결합합니다.
4. Southpole이 생성한 output 파일을 일회성 산출물이 아니라 Manus의 지속적인 마케팅 운영 데이터로 흡수합니다.
5. 자동 발송보다는 검토, 승인, 상태 전환, 다음 액션 추천 중심으로 설계합니다.

## 산출해야 할 결과물

Manus는 repo 분석 후 아래 결과물을 작성하세요.

### 1. 현재 구조 분석

다음을 표로 정리하세요.

- 컴포넌트 이름
- 파일/경로
- 역할
- 입력 데이터
- 출력 데이터
- Manus 통합 시 재사용 가능 여부
- 수정 필요 여부

반드시 포함할 컴포넌트:

- Operator UI
- `/run` API
- `/dm/generate` API
- comment target/collect/analyze API
- scoring API
- outreach sync API
- output writers
- n8n workflow
- `.env.example` 설정

### 2. 통합 아키텍처 제안

최소 2가지 방안을 제시하세요.

방안 A: 느슨한 통합
- Manus가 Southpole API를 외부 서비스처럼 호출합니다.
- Southpole은 Docker Compose로 독립 실행됩니다.
- Manus는 run 결과 폴더 또는 API 응답을 읽어 대시보드에 반영합니다.

방안 B: 데이터 계층 통합
- Southpole 산출물을 Manus의 DB 또는 데이터 모델로 ingest합니다.
- `creators.csv`, `summary.json`, `dm_drafts.csv`, `outreach_registry.csv`에 해당하는 데이터를 Manus 엔티티로 매핑합니다.
- 장기적으로 캠페인, 크리에이터, 포스트, 댓글, 리뷰, outreach action을 하나의 데이터 모델로 관리합니다.

각 방안에 대해 다음을 쓰세요.

- 장점
- 단점
- 구현 난이도
- 예상 작업량
- 우선 추천 여부

### 3. 데이터 모델 매핑

Southpole 출력물을 Manus 데이터 구조에 매핑하는 초안을 작성하세요.

필수 매핑 대상:

- `outputs/runs/<run_id>/summary.json`
- `outputs/runs/<run_id>/creators.csv`
- `outputs/runs/<run_id>/keyword_totals.csv`
- `outputs/runs/<run_id>/daily_metrics.csv`
- `outputs/runs/<run_id>/raw_events.csv`
- `outputs/runs/<run_id>/dm/dm_drafts.csv`
- `outputs/operator_state/outreach_registry.csv`
- `outputs/operator_state/outreach_history.jsonl`

권장 Manus 엔티티:

- `Campaign`
- `MarketingAccount`
- `ContentItem`
- `CreatorProfile`
- `CreatorScore`
- `CommentInsight`
- `OutreachDraft`
- `OutreachStatus`
- `ReviewItem`
- `ActionQueueItem`

각 필드의 타입, source file, update frequency, primary key 후보를 제안하세요.

### 4. API 통합 계획

Manus가 호출할 Southpole API wrapper 설계를 제안하세요.

필수 흐름:

1. 캠페인 선택
2. 키워드와 기간 입력
3. `POST /run` 실행
4. run 상태와 결과 확인
5. creator 후보를 Manus DB에 반영
6. `POST /dm/generate`로 DM 초안 생성
7. 운영자 review queue에 DM 초안 등록
8. 승인/보류/수정 필요 상태 관리
9. 댓글/리뷰 분석 결과를 content review 화면에 연결

각 API 호출에 대해 다음을 제시하세요.

- endpoint
- request body 예시
- response에서 저장할 필드
- 실패 시 retry/에러 처리
- UI에 보여줄 상태값

### 5. UI 통합 제안

Manus 대시보드에 추가할 화면 또는 섹션을 구체적으로 제안하세요.

필수 화면:

- 캠페인별 TikTok 리서치 실행 화면
- run history 화면
- creator 후보 리스트
- creator detail 화면
- DM draft review queue
- comment/review insight 화면
- outreach status board

각 화면에 대해 다음을 쓰세요.

- 목적
- 주요 필터
- 주요 컬럼
- 사용자가 누를 버튼
- Southpole 데이터 출처
- Manus 기존 기능과 연결되는 지점

### 6. 실행 우선순위

통합 작업을 3단계로 나누세요.

Phase 1: 읽기 전용 통합
- Southpole 실행 결과를 Manus에서 읽고 보여줍니다.
- 자동 쓰기/상태 변경은 최소화합니다.

Phase 2: 운영 상태 통합
- DM 초안 review queue, outreach 상태, creator scoring을 Manus workflow에 연결합니다.

Phase 3: 캠페인 운영 자동화
- Manus에서 Southpole run을 직접 시작하고, 결과를 자동 ingest하며, 다음 액션 추천까지 제공합니다.

각 phase에 대해 다음을 작성하세요.

- 목표
- 작업 목록
- 수정할 파일/모듈 후보
- acceptance criteria
- 위험 요소

### 7. 바로 실행 가능한 다음 작업

마지막에 “바로 할 일”을 체크리스트로 작성하세요.

예시 형식:

```markdown
## Immediate Next Steps

- [ ] Southpole API schema를 OpenAPI 형태로 정리한다.
- [ ] `summary.json`과 `creators.csv` 샘플을 기준으로 Manus ingest mapper를 설계한다.
- [ ] Manus의 Campaign/Creator/Review 모델과 Southpole output 필드를 매핑한다.
- [ ] 읽기 전용 prototype 화면을 만든다.
- [ ] DM draft review queue 상태값을 정의한다.
```

## 중요한 설계 원칙

- Southpole은 우선 “리서치/분석/초안 생성 엔진”으로 취급하세요.
- Manus는 “운영 대시보드/승인 워크플로우/통합 데이터 허브”로 취급하세요.
- 자동 게시나 자동 DM 발송보다, 사람이 검토하고 승인하는 흐름을 먼저 완성하세요.
- 생성 데이터와 비밀값을 Git에 올리는 방식은 사용하지 마세요.
- 장기적으로는 파일 기반 output을 DB/event 기반 ingest로 바꾸는 방안을 제안하되, 1차 통합은 파일/API 기반으로 빠르게 시작하세요.

## 최종 답변 형식

Manus는 최종 답변을 아래 구조로 작성하세요.

1. Executive Summary
2. Current Southpole Architecture
3. Integration Options
4. Recommended Architecture
5. Data Model Mapping
6. API Integration Plan
7. UI/Workflow Plan
8. Phased Implementation Roadmap
9. Risks And Mitigations
10. Immediate Next Steps

가능하면 추상적인 표현을 피하고, 실제 파일명, endpoint, 데이터 필드, 구현 순서를 포함하세요.
