# Southpole

TikTok 키워드 리서치를 로컬에서 실행하고 크리에이터 결과를 확인하는 도구입니다. 필요할 때 OpenAI로 DM **초안**을 만들 수 있습니다. 소스 저장소는 [bglassm/southpole-marketer](https://github.com/bglassm/southpole-marketer)이며 공개 상태입니다.

## 사용 흐름

1. `http://localhost:8080/ui`에서 키워드·기간·실행 이름을 입력합니다.
2. **Run Collect + Aggregate**가 Apify 수집 → 정규화 → 키워드·크리에이터 집계를 실행합니다.
3. **Latest Creators Preview**에서 크리에이터를 확인하고 HTML 보고서·크리에이터 CSV 링크를 엽니다. 요약 JSON과 XLSX는 실행 폴더에 저장됩니다.
4. 선택적으로 **Generate DM Drafts**를 실행해 `dm_review.html`과 메시지 파일을 사람이 검토합니다. 메시지를 발송하지 않습니다.

실행별 결과는 `outputs/runs/<run_id>/`에 저장됩니다. 댓글 분석·규칙 기반 점수화·아웃리치 상태 동기화는 별도 API/CLI 단계이며 기본 수집 버튼이 자동 실행하지 않습니다.

## 실행

Docker Desktop과 Compose를 준비한 뒤 저장소 루트에서 실행합니다.

```bash
cp .env.example .env
# .env: 실제 수집에는 APIFY_TOKEN, AI 초안에는 OPENAI_API_KEY 설정
# n8n을 사용할 때는 N8N_ENCRYPTION_KEY도 설정
bash scripts/up.sh
```

[Operator UI](http://localhost:8080/ui)를 열고 종료할 때 `bash scripts/down.sh`를 실행합니다. macOS/Windows 런처는 `start.command`/`start.bat`입니다. Python 단독 실행과 상세 설정은 [실행 가이드](REBUILD.md)를 참고하세요.

## 모의 검증

```bash
bash scripts/check-portability.sh
bash scripts/verify.sh
```

`verify.sh`는 Docker로 고정 fixture를 읽고 산출물 파일의 존재를 검사합니다. fixture 날짜가 기간 밖이면 **0행이어도 통과**할 수 있습니다. 키 없이 의미 있는 입력·출력을 비교하는 Python 명령과 [실행 기록·실제 GUI 캡처](docs/verification.md)를 함께 확인하세요. 실서비스 수집·AI 호출의 성공 기록과는 구분합니다.

## 현재 범위와 한계

- 실제 수집 경로는 **TikTok/Apify**입니다. 다중 SNS 수집, OAuth, 실제 게시·예약, 자동 DM 발송, Clay 연동은 구현되어 있지 않습니다.
- AI DM 초안에는 별도 API 키와 호출 비용이 필요합니다. 초안 검토 화면에는 승인 상태 저장이나 발송 기능이 없습니다.
- 기본 수집은 동기 요청입니다. GUI에 모의 데이터 선택 기능은 없습니다. 수집량은 Actor 동작에 의존하며 `APIFY_MAX_ITEMS`는 현재 코드에서 강제 상한으로 적용되지 않습니다.
- 개인 로컬 환경을 전제로 하며 API에 사용자 인증이 없습니다. Compose의 공개 포트와 `/artifacts`의 결과 노출 범위를 확인하고 인터넷에 직접 노출하지 마세요.
- 저장소 공개는 포함 자료의 라이선스·권리 확인 완료를 뜻하지 않습니다. [공개 이력 점검](docs/public-history-review.md)에 남은 항목이 있습니다.

## 문서

- [현재 아키텍처](docs/architecture.md) · [향후 로드맵](docs/roadmap.md)
- [한국어 사용 가이드](HANDOFF.ko.md) · [English guide](HANDOFF.md) · [재실행/복구](REBUILD.md)
- [API·CLI](apps/pipeline/README.md) · [출력 스키마](docs/output-files.md) · [저장소 맥락](REPO_CONTEXT.md)
- [레거시 n8n 운영 기록](docs/runbook.md) · [레거시 Looker 구성](docs/looker_studio_setup.md)

현재 Compose는 Python 서비스와 n8n을 함께 구성합니다. `n8n/workflows/`는 Python `/run` 호출용 래퍼이며, `docker/`·`workflows/`의 이전 KoreaSignals/Sheets 구성과 구분합니다.
