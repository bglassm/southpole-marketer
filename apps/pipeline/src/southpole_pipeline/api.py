from __future__ import annotations

from typing import Any, Literal

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .collector import CollectorError
from .config import load_settings
from .dm_generator import generate_dm_drafts
from .operator_ui import router as operator_ui_router
from .runner import (
    analyze_comments_for_run,
    build_comment_targets_for_run,
    collect_comments_for_run,
    run_pipeline,
    score_creators_for_run,
    sync_outreach_state_for_run,
)


class RunRequest(BaseModel):
    keywords: str | list[str]
    days: int = Field(default=7, ge=1, le=365)
    slug: str | None = None
    source: str = "n8n"
    mock_file: str | None = None


class DmGenerateRequest(BaseModel):
    run_dir: str | None = None
    language_mode: Literal["auto", "ko", "en"] = Field(default="ko")
    brand_context: str | None = None
    limit: int = Field(default=10, ge=1)


class CommentTargetsRequest(BaseModel):
    run_dir: str | None = None
    max_targets: int = Field(default=20, ge=1, le=500)
    requested_comment_limit: int = Field(default=50, ge=1, le=5000)
    selection_mode: str = "top_by_views"
    selected_by: str = "operator"
    selection_note: str = ""


class CommentCollectRequest(BaseModel):
    run_dir: str | None = None
    targets_file: str | None = None
    mock_file: str | None = None


class CommentAnalyzeRequest(BaseModel):
    run_dir: str | None = None
    limit: int | None = Field(default=None, ge=1)
    analysis_model: str | None = None


class CreatorScoreRequest(BaseModel):
    run_dir: str | None = None


class OutreachSyncRequest(BaseModel):
    run_dir: str | None = None
    campaign_id: str = "default-campaign"
    owner: str = "operator"
    status: str = "pending_review"
    notes: str = ""


app = FastAPI(title="Southpole Pipeline", version="1.0.0")
app.include_router(operator_ui_router)

ARTIFACTS_DIR = load_settings().output_root.parent.resolve()
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/artifacts", StaticFiles(directory=str(ARTIFACTS_DIR)), name="artifacts")


@app.get("/health")
def health() -> dict[str, Any]:
    return {"status": "ok"}


@app.post("/run")
def run(request: RunRequest) -> dict[str, Any]:
    try:
        summary = run_pipeline(
            keywords_input=request.keywords,
            days=request.days,
            slug=request.slug,
            source=request.source,
            mock_file=request.mock_file,
        )
    except (CollectorError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return summary


@app.post("/dm/generate")
def generate_dm(request: DmGenerateRequest) -> dict[str, Any]:
    try:
        return generate_dm_drafts(
            run_dir=request.run_dir,
            language_mode=request.language_mode,
            brand_context=request.brand_context,
            limit=request.limit,
        )
    except (CollectorError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/comments/targets")
def build_comment_targets(request: CommentTargetsRequest) -> dict[str, Any]:
    try:
        return build_comment_targets_for_run(
            run_dir=request.run_dir,
            max_targets=request.max_targets,
            requested_comment_limit=request.requested_comment_limit,
            selection_mode=request.selection_mode,
            selected_by=request.selected_by,
            selection_note=request.selection_note,
        )
    except (CollectorError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/comments/collect")
def collect_comments(request: CommentCollectRequest) -> dict[str, Any]:
    try:
        return collect_comments_for_run(
            run_dir=request.run_dir,
            targets_file=request.targets_file,
            mock_file=request.mock_file,
        )
    except (CollectorError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/comments/analyze")
def analyze_comments(request: CommentAnalyzeRequest) -> dict[str, Any]:
    try:
        return analyze_comments_for_run(
            run_dir=request.run_dir,
            limit=request.limit,
            analysis_model=request.analysis_model,
        )
    except (CollectorError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/scoring/creators")
def score_creators(request: CreatorScoreRequest) -> dict[str, Any]:
    try:
        return score_creators_for_run(run_dir=request.run_dir)
    except (CollectorError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/outreach/sync")
def sync_outreach(request: OutreachSyncRequest) -> dict[str, Any]:
    try:
        return sync_outreach_state_for_run(
            run_dir=request.run_dir,
            campaign_id=request.campaign_id,
            owner=request.owner,
            status=request.status,
            notes=request.notes,
        )
    except (CollectorError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc
